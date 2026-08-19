#!/usr/bin/env python3
#-----------------------------------------------------------------------------
# Title      : Pool allocation coverage benchmark
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
"""Coverage-gap-closure benchmark for the heap_allocations metric family
(pool_alloc_total_count, pool_alloc_total_bytes, pool_alloc_peak_bytes).
None of the other five tests/perf/ modules holds a Python-readable
rogue.interfaces.stream.Pool that mirrors its own real allocations, so
this module attaches a bare rogue.interfaces.stream.Slave() directly as a
Prbs master's primary slave: it is simultaneously the allocating Pool and
a real frame counter, since this module leaves the base Slave class's own
frame-accepting behaviour untouched, with no subclass anywhere here.

This module publishes no Tier 3 record and emits no wall-clock result of
its own kind, so it adds nothing to the gh-pages published series's
backward-compatible field set.
"""
import rogue.interfaces.stream
import rogue
import pytest

from tests.perf import _perf_harness

pytestmark = [pytest.mark.integration, pytest.mark.perf]

BENCHMARK_NAME = "pool_alloc_perf"

# Reduced per-repeat frame count, following test_fifo_perf.py's own derivation
# (FRAME_COUNT // 50): a deterministic count scales exactly with work and needs no long
# timing loop.
HARNESS_FRAME_COUNT = 200
FRAME_SIZE = 1000

PEAK_BYTES_METRIC = "pool_alloc_peak_bytes"


def _derive_pool_alloc_peak_bytes(harness_metrics, peak_bytes_samples):
    """pool_alloc_peak_bytes (Tier 1, a deterministic count) is an absolute high-water-mark
    reading, never a before-and-after delta: getAllocPeakBytes() is
    monotone non-decreasing, so once the warmup repeat has established the
    steady-state working set, every subsequent repeat's delta would be
    exactly zero. Wiring it as an ordinary counter_readers entry would
    therefore publish a bit-identical zero under a name that reads as a
    byte figure. Instead, this reads the absolute reading captured by the
    workload closure immediately after each measured repeat, dropping the
    one warmup-repeat reading the harness took before its first counted
    repeat, modelled line for line on test_fifo_perf.py's
    _derive_bytes_on_wire_ratio.
    """
    reference_entry = harness_metrics["pool_alloc_total_count"]
    completed_repeats = reference_entry["n_clean"]
    guard_exceeded = (
        reference_entry["status"] != _perf_harness.STATUS_OK
        and reference_entry["reason"] == _perf_harness.REASON_GUARD_EXCEEDED
    )
    samples = peak_bytes_samples[-completed_repeats:] if completed_repeats else []

    repeatability = _perf_harness.within_run_repeatability(samples)
    entry = {
        "tier_candidate": _perf_harness.perf_tier_registry.tier_for(PEAK_BYTES_METRIC),
        "within_run_repeatability": repeatability,
        "rejected_samples": [],
        "n_clean": len(samples),
        "samples": samples,
    }
    if repeatability.get("verdict") == _perf_harness.VERDICT_UNSTABLE:
        entry["tier_demoted_to"] = _perf_harness.perf_tier_registry.TIER_2
        entry["demotion_reason"] = _perf_harness.DEMOTED_TO_TIER_2
        entry["min"] = repeatability["min"]
        entry["max"] = repeatability["max"]
        entry["spread"] = repeatability["spread"]

    if len(samples) < _perf_harness.DEFAULT_TARGET_CLEAN_SAMPLES:
        entry["status"] = _perf_harness.STATUS_INCONCLUSIVE
        entry["reason"] = (
            _perf_harness.REASON_GUARD_EXCEEDED if guard_exceeded
            else _perf_harness.REASON_INSUFFICIENT_CLEAN_SAMPLES
        )
    else:
        entry["status"] = _perf_harness.STATUS_OK
        entry["reason"] = None
        entry["median"], entry["mad"] = _perf_harness.median_and_mad(samples)

    return entry


def pool_alloc_path():

    # PRBS master feeding a bare Slave sink. sink is not subclassed anywhere
    # in this module: the whole point is that the base Slave class's own
    # frame-accepting behaviour runs untouched, incrementing its frame/byte
    # counters and, via Master::reqFrame allocating from sink's own Pool,
    # its monotonic allocation counters too.
    prbs_tx = rogue.utilities.Prbs()
    sink = rogue.interfaces.stream.Slave()
    prbs_tx >> sink

    # Correctness check before the harness call: a disconnected pipeline
    # must fail loudly here rather than measuring nothing.
    frame_count_before = sink.getFrameCount()
    prbs_tx.genFrame(FRAME_SIZE)
    assert sink.getFrameCount() - frame_count_before == 1, (
        "prbs_tx >> sink did not deliver a generated frame to sink"
    )

    peak_bytes_samples = []

    def _harness_repeat():
        for _ in range(HARNESS_FRAME_COUNT):
            prbs_tx.genFrame(FRAME_SIZE)
        peak_bytes_samples.append(sink.getAllocPeakBytes())

    harness_pool_alloc_readers = {
        "pool_alloc_total_count": sink.getAllocTotalCount,
        "pool_alloc_total_bytes": sink.getAllocTotalBytes,
        "slave_frame_count": sink.getFrameCount,
        "slave_byte_count": sink.getByteCount,
    }
    harness_counter_readers = {
        metric_name: harness_pool_alloc_readers[metric_name]
        for metric_name in _perf_harness.perf_tier_registry.metrics_for_benchmark(BENCHMARK_NAME)
        if metric_name in harness_pool_alloc_readers
    }
    harness_metrics = _perf_harness.measure_benchmark(
        BENCHMARK_NAME,
        _harness_repeat,
        harness_counter_readers,
        bytes_per_repeat=HARNESS_FRAME_COUNT * FRAME_SIZE,
        ops_per_repeat=HARNESS_FRAME_COUNT,
    )
    harness_metrics[PEAK_BYTES_METRIC] = _derive_pool_alloc_peak_bytes(harness_metrics, peak_bytes_samples)

    # A future registry rescope that silently drops the slave_frame_accounting family from
    # this benchmark's scope must fail this module loudly rather than quietly shrinking the
    # emitted record.
    assert "slave_frame_count" in harness_metrics, "slave_frame_count missing from harness_metrics"
    assert "slave_byte_count" in harness_metrics, "slave_byte_count missing from harness_metrics"

    harness_record = _perf_harness.build_harness_record(
        BENCHMARK_NAME,
        harness_metrics,
        {"reduced_size": HARNESS_FRAME_COUNT, "full_size": HARNESS_FRAME_COUNT},
    )
    _perf_harness.emit_harness_result(harness_record, BENCHMARK_NAME)

    print("Done testing")


def test_pool_alloc_path():
    pool_alloc_path()


if __name__ == "__main__":
    test_pool_alloc_path()
