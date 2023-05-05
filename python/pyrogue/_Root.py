#-----------------------------------------------------------------------------
# Title      : PyRogue base module - Root Class
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
import logging
import pyrogue as pr
import pyrogue.interfaces.stream
import functools as ft
import time
import queue
import json
import zipfile
import traceback
import datetime
from contextlib import contextmanager

SystemLogInit = '[]'

class UpdateTracker(object):
    """
    """
    def __init__(self,q):
        self._count = 0
        self._list = {}
        self._period = 0
        self._last = time.time()
        self._q = q

    def increment(self, period):
        """

        Parameters
        ----------
        period : int
            default value period = 0

        Returns
        -------
        """

        if self._count == 0 or self._period < period:
            self._period = period
        self._count +=1

    def decrement(self):
        if self._count != 0:
            self._count -= 1

        self._check()

    def _check(self):
        if len(self._list) != 0 and (self._count == 0 or (self._period != 0 and (time.time() - self._last) > self._period)):
            #print(f"Utpdate fired {time.time()}")
            self._last = time.time()
            self._q.put(self._list)
            self._list = {}

    def update(self,var):
        """


        Parameters
        ----------
        var :


        Returns
        -------

        """
        self._list[var.path] = var
        self._check()

class RootLogHandler(logging.Handler):
    """Class to listen to log entries and add them to syslog variable"""
    def __init__(self,*, root):
        logging.Handler.__init__(self)
        self._root = root

    def emit(self,record):
        """


        Parameters
        ----------
        record :


        Returns
        -------

        """

        if not self._root.running:
            return

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

                self._root.SystemLogLast.set(json.dumps(se))

                # System log is a running json encoded list
                with self._root.SystemLog.lock:
                    lst = json.loads(self._root.SystemLog.value())

                    # Limit system log size
                    lst = lst[-1 * (self._root._maxLog-1):]

                    lst.append(se)
                    self._root.SystemLog.set(json.dumps(lst))


            except Exception as e:
                print("-----------Error Logging Exception -------------")
                print(e)
                print(traceback.print_exc(file=sys.stdout))
                print("-----------Original Error-----------------------")
                print(self.format(record))
                print("------------------------------------------------")

class Root(pr.Device):
    """
    Class which serves as the root of a tree of nodes.
    The root is the interface point for tree level access and updates.
    The root is a stream master which generates frames containing tree
    configuration and status values. This allows configuration and status
    to be stored in data files.

    Attributes
    ----------
    rogue.interfaces.stream.Master :


    pr.Device :

    Returns
    -------

    """

    def __enter__(self):
        """Root enter."""
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
                 maxLog=1000,
                 # Deprecated
                 serverPort=None,  # 9099 is the default, 0 for auto
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
        self._maxLog          = maxLog
        self._doHeartbeat     = True # Backdoor flag
        self._testFunc        = None

        # Deprecated
        self._serverPort      = serverPort
        self._sqlUrl          = sqlUrl
        self._sqlIncGroups    = sqlIncGroups
        self._sqlExcGroups    = sqlExcGroups
        self._streamIncGroups = streamIncGroups
        self._streamExcGroups = streamExcGroups
        self._streamMaster    = None

        # Create log listener to add to SystemLog variable
        formatter = logging.Formatter("%(msg)s")
        handler = RootLogHandler(root=self)
        handler.setFormatter(formatter)
        self._logger = logging.getLogger('pyrogue')
        self._logger.addHandler(handler)

        # Running status
        self._running = False

        # Polling worker
        self._pollQueue = self._pollQueue = pr.PollQueue(root=self)

        # List of variable listeners
        self._varListeners  = []
        self._varListenLock = threading.Lock()

        # Variable update worker
        self._updateQueue = queue.Queue()
        self._updateThread = None
        self._updateLock   = threading.Lock()
        self._updateTrack  = {}

        # Init
        pr.Device.__init__(self, name=name, description=description, expand=expand)

        # Variables
        self.add(pr.LocalVariable(name='RogueVersion', value=rogue.Version.current(), mode='RO', hidden=False,
                 description='Rogue Version String'))

        self.add(pr.LocalVariable(name='RogueDirectory', value=os.path.dirname(pr.__file__), mode='RO', hidden=False,
                 description='Rogue Library Directory'))

        self.add(pr.LocalVariable(name='SystemLog', value=SystemLogInit, mode='RO', hidden=True, groups=['NoStream','NoSql','NoState'],
            description='String containing newline separated system logic entries'))

        self.add(pr.LocalVariable(name='SystemLogLast', value='', mode='RO', hidden=True, groups=['NoStream','NoState'],
            description='String containing last system log entry'))

        self.add(pr.LocalVariable(name='ForceWrite', value=False, mode='RW', hidden=True,
            description='Configuration Flag To Always Write Non Stale Blocks For WriteAll, LoadConfig and setYaml'))

        self.add(pr.LocalVariable(name='InitAfterConfig', value=False, mode='RW', hidden=True,
            description='Configuration Flag To Execute Initialize after LoadConfig or setYaml'))

        self.add(pr.LocalVariable(name='Time', value=0.0, mode='RO', hidden=True,
                                  description='Current Time In Seconds Since EPOCH UTC', groups=['NoSql']))

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
                                 description='Save state to file. Data is saved in YAML format. Passed arg is full path to file to sore data to.'))

        self.add(pr.LocalCommand(name='SaveConfig', value='',
                                 function=lambda arg: self.saveYaml(name=arg,
                                                                    readFirst=True,
                                                                    modes=['RW','WO'],
                                                                    incGroups=None,
                                                                    excGroups='NoConfig',
                                                                    autoPrefix='config',
                                                                    autoCompress=False),
                                 hidden=True,
                                 description='Save configuration to file. Data is saved in YAML format. Passed arg is full path to file to sore data to.'))

        self.add(pr.LocalCommand(name='LoadConfig', value='',
                                 function=lambda arg: self.loadYaml(name=arg,
                                                                    writeEach=False,
                                                                    modes=['RW','WO'],
                                                                    incGroups=None,
                                                                    excGroups='NoConfig'),
                                 hidden=True,
                                 description='Read configuration from file. Data is read in YAML format. Passed arg is full path to file to read data from.'))

        self.add(pr.LocalCommand(name='RemoteVariableDump', value='',
                                 function=lambda arg: self.remoteVariableDump(name=arg,
                                                                              modes=['RW','WO','RO'],
                                                                              readFirst=True),
                                 hidden=True,
                                 description='Save a dump of the remote variable state'))

        self.add(pr.LocalCommand(name='RemoteConfigDump', value='',
                                 function=lambda arg: self.remoteVariableDump(name=arg,
                                                                              modes=['RW','WO'],
                                                                              readFirst=True),
                                 hidden=True,
                                 description='Save a dump of the remote variable state'))


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
                                 description='Set configuration from YAML string. Passed arg is configuration string in YAML format.'))

        self.add(pr.LocalCommand(name='GetYamlConfig', value=True, retValue='',
                                 function=lambda arg: self.getYaml(readFirst=arg,
                                                                   modes=['RW','WO'],
                                                                   incGroups=None,
                                                                   excGroups='NoConfig',
                                                                   recurse=True),
                                 hidden=True,
                                 description='Get configuration in YAML string. '
                                             'Passed arg is a boolean indicating if a full system read should be generated. '
                                             'Return data is configuration as a YAML string.'))

        self.add(pr.LocalCommand(name='GetYamlState', value=True, retValue='',
                                 function=lambda arg: self.getYaml(readFirst=arg,
                                                                   modes=['RW','RO','WO'],
                                                                   incGroups=None,
                                                                   excGroups='NoState',
                                                                   recurse=True),
                                 hidden=True,
                                 description='Get current state as YAML string. Pass read first arg.'))

        #self.add(pr.LocalCommand(name='Restart', function=self._restart,
        #                         description='Restart and reload the server application'))

        #self.add(pr.LocalCommand(name='Exit', function=self._exit,
        #                         description='Exit the server application'))


    def start(self):
        """Setup the tree. Start the polling thread."""

        if self._running:
            raise pr.NodeError("Root is already started! Can't restart!")

        # Call special root level rootAttached
        self._rootAttached()

        # Finish Initialization
        self._finishInit()

        # Get full list of Devices and Blocks
        tmpList = []
        for d in self.deviceList:
            tmpList.append(d)
            for b in d._blocks:
                if isinstance(b, rim.Block):
                    tmpList.append(b)

        # Sort the list by address/size
        tmpList.sort(key=lambda x: (x._reqSlaveId(), x.address, x.size))

        # Look for overlaps
        for i in range(1,len(tmpList)):

            self._log.debug("Comparing {} with address={:#x} to {} with address={:#x} and size={}".format(
                            tmpList[i].path,  tmpList[i].address,
                            tmpList[i-1].path,tmpList[i-1].address, tmpList[i-1].size))

            # Detect overlaps
            if (tmpList[i].size != 0) and (tmpList[i]._reqSlaveId() == tmpList[i-1]._reqSlaveId()) and \
               (tmpList[i].address < (tmpList[i-1].address + tmpList[i-1].size)):

                raise pr.NodeError("{} at address={:#x} overlaps {} at address={:#x} with size={}".format(
                                   tmpList[i].path,tmpList[i].address,
                                   tmpList[i-1].path,tmpList[i-1].address,tmpList[i-1].size))

        # Set timeout if not default
        if self._timeout != 1.0:
            for key,value in self._nodes.items():
                value._setTimeout(self._timeout)

        # Start ZMQ server if enabled
        if self._serverPort is not None:
            print("========== Deprecation Warning ===============================================")
            print(" Setting up zmq server through the Root class creator is                      ")
            print(" no longer supported. Instead create the ZmqServer seperately                 ")
            print(" add add it as an interface:                                                  ")
            print("                                                                              ")
            print("    with Root() as r:                                                         ")
            print("       r.addInterface(pyrogue.interfaces.ZmqServer(root=r, addr='*', port=0)) ")
            print("==============================================================================")
            self.addProtocol(pr.interfaces.ZmqServer(root=self, addr="*", port=self._serverPort))

        # Start sql interface
        if self._sqlUrl is not None:
            print("========== Deprecation Warning =========================================")
            print(" Setting up sql logger through the Root class creator is                ")
            print(" no longer supported. Instead create the SqlLogger seperately           ")
            print(" add add it as an interface:                                            ")
            print("                                                                        ")
            print("    with Root() as r:                                                   ")
            print("       r.addInterface(pyrogue.interfaces.SqlLogger(root=r, url=sqlUrl)) ")
            print("========================================================================")
            self.addProtocol(pr.interfaces.SqlLogger(root=self, url=self._sqlUrl, incGroups=self._sqlIncGroups, excGroups=self._sqlExcGroups))

        # Start update thread
        self._running = True
        self._updateThread = threading.Thread(target=self._updateWorker)
        self._updateThread.start()

        # Start heartbeat
        if self._doHeartbeat:
            self._hbeatThread = threading.Thread(target=self._hbeatWorker)
            self._hbeatThread.start()

        # Start interfaces and protocols
        pr.Device._start(self)

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


    def stop(self):
        """Stop the polling thread. Must be called for clean exit."""

        self._running = False
        self._updateQueue.put(None)
        self._updateThread.join()

        if self._pollQueue:
            self._pollQueue._stop()

        pr.Device._stop(self)

    @pr.expose
    @property
    def running(self):
        """
        """
        return self._running

    def addVarListener(self,func,*,done=None,incGroups=None,excGroups=None):
        """
        Add a variable update listener function.
        The variable and value structure will be passed as args: func(path,varValue)

        Parameters
        ----------
        func :
        done :
        incGroups :
        excGroups :

        Returns
        -------
        """

        with self._varListenLock:
            self._varListeners.append((func,done,incGroups,excGroups))

    def _addVarListenerCpp(self, func, done):
        self.addVarListener(lambda path, varValue: func(path, varValue.valueDisp), done=done)

    @contextmanager
    def updateGroup(self, period=0):
        """


        Parameters
        ----------
        period :
             (Default value = 0)

        Returns
        -------

        """
        tid = threading.get_ident()

        # At with call
        with self._updateLock:
            if tid not in self._updateTrack:
                self._updateTrack[tid] = UpdateTracker(self._updateQueue)

            self._updateTrack[tid].increment(period)

        try:
            yield
        finally:

            # After with is done
            with self._updateLock:
                self._updateTrack[tid].decrement()

    @contextmanager
    def pollBlock(self):
        """
        """

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
        """Wait until all update queue items have been processed."""
        self._updateQueue.join()

    def hardReset(self):
        """Generate a hard reset on all devices"""
        super().hardReset()
        self._clearLog()

    def __reduce__(self):
        return pr.Node.__reduce__(self)

    @ft.lru_cache(maxsize=None)
    def getNode(self,path):
        """


        Parameters
        ----------
        path :


        Returns
        -------

        """
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
    def saveAddressMap(self,fname,headerEn=False):
        """


        Parameters
        ----------
        fname :

        headerEn :
             (Default value = False)

        Returns
        -------

        """

        # First form header
        # Changing these names here requires changing the createVariable() method in LibraryBase.cpp
        header  = "Path\t"
        header += "TypeStr\t"
        header += "Address\t"
        header += "Offset\t"
        header += "Mode\t"
        header += "BitOffset\t"
        header += "BitSize\t"
        header += "Minimum\t"
        header += "Maximum\t"
        header += "Enum\t"
        header += "OverlapEn\t"
        header += "Verify\t"
        header += "ModelId\t"
        header += "ByteReverse\t"
        header += "BitReverse\t"
        header += "BinPoint\t"
        header += "BulkEn\t"
        header += "UpdateNotify\t"
        header += "MemBaseName\t"
        header += "BlockName\t"
        header += "BlockSize\t"
        header += "NumValues\t"
        header += "ValueBits\t"
        header += "ValueStride\t"
        header += "RetryCount\t"
        header += "Description"

        lines = []
        for v in self.variableList:
            if v.isinstance(pr.RemoteVariable):
                data  = "{}\t".format(v.path)
                data += "{}\t".format(v.typeStr)
                data += "{:#x}\t".format(v.address)
                data += "{:#x}\t".format(v.offset)
                data += "{}\t".format(v.mode)
                data += "{}\t".format(v.bitOffset)
                data += "{}\t".format(v.bitSize)
                data += "{}\t".format(v.minimum)
                data += "{}\t".format(v.maximum)
                data += "{}\t".format(v.enum)
                data += "{}\t".format(v.overlapEn)
                data += "{}\t".format(v.verifyEn)
                data += "{}\t".format(v._base.modelId)
                data += "{}\t".format(v._base.isBigEndian)
                data += "{}\t".format(v._base.bitReverse)
                data += "{}\t".format(v._base.binPoint)
                data += "{}\t".format(v.bulkEn)
                data += "{}\t".format(v.updateNotify)
                data += "{}\t".format(v._block._reqSlaveName())
                data += "{}\t".format(v._block.path)
                data += "{:#x}\t".format(v._block.size)
                data += "{}\t".format(v._numValues())
                data += "{}\t".format(v._valueBits())
                data += "{}\t".format(v._valueStride())
                data += "{}\t".format(v._retryCount())
                # Escape " characters
                description = v.description.replace('"',r'\"')
                # Escape \n characters and strip each line in the description field
                description = description.split('\n')
                description = '\\\n'.join([x.strip() for x in description])
                data += "{}".format(description)
                lines.append(data)

        with open(fname,'w') as f:

            if headerEn:
                f.write('// #############################################\n')
                f.write('// Auto Generated Header File From Rogue\n')
                f.write('// #############################################\n')
                f.write('#ifndef __ROGUE_ADDR_MAP_H__\n')
                f.write('#define __ROGUE_ADDR_MAP_H__\n\n')
                f.write(f'#define ROGUE_ADDR_MAP "{header}|"\\\n')

                for line in lines:
                    f.write(f'     "{line}|"\\\n')

                f.write('\n#endif\n')
            else:
                f.write(header + '\n')
                for line in lines:
                    f.write(line + '\n')

    @pr.expose
    def saveVariableList(self,fname,polledOnly=False,incGroups=None):
        """


        Parameters
        ----------
        fname :

        polledOnly : bool
             (Default value = False)
        incGroups :
             (Default value = None)

        Returns
        -------

        """
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

    def _hbeatWorker(self):
        """
        """
        while self._running:
            time.sleep(1)

            with self.updateGroup():
                self.Time.set(time.time())

    def _rootAttached(self):
        """
        """
        self._parent = self
        self._root   = self
        self._path   = self.name

        for key,value in self._nodes.items():
            value._rootAttached(self,self)

        self._buildBlocks()

        # Some variable initialization can run until the blocks are built
        for v in self.variables.values():
            v._finishInit()

    def _write(self):
        """Write all blocks"""
        self._log.info("Start root write")
        with self.pollBlock(), self.updateGroup():
            self.writeBlocks(force=self.ForceWrite.value(), recurse=True)
            self._log.info("Verify root read")
            self.verifyBlocks(recurse=True)
            self._log.info("Check root read")
            self.checkBlocks(recurse=True)

        self._log.info("Done root write")
        return True

    def _read(self):
        """Read all blocks"""
        self._log.info("Start root read")
        with self.pollBlock(), self.updateGroup():
            self.readBlocks(recurse=True)
            self._log.info("Check root read")
            self.checkBlocks(recurse=True)

        self._log.info("Done root read")
        return True

    @pr.expose
    def saveYaml(self,name,readFirst,modes,incGroups,excGroups,autoPrefix,autoCompress):
        """
        Save YAML configuration/status to a file. Called from command

        Parameters
        ----------
        name :

        readFirst :

        modes :

        incGroups :

        excGroups :

        autoPrefix :

        autoCompress :


        Returns
        -------

        """

        # Auto generate name if no arg
        if name is None or name == '':
            name = datetime.datetime.now().strftime(autoPrefix + "_%Y%m%d_%H%M%S.yml")

            if autoCompress:
                name += '.zip'

        yml = self.getYaml(readFirst=readFirst,modes=modes,incGroups=incGroups,excGroups=excGroups, recurse=True)

        if name.split('.')[-1] == 'zip':
            with zipfile.ZipFile(name, 'w', compression=zipfile.ZIP_LZMA) as zf:
                with zf.open(os.path.basename(name[:-4]),'w') as f:
                    f.write(yml.encode('utf-8'))
        else:
            with open(name,'w') as f:
                f.write(yml)

        return True


    def loadYaml(self,name,writeEach,modes,incGroups,excGroups):
        """
        Load YAML configuration from a file. Called from command

        Parameters
        ----------
        name :

        writeEach :

        modes :

        incGroups :

        excGroups :


        Returns
        -------

        """

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
                with zipfile.ZipFile(base, 'r', compression=zipfile.ZIP_LZMA) as myzip:

                    # Check if passed name is a directory, otherwise generate an error
                    if not any(x.startswith("%s/" % sub.rstrip("/")) for x in myzip.namelist()):
                        raise Exception("loadYaml: Invalid load file: {}, must be a directory or end in .yml or .yaml".format(rl))

                    else:

                        # Iterate through directory contents
                        for zfn in myzip.namelist():

                            # Filter by base directory
                            if zfn.find(sub) == 0:
                                spt = zfn.split('%s/' % sub.rstrip('/'))[1]

                                # Entry ends in .yml or *.yml and is in current directory
                                if '/' not in spt and (spt[-4:] == '.yml' or spt[-5:] == '.yaml'):
                                    lst.append(base + '/' + zfn)

            # Entry is a directory
            elif os.path.isdir(rl):
                dlst = glob.glob('{}/*.yml'.format(rl))
                dlst.extend(glob.glob('{}/*.yaml'.format(rl)))
                lst.extend(sorted(dlst))

            # Not a zipfile, not a directory and does not end in .yml
            else:
                raise Exception("loadYaml: Invalid load file: {}, must be a directory or end in .yml or .yaml".format(rl))

        # Read each file
        with self.pollBlock(), self.updateGroup():
            for fn in lst:
                d = pr.yamlToData(fName=fn)
                self._setDictRoot(d=d,writeEach=writeEach,modes=modes,incGroups=incGroups,excGroups=excGroups)

            if not writeEach:
                self._write()

        if self.InitAfterConfig.value():
            self.initialize()

        return True

    def treeDict(self, modes=['RW', 'RO', 'WO'], incGroups=None, excGroups=None):
        d = self._getDict(modes, incGroups, excGroups, properties=True)
        return {self.name: d}

    def treeYaml(self, modes=['RW', 'RO', 'WO'], incGroups=None, excGroups=None, properties=None):
        return pr.dataToYaml(self.treeDict(modes, incGroups, excGroups, properties))

    def setYaml(self,yml,writeEach,modes,incGroups,excGroups):
        """
        Set variable values from a yaml file
        modes is a list of variable modes to act on.
        writeEach is set to true if accessing a single variable at a time.
        Writes will be performed as each variable is updated. If set to
        false a bulk write will be performed after all of the variable updates
        are completed. Bulk writes provide better performance when updating a large
        quantity of variables.

        Parameters
        ----------
        yml :

        writeEach :

        modes :

        incGroups :

        excGroups :


        Returns
        -------

        """
        d = pr.yamlToData(yml)

        with self.pollBlock(), self.updateGroup():
            self._setDictRoot(d=d,writeEach=writeEach,modes=modes,incGroups=incGroups,excGroups=excGroups)

            if not writeEach:
                self._write()

        if self.InitAfterConfig.value():
            self.initialize()

    def remoteVariableDump(self,name,modes,readFirst):
        """
        Dump remote variable values to a file.

        Parameters
        ----------
        name :

        modes :

        readFirst :


        Returns
        -------

        """

        # Auto generate name if no arg
        if name is None or name == '':
            name = datetime.datetime.now().strftime("regdump_%Y%m%d_%H%M%S.txt")

        if readFirst:
            self._read()

        with open(name,'w') as f:
            for v in self.variableList:
                if hasattr(v,'_getDumpValue') and v.mode in modes:
                    f.write(v._getDumpValue(False))

        return True


    def _setDictRoot(self,d,writeEach,modes,incGroups,excGroups):
        """


        Parameters
        ----------
        d :

        writeEach :

        modes :

        incGroups :

        excGroups :


        Returns
        -------

        """
        for key, value in d.items():

            # Attempt to get node
            node = self.getNode(key)

            # Call setDict on node
            if node is not None:
                node._setDict(d=value,writeEach=writeEach,modes=modes,incGroups=incGroups,excGroups=excGroups,keys=None)
            else:
                self._log.error("Entry {} not found".format(key))


    def _clearLog(self):
        """Clear the system log"""
        self.SystemLog.set(SystemLogInit)
        self.SystemLogLast.set('')

    def _queueUpdates(self,var):
        """


        Parameters
        ----------
        var :


        Returns
        -------

        """
        tid = threading.get_ident()

        with self._updateLock:
            if tid not in self._updateTrack:
                self._updateTrack[tid] = UpdateTracker(self._updateQueue)
            self._updateTrack[tid].update(var)

    # Worker thread
    def _updateWorker(self):
        """ """
        self._log.info("Starting update thread")

        while True:
            uvars = self._updateQueue.get()

            # Done
            if uvars is None:
                self._log.info("Stopping update thread")
                self._updateQueue.task_done()
                return

            # Process list
            elif len(uvars) > 0:
                self._log.debug(F'Process update group. Length={len(uvars)}. Entry={list(uvars.keys())[0]}')
                for p,v in uvars.items():
                    val = v._doUpdate()

                    # Call listener functions,
                    with self._varListenLock:
                        for func,doneFunc,incGroups,excGroups in self._varListeners:
                            if v.filterByGroup(incGroups, excGroups):
                                try:
                                    func(p,val)

                                except Exception as e:
                                    if v == self.SystemLog or v == self.SystemLogLast:
                                        print("------- Error Executing Syslog Listeners -------")
                                        print("Error: {}".format(e))
                                        print("------------------------------------------------")
                                    else:
                                        pr.logException(self._log,e)

                # Finalize listeners
                with self._varListenLock:
                    for func,doneFunc,incGroups,excGroups in self._varListeners:
                        if doneFunc is not None:
                            try:
                                doneFunc()
                            except Exception as e:
                                pr.logException(self._log,e)

                self._log.debug(F"Done update group. Length={len(uvars)}. Entry={list(uvars.keys())[0]}")

            # Set done
            self._updateQueue.task_done()

    # Deprecated
    def _getStreamMaster(self):
        if self._streamMaster is None:
            print("========== Deprecation Warning =============================== ")
            print(" Setting up variable streaming directly through the root class ")
            print(" is no longer supported. Instead create a VariableStram        ")
            print(" object seperately and add it as an interface:                 ")
            print("                                                               ")
            print("    with Root() as r:                                          ")
            print("       stream = pyrogue.interfaces.stream.Variable(root=r)     ")
            print("       r.addInterface(stream)                                  ")
            print("                                                               ")
            print(" You can then connect stream slaves to the newly created       ")
            print(" VariableStream instance:                                      ")
            print("                                                               ")
            print("    slave << stream                                            ")
            print("===============================================================")
            self._streamMaster = pr.interfaces.stream.Variable(root=self, incGroups=self._streamIncGroups, excGroups=self._streamExcGroups)
            self.addInterface(self._streamMaster)

        return self._streamMaster

    # Deprecated support
    def __rshift__(self,other):
        pr.streamConnect(self,other)
        return other
