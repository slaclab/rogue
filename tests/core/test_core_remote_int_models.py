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

class RemoteIntDevice(pr.Device):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.add(pr.RemoteVariable(
            name         = "SimpleTestAA",
            offset       =  0x1c,
            bitSize      =  16,
            bitOffset    =  0x00,
            base         = pr.Int,
            mode         = "RW",
        ))

        self.add(pr.RemoteVariable(
            name         = "SimpleTestAB",
            offset       =  0x1e,
            bitSize      =  16,
            bitOffset    =  0x00,
            base         = pr.Int,
            mode         = "RW",
        ))

        self.add(pr.RemoteVariable(
            name         = "SimpleTestBA",
            offset       =  0x20,
            bitSize      =  8,
            bitOffset    =  0x00,
            base         = pr.Int,
            mode         = "RW",
        ))

        self.add(pr.RemoteVariable(
            name         = "SimpleTestBB",
            offset       =  0x21,
            bitSize      =  7,
            bitOffset    =  0x00,
            base         = pr.Int,
            mode         = "RW",
        ))

        self.add(pr.RemoteVariable(
            name         = "SimpleTestBC",
            offset       =  0x22,
            bitSize      =  5,
            bitOffset    =  0x00,
            base         = pr.Int,
            mode         = "RW",
        ))

        self.add(pr.RemoteVariable(
            name         = "SimpleTestBD",
            offset       =  0x23,
            bitSize      =  8,
            bitOffset    =  0x00,
            base         = pr.Int,
            mode         = "RW",
        ))

class RemoteIntRoot(pr.Root):
    def __init__(self):
        super().__init__(name='dummyTree', description="Dummy tree for example", timeout=2.0, pollEn=False)

        # Exercise signed remote-variable conversion against the real memory block path.
        sim = rogue.interfaces.memory.Emulate(4,0x1000)
        self.addInterface(sim)

        self.add(RemoteIntDevice(
            name    = 'SimpleDev',
            offset  = 0x80000,
            memBase = sim,
        ))

def test_remote_int_model_reads_and_writes_signed_values():
    with RemoteIntRoot() as root:

        root.SimpleDev.SimpleTestAA.set(-1)
        root.SimpleDev.SimpleTestAB.set(2)
        root.SimpleDev.SimpleTestBA.set(-2)
        root.SimpleDev.SimpleTestBB.set(-5)
        root.SimpleDev.SimpleTestBC.set(7)
        root.SimpleDev.SimpleTestBD.set(-7)

        retAA = root.SimpleDev.SimpleTestAA.get()
        retAB = root.SimpleDev.SimpleTestAB.get()
        retBA = root.SimpleDev.SimpleTestBA.get()
        retBB = root.SimpleDev.SimpleTestBB.get()
        retBC = root.SimpleDev.SimpleTestBC.get()
        retBD = root.SimpleDev.SimpleTestBD.get()

        assert (retAA, retAB, retBA, retBB, retBC, retBD) == (-1, 2, -2, -5, 7, -7)


if __name__ == "__main__":
    test_remote_int_model_reads_and_writes_signed_values()
