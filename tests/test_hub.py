#!/usr/bin/env python3
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

# This test file tests and demonstrates the ability to have virtual address space
# directly in a device using the hub override calls. In this example the real address
# space contains two registers, one to issue commands over SPI. The data field for these
# commands are:
# Bit 31 = read/write bit. Set to '1' for reads
# bits 30:20 = address field
# bits 19:00 = data field, ignored on read
#
# The second register is a read back register to get the results of the previous
# read command.
#
# The remaining registers in this device are virtual and read or write accesses to them
# are converted to multiple transactions using the above two handshake registers.

import pyrogue as pr
import rogue.interfaces.memory
import threading
import random

class HubTestDev(pr.Device):

    # Read address space of the device.
    WRITE_ADDR  = 0x000
    READ_ADDR   = 0x004

    # Any addresses above this value are treated as vritual
    OFFSET_ADDR = 0x100
    MAX_RETRIES = 5

    def __init__(self,**kwargs):
        super().__init__(**kwargs)

        self._lock = threading.Lock()

        # Write register to initiating commands. The data field takes the following
        # Format:
        #    Bit 31 = read/write bit. Set to '1' for reads
        #    bits 30:20 = address field
        #    bits 19:00 = data field, ignored on read
        self.add(pr.RemoteVariable(
            name         = "Write",
            offset       =  self.WRITE_ADDR,
            bitSize      =  32,
            bitOffset    =  0x00,
            base         = pr.UInt,
            mode         = "RW",
        ))

        # Read register to get read command results. The data returned will contain
        # the following data:
        #    Bit 31 = read/write bit. Set to '1' for reads
        #    bits 30:20 = address field
        #    bits 19:00 = data field
        self.add(pr.RemoteVariable(
            name         = "Read",
            offset       =  self.READ_ADDR,
            bitSize      =  32,
            bitOffset    =  0x00,
            base         = pr.UInt,
            mode         = "RO",
        ))

        # Virtual registers
        for i in range(10):
            self.add(pr.RemoteVariable(
                name         = f"Reg[{i}]",
                offset       =  self.OFFSET_ADDR + (4 * i),
                bitSize      =  32,
                bitOffset    =  0x00,
                base         = pr.UInt,
                mode         = "RW",
            ))

    # Return the command field from the read data
    @classmethod
    def cmd_address(cls, data): # returns address data
        return((data & 0x7FFF0000) >> 20)

    # Return the data field from the read data
    @classmethod
    def cmd_data(cls, data):  # returns data
        return(data & 0xFFFFF)

    # Build the data field for a write command
    @classmethod
    def cmd_make(cls, read, address, data):
        return((read << 31) | ((address << 20) & 0x7FF00000) | (data & 0xFFFFF))

    # Helper function to initiate outbound write transactions and wait for the result
    # Returns error string or "" for no error
    def _wrapWriteTransaction(self, data):
        self._clearError()
        dataBytes = data.to_bytes(4,'little',signed=False)
        id = self._reqTransaction(self.WRITE_ADDR, dataBytes, 4, 0, rogue.interfaces.memory.Write)
        self._waitTransaction(id)
        return self._getError()

    # Helper function to initiate outbound read transactions and wait for the result
    # Returns data,error where error is "" for no error
    def _wrapReadTransaction(self):
        self._clearError()
        dataBytes = bytearray(4)
        id = self._reqTransaction(self.READ_ADDR, dataBytes, 4, 0, rogue.interfaces.memory.Read)
        self._waitTransaction(id)

        return int.from_bytes(dataBytes, 'little', signed=False), self._getError()

    # Execute write to the passed virtual address
    def _doVirtualWrite(self,address,data):
        return self._wrapWriteTransaction(self.cmd_make(read=0,  address=(address - self.OFFSET_ADDR), data=data))

    # Execute read from the passed virtual address, retry until data is ready
    def _doVirtualRead(self,address):
        writeData = self.cmd_make(read=1, address=(address - self.OFFSET_ADDR), data=0)

        rsp = self._wrapWriteTransaction(writeData)

        if rsp != "":
            return None, rsp

        for _ in range(self.MAX_RETRIES):
            rsp = self._wrapWriteTransaction(writeData)

            if rsp != "":
                return None, rsp

            data, rsp = self._wrapReadTransaction()

            if rsp != "":
                return None, rsp

            if self.cmd_address(data) == (address - self.OFFSET_ADDR):
                return self.cmd_data(data), ""

        return None,"Indirect Read Timeout"

    # Intercept transactions
    def _doTransaction(self,transaction):
        with self._lock:

            addr = transaction.address()

            # Read transactions to non virtual space are passed through
            if addr < self.OFFSET_ADDR:
                super()._doTransaction(transaction)
            else:

                with transaction.lock():

                    # Write transaction
                    if transaction.type() == rogue.interfaces.memory.Write or \
                       transaction.type() == rogue.interfaces.memory.Post:

                        cmdDataBytes = bytearray(transaction.size())
                        transaction.getData(cmdDataBytes,0)
                        rsp = self._doWrite(addr,int.from_bytes(cmdDataBytes,byteorder='little', signed=False))

                        if rsp != "":
                            transaction.error(rsp)
                        else:
                            transaction.done()

                    # Read or read/verity transaction
                    else:

                        data, error = self._doRead(addr)

                        if error != "":
                            transaction.error(error)
                        else:
                            transaction.setData(data.to_bytes(4,'little',signed=False),0)
                            transaction.done()


# Device which emulates the SPI interface under tests.
class TestEmulate(rogue.interfaces.memory.Slave):

    def __init__(self, *, minWidth=4, maxSize=0xFFFFFFFF):
        rogue.interfaces.memory.Slave.__init__(self,4,4)
        self._minWidth = minWidth
        self._maxSize  = maxSize
        self._data  = {}
        self._addr  = 0
        self._echo  = 0
        self._read  = 0
        self._wd    = 0

    def _checkRange(self, address, size):
        return 0

    def _doMaxAccess(self):
        return(self._maxSize)

    def _doMinAccess(self):
        return(self._minWidth)

    def _doTransaction(self,transaction):
        address = transaction.address()
        size    = transaction.size()
        type    = transaction.type()

        if size == 4 and address == 0:
            if type == rogue.interfaces.memory.Write:
                ba = bytearray(4)
                transaction.getData(ba,0)
                self._wd = int.from_bytes(ba,'little',signed=False)

                self._addr = (self._wd >> 20) & 0x7FF
                data = (self._wd & 0xFFFFF)
                self._read = (self._wd >> 31) & 0x1

                if self._addr not in self._data:
                    self._data[self._addr] = 0

                if self._read == 0:
                    self._data[self._addr] = data

                #print(f"Indirect write addr={self._addr:#x}, data={data:#x}, read={self._read}")

            elif type == rogue.interfaces.memory.Verify or type == rogue.interfaces.memory.Read:
                ba  = self._wd.to_bytes(4,'little',signed=False)
                transaction.setData(ba,0)

            transaction.done()

        elif size == 4 and address == 4 and type == rogue.interfaces.memory.Read:
            data = self._data[self._addr]

            ret = (self._read << 31) + (self._addr << 20) + data

            ba  = ret.to_bytes(4,'little',signed=False)

            #print(f"Indirect read addr={self._addr:#x}, read={self._read}, ret={ret:#x}")
            transaction.setData(ba,0)
            transaction.done()

        else:
            transaction.error(f"Invalid transaction. Addr:{address:#x}, size:{size}, type:{type}")

class DummyTree(pr.Root):

    def __init__(self):
        pr.Root.__init__(self,
                         name='dummyTree',
                         description="Dummy tree for example",
                         timeout=2.0,
                         pollEn=False,
                         serverPort=None)

        # Use a memory space emulator
        sim = TestEmulate()
        self.addInterface(sim)

        self.add(HubTestDev(
                offset     = 0x0,
                memBase    = sim,
            ))

def test_hub():

    with DummyTree() as root:

        test = [int(random.random()*100) for i in range(10)]

        for i in range(10):
            root.HubTestDev.Reg[i].set(test[i])

        for i in range(10):
            val = root.HubTestDev.Reg[i].get()
            if test[i] != val:
                raise AssertionError(f'read mismatch at reg {i}. Got {val} exp {test[i]}')

        root.HubTestDev.Write.set(root.HubTestDev.cmd_make(1,5*4,0))
        val = root.HubTestDev.cmd_data(root.HubTestDev.Read.get())

        if test[5] != val:
            raise AssertionError(f'read mismatch at reg 5. Got {val} exp {test[5]}')


if __name__ == "__main__":
    test_hub()
