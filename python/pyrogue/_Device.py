#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Title      : PyRogue base module - Device Class
#-----------------------------------------------------------------------------
# File       : pyrogue/_Device.py
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
import rogue.interfaces.memory as rim
import collections
import datetime
import functools as ft
import pyrogue as pr
import inspect
import threading
import math
import time

class EnableVariable(pr.BaseVariable):
    def __init__(self, *, enabled, deps=None):
        pr.BaseVariable.__init__(
            self,
            description='Determines if device is enabled for hardware access',            
            name='enable',
            mode='RW',
            value=enabled, 
            disp={False: 'False', True: 'True', 'parent': 'ParentFalse', 'deps': 'ExtDepFalse'})

        if deps is None:
            self._deps   = []
            self._depDis = False
        else:
            self._deps   = deps
            self._depDis = True

        for d in self._deps:
            d.addListener(self)

        self._value  = enabled
        self._lock   = threading.Lock()

    def nativeType(self):
        return bool

    @pr.expose
    def get(self, read=False):
        ret = self._value

        with self._lock:
            if self._value is False:
                ret = False
            elif self._depDis:
                ret = 'deps'
            elif self._parent == self._root:
                #print("Root enable = {}".format(self._value))
                ret = self._value
            else:
                if self._parent._parent.enable.value() is not True:
                    ret = 'parent'
                else:
                    ret = True

        return ret
        
    @pr.expose
    def set(self, value, write=True):
        if value != 'parent' and value != 'deps':
            old = self.value()

            with self._lock:
                self._value = value
            
            if old != value and old != 'parent' and old != 'deps':
                self.parent.enableChanged(value)

        with self.parent.root.updateGroup():
            self._queueUpdate()

    def _doUpdate(self):
        if len(self._deps) != 0:
            oldEn = (self.value() == True)

            with self._lock:
                self._depDis = not all(x.value() for x in self._deps)

            newEn = (self.value() == True)

            if oldEn != newEn:
                self.parent.enableChanged(newEn)

        return super()._doUpdate()

    def _rootAttached(self,parent,root):
        pr.Node._rootAttached(self,parent,root)

        if parent != root:
            parent._parent.enable.addListener(self)

class DeviceError(Exception):
    """ Exception for device manipulation errors."""
    pass


class Device(pr.Node,rim.Hub):
    """Device class holder. TODO: Update comments"""

    def __init__(self, *,
                 name=None,
                 description='',
                 memBase=None,
                 offset=0,
                 size=0,
                 hidden=False,
                 blockSize=None,
                 expand=False,
                 enabled=True,
                 defaults=None,
                 enableDeps=None,
                 hubMin=0,
                 hubMax=0):

        
        """Initialize device class"""
        if name is None:
            name = self.__class__.__name__

        # Hub.__init__ must be called first for _setSlave to work below
        rim.Hub.__init__(self,offset,hubMin,hubMax)

        # Blocks
        self._blocks    = []
        self._memBase   = memBase
        self._memLock   = threading.RLock()
        self._size      = size
        self._blockSize = blockSize
        self._defaults  = defaults if defaults is not None else {}

        self.forceCheckEach = False

        # Connect to memory slave
        if memBase: self._setSlave(memBase)

        # Node.__init__ can't be called until after self._memBase is created
        pr.Node.__init__(self, name=name, hidden=hidden, description=description, expand=expand)

        self._log.info("Making device {:s}".format(name))

        # Convenience methods
        self.addRemoteCommands = ft.partial(self.addNodes, pr.RemoteCommand)

        # Variable interface to enable flag
        self.add(EnableVariable(enabled=enabled, deps=enableDeps))

        self.add(pr.LocalCommand(name='ReadDevice', value=False, hidden=True,
                                 function=lambda arg: self.readAndCheckBlocks(recurse=arg),
                                 description='Force read of device without recursion'))

        self.add(pr.LocalCommand(name='WriteDevice', value='', hidden=True,
                                 function=lambda arg: self.writeAndVerifyBlocks(force=True,recurse=arg),
                                 description='Force write of device without recursion'))

    @pr.expose
    @property
    def address(self):
        return self._getAddress()

    @pr.expose
    @property
    def offset(self):
        return self._getOffset()

    @pr.expose
    @property
    def size(self):
        return self._size

    @pr.expose
    @property
    def memBaseId(self):
        return self._reqSlaveId()

    def add(self,node):
        # Call node add
        pr.Node.add(self,node)

        # Adding device
        if isinstance(node,Device):
           
            # Device does not have a membase
            if node._memBase is None:
                node._setSlave(self)

    def addRemoteVariables(self, number, stride, pack=False, **kwargs):
        hidden = pack or kwargs.pop('hidden', False)
        self.addNodes(pr.RemoteVariable, number, stride, hidden=hidden, **kwargs)

        # If pack specified, create a linked variable to combine everything
        if pack:
            varList = getattr(self, kwargs['name']).values()
            
            def linkedSet(dev, var, val, write):
                if val == '': return
                values = reversed(val.split('_'))
                for variable, value in zip(varList, values):
                    variable.setDisp(value, write=write)

            def linkedGet(dev, var, read):
                values = [v.getDisp(read=read) for v in varList]
                return '_'.join(reversed(values))

            name = kwargs.pop('name')
            kwargs.pop('value', None)
            
            lv = pr.LinkVariable(name=name, value='', dependencies=varList, linkedGet=linkedGet, linkedSet=linkedSet, **kwargs)
            self.add(lv)

    def setPollInterval(self, interval, variables=None):
        """Set the poll interval for a group of variables.
        The variables param is an Iterable of strings
        If variables=None, set interval for all variables that currently have nonzero pollInterval"""
        if variables is None:
            variables = [k for k,v in self.variables.items() if v.pollInterval != 0]

        for x in variables:
            v = self.node(x).pollInterval = interval

    def hideVariables(self, hidden, variables=None):
        """Hide a list of Variables (or Variable names)"""
        if variables is None:
            variables=self.variables.values()
            
        for v in variables:
            if isinstance(v, pr.BaseVariable):
                v._hidden = hidden;
            elif isinstance(variables[0], str):
                self.variables[v]._hidden = hidden

    def initialize(self):
        for key,value in self.devices.items():
            value.initialize()

    def hardReset(self):
        for block in self._blocks:
            block._forceStale()
        for key,value in self.devices.items():
            value.hardReset()

    def countReset(self):
        for key,value in self.devices.items():
            value.countReset()

    def enableChanged(self,value):
        pass # Do nothing
        #if value is True:
        #    self.writeAndVerifyBlocks(force=True, recurse=True, variable=None)

    def writeBlocks(self, force=False, recurse=True, variable=None, checkEach=False):
        """
        Write all of the blocks held by this Device to memory
        """
        self._log.debug(f'Calling {self.path}._writeBlocks')

        checkEach = checkEach or self.forceCheckEach

        # Process local blocks.
        if variable is not None:
            for b in self._getBlocks(variable):
                if (force or b.stale):                
                    b.startTransaction(rim.Write, check=checkEach)

        else:
            for block in self._blocks:
                if (force or block.stale) and block.bulkEn:
                    block.startTransaction(rim.Write, check=checkEach)

            if recurse:
                for key,value in self.devices.items():
                    value.writeBlocks(force=force, recurse=True, checkEach=checkEach)

    def verifyBlocks(self, recurse=True, variable=None, checkEach=False):
        """
        Perform background verify
        """
        #print(f'Calling {self.path}.verifyBlocks(recurse={recurse}, variable={variable}, checkEach={checkEach}')

        checkEach = checkEach or self.forceCheckEach        

        # Process local blocks.
        if variable is not None:
            for b in self._getBlocks(variable):
                b.startTransaction(rim.Verify, check=checkEach)

        else:
            for block in self._blocks:
                if block.bulkEn:
                    block.startTransaction(rim.Verify, checkEach)

            if recurse:
                for key,value in self.devices.items():
                    value.verifyBlocks(recurse=True, checkEach=checkEach)

    def readBlocks(self, recurse=True, variable=None, checkEach=False):
        """
        Perform background reads
        """
        self._log.debug(f'Calling {self.path}._readBlocks(recurse={recurse}, variable={variable}, checkEach={checkEach}')
        #print(f'Calling {self.path}.readBlocks(recurse={recurse}, variable={variable}, checkEach={checkEach})')

        checkEach = checkEach or self.forceCheckEach        

        # Process local blocks. 
        if variable is not None:
            for b in self._getBlocks(variable):
                b.startTransaction(rim.Read, check=checkEach)

        else:
            for block in self._blocks:
                if block.bulkEn:
                    block.startTransaction(rim.Read, check=checkEach)

            if recurse:
                for key,value in self.devices.items():
                    value.readBlocks(recurse=True, checkEach=checkEach)

    def checkBlocks(self, recurse=True, variable=None):
        """Check errors in all blocks and generate variable update nofifications"""
        self._log.debug(f'Calling {self.path}._checkBlocks')

        with self.root.updateGroup():

            # Process local blocks
            if variable is not None:
                for b in self._getBlocks(variable):
                    b._checkTransaction()

            else:
                for block in self._blocks:
                    block._checkTransaction()

                if recurse:
                    for key,value in self.devices.items():
                            value.checkBlocks(recurse=True)

    def writeAndVerifyBlocks(self, force=False, recurse=True, variable=None, checkEach=False):
        """Perform a write, verify and check. Usefull for committing any stale variables"""
        self.writeBlocks(force=force, recurse=recurse, variable=variable, checkEach=checkEach)
        self.verifyBlocks(recurse=recurse, variable=variable, checkEach=checkEach)
        self.checkBlocks(recurse=recurse, variable=variable)

    def readAndCheckBlocks(self, recurse=True, variable=None, checkEach=False):
        """Perform a read and check."""
        self.readBlocks(recurse=recurse, variable=variable, checkEach=checkEach)
        self.checkBlocks(recurse=recurse, variable=variable)

    def _rawTxnChunker(self, offset, data, base=pr.UInt, stride=4, wordBitSize=32, txnType=rim.Write, numWords=1):
        if offset + (numWords * stride) > self._size:
            raise pr.MemoryError(name=self.name, address=offset|self.address,
                                 msg='Raw transaction outside of device size')

        if wordBitSize > stride*8:
            raise pr.MemoryError(name=self.name, address=offset|self.address,
                                 msg='Called raw memory access with wordBitSize > stride')

        if txnType == rim.Write or txnType == rim.Post:
            if isinstance(data, bytearray):
                ldata = data
            elif isinstance(data, collections.Iterable):
                ldata = b''.join(base.toBytes(word, wordBitSize) for word in data)
            else:
                ldata = base.toBytes(data, wordBitSize)

        else:
            if data is not None:
                ldata = data
            else:
                ldata = bytearray(numWords*stride)
            
        with self._memLock:
            for i in range(offset, offset+len(ldata), self._reqMaxAccess()):
                sliceOffset = i | self.offset
                txnSize = min(self._reqMaxAccess(), len(ldata)-(i-offset))
                #print(f'sliceOffset: {sliceOffset:#x}, ldata: {ldata}, txnSize: {txnSize}, buffOffset: {i-offset}')
                self._reqTransaction(sliceOffset, ldata, txnSize, i-offset, txnType)

            return ldata

    def _rawWrite(self, offset, data, base=pr.UInt, stride=4, wordBitSize=32, tryCount=1, posted=False):
        with self._memLock:

            if posted: txn = rim.Post
            else: txn = rim.Write

            for _ in range(tryCount):
                self._setError(0)
                self._rawTxnChunker(offset, data, base, stride, wordBitSize, txn)
                self._waitTransaction(0)

                if self._getError() == 0: return
                elif posted: break
                self._log.warning("Retrying raw write transaction")

            # If we get here an error has occured
            raise pr.MemoryError (name=self.name, address=offset|self.address, error=self._getError())
        
    def _rawRead(self, offset, numWords=1, base=pr.UInt, stride=4, wordBitSize=32, data=None, tryCount=1):
        with self._memLock:
            for _ in range(tryCount):
                self._setError(0)
                ldata = self._rawTxnChunker(offset, data, base, stride, wordBitSize, txnType=rim.Read, numWords=numWords)
                self._waitTransaction(0)

                if self._getError() == 0:
                    if numWords == 1:
                        return base.fromBytes(base.mask(ldata, wordBitSize),wordBitSize)
                    else:
                        return [base.fromBytes(base.mask(ldata[i:i+stride], wordBitSize),wordBitSize) for i in range(0, len(ldata), stride)]
                self._log.warning("Retrying raw read transaction")
                
            # If we get here an error has occured
            raise pr.MemoryError (name=self.name, address=offset|self.address, error=self._getError())


    def _getBlocks(self, variables):
        """
        Get a list of unique blocks from a list of Variables. 
        Variables must belong to this device!
        """
        if isinstance(variables, pr.BaseVariable):
            variables = [variables]

        blocks = []
        for v in variables:
            if v.parent is not self:
                raise DeviceError(
                    f'Variable {v.path} passed to {self.path}._getBlocks() is not a member of {self.path}')
            else:
                if v._block not in blocks and v._block is not None:
                    blocks.append(v._block)
                
        return blocks

    def _buildBlocks(self):
        remVars = []

        blkSize = self._blkMinAccess()

        if self._blockSize is not None:
            if self._blockSize > self._blkMaxAccess():
                blkSize = self._blkMaxAccess()
            else:
                blkSize = self._blockSize

        # Process all of the variables
        for k,n in self.nodes.items():

            # Local variables have a 1:1 block association
            if isinstance(n,pr.LocalVariable):
                self._blocks.append(n._block)

            # Align to min access, create list sorted by offset 
            elif isinstance(n,pr.RemoteVariable) and n.offset is not None:
                n._shiftOffsetDown(n.offset % blkSize, blkSize)
                remVars += [n]

        # Sort var list by offset, size
        remVars.sort(key=lambda x: (x.offset, x.varBytes))
        blocks = []
        blk = None

        # Go through sorted variable list, look for overlaps, group into blocks
        for n in remVars:
            if blk is not None and ( (blk['offset'] + blk['size']) > n.offset):
                self._log.info("Overlap detected var offset={} block offset={} block bytes={}".format(n.offset,blk['offset'],blk['size']))
                n._shiftOffsetDown(n.offset - blk['offset'], blkSize)
                blk['vars'].append(n)

                if n.varBytes > blk['size']: blk['size'] = n.varBytes

            else:
                blk = {'offset':n.offset, 'size':n.varBytes, 'vars':[n]}
                blocks.append(blk)

        # Create blocks
        for b in blocks:
            self._blocks.append(pr.RemoteBlock(offset=b['offset'], size=b['size'], variables=b['vars']))
            self._log.debug("Adding new block at offset {:#02x}, size {}".format(b['offset'], b['size']))

    def _rootAttached(self, parent, root):
        pr.Node._rootAttached(self, parent, root)

        for key,value in self._nodes.items():
            value._rootAttached(self,root)

        self._buildBlocks()

        # Override defaults as dictated by the _defaults dict
        for varName, defValue in self._defaults.items():
            match = pr.nodeMatch(self.variables, varName)
            for var in match:
                var._default = defValue

        # Some variable initialization can run until the blocks are built
        for v in self.variables.values():
            v._finishInit()


    def _setTimeout(self,timeout):
        """
        Set timeout value on all devices & blocks
        """

        for block in self._blocks:
            block.timeout = timeout

        rim.Master._setTimeout(self, int(timeout*1000000))

        for key,value in self._nodes.items():
            if isinstance(value,Device):
                value._setTimeout(timeout)

    def command(self, **kwargs):
        """A Decorator to add inline constructor functions as commands"""
        def _decorator(func):
            if 'name' not in kwargs:
                kwargs['name'] = func.__name__

            self.add(pr.LocalCommand(function=func, **kwargs))

            return func
        return _decorator

    def linkVariableGet(self, **kwargs):
        """ Decorator to add inline constructor functions as LinkVariable.linkedGet functions"""
        def _decorator(func):
            if 'name' not in kwargs:
                kwargs['name'] = func.__name__

            self.add(pr.LinkVariable(linkedGet=func, **kwargs))

            return func
        return _decorator

class ArrayDevice(Device):
    def __init__(self, *, arrayClass, number, stride=0, arrayArgs=None, **kwargs):
        if 'name' not in kwargs:
            kwargs['name'] = f'{arrayClass.__name__}Array'
        super().__init__(**kwargs)

        if arrayArgs is None:
            arrayArgs = [{} for x in range(number)]
        elif isinstance(arrayArgs, dict):
            arrayArgs = [arrayArgs for x in range(number)]
            
        for i in range(number):
            args = arrayArgs[i]
            if 'name' in args:
                name = args.pop('name')
            else:
                name = f'{arrayClass.__name__}[{i}]'
            self.add(arrayClass(
                name=name,
                offset=i*stride,
                **args))
                
class DataWriter(Device):
    """Special base class to control data files. TODO: Update comments"""

    def __init__(self, *, hidden=True, **kwargs):
        """Initialize device class"""

        Device.__init__(self, hidden=hidden, **kwargs)

        self.add(pr.LocalVariable(
            name='dataFile',
            mode='RW',
            value='',
            description='Data file for storing frames for connected streams.'))

        self.add(pr.LocalVariable(
            name='open',
            mode='RW',
            value=False,
            localSet=self._setOpen,
            description='Data file open state'))

        self.add(pr.LocalVariable(
            name='bufferSize',
            mode='RW',
            value=0,
            typeStr='UInt32',
            localSet=self._setBufferSize,
            description='File buffering size. Enables caching of data before call to file system.'))

        self.add(pr.LocalVariable(
            name='maxFileSize',
            mode='RW',
            value=0,
            typeStr='UInt64',
            localSet=self._setMaxFileSize,
            description='Maximum size for an individual file. Setting to a non zero splits the run data into multiple files.'))

        self.add(pr.LocalVariable(
            name='fileSize',
            mode='RO',
            value=0,
            typeStr='UInt64',
            pollInterval=1,
            localGet=self._getFileSize,
            description='Size of data files(s) for current open session in bytes.'))

        self.add(pr.LocalVariable(
            name='frameCount',
            mode='RO',
            value=0,
            typeStr='UInt32',
            pollInterval=1,
            localGet=self._getFrameCount,
            description='Frame in data file(s) for current open session in bytes.'))

        self.add(pr.LocalCommand(
            name='autoName',
            function=self._genFileName,
            description='Auto create data file name using data and time.'))

    def _setOpen(self,value,changed):
        """Set open state. Override in sub-class"""
        pass

    def _setBufferSize(self,value):
        """Set buffer size. Override in sub-class"""
        pass

    def _setMaxFileSize(self,value):
        """Set max file size. Override in sub-class"""
        pass

    def _getFileSize(self):
        """get current file size. Override in sub-class"""
        return(0)

    def _getFrameCount(self):
        """get current file frame count. Override in sub-class"""
        return(0)

    def _genFileName(self):
        """
        Auto create data file name based upon date and time.
        Preserve file's location in path.
        """
        idx = self.dataFile.value().rfind('/')

        if idx < 0:
            base = ''
        else:
            base = self.dataFile.value()[:idx+1]

        self.dataFile.set(base + datetime.datetime.now().strftime("data_%Y%m%d_%H%M%S.dat")) 

class RunControl(Device):
    """Special base class to control runs. TODO: Update comments."""

    def __init__(self, *, hidden=True, rates=None, states=None, cmd=None, **kwargs):
        """Initialize device class"""

        if rates is None:
            rates={1:'1 Hz', 10:'10 Hz'}

        if states is None:
            states={0:'Stopped', 1:'Running'}

        Device.__init__(self, hidden=hidden, **kwargs)

        value = [k for k,v in states.items()][0]

        self._thread = None
        self._cmd = cmd

        self.add(pr.LocalVariable(
            name='runState',
            value=value,
            mode='RW',
            disp=states,
            localSet=self._setRunState,
            description='Run state of the system.'))

        value = [k for k,v in rates.items()][0]

        self.add(pr.LocalVariable(
            name='runRate',
            value=value,
            mode='RW',
            disp=rates,
            localSet=self._setRunRate,
            description='Run rate of the system.'))

        self.add(pr.LocalVariable(
            name='runCount',
            value=0,
            typeStr='UInt32',
            mode='RO',
            pollInterval=1,
            description='Run Counter updated by run thread.'))

    def _setRunState(self,value,changed):
        """
        Set run state. Reimplement in sub-class.
        Enum of run states can also be overriden.
        Underlying run control must update runCount variable.
        """
        if changed:
            if self.runState.valueDisp() == 'Running':
                #print("Starting run")
                self._thread = threading.Thread(target=self._run)
                self._thread.start()
            elif self._thread is not None:
                #print("Stopping run")
                self._thread.join()
                self._thread = None

    def _setRunRate(self,value):
        """
        Set run rate. Reimplement in sub-class if neccessary.
        """
        pass

    def _run(self):
        #print("Thread start")
        self.runCount.set(0)

        while (self.runState.valueDisp() == 'Running'):
            time.sleep(1.0 / float(self.runRate.value()))
            if self._cmd is not None:
                self._cmd()

            self.runCount.set(self.runCount.value() + 1,write=False)
        #print("Thread stop")

