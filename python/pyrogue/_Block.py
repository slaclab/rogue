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

        self._value = "Error in block with address {:#08x}: ".format(block.address)

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

        elif (self._error & 0xFF000000) == rogue.interfaces.memory.Unsupported:
            self._value += "Unsupported Transaction"

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
        self._verifyEn  = False
        self._bulkEn    = False
        self._doVerify  = False
        self._tranTime  = time.time()
        self._value     = None
        self._stale     = False
        self._verifyWr  = False

        # Setup logging
        self._log = pr.logInit(self,variable.name)

        # Add the variable
        self._addVariable(variable)

    def __repr__(self):
        return repr(self._variables)

    def set(self, var, value):
        pass

    def get(self, var, value):
        return None

    def backgroundTransaction(self,type):
        """
        Perform a background transaction
        """
        self._startTransaction(type)

    def blockingTransaction(self,type):
        """
        Perform a blocking transaction
        """
        self._log.debug("Setting block. Addr=0x{:08x}, Data={}".format(self._variables[0].offset,self._bData))
        self._startTransaction(type)
        self._checkTransaction(update=False)
        self._log.debug("Done block. Addr=0x{:08x}, Data={}".format(self._variables[0].offset,self._bData))

    @property
    def offset(self):
        return self._variables[0].offset

    @property
    def address(self):
        if len(self._variables) == 0:
            return 0
        elif isinstance(self,rogue.interfaces.memory.Master):
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

    @property
    def bulkEn(self):
        return self._bulkEn

    def _waitTransaction(self):
        pass

    def _addVariable(self,var):
        """
        Add a variable to the block
        """
        with self._lock:
            if not isinstance(var, pr.BaseCommand):
                self._bulkEn = True
                
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
        if self._localGet is not None:
            with self._lock:
                dev   = var.parent
                value = 0

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

            ba = var._base.toBlock(value, sum(var.bitSize))

            # Access is fully byte aligned
            if len(var.bitOffset) == 1 and (var.bitOffset[0] % 8) == 0 and (var.bitSize[0] % 8) == 0:
                self._bData[var.bitOffset[0]//8:(var.bitOffset[0]+var.bitSize[0])//8] = ba

            # Bit level access
            else:
                bit = 0
                for x in range(0, len(var.bitOffset)):
                    for y in range(0, var.bitSize[x]):
                        setBitToBytes(self._bData,var.bitOffset[x]+y,getBitFromBytes(ba,bit))
                        bit += 1

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
            if len(var.bitOffset) == 1 and (var.bitOffset[0] % 8) == 0 and (var.bitSize[0] % 8) == 0:
                return var._base.fromBlock(self._bData[int(var.bitOffset[0]/8):int((var.bitOffset[0]+var.bitSize[0])/8)])

            # Bit level access
            else:
                ba = bytearray(int(math.ceil(float(sum(var.bitSize)) / 8.0)))

                bit = 0
                for x in range(0, len(var.bitOffset)):
                    for y in range(0, var.bitSize[x]):
                        setBitToBytes(ba,bit,getBitFromBytes(self._bData,var.bitOffset[x]+y))
                        bit += 1

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

        with self._cond:
            self._waitTransaction()

            # Return false if offset does not match
            if len(self._variables) != 0 and var.offset != self._variables[0].offset:
                return False
    
            # Range check
            if var.varBytes > self._maxSize:
                raise BlockError(self,"Variable {} size {} exceeds maxSize {}".format(var.name,var.varBytes,self._maxSize))

            # Link variable to block
            var._block = self
            
            if not isinstance(var, pr.BaseCommand):
                self._bulkEn = True
                
            self._variables.append(var)

            self._log.debug("Adding variable {} to block {} at offset 0x{:02x}".format(var.name,self.name,self.offset))

            # If variable modes mismatch, set block to read/write
            if var.mode != self._mode:
                self._mode = 'RW'

            # Adjust size to hold variable. Underlying class will adjust
            # size to align to minimum protocol access size 
            if self._size < var.varBytes:
                self._bData.extend(bytearray(var.varBytes - self._size))
                self._vData.extend(bytearray(var.varBytes - self._size))
                self._mData.extend(bytearray(var.varBytes - self._size))
                self._size = var.varBytes

            # Update verify mask
            if var.mode == 'RW' and var.verify is True:
                self._verifyEn = True

                for x in range(0, len(var.bitOffset)):
                    for y in range(0, var.bitSize[x]):
                        setBitToBytes(self._mData,var.bitOffset[x]+y,1)

            return True

    def _startTransaction(self,type):
        """
        Start a transaction.
        """
        # Check for invalid combinations or disabled device
        if (self._variables[0].parent.enable.value() is not True) or \
           (type == rogue.interfaces.memory.Write  and (self.mode == 'RO')) or \
           (type == rogue.interfaces.memory.Post   and (self.mode == 'RO')) or \
           (type == rogue.interfaces.memory.Read   and (self.mode == 'WO')) or \
           (type == rogue.interfaces.memory.Verify and (self.mode == 'WO' or \
                                                        self.mode == 'RO' or \
                                                        self._verifyWr == False)):
            return

        self._log.debug('_startTransaction type={}'.format(type))

        tData = None

        with self._cond:
            self._waitTransaction()

            self._log.debug('len bData = {}, vData = {}, mData = {}'.format(len(self._bData), len(self._vData), len(self._mData)))

            # Track verify after writes. 
            # Only verify blocks that have been written since last verify
            if type == rogue.interfaces.memory.Write:
                self._verifyWr = self._verifyEn
                  
            # Setup transaction
            self._doVerify = (type == rogue.interfaces.memory.Verify)
            self._doUpdate = (type == rogue.interfaces.memory.Read)
            self._error    = 0

            # Set data pointer
            tData = self._vData if self._doVerify else self._bData

            # Start transaction
            self._reqTransaction(self._variables[0].offset,tData,type)

            # Start timer after return
            self._tranTime = time.time()

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

            # Do verify
            if self._doVerify:
                self._verifyWr = False
                for x in range(0,self._size):
                    if (self._vData[x] & self._mData[x]) != (self._bData[x] & self._mData[x]):
                        self._error = rogue.interfaces.memory.VerifyError
                        break

            if self._error == 0:
                self._stale = False
            else:
                self._doUpdate = False

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

