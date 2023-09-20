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
import pyrogue as pr
import pyrogue.interfaces.simulation
import rogue.interfaces.memory
import time
import hwcounter

#rogue.Logging.setLevel(rogue.Logging.Debug)
#import logging
#logger = logging.getLogger('pyrogue')
#logger.setLevel(logging.DEBUG)

MaxCycles = { 'remoteSetRate'   : 5.9e9,
              'remoteSetNvRate' : 5.5e9,
              'remoteGetRate'   : 4.8e9,
              'localSetRate'    : 6.8e9,
              'localGetRate'    : 4.6e9,
              'linkedSetRate'   : 6.9e9,
              'linkedGetRate'   : 5.5e9 }

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

        self.add(pr.RemoteVariable(
            name         = "TestRemoteNoVerify",
            offset       =  0x08,
            verify       = False,
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
                         pollEn=False)

        # Use a memory space emulator
        sim = rogue.interfaces.memory.Emulate(4,0x1000)
        #sim = pr.interfaces.simulation.MemEmulate()
        self.addInterface(sim)

        self.add(TestDev(
            offset     = 0,
            memBase    = sim,
        ))


def test_rate():

    with DummyTree() as root:
        count = 100000
        resultRate = {}
        resultCycles = {}

        stime = time.time()
        scount = hwcounter.count()
        with root.updateGroup():
            for i in range(count):
                root.TestDev.TestRemote.set(i)
        resultCycles['remoteSetRate'] = float(hwcounter.count_end() - scount)
        resultRate['remoteSetRate'] = int(1/((time.time()-stime) / count))

        stime = time.time()
        scount = hwcounter.count()
        with root.updateGroup():
            for i in range(count):
                root.TestDev.TestRemoteNoVerify.set(i)
        resultCycles['remoteSetNvRate'] = float(hwcounter.count_end() - scount)
        resultRate['remoteSetNvRate'] = int(1/((time.time()-stime) / count))

        stime = time.time()
        scount = hwcounter.count()
        with root.updateGroup():
            for i in range(count):
                root.TestDev.TestRemote.get()
        resultCycles['remoteGetRate'] = float(hwcounter.count_end() - scount)
        resultRate['remoteGetRate'] = int(1/((time.time()-stime) / count))

        stime = time.time()
        scount = hwcounter.count()
        with root.updateGroup():
            for i in range(count):
                root.TestDev.TestLocal.set(i)
        resultCycles['localSetRate'] = float(hwcounter.count_end() - scount)
        resultRate['localSetRate'] = int(1/((time.time()-stime) / count))

        stime = time.time()
        scount = hwcounter.count()
        with root.updateGroup():
            for i in range(count):
                root.TestDev.TestLocal.get()
        resultCycles['localGetRate'] = float(hwcounter.count_end() - scount)
        resultRate['localGetRate'] = int(1/((time.time()-stime) / count))

        stime = time.time()
        scount = hwcounter.count()
        with root.updateGroup():
            for i in range(count):
                root.TestDev.TestLink.set(i)
        resultCycles['linkedSetRate'] = float(hwcounter.count_end() - scount)
        resultRate['linkedSetRate'] = int(1/((time.time()-stime) / count))

        stime = time.time()
        scount = hwcounter.count()
        with root.updateGroup():
            for i in range(count):
                root.TestDev.TestLink.get(i)
        resultCycles['linkedGetRate'] = float(hwcounter.count_end() - scount)
        resultRate['linkedGetRate'] = int(1/((time.time()-stime) / count))

        passed = True

        for k,v in MaxCycles.items():

            print(f"{k} cyles {resultCycles[k]:.2e}, maximum {v:.2e}, rate {resultRate[k]}")

            if resultCycles[k] > v:
                passed = False

        if passed is False:
            raise AssertionError('Rate check failed')

if __name__ == "__main__":
    test_rate()
