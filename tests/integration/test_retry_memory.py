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
import pyrogue.interfaces.simulation
import pytest

pytestmark = pytest.mark.integration

class RetryMemoryDevice(pr.Device):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.add(pr.RemoteVariable(
            name         = "SimpleTestAA",
            offset       =  0x1c,
            bitSize      =  16,
            bitOffset    =  0x00,
            base         = pr.UInt,
            mode         = "RW",
            retryCount   = 3
        ))

        self.add(pr.RemoteVariable(
            name         = "SimpleTestAB",
            offset       =  0x1e,
            bitSize      =  16,
            bitOffset    =  0x00,
            base         = pr.UInt,
            mode         = "RW",
            retryCount   = 3
        ))

        self.add(pr.RemoteVariable(
            name         = "SimpleTestBA",
            offset       =  0x20,
            bitSize      =  8,
            bitOffset    =  0x00,
            base         = pr.UInt,
            mode         = "RW",
            retryCount   = 3
        ))

        self.add(pr.RemoteVariable(
            name         = "SimpleTestBB",
            offset       =  0x21,
            bitSize      =  8,
            bitOffset    =  0x00,
            base         = pr.UInt,
            mode         = "RW",
            retryCount   = 3
        ))

        self.add(pr.RemoteVariable(
            name         = "SimpleTestBC",
            offset       =  0x22,
            bitSize      =  8,
            bitOffset    =  0x00,
            base         = pr.UInt,
            mode         = "RW",
            retryCount   = 3
        ))

        self.add(pr.RemoteVariable(
            name         = "SimpleTestBD",
            offset       =  0x23,
            bitSize      =  8,
            bitOffset    =  0x00,
            base         = pr.UInt,
            mode         = "RW",
            retryCount   = 3
        ))


class RetryMemoryRoot(pr.Root):
    def __init__(self):
        super().__init__(name='dummyTree', description="Dummy tree for example", timeout=.01, pollEn=False)

        # Drop the first few transactions so retry handling is exercised.
        sim = pr.interfaces.simulation.MemEmulate(dropCount=2)
        self.addInterface(sim)

        self.add(RetryMemoryDevice(
            name    = 'SimpleDev',
            offset  = 0x80000,
            memBase = sim
        ))

def test_memory():
    with RetryMemoryRoot() as root:

        for i in range(10):

            root.SimpleDev.SimpleTestAA.set(0x40 + i)
            root.SimpleDev.SimpleTestAB.set(0x80 + i)
            root.SimpleDev.SimpleTestBA.set(0x41 + i)
            root.SimpleDev.SimpleTestBB.set(0x42 + i)
            root.SimpleDev.SimpleTestBC.set(0x43 + i)
            root.SimpleDev.SimpleTestBD.set(0x44 + i)

            retAA = root.SimpleDev.SimpleTestAA.get()
            retAB = root.SimpleDev.SimpleTestAB.get()
            retBA = root.SimpleDev.SimpleTestBA.get()
            retBB = root.SimpleDev.SimpleTestBB.get()
            retBC = root.SimpleDev.SimpleTestBC.get()
            retBD = root.SimpleDev.SimpleTestBD.get()

            assert (retAA, retAB, retBA, retBB, retBC, retBD) == (
                0x40 + i,
                0x80 + i,
                0x41 + i,
                0x42 + i,
                0x43 + i,
                0x44 + i,
            )


if __name__ == "__main__":
    test_memory()
