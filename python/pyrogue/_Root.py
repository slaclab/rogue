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
import sys
import os
import glob
import rogue
import rogue.interfaces.memory as rim
import threading
from collections import OrderedDict as odict
import logging
import pyrogue as pr
import pyrogue.interfaces
import functools as ft
import time
import queue
import jsonpickle
import zipfile
import traceback
import gzip
import datetime
from contextlib import contextmanager

SystemLogInit = '[]'

class RootLogHandler(logging.Handler):
    """ Class to listen to log entries and add them to syslog variable"""
    def __init__(self,*, root):
        logging.Handler.__init__(self)
        self._root = root

    def emit(self,record):

        if not self._root.running: return

        with self._root.updateGroup():
           try:
                se = { 'created'     : record.created,
                       'name'        : record.name,
                       'message'     : str(record.msg),
                       'exception'   : None,
                       'traceBack'   : None,
                       'levelName'   : record.levelname,
                       'levelNumber' : record.levelno }

                if record.exc_info is not None:
                    se['exception'] = record.exc_info[0].__name__
                    se['traceBack'] = []

                    for tb in traceback.format_tb(record.exc_info[2]):
                        se['traceBack'].append(tb.rstrip())

                # System log is a running json encoded list
                # Need to remove list terminator ']' and add new entry + list terminator
                with self._root.SystemLog.lock:
                    msg =  self._root.SystemLog.value()[:-1]

                    # Only add a comma and return if list is not empty
                    if len(msg) > 1:
                        msg += ',\n'

                    msg += jsonpickle.encode(se) + ']'
                    self._root.SystemLog.set(msg)

                # Log to database
                if self._root._sqlLog is not None:
                    self._root._sqlLog.logSyslog(se)

           except Exception as e:
               print("-----------Error Logging Exception -------------")
               print(e)
               print(traceback.print_exc(file=sys.stdout))
               print("-----------Original Error-----------------------")
               print(self.format(record))
               print("------------------------------------------------")

class Root(rogue.interfaces.stream.Master,pr.Device):
    """
    Class which serves as the root of a tree of nodes.
    The root is the interface point for tree level access and updates.
    The root is a stream master which generates frames containing tree
    configuration and status values. This allows configuration and status
    to be stored in data files.
    """

    def __enter__(self):
        """Root enter."""

        if self._running:
            print("")
            print("=======================================================================")
            print("Detected 'with Root() as root' call after start() being called in")
            print("Root's __init__ method. It is no longer recommended to call")
            print("start() in a Root class's init() method! Instead start() should")
            print("be re-implemented to startup sub-modules such as epics!")
            print("=======================================================================")
        else:
            self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Root exit."""
        self.stop()

    def __init__(self, *, 
                 name=None, 
                 description='', 
                 expand=True,
                 timeout=1.0,
                 initRead=False,
                 initWrite=False,
                 pollEn=True,
                 serverPort=0,  # 9099 is the default, 0 for auto
                 sqlUrl=None,
                 streamIncGroups=None,
                 streamExcGroups=['NoStream'],
                 sqlIncGroups=None,
                 sqlExcGroups=['NoSql']):
        """Init the node with passed attributes"""
        rogue.interfaces.stream.Master.__init__(self)

        # Store startup parameters
        self._timeout         = timeout
        self._initRead        = initRead
        self._initWrite       = initWrite
        self._pollEn          = pollEn
        self._serverPort      = serverPort
        self._sqlUrl          = sqlUrl
        self._streamIncGroups = streamIncGroups
        self._streamExcGroups = streamExcGroups
        self._sqlIncGroups    = sqlIncGroups
        self._sqlExcGroups    = sqlExcGroups
        self._doHeartbeat     = True # Backdoor flag

        # Create log listener to add to SystemLog variable
        formatter = logging.Formatter("%(msg)s")
        handler = RootLogHandler(root=self)
        handler.setLevel(logging.ERROR)
        handler.setFormatter(formatter)
        self._logger = logging.getLogger('pyrogue')
        self._logger.addHandler(handler)

        # Running status
        self._running = False

        # Polling worker
        self._pollQueue = self._pollQueue = pr.PollQueue(root=self)

        # Zeromq server
        self._zmqServer  = None

        # List of variable listeners
        self._varListeners  = []
        self._varListenLock = threading.Lock()

        # Variable update worker
        self._updateQueue = queue.Queue()
        self._updateThread = None
        self._updateLock   = threading.Lock()
        self._updateCount  = {}
        self._updateList   = {}

        # SQL URL
        self._sqlLog = None

        # Init 
        pr.Device.__init__(self, name=name, description=description, expand=expand)

        # Variables
        self.add(pr.LocalVariable(name='RogueVersion', value=rogue.Version.current(), mode='RO', hidden=False,
                 description='Rogue Version String'))

        self.add(pr.LocalVariable(name='RogueDirectory', value=os.path.dirname(pr.__file__), mode='RO', hidden=False,
                 description='Rogue Library Directory'))

        self.add(pr.LocalVariable(name='SystemLog', value=SystemLogInit, mode='RO', hidden=True, groups=['NoStream','NoSql','NoState'],
            description='String containing newline separated system logic entries'))

        self.add(pr.LocalVariable(name='ForceWrite', value=False, mode='RW', hidden=True,
            description='Configuration Flag To Always Write Non Stale Blocks For WriteAll, LoadConfig and setYaml'))

        self.add(pr.LocalVariable(name='InitAfterConfig', value=False, mode='RW', hidden=True,
            description='Configuration Flag To Execute Initialize after LoadConfig or setYaml'))

        self.add(pr.LocalVariable(name='Time', value=0.0, mode='RO', hidden=True,
                 description='Current Time In Seconds Since EPOCH UTC'))

        self.add(pr.LinkVariable(name='LocalTime', value='', mode='RO', groups=['NoStream','NoSql','NoState'],
                 linkedGet=lambda: time.strftime("%Y-%m-%d %H:%M:%S %Z", time.localtime(self.Time.value())),
                 dependencies=[self.Time], description='Local Time'))

        self.add(pr.LocalVariable(name='PollEn', value=False, mode='RW',groups=['NoStream','NoSql','NoState'],
                                  localSet=lambda value: self._pollQueue.pause(not value),
                                  localGet=lambda: not self._pollQueue.paused()))

        # Commands
        self.add(pr.LocalCommand(name='WriteAll', function=self._write, hidden=True,
                                 description='Write all values to the hardware'))

        self.add(pr.LocalCommand(name="ReadAll", function=self._read, hidden=True,
                                 description='Read all values from the hardware'))

        self.add(pr.LocalCommand(name='SaveState', value='', 
                                 function=lambda arg: self.saveYaml(name=arg,
                                                                    readFirst=True,
                                                                    modes=['RW','RO','WO'],
                                                                    incGroups=None,
                                                                    excGroups='NoState',
                                                                    autoPrefix='state',
                                                                    autoCompress=True),
                                 hidden=True,
                                 description='Save state to passed filename in YAML format'))

        self.add(pr.LocalCommand(name='SaveConfig', value='', 
                                 function=lambda arg: self.saveYaml(name=arg,
                                                                    readFirst=True,
                                                                    modes=['RW','WO'],
                                                                    incGroups=None,
                                                                    excGroups='NoConfig',
                                                                    autoPrefix='config',
                                                                    autoCompress=False),
                                 hidden=True,
                                 description='Save configuration to passed filename in YAML format'))

        self.add(pr.LocalCommand(name='LoadConfig', value='', 
                                 function=lambda arg: self.loadYaml(name=arg,
                                                                    writeEach=False,
                                                                    modes=['RW','WO'],
                                                                    incGroups=None,
                                                                    excGroups='NoConfig'),
                                 hidden=True,
                                 description='Read configuration from passed filename in YAML format'))

        self.add(pr.LocalCommand(name='Initialize', function=self.initialize, hidden=True,
                                 description='Generate a soft reset to each device in the tree'))

        self.add(pr.LocalCommand(name='HardReset', function=self.hardReset, hidden=True,
                                 description='Generate a hard reset to each device in the tree'))

        self.add(pr.LocalCommand(name='CountReset', function=self.countReset, hidden=True,
                                 description='Generate a count reset to each device in the tree'))

        self.add(pr.LocalCommand(name='ClearLog', function=self._clearLog, hidden=True,
                                 description='Clear the message log contained in the SystemLog variable'))

        self.add(pr.LocalCommand(name='SetYamlConfig', value='', 
                                 function=lambda arg: self.setYaml(yml=arg,
                                                                   writeEach=False,
                                                                   modes=['RW','WO'],
                                                                   incGroups=None,
                                                                   excGroups='NoConfig'), 
                                 hidden=True,
                                 description='Set configuration from passed YAML string'))

        self.add(pr.LocalCommand(name='GetYamlConfig', value=True, retValue='',
                                 function=lambda arg: self.getYaml(readFirst=arg,
                                                                   modes=['RW','WO'],
                                                                   incGroups=None,
                                                                   excGroups='NoConfig'), 
                                 hidden=True,
                                 description='Get current configuration as YAML string. Pass read first arg.'))

        self.add(pr.LocalCommand(name='GetYamlState', value=True, retValue='',
                                 function=lambda arg: self.getYaml(readFirst=arg,
                                                                   modes=['RW','RO','WO'],
                                                                   incGroups=None,
                                                                   excGroups='NoState'), 
                                 hidden=True,
                                 description='Get current state as YAML string. Pass read first arg.'))

        self.add(pr.LocalCommand(name='Restart', function=self._restart,
                                 description='Restart and reload the server application'))

        self.add(pr.LocalCommand(name='Exit', function=self._exit,
                                 description='Exit the server application'))

    def start(self, **kwargs):
        """Setup the tree. Start the polling thread."""

        if self._running:
            raise pr.NodeError("Root is already started! Can't restart!")

        # Deprecation Warning
        if len(kwargs) != 0:
            print("")
            print("==========================================================")
            print(" Passing startup args in start() method is now deprecated.")
            print(" Startup args should now be passed to the root creator.   ")
            print("    Example: pyrogue.Root(timeout=1.0, pollEn=True)       ")
            print("==========================================================")

            # Override startup parameters if passed in start()
            if 'streamIncGroups' in kwargs: self._streamIncGroups = kwargs['streamIncGroups']
            if 'streamExcGroups' in kwargs: self._streamExcGroups = kwargs['streamExcGroups']
            if 'sqlIncGroups'    in kwargs: self._sqlIncGroups    = kwargs['sqlIncGroups']
            if 'sqlExcGroups'    in kwargs: self._sqlExcGroups    = kwargs['sqlExcGroups']
            if 'timeout'         in kwargs: self._timeout         = kwargs['timeout']
            if 'initRead'        in kwargs: self._initRead        = kwargs['initRead']
            if 'initWrite'       in kwargs: self._initWrite       = kwargs['initWrite']
            if 'pollEn'          in kwargs: self._pollEn          = kwargs['pollEn']
            if 'serverPort'      in kwargs: self._serverPort      = kwargs['serverPort']
            if 'sqlUrl'          in kwargs: self._sqlUrl          = kwargs['sqlUrl']

        # Call special root level rootAttached
        self._rootAttached()

        # Get full list of Devices and Blocks
        tmpList = []
        for d in self.deviceList:
            tmpList.append(d)
            for b in d._blocks:
                if isinstance(b, rim.Block):
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
                # Check for instances when device comes before block and when block comes before device 
                if (not (isinstance(tmpList[i-1],pr.Device) and isinstance(tmpList[i],rim.Block) and \
                         (tmpList[i].path.find(tmpList[i-1].path) == 0 and tmpList[i].overlapEn))) and \
                   (not (isinstance(tmpList[i],pr.Device) and isinstance(tmpList[i-1],rim.Block) and \
                        (tmpList[i-1].path.find(tmpList[i].path) == 0 and tmpList[i-1].overlapEn))):

                    raise pr.NodeError("{} at address={:#x} overlaps {} at address={:#x} with size={}".format(
                                       tmpList[i].path,tmpList[i].address,
                                       tmpList[i-1].path,tmpList[i-1].address,tmpList[i-1].size))

        # Set timeout if not default
        if self._timeout != 1.0:
            for key,value in self._nodes.items():
                value._setTimeout(self._timeout)

        # Start ZMQ server if enabled
        if self._serverPort is not None:
            self._zmqServer  = pr.interfaces.ZmqServer(root=self,addr="*",port=self._serverPort)
            self._serverPort = self._zmqServer.port()
            print("start: Started zmqServer on port %d" % self._serverPort)

        # Start sql interface
        if self._sqlUrl is not None:
            self._sqlLog = pr.interfaces.SqlLogger(self._sqlUrl)

        # Start update thread
        self._running = True
        self._updateThread = threading.Thread(target=self._updateWorker)
        self._updateThread.start()

        # Read current state
        if self._initRead:
            self._read()

        # Commit default values
        # Read did not override defaults because set values are cached
        if self._initWrite:
            self._write()

        # Start poller if enabled
        self._pollQueue._start()
        self.PollEn.set(self._pollEn)

        self._heartbeat()

    def stop(self):
        """Stop the polling thread. Must be called for clean exit."""
        self._running = False
        self._updateQueue.put(None)
        self._updateThread.join()

        if self._pollQueue:
            self._pollQueue.stop()

        if self._zmqServer is not None:
            self._zmqServer.close()

        if self._sqlLog is not None:
            self._sqlLog.stop()

    @property
    def serverPort(self):
        return self._serverPort

    @pr.expose
    @property
    def running(self):
        return self._running

    def addVarListener(self,func):
        """
        Add a variable update listener function.
        The variable and value structure will be passed as args: func(path,varValue)
        """
        with self._varListenLock:
            self._varListeners.append(func)

    @pr.expose
    def get(self,path):
        obj = self.getNode(path)
        return obj.get()

    @pr.expose
    def getDisp(self,path):
        obj = self.getNode(path)
        return obj.getDisp()

    @pr.expose
    def value(self,path):
        obj = self.getNode(path)
        return obj.value()

    @pr.expose
    def valueDisp(self,path):
        obj = self.getNode(path)
        return obj.valueDisp()

    @pr.expose
    def set(self,path,value):
        obj = self.getNode(path)
        return obj.set(value)

    @pr.expose
    def setDisp(self,path,value):
        obj = self.getNode(path)
        return obj.setDisp(value)

    @pr.expose
    def exec(self,path,arg):
        obj = self.getNode(path)
        return obj(arg)

    @contextmanager
    def updateGroup(self):
        tid = threading.get_ident()

        # At with call
        with self._updateLock:
            if not tid in self._updateCount:
                self._updateList[tid] = {}
                self._updateCount[tid] = 0

            self._updateCount[tid] += 1

        try:
            yield
        finally:

            # After with is done
            with self._updateLock:
                if self._updateCount[tid] == 1:
                    self._updateCount[tid] = 0
                    self._updateQueue.put(self._updateList[tid])
                    self._updateList[tid] = {}
                else:
                    self._updateCount[tid] -= 1

    @contextmanager
    def pollBlock(self):

        # At with call
        self._pollQueue._blockIncrement()

        # Return to block within with call
        try:
            yield
        finally:

            # After with is done
            self._pollQueue._blockDecrement()

    @pr.expose
    def waitOnUpdate(self):
        """
        Wait until all update queue items have been processed.
        """
        self._updateQueue.join()

    def hardReset(self):
        """Generate a hard reset on all devices"""
        super().hardReset()
        self._clearLog()

    def __reduce__(self):
        return pr.Node.__reduce__(self)

    @ft.lru_cache(maxsize=None)
    def getNode(self,path):
        obj = self

        if '.' in path:
            lst = path.split('.')

            if lst[0] != self.name and lst[0] != 'root':
                return None

            for a in lst[1:]:
                if not hasattr(obj,'node'):
                    return None
                obj = obj.node(a)

        elif path != self.name and path != 'root':
            return None

        return obj

    @pr.expose
    def saveAddressMap(self,fname):
        try:
            with open(fname,'w') as f:
                f.write("Path\t")
                f.write("TypeStr\t")
                f.write("MemBaseId\t")
                f.write("Full Address\t")
                f.write("Device Offset\t")
                f.write("Mode\t")
                f.write("Bit Offset\t")
                f.write("Bit Size\t")
                f.write("Enum\t")
                f.write("Description\n")

                for v in self.variableList:
                    if v.isinstance(pr.RemoteVariable):
                        f.write("{}\t".format(v.path))
                        f.write("{}\t".format(v.typeStr))
                        f.write("{}\t".format(v._block.memBaseId))
                        f.write("{:#x}\t".format(v.address))
                        f.write("{:#x}\t".format(v.offset))
                        f.write("{}\t".format(v.mode))
                        f.write("{}\t".format(v.bitOffset))
                        f.write("{}\t".format(v.bitSize))
                        f.write("{}\t".format(v.enum))
                        f.write("{}\n".format(v.description))

        except Exception as e:
            pr.logException(self._log,e)

    @pr.expose
    def saveVariableList(self,fname,polledOnly=False,incGroups=None):
        try:
            with open(fname,'w') as f:
                f.write("Path\t")
                f.write("TypeStr\t")
                f.write("Mode\t")
                f.write("Enum\t")
                f.write("PollInterval\t")
                f.write("Groups\t")
                f.write("Description\n")

                for v in self.variableList:
                    if ((not polledOnly) or (v.pollInterval > 0)) and v.filterByGroup(incGroups=incGroups,excGroups=None):
                        f.write("{}\t".format(v.path))
                        f.write("{}\t".format(v.typeStr))
                        f.write("{}\t".format(v.mode))
                        f.write("{}\t".format(v.enum))
                        f.write("{}\t".format(v.pollInterval))
                        f.write("{}\t".format(v.groups))
                        f.write("{}\n".format(v.description))

        except Exception as e:
            pr.logException(self._log,e)

    def _heartbeat(self):
        if self._running and self._doHeartbeat:
            with self.updateGroup():
                threading.Timer(1.0,self._heartbeat).start()
                self.Time.set(time.time())

    def _exit(self):
        self.stop()
        exit()

    def _restart(self):
        self.stop()
        py = sys.executable
        os.execl(py, py, *sys.argv)

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

    def streamYaml(self,modes=['RW','RO','WO'],incGroups=None,excGroups=None):
        """
        Generate a frame containing all variables values in yaml format.
        A hardware read is not generated before the frame is generated.
        incGroups is a list of groups that the variable must be a member 
        of in order to be included in the stream. excGroups is a list of 
        groups that the variable must not be a member of to include. 
        excGroups takes precedence over incGroups. If excGroups or 
        incGroups are None, the default set of stream include and 
        exclude groups will be used as specified when the Root class was created.
        By default all variables are included, except for members of the NoStream group.
        """

        # Don't send if there are not any Slaves connected
        if self._slaveCount == 0: return

        # Inherit include and exclude groups from global if not passed
        if incGroups is None: incGroups = self._streamIncGroups
        if excGroups is None: excGroups = self._streamExcGroups

        self._sendYamlFrame(self.getYaml(readFirst=False,
                                          modes=modes,
                                          incGroups=incGroups,
                                          excGroups=excGroups))

    def _write(self):
        """Write all blocks"""
        self._log.info("Start root write")
        with self.pollBlock(), self.updateGroup():
            try:
                self.writeBlocks(force=self.ForceWrite.value(), recurse=True)
                self._log.info("Verify root read")
                self.verifyBlocks(recurse=True)
                self._log.info("Check root read")
                self.checkBlocks(recurse=True)
            except Exception as e:
                pr.logException(self._log,e)
                return False

        self._log.info("Done root write")
        return True

    def _read(self):
        """Read all blocks"""
        self._log.info("Start root read")
        with self.pollBlock(), self.updateGroup():
            try:
                self.readBlocks(recurse=True)
                self._log.info("Check root read")
                self.checkBlocks(recurse=True)
            except Exception as e:
                pr.logException(self._log,e)
                return False

        self._log.info("Done root read")
        return True

    def saveYaml(self,name,readFirst,modes,incGroups,excGroups,autoPrefix,autoCompress):
        """Save YAML configuration/status to a file. Called from command"""

        # Auto generate name if no arg
        if name is None or name == '':
            name = datetime.datetime.now().strftime(autoPrefix + "_%Y%m%d_%H%M%S.yml")

            if autoCompress:
                name += '.gz'
        try:
            yml = self.getYaml(readFirst=readFirst,modes=modes,incGroups=incGroups,excGroups=excGroups)

            if name.split('.')[-1] == 'gz':
                with gzip.open(name,'w') as f: f.write(yml.encode('utf-8'))

            else:
                with open(name,'w') as f: f.write(yml)

        except Exception as e:
            pr.logException(self._log,e)
            return False

        return True


    def loadYaml(self,name,writeEach,modes,incGroups,excGroups):
        """Load YAML configuration from a file. Called from command"""

        # Pass arg is a python list
        if isinstance(name,list):
            rawlst = name

        # Passed arg is a comma separated list of files
        elif ',' in name:
            rawlst = name.split(',')

        # Not a list
        else:
            rawlst = [name]

        # Init final list
        lst = []

        # Iterate through raw list and look for directories
        for rl in rawlst:

            # Name ends with .yml or .yaml
            if rl[-4:] == '.yml' or rl[-5:] == '.yaml': 
                lst.append(rl)

            # Entry is a zip file directory
            elif '.zip' in rl:
                base = rl.split('.zip')[0] + '.zip'
                sub = rl.split('.zip')[1][1:]

                # Open zipfile
                with zipfile.ZipFile(base, 'r') as myzip:

                    # Check if passed name is a directory, otherwise generate an error
                    if not any(x.startswith("%s/" % sub.rstrip("/")) for x in myzip.namelist()):
                        self._log.error("loadYaml: Invalid load file: {}, must be a directory or end in .yml or .yaml".format(rl))

                    else:

                        # Iterate through directory contents
                        for zfn in myzip.namelist():

                            # Filter by base directory
                            if zfn.find(sub) == 0:
                                spt = zfn.split('%s/' % sub.rstrip('/'))[1]

                                # Entry ends in .yml or *.yml and is in current directory 
                                if not '/' in spt and (spt[-4:] == '.yml' or spt[-5:] == '.yaml'): 
                                    lst.append(base + '/' + zfn)

            # Entry is a directory
            elif os.path.isdir(rl):
                dlst = glob.glob('{}/*.yml'.format(rl))
                dlst.extend(glob.glob('{}/*.yaml'.format(rl)))
                lst.extend(sorted(dlst))

            # Not a zipfile, not a directory and does not end in .yml
            else: 
                self._log.error("loadYaml: Invalid load file: {}, must be a directory or end in .yml or .yaml".format(rl))

        # Read each file
        try:
            with self.pollBlock(), self.updateGroup():
                for fn in lst:
                    d = pr.yamlToData(fName=fn)
                    self._setDictRoot(d=d,writeEach=writeEach,modes=modes,incGroups=incGroups,excGroups=excGroups)

                if not writeEach: self._write()

            if self.InitAfterConfig.value():
                self.initialize()

        except Exception as e:
            pr.logException(self._log,e)
            return False

        return True

    def getYaml(self,readFirst,modes,incGroups,excGroups):
        """
        Get current values as yaml data.
        modes is a list of variable modes to include.
        If readFirst=True a full read from hardware is performed.
        """

        if readFirst: self._read()
        try:
            return pr.dataToYaml({self.name:self._getDict(modes=modes,incGroups=incGroups,excGroups=excGroups)})
        except Exception as e:
            pr.logException(self._log,e)
            return ""


    def setYaml(self,yml,writeEach,modes,incGroups,excGroups):
        """
        Set variable values from a yaml file
        modes is a list of variable modes to act on.
        writeEach is set to true if accessing a single variable at a time.
        Writes will be performed as each variable is updated. If set to 
        false a bulk write will be performed after all of the variable updates
        are completed. Bulk writes provide better performance when updating a large
        quantity of variables.
        """
        d = pr.yamlToData(yml)

        with self.pollBlock(), self.updateGroup():
            self._setDictRoot(d=d,writeEach=writeEach,modes=modes,incGroups=incGroups,excGroups=excGroups)

            if not writeEach: self._write()

        if self.InitAfterConfig.value():
            self.initialize()


    def _setDictRoot(self,d,writeEach,modes,incGroups,excGroups):
        for key, value in d.items():

            # Attempt to get node
            node = self.getNode(key)

            # Call setDict on node
            if node is not None:
                node._setDict(d=value,writeEach=writeEach,modes=modes,incGroups=incGroups,excGroups=excGroups)
            else:
                self._log.error("Entry {} not found".format(key))


    def _clearLog(self):
        """Clear the system log"""
        self.SystemLog.set(SystemLogInit)

    def _queueUpdates(self,var):
        tid = threading.get_ident()

        with self._updateLock:
            if not tid in self._updateCount:
                self._updateList[tid] = {}
                self._updateCount[tid] = 0

            self._updateList[tid][var.path] = var

            if self._updateCount[tid] == 0:
                self._updateQueue.put(self._updateList[tid])
                self._updateList[tid] = {}

    # Worker thread
    def _updateWorker(self):
        self._log.info("Starting update thread")

        while True:
            uvars = self._updateQueue.get()

            # Done
            if uvars is None:
                self._log.info("Stopping update thread")
                return

            # Process list
            elif len(uvars) > 0:
                self._log.debug(F"Process update group. Length={len(uvars)}. Entry={list(uvars.keys())[0]}")
                strm = odict()
                zmq  = odict()

                for p,v in uvars.items():
                    try:
                        val = v._doUpdate()

                        # Add to stream
                        if self._slaveCount() != 0 and v.filterByGroup(self._streamIncGroups, self._streamExcGroups):
                            strm[p] = val

                        # Add to zmq publish
                        if not v.inGroup('NoServe'):
                            zmq[p] = val

                        # Call listener functions,
                        with self._varListenLock:
                            for func in self._varListeners:
                                func(p,val)

                        # Log to database
                        if self._sqlLog is not None and v.filterByGroup(self._sqlIncGroups, self._sqlExcGroups):
                            self._sqlLog.logVariable(p, val)

                    except Exception as e:
                        if v == self.SystemLog:
                            print("------- Error Executing Syslog Listeners -------")
                            print("Error: {}".format(e))
                            print("------------------------------------------------")
                        else:
                            pr.logException(self._log,e)
                        
                self._log.debug(F"Done update group. Length={len(uvars)}. Entry={list(uvars.keys())[0]}")


                # Generate yaml stream
                try:
                    if len(strm) > 0:
                        self._sendYamlFrame(pr.dataToYaml(strm))

                except Exception as e:
                    pr.logException(self._log,e)

                # Send over zmq link
                if self._zmqServer is not None:
                    self._zmqServer._publish(jsonpickle.encode(zmq))

            # Set done
            self._updateQueue.task_done()

