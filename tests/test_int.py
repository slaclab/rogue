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

        self.add(SimpleDev(
                name       = 'SimpleDev',
                offset     = 0x80000,
                memBase    = sim,
            ))

def test_int():

    with DummyTree() as root:

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

        if (retAA != -1) or (retAB != 2) or (retBA != -2) or (retBB != -5) or (retBC != 7) or (retBD != -7):
            raise AssertionError(f'Verification Failure: retAA={retAA}, retAB={retAB}, retBA={retBA}, retBB={retBB}, retBC={retBC}, retBD={retBD}')


if __name__ == "__main__":
    test_int()
