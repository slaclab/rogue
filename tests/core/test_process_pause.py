#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

import threading
from contextlib import contextmanager

import pytest

import pyrogue as pr


@contextmanager
def process_root(function):
    root = pr.Root(name="root", pollEn=False)
    root.add(pr.Process(
        name="Proc", function=function,
        argVariable=pr.LocalVariable(name="Arg", value=0),
        returnVariable=pr.LocalVariable(name="Result", value=-1),
    ))
    root.Proc.add(pr.LocalVariable(name="Snapshot", value=-1))
    with root:
        # Disable periodic leaking to prove pause updates are explicitly flushed.
        root.Proc.UpdatePeriod.set(0.0)
        yield root


def join_worker(proc):
    proc._thread.join(timeout=2.0)
    assert not proc._thread.is_alive()
    assert proc.Running.value() is False
    assert proc.Paused.value() is False


def test_pause_resume_preserves_worker_and_publishes_snapshot(wait_until):
    ready = [threading.Event(), threading.Event()]
    advance = [threading.Event(), threading.Event()]
    completed = []
    publications = []
    updates = []

    def run(*, dev, arg):
        for step in range(2):
            def publish():
                publications.append((step, threading.get_ident()))
                dev.Snapshot.set(step)

            # Nested grouping must survive the checkpoint flush too.
            with dev.root.updateGroup():
                dev.setProgress(step / 2)
                ready[step].set()
                assert advance[step].wait(timeout=2.0)
                if not dev.pausePoint(publish=publish):
                    return -1
                completed.append(step)
        return arg

    with process_root(run) as root:
        proc = root.Proc
        root.addVarListener(lambda path, value: updates.append((path, value.value)))
        proc(17)
        worker = proc._thread
        try:
            for step in range(2):
                assert ready[step].wait(timeout=2.0)
                proc.Pause()
                proc.Pause()
                assert proc.Paused.value() is False
                advance[step].set()
                assert wait_until(lambda: proc.Paused.value())
                assert wait_until(lambda: (proc.Snapshot.path, step) in updates)
                assert wait_until(lambda: (proc.Paused.path, True) in updates)
                assert publications[step] == (step, worker.ident)
                assert proc.Running.value() is True
                assert proc.Progress.value() == step / 2
                assert proc.Message.value() == "Running"
                assert completed == list(range(step))

                # Neither entry point starts a second worker or changes its arg.
                proc.Start()
                proc(99)
                assert proc._thread is worker
                assert proc.Arg.value() == 17
                proc.Resume()
                assert wait_until(lambda: not proc.Paused.value())

            join_worker(proc)
            assert completed == [0, 1]
            assert proc.Result.value() == 17
            assert proc.Progress.value() == 1.0
            assert proc.Message.value() == "Done"
        finally:
            for event in advance:
                event.set()
            proc.Stop()


@pytest.mark.parametrize("shutdown", [False, True])
def test_stop_or_root_shutdown_wakes_paused_worker(wait_until, shutdown):
    entered = threading.Event()
    advance = threading.Event()

    def run(*, dev):
        dev.setProgress(0.25)
        entered.set()
        assert advance.wait(timeout=2.0)
        return 1 if dev.pausePoint() else 0

    with process_root(run) as root:
        proc = root.Proc
        proc.Start()
        assert entered.wait(timeout=2.0)
        proc.Pause()
        advance.set()
        assert wait_until(lambda: proc.Paused.value())
        if shutdown:
            root.stop()
        else:
            proc.Stop()
        join_worker(proc)
        assert proc.Result.value() == 0
        assert proc.Message.value() == "Stopped"
        assert proc.Progress.value() == 0.25
        assert proc.pausePoint() is False

        if not shutdown:
            # Stop must clear the request so the next run does not pause.
            proc.Start()
            join_worker(proc)
            assert proc.Result.value() == 1
            assert proc.Message.value() == "Done"


@pytest.mark.parametrize("action", ["cancel", "no-checkpoint", "error"])
def test_pending_pause_cancellation_and_exit_cleanup(action):
    entered = threading.Event()
    advance = threading.Event()
    calls = []

    def run(*, dev):
        entered.set()
        assert advance.wait(timeout=2.0)
        if not calls:
            calls.append(1)
            if action == "error":
                raise RuntimeError("failed before checkpoint")
            if action == "no-checkpoint":
                return 1
        assert dev.pausePoint(publish=lambda: pytest.fail("unexpected pause"))
        return 2

    with process_root(run) as root:
        proc = root.Proc
        # Idle commands do not affect the next run or start a worker.
        proc.Pause()
        proc.Resume()
        assert proc.Running.value() is False
        proc.Start()
        assert entered.wait(timeout=2.0)
        proc.Pause()
        assert proc.Paused.value() is False
        if action == "cancel":
            proc.Resume()
            proc.Resume()
        advance.set()
        join_worker(proc)
        assert proc.Message.value() == ("Stopped after error!" if action == "error" else "Done")
        assert proc.pausePoint() is False
        proc.Start()
        join_worker(proc)
        assert proc.Result.value() == 2
        assert proc.Message.value() == "Done"


@pytest.mark.parametrize("action", ["resume", "stop", "error"])
def test_snapshot_callback_can_control_process_or_raise(action):
    entered = threading.Event()
    advance = threading.Event()
    publications = []

    def run(*, dev):
        entered.set()
        assert advance.wait(timeout=2.0)

        def publish():
            publications.append(threading.get_ident())
            if action == "resume":
                dev.Resume()
            elif action == "stop":
                dev.Stop()
            else:
                raise RuntimeError("snapshot failed")

        return int(dev.pausePoint(publish=publish))

    with process_root(run) as root:
        proc = root.Proc
        proc.Start()
        assert entered.wait(timeout=2.0)
        proc.Pause()
        advance.set()
        join_worker(proc)
        assert publications == [proc._thread.ident]
        assert proc.Message.value() == {
            "resume": "Done", "stop": "Stopped", "error": "Stopped after error!",
        }[action]
        if action != "error":
            assert proc.Result.value() == (1 if action == "resume" else 0)
        assert proc.pausePoint() is False


def test_pause_requested_during_startup_does_not_launch_another_worker(monkeypatch, wait_until):
    entered = threading.Event()
    advance = threading.Event()

    def run(*, dev, arg):
        return arg if dev.pausePoint() else -1

    with process_root(run) as root:
        proc = root.Proc
        original_run = proc._run

        def delayed_run():
            entered.set()
            assert advance.wait(timeout=2.0)
            original_run()

        monkeypatch.setattr(proc, "_run", delayed_run)
        proc(17)
        worker = proc._thread
        try:
            assert entered.wait(timeout=2.0)
            assert proc.Running.value() is False
            proc.Pause()
            proc.Start()
            proc(99)
            assert proc._thread is worker
            advance.set()
            assert wait_until(lambda: proc.Paused.value())
            proc.Resume()
            join_worker(proc)
            assert proc.Result.value() == 17
        finally:
            advance.set()
            proc.Stop()


def test_pause_flush_preserves_enclosing_update_groups(wait_until):
    entered = threading.Event()
    checkpoint = threading.Event()
    resumed = threading.Event()
    finish = threading.Event()
    updates = []

    def run(*, dev):
        with dev.root.updateGroup():
            entered.set()
            assert checkpoint.wait(timeout=2.0)
            if not dev.pausePoint():
                return -1
            dev.Snapshot.set(42)
        # The enclosing Process updateGroup must still buffer Snapshot.
        resumed.set()
        assert finish.wait(timeout=2.0)
        return 1

    with process_root(run) as root:
        proc = root.Proc
        root.addVarListener(lambda path, value: updates.append((path, value.value)))
        proc.Start()
        try:
            assert entered.wait(timeout=2.0)
            proc.Pause()
            checkpoint.set()
            assert wait_until(lambda: (proc.Paused.path, True) in updates)
            proc.Resume()
            assert resumed.wait(timeout=2.0)
            root.waitOnUpdate()
            assert (proc.Paused.path, False) in updates
            assert (proc.Snapshot.path, 42) not in updates
            finish.set()
            join_worker(proc)
            assert wait_until(lambda: (proc.Snapshot.path, 42) in updates)
        finally:
            checkpoint.set()
            finish.set()
            proc.Stop()
