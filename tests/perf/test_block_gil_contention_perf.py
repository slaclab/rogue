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

pytestmark = pytest.mark.perf

# Mirrors the ~42k entry update-queue drain from the #1262 report.
DRAIN_COUNT = 42000

# Host-robust ceiling. Pre-fix the contended drain runs in the tens of seconds
# (the reported 42-126 s stall under load); post-fix it completes in well under
# a second on any CI host, so a wide margin keeps the test deterministic.
CEILING_S = 10.0


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


if __name__ == "__main__":
    test_block_getset_drain_under_gil_contention()
