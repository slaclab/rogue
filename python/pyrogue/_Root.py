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
import time
import queue
from contextlib import contextmanager

class RootLogHandler(logging.Handler):
    """ Class to listen to log entries and add them to syslog variable"""
    def __init__(self,*, root):
        logging.Handler.__init__(self)
        self._root = root

    def emit(self,record):
        with self._root.updateGroup():
           try:
               val = (self.format(record).splitlines()[0] + '\n')
               self._root.SystemLog += val
           except e:
               print("-----------Error Logging Exception -------------")
               print(e)
               print("------------------------------------------------")

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

    def __init__(self, *, name=None, description=''):
        """Init the node with passed attributes"""

        rogue.interfaces.stream.Master.__init__(self)

        # Create log listener to add to systemlog variable
        formatter = logging.Formatter("%(msg)s")
        handler = RootLogHandler(root=self)
        handler.setLevel(logging.ERROR)
        handler.setFormatter(formatter)
        self._logger = logging.getLogger('pyrogue')
        self._logger.addHandler(handler)

        # Running status
        self._running = False

        # Polling worker
        self._pollQueue = None

        # Remote object export
        self._pyroThread = None
        self._pyroDaemon = None

        # List of variable listeners
        self._varListeners  = []
        self._varListenLock = threading.Lock()

        # Variable update worker
        self._updateQueue = queue.Queue()
        self._updateThread = None

        # Init 
        pr.Device.__init__(self, name=name, description=description)

        # Variables
        self.add(pr.LocalVariable(name='SystemLog', value='', mode='RO', hidden=True,
            description='String containing newline seperated system logic entries'))

        self.add(pr.LocalVariable(name='ForceWrite', value=False, mode='RW', hidden=True,
            description='Configuration Flag To Control Write All Block'))

        # Commands
        self.add(pr.LocalCommand(name='WriteAll', function=self._write, 
                                 description='Write all values to the hardware'))

        self.add(pr.LocalCommand(name="ReadAll", function=self._read,
                                 description='Read all values from the hardware'))

        self.add(pr.LocalCommand(name='WriteConfig', value='', function=self._writeConfig,
                                 description='Write configuration to passed filename in YAML format'))

        self.add(pr.LocalCommand(name='ReadConfig', value='', function=self._readConfig,
                                 description='Read configuration from passed filename in YAML format'))

        self.add(pr.LocalCommand(name='SoftReset', function=self._softReset,
                                 description='Generate a soft reset to each device in the tree'))

        self.add(pr.LocalCommand(name='HardReset', function=self._hardReset,
                                 description='Generate a hard reset to each device in the tree'))

        self.add(pr.LocalCommand(name='CountReset', function=self._countReset,
                                 description='Generate a count reset to each device in the tree'))

        self.add(pr.LocalCommand(name='ClearLog', function=self._clearLog,
                                 description='Clear the message log cntained in the SystemLog variable'))


    def start(self, timeout=1.0, initRead=False, initWrite=False, pollEn=True, pyroGroup=None, pyroAddr=None, pyroNsAddr=None):
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

        # Look for device overlaps
        tmpDevs = self.deviceList
        tmpDevs.sort(key=lambda x: (x.memBaseId, x.address, x.size))

        for i in range(1,len(tmpDevs)):
            if (tmpDevs[i].size != 0) and (tmpDevs[i].memBaseId == tmpDevs[i-1].memBaseId) and \
                (tmpDevs[i].address < (tmpDevs[i-1].address + tmpDevs[i-1].size)):

                print("\n\n\n------------------------ Device Overlap Warning !!! --------------------------------")
                print("Device {} at address={:#x} overlaps {} at address={:#x} with size={}".format(
                      tmpDevs[i].path,tmpDevs[i].address,tmpDevs[i-1].path,tmpDevs[i-1].address,tmpDevs[i-1].size))
                print("This warning will be replaced with an exception in the next release!!!!!!!!")

                #raise pr.NodeError("Device {} at address={} overlaps {} at address={} with size={}".format(
                #    tmpDevs[i].path,tmpDevs[i].address,tmpDevs[i-1].path,tmpDevs[i-1].address,tmpDevs[i-1].size))

        # Set timeout if not default
        if timeout != 1.0:
            for key,value in self._nodes.items():
                value._setTimeout(timeout)

        # Start pyro server if enabled
        if pyroGroup is not None:
            Pyro4.config.THREADPOOL_SIZE = 1000
            Pyro4.config.SERVERTYPE = "multiplex"
            Pyro4.config.POLLTIMEOUT = 3

            Pyro4.util.SerializerBase.register_dict_to_class("collections.OrderedDict", recreate_OrderedDict)

            self._pyroDaemon = Pyro4.Daemon(host=pyroAddr)

            uri = self._pyroDaemon.register(self)

            # Do we create our own nameserver?
            try:
                if pyroNsAddr is None:
                    nsUri, nsDaemon, nsBcast = Pyro4.naming.startNS(host=pyroAddr)
                    self._pyroDaemon.combine(nsDaemon)
                    if nsBcast is not None:
                        self._pyroDaemon.combine(nsBcast)
                    ns = nsDaemon.nameserver
                    self._log.info("Started pyro4 nameserver: {}".format(nsUri))
                else:
                    ns = Pyro4.locateNS(pyroNsAddr)
                    self._log.info("Using pyro4 nameserver at addr: {}".format(pyroNsAddr))

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

        # Start update thread
        self._updateThread = threading.Thread(target=self._updateWorker)
        self._updateThread.start()

        # Start poller if enabled
        if pollEn:
            self._pollQueue._start()

        self._running = True

    def stop(self):
        """Stop the polling thread. Must be called for clean exit."""
        self._updateQueue.put(None)

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
        The variable, value and display string will be passed as an arg: func(path,value,disp)
        """
        with self._varListenLock:
            self._varListeners.append(func)

            if isinstance(func,Pyro4.core.Proxy):                                    
                func._pyroOneway.add("varListener")                                  

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

    def setYaml(self,yml,writeEach,modes=['RW','WO']):
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
        with self.updateGroup():

            for key, value in d.items():
                if key == self.name:
                    self._setDict(value,writeEach,modes)
                else:
                    try:
                        self._getPath(key).setDisp(value)
                    except:
                        self._log.error("Entry {} not found".format(key))

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

    @contextmanager
    def updateGroup(self):

        # At wtih call
        self._updateQueue.put(True)

        # Return to block within with call
        try:
            yield
        finally:

            # After with is done
            self._updateQueue.put(False)

    def _sendYamlFrame(self,yml):
        """
        Generate a frame containing the passed string.
        """
        b = bytearray(yml,'utf-8')
        frame = self._reqFrame(len(b),True)
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

    def _write(self):
        """Write all blocks"""
        self._log.info("Start root write")
        with self.updateGroup():
            try:
                self.writeBlocks(force=self.ForceWrite.value(), recurse=True)
                self._log.info("Verify root read")
                self.verifyBlocks(recurse=True)
                self._log.info("Check root read")
                self.checkBlocks(recurse=True)
            except Exception as e:
                self._log.exception(e)
        self._log.info("Done root write")

    def _read(self):
        """Read all blocks"""
        self._log.info("Start root read")
        with self.updateGroup():
            try:
                self.readBlocks(recurse=True)
                self._log.info("Check root read")
                self.checkBlocks(recurse=True)
            except Exception as e:
                self._log.exception(e)
        self._log.info("Done root read")

    def _writeConfig(self,arg):
        """Write YAML configuration to a file. Called from command"""
        try:
            with open(arg,'w') as f:
                f.write(self.getYaml(True,modes=['RW']))
        except Exception as e:
            self._log.exception(e)

    def _readConfig(self,arg):
        """Read YAML configuration from a file. Called from command"""
        try:
            with open(arg,'r') as f:
                self.setYaml(f.read(),False,['RW','WO'])
        except Exception as e:
            self._log.exception(e)

    def _softReset(self):
        """Generate a soft reset on all devices"""
        self.callRecursive('softReset', nodeTypes=[pr.Device])

    def _hardReset(self):
        """Generate a hard reset on all devices"""
        self.callRecursive('hardReset', nodeTypes=[pr.Device])        
        self._clearLog()

    def _countReset(self):
        """Generate a count reset on all devices"""
        self.callRecursive('countReset', nodeTypes=[pr.Device])        

    def _clearLog(self):
        """Clear the system log"""
        self.SystemLog.set('')

    def _queueUpdates(self,var):
        self._updateQueue.put(var)

    # Worker thread
    def _updateWorker(self):
        self._log.info("Starting update thread")

        # Init
        count = 0
        uvars = {}

        while True:
            ent = self._updateQueue.get()

            # Done
            if ent is None:
                self._log.info("Stopping update thread")
                return

            # Increment
            elif ent is True:
                count += 1

            # Decrement
            elif ent is False:
                if count > 0:
                    count -= 1

            # Variable
            else:
                uvars[ent.path] = ent

            # Process list if count = 0
            if count == 0 and len(uvars) > 0:

                self._log.debug(F"Process update group. Length={len(uvars)}. Entry={list(uvars.keys())[0]}")
                yml = ""

                for p,v in uvars.items():
                    path,value,disp = v._doUpdate()

                    # Update yaml string
                    yml += (f"{path}:{disp}" + "\n")

                    # Call listener functions,
                    with self._varListenLock:
                        for func in self._varListeners:
                            try:

                                if isinstance(func,Pyro4.core.Proxy) or hasattr(func,'varListener'):
                                    func.varListener(path,value,disp)
                                else:
                                    func(path,value,disp)

                            except Pyro4.errors.CommunicationError as msg:
                                if 'Connection refused' in str(msg):
                                    self._log.info("Pyro Disconnect. Removing callback")
                                    self._varListeners.remove(func)
                                else:
                                    self._log.error("Pyro callback failed for {}: {}".format(self.name,msg))

                # Generate yaml stream
                self._sendYamlFrame(yml)

                # Init var list
                uvars = {}

            # Set done
            self._updateQueue.task_done()


class PyroRoot(pr.PyroNode):
    def __init__(self, *, node,daemon):
        pr.PyroNode.__init__(self,root=self,node=node,daemon=daemon)

        self._varListeners   = []
        self._relayListeners = {}

    def addInstance(self,node):
        self._daemon.register(node)

    def getNode(self, path):
        return pr.PyroNode(root=self,node=self._node.getNode(path),daemon=self._daemon)

    def addVarListener(self,listener):
        self._varListeners.append(listener)

    def _addRelayListener(self, path, listener):
        if not path in self._relayListeners:
            self._relayListeners[path] = []

        self._relayListeners[path].append(listener)

    @Pyro4.expose
    def varListener(self, path, value, disp):
        for f in self._varListeners:
            f.varListener(path=path, value=value, disp=disp)

        if path in self._relayListeners:
            for f in self._relayListeners[path]:
                f.varListener(path=path, value=value, disp=disp)

class PyroClient(object):
    def __init__(self, group, localAddr=None, nsAddr=None):
        self._group = group

        Pyro4.config.THREADPOOL_SIZE = 100
        Pyro4.config.SERVERTYPE = "multiplex"
        Pyro4.config.POLLTIMEOUT = 3

        Pyro4.util.SerializerBase.register_dict_to_class("collections.OrderedDict", recreate_OrderedDict)

        if nsAddr is None:
            nsAddr = localAddr

        try:
            self._ns = Pyro4.locateNS(host=nsAddr)
        except:
            raise pr.NodeError("PyroClient Failed to find nameserver")

        self._pyroDaemon = Pyro4.Daemon(host=localAddr)

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

