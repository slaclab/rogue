#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Title      : PyRogue base module - Root Class
#-----------------------------------------------------------------------------
# File       : pyrogue/_Root.py
# Created    : 2017-05-16
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to 
# the license terms in the LICENSE.txt file found in the top-level directory 
# of this distribution and at: 
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html. 
# No part of the rogue software platform, including this file, may be 
# copied, modified, propagated, or distributed except according to the terms 
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
import rogue.interfaces.memory
import yaml
import threading
from collections import OrderedDict as odict
import logging
import pyrogue as pr
import Pyro4
import Pyro4.naming
import functools as ft

class RootLogHandler(logging.Handler):
    """ Class to listen to log entries and add them to syslog variable"""
    def __init__(self,*, root):
        logging.Handler.__init__(self)
        self._root = root

    def emit(self,record):
        with self._root._sysLogLock:
            val = self._root.SystemLog.value()
            val += (self.format(record).splitlines()[0] + '\n')
            self._root.SystemLog.set(write=False,value=val)
        self._root.SystemLog.updated() # Update outside of lock

class Root(rogue.interfaces.stream.Master,pr.Device):
    """
    Class which serves as the root of a tree of nodes.
    The root is the interface point for tree level access and updats.
    The root is a stream master which generates frames containing tree
    configuration and status values. This allows confiuration and status
    to be stored in data files.
    """

    def __enter__(self):
        """Root enter."""
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Root exit."""
        self.stop()

    def __init__(self, *, name, description):
        """Init the node with passed attributes"""

        rogue.interfaces.stream.Master.__init__(self)

        # Create log listener to add to systemlog variable
        formatter = logging.Formatter("%(msg)s")
        handler = RootLogHandler(root=self)
        handler.setLevel(logging.ERROR)
        handler.setFormatter(formatter)
        self._logger = logging.getLogger('pyrogue')
        self._logger.addHandler(handler)

        # Keep of list of errors, exposed as a variable
        self._sysLogLock = threading.Lock()

        # Background threads
        self._pollQueue = None
        self._running   = False

        # Remote object export
        self._pyroThread = None
        self._pyroDaemon = None

        # Variable update list
        self._updatedDict = None
        self._updatedLock = threading.Lock()

        # Variable update listener
        self._varListeners  = []

        # Init after _updatedLock exists
        pr.Device.__init__(self, name=name, description=description)

        # Variables
        self.add(pr.LocalVariable(name='SystemLog', value='', mode='RO', hidden=True,
            description='String containing newline seperated system logic entries'))

        self.add(pr.LocalVariable(name='ForceWrite', value=False, mode='RW', hidden=True,
            description='Configuration Flag To Control Write All Block'))

    def start(self, initRead=False, initWrite=False, pollEn=True, pyroGroup=None, pyroHost=None, pyroNs=None):
        """Setup the tree. Start the polling thread."""

        # Create poll queue object
        if pollEn:
            self._pollQueue = pr.PollQueue(root=self)

        # Set myself as root
        self._parent = self
        self._root   = self
        self._path   = self.name

        for key,value in self._nodes.items():
            value._rootAttached(self,self)

        # Get list of deprecated nodes
        lst = self._getDepWarn()

        cnt=len(lst)
        if cnt > 0:
            print("----------- Deprecation Warning --------------------------------")
            print("The following nodes were created with deprecated calls:")
            if cnt > 50:
                print("   (Only showing 50 out of {} total deprecated nodes)".format(cnt))

            for n in lst[:50]:
                print("   " + n)

            print("----------------------------------------------------------------")

        # Start pyro server if enabled
        if pyroGroup is not None:
            Pyro4.config.THREADPOOL_SIZE = 1000
            Pyro4.config.SERVERTYPE = "multiplex"
            Pyro4.config.POLLTIMEOUT = 3

            Pyro4.util.SerializerBase.register_dict_to_class("collections.OrderedDict", recreate_OrderedDict)

            self._pyroDaemon = Pyro4.Daemon(host=pyroHost)

            uri = self._pyroDaemon.register(self)

            # Do we create our own nameserver?
            try:
                if pyroNs is None:
                    nsUri, nsDaemon, nsBcast = Pyro4.naming.startNS(host=pyroHost)
                    self._pyroDaemon.combine(nsDaemon)
                    if nsBcast is not None:
                        self._pyroDaemon.combine(nsBcast)
                    ns = nsDaemon.nameserver
                    self._log.info("Started pyro4 nameserver: {}".format(nsUri))
                else:
                    ns = Pyro4.locateNS(pyroNs)
                    self._log.info("Using pyro4 nameserver at host: {}".format(pyroNs))

                ns.register('{}.{}'.format(pyroGroup,self.name),uri)
                self._exportNodes(self._pyroDaemon)
                self._pyroThread = threading.Thread(target=self._pyroDaemon.requestLoop)
                self._pyroThread.start()

            except Exception as e:
                self._log.error("Failed to start or locate pyro4 nameserver with error: {}".format(e))

        # Read current state
        if initRead:
            self._read()

        # Commit default values
        # Read did not override defaults because set values are cached
        if initWrite:
            self._write()

        # Start poller if enabled
        if pollEn:
            self._pollQueue._start()

        self._running = True

    def stop(self):
        """Stop the polling thread. Must be called for clean exit."""
        if self._pollQueue:
            self._pollQueue.stop()
        if self._pyroDaemon:
            self._pyroDaemon.shutdown()
        self._running=False

    @Pyro4.expose
    @property
    def running(self):
        return self._running

    @Pyro4.expose
    def getNode(self, path):
        return self._getPath(path)

    @ft.lru_cache(maxsize=None)
    def _getPath(self,path):
        """Find a node in the tree that has a particular path string"""
        obj = self
        if '.' in path:
            for a in path.split('.')[1:]:
                obj = obj.node(a)

        return obj

    @Pyro4.expose
    def addVarListener(self,func):
        """
        Add a variable update listener function.
        The variable, value and display string will be passed as an arg: func(var,value,disp)
        """
        self._varListeners.append(func)

    def getYaml(self,readFirst,modes=['RW']):
        """
        Get current values as a yaml dictionary.
        modes is a list of variable modes to include.
        If readFirst=True a full read from hardware is performed.
        """
        ret = ""

        if readFirst: self._read()
        try:
            ret = dictToYaml({self.name:self._getDict(modes)},default_flow_style=False)
        except Exception as e:
            self._log.exception(e)

        return ret

    def setYaml(self,yml,writeEach,modes=['RW']):
        """
        Set variable values or execute commands from a dictionary.
        modes is a list of variable modes to act on.
        writeEach is set to true if accessing a single variable at a time.
        Writes will be performed as each variable is updated. If set to 
        false a bulk write will be performed after all of the variable updates
        are completed. Bulk writes provide better performance when updating a large
        quanitty of variables.
        """
        d = yamlToDict(yml)
        self._initUpdatedVars()

        for key, value in d.items():
            if key == self.name:
                self._setDict(value,writeEach,modes)

        self._doneUpdatedVars()

        if not writeEach: self._write()

    @Pyro4.expose
    def get(self,path):
        obj = self.getNode(path)
        return obj.get()

    @Pyro4.expose
    def getDisp(self,path):
        obj = self.getNode(path)
        return obj.getDisp()

    @Pyro4.expose
    def value(self,path):
        obj = self.getNode(path)
        return obj.value()

    @Pyro4.expose
    def valueDisp(self,path):
        obj = self.getNode(path)
        return obj.valueDisp()

    @Pyro4.expose
    def set(self,path,value):
        obj = self.getNode(path)
        return obj.set(value)

    @Pyro4.expose
    def setDisp(self,path,value):
        obj = self.getNode(path)
        return obj.setDisp(value)

    @Pyro4.expose
    def exec(self,path,arg):
        obj = self.getNode(path)
        return obj.call(arg)

    def setTimeout(self,timeout):
        """
        Set timeout value on all devices & blocks
        """
        for key,value in self._nodes.items():
            value._setTimeout(timeout)

    def _sendYamlFrame(self,yml):
        """
        Generate a frame containing the passed string.
        """
        frame = self._reqFrame(len(yml),True,0)
        b = bytearray(yml,'utf-8')
        frame.write(b,0)
        self._sendFrame(frame)

    def _streamYaml(self,modes=['RW','RO']):
        """
        Generate a frame containing all variables values in yaml format.
        A hardware read is not generated before the frame is generated.
        Vlist can contain an optional list of variale paths to include in the
        stream. If this list is not NULL only these variables will be included.
        """
        self._sendYamlFrame(self.getYaml(False,modes))

    def _initUpdatedVars(self):
        """Initialize the update tracking log before a bulk variable update"""
        with self._updatedLock:
            self._updatedDict = odict()

    def _doneUpdatedVars(self):
        """Stream the results of a bulk variable update and update listeners"""
        with self._updatedLock:
            if self._updatedDict:
                yml = dictToYaml(self._updatedDict,default_flow_style=False)
                self._sendYamlFrame(yml)
                self._updatedDict = None

    @pr.command(order=7, name='WriteAll', description='Write all values to the hardware')
    def _write(self):
        """Write all blocks"""
        self._log.info("Start root write")
        try:
            self.writeBlocks(force=self.ForceWrite.value(), recurse=True)
            self._log.info("Verify root read")
            self.verifyBlocks(recurse=True)
            self._log.info("Check root read")
            self.checkBlocks(recurse=True)
        except Exception as e:
            self._log.exception(e)
        self._log.info("Done root write")

    @pr.command(order=6, name="ReadAll", description='Read all values from the hardware')
    def _read(self):
        """Read all blocks"""
        self._log.info("Start root read")
        self._initUpdatedVars()
        try:
            self.readBlocks(recurse=True)
            self._log.info("Check root read")
            self.checkBlocks(recurse=True)
        except Exception as e:
            self._log.exception(e)
        self._doneUpdatedVars()
        self._log.info("Done root read")

    @pr.command(order=0, name='WriteConfig', value='', description='Write configuration to passed filename in YAML format')
    def _writeConfig(self,arg):
        """Write YAML configuration to a file. Called from command"""
        try:
            with open(arg,'w') as f:
                f.write(self.getYaml(True,modes=['RW']))
        except Exception as e:
            self._log.exception(e)

    @pr.command(order=1, name='ReadConfig', value='', description='Read configuration from passed filename in YAML format')
    def _readConfig(self,arg):
        """Read YAML configuration from a file. Called from command"""
        try:
            with open(arg,'r') as f:
                self.setYaml(f.read(),False,['RW'])
        except Exception as e:
            self._log.exception(e)

    @pr.command(order=3, name='SoftReset', description='Generate a soft reset to each device in the tree')
    def _softReset(self):
        """Generate a soft reset on all devices"""
        self.callRecursive('softReset', nodeTypes=[pr.Device])

    @pr.command(order=2, name='HardReset', description='Generate a hard reset to each device in the tree')
    def _hardReset(self):
        """Generate a hard reset on all devices"""
        self.callRecursive('hardReset', nodeTypes=[pr.Device])        
        self._clearLog()

    @pr.command(order=4, name='CountReset', description='Generate a count reset to each device in the tree')
    def _countReset(self):
        """Generate a count reset on all devices"""
        self.callRecursive('countReset', nodeTypes=[pr.Device])        

    @pr.command(order=5, name='ClearLog', description='Clear the message log cntained in the SystemLog variable')
    def _clearLog(self):
        """Clear the system log"""
        with self._sysLogLock:
            self.SystemLog.set(value='',write=False)
        self.SystemLog.updated()

    def _varUpdated(self,var,value,disp):
        for func in self._varListeners:

            try:
                if hasattr(func,'varListener'):
                    func.varListener(var,value,disp)
                else:
                    func(var,value,disp)

            except Pyro4.errors.CommunicationError as msg:
                if 'Connection refused' in str(msg):
                    self._log.info("Pyro Disconnect. Removing callback")
                    self._varListeners.remove(func)
                else:
                    self._log.error("Pyro callback failed for {}: {}".format(self.name,msg))
                    print("Pyro callback failed for {}: {}".format(self.name,msg))

        with self._updatedLock:

            # Log is active add to log
            if self._updatedDict is not None:
                addPathToDict(self._updatedDict,var.path,disp)

            # Otherwise act directly
            else:
                d   = {}
                addPathToDict(d,var.path,disp)
                yml = dictToYaml(d,default_flow_style=False)
                self._sendYamlFrame(yml)


class PyroRoot(pr.PyroNode):
    def __init__(self, *, node,daemon):
        pr.PyroNode.__init__(self,root=self,node=node,daemon=daemon)

        self._varListeners  = {}
        self._rootListeners = {}

    def addInstance(self,node):
        self._daemon.register(node)

    def getNode(self, path):
        return pr.PyroNode(root=self,node=self._node.getNode(path),daemon=self._daemon)

    def addVarListener(self,listener):
        self._rootListeners.append(listener)

    def _addRootVarListener(self, path, listener):
        if not path in self._varListeners:
            self._varListeners[path] = []

        self._varListeners[path].append(listener)

    @Pyro4.expose
    def rootListener(self, yml, l):
        for f in self._rootListeners:
            f.rootListener(yml, l)

    @Pyro4.expose
    def varListener(self, var, value, disp):
        locVar = pr.PyroNode(root=self,node=var,daemon=self._daemon)
        path   = locVar.path

        if path in self._varListeners:
            for f in self._varListeners[path]:
                f.varListener(var=locVar, value=value, disp=disp)


class PyroClient(object):
    def __init__(self, group, host=None, ns=None):
        self._group = group

        Pyro4.config.THREADPOOL_SIZE = 100
        Pyro4.config.SERVERTYPE = "multiplex"
        Pyro4.config.POLLTIMEOUT = 3

        Pyro4.util.SerializerBase.register_dict_to_class("collections.OrderedDict", recreate_OrderedDict)

        try:
            self._ns = Pyro4.locateNS(host=ns)
        except:
            raise pr.NodeError("PyroClient Failed to find nameserver")

        self._pyroDaemon = Pyro4.Daemon(host=host)

        self._pyroThread = threading.Thread(target=self._pyroDaemon.requestLoop)
        self._pyroThread.start()

    def stop(self):
        self._pyroDaemon.shutdown()

    def getRoot(self,name):
        try:
            uri = self._ns.lookup("{}.{}".format(self._group,name))
            ret = PyroRoot(node=Pyro4.Proxy(uri),daemon=self._pyroDaemon)
            self._pyroDaemon.register(ret)

            ret._node.addVarListener(ret)
            return ret
        except:
            raise pr.NodeError("PyroClient Failed to find {}.{}.".format(self._group,name))


def addPathToDict(d, path, value):
    """Helper function to add a path/value pair to a dictionary tree"""
    npath = path
    sd = d

    # Transit through levels
    while '.' in npath:
        base  = npath[:npath.find('.')]
        npath = npath[npath.find('.')+1:]

        if base in sd:
           sd = sd[base]
        else:
           sd[base] = odict()
           sd = sd[base]

    # Add final node
    sd[npath] = value


def yamlToDict(stream, Loader=yaml.Loader, object_pairs_hook=odict):
    """Load yaml to ordered dictionary"""
    class OrderedLoader(Loader):
        pass
    def construct_mapping(loader, node):
        loader.flatten_mapping(node)
        return object_pairs_hook(loader.construct_pairs(node))
    OrderedLoader.add_constructor(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
        construct_mapping)
    return yaml.load(stream, OrderedLoader)


def dictToYaml(data, stream=None, Dumper=yaml.Dumper, **kwds):
    """Convert ordered dictionary to yaml"""
    class OrderedDumper(Dumper):
        pass
    def _dict_representer(dumper, data):
        return dumper.represent_mapping(
            yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,data.items())
    OrderedDumper.add_representer(odict, _dict_representer)
    try:
        ret = yaml.dump(data, stream, OrderedDumper, **kwds)
    except Exception as e:
        #print("Error: {} dict {}".format(e,data))
        return None
    return ret

def recreate_OrderedDict(name, values):
    return odict(values['items'])

def generateAddressMap(root,fname):
    vlist = root.variableList

    with open(fname,'w') as f:
        f.write("Path\t")
        f.write("Type\t")
        f.write("Offset\t")
        f.write("BitOffset\t")
        f.write("BitSize\t")
        f.write("Enum\t")
        f.write("Description\n")

        for v in vlist:
            if isinstance(v, pr.RemoteVariable):
                f.write("{}\t".format(v.path))
                f.write("{}\t".format(type(v)))
                f.write("{:#x}\t".format(v.offset))
                f.write("{}\t".format(v.bitOffset))
                f.write("{}\t".format(v.bitSize))
                f.write("{}\t".format(v.enum))
                f.write("{}\n".format(v.description))

