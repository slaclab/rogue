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
           except Exception as e:
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
            description='Configuration Flag To Always Write Non Stale Blocks For WriteAll, LoadConfig and setYaml'))

        self.add(pr.LocalVariable(name='InitAfterConfig', value=False, mode='RW', hidden=True,
            description='Configuration Flag To Execute Initialize after LoadConfig or setYaml'))

        self.add(pr.LocalVariable(name='Time', value=0.0, mode='RO', hidden=True,
                 localGet=lambda: time.time(), pollInterval=1.0, description='Current Time In Seconds Since EPOCH UTC'))

        self.add(pr.LocalVariable(name='LocalTime', value='', mode='RO', hidden=False,
                 localGet=lambda: time.strftime("%Y-%m-%d %H:%M:%S %Z", time.localtime(time.time())),
                 pollInterval=1.0, description='Local Time'))

        # Commands
        self.add(pr.LocalCommand(name='WriteAll', function=self._write, hidden=True,
                                 description='Write all values to the hardware'))

        self.add(pr.LocalCommand(name="ReadAll", function=self._read, hidden=True,
                                 description='Read all values from the hardware'))

        self.add(pr.LocalCommand(name='SaveState', value='', function=self._saveState, hidden=True,
                                 description='Save state to passed filename in YAML format'))

        self.add(pr.LocalCommand(name='SaveConfig', value='', function=self._saveConfig, hidden=True,
                                 description='Save configuration to passed filename in YAML format'))

        self.add(pr.LocalCommand(name='LoadConfig', value='', function=self._loadConfig, hidden=True,
                                 description='Read configuration from passed filename in YAML format'))

        self.add(pr.LocalCommand(name='Initialize', function=self.initialize, hidden=True,
                                 description='Generate a soft reset to each device in the tree'))

        self.add(pr.LocalCommand(name='HardReset', function=self.hardReset, hidden=True,
                                 description='Generate a hard reset to each device in the tree'))

        self.add(pr.LocalCommand(name='CountReset', function=self.countReset, hidden=True,
                                 description='Generate a count reset to each device in the tree'))

        self.add(pr.LocalCommand(name='ClearLog', function=self._clearLog, hidden=True,
                                 description='Clear the message log cntained in the SystemLog variable'))

        self.add(pr.LocalCommand(name='SetYamlConfig', value='', function=lambda arg: self._setYaml(arg,False,['RW','WO']), hidden=True,
                                 description='Set configuration from passed YAML string'))

        self.add(pr.LocalCommand(name='GetYamlConfig', value=True, function=lambda arg: self._getYaml(arg,['RW','WO']), hidden=True,
                                 description='Get current configuration as YAML string. Pass read first arg.'))

        self.add(pr.LocalCommand(name='GetYamlState', value=True, function=lambda arg: self._getYaml(arg,['RW','RO','WO']), hidden=True,
                                 description='Get current state as YAML string. Pass read first arg.'))

    def start(self, timeout=1.0, initRead=False, initWrite=False, pollEn=True, pyroGroup=None, pyroAddr=None, pyroNsAddr=None):
        """Setup the tree. Start the polling thread."""

        # Create poll queue object
        if pollEn:
            self._pollQueue = pr.PollQueue(root=self)

        # Call special root level rootAttached
        self._rootAttached()

        # Get full list of Devices and Blocks
        tmpList = []
        for d in self.deviceList:
            tmpList.append(d)
            for b in d._blocks:
                if isinstance(b, pr.RemoteBlock):
                    tmpList.append(b)

        # Sort the list by address/size
        tmpList.sort(key=lambda x: (x.memBaseId, x.address, x.size))

        # Look for overlaps
        for i in range(1,len(tmpList)):

            self._log.debug("Comparing {} with address={:#x} to {} with address={:#x} and size={}".format(
                            tmpList[i].path,  tmpList[i].address,
                            tmpList[i-1].path,tmpList[i-1].address, tmpList[i-1].size))

            # Detect overlaps
            if (tmpList[i].size != 0) and (tmpList[i].memBaseId == tmpList[i-1].memBaseId) and \
               (tmpList[i].address < (tmpList[i-1].address + tmpList[i-1].size)):

                # Allow overlaps between Devices and Blocks if the Device is an ancestor of the Block and the block allows overlap.
                if not (isinstance(tmpList[i-1],pr.Device) and isinstance(tmpList[i],pr.BaseBlock) and \
                        (tmpList[i].path.find(tmpList[i-1].path) == 0 and tmpList[i]._overlapEn)):

                    print("\n\n\n------------------------ Memory Overlap Warning !!! --------------------------------")
                    print("{} at address={:#x} overlaps {} at address={:#x} with size={}".format(
                          tmpList[i].path,tmpList[i].address,
                          tmpList[i-1].path,tmpList[i-1].address,tmpList[i-1].size))
                    print("This warning will be replaced with an exception in the next release!!!!!!!!")

                    #raise pr.NodeError("{} at address={:#x} overlaps {} at address={:#x} with size={}".format(
                    #                   tmpList[i].name,tmpList[i].address,
                    #                   tmpList[i-1].name,tmpList[i-1].address,tmpList[i-1].size))

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

    def waitOnUpdate(self):
        """
        Wait until all update queue items have been processed.
        """
        self._updateQueue.join()

    def hardReset(self):
        """Generate a hard reset on all devices"""
        super().hardReset()
        self._clearLog()

    @ft.lru_cache(maxsize=None)
    def _getPath(self,path):
        """Find a node in the tree that has a particular path string"""
        obj = self

        if '.' in path:
            lst = path.split('.')

            if lst[0] != self.name:
                return None

            for a in lst[1:]:
                obj = obj.node(a)

        elif path != self.name:
            return None

        return obj

    def _rootAttached(self):
        self._parent = self
        self._root   = self
        self._path   = self.name

        for key,value in self._nodes.items():
            value._rootAttached(self,self)

        self._buildBlocks()

        # Some variable initialization can run until the blocks are built
        for v in self.variables.values():
            v._finishInit()

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
        self._sendYamlFrame(self._getYaml(False,modes))

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
                return False

        self._log.info("Done root write")
        return True

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
                return False

        self._log.info("Done root read")
        return True

    def _saveState(self,arg):
        """Save YAML configuration/status to a file. Called from command"""

        # Auto generate name if no arg
        if arg is None or arg == '':
            arg = datetime.datetime.now().strftime("state_%Y%m%d_%H%M%S.yml")

        try:
            with open(arg,'w') as f:
                f.write(self._getYaml(True,modes=['RW','RO','WO']))
        except Exception as e:
            self._log.exception(e)
            return False

        return True

    def _saveConfig(self,arg):
        """Save YAML configuration to a file. Called from command"""

        # Auto generate name if no arg
        if arg is None or arg == '':
            arg = datetime.datetime.now().strftime("config_%Y%m%d_%H%M%S.yml") 

        try:
            with open(arg,'w') as f:
                f.write(self._getYaml(True,modes=['RW','WO']))
        except Exception as e:
            self._log.exception(e)
            return False

        return True

    def _loadConfig(self,arg):
        """Load YAML configuration from a file. Called from command"""
        try:
            with open(arg,'r') as f:
                self._setYaml(f.read(),False,['RW','WO'])
        except Exception as e:
            self._log.exception(e)
            return False

        return True

    def _getYaml(self,readFirst,modes=['RW']):
        """
        Get current values as a yaml dictionary.
        modes is a list of variable modes to include.
        If readFirst=True a full read from hardware is performed.
        """

        if readFirst: self._read()
        try:
            return  dictToYaml({self.name:self._getDict(modes)},default_flow_style=False)
        except Exception as e:
            self._log.exception(e)
            return ""

    def _setYaml(self,yml,writeEach,modes=['RW','WO']):
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

        if self.InitAfterConfig.value():
            self.initialize()

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
                d = odict()

                for p,v in uvars.items():
                    val = v._doUpdate()
                    d[p] = val

                    # Call listener functions,
                    with self._varListenLock:
                        for func in self._varListeners:
                            try:

                                if isinstance(func,Pyro4.core.Proxy) or hasattr(func,'varListener'):
                                    func.varListener(p,val.value,val.valueDisp)
                                else:
                                    func(p,val.value.val,valueDisp)

                            except Pyro4.errors.CommunicationError as msg:
                                if 'Connection refused' in str(msg):
                                    self._log.info("Pyro Disconnect. Removing callback")
                                    self._varListeners.remove(func)
                                else:
                                    self._log.error("Pyro callback failed for {}: {}".format(self.name,msg))
                            except Exception as msg:
                                self._log.error("Update thread error: " + str(msg))

                self._log.debug(F"Done update group. Length={len(uvars)}. Entry={list(uvars.keys())[0]}")

                # Generate yaml stream
                self._sendYamlFrame(dictToYaml(d,default_flow_style=False))

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

    OrderedLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,construct_mapping)

    return yaml.load(stream, OrderedLoader)

def dictToYaml(data, stream=None, Dumper=yaml.Dumper, **kwds):
    """Convert ordered dictionary to yaml"""

    class OrderedDumper(Dumper):
        pass

    def _var_representer(dumper, data):
        if type(data.value) == bool:
            enc = 'tag:yaml.org,2002:bool'
        elif data.enum is not None:
            enc = 'tag:yaml.org,2002:str'
        elif type(data.value) == int:
            enc = 'tag:yaml.org,2002:int'
        elif type(data.value) == float:
            enc = 'tag:yaml.org,2002:float'
        else:
            enc = 'tag:yaml.org,2002:str'

        return dumper.represent_scalar(enc, data.valueDisp)

    def _dict_representer(dumper, data):
        return dumper.represent_mapping(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, data.items())

    OrderedDumper.add_representer(pr.VariableValue, _var_representer)
    OrderedDumper.add_representer(odict, _dict_representer)

    try:
        ret = yaml.dump(data, stream, OrderedDumper, **kwds)
    except Exception as e:
        #print("Error: {} dict {}".format(e,data))
        return None
    return ret

def keyValueUpdate(old, key, value):
    d = old
    parts = key.split('.')
    for part in parts[:-1]:
        if part not in d:
            d[part] = {}
        d = d.get(part)
    d[parts[-1]] = value


def dictUpdate(old, new):
    for k,v in new.items():
        if '.' in k:
            keyValueUpdate(old, k, v)
        elif k in old:
            old[k].update(v)
        else:
            old[k] = v

def yamlUpdate(old, new):
    dictUpdate(old, yamlToDict(new))

def recreate_OrderedDict(name, values):
    return odict(values['items'])

def generateAddressMap(root,fname):
    vlist = root.variableList

    with open(fname,'w') as f:
        f.write("Path\t")
        f.write("Type\t")
        f.write("Full Address\t")
        f.write("Device Offset\t")
        f.write("Mode\t")
        f.write("Bit Offset\t")
        f.write("Bit Size\t")
        f.write("Enum\t")
        f.write("Description\n")

        for v in vlist:
            if isinstance(v, pr.RemoteVariable):
                f.write("{}\t".format(v.path))
                f.write("{}\t".format(type(v)))
                f.write("{:#x}\t".format(v.address))
                f.write("{:#x}\t".format(v.offset))
                f.write("{}\t".format(v.mode))
                f.write("{}\t".format(v.bitOffset))
                f.write("{}\t".format(v.bitSize))
                f.write("{}\t".format(v.enum))
                f.write("{}\n".format(v.description))

