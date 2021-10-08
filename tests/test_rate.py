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

class TestDev(pr.Device):

    def __init__(self,**kwargs):

        super().__init__(**kwargs)
        self._localValue = 0

        self.add(pr.RemoteVariable(
            name         = "TestRemote",
            offset       =  0x1c,
            bitSize      =  32,
            bitOffset    =  0x00,
            base         = pr.UInt,
            mode         = "RW",
        ))

        self.add(pr.LocalVariable(
            name         = "TestLocal",
            mode         = "RW",
            value        = 0,
            localGet     = self._localGet,
            localSet     = self._localSet,
        ))

        self.add(pr.LinkVariable(
            name         = "TestLink",
            mode         = "RW",
            linkedSet    = self._linkedSet,
            linkedGet    = self._linkedGet,
        ))

    def _localSet(self, dev, var, value, changed):
        self._localValue = value

    def _localGet(self, dev, var):
        return self._localValue

    def _linkedSet(self, dev, var, value, write, index):
        self.TestRemote.set(value,write=write,index=index)

    def _linkedGet(self, dev, read, index):
        return self.TestRemote.get(read=read,index=index)


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

        self.add(TestDev(
            offset     = 0,
            memBase    = sim,
        ))


def test_rate():

    with DummyTree() as root:
        count = 100000

        stime = time.time()
        with root.updateGroup():
            for i in range(count):
                root.TestDev.TestRemote.set(i)
        remoteSetRate = 1/((time.time()-stime) / count)

        stime = time.time()
        with root.updateGroup():
            for i in range(count):
                root.TestDev.TestRemote.get()
        remoteGetRate = 1/((time.time()-stime) / count)

        stime = time.time()
        with root.updateGroup():
            for i in range(count):
                root.TestDev.TestLocal.set(i)
        localSetRate = 1/((time.time()-stime) / count)

        stime = time.time()
        with root.updateGroup():
            for i in range(count):
                root.TestDev.TestLocal.get()
        localGetRate = 1/((time.time()-stime) / count)

        stime = time.time()
        with root.updateGroup():
            for i in range(count):
                root.TestDev.TestLink.set(i)
        linkedSetRate = 1/((time.time()-stime) / count)

        stime = time.time()
        with root.updateGroup():
            for i in range(count):
                root.TestDev.TestLink.get(i)
        linkedGetRate = 1/((time.time()-stime) / count)

        print(f"Remote Set Rate = {remoteSetRate:.0f}")
        print(f"Remote Get Rate = {remoteGetRate:.0f}")
        print(f"Local  Set Rate = {localSetRate:.0f}")
        print(f"Local  Get Rate = {localGetRate:.0f}")
        print(f"Linked Set Rate = {linkedSetRate:.0f}")
        print(f"Linked Get Rate = {linkedGetRate:.0f}")


if __name__ == "__main__":
    test_rate()
