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

        elif (error & 0xFF000000) == rim.BusTimeout:
            self._value += "Bus timeout."

        elif (error & 0xFF000000) == rim.BusFail:
            self._value += "Bus Error: {:#02x}".format(error & 0xFF)

        elif (error & 0xFF000000) == rim.Unsupported:
            self._value += "Unsupported Transaction."

        elif (error & 0xFF000000) == rim.ProtocolError:
            self._value += "Protocol Error."

        elif error != 0:
            self._value += f"Unknown error {error:#02x}."

        if msg is not None:
            self._value += (' ' + msg)

    def __str__(self):
        return repr(self._value)


class BaseBlock(object):

    def __init__(self, *, path, mode, device):

        self._path      = path
        self._mode      = mode
        self._device    = device
        self._lock      = threading.RLock()
        self._doUpdate  = False

        # Setup logging
        self._log = pr.logInit(cls=self,name=path)


    def __repr__(self):
        return repr(self.path)

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
    def path(self):
        return self._path

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

    def _forceStale(self):
        pass
        
    def updated(self):
        pass

class LocalBlock(BaseBlock):
    def __init__(self, *, variable, localSet, localGet, value):
        BaseBlock.__init__(self, path=variable.path, mode=variable.mode, device=variable.parent)

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

    def set(self, var, value):
        with self._lock:
            changed = self._value != value
            self._value = value

            # If a setFunction exists, call it (Used by local variables)
            if self._localSet is not None:

                # Possible args
                pargs = {'dev' : self._device, 'var' : self._variable, 'value' : self._value, 'changed' : changed}

                pr.varFuncHelper(self._localSet, pargs, self._log, self._variable.path)

    def get(self, var):
        if self._localGet is not None:
            with self._lock:

                # Possible args
                pargs = {'dev' : self._device, 'var' : self._variable}

                self._value = pr.varFuncHelper(self._localGet,pargs, self._log, self._variable.path)

        return self._value

    def updated(self):
        self._variable._queueUpdate()

    def _iadd(self, other):
        with self._lock:
            self.set(None, self.get(None) + other)
            self.updated()

    def _isub(self, other):
        with self._lock:
            self.set(None, self.get(None) - other)
            self.updated()

    def _imul(self, other):
        with self._lock:
            self.set(None, self.get(None) * other)
            self.updated()

    def _imatmul(self, other):
        with self._lock:
            self.set(None, self.get(None) @ other)
            self.updated()

    def _itruediv(self, other):
        with self._lock:
            self.set(None, self.get(None) / other)
            self.updated()

    def _ifloordiv(self, other):
        with self._lock:
            self.set(None, self.get(None) // other)
            self.updated()

    def _imod(self, other):
        with self._lock:
            self.set(None, self.get(None) % other)
            self.updated()

    def _ipow(self, other):
        with self._lock:
            self.set(None, self.get(None) ** other)
            self.updated()

    def _ilshift(self, other):
        with self._lock:
            self.set(None, self.get(None) << other)
            self.updated()

    def _irshift(self, other):
        with self._lock:
            self.set(None, self.get(None) >> other)
            self.updated()

    def _iand(self, other):
        with self._lock:
            self.set(None, self.get(None) & other)
            self.updated()

    def _ixor(self, other):
        with self._lock:
            self.set(None, self.get(None) ^ other)
            self.updated()

    def _ior(self, other):
        with self._lock:
            self.set(None, self.get(None) | other)
            self.updated()


class RemoteBlock(BaseBlock, rim.Master):
    def __init__(self, *, offset, size, variables):
     
        rim.Master.__init__(self)
        self._setSlave(variables[0].parent)
        
        BaseBlock.__init__(self, path=variables[0].path, mode=variables[0].mode, device=variables[0].parent)
        self._verifyEn  = False
        self._bulkEn    = False
        self._doVerify  = False
        self._verifyWr  = False
        self._sData     = bytearray(size)  # Set data
        self._sDataMask = bytearray(size)  # Set data mask
        self._bData     = bytearray(size)  # Block data
        self._vData     = bytearray(size)  # Verify data
        self._vDataMask = bytearray(size)  # Verify data mask
        self._size      = size
        self._offset    = offset
        self._minSize   = self._reqMinAccess()
        self._maxSize   = self._reqMaxAccess()
        self._variables = variables

        if self._minSize == 0 or self._maxSize == 0:
            raise MemoryError(name=self.path, address=self.address, msg="Invalid min/max size")

        # Range check
        if self._size > self._maxSize:
            msg = f'Block {self.path} size {self._size} exceeds maxSize {self._maxSize}'
            raise MemoryError(name=self.path, address=self.address, msg=msg)

        # Temp bit masks
        excMask = bytearray(size)  # Variable bit mask for exclusive variables
        oleMask = bytearray(size)  # Variable bit mask for overlap enabled variables

        # Go through variables
        for var in variables:

            # Link variable to block
            var._block = self

            if not isinstance(var, pr.BaseCommand):
                self._bulkEn = True

            self._log.debug(f"Adding variable {var.name} to block {self.path} at offset {self.offset:#02x}")

            # If variable modes mismatch, set block to read/write
            if var.mode != self._mode:
                self._mode = 'RW'

            # Update variable masks
            for x in range(len(var.bitOffset)):

                # Variable allows overlaps, add to overlap enable mask
                if var._overlapEn:
                    self._setBits(oleMask,var.bitOffset[x],var.bitSize[x])

                # Otherwise add to exclusive mask and check for existing mapping
                else:
                    if self._anyBits(excMask,var.bitOffset[x],var.bitSize[x]):
                        raise MemoryError(name=self.path, address=self.address, msg="Variable bit overlap detected.")
                    self._setBits(excMask,var.bitOffset[x],var.bitSize[x])

                # update verify mask
                if var.mode == 'RW' and var.verify is True:
                    self._verifyEn = True
                    self._setBits(self._vDataMask,var.bitOffset[x],var.bitSize[x])

        # Check for overlaps by anding exclusive and overmap bit vectors
        for b1, b2 in zip(oleMask, excMask):
            if b1 & b2 != 0:
                raise MemoryError(name=self.path, address=self.address, msg="Variable bit overlap detected.")

        # Set exclusive flag
        self._overlapEn = all (excMask[i] == 0 for i in range(size))

        # Force block to be stale at startup
        self._forceStale()

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
    def size(self):
        return self._size

    @property
    def memBaseId(self):
        return self._reqSlaveId()

    @property
    def timeout(self):
        return float(self._getTimeout()) / 1000000.0

    @timeout.setter
    def timeout(self,value):
        self._setTimeout(int(value*1000000))

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
            raise MemoryError(name=var.path, address=self.address, msg=msg)

        with self._lock:
            ba = var._base.toBytes(value, sum(var.bitSize))

            srcBit = 0
            for x in range(len(var.bitOffset)):
                self._copyBits(self._sData, var.bitOffset[x], ba, srcBit, var.bitSize[x])
                self._setBits(self._sDataMask, var.bitOffset[x], var.bitSize[x])
                srcBit += var.bitSize[x]

    def get(self, var):
        """
        Get bitSize bytes from block data.
        Offset sets the starting point in the block array.
        bytearray is returned
        """
        with self._lock:
            ba = bytearray(int(math.ceil(float(sum(var.bitSize)) / 8.0)))

            dstBit = 0
            for x in range(len(var.bitOffset)):
                if self._anyBits(self._sDataMask, var.bitOffset[x], var.bitSize[x]):
                    self._copyBits(ba, dstBit, self._sData, var.bitOffset[x], var.bitSize[x])
                else:
                    self._copyBits(ba, dstBit, self._bData, var.bitOffset[x], var.bitSize[x])
                dstBit += var.bitSize[x]

            return var._base.fromBytes(ba,sum(var.bitSize))

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
            #print(f'Checking {self.path}.startTransaction(check={check})')
            self._checkTransaction()

    def _forceStale(self):
        for b in self._sDataMask: b = 0xFF

    def _checkTransaction(self):
        
        doUpdate = False
        with self._lock:
            self._waitTransaction(0)

            #print(f'Checking {self.path}._checkTransaction()')            

            # Error
            err = self.error
            self.error = 0

            if err > 0:
                raise MemoryError(name=self.path, address=self.address, error=err, size=self._size)

            if self._doVerify:
                self._verifyWr = False

                for x in range(self._size):
                    if (self._vData[x] & self._vDataMask[x]) != (self._bData[x] & self._vDataMask[x]):
                        msg  = ('Local='    + ''.join(f'{x:#02x}' for x in self._bData))
                        msg += ('. Verify=' + ''.join(f'{x:#02x}' for x in self._vData))
                        msg += ('. Mask='   + ''.join(f'{x:#02x}' for x in self._vDataMask))

                        raise MemoryError(name=self.path, address=self.address, error=rim.VerifyError, msg=msg, size=self._size)

               # Updated
            doUpdate = self._doUpdate
            self._doUpdate = False

        # Update variables outside of lock
        if doUpdate: self.updated()

    def _setDefault(self, var, value):
        with self._lock:
            # Stage the default data        
            self.set(var, value)

            # Move stage data to block, but keep it staged as well
            for x in range(self._size):
                self._bData[x] = self._bData[x] & (self._sDataMask[x] ^ 0xFF)
                self._bData[x] = self._bData[x] | (self._sDataMask[x] & self._sData[x])


    def updated(self):
        self._log.debug(f'Block {self._path} _update called')
        for v in self._variables:
            v._queueUpdate()

