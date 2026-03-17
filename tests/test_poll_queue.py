import contextlib
import datetime

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

    def fake_check(entry_block, **kwargs):
        calls.append(("check", entry_block.path))
        with pq._condLock:
            pq._run = False
            pq._condLock.notify()

    monkeypatch.setattr(pr, "startTransaction", fake_start)
    monkeypatch.setattr(pr, "checkTransaction", fake_check)

    pq._addEntry(block, 10.0)
    pq._start()

    assert wait_until(lambda: calls == [("start", "poll.block", 1), ("check", "poll.block")], timeout=1.0)
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
