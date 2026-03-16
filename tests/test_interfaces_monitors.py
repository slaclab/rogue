import json

import pyrogue.interfaces as pr_intf


class FakeVarValue:
    def __init__(self, value=None, value_disp=None):
        self.value = value
        self.valueDisp = value_disp


def test_system_log_monitor_processes_only_new_entries(capsys, monkeypatch):
    monitor = pr_intf.SystemLogMonitor(details=True)
    monkeypatch.setattr(pr_intf.time, "strftime", lambda *_args, **_kwargs: "STAMP")
    monkeypatch.setattr(pr_intf.time, "localtime", lambda value: value)

    entries = json.dumps([
        {
            "created": 1.0,
            "name": "pyrogue.test",
            "message": "line1\nline2",
            "exception": "RuntimeError",
            "levelName": "INFO",
            "levelNumber": 20,
            "rogueCpp": True,
            "rogueComponent": "memory",
            "rogueLogger": "pyrogue.memory.Emulate",
            "rogueTid": 11,
            "roguePid": 22,
            "traceBack": ["tb line 1", "tb line 2"],
        },
        {
            "created": 2.0,
            "name": "pyrogue.test",
            "message": "second",
            "exception": None,
            "levelName": "WARNING",
            "levelNumber": 30,
        },
    ])

    # The monitor tracks how many log entries it has already printed, so a
    # second call with the same payload should produce no duplicate output.
    monitor.processLogString(entries)
    first = capsys.readouterr().out
    monitor.processLogString(entries)
    second = capsys.readouterr().out

    assert "STAMP [C++ memory]: line1" in first
    assert "line2" in first
    assert "Rogue Logger: pyrogue.memory.Emulate" in first
    assert "Exception: RuntimeError" in first
    assert "STAMP: second" in first
    assert second == ""


def test_system_log_monitor_var_updated_filters_non_systemlog(monkeypatch):
    seen = []
    monitor = pr_intf.SystemLogMonitor(details=False)
    monkeypatch.setattr(monitor, "processLogString", lambda payload: seen.append(payload))

    monitor.varUpdated("root.SystemLogLast", FakeVarValue(value="payload"))
    monitor.varUpdated("root.Dev.Value", FakeVarValue(value="ignored"))

    assert seen == ["payload"]


def test_variable_monitor_display_and_filter(capsys, monkeypatch):
    monitor = pr_intf.VariableMonitor("root.Dev.Value")
    monkeypatch.setattr(pr_intf.time, "strftime", lambda *_args, **_kwargs: "STAMP")
    monkeypatch.setattr(pr_intf.time, "localtime", lambda value: value)
    monkeypatch.setattr(pr_intf.time, "time", lambda: 123.0)

    monitor.display("42")
    first = capsys.readouterr().out
    assert first == "STAMP: root.Dev.Value = 42\n"

    monitor.varUpdated("root.Dev.Other", FakeVarValue(value_disp="ignore"))
    assert capsys.readouterr().out == ""

    monitor.varUpdated("root.Dev.Value", FakeVarValue(value_disp="99"))
    assert capsys.readouterr().out == "STAMP: root.Dev.Value = 99\n"
