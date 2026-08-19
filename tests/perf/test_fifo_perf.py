#!/usr/bin/env python3
#-----------------------------------------------------------------------------
# Title      : FIFO stream performance test
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
import rogue.interfaces.stream
import rogue
import time
import pytest

from tests.perf._perf_metrics import emit_perf_result
from tests.perf import _perf_harness

pytestmark = [pytest.mark.integration, pytest.mark.perf]

#rogue.Logging.setLevel(rogue.Logging.Debug)

# Preserve the original larger FIFO workload as the recorded soak benchmark.
FRAME_COUNT = 10000
FRAME_SIZE = 10000
FRAME_DRAIN_POLLS = 300
FRAME_DRAIN_INTERVAL = 0.1


def _derive_bytes_on_wire_ratio(harness_metrics):
    """bytes_on_wire_ratio (Tier 1) is io_bytes over prbs_tx_bytes,
    derived here from the two Tier 1 counters _perf_harness.measure_benchmark
    already collected per repeat -- both share the same repeat set and guard
    outcome, so their per-repeat sample lists line up index for index --
    rather than a raw counter this harness could read and delta on its own.
    """
    io_entry = harness_metrics['io_bytes']
    tx_entry = harness_metrics['prbs_tx_bytes']
    ratios = [
        (io / tx) if tx else 0.0
        for io, tx in zip(io_entry['samples'], tx_entry['samples'])
    ]
    repeatability = _perf_harness.within_run_repeatability(ratios)
    entry = {
        'tier_candidate': _perf_harness.perf_tier_registry.TIER_1,
        'within_run_repeatability': repeatability,
        'rejected_samples': [],
        'n_clean': len(ratios),
        'samples': ratios,
        'status': io_entry['status'],
        'reason': io_entry['reason'],
    }
    if repeatability.get('verdict') == _perf_harness.VERDICT_UNSTABLE:
        entry['tier_demoted_to'] = _perf_harness.perf_tier_registry.TIER_2
        entry['demotion_reason'] = _perf_harness.DEMOTED_TO_TIER_2
        entry['min'] = repeatability['min']
        entry['max'] = repeatability['max']
        entry['spread'] = repeatability['spread']
    if entry['status'] == _perf_harness.STATUS_OK:
        entry['median'], entry['mad'] = _perf_harness.median_and_mad(ratios)
    return entry


def fifo_path():

    # PRBS
    prbs_tx = rogue.utilities.Prbs()
    prbs_rx = rogue.utilities.Prbs()

    # FIFO
    fifo = rogue.interfaces.stream.Fifo(0, 0, False)

    # Client stream
    prbs_tx >> fifo >> prbs_rx

    prbs_rx.checkPayload(True)

    print("Generating Frames")
    start = time.perf_counter()
    for _ in range(FRAME_COUNT):
        prbs_tx.genFrame(FRAME_SIZE)

    for _ in range(FRAME_DRAIN_POLLS):
        if prbs_rx.getRxCount() == FRAME_COUNT:
            break
        time.sleep(FRAME_DRAIN_INTERVAL)

    elapsed = time.perf_counter() - start
    received = prbs_rx.getRxCount()
    errors = prbs_rx.getRxErrors()
    result = emit_perf_result(
        "fifo_perf",
        frames_sent=FRAME_COUNT,
        frames_received=received,
        frame_size=FRAME_SIZE,
        elapsed_sec=elapsed,
        throughput_mb_s=((received * FRAME_SIZE) / (1024.0 * 1024.0)) / elapsed if elapsed > 0 else 0.0,
        rx_errors=errors,
        drain_complete=(received == FRAME_COUNT),
    )

    print(f"Perf metrics: {result}")

    assert received > 0, "No frames were received during the FIFO perf run"
    assert errors == 0, f"PRBS frame errors detected: {errors}"
    assert received == FRAME_COUNT, f"Frame count error. Got = {received} expected = {FRAME_COUNT}"

    # Tiered measurement harness (warmup repeats, measured repeats, a per-benchmark
    # wall-clock guard, and contamination rejection): a separate
    # reduced-size loop with its own counter snapshots, run after this
    # module's Tier 3 region and its drain wait have completed, on the same
    # already-built prbs_tx/fifo/prbs_rx chain.
    harness_reduced_count = max(1, FRAME_COUNT // 50)

    def _harness_repeat():
        target = prbs_rx.getRxCount() + harness_reduced_count
        for _ in range(harness_reduced_count):
            prbs_tx.genFrame(FRAME_SIZE)
        for _ in range(FRAME_DRAIN_POLLS):
            if prbs_rx.getRxCount() >= target:
                break
            time.sleep(FRAME_DRAIN_INTERVAL)

    harness_stream_readers = {
        'buffer_copy_bytes': rogue.PerfCounters.getBufferCopyBytes,
        'buffer_copy_count': rogue.PerfCounters.getBufferCopyCount,
        'frame_create_count': rogue.PerfCounters.getFrameCreateCount,
        'frame_lock_acquisitions': rogue.PerfCounters.getFrameLockCount,
        'gil_acquire_count': rogue.PerfCounters.getGilAcquireCount,
        'gil_release_count': rogue.PerfCounters.getGilReleaseCount,
        'scoped_gil_count': rogue.PerfCounters.getScopedGilCount,
        'io_call_count': rogue.PerfCounters.getIoCallCount,
        'io_bytes': rogue.PerfCounters.getIoBytes,
        'prbs_rx_count': prbs_rx.getRxCount,
        'prbs_rx_bytes': prbs_rx.getRxBytes,
        'prbs_rx_errors': prbs_rx.getRxErrors,
        'prbs_tx_count': prbs_tx.getTxCount,
        'prbs_tx_bytes': prbs_tx.getTxBytes,
        'prbs_tx_errors': prbs_tx.getTxErrors,
    }
    harness_counter_readers = {
        metric_name: harness_stream_readers[metric_name]
        for metric_name in _perf_harness.perf_tier_registry.metrics_for_benchmark("fifo_perf")
        if metric_name in harness_stream_readers
    }
    harness_metrics = _perf_harness.measure_benchmark(
        "fifo_perf",
        _harness_repeat,
        harness_counter_readers,
        bytes_per_repeat=harness_reduced_count * FRAME_SIZE,
        ops_per_repeat=harness_reduced_count,
    )
    harness_metrics['bytes_on_wire_ratio'] = _derive_bytes_on_wire_ratio(harness_metrics)
    harness_record = _perf_harness.build_harness_record(
        "fifo_perf",
        harness_metrics,
        {"reduced_size": harness_reduced_count, "full_size": FRAME_COUNT},
    )
    _perf_harness.emit_harness_result(harness_record, "fifo_perf")

    print("Done testing")


def test_fifo_path():
    fifo_path()


if __name__ == "__main__":
    test_fifo_path()
