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
import pyrogue as pr

class BlockError(Exception):
    """ Exception for memory access errors."""

    def __init__(self,block):
        self._error = block.error
        block._error = 0
        self._value = "Error in block %s with address 0x%x: Block Variables: %s. " % (block.name,block.address,block._variables)

        if (self._error & 0xFF000000) == rogue.interfaces.memory.TimeoutError:
            self._value += "Timeout after %s seconds" % (block.timeout)

        elif (self._error & 0xFF000000) == rogue.interfaces.memory.VerifyError:
            bStr = ''.join('0x{:02x} '.format(x) for x in block._bData)
            vStr = ''.join('0x{:02x} '.format(x) for x in block._vData)
            mStr = ''.join('0x{:02x} '.format(x) for x in block._mData)
            self._value += "Verify error. Local=%s, Verify=%s, Mask=%s" % (bStr,vStr,mStr)

        elif (self._error & 0xFF000000) == rogue.interfaces.memory.AddressError:
            self._value += "Address error"

        elif (self._error & 0xFF000000) == rogue.interfaces.memory.SizeError:
            self._value += "Size error. Size=%i" % (block._size)

        elif (self._error & 0xFF000000) == rogue.interfaces.memory.AxiTimeout:
            self._value += "AXI timeout"

        elif (self._error & 0xFF000000) == rogue.interfaces.memory.AxiFail:
            self._value += "AXI fail"

        else:
            self._value += "Unknown error 0x%x" % (self._error)

    def __str__(self):
        return repr(self._value)


class Block(rogue.interfaces.memory.Master):
    """Internal memory block holder"""

    def __init__(self,device,variable):
        """
        Initialize memory block class.
        Pass initial variable.
        """
        rogue.interfaces.memory.Master.__init__(self)

        # Attributes
        self._offset    = variable.offset
        self._mode      = variable.mode
        self._name      = variable.name
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
        self._device    = variable.parent
        self._tranTime  = time.time()

        self._setSlave(self._device)
        self._addVariable(variable)

        # Setup logging
        self._log = pr.logInit(self,self._name)

    def __repr__(self):
        return repr(self._variables)

    def set(self,bitOffset,bitCount,ba):
        """
        Update block with bitCount bits from passed byte array.
        Offset sets the starting point in the block array.
        """
        with self._cond:
            self._waitTransaction()

            # Access is fully byte aligned
            if (bitOffset % 8) == 0 and (bitCount % 8) == 0:
                self._bData[int(bitOffset/8):int((bitOffset+bitCount)/8)] = ba

            # Bit level access
            else:
                for x in range(0,bitCount):
                    setBitToBytes(self._bData,x+bitOffset,getBitFromBytes(ba,x))

    def get(self,bitOffset,bitCount):
        """
        Get bitCount bytes from block data.
        Offset sets the starting point in the block array.
        bytearray is returned
        """
        with self._cond:
            self._waitTransaction()

            # Error
            if self._error > 0:
                raise BlockError(self)


            # Access is fully byte aligned
            if (bitOffset % 8) == 0 and (bitCount % 8) == 0:
                return self._bData[int(bitOffset/8):int((bitOffset+bitCount)/8)]

            # Bit level access
            else:
                ba = bytearray(int(bitCount / 8))
                if (bitCount % 8) > 0: ba.extend(bytearray(1))
                for x in range(0,bitCount):
                    setBitToBytes(ba,x,getBitFromBytes(self._bData,x+bitOffset))
                return ba

    def setUInt(self,bitOffset,bitCount,value):
        """
        Set a uint. to be deprecated
        """
        bCount = (int)(bitCount / 8)
        if ( bitCount % 8 ) > 0: bCount += 1
        ba = bytearray(bCount)

        for x in range(0,bCount):
            ba[x] = (value >> (x*8)) & 0xFF

        self.set(bitOffset,bitCount,ba)

    def getUInt(self,bitOffset,bitCount):
        """
        Get a uint. to be deprecated
        """
        ba = self.get(bitOffset,bitCount)
        ret = 0

        for x in range(0,len(ba)):
            ret += (ba[x] << (x*8))

        return ret

    def setString(self,value):
        """
        Set a string. to be deprecated
        """
        ba = bytarray(value,'utf-8')
        ba.extend(bytearray(1))

        self.set(0,len(ba)*8,ba)

    def getString(self):
        """
        Get a string. to be deprecated
        """
        ba = self.get(0,self._size*8).rstrip(bytearray(1))
        return(ba.decode('utf-8'))

    def backgroundTransaction(self,type):
        """
        Perform a background transaction
        """
        self._startTransaction(type)

    def blockingTransaction(self,type):
        """
        Perform a blocking transaction
        """
        self._log.debug("Setting block. Addr=%x, Data=%s" % (self._offset,self._bData))
        self._startTransaction(type)
        self._checkTransaction(update=False)
        self._log.debug("Done block. Addr=%x, Data=%s" % (self._offset,self._bData))

    @property
    def offset(self):
        return self._offset

    @property
    def address(self):
        return self._offset | self._reqOffset()

    @property
    def name(self):
        return self._name

    @property
    def mode(self):
        return self._mode

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
        Add a variable to the block
        """

	
        with self._cond:
            self._waitTransaction()

            # Return false if offset does not match
            if var.offset != self._offset:
                return False

            # Compute the max variable address to determine required size of block
            varBytes = int(math.ceil(float(var.bitOffset + var.bitSize) / 8.0))

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

        minSize = self._reqMinAccess()
        tData = None

        with self._cond:
            self._waitTransaction()

            # Adjust size if required
            if (self._size % minSize) > 0:
                newSize = (((int)(self._size / minSize) + 1) * minSize)
                self._bData.extend(bytearray(newSize - self._size))
                self._vData.extend(bytearray(newSize - self._size))
                self._mData.extend(bytearray(newSize - self._size))
                self._size = newSize

            # Return if not enabled
            if not self._device.enable.get():
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
        self._reqTransaction(self._offset,tData,type)

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

