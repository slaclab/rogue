#!/usr/bin/env python3
#-----------------------------------------------------------------------------
# Title      : Block getBytes/setBytes GIL-contention drain perf regression
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
#
# Reproduces SLAC rogue #1262: the v6 update-queue drain stalls because
# Block::getBytes / Block::setBytes released the Python GIL unconditionally on
# every call. During a bulk drain (~42k staged variable updates) that is ~42k
# PyEval_SaveThread/PyEval_RestoreThread cycles; with another Python thread
# contending for the GIL, each hand-off costs milliseconds and the drain stalls
# for tens of seconds.
#
# This test drives a ~42k staged set(write=False)/get(read=False) drain -- the
# pure Block::setBytes/getBytes path, no hardware transaction -- while a busy
# pure-Python thread contends for the GIL. The drain is timed both with and
# without the contender. Pre-fix the contended drain blows past the ceiling;
# post-fix the uncontended fast path keeps the GIL and the drain stays fast.

import threading
import time

import pyrogue as pr
import pytest
import rogue.interfaces.memory

from tests.perf._perf_metrics import emit_perf_result
from tests.perf import _perf_harness

pytestmark = pytest.mark.perf

# Mirrors the ~42k entry update-queue drain from the #1262 report.
DRAIN_COUNT = 42000

# Host-robust ceiling. Pre-fix the contended drain runs in the tens of seconds
# (the reported 42-126 s stall under load); post-fix it completes in well under
# a second on any CI host, so a wide margin keeps the test deterministic.
CEILING_S = 10.0

# Dual-clock CPU per-byte normalization: the pure staged
# set(write=False)/get(read=False) drain this benchmark exercises issues no
# transaction at all (write=False skips writeBlocks(), read=False skips
# readBlocks()), so rogue.PerfCounters.getTransactionRequestBytes() would
# record a permanent zero delta here -- an unusable divisor. Reg's own byte
# width (32 bits) is used instead, a deterministic nonzero unit of work.
REG_BYTE_WIDTH = 4


class _DrainRoot(pr.Root):
    def __init__(self) -> None:
        super().__init__(name="DrainRoot", description="GIL contention drain", pollEn=False)
        sim = rogue.interfaces.memory.Emulate(4, 0x1000)
        self.addInterface(sim)
        self.add(pr.Device(name="Dev", offset=0, memBase=sim))
        self.Dev.add(pr.RemoteVariable(
            name="Reg",
            offset=0,
            bitOffset=0,
            bitSize=32,
            base=pr.UInt,
            mode="RW",
        ))


def _spawn_gil_contender(stop_event):
    """Always-runnable pure-Python thread that maximizes GIL hand-off cost.

    It never blocks on I/O, so it is always ready to grab the GIL the instant a
    pre-fix getBytes/setBytes releases it -- which is exactly what turns each
    release/re-acquire into a multi-millisecond stall under the interpreter's
    GIL hand-off interval.
    """
    def churn():
        x = 0
        while not stop_event.is_set():
            x = (x + 1) % 1_000_003
    t = threading.Thread(target=churn, daemon=True)
    t.start()
    return t


def _drain(var, count):
    """Pure staged set/get drain: setBytes via set(write=False), getBytes via
    get(read=False). No transaction is issued, so the Block mutex is
    uncontended; the only variable is whether the GIL is thrashed per call."""
    for i in range(count):
        var.set(i & 0xFFFFFFFF, write=False)
        var.get(read=False)


def test_block_getset_drain_under_gil_contention():
    with _DrainRoot() as root:
        var = root.Dev.Reg

        # Baseline drain with no GIL contender.
        start = time.perf_counter()
        _drain(var, DRAIN_COUNT)
        baseline_s = time.perf_counter() - start

        # Drain again with a background GIL-contending thread.
        stop = threading.Event()
        contender = _spawn_gil_contender(stop)
        try:
            time.sleep(0.05)
            start = time.perf_counter()
            _drain(var, DRAIN_COUNT)
            contended_s = time.perf_counter() - start
        finally:
            stop.set()
            contender.join(timeout=5.0)

        ratio = contended_s / baseline_s if baseline_s > 0 else float("inf")
        threshold_pass = contended_s < CEILING_S

        print(
            f"drain {DRAIN_COUNT}: baseline {baseline_s:.3f}s, "
            f"contended {contended_s:.3f}s, ratio {ratio:.1f}x, "
            f"ceiling {CEILING_S:.1f}s"
        )

        emit_perf_result(
            "block_gil_contention_drain",
            drain_count=DRAIN_COUNT,
            baseline_s=baseline_s,
            contended_s=contended_s,
            slowdown_ratio=ratio,
            ceiling_s=CEILING_S,
            threshold_pass=threshold_pass,
        )

        # The contended drain is the #1262 regression signal. Pre-fix it trips
        # the ceiling (tens of seconds); post-fix it stays well under it.
        assert threshold_pass, (
            f"contended drain took {contended_s:.2f}s (>{CEILING_S:.1f}s ceiling); "
            f"baseline {baseline_s:.2f}s, slowdown {ratio:.1f}x -- #1262 GIL thrash"
        )

        # Tiered measurement harness (warmup repeats, measured repeats, a per-benchmark
        # wall-clock guard, and contamination rejection): a
        # separate reduced-drain-count loop, each repeat running its own
        # baseline and its own contended pass (with its own spawned/joined
        # GIL contender) so slowdown_ratio is a genuine per-repeat sample
        # rather than one figure repeated k times.
        harness_reduced_count = max(1, DRAIN_COUNT // 100)
        harness_slowdown_samples = []

        def _harness_repeat():
            harness_start = time.perf_counter()
            _drain(var, harness_reduced_count)
            harness_baseline_s = time.perf_counter() - harness_start

            harness_stop = threading.Event()
            harness_contender = _spawn_gil_contender(harness_stop)
            try:
                harness_start = time.perf_counter()
                _drain(var, harness_reduced_count)
                harness_contended_s = time.perf_counter() - harness_start
            finally:
                harness_stop.set()
                harness_contender.join(timeout=5.0)

            harness_slowdown_samples.append(
                harness_contended_s / harness_baseline_s if harness_baseline_s > 0 else float("inf")
            )

        harness_gil_readers = {
            'gil_acquire_count': rogue.PerfCounters.getGilAcquireCount,
            'gil_release_count': rogue.PerfCounters.getGilReleaseCount,
            'scoped_gil_count': rogue.PerfCounters.getScopedGilCount,
        }
        harness_counter_readers = {
            metric_name: harness_gil_readers[metric_name]
            for metric_name in _perf_harness.perf_tier_registry.metrics_for_benchmark(
                "block_gil_contention_drain"
            )
            if metric_name in harness_gil_readers
        }
        harness_metrics = _perf_harness.measure_benchmark(
            "block_gil_contention_drain",
            _harness_repeat,
            harness_counter_readers,
            bytes_per_repeat=harness_reduced_count * REG_BYTE_WIDTH,
            ops_per_repeat=harness_reduced_count,
        )

        # slowdown_ratio (Tier 2, a normalized cost): derived from the per-repeat samples
        # _harness_repeat appended above, discarding the leading
        # warmup-repeat sample the harness ran before its first counted
        # repeat. Every Tier 1 metric collected in the same call shares the
        # same completed-repeat count, so gil_acquire_count's own n_clean and
        # guard outcome apply here too.
        reference_entry = harness_metrics['gil_acquire_count']
        guard_exceeded = (
            reference_entry['status'] != _perf_harness.STATUS_OK
            and reference_entry['reason'] == _perf_harness.REASON_GUARD_EXCEEDED
        )
        completed_repeats = reference_entry['n_clean']
        slowdown_samples = harness_slowdown_samples[-completed_repeats:] if completed_repeats else []
        rejected_indices = set(_perf_harness.mad_band_rejections(slowdown_samples))
        slowdown_entry = {
            'tier_candidate': _perf_harness.perf_tier_registry.TIER_2,
            'rejected_samples': [
                {'index': index, 'value': slowdown_samples[index], 'reason': _perf_harness.REJECTION_MAD_BAND}
                for index in sorted(rejected_indices)
            ],
        }
        accepted_slowdown = [
            value for index, value in enumerate(slowdown_samples) if index not in rejected_indices
        ]
        slowdown_entry['n_clean'] = len(accepted_slowdown)
        slowdown_entry['samples'] = accepted_slowdown
        if len(accepted_slowdown) < _perf_harness.DEFAULT_TARGET_CLEAN_SAMPLES:
            slowdown_entry['status'] = _perf_harness.STATUS_INCONCLUSIVE
            slowdown_entry['reason'] = (
                _perf_harness.REASON_GUARD_EXCEEDED if guard_exceeded
                else _perf_harness.REASON_INSUFFICIENT_CLEAN_SAMPLES
            )
        else:
            slowdown_entry['status'] = _perf_harness.STATUS_OK
            slowdown_entry['reason'] = None
            slowdown_entry['median'], slowdown_entry['mad'] = _perf_harness.median_and_mad(accepted_slowdown)
        harness_metrics['slowdown_ratio'] = slowdown_entry

        harness_record = _perf_harness.build_harness_record(
            "block_gil_contention_drain",
            harness_metrics,
            {"reduced_size": harness_reduced_count, "full_size": DRAIN_COUNT},
        )
        _perf_harness.emit_harness_result(harness_record, "block_gil_contention_drain")


if __name__ == "__main__":
    test_block_getset_drain_under_gil_contention()
