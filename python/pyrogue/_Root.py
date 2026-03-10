#-----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
#-----------------------------------------------------------------------------
#  Description:
#       PyRogue base module - Root Class
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
from __future__ import annotations

import sys
import os
import glob
import rogue
import rogue.interfaces.memory as rim
import threading
import logging
import pyrogue as pr
import functools as ft
import time
import queue
import json
import zipfile
import traceback
import datetime
from contextlib import contextmanager
from typing import Any, Callable, Iterator

SystemLogInit = '[]'

class UpdateTracker(object):
    """Track grouped variable updates for root listeners."""
    def __init__(self, q: Any) -> None:
        """Initialize update tracking state for one worker thread."""
        self._count = 0
        self._list = {}
        self._period = 0
        self._last = time.time()
        self._q = q

    def increment(self, period: float) -> None:
        """
        Increment active update-group depth.

        Parameters
        ----------
        period : float, optional (default = 0)
            Maximum group flush period in seconds.
        """

        if self._count == 0 or self._period < period:
            self._period = period
        self._count +=1

    def decrement(self) -> None:
        """Decrement active update-group depth."""
        if self._count != 0:
            self._count -= 1

        self._check()

    def _check(self) -> None:
        """Flush queued updates when depth or period criteria are met."""
        if self._count == 0 or (self._period != 0 and (time.time() - self._last) > self._period):
            if len(self._list) != 0:
                #print(f"Update fired {time.time()}")
                self._last = time.time()
                self._q.put(self._list)
                self._list = {}

    def update(self, var: pr.BaseVariable) -> None:
        """
        Queue a variable update.

        Parameters
        ----------
        var : pr.BaseVariable
            Variable object that was updated.
        """
        self._list[var.path] = var
        self._check()

class RootLogHandler(logging.Handler):
    """Listen to log entries and mirror them into root log variables."""
    def __init__(self,*, root: Any) -> None:
        """Initialize a log handler bound to a Root instance."""
        logging.Handler.__init__(self)
        self._root = root

    def emit(self, record: logging.LogRecord) -> None:
        """
        Parameters
        ----------
        record : logging.LogRecord
            Logging record to store in ``SystemLog``.
        """

        if not self._root.running:
            return

        with self._root.updateGroup():
            try:
                se = { 'created'     : record.created,
                       'name'        : record.name,
                       'message'     : record.getMessage(),
                       'exception'   : None,
                       'traceBack'   : None,
                       'levelName'   : record.levelname,
                       'levelNumber' : record.levelno }

                if hasattr(record, 'rogue_cpp'):
                    se['rogueCpp'] = record.rogue_cpp
                if hasattr(record, 'rogue_tid'):
                    se['rogueTid'] = record.rogue_tid
                if hasattr(record, 'rogue_pid'):
                    se['roguePid'] = record.rogue_pid
                if hasattr(record, 'rogue_logger'):
                    se['rogueLogger'] = record.rogue_logger
                if hasattr(record, 'rogue_timestamp'):
                    se['rogueTimestamp'] = record.rogue_timestamp
                if hasattr(record, 'rogue_component'):
                    se['rogueComponent'] = record.rogue_component

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
    Class which serves as the root of a tree of Nodes.
    The root is the interface point for tree level access and updates.

    Parameters
    ----------
    name : str, optional
        Root name. Defaults to class name.
    description : str, optional (default = "")
        Human-readable description.
    expand : bool, optional (default = True)
        Default GUI expand state.
    timeout : float, optional (default = 1.0)
        Transaction timeout in seconds.
    initRead : bool, optional (default = False)
        Perform an initial read on start.
    initWrite : bool, optional (default = False)
        Perform an initial write on start.
    pollEn : bool, optional (default = True)
        Enable polling on start.
    maxLog : int, optional (default = 1000)
        Maximum log entries to retain.
    unifyLogs : bool, optional (default = False)
        Forward Rogue C++ logs into Python logging and disable the native Rogue
        stdout sink to avoid duplicate output in mixed PyRogue applications.
    """

    def __enter__(self) -> Root:
        """Root enter."""
        self.start()
        return self

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        """Root exit."""
        self.stop()

    def __init__(self, *,
                 name: str | None = None,
                 description: str = '',
                 expand: bool = True,
                 timeout: float = 1.0,
                 initRead: bool = False,
                 initWrite: bool = False,
                 pollEn: bool = True,
                 maxLog: int = 1000,
                 unifyLogs: bool = False) -> None:
        """Initialize the root node, workers, and built-in variables/commands."""
        rogue.interfaces.stream.Master.__init__(self)

        # Store startup parameters
        self._timeout         = timeout
        self._initRead        = initRead
        self._initWrite       = initWrite
        self._pollEn          = pollEn
        self._maxLog          = maxLog
        self._unifyLogs       = unifyLogs
        self._doHeartbeat     = True # Backdoor flag

        if self._unifyLogs:
            pr.setUnifiedLogging(True)

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

        self.add(pr.LocalVariable(name='Time', value=time.time(), mode='RO', hidden=True,
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


    def start(self) -> None:
        """Setup the tree and start background threads for pollQueue and updateQueue.
        Call Device._start() recursively on child Nodes.

        """

        if self._running:
            raise pr.NodeError("Root is already started! Can't restart!")

        self._log.info("Starting root lifecycle")

        # Call special root level rootAttached
        self._rootAttached()

        # Finish Initialization
        self._finishInit()

        # Get full list of Blocks and Devices with size
        tmpList = []
        for d in self.deviceList:
            for b in d._blocks:
                if isinstance(b, rim.Block):
                    tmpList.append(b)

        # Sort the list by address/size
        tmpList.sort(key=lambda x: (x._reqSlaveId(), x.address, x.size))

        # Look for overlaps
        for i in range(1,len(tmpList)):

            self._log.debug(
                "Comparing %s with address=%#x to %s with address=%#x and size=%s",
                tmpList[i].path,
                tmpList[i].address,
                tmpList[i-1].path,
                tmpList[i-1].address,
                tmpList[i-1].size,
            )

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

        # Detect large timeout
        if self._timeout > 10.0:
            self._log.warning(
                "Large timeout value of %s seconds detected. This may cause unexpected system behavior.",
                self._timeout,
            )

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
        self._log.info("Root lifecycle started")


    def stop(self) -> None:
        """Stop background threads. Must be called for clean exit.
        Call Device._stop() to recursively stop all Devices in the tree.
        """

        self._log.info("Stopping root lifecycle")
        self._running = False
        self._updateQueue.put(None)
        self._updateThread.join()

        if self._pollQueue:
            self._pollQueue._stop()

        pr.Device._stop(self)
        self._log.info("Root lifecycle stopped")

    @pr.expose
    @property
    def running(self) -> bool:
        """Return True if the root is running."""
        return self._running

    def addVarListener(
        self,
        func: Callable[[str, pr.VariableValue], None],
        *,
        done: Callable[[], None] | None = None,
        incGroups: str | list[str] | None = None,
        excGroups: str | list[str] | None = None,
    ) -> None:
        """
        Add a variable update listener function.
        The variable path and value are passed as ``func(path, varValue)``.

        Parameters
        ----------
        func : callable
            Listener callback of the form ``func(path, varValue)`` where
            ``path`` is a full variable path and ``varValue`` is a
            :py:class:`pyrogue.VariableValue`.
        done : callable, optional
            Optional callback of the form ``done()`` executed after each update
            batch.
        incGroups : str or list[str], optional
            Group name or group names to include.
        excGroups : str or list[str], optional
            Group name or group names to exclude.
        """

        with self._varListenLock:
            self._varListeners.append((func, done, incGroups, excGroups))

    def _addVarListenerCpp(
        self,
        func: Callable[[str, str], None],
        done: Callable[[], None],
    ) -> None:
        """Add a listener callback using display-string values.

        Parameters
        ----------
        func : callable
            Callback of the form ``func(path, valueDisp)``.
        done : callable
            Callback of the form ``done()`` called after each batch.
        """

        self.addVarListener(lambda path, varValue: func(path, varValue.valueDisp), done=done)

    @contextmanager
    def updateGroup(self, period: float = 0) -> Iterator[None]:
        """Get a context manager within which many Variable updates will be broadcast as one.

        Functions that operate on and set() more than one Variable should do so within a Root.updateGroup() context.
        This will reduce the number of update broadcasts that the Root has to make.

        The optional 'period' parameter will allow broadcasts of the state every 'period' seconds, useful for long running functions.

        Parameters
        ----------
        period : float, optional (default = 0)
            Maximum update period in seconds.
        """
        tid = threading.get_ident()

        # At with call
        try:
            self._updateTrack[tid].increment(period)
        except Exception:
            with self._updateLock:
                self._updateTrack[tid] = UpdateTracker(self._updateQueue)
                self._updateTrack[tid].increment(period)

        try:
            yield
        finally:

            # After with is done
            self._updateTrack[tid].decrement()

    @contextmanager
    def pollBlock(self) -> Iterator[None]:
        """
        Context manager that blocks poll activity while active.
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
    def waitOnUpdate(self) -> None:
        """Wait until all update queue items have been processed."""
        self._updateQueue.join()

    def hardReset(self) -> None:
        """Generate a hard reset on all devices.

        Called recursively on the entire tree.

        """
        super().hardReset()
        self._clearLog()

    def __reduce__(self) -> tuple[Any, tuple[dict]]:
        """Return reduced state used by virtual-client serialization."""
        return pr.Node.__reduce__(self)

    @ft.lru_cache(maxsize=None)
    def getNode(self, path: str) -> pr.Node:
        """Get a Node of the tree by its path string

        Parameters
        ----------
        path : str
            Node path. Accepts absolute dotted path, root name, or ``root``.

        Returns
        -------
        pr.Node or None
            Located node object, or ``None`` if no node matches.
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
    def saveAddressMap(self, fname: str) -> None:
        """Dump the tree address map to a file

        Parameters
        ----------
        fname : str
            Destination file path.
        """

        # First form header
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
            f.write(header + '\n')
            for line in lines:
                f.write(line + '\n')

    @pr.expose
    def saveVariableList(
        self,
        fname: str,
        polledOnly: bool = False,
        incGroups: str | list[str] | None = None,
    ) -> None:
        """Save a string representing the entire tree

        Parameters
        ----------
        fname : str
            Destination file path.
        polledOnly : bool, optional (default = False)
            If True, include only polled variables.
        incGroups : str or list[str], optional
            Group name or group names to include.
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

    def _hbeatWorker(self) -> None:
        """Heartbeat worker which updates the ``Time`` variable."""
        while self._running:
            time.sleep(1)

            with self.updateGroup():
                self.Time.set(time.time())

    def _rootAttached(self) -> None:
        """Attach root references to the full node tree."""
        self._parent = self
        self._root   = self
        self._path   = self.name

        for key,value in self._nodes.items():
            value._rootAttached(self,self)

        self._buildBlocks()

        # Some variable initialization can run until the blocks are built
        for v in self.variables.values():
            v._finishInit()

    def _write(self) -> bool:
        """Write and verify all blocks."""
        self._log.info("Start root write (forceWrite=%s)", self.ForceWrite.value())
        with self.pollBlock(), self.updateGroup():
            self.writeBlocks(force=self.ForceWrite.value(), recurse=True)
            self._log.info("Verify root write with readback")
            self.verifyBlocks(recurse=True)
            self._log.info("Check verified root write transactions")
            self.checkBlocks(recurse=True)

        self._log.info("Done root write")
        return True

    def _read(self) -> bool:
        """Read and check all blocks."""
        self._log.info("Start root read")
        with self.pollBlock(), self.updateGroup():
            self.readBlocks(recurse=True)
            self._log.info("Check root read transactions")
            self.checkBlocks(recurse=True)

        self._log.info("Done root read")
        return True

    @pr.expose
    def saveYaml(
        self,
        name: str | None,
        readFirst: bool,
        modes: list[str] = ['RW', 'RO', 'WO'],
        incGroups: str | list[str] | None = None,
        excGroups: str | list[str] | None = None,
        autoPrefix: str = '',
        autoCompress: bool = False,
    ) -> bool:
        """
        Save YAML configuration or status to a file.

        Parameters
        ----------
        name : str, optional
            Destination file path. If empty, a timestamped name is generated.
        readFirst : bool
            Read values from hardware before exporting.
        modes : list['RW' | 'WO' | 'RO'], optional (default = ['RW', 'RO', 'WO'])
            Variable modes to include. Allowed values are ``'RW'``, ``'WO'``, and ``'RO'``.
        incGroups : str or list[str], optional
            Group name or group names to include.
        excGroups : str or list[str], optional
            Group name or group names to exclude.
        autoPrefix : str, optional
            Prefix for auto-generated filenames.
        autoCompress : bool, optional
            Generate a ``.zip`` file when auto-generating names. Default False

        Returns
        -------
        bool
            Returns ``True`` when export completes.
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


    def loadYaml(
        self,
        name: str | list[str],
        writeEach: bool,
        modes: list[str],
        incGroups: str | list[str] | None = None,
        excGroups: str | list[str] | None = None,
    ) -> bool:
        """
        Load YAML configuration from files or directories.

        Parameters
        ----------
        name : str or list[str]
            Input file, directory, zip-path, or list of those entries.
        writeEach : bool
            Write each variable as it is applied.
        modes : list['RW' | 'WO' | 'RO']
            Variable modes to include. Allowed values are ``'RW'``, ``'WO'``, and ``'RO'``.
        incGroups : str or list[str], optional
            Group name or group names to include.
        excGroups : str or list[str], optional
            Group name or group names to exclude.

        Returns
        -------
        bool
            Returns ``True`` when load completes.
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

        self._log.info(
            "Loading YAML config from %s file(s), writeEach=%s, modes=%s, incGroups=%s, excGroups=%s",
            len(lst),
            writeEach,
            modes,
            incGroups,
            excGroups,
        )

        # Read each file
        with self.pollBlock(), self.updateGroup():
            for fn in lst:
                self._log.debug("Applying YAML config file %s", fn)
                d = pr.yamlToData(fName=fn)
                self._setDictRoot(d=d,writeEach=writeEach,modes=modes,incGroups=incGroups,excGroups=excGroups)

            if not writeEach:
                self._log.info("Committing staged YAML config to hardware")
                self._write()

        if self.InitAfterConfig.value():
            self._log.info("Running initialize() after YAML config load")
            self.initialize()

        return True

    def treeDict(
        self,
        modes: list[str] = ['RW', 'RO', 'WO'],
        incGroups: str | list[str] | None = None,
        excGroups: str | list[str] | None = None,
        properties: bool = True,
    ) -> dict[str, Any]:
        """
        Return the root tree as a dictionary.

        Parameters
        ----------
        modes : list['RW' | 'WO' | 'RO'], optional (default = ['RW', 'RO', 'WO'])
            Variable modes to include. Allowed values are ``'RW'``, ``'WO'``, and ``'RO'``.
        incGroups : str or list[str], optional
            Group names to include.
        excGroups : str or list[str], optional
            Group names to exclude.
        properties : bool, optional (default = True)
            Include variable property fields.

        Returns
        -------
        dict[str, object]
            Dictionary keyed by root name with tree data.
        """
        d = self._getDict(modes, incGroups, excGroups, properties=properties)
        return {self.name: d}

    def treeYaml(
        self,
        modes: list[str] = ['RW', 'RO', 'WO'],
        incGroups: str | list[str] | None = None,
        excGroups: str | list[str] | None = None,
        properties: bool | None = None,
    ) -> str:
        """
        Return the root tree as YAML text.

        Parameters
        ----------
        modes : list['RW' | 'WO' | 'RO'], optional (default = ['RW', 'RO', 'WO'])
            Variable modes to include. Allowed values are ``'RW'``, ``'WO'``, and ``'RO'``.
        incGroups : str or list[str], optional
            Group names to include.
        excGroups : str or list[str], optional
            Group names to exclude.
        properties : bool, optional
            Include variable property fields. If ``None``, defaults to ``True``.

        Returns
        -------
        str
            YAML representation of the root tree.
        """
        if properties is None:
            properties = True
        return pr.dataToYaml(self.treeDict(modes, incGroups, excGroups, properties))

    def setYaml(
        self,
        yml: str,
        writeEach: bool,
        modes: list[str],
        incGroups: str | list[str] | None = None,
        excGroups: str | list[str] | None = None,
    ) -> None:
        """
        Set variable values from YAML text.

        Parameters
        ----------
        yml : str
            YAML text containing values to apply.
        writeEach : bool
            Write each variable as it is applied.
        modes : list['RW' | 'WO' | 'RO']
            Variable modes to include. Allowed values are ``'RW'``, ``'WO'``, and ``'RO'``.
        incGroups : str or list[str], optional
            Group name or group names to include.
        excGroups : str or list[str], optional
            Group name or group names to exclude.
        """
        d = pr.yamlToData(yml)

        self._log.info(
            "Applying YAML text config, writeEach=%s, modes=%s, incGroups=%s, excGroups=%s",
            writeEach,
            modes,
            incGroups,
            excGroups,
        )

        with self.pollBlock(), self.updateGroup():
            self._setDictRoot(d=d,writeEach=writeEach,modes=modes,incGroups=incGroups,excGroups=excGroups)

            if not writeEach:
                self._log.info("Committing staged YAML text config to hardware")
                self._write()

        if self.InitAfterConfig.value():
            self._log.info("Running initialize() after YAML text config")
            self.initialize()

    def remoteVariableDump(
        self,
        name: str | None,
        modes: list[str],
        readFirst: bool,
    ) -> bool:
        """
        Dump remote variable values to a file.

        Parameters
        ----------
        name : str, optional
            Destination file path. If empty, a timestamped name is generated.
        modes : list['RW' | 'WO' | 'RO']
            Variable modes to include. Allowed values are ``'RW'``, ``'WO'``, and ``'RO'``.
        readFirst : bool
            Read values from hardware before dumping.

        Returns
        -------
        bool
            Returns ``True`` when dump completes.
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


    def _setDictRoot(
        self,
        d: dict[str, Any],
        writeEach: bool,
        modes: list[str],
        incGroups: str | list[str] | None = None,
        excGroups: str | list[str] | None = None,
    ) -> None:
        """
        Parameters
        ----------
        d : dict[str, object]
            Root-level dictionary to apply.
        writeEach : bool
            Write each variable as it is applied.
        modes : list['RW' | 'WO' | 'RO']
            Variable modes to include. Allowed values are ``'RW'``, ``'WO'``, and ``'RO'``.
        incGroups : str or list[str], optional
            Group name or group names to include.
        excGroups : str or list[str], optional
            Group name or group names to exclude.
        """
        for key, value in d.items():

            # Attempt to get node
            node = self.getNode(key)

            # Call setDict on node
            if node is not None:
                node._setDict(d=value,writeEach=writeEach,modes=modes,incGroups=incGroups,excGroups=excGroups,keys=None)
            else:
                self._log.error("Entry %s not found", key)


    def _clearLog(self) -> None:
        """Clear the system log."""
        self.SystemLog.set(SystemLogInit)
        self.SystemLogLast.set('')

    def _queueUpdates(self, var: Any) -> None:
        """
        Parameters
        ----------
        var : object
            Variable object queued for listener update.
        """
        tid = threading.get_ident()

        try:
            self._updateTrack[tid].update(var)
        except Exception:
            with self._updateLock:
                self._updateTrack[tid] = UpdateTracker(self._updateQueue)
                self._updateTrack[tid].update(var)

    # Recursively add listeners to update list
    def _recurseAddListeners(self, nvars: dict[str, Any], var: Any) -> None:
        """Collect listener variables recursively into an update dictionary."""
        for vl in var._listeners:
            nvars[vl.path] = vl

            self._recurseAddListeners(nvars, vl)

    # Worker thread
    def _updateWorker(self) -> None:
        """Update-thread worker for variable notifications."""
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
                self._log.debug(
                    "Process update group. Length=%s. Entry=%s",
                    len(uvars),
                    list(uvars.keys())[0],
                )

                # Copy list and add listeners
                nvars = uvars.copy()
                for p,v in uvars.items():
                    self._recurseAddListeners(nvars, v)

                # Process the new list
                for p,v in nvars.items():

                    # Process updates
                    val = v._doUpdate()

                    # Call root listener functions,
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

                # Finalize root listeners
                with self._varListenLock:
                    for func,doneFunc,incGroups,excGroups in self._varListeners:
                        if doneFunc is not None:
                            try:
                                doneFunc()
                            except Exception as e:
                                pr.logException(self._log,e)

                self._log.debug(
                    "Done update group. Length=%s. Entry=%s",
                    len(uvars),
                    list(uvars.keys())[0],
                )

            # Set done
            self._updateQueue.task_done()
