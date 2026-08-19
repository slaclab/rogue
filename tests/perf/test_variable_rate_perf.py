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
import rogue
import rogue.interfaces.memory
import time
import pytest
from tests.perf._perf_metrics import emit_perf_result
from tests.perf import _perf_harness

pytestmark = pytest.mark.perf

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

# Pre-existing tuned thresholds from the original x86/hwcounter-based test.
MaxCycles = { 'remoteSetRate'   : 8.0e9,
              'remoteSetNvRate' : 7.0e9,
              'remoteGetRate'   : 6.0e9,
              'localSetRate'    : 8.0e9,
              'localGetRate'    : 6.0e9,
              'linkedSetRate'   : 9.0e9,
              'linkedGetRate'   : 8.0e9 }

BENCH_COUNT = 100000
NOMINAL_CPU_HZ = 3.0e9

# Cross-platform fallback thresholds in ns/op derived from MaxCycles assuming
# NOMINAL_CPU_HZ and BENCH_COUNT.
MaxAvgNs = {
    k: (v * 1.0e9) / (NOMINAL_CPU_HZ * BENCH_COUNT)
    for k, v in MaxCycles.items()
}

# Tier 1 counter readers for the harness, one entry per
# rogue.PerfCounters getter perf_tier_registry.metrics_for_benchmark can
# assign to a transaction-path benchmark.
TIER1_COUNTER_READERS = {
    'gil_acquire_count': rogue.PerfCounters.getGilAcquireCount,
    'gil_release_count': rogue.PerfCounters.getGilReleaseCount,
    'scoped_gil_count': rogue.PerfCounters.getScopedGilCount,
    'transaction_create_count': rogue.PerfCounters.getTransactionCreateCount,
    'transaction_lock_acquisitions': rogue.PerfCounters.getTransactionLockCount,
    'transaction_request_bytes': rogue.PerfCounters.getTransactionRequestBytes,
    'transaction_request_count': rogue.PerfCounters.getTransactionRequestCount,
}

# Dual-clock CPU per-byte normalization: localSetRate/localGetRate
# issue no transaction at all (LocalVariable has no block/transaction path),
# so rogue.PerfCounters.getTransactionRequestBytes() records a permanent
# zero delta for them -- an unusable divisor. Every one of the seven
# operations here reads or writes the same 32-bit (4-byte) test value,
# whether or not that value crosses a real hardware transaction, so the
# register's own byte width is used uniformly instead of a per-benchmark
# measured delta that would be zero for two of the seven paths.
TRANSACTION_BYTES_PER_OP = 4

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
        count = BENCH_COUNT
        operations = {
            'remoteSetRate': lambda i: root.LocalDev.TestRemote.set(i),
            'remoteSetNvRate': lambda i: root.LocalDev.TestRemoteNoVerify.set(i),
            'remoteGetRate': lambda i: root.LocalDev.TestRemote.get(),
            'localSetRate': lambda i: root.LocalDev.TestLocal.set(i),
            'localGetRate': lambda i: root.LocalDev.TestLocal.get(),
            'linkedSetRate': lambda i: root.LocalDev.TestLink.set(i),
            'linkedGetRate': lambda i: root.LocalDev.TestLink.get(i),
        }

        for name, operation in operations.items():
            result = _measure_operation(root, count, operation)

            msg = (
                f"{name}: avg {result['avg_ns']:.2e} ns/op, "
                f"maximum {MaxAvgNs[name]:.2e} ns/op, "
                f"rate {result['rate_hz']:.2e} ops/s"
            )
            if HAS_HWCOUNTER:
                msg += (
                    f", cycles {result['cycles']:.2e} cycles, "
                    f"maximum {MaxCycles[name]:.2e} cycles"
                )
            print(msg)

            # Phase 1's authorized cycles demotion: the comparison and the
            # published threshold_pass field are retained, only the failure
            # accumulation and the aggregate assertion are removed.
            if HAS_HWCOUNTER:
                threshold_pass = result['cycles'] <= MaxCycles[name]
            else:
                threshold_pass = result['avg_ns'] <= MaxAvgNs[name]

            emit_perf_result(
                f"variable_rate_perf_{name}",
                benchmark=name,
                avg_ns=result['avg_ns'],
                rate_hz=result['rate_hz'],
                cycles=result.get('cycles'),
                threshold_pass=threshold_pass,
                max_avg_ns=MaxAvgNs[name],
                max_cycles=MaxCycles[name],
            )

            # Tiered measurement harness (warmup repeats, measured repeats, and a
            # per-benchmark wall-clock guard): one call per
            # operation, its own separate reduced-size loop with its own
            # counter snapshots, outside the timed region above.
            harness_reduced_count = max(1, BENCH_COUNT // 100)
            harness_counter_readers = {
                metric_name: TIER1_COUNTER_READERS[metric_name]
                for metric_name in _perf_harness.perf_tier_registry.metrics_for_benchmark(name)
                if metric_name in TIER1_COUNTER_READERS
            }
            harness_metrics = _perf_harness.measure_benchmark(
                name,
                lambda: _run_update_loop(root, harness_reduced_count, operation),
                harness_counter_readers,
                bytes_per_repeat=harness_reduced_count * TRANSACTION_BYTES_PER_OP,
                ops_per_repeat=harness_reduced_count,
            )
            harness_record = _perf_harness.build_harness_record(
                name,
                harness_metrics,
                {"reduced_size": harness_reduced_count, "full_size": BENCH_COUNT},
            )
            _perf_harness.emit_harness_result(harness_record, name)


    #pr.disable()

    #s = io.StringIO()
    #sortby = SortKey.CUMULATIVE
    #ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
    #ps.print_stats()
    #print(s.getvalue())

if __name__ == "__main__":
    test_rate()
