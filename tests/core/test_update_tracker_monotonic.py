#!/usr/bin/env python3
#-----------------------------------------------------------------------------
# Title      : UpdateTracker monotonic-clock flush regression tests
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
# UpdateTracker flushes batched variable updates once its period has elapsed.
# Measuring that period against the wall clock made the flush vulnerable to an
# NTP correction or a manual clock set: a backward step stalls batched updates
# for the duration of the jump, a forward step flushes early. These tests pin
# the flush to the monotonic clock.

import queue
import time
from types import SimpleNamespace

import pyrogue as pr


def _tracker():
    return pr._Root.UpdateTracker(queue.Queue())


def _var(path):
    return SimpleNamespace(path=path)


def test_update_tracker_flush_ignores_wall_clock_jumps(monkeypatch):
    """A wall-clock step must not affect flush timing."""
    def exploding_time():
        raise AssertionError("UpdateTracker read the wall clock via time.time()")

    monkeypatch.setattr(pr._Root.time, "time", exploding_time)

    var = _var("Top.A")
    tracker = _tracker()
    tracker.increment(period=10.0)
    tracker.update(var)

    # Period has not elapsed on the monotonic clock, so nothing is flushed.
    assert tracker._q.empty()

    # Closing the group flushes regardless of period.
    tracker.decrement()
    assert tracker._q.get_nowait() == {"Top.A": var}
    assert tracker._q.empty()


def test_update_tracker_flushes_once_monotonic_period_elapses(monkeypatch):
    """Flush fires when the monotonic period is exceeded, not the wall period."""
    fake_now = {"t": 1000.0}

    monkeypatch.setattr(pr._Root.time, "monotonic", lambda: fake_now["t"])

    tracker = _tracker()
    tracker.increment(period=5.0)

    tracker.update(_var("Top.A"))
    assert tracker._q.empty(), "flushed before the period elapsed"

    # Advance the monotonic clock past the period.
    fake_now["t"] += 6.0
    tracker.update(_var("Top.B"))

    batch = tracker._q.get_nowait()
    assert set(batch) == {"Top.A", "Top.B"}


def test_update_tracker_period_baseline_is_monotonic():
    """The flush baseline is seeded from the monotonic clock."""
    before = time.monotonic()
    tracker = _tracker()
    after = time.monotonic()

    assert before <= tracker._last <= after
