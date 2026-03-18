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

import pyrogue as pr
import rogue.interfaces.memory
import pytest

pytestmark = pytest.mark.integration

class MixedWidthDevice(pr.Device):
    def __init__(self, **kwargs):
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

class OverlapMemoryDevice(pr.Device):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        for i in range(int(256/4)):
            for j in range(4):
                # Sweep byte accesses across multiple 32-bit word boundaries.
                value = 4*i+j
                self.add(pr.RemoteVariable(
                    name         = f'TestBlockBytes[{value}]',
                    offset       = 0x000+4*i,
                    bitSize      = 8,
                    bitOffset    = 8*j,
                    mode         = "RW",
                    value        = value
                ))

        for i in range(256):
            # Sweep a 9-bit field across overlapping 32-bit words.
            self.add(pr.RemoteVariable(
                name         = f'TestBlockBits[{i}]',
                offset       = 0x100,
                bitSize      = 9,
                bitOffset    = 9*i,
                mode         = "RW",
                value        = i
            ))


class MemoryTransportRoot(pr.Root):
    def __init__(self, *, port):
        super().__init__(name='dummyTree', description="Dummy tree for example", timeout=2.0, pollEn=False)

        # Exercise the real TCP memory gateway path over a local emulator.
        sim = rogue.interfaces.memory.Emulate(4,0x1000)
        self.addInterface(sim)

        ms = rogue.interfaces.memory.TcpServer("127.0.0.1", port)
        self.addInterface(ms)
        sim << ms

        mc = rogue.interfaces.memory.TcpClient("127.0.0.1", port)
        self.addInterface(mc)

        for i in range(4):
            self.add(OverlapMemoryDevice(
                name       = f'MemDev[{i}]',
                offset     = i*0x10000,
                memBase    = mc,
            ))

        self.add(MixedWidthDevice(
            name    = 'SimpleDev',
            offset  = 0x80000,
            memBase = mc,
        ))

def test_memory(free_tcp_port):
    with MemoryTransportRoot(port=free_tcp_port) as root:

        for dev in range(2):
            write_var = dev == 0
            for i in range(256):
                root.MemDev[dev].TestBlockBytes[i].set(value=i, write=write_var)
                root.MemDev[dev].TestBlockBits[i].set(value=i, write=write_var)

        root.SimpleDev.SimpleTestAA.set(0x40)
        root.SimpleDev.SimpleTestAB.set(0x80)
        root.SimpleDev.SimpleTestBA.set(0x41)
        root.SimpleDev.SimpleTestBB.set(0x42)
        root.SimpleDev.SimpleTestBC.set(0x43)
        root.SimpleDev.SimpleTestBD.set(0x44)

        root.MemDev[1].WriteDevice()
        root.MemDev[3].ReadDevice()

        for dev in range(4):
            for i in range(256):
                if dev != 3:
                    retByte = root.MemDev[dev].TestBlockBytes[i].get()
                    retBit  = root.MemDev[dev].TestBlockBits[i].get()
                else:
                    retByte = root.MemDev[dev].TestBlockBytes[i].value()
                    retBit  = root.MemDev[dev].TestBlockBits[i].value()
                assert retByte == i, f"{root.MemDev[dev].path}: byte mismatch at {i}"
                assert retBit == i, f"{root.MemDev[dev].path}: bit mismatch at {i}"

        retAA = root.SimpleDev.SimpleTestAA.get()
        retAB = root.SimpleDev.SimpleTestAB.get()
        retBA = root.SimpleDev.SimpleTestBA.get()
        retBB = root.SimpleDev.SimpleTestBB.get()
        retBC = root.SimpleDev.SimpleTestBC.get()
        retBD = root.SimpleDev.SimpleTestBD.get()

        assert (retAA, retAB, retBA, retBB, retBC, retBD) == (0x40, 0x80, 0x41, 0x42, 0x43, 0x44)


if __name__ == "__main__":
    test_memory()
