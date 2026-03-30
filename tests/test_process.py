#!/usr/bin/env python3
# ----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
# ----------------------------------------------------------------------------

import pyrogue
import queue
import threading
import time
import rogue.interfaces.memory

from pyrogue.protocols._uart import UartMemory


class LocalRoot(pyrogue.Root):
    def __init__(self):
        super().__init__(name="LocalRoot", description="Local root", pollEn=False)
        self.add(pyrogue.Process(name="Proc"))


def test_process_progress_helper_api_clamps_and_tracks_steps():
    with LocalRoot() as root:
        assert root.Proc.Progress.minimum is None
        assert root.Proc.Progress.maximum is None

        root.Proc.setProgress(1.5)
        assert root.Proc.Progress.value() == 1.0

        root.Proc.setProgress(-0.25)
        assert root.Proc.Progress.value() == 0.0

        root.Proc.setTotalSteps(4)
        root.Proc.setStep(2)
        assert root.Proc.Progress.value() == 0.5

        root.Proc.incrementSteps(10)
        assert root.Proc.Step.value() == 12
        assert root.Proc.Progress.value() == 1.0

        root.Proc.Progress.set(2.0)
        assert root.Proc.Progress.value() == 1.0

        root.Proc.Progress.set(-0.5)
        assert root.Proc.Progress.value() == 0.0


def test_process_progress_recomputes_on_direct_state_writes():
    with LocalRoot() as root:
        root.Proc.Step.set(5)
        assert root.Proc.Progress.value() == 1.0

        root.Proc.TotalSteps.set(10)
        assert root.Proc.Progress.value() == 0.5

        root.Proc.TotalSteps.set(0)
        assert root.Proc.Progress.value() == 0.0

        root.Proc.Step.set(-3)
        root.Proc.TotalSteps.set(4)
        assert root.Proc.Progress.value() == 0.0


class RunControlRoot(pyrogue.Root):
    def __init__(self):
        super().__init__(name="RunControlRoot", description="RunControl root", pollEn=False)
        self.add(RestartingRunControl(name="RC"))


class RestartingRunControl(pyrogue.RunControl):
    def __init__(self, **kwargs):
        self._runEntries = 0
        self._cmdCalls = 0
        self._stateLock = threading.Lock()
        super().__init__(
            rates={1000: "1000 Hz"},
            cmd=self._cmd,
            **kwargs,
        )

    def _cmd(self):
        with self._stateLock:
            self._cmdCalls += 1
            cmd_calls = self._cmdCalls

        if cmd_calls == 1:
            self.runState.set(0)
            self.runState.set(1)
        else:
            self.runState.set(0)

    def _run(self):
        with self._stateLock:
            self._runEntries += 1
        super()._run()


def test_runcontrol_does_not_spawn_second_thread_when_restarted_from_worker():
    with RunControlRoot() as root:
        root.RC.runState.set(1)

        deadline = time.time() + 2.0
        while time.time() < deadline:
            with root.RC._stateLock:
                done = root.RC._cmdCalls >= 2 and root.RC._thread is None
            if done:
                break
            time.sleep(0.01)

        assert root.RC._cmdCalls >= 2
        assert root.RC._runEntries == 1
        assert root.RC._thread is None


class FakeTransaction:
    def __init__(self, transaction_type):
        self._transaction_type = transaction_type
        self._lock = threading.Lock()
        self.errors = []
        self.done_called = False

    def lock(self):
        return self._lock

    def type(self):
        return self._transaction_type

    def error(self, msg):
        self.errors.append(msg)

    def done(self):
        self.done_called = True


def test_uart_worker_marks_task_done_when_transaction_raises():
    uart = UartMemory.__new__(UartMemory)
    uart._log = pyrogue.logInit(name="test-uart")
    uart._workerQueue = queue.Queue()

    def fail_transaction(transaction):
        raise ValueError("boom")

    uart._doWrite = fail_transaction
    uart._doRead = lambda transaction: None

    transaction = FakeTransaction(rogue.interfaces.memory.Write)
    uart._workerQueue.put(transaction)
    uart._workerQueue.put(None)

    uart._worker()

    assert uart._workerQueue.unfinished_tasks == 0
    assert not transaction.done_called
    assert len(transaction.errors) == 1
    assert "Unhandled UART worker exception: boom" in transaction.errors[0]
