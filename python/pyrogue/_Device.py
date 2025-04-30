#-----------------------------------------------------------------------------
# Title      : PyRogue base module - Device Class
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
            groups='Enable',
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
            elif self._parent is self._root:
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

            # The following concept will trigger enable listeners
            # directly. This is causing lock contentions in practice
            # (epics as an example)

            #self._doUpdate()
            #for var in self._listeners:
            #    var._doUpdate()

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

        if parent is not root:
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
                 groups=None,
                 blockSize=None,
                 expand=False,
                 enabled=True,
                 defaults=None,
                 enableDeps=None,
                 hubMin=0,
                 hubMax=0,
                 guiGroup=None):


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
        pr.Node.__init__(self, name=name, hidden=hidden, groups=groups, description=description, expand=expand, guiGroup=guiGroup)

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
        if pack:
            hidden=True
        else:
            hidden=kwargs.pop('hidden', False)

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
                v.hidden = hidden
            elif isinstance(variables[0], str):
                self.variables[v].hidden = hidden

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
            for b,v in self._getBlocks(variable).items():
                if (force or b.stale):
                    b.startTransaction(rim.Write, check=checkEach, lowByte=v[0], highByte=v[1])

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
            for b,v in self._getBlocks(variable).items():
                b.startTransaction(rim.Verify, check=checkEach, lowByte=v[0], highByte=v[1])

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
            for b,v in self._getBlocks(variable).items():
                b.startTransaction(rim.Read, check=checkEach, lowByte=v[0], highByte=v[1])

        else:
            for block in self._blocks:
                if block.bulkEn:
                    block.startTransaction(rim.Read, check=checkEach)

            if recurse:
                for key,value in self.devices.items():
                    value.readBlocks(recurse=True, checkEach=checkEach)

    def checkBlocks(self, recurse=True, variable=None):
        """Check errors in all blocks and generate variable update notifications"""
        self._log.debug(f'Calling {self.path}._checkBlocks')

        with self.root.updateGroup():

            # Process local blocks
            if variable is not None:
                for b,v in self._getBlocks(variable).items():
                    b._checkTransaction()

            else:
                for block in self._blocks:
                    block._checkTransaction()

                if recurse:
                    for key,value in self.devices.items():
                            value.checkBlocks(recurse=True)

    def writeAndVerifyBlocks(self, force=False, recurse=True, variable=None, checkEach=False):
        """Perform a write, verify and check. Useful for committing any stale variables"""
        self.writeBlocks(force=force, recurse=recurse, variable=variable, checkEach=checkEach)
        self.verifyBlocks(recurse=recurse, variable=variable, checkEach=checkEach)
        self.checkBlocks(recurse=recurse, variable=variable)

    def readAndCheckBlocks(self, recurse=True, variable=None, checkEach=False):
        """Perform a read and check."""
        self.readBlocks(recurse=recurse, variable=variable, checkEach=checkEach)
        self.checkBlocks(recurse=recurse, variable=variable)

    def _rawTxnChunker(self, offset, data, base=pr.UInt, stride=4, wordBitSize=32, txnType=rim.Write, numWords=1):

        if not isinstance(base, pr.Model):
            base = base(wordBitSize)

        if offset + (numWords * stride) > self._size:
            raise pr.MemoryError(name=self.name, address=offset|self.address,
                                 msg='Raw transaction outside of device size')

        if base.bitSize > stride*8:
            raise pr.MemoryError(name=self.name, address=offset|self.address,
                                 msg='Called raw memory access with wordBitSize > stride')

        if txnType == rim.Write or txnType == rim.Post:
            if isinstance(data, bytearray):
                ldata = data
            elif isinstance(data, collections.abc.Iterable):
                ldata = b''.join(base.toBytes(word) for word in data)
            else:
                ldata = base.toBytes(data)

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

        if not isinstance(base, pr.Model):
            base = base(wordBitSize)

        with self._memLock:

            if posted: txn = rim.Post
            else: txn = rim.Write

            for _ in range(tryCount):
                self._clearError()
                self._rawTxnChunker(offset, data, base, stride, wordBitSize, txn)
                self._waitTransaction(0)

                if self._getError() == "": return
                elif posted: break
                self._log.warning("Retrying raw write transaction")

            # If we get here an error has occurred
            raise pr.MemoryError (name=self.name, address=offset|self.address, msg=self._getError())

    def _rawRead(self, offset, numWords=1, base=pr.UInt, stride=4, wordBitSize=32, data=None, tryCount=1):

        if not isinstance(base, pr.Model):
            base = base(wordBitSize)

        with self._memLock:
            for _ in range(tryCount):
                self._clearError()
                ldata = self._rawTxnChunker(offset, data, base, stride, wordBitSize, txnType=rim.Read, numWords=numWords)
                self._waitTransaction(0)

                if self._getError() == "":
                    if numWords == 1:
                        return base.fromBytes(ldata)
                    else:
                        return [base.fromBytes(ldata[i:i+stride]) for i in range(0, len(ldata), stride)]
                self._log.warning("Retrying raw read transaction")

            # If we get here an error has occurred
            raise pr.MemoryError (name=self.name, address=offset|self.address, msg=self._getError())


    def _getBlocks(self, variables):
        """
        Get a list of unique blocks from a list of Variables.
        The returned dictionary has the block as the key with each block associated
        with a list. The first list item is the low byte associated with the variable list,
        the second is the high byte associated with the variable list.
        Variables must belong to this device!
        """
        if isinstance(variables, pr.BaseVariable):
            variables = [variables]

        blocks = {}

        for v in variables:
            if v.parent is not self:
                raise DeviceError(
                    f'Variable {v.path} passed to {self.path}._getBlocks() is not a member of {self.path}')
            elif v._block is not None:

                if isinstance(v,pr.RemoteVariable):
                    lowByte  = math.floor(v.bitOffset[0] / 8)
                    highByte = math.floor((v.bitOffset[-1] + v.bitSize[-1] - 1) / 8)
                else:
                    lowByte  = None
                    highByte = None

                if v._block not in blocks:
                    blocks[v._block] = [lowByte, highByte]
                elif lowByte is not None and highByte is not None:
                    if lowByte  < blocks[v._block][0]: blocks[v._block][0] = lowByte
                    if highByte > blocks[v._block][1]: blocks[v._block][1] = highByte

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
            match = self._nodeMatch(varName)

            if match is not None:
                if not isinstance(match,list):
                    match = [match]

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

