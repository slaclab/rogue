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


class MemoryError(Exception):
    """ Exception for memory access errors."""

    def __init__(self, *, name, address, error=0, msg=None, size=0):

        self._value = f"Memory Error for {name} at address {address:#08x} "

        if (error & 0xFF000000) == rim.TimeoutError:
            self._value += "Timeout."

        elif (error & 0xFF000000) == rim.VerifyError:
            self._value += "Verify error."

        elif (error & 0xFF000000) == rim.AddressError:
            self._value += "Address error."

        elif (error & 0xFF000000) == rim.SizeError:
            self._value += f"Size error. Size={size}."

        elif (error & 0xFF000000) == rim.AxiTimeout:
            self._value += "AXI timeout."

        elif (error & 0xFF000000) == rim.AxiFail:
            self._value += "AXI fail."

        elif (error & 0xFF000000) == rim.Unsupported:
            self._value += "Unsupported Transaction."

        elif error != 0:
            self._value += f"Unknown error {error:#02x}."

        if msg is not None:
            self._value += (' ' + msg)

    def __str__(self):
        return repr(self._value)


class BaseBlock(object):

    def __init__(self, *, name, mode, device):

        self._name      = name
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
        self.startTransaction(type, check=False)

    def blockingTransaction(self,type):
        """
        Perform a blocking transaction
        """
        self.startTransaction(type, check=True)

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

    @property
    def bulkEn(self):
        return True

    def startTransaction(self,type, check=False):
        """
        Start a transaction.
        """
        with self._lock:
            self._doUpdate = True

    def _checkTransaction(self):
        """
        Check status of block.
        If update=True notify variables if read
        """
        doUpdate = False
        with self._lock:
            doUpdate = self._doUpdate
            self._doUpdate = False

        # Update variables outside of lock
        if doUpdate: self.updated()
        
    def updated(self):
        pass

    def _addVariable(self,var):
        return False

class LocalBlock(BaseBlock):
    def __init__(self, *, variable, localSet, localGet, value):
        BaseBlock.__init__(self, name=variable.path, mode=variable.mode, device=variable.parent)

        self._localSet = localSet
        self._localGet = localGet
        self._variable = variable
        self._variables = [variable] # Used by poller
        self._value = value

    @property
    def value(self):
        return self._value
        
    @property
    def stale(self):
        return False

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

    def updated(self):
        self._variable.updated()


class RemoteBlock(BaseBlock, rim.Master):
    def __init__(self, *, variable):
     
        rim.Master.__init__(self)
        self._setSlave(variable.parent)
        
        BaseBlock.__init__(self, name=variable.path, mode=variable.mode, device=variable.parent)
        self._verifyEn  = False
        self._bulkEn    = False
        self._doVerify  = False
        self._verifyWr  = False
        self._sData     = bytearray()  # Set data
        self._sDataMask = bytearray()  # Set data mask
        self._bData     = bytearray()  # Block data
        self._vData     = bytearray()  # Verify data
        self._vDataMask = bytearray()  # Verify data mask
        self._varMask   = bytearray()  # Variable bit mask, used to detect overlaps
        self._size      = 0
        self._offset    = variable.offset
        self._minSize   = self._reqMinAccess()
        self._maxSize   = self._reqMaxAccess()
        self._variables = []

        if self._minSize == 0 or self._maxSize == 0:
            raise MemoryError(name=self.name, address=self.address, msg="Invalid min/max size")

        self._addVariable(variable)

    def __repr__(self):
        return repr(self._variables)

    @property
    def stale(self):
        return any([b != 0 for b in self._sDataMask])

    @property
    def offset(self):
        return self._offset

    @property
    def address(self):
        return self._offset | self._reqAddress()

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

    @property
    def bulkEn(self):
        return self._bulkEn

    def set(self, var, value):
        """
        Update block with bitSize bits from passed byte array.
        Offset sets the starting point in the block array.
        """
        if not var._base.check(value,sum(var.bitSize)):
            msg = "Invalid value '{}' for base type {} with bit size {}".format(value,var._base.pytype,sum(var.bitSize))
            raise MemoryError(name=var.name, address=self.address, msg=msg)

        with self._lock:
            ba = var._base.toBytes(value, sum(var.bitSize))

            # Access is fully byte aligned
            if len(var.bitOffset) == 1 and (var.bitOffset[0] % 8) == 0 and (var.bitSize[0] % 8) == 0:
                self._sData[var.bitOffset[0]//8:(var.bitOffset[0]+var.bitSize[0])//8] = ba
                self._sDataMask[var.bitOffset[0]//8:(var.bitOffset[0]+var.bitSize[0])//8] = bytearray([0xff] * (var.bitSize[0] // 8))

            # Bit level access
            else:
                bit = 0
                for x in range(0, len(var.bitOffset)):
                    for y in range(0, var.bitSize[x]):
                        setBitToBytes(self._sData,var.bitOffset[x]+y,getBitFromBytes(ba,bit))
                        setBitToBytes(self._sDataMask,var.bitOffset[x]+y,1)
                        bit += 1

    def get(self, var):
        """
        Get bitSize bytes from block data.
        Offset sets the starting point in the block array.
        bytearray is returned
        """
        with self._lock:

            # Access is fully byte aligned
            if len(var.bitOffset) == 1 and (var.bitOffset[0] % 8) == 0 and (var.bitSize[0] % 8) == 0:
                return var._base.fromBytes(self._bData[int(var.bitOffset[0]/8):int((var.bitOffset[0]+var.bitSize[0])/8)])

            # Bit level access
            else:
                ba = bytearray(int(math.ceil(float(sum(var.bitSize)) / 8.0)))

                bit = 0
                for x in range(0, len(var.bitOffset)):
                    for y in range(0, var.bitSize[x]):
                        setBitToBytes(ba,bit,getBitFromBytes(self._bData,var.bitOffset[x]+y))
                        bit += 1

                return var._base.fromBytes(ba)

    def startTransaction(self, type, check=False):
        """
        Start a transaction.
        """
        with self._lock:

            #print(f'Called {self.name}.startTransaction(check={check})')

            # Check for invalid combinations
            if (type == rim.Write  and (self.mode == 'RO')) or \
               (type == rim.Post   and (self.mode == 'RO')) or \
               (type == rim.Read   and (self.mode == 'WO')) or \
               (type == rim.Verify and (self.mode == 'WO' or \
                                        self.mode == 'RO' or \
                                        self._verifyWr == False)):
                return

            self._waitTransaction(0)
            self.error = 0

            # Move staged write data to block. Clear stale.
            if type == rim.Write or type == rim.Post:
                for x in range(self._size):
                    self._bData[x] = self._bData[x] & (self._sDataMask[x] ^ 0xFF)
                    self._bData[x] = self._bData[x] | (self._sDataMask[x] & self._sData[x])

                self._sData = bytearray(self._size)
                self._sDataMask = bytearray(self._size)

            # Do not write to hardware for a disabled device
            if (self._device.enable.value() is not True):
                return

            self._log.debug(f'startTransaction type={type}')
            self._log.debug(f'len bData = {len(self._bData)}, vData = {len(self._vData)}, vDataMask = {len(self._vDataMask)}')

            # Track verify after writes. 
            # Only verify blocks that have been written since last verify
            if type == rim.Write:
                self._verifyWr = self._verifyEn
                  
            # Setup transaction
            self._doVerify = (type == rim.Verify)
            self._doUpdate = True

            # Set data pointer
            tData = self._vData if self._doVerify else self._bData

            # Start transaction
            self._reqTransaction(self.offset,tData,0,0,type)

        if check:
            #print(f'Checking {self.name}.startTransaction(check={check})')
            self._checkTransaction()


    def _checkTransaction(self):
        
        doUpdate = False
        with self._lock:
            self._waitTransaction(0)

            #print(f'Checking {self.name}._checkTransaction()')            

            # Error
            err = self.error
            self.error = 0

            if err > 0:
                raise MemoryError(name=self.name, address=self.address, error=err, size=self._size)

            if self._doVerify:
                self._verifyWr = False

                for x in range(self._size):
                    if (self._vData[x] & self._vDataMask[x]) != (self._bData[x] & self._vDataMask[x]):
                        msg  = ('Local='    + ''.join(f'{x:#02x}' for x in self._bData))
                        msg += ('. Verify=' + ''.join(f'{x:#02x}' for x in self._vData))
                        msg += ('. Mask='   + ''.join(f'{x:#02x}' for x in self._vDataMask))

                        raise MemoryError(name=self.name, address=self.address, error=rim.VerifyError, msg=msg, size=self._size)

               # Updated
            doUpdate = self._doUpdate
            self._doUpdate = False

        # Update variables outside of lock
        if doUpdate: self.updated()

    def _addVariable(self,var):
        """
        Add a variable to the block. Called from Device for BlockMemory
        """

        with self._lock:

            # Return false if offset does not match
            if len(self._variables) != 0 and var.offset != self._variables[0].offset:
                return False
    
            # Range check
            if var.varBytes > self._maxSize:
                msg = f'Variable {var.name} size {var.varBytes} exceeds maxSize {self._maxSize}'
                raise MemoryError(name=self.name, address=self.address, msg=msg)

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
                self._vDataMask.extend(bytearray(var.varBytes - self._size))
                self._varMask.extend(bytearray(var.varBytes - self._size))
                self._size = var.varBytes

            self._sData = bytearray(self._size)
            self._sDataMask = bytearray(self._size)

            # Update var bit mask and check for overlaps
            for x in range(0, len(var.bitOffset)):
                for y in range(0, var.bitSize[x]):
                    if getBitFromBytes(self._varMask,var.bitOffset[x]+y):
                        msg = f"Detected bit overlap for variable {var.name}"
                        raise MemoryError(name=self.name, address=self.address, msg=msg)
                    setBitToBytes(self._varMask,var.bitOffset[x]+y,1)

            # Update verify mask
            if var.mode == 'RW' and var.verify is True:
                self._verifyEn = True

                for x in range(0, len(var.bitOffset)):
                    for y in range(0, var.bitSize[x]):
                        setBitToBytes(self._vDataMask,var.bitOffset[x]+y,1)

            return True

    def _setDefault(self, var, value):
        with self._lock:
            # Stage the default data        
            self.set(var, value)

            # Move stage data to block, but keep it staged as well
            for x in range(self._size):
                self._bData[x] = self._bData[x] & (self._sDataMask[x] ^ 0xFF)
                self._bData[x] = self._bData[x] | (self._sDataMask[x] & self._sData[x])


    def updated(self):
        self._log.debug(f'Block {self._name} _update called')
        for v in self._variables:
            v.updated()

        
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

