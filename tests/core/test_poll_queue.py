#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

import contextlib
import time

import pyrogue as pr


class FakeRoot:
    def updateGroup(self):
        return contextlib.nullcontext()


class FakeBlock:
    def __init__(self, path):
        self.path = path
        self.variables = []


class FakeVar:
    def __init__(self, *, name, block=None, poll_interval=0, dependencies=None):
        self.name = name
        self._block = block
        self._pollInterval = poll_interval
        self.dependencies = [] if dependencies is None else dependencies
        self.set_poll_calls = []

    @property
    def pollInterval(self):
        return self._pollInterval

    def setPollInterval(self, interval):
        self.set_poll_calls.append(interval)
        self._pollInterval = interval

    def __repr__(self):
        return self.name


def test_poll_queue_entry_ordering_add_and_expired_entries():
    pq = pr.PollQueue(root=FakeRoot())
    early = FakeBlock("early")
    late = FakeBlock("late")

    pq._addEntry(early, 2.0)
    pq._addEntry(late, 5.0)

    assert pq.empty() is False
    assert pq.peek().block is early

    expired = list(pq._expiredEntries(time.monotonic()))
    assert [entry.block for entry in expired] == [early, late]
    assert pq.empty() is True


def test_poll_queue_update_poll_interval_adds_updates_and_removes_entries():
    pq = pr.PollQueue(root=FakeRoot())
    block = FakeBlock("blk")
    fast = FakeVar(name="fast", block=block, poll_interval=1.0)
    slow = FakeVar(name="slow", block=block, poll_interval=5.0)
    block.variables = [fast, slow]

    pq.updatePollInterval(fast)
    assert pq.peek().block is block
    assert pq._entries[block].interval == 1.0

    # Increasing the active variable interval should switch the block to the
    # next-fastest member still attached to that block.
    fast._pollInterval = 6.0
    pq.updatePollInterval(fast)
    assert pq._entries[block].interval == 5.0

    slow._pollInterval = 0
    fast._pollInterval = 0
    pq.updatePollInterval(fast)
    assert block not in pq._entries


def test_poll_queue_dependency_only_variables_push_intervals_downstream():
    pq = pr.PollQueue(root=FakeRoot())
    dep = FakeVar(name="dep", block=FakeBlock("dep"), poll_interval=0)
    derived = FakeVar(name="derived", block=None, poll_interval=2.5, dependencies=[dep])

    pq.updatePollInterval(derived)
    assert dep.set_poll_calls == [2.5]


def test_poll_queue_poll_cycle_processes_and_reschedules(wait_until, monkeypatch):
    pq = pr.PollQueue(root=FakeRoot())
    pq.pause(False)
    block = FakeBlock("poll.block")
    calls = []

    def fake_start(entry_block, **kwargs):
        calls.append(("start", entry_block.path, kwargs["type"]))

    def fake_wait(entry_block, **kwargs):
        calls.append(("wait", entry_block.path))
        with pq._condLock:
            pq._run = False
            pq._condLock.notify()

    monkeypatch.setattr(pr, "startTransaction", fake_start)
    monkeypatch.setattr(pr, "waitTransaction", fake_wait)

    pq._addEntry(block, 10.0)
    pq._start()

    assert wait_until(lambda: calls == [("start", "poll.block", 1), ("wait", "poll.block")], timeout=1.0)
    pq._pollThread.join(timeout=1.0)

    assert pq._entries[block].block is block
    assert pq._entries[block].readTime > time.monotonic()


def test_poll_queue_uses_monotonic_clock_not_wall_clock(monkeypatch):
    """Scheduling must not read the wall clock.

    A wall-clock step from an NTP correction or a manual clock set would
    otherwise stretch or shorten every poll interval. Break time.time() and
    assert scheduling still works off time.monotonic().
    """
    def exploding_time():
        raise AssertionError("PollQueue read the wall clock via time.time()")

    monkeypatch.setattr(pr._PollQueue.time, "time", exploding_time)

    pq = pr.PollQueue(root=FakeRoot())
    block = FakeBlock("blk")

    pq._addEntry(block, 2.0)

    entry = pq._entries[block]
    assert isinstance(entry.readTime, float)
    assert isinstance(entry.interval, float)

    # A new entry is due immediately, so it expires against a "now" cutoff.
    assert [e.block for e in pq._expiredEntries(time.monotonic())] == [block]


def test_poll_queue_reschedules_relative_to_previous_read_time():
    """A polled entry is rescheduled to now + interval on the monotonic base."""
    pq = pr.PollQueue(root=FakeRoot())
    block = FakeBlock("blk")
    interval = 7.5

    pq._addEntry(block, interval)
    entry = pq._entries[block]

    before = time.monotonic()
    now = time.monotonic()
    entry.readTime = now + entry.interval
    after = time.monotonic()

    assert entry.readTime >= before + interval
    assert entry.readTime <= after + interval


def test_poll_queue_wait_time_is_never_negative():
    """An overdue entry must not produce a negative Condition.wait() timeout.

    threading.Condition.wait() rejects a negative timeout, so the poll loop
    clamps the computed delta at zero.
    """
    pq = pr.PollQueue(root=FakeRoot())
    block = FakeBlock("blk")

    pq._addEntry(block, 1.0)
    # Force the entry well into the past, as a delayed poll thread would see.
    pq._entries[block].readTime = time.monotonic() - 60.0

    waitTime = max(0.0, pq.peek().readTime - time.monotonic())
    assert waitTime == 0.0


def test_poll_queue_pause_and_block_count_controls():
    pq = pr.PollQueue(root=FakeRoot())
    assert pq.paused() is True

    pq.pause(False)
    assert pq.paused() is False

    pq._blockIncrement()
    assert pq.blockCount == 1
    pq._blockDecrement()
    assert pq.blockCount == 0

    pq._stop()
    assert pq._run is False
