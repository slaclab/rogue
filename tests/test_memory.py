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

# Comment added by rherbst for demonstration purposes.
import datetime
import parse
import pyrogue as pr
import pyrogue.interfaces.simulation
import rogue.interfaces.memory
import time

#rogue.Logging.setLevel(rogue.Logging.Debug)
#import logging
#logger = logging.getLogger('pyrogue')
#logger.setLevel(logging.DEBUG)

class SimpleDev(pr.Device):

    def __init__(self,**kwargs):

        super().__init__(**kwargs)

        self.add(pr.RemoteVariable(
            name         = "SimpleTestAA",
            offset       =  0x1c,
            bitSize      =  16,
            bitOffset    =  0x00,
            base         = pr.UInt,
            mode         = "RW",
        ))

        self.add(pr.RemoteVariable(
            name         = "SimpleTestAB",
            offset       =  0x1e,
            bitSize      =  16,
            bitOffset    =  0x00,
            base         = pr.UInt,
            mode         = "RW",
        ))

        self.add(pr.RemoteVariable(
            name         = "SimpleTestBA",
            offset       =  0x20,
            bitSize      =  8,
            bitOffset    =  0x00,
            base         = pr.UInt,
            mode         = "RW",
        ))

        self.add(pr.RemoteVariable(
            name         = "SimpleTestBB",
            offset       =  0x21,
            bitSize      =  8,
            bitOffset    =  0x00,
            base         = pr.UInt,
            mode         = "RW",
        ))

        self.add(pr.RemoteVariable(
            name         = "SimpleTestBC",
            offset       =  0x22,
            bitSize      =  8,
            bitOffset    =  0x00,
            base         = pr.UInt,
            mode         = "RW",
        ))

        self.add(pr.RemoteVariable(
            name         = "SimpleTestBD",
            offset       =  0x23,
            bitSize      =  8,
            bitOffset    =  0x00,
            base         = pr.UInt,
            mode         = "RW",
        ))

class MemDev(pr.Device):

    def __init__(self,modeConfig='RW',**kwargs):

        super().__init__(**kwargs)

        for i in range(int(256/4)):
            for j in range(4):
                # 4 bytes all in the same 32-bit address alignment across multiple 32-bit word boundaries
                value = 4*i+j
                self.add(pr.RemoteVariable(
                    name         = f'TestBlockBytes[{value}]',
                    offset       = 0x000+4*i,
                    bitSize      = 8,
                    bitOffset    = 8*j,
                    mode         = modeConfig,
                    value        = None if modeConfig=='RW' else value,
                ))

        for i in range(256):
            # Sweeping across a non-byte remote variable with overlapping 32-bit address alignments
            # with same offsets for all variables (sometimes ASIC designers do this registers definition)
            self.add(pr.RemoteVariable(
                name         = f'TestBlockBits[{i}]',
                offset       = 0x100,
                bitSize      = 9,
                bitOffset    = 9*i,
                mode         = modeConfig,
                value        = None if modeConfig=='RW' else i,
            ))


class DummyTree(pr.Root):

    def __init__(self):
        pr.Root.__init__(self,
                         name='dummyTree',
                         description="Dummy tree for example",
                         timeout=2.0,
                         pollEn=False,
                         serverPort=None)

        # Use a memory space emulator
        sim = pr.interfaces.simulation.MemEmulate()
        self.addInterface(sim)

        # Create a memory gateway
        ms = rogue.interfaces.memory.TcpServer("127.0.0.1",9080);
        self.addInterface(ms)

        # Connect the memory gateways together
        sim << ms

        # Create a memory gateway
        mc = rogue.interfaces.memory.TcpClient("127.0.0.1",9080);
        self.addInterface(mc)

        # Add Device
        modeConfig = ['RW','RW','RO','RO']
        for i in range(4):
            self.add(MemDev(
                name       = f'MemDev[{i}]',
                offset     = i*0x10000,
                modeConfig = modeConfig[i],
                memBase    = mc,
            ))

        self.add(SimpleDev(
                name       = 'SimpleDev',
                offset     = 0x80000,
                memBase    = mc,
            ))

def test_memory():

    with DummyTree() as root:

        # Load the R/W variables
        for dev in range(2):
            writeVar = (dev == 0)
            for i in range(256):
                root.MemDev[dev].TestBlockBytes[i].set(value=i,write=writeVar)
                root.MemDev[dev].TestBlockBits[i].set(value=i,write=writeVar)

        root.SimpleDev.SimpleTestAA.set(0x40)
        root.SimpleDev.SimpleTestAB.set(0x80)
        root.SimpleDev.SimpleTestBA.set(0x41)
        root.SimpleDev.SimpleTestBB.set(0x42)
        root.SimpleDev.SimpleTestBC.set(0x43)
        root.SimpleDev.SimpleTestBD.set(0x44)

        # Bulk Write Device
        root.MemDev[1].WriteDevice()

        # Bulk Read Device
        root.MemDev[3].ReadDevice()

        # Verify all the RW and RO variables
        for dev in range(4):
            for i in range(256):
                if dev!=3:
                    retByte = root.MemDev[dev].TestBlockBytes[i].get()
                    retBit  = root.MemDev[dev].TestBlockBits[i].get()
                else:
                    retByte = root.MemDev[dev].TestBlockBytes[i].value()
                    retBit  = root.MemDev[dev].TestBlockBits[i].value()
                if (retByte != i) or (retBit != i):
                    raise AssertionError(f'{root.MemDev[dev].path}: Verification Failure: i={i}, TestBlockBytes={retByte}, TestBlockBits={retBit}')

        retAA = root.SimpleDev.SimpleTestAA.get()
        retAB = root.SimpleDev.SimpleTestAB.get()
        retBA = root.SimpleDev.SimpleTestBA.get()
        retBB = root.SimpleDev.SimpleTestBB.get()
        retBC = root.SimpleDev.SimpleTestBC.get()
        retBD = root.SimpleDev.SimpleTestBD.get()

        if (retAA != 0x40) or (retAB != 0x80) or (retBA != 0x41) or (retBB != 0x42) or (retBC != 0x43) or (retBD != 0x44):
            raise AssertionError(f'Verification Failure: retAA={retAA}, retAB={retAB}, retBA={retBA}, retBB={retBB}, retBC={retBC}, retBD={retBD}')


if __name__ == "__main__":
    test_memory()
