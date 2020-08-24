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
            retryCount   = 2
        ))

        self.add(pr.RemoteVariable(
            name         = "SimpleTestAB",
            offset       =  0x1e,
            bitSize      =  16,
            bitOffset    =  0x00,
            base         = pr.UInt,
            mode         = "RW",
            retryCount   = 2
        ))

        self.add(pr.RemoteVariable(
            name         = "SimpleTestBA",
            offset       =  0x20,
            bitSize      =  8,
            bitOffset    =  0x00,
            base         = pr.UInt,
            mode         = "RW",
            retryCount   = 2
        ))

        self.add(pr.RemoteVariable(
            name         = "SimpleTestBB",
            offset       =  0x21,
            bitSize      =  8,
            bitOffset    =  0x00,
            base         = pr.UInt,
            mode         = "RW",
            retryCount   = 2
        ))

        self.add(pr.RemoteVariable(
            name         = "SimpleTestBC",
            offset       =  0x22,
            bitSize      =  8,
            bitOffset    =  0x00,
            base         = pr.UInt,
            mode         = "RW",
            retryCount   = 2
        ))

        self.add(pr.RemoteVariable(
            name         = "SimpleTestBD",
            offset       =  0x23,
            bitSize      =  8,
            bitOffset    =  0x00,
            base         = pr.UInt,
            mode         = "RW",
            retryCount   = 2
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
        sim = pr.interfaces.simulation.MemEmulate(dropCount=2)
        self.addInterface(sim)

        self.add(SimpleDev(
                name       = 'SimpleDev',
                offset     = 0x80000,
                memBase    = sim
            ))

def test_memory():

    with DummyTree() as root:

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

            if (retAA != 0x40 + i) or (retAB != 0x80 + i) or (retBA != 0x41 + i) or (retBB != 0x42 + i) or (retBC != 0x43 + i) or (retBD != 0x44 + i):
                raise AssertionError(f'Verification Failure: retAA={retAA}, retAB={retAB}, retBA={retBA}, retBB={retBB}, retBC={retBC}, retBD={retBD}')


if __name__ == "__main__":
    test_memory()
