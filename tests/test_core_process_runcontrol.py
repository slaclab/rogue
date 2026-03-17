import pyrogue as pr


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
        self.add(TrackingRunControl(name="Run"))


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
