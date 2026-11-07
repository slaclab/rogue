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
import datetime
import threading

import pyrogue as pr


class FakeRoot:
    def updateGroup(self):
        return contextlib.nullcontext()


class FakeBlock:
    def __init__(self, path):
        self.path = path
        self.variables = []


class UntimedWaitCondition(threading.Condition):
    """Condition that flags when a waiter blocks without a timeout."""
    def __init__(self):
        super().__init__(threading.RLock())
        self.untimed_wait = threading.Event()

    def wait(self, timeout=None):
        if timeout is None:
            self.untimed_wait.set()
        return super().wait(timeout)


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

    expired = list(pq._expiredEntries(datetime.datetime.now()))
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
    assert pq._entries[block].interval == datetime.timedelta(seconds=1.0)

    # Increasing the active variable interval should switch the block to the
    # next-fastest member still attached to that block.
    fast._pollInterval = 6.0
    pq.updatePollInterval(fast)
    assert pq._entries[block].interval == datetime.timedelta(seconds=5.0)

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
    assert pq._entries[block].readTime > datetime.datetime.now()


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


def test_poll_queue_stop_between_idle_check_and_wait_is_not_lost(wait_until, monkeypatch):
    pq = pr.PollQueue(root=FakeRoot())
    # Daemon so a regression fails the join assertion instead of hanging pytest
    pq._pollThread.daemon = True
    # Non-empty and paused, so the idle check consults paused()
    pq._addEntry(FakeBlock("idle.block"), 10.0)

    orig_paused = pq.paused
    stoppers = []

    def racing_paused():
        result = orig_paused()
        if not stoppers and threading.current_thread() is pq._pollThread:
            # Issue the stop from another thread after the idle check but
            # before the poll thread reaches its wait.
            stopper = threading.Thread(target=pq._stop, daemon=True)
            stoppers.append(stopper)
            stopper.start()
            wait_until(lambda: pq._run is False, timeout=0.2)
        return result

    monkeypatch.setattr(pq, "paused", racing_paused)

    pq._start()
    pq._pollThread.join(timeout=2.0)

    assert stoppers
    assert pq._pollThread.is_alive() is False
    stoppers[0].join(timeout=2.0)
    assert stoppers[0].is_alive() is False


def test_poll_queue_stop_during_poll_block_exits_without_unblocking(monkeypatch):
    pq = pr.PollQueue(root=FakeRoot())
    pq._pollThread.daemon = True
    pq._condLock = UntimedWaitCondition()
    calls = []

    monkeypatch.setattr(pr, "startTransaction", lambda block, **kwargs: calls.append(block))
    monkeypatch.setattr(pr, "waitTransaction", lambda block, **kwargs: None)

    pq.pause(False)
    pq._addEntry(FakeBlock("blocked.block"), 10.0)
    # Equivalent to holding a Root.pollBlock() section open
    pq._blockIncrement()
    pq._start()

    # The entry is due immediately, so the only untimed wait is the
    # block-count wait.
    assert pq._condLock.untimed_wait.wait(timeout=2.0)

    stopper = threading.Thread(target=pq._stop, daemon=True)
    stopper.start()
    stopper.join(timeout=2.0)

    assert stopper.is_alive() is False
    assert pq._pollThread.is_alive() is False
    assert pq.blockCount == 1
    assert calls == []
