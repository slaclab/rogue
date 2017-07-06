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
import rogue.interfaces.memory as rim
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
        block.error = 0

        self._value = "Error in block with address {:#08x}: ".format(block.address)

        if hasattr(block,'_variables'):
            self._value += "Block Variables: {}. ".format(block._variables)

        if msg is not None:
            self._value += msg

        elif (self._error & 0xFF000000) == rim.TimeoutError:
            self._value += "Timeout after {} seconds".format(block.timeout)

        elif (self._error & 0xFF000000) == rim.VerifyError and hasattr(block,'_bData'):
            bStr = ''.join('0x{:02x} '.format(x) for x in block._bData)
            vStr = ''.join('0x{:02x} '.format(x) for x in block._vData)
            mStr = ''.join('0x{:02x} '.format(x) for x in block._mData)
            self._value += "Verify error. Local={}, Verify={}, Mask={}".format(bStr,vStr,mStr)

        elif (self._error & 0xFF000000) == rim.AddressError:
            self._value += "Address error"

        elif (self._error & 0xFF000000) == rim.SizeError:
            self._value += "Size error. Size={}".format(block._size)

        elif (self._error & 0xFF000000) == rim.AxiTimeout:
            self._value += "AXI timeout"

        elif (self._error & 0xFF000000) == rim.AxiFail:
            self._value += "AXI fail"

        elif (self._error & 0xFF000000) == rim.Unsupported:
            self._value += "Unsupported Transaction"

        else:
            self._value += "Unknown error 0x{:02x}".format(self._error)

    def __str__(self):
        return repr(self._value)


class BaseBlock(object):

    def __init__(self, name, mode, device):

        self._mode      = mode
        self._device    = device
        self._lock      = threading.RLock()
        self._doUpdate  = False

        # Setup logging
        self._log = pr.logInit(self,name)


    def __repr__(self):
        return repr(self.name)


    def backgroundTransaction(self,type):
        """
        Perform a background transaction
        """
        self._startTransaction(type)

    def blockingTransaction(self,type):
        """
        Perform a blocking transaction
        """
        self._startTransaction(type)
        self._checkTransaction(update=False)

    @property
    def name(self):
        return self._name

    @property
    def mode(self):
        return self._mode


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


    def _waitTransaction(self):
        pass


    def _startTransaction(self,type):
        """
        Start a transaction.
        """
        with self._lock:
            self._doUpdate = (type == rim.Read)

    def _checkTransaction(self,update):
        """
        Check status of block.
        If update=True notify variables if read
        """
        doUpdate = False
        with self._lock:
            self._waitTransaction()

            # Updated
            doUpdate = update and self._doUpdate
            self._doUpdate = False

            # Error
            if self.error > 0:
                raise BlockError(self)

        # Update variables outside of lock
        if doUpdate: self._updated()

    def _updated(self):
        pass


class LocalBlock(BaseBlock):
    def __init__(self, variable, localSet, localGet, value):
        BaseBlock.__init__(self, name=variable.name, mode=variable.mode)

        self._localSet = localSet
        self._localGet = localGet
        self._variable = variable
        self._value = value


    @property
    def value(self):
        return self._value
        

    def set(self, value):
        with self._lock:
            changed = self._value != value
            self._value = value

            # If a setFunction exists, call it (Used by local variables)
            if self._localSet is not None:

                # Possible args
                pargs = {'dev' : self._device, 'var' : self._variable, 'value' : self._value, 'changed' : changed}

                pr.varFuncHelper(self._localSet, pargs, self._log, self._variable.path)

    def get(self):
        if self._localGet is not None:
            with self._lock:

                # Possible args
                pargs = {'dev' : self._device, 'var' : self._variable}

                self._value = pr.varFuncHelper(self._localGet,pargs, self._log, self._variable.path)

        return self._value

    def _updated(self):
        self._variable._updated()


class RemoteBlock(BaseBlock, rim.Master):
    def __init__(self, name, mode, device, offset=0):
        
        rim.Master__init__(self)
        self._setSlave(device)
        
        BaseBlock.__init__(self, name=name, mode=mode, device=device)
        self._verifyEn  = False
        self._bulkEn    = False
        self._doVerify  = False
        self._stale     = False
        self._verifyWr  = False
        self._bData     = bytearray()
        self._vData     = bytearray()
        self._mData     = bytearray()
        self._size      = 0
        self._offset    = offset
        self._minSize   = self._reqMinAccess()
        self._maxSize   = self._reqMaxAccess()

        if self._minSize == 0 or self._maxSize == 0:
            raise BlockError(self,"Invalid min/max size.")

    @property
    def stale(self):
        return self._stale

    @property
    def offset(self):
        return self._offset

    @property
    def address(self):
        return self._offset | self._reqOffset()

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
        return self._setError(value)

    @property
    def bulkEn(self):
        return self._bulkEn


    def _startTransaction(self,type):
        """
        Start a transaction.
        """
        # Check for invalid combinations or disabled device
        if (self._device.enable.value() is not True) or \
           (type == rim.Write  and (self.mode == 'RO')) or \
           (type == rim.Post   and (self.mode == 'RO')) or \
           (type == rim.Read   and (self.mode == 'WO')) or \
           (type == rim.Verify and (self.mode == 'WO' or \
                                    self.mode == 'RO' or \
                                    self._verifyWr == False)):
            return

        self._log.debug(f'_startTransaction type={type}')

        tData = None

        with self._lock:
            self._waitTransaction()

            self._log.debug(f'len bData = {len(self._bData)}, vData = {len(self._vData)}, mData = {len(self._mData)}')

            # Track verify after writes. 
            # Only verify blocks that have been written since last verify
            if type == rim.Write:
                self._verifyWr = self._verifyEn
                  
            # Setup transaction
            self._doVerify = (type == rim.Verify)
            self._doUpdate = (type == rim.Read)

            # Set data pointer
            tData = self._vData if self._doVerify else self._bData

            # Start transaction
            self._reqTransaction(self.offset,tData,type)
    

class RegisterBlock(RemoteBlock):
    """Internal memory block holder"""

    def __init__(self, variable):
        """
        Initialize memory block class.
        Pass initial variable.
        """
        super().__init__(name=variable.name, mode=variable.mode, device=variable.parent, offset=variable.offset)

        self._variables = []
        self._addVariable(variable)

    def __repr__(self):
        return repr(self._variables)

    def blockingTransaction(self, type):
        # Call is same as BaseBlock, just add logging
        self._log.debug(f"Setting block. Addr={self.offset:#08x}, Data={self._bData}")
        BaseBlock.blockingTransaction(self, type)
        self._log.debug(f"Done block. Addr={self._offset:08x}, Data={self._bData}")


    def set(self, var, value):
        """
        Update block with bitSize bits from passed byte array.
        Offset sets the starting point in the block array.
        """
        with self._lock:
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
        with self._lock:
            self._waitTransaction()

            # Error
            if self.error > 0:
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

    def _addVariable(self,var):
        """
        Add a variable to the block. Called from Device for BlockMemory
        """

        with self._lock:
            self._waitTransaction()

            # Return false if offset does not match
            if len(self._variables) != 0 and var.offset != self._variables[0].offset:
                return False
    
            # Range check
            if var.varBytes > self._maxSize:
                raise BlockError(self,f"Variable {var.name} size {var.varBytes} exceeds maxSize {self._maxSize}")

            # Link variable to block
            var._block = self
            
            if not isinstance(var, pr.BaseCommand):
                self._bulkEn = True
                
            self._variables.append(var)

            self._log.debug(f"Adding variable {var.name} to block {self.name} at offset {self.offset:#02x}")

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



    def _doneTransaction(self,tid,error):
        """
        Callback for when transaction is complete
        """
        with self._lock:

            # Do verify
            if self._doVerify:
                self._verifyWr = False
                for x in range(0,self._size):
                    if (self._vData[x] & self._mData[x]) != (self._bData[x] & self._mData[x]):
                        self.error = rim.VerifyError
                        break

            if self.error == 0:
                self._stale = False
            else:
                self._doUpdate = False

                
class MemoryBlock(RemoteBlock):

    def __init__(self, name, mode, device, offset):
        """device is expected to be a MemoryDevice"""

        super().__init__(name=name, mode=mode, device=device, offset=offset)

    def set(self, values):

        with self._lock:
            self._waitTransaction()            
            size = bytearray(len(values)*self._dev._stride)

            if size > self._maxSize:
                raise BlockError(self, "Tried to call set with transaction that is too big")

            self._bData = b''.join( self._dev._base.toBlock(v, self._dev._stride) for v in values)
            self._vData = bytearray(len(self._bData))


    def _doneTransaction(self, tid, error):
        with self._lock:
            if self._dev.Verify.value():
                self._verifyWr = False
                if self._vData != self._bData:
                    self.error = rim.VerifyError
                    break

            if self.error == 0 and self._verifyWr is False:
                self._bData = bytearray()
                self._vData = bytearray()
                
                


class RawBlock(rim.Master):

    def __init__(self, slave):
        rim.Master.__init__(self)
        self._setSlave(slave)

        self._lock      = threading.RLock()
        self._address   = 0
        self._size      = 0

    @property
    def address(self):
        return self._address | self._reqOffset()


    def write(self,address,value):
        if isinstance(value,bytearray):
            ldata = value
        else:
            ldata = value.to_bytes(4,'little',signed=False)

        self._doTransaction(rim.Write, address, ldata)

    def read(self,address,bdata=None):
        if bdata:
            ldata = bdata
        else:
            ldata = bytearray(4)

        self._doTransaction(rim.Read, address, ldata)

        if bdata is None:
            return int.from_bytes(ldata,'little',signed=False)

    def _doTransaction(self, type, address, bdata):

        with self._lock:
            self._waitTransaction()

            # Setup transaction
            self._size     = len(bdata)
            self._address  = address

        # Start transaction outside of lock
        self._reqTransaction(address,bdata,type)

        # wait for completion
        self._waitTransaction()

        # Error
        if self.error > 0:
            raise BlockError(self)


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

