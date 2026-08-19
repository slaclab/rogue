#!/usr/bin/env python3
#-----------------------------------------------------------------------------
# Title      : Batcher combiner coverage benchmark
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
"""Coverage-gap-closure benchmark for the batcher_combining metric family
(combiner_count). None of the other tests/perf/ modules constructs a
batcher CombinerV1/CombinerV2 at all, so this module builds a Prbs master
feeding a CombinerV2 that queues frames, terminated by a bare
rogue.interfaces.stream.Slave() sink.

CombinerV2::getCount() returns the combiner's live queue depth
(queue_.size()), not a cumulative counter. This benchmark's workload never
calls the batch-send method: the queue grows monotonically across the
warmup repeat and every measured repeat, so the before-and-after delta
measure_benchmark takes for a given repeat equals exactly the number of
frames accepted into a batch during that repeat. The queue is drained by
one explicit batch-send call after the harness has taken its final
snapshot, proving the queued frames formed a real super-frame delivered to
the sink. The total memory held is HARNESS_FRAME_COUNT * FRAME_SIZE * (1 +
_perf_harness.DEFAULT_TARGET_CLEAN_SAMPLES), about 1.2 megabytes at the
values below, so the non-draining design is bounded and deliberate.

This module publishes no Tier 3 record and emits no wall-clock result of
its own kind, so it adds nothing to the gh-pages published series's
backward-compatible field set.
"""
import rogue.interfaces.stream
import rogue.protocols.batcher
import rogue.utilities
import rogue
import pytest

from tests.perf import _perf_harness

pytestmark = [pytest.mark.integration, pytest.mark.perf]

BENCHMARK_NAME = "batcher_combine_perf"

# Matches test_pool_alloc_perf.py's own values so the two coverage benchmarks' per-repeat
# workloads are directly comparable.
HARNESS_FRAME_COUNT = 200
FRAME_SIZE = 1000


def batcher_combine_path():

    # Prbs master feeding a CombinerV2, terminated by a bare Slave sink. sink is not
    # subclassed anywhere in this module.
    prbs_tx = rogue.utilities.Prbs()
    combiner = rogue.protocols.batcher.CombinerV2()
    sink = rogue.interfaces.stream.Slave()
    prbs_tx >> combiner >> sink

    # Correctness check before the harness call: a disconnected pipeline must fail loudly
    # here rather than measuring nothing. One probe frame raises the queue depth by exactly
    # one, then the drain below clears it so the measured region starts from an empty queue.
    prbs_tx.genFrame(FRAME_SIZE)
    assert combiner.getCount() == 1, (
        "prbs_tx >> combiner did not enqueue the generated probe frame"
    )
    combiner.sendBatch()
    assert combiner.getCount() == 0, "the probe-frame drain did not clear the queue"

    def _harness_repeat():
        for _ in range(HARNESS_FRAME_COUNT):
            prbs_tx.genFrame(FRAME_SIZE)

    harness_combiner_readers = {
        "combiner_count": combiner.getCount,
    }
    harness_counter_readers = {
        metric_name: harness_combiner_readers[metric_name]
        for metric_name in _perf_harness.perf_tier_registry.metrics_for_benchmark(BENCHMARK_NAME)
        if metric_name in harness_combiner_readers
    }
    harness_metrics = _perf_harness.measure_benchmark(
        BENCHMARK_NAME,
        _harness_repeat,
        harness_counter_readers,
        bytes_per_repeat=HARNESS_FRAME_COUNT * FRAME_SIZE,
        ops_per_repeat=HARNESS_FRAME_COUNT,
    )

    # Drain once, after the harness has taken its final snapshot: proves the queued frames
    # were real and formed a genuine super-frame rather than sitting unread.
    frame_count_before_drain = sink.getFrameCount()
    combiner.sendBatch()
    assert combiner.getCount() == 0, "the final drain did not empty the combiner's queue"
    assert sink.getFrameCount() - frame_count_before_drain == 1, (
        "the final drain did not deliver a super-frame to sink"
    )

    harness_record = _perf_harness.build_harness_record(
        BENCHMARK_NAME,
        harness_metrics,
        {"reduced_size": HARNESS_FRAME_COUNT, "full_size": HARNESS_FRAME_COUNT},
    )
    _perf_harness.emit_harness_result(harness_record, BENCHMARK_NAME)

    print("Done testing")


def test_batcher_combine_path():
    batcher_combine_path()


if __name__ == "__main__":
    test_batcher_combine_path()
