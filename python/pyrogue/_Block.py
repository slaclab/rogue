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


class MemoryError(Exception):
    """ Exception for memory access errors."""

    def __init__(self, name, address, error=0, msg=None, size=0):

        self._value = "Memory Error for {} at address {:#08x}: ".format(name,address)

        if (error & 0xFF000000) == rogue.interfaces.memory.TimeoutError:
            self._value += "Timeout."

        elif (error & 0xFF000000) == rogue.interfaces.memory.VerifyError:
            self._value += "Verify error."

        elif (error & 0xFF000000) == rogue.interfaces.memory.AddressError:
            self._value += "Address error."

        elif (error & 0xFF000000) == rogue.interfaces.memory.SizeError:
            self._value += "Size error. Size={}.".format(size)

        elif (error & 0xFF000000) == rogue.interfaces.memory.AxiTimeout:
            self._value += "AXI timeout."

        elif (error & 0xFF000000) == rogue.interfaces.memory.AxiFail:
            self._value += "AXI fail."

        elif (error & 0xFF000000) == rogue.interfaces.memory.Unsupported:
            self._value += "Unsupported Transaction."

        else:
            self._value += "Unknown error 0x{:02x}.".format(error)

        if msg is not None:
            self._value += (' ' + msg)

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
        self._lock      = threading.RLock()
        self._doUpdate  = False
        self._verifyEn  = False
        self._bulkEn    = False
        self._doVerify  = False
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
        return 0

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
        return 0

    @timeout.setter
    def timeout(self,value):
        pass

    @property
    def error(self):
        return 0

    @error.setter
    def error(self,value):
        pass

    @property
    def bulkEn(self):
        return self._bulkEn

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

    def _blockWait(self):
        pass

    def _checkTransaction(self,update):
        """
        Check status of block.
        If update=True notify variables if read
        """
        doUpdate = False
        with self._lock:
            self._blockWait()

            # Error
            err = self.error
            self.error = 0

            if err > 0:
                raise MemoryError(name=self.name, address=self.address, error=err, size=self._size)

            if self._doVerify:
                self._verifyWr = False

                for x in range(0,self._size):
                    if (self._vData[x] & self._mData[x]) != (self._bData[x] & self._mData[x]):
                        msg  = ('Local='    + ''.join('0x{:02x} '.format(x) for x in block._bData))
                        msg += ('. Verify=' + ''.join('0x{:02x} '.format(x) for x in block._vData))
                        msg += ('. Mask='   + ''.join('0x{:02x} '.format(x) for x in block._mData))

                        raise MemoryError(name=self.name, address=self.address, error=rogue.interfaces.memory.VerifyError, msg=msg, size=self._size)

            # Updated
            doUpdate = update and self._doUpdate
            self._doUpdate = False

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

            # If a setFunction exists, call it (Used by local variables)
            if self._localSet is not None:

                # Possible args
                pargs = {'dev' : var.parent, 'var' : var, 'value' : self._value, 'changed' : changed}

                pr.varFuncHelper(self._localSet, pargs, self._log, var.path)

    def get(self, var):
        if self._localGet is not None:
            with self._lock:

                # Possible args
                pargs = {'dev' : var.parent, 'var' : var}

                self._value = pr.varFuncHelper(self._localGet,pargs, self._log, var.path)

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
            raise MemoryError(name=self.name, address=self.address, msg="Invalid min/max size")

        BaseBlock.__init__(self,variable)

    @property
    def address(self):
        return self._variables[0].offset | self._reqAddress()

    @property
    def timeout(self):
        return float(self._getTimeout()) / 1000000.0

    @timeout.setter
    def timeout(self,value):
        self._setTimeout(value*1000000)

    @property
    def error(self):
        return self._getError()

    @error.setter
    def error(self,value):
        self._setError(value)

    def set(self, var, value):
        """
        Update block with bitSize bits from passed byte array.
        Offset sets the starting point in the block array.
        """
        with self._lock:
            self._blockWait()
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
        with self._lock:
            self._blockWait()

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

    def _addVariable(self,var):
        """
        Add a variable to the block. Called from Device for BlockMemory
        """

        with self._lock:
            self._blockWait()

            # Return false if offset does not match
            if len(self._variables) != 0 and var.offset != self._variables[0].offset:
                return False
    
            # Range check
            if var.varBytes > self._maxSize:
                msg = 'Variable {} size {} exceeds maxSize {}'.format(var.name,var.varBytes,self._maxSize)
                raise MemoryError(name=self.name, address=self.address, msg=msg)

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

        with self._lock:
            self._blockWait()

            self._log.debug('len bData = {}, vData = {}, mData = {}'.format(len(self._bData), len(self._vData), len(self._mData)))

            # Track verify after writes. 
            # Only verify blocks that have been written since last verify
            if type == rogue.interfaces.memory.Write:
                self._verifyWr = self._verifyEn
                  
            # Setup transaction
            self._doVerify = (type == rogue.interfaces.memory.Verify)
            self._doUpdate = (type == rogue.interfaces.memory.Read)

            # Set data pointer
            tData = self._vData if self._doVerify else self._bData

            # Start transaction
            self._reqTransaction(self._variables[0].offset,tData,type)

    def _blockWait(self):
        self._waitTransaction()

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

