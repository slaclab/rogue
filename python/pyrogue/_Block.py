#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Title      : PyRogue base module - Block Class
#-----------------------------------------------------------------------------
# File       : pyrogue/_Block.py
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
import threading
import time
import math
import textwrap
import pyrogue as pr
import inspect

class BlockError(Exception):
    """ Exception for memory access errors."""

    def __init__(self,block,msg=None):
        self._error = block.error
        block._error = 0

        self._value = "Error in block with address 0x{:02x}: ".format(block.address)

        if hasattr(block,'_variables'):
            self._value += "Block Variables: {}. ".format(block._variables)

        if msg is not None:
            self._value += msg

        elif (self._error & 0xFF000000) == rogue.interfaces.memory.TimeoutError:
            self._value += "Timeout after {} seconds".format(block.timeout)

        elif (self._error & 0xFF000000) == rogue.interfaces.memory.VerifyError and hasattr(block,'_bData'):
            bStr = ''.join('0x{:02x} '.format(x) for x in block._bData)
            vStr = ''.join('0x{:02x} '.format(x) for x in block._vData)
            mStr = ''.join('0x{:02x} '.format(x) for x in block._mData)
            self._value += "Verify error. Local={}, Verify={}, Mask={}".format(bStr,vStr,mStr)

        elif (self._error & 0xFF000000) == rogue.interfaces.memory.AddressError:
            self._value += "Address error"

        elif (self._error & 0xFF000000) == rogue.interfaces.memory.SizeError:
            self._value += "Size error. Size={}".format(block._size)

        elif (self._error & 0xFF000000) == rogue.interfaces.memory.AxiTimeout:
            self._value += "AXI timeout"

        elif (self._error & 0xFF000000) == rogue.interfaces.memory.AxiFail:
            self._value += "AXI fail"

        else:
            self._value += "Unknown error 0x{:02x}".format(self._error)

    def __str__(self):
        return repr(self._value)


class BaseBlock(object):

    def __init__(self, variable):
        self._mode      = variable.mode
        self._bData     = bytearray()
        self._vData     = bytearray()
        self._mData     = bytearray()
        self._size      = 0
        self._variables = []
        self._timeout   = 1.0
        self._lock      = threading.Lock()
        self._cond      = threading.Condition(self._lock)
        self._error     = 0
        self._doUpdate  = False
        self._doVerify  = False
        self._tranTime  = time.time()
        self._value     = None
        self._stale     = False

        # Setup logging
        self._log = pr.logInit(self,variable.name)

        # Add the variable
        self._addVariable(variable)

    def __repr__(self):
        return repr(self._variables)

    def set(self, var, value):
        self._value = value
        self._stale = True

    def get(self, var, value):
        return self._value

    def backgroundTransaction(self,type):
        """
        Perform a background transaction
        """
        if (type == rogue.interfaces.memory.Write  and (self.mode == 'CMD' or self.mode == 'WO' or self.mode == 'RW')) or \
           (type == rogue.interfaces.memory.Post   and (self.mode == 'CMD' or self.mode == 'WO' or self.mode == 'RW')) or \
           (type == rogue.interfaces.memory.Read   and (self.mode == 'CMD' or self.mode == 'RO' or self.mode == 'RW')) or  \
           (type == rogue.interfaces.memory.Verify and (self.mode == 'CMD' or self.mode == 'RW')):
            self._startTransaction(type)

    def blockingTransaction(self,type):
        """
        Perform a blocking transaction
        """
        if (type == rogue.interfaces.memory.Write  and (self.mode == 'CMD' or self.mode == 'WO' or self.mode == 'RW')) or \
           (type == rogue.interfaces.memory.Post   and (self.mode == 'CMD' or self.mode == 'WO' or self.mode == 'RW')) or \
           (type == rogue.interfaces.memory.Read   and (self.mode == 'CMD' or self.mode == 'RO' or self.mode == 'RW')) or  \
           (type == rogue.interfaces.memory.Verify and (self.mode == 'CMD' or self.mode == 'RW')):

            self._log.debug("Setting block. Addr=0x{:02x}, Data={}".format(self._variables[0].offset,self._bData))
            self._startTransaction(type)
            self._checkTransaction(update=False)
            self._log.debug("Done block. Addr=0x{:02x}, Data={}".format(self._variables[0].offset,self._bData))

    @property
    def offset(self):
        return self._variables[0].offset

    @property
    def address(self):
        if isinstance(self,rogue.interfaces.memory.Master):
            return self._variables[0].offset | self._reqOffset()
        else:
            return self._variables[0].offset

    @property
    def name(self):
        return self._variables[0].name

    @property
    def mode(self):
        return self._mode

    @property
    def value(self):
        return self._value

    @property
    def stale(self):
        return self._stale

    @property
    def timeout(self):
        return self._timeout

    @timeout.setter
    def timeout(self,value):
        with self._cond:
            self._waitTransaction()
            self._timeout = value

    @property
    def error(self):
        return self._error

    def _waitTransaction(self):
        pass

    def _addVariable(self,var):
        """
        Add a variable to the block
        """
        with self._lock:
            if len(self._variables) == 0:
                self._variables.append(var)
                return True;
            else:
                return False

    def _startTransaction(self,type):
        """
        Start a transaction.
        """
        with self._lock:
            self._doUpdate = (type == rogue.interfaces.memory.Read)

    def _checkTransaction(self,update):
        """
        Check status of block.
        If update=True notify variables if read
        """
        doUpdate = False
        with self._cond:
            self._waitTransaction()

            # Updated
            doUpdate = update and self._doUpdate
            self._doUpdate = False

            # Error
            if self._error > 0:
                raise BlockError(self)

        # Update variables outside of lock
        if doUpdate: self._updated()
        self._stale = False

    def _updated(self):
        for variable in self._variables:
            variable._updated()


class LocalBlock(BaseBlock):
    def __init__(self, variable, localSet, localGet, value):
        self._localSet = localSet
        self._localGet = localGet

        BaseBlock.__init__(self,variable)
        self._value = value

    def set(self, var, value):
        with self._lock:
            changed = self._value != value
            self._value = value
            dev = var.parent
            self._stale = True

            # If a setFunction exists, call it (Used by local variables)        
            if self._localSet is not None:
                if callable(self._localSet):
                    # Function takes changed arg
                    if len(inspect.signature(self._localSet).parameters) == 4:
                        self._localSet(dev, var, value, changed)
                    else:
                        self._localSet(dev, var, value)
                else:
                    exec(textwrap.dedent(self._localSet))

    def get(self, var):
        with self._lock:
            dev   = var.parent
            value = 0

            if self._localGet is not None:
                if callable(self._localGet):
                    self._value = self._localGet(dev,var)
                else:
                    ns = locals()
                    exec(textwrap.dedent(self._localGet),ns)
                    self._value = ns['value']

            return self._value


class MemoryBlock(BaseBlock, rogue.interfaces.memory.Master):
    """Internal memory block holder"""

    def __init__(self, variable):
        """
        Initialize memory block class.
        Pass initial variable.
        """
        rogue.interfaces.memory.Master.__init__(self)
        self._setSlave(variable.parent)

        self._minSize = self._reqMinAccess()
        self._maxSize = self._reqMaxAccess()

        if self._minSize == 0 or self._maxSize == 0:
            raise BlockError(self,"Invalid min/max size.")

        BaseBlock.__init__(self,variable)


    def set(self, var, value):
        """
        Update block with bitSize bits from passed byte array.
        Offset sets the starting point in the block array.
        """
        with self._cond:
            self._waitTransaction()
            self._value = value
            self._stale = True

            ba = var._base.toBlock(value, var.bitSize)

            # Access is fully byte aligned
            if (var.bitOffset % 8) == 0 and (var.bitSize % 8) == 0:
                self._bData[var.bitOffset//8:(var.bitOffset+var.bitSize)//8] = ba

            # Bit level access
            else:
                for x in range(0, var.bitSize):
                    setBitToBytes(self._bData,x+var.bitOffset,getBitFromBytes(ba,x))

    def get(self, var):
        """
        Get bitSize bytes from block data.
        Offset sets the starting point in the block array.
        bytearray is returned
        """
        with self._cond:
            self._waitTransaction()

            # Error
            if self._error > 0:
                raise BlockError(self)

            # Access is fully byte aligned
            if (var.bitOffset % 8) == 0 and (var.bitSize % 8) == 0:
                return var._base.fromBlock(self._bData[int(var.bitOffset/8):int((var.bitOffset+var.bitSize)/8)])

            # Bit level access
            else:
                ba = bytearray(int(var.bitSize / 8))
                if (var.bitSize % 8) > 0: ba.extend(bytearray(1))
                for x in range(0,var.bitSize):
                    setBitToBytes(ba,x,getBitFromBytes(self._bData,x+var.bitOffset))
                return var._base.fromBlock(ba)

    def _waitTransaction(self):
        """
        Wait while a transaction is pending.
        Set an error on timeout.
        Lock must be held before calling this method
        """
        lid = self._getId()
        while lid > 0:
            self._cond.wait(.01)
            if self._getId() == lid and (time.time() - self._tranTime) > self._timeout:
                self._endTransaction()
                self._error = rogue.interfaces.memory.TimeoutError
                break
            lid = self._getId()

    def _addVariable(self,var):
        """
        Add a variable to the block. Called from Device for BlockMemory
        """

        # Align variable address to block alignment
        varShift = var.offset % self._minSize
        var._offset -= varShift
        var._bitOffset += (varShift * 8)

        with self._cond:
            self._waitTransaction()

            # Return false if offset does not match
            if len(self._variables) != 0 and var.offset != self._variables[0].offset:
                return False

            # Compute the max variable address to determine required size of block
            varBytes = int(math.ceil(float(var.bitOffset + var.bitSize) / float(self._minSize*8))) * self._minSize

            # Link variable to block
            var._block = self
            self._variables.append(var)

            # If variable modes mismatch, set to read/write
            if var.mode != self._mode:
                self._mode = 'RW'

            # Adjust size to hold variable. Underlying class will adjust
            # size to align to minimum protocol access size 
            if self._size < varBytes:
                self._bData.extend(bytearray(varBytes - self._size))
                self._vData.extend(bytearray(varBytes - self._size))
                self._mData.extend(bytearray(varBytes - self._size))
                self._size = varBytes

            # Update verify mask
            if var.mode == 'RW' and var.verify is True:
                for x in range(var.bitOffset,var.bitOffset+var.bitSize):
                    setBitToBytes(self._mData,x,1)

            return True

    def _startTransaction(self,type):
        """
        Start a transaction.
        """
        self._log.debug('_startTransaction type={}'.format(type))

        tData = None

        with self._cond:
            self._waitTransaction()

            # Return if not enabled
            if self._variables[0].parent.enable.value() is not True:
                return
            
            self._log.debug('len bData = {}, vData = {}, mData = {}'.format(len(self._bData), len(self._vData), len(self._mData)))
                  
            # Setup transaction
            self._doVerify = (type == rogue.interfaces.memory.Verify)
            self._doUpdate = (type == rogue.interfaces.memory.Read)
            self._error    = 0
            self._tranTime = time.time()

            # Set data pointer
            tData = self._vData if self._doVerify else self._bData

        # Start transaction outside of lock
        self._reqTransaction(self._variables[0].offset,tData,type)

    def _doneTransaction(self,tid,error):
        """
        Callback for when transaction is complete
        """
        with self._lock:

            # Make sure id matches
            if tid != self._getId():
                return

            # Clear transaction state
            self._endTransaction()
            self._error = error

            # Check for error
            if error > 0:
                self._doUpdate = False

            # Do verify
            elif self._doVerify:
                for x in range(0,self._size):
                    if (self._vData[x] & self._mData[x]) != (self._bData[x] & self._mData[x]):
                        self._error = rogue.interfaces.memory.VerifyError
                        break

            # Notify waiters
            self._cond.notify()


class RawBlock(rogue.interfaces.memory.Master):

    def __init__(self, slave):
        rogue.interfaces.memory.Master.__init__(self)
        self._setSlave(slave)

        self._timeout   = 1.0
        self._lock      = threading.Lock()
        self._cond      = threading.Condition(self._lock)
        self._error     = 0
        self._address   = 0
        self._size      = 0
        self._tranTime  = time.time()

    @property
    def address(self):
        return self._addr | self._reqOffset()

    @property
    def timeout(self):
        return self._timeout

    @timeout.setter
    def timeout(self,value):
        with self._cond:
            self._waitTransaction()
            self._timeout = value

    def write(self,address,value):
        if isinstance(value,bytearray):
            ldata = value
        else:
            ldata = value.to_bytes(4,'little',signed=False)

        self._doTransaction(rogue.interfaces.memory.Write, address, ldata)

    def read(self,address,bdata=None):
        if bdata:
            ldata = bdata
        else:
            ldata = bytearray(4)

        self._doTransaction(rogue.interfaces.memory.Read, address, ldata)

        if bdata is None:
            return int.from_bytes(ldata,'little',signed=False)

    def _doTransaction(self, type, address, bdata):

        with self._cond:
            self._waitTransaction()

            # Setup transaction
            self._size     = len(bdata)
            self._address  = address
            self._error    = 0
            self._tranTime = time.time()

        # Start transaction outside of lock
        self._reqTransaction(address,bdata,type)

        # wait for completion
        with self._cond:
            self._waitTransaction()

            # Error
            if self._error > 0:
                raise BlockError(self)

    def _waitTransaction(self):
        """
        Wait while a transaction is pending.
        Set an error on timeout.
        Lock must be held before calling this method
        """
        lid = self._getId()
        while lid > 0:
            self._cond.wait(.01)
            if self._getId() == lid and (time.time() - self._tranTime) > self._timeout:
                self._endTransaction()
                self._error = rogue.interfaces.memory.TimeoutError
                break
            lid = self._getId()

    def _doneTransaction(self,tid,error):
        """
        Callback for when transaction is complete
        """
        with self._lock:

            # Make sure id matches
            if tid != self._getId():
                return

            # Clear transaction state
            self._endTransaction()
            self._error = error

            # Notify waiters
            self._cond.notify()


def setBitToBytes(ba, bitOffset, value):
    """
    Set a bit to a specific location in an array of bytes
    """
    byte = int(bitOffset / 8)
    bit  = bitOffset % 8

    if value > 0:
        ba[byte] |= (1 << bit)
    else:
        ba[byte] &= (0xFF ^ (1 << bit))


def getBitFromBytes(ba, bitOffset):
    """
    Get a bit from a specific location in an array of bytes
    """
    byte = int(bitOffset / 8)
    bit  = bitOffset % 8

    return ((ba[byte] >> bit) & 0x1)

