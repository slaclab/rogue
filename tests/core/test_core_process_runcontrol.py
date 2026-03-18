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

import pyrogue as pr
import pyrogue._Process as process_module


class ArgumentProcess(pr.Process):
    def __init__(self, **kwargs):
        super().__init__(
            argVariable=pr.LocalVariable(name="Arg", value=0),
            returnVariable=pr.LocalVariable(name="Result", value=""),
            function=self._run_with_arg,
            **kwargs,
        )

    def _run_with_arg(self, *, arg):
        return f"arg={arg}"


class ProcessDevice(pr.Process):
    def __init__(self, **kwargs):
        self.events = []
        self.raise_error = False
        super().__init__(
            returnVariable=pr.LocalVariable(name="Result", value=""),
            function=self._run_process,
            **kwargs,
        )

    def _run_process(self, *, dev):
        # Keep the body deterministic and short so the test can assert state
        # transitions without racing a long-lived worker thread.
        self.Message.set("Running")
        self.TotalSteps.set(4)
        for step in range(1, 5):
            if not self._runEn:
                self.Message.set("Stopped")
                return "stopped"
            self.events.append(step)
            self._setSteps(step)
        if self.raise_error:
            raise RuntimeError("process failed")
        self.Message.set("Completed")
        return "done"


class TrackingRunControl(pr.RunControl):
    def __init__(self, **kwargs):
        self.rate_updates = []
        self.command_calls = 0
        super().__init__(
            rates={20: "20 Hz", 50: "50 Hz"},
            cmd=self._tick,
            **kwargs,
        )

    def _tick(self):
        self.command_calls += 1

    def _setRunRate(self, value):
        self.rate_updates.append(value)


class ProcessRoot(pr.Root):
    def __init__(self):
        super().__init__(name="root", pollEn=False)
        self.add(ProcessDevice(name="Proc"))
        self.add(ArgumentProcess(name="ArgProc"))
        self.add(pr.Process(name="DefaultProc"))
        self.add(TrackingRunControl(name="Run"))


class DummyRoot:
    def _queueUpdates(self, _var):
        pass


def attach_dummy_root(proc):
    dummy = DummyRoot()
    proc._root = dummy

    # The default process path only needs a root object that accepts queued
    # updates, so attach the same shim directly to the built variables.
    for variable in (proc.Running, proc.Progress, proc.Message, proc.Step, proc.TotalSteps):
        variable._root = dummy

    return proc


def test_process_start_stop_and_return_value(wait_until):
    with ProcessRoot() as root:
        root.Proc.Start()
        assert wait_until(lambda: root.Proc.Running.value() is False)
        assert root.Proc.Result.value() == "done"
        assert root.Proc.Progress.value() == 1.0
        assert root.Proc.Message.value() == "Done"
        assert root.Proc.events == [1, 2, 3, 4]

        # Reset the small amount of process state we intentionally inspect so
        # the stop path can be exercised in the same test without rebuilding
        # the whole tree.
        root.Proc._runEn = True
        root.Proc._thread = None
        root.Proc.Message.set("")
        root.Proc.Progress.set(0.0)
        root.Proc.Step.set(1)
        root.Proc.events.clear()

        root.Proc._startProcess()
        root.Proc.Stop()
        assert wait_until(lambda: root.Proc.Running.value() is False)
        assert root.Proc.Result.value() in {"done", "stopped"}


def test_process_error_path_sets_message(wait_until):
    with ProcessRoot() as root:
        root.Proc.raise_error = True
        root.Proc.Start()
        assert wait_until(lambda: root.Proc.Running.value() is False)
        assert root.Proc.Message.value() == "Stopped after error!"


def test_process_call_sets_argument_and_progress_helpers():
    with ProcessRoot() as root:
        root.ArgProc(17)
        assert root.ArgProc._thread is not None
        root.ArgProc._thread.join(timeout=1.0)
        assert root.ArgProc.Result.value() == "arg=17"
        assert root.ArgProc.Arg.value() == 17

        root.ArgProc.TotalSteps.set(8)
        root.ArgProc.Step.set(1)
        root.ArgProc._incrementSteps(3)
        assert root.ArgProc.Step.value() == 4
        assert root.ArgProc.Progress.value() == 0.5

        root.ArgProc._setSteps(6)
        assert root.ArgProc.Step.value() == 6
        assert root.ArgProc.Progress.value() == 0.75

        root.ArgProc._setSteps(12)
        assert root.ArgProc.Step.value() == 12
        assert root.ArgProc.Progress.value() == 1.0

        root.ArgProc.TotalSteps.set(0)
        root.ArgProc._setSteps(3)
        assert root.ArgProc.Progress.value() == 0.0


def test_process_start_and_call_warn_when_already_running(monkeypatch):
    with ProcessRoot() as root:
        warnings = []
        blocker = threading.Event()

        def hold_process(*, dev):
            blocker.wait(timeout=1.0)
            return "held"

        root.Proc._function = hold_process
        root.Proc._functionWrap = pr.functionWrapper(function=hold_process, callArgs=["root", "dev", "arg"])
        monkeypatch.setattr(root.Proc._log, "warning", lambda msg: warnings.append(msg))

        root.Proc.Start()
        assert root.Proc.Running.value() is True or root.Proc._thread is not None

        root.Proc.Start()
        root.Proc()

        blocker.set()
        root.Proc._thread.join(timeout=1.0)

        assert warnings == ["Process already running!", "Process already running!"]


def test_process_without_callback_runs_default_loop(monkeypatch):
    sleep_calls = []
    monkeypatch.setattr(process_module.time, "sleep", lambda delay: sleep_calls.append(delay))

    proc = attach_dummy_root(pr.Process(name="Proc"))
    proc._runEn = True
    proc._process()

    assert proc.Message.value() == "Done"
    assert proc.TotalSteps.value() == 100
    assert proc.Step.value() == 100
    assert proc.Progress.value() == 1.0
    assert len(sleep_calls) == 100


def test_process_stop_stops_default_loop(monkeypatch):
    call_count = {"count": 0}
    proc = attach_dummy_root(pr.Process(name="Proc"))

    def stop_after_first(_delay):
        call_count["count"] += 1
        proc._runEn = False

    monkeypatch.setattr(process_module.time, "sleep", stop_after_first)

    proc._runEn = True
    proc._process()

    assert proc.Message.value() == "Done"
    assert proc.Step.value() == 1
    assert proc.Progress.value() == 0.01
    assert call_count["count"] == 1


def test_process_stop_calls_stop_process(monkeypatch):
    with ProcessRoot() as root:
        calls = []

        monkeypatch.setattr(root.DefaultProc, "_stopProcess", lambda: calls.append("stop"))

        root.DefaultProc._stop()
        assert calls == ["stop"]


def test_run_control_transitions_and_counts(wait_until):
    with ProcessRoot() as root:
        root.Run.runRate.setDisp("50 Hz")
        assert root.Run.rate_updates[-1] == 50

        root.Run.runState.setDisp("Running")
        assert wait_until(lambda: root.Run.command_calls >= 3)
        root.Run.runState.setDisp("Stopped")
        assert wait_until(lambda: root.Run._thread is None)
        assert root.Run.command_calls >= 3
        assert root.Run.runCount.value() >= 2
