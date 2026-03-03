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

try:
    import hwcounter
    HAS_HWCOUNTER = True
except ImportError:
    HAS_HWCOUNTER = False

#import cProfile, pstats, io
#from pstats import SortKey

#rogue.Logging.setLevel(rogue.Logging.Debug)
#import logging
#logger = logging.getLogger('pyrogue')
#logger.setLevel(logging.DEBUG)

MaxAvgNs = { 'remoteSetRate'   : 1.0e6,
             'remoteSetNvRate' : 1.0e6,
             'remoteGetRate'   : 1.0e6,
             'localSetRate'    : 1.0e6,
             'localGetRate'    : 1.0e6,
             'linkedSetRate'   : 1.0e6,
             'linkedGetRate'   : 1.0e6 }

class LocalDev(pr.Device):

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

        self.add(LocalDev(
            offset     = 0,
            memBase    = sim,
        ))


def _run_update_loop(root, count, operation):
    with root.updateGroup():
        for i in range(count):
            operation(i)


def _measure_operation(root, count, operation):
    start_ns = time.perf_counter_ns()
    start_cycles = hwcounter.count() if HAS_HWCOUNTER else None
    _run_update_loop(root, count, operation)
    elapsed_ns = time.perf_counter_ns() - start_ns

    result = {
        'avg_ns': float(elapsed_ns) / count,
        'rate_hz': int(count / (elapsed_ns / 1.0e9)),
    }

    if HAS_HWCOUNTER:
        result['cycles'] = float(hwcounter.count_end() - start_cycles)

    return result


def test_rate():

    #pr = cProfile.Profile()
    #pr.enable()

    with DummyTree() as root:
        count = 100000
        operations = {
            'remoteSetRate': lambda i: root.LocalDev.TestRemote.set(i),
            'remoteSetNvRate': lambda i: root.LocalDev.TestRemoteNoVerify.set(i),
            'remoteGetRate': lambda i: root.LocalDev.TestRemote.get(),
            'localSetRate': lambda i: root.LocalDev.TestLocal.set(i),
            'localGetRate': lambda i: root.LocalDev.TestLocal.get(),
            'linkedSetRate': lambda i: root.LocalDev.TestLink.set(i),
            'linkedGetRate': lambda i: root.LocalDev.TestLink.get(i),
        }

        failures = []

        for name, operation in operations.items():
            result = _measure_operation(root, count, operation)

            msg = (
                f"{name} avg_ns {result['avg_ns']:.2e}, "
                f"maximum {MaxAvgNs[name]:.2e}, rate {result['rate_hz']}"
            )
            if HAS_HWCOUNTER:
                msg += f", cycles {result['cycles']:.2e}"
            print(msg)

            if result['avg_ns'] > MaxAvgNs[name]:
                failures.append(
                    f"{name}: avg_ns {result['avg_ns']:.2e} > {MaxAvgNs[name]:.2e}"
                )

        assert not failures, "Rate check failed:\n" + "\n".join(failures)


    #pr.disable()

    #s = io.StringIO()
    #sortby = SortKey.CUMULATIVE
    #ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
    #ps.print_stats()
    #print(s.getvalue())

if __name__ == "__main__":
    test_rate()
