# ----------------------------------------------------------------------------
# Title      : Probe Perf Events Tests
# ----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
# ----------------------------------------------------------------------------

from __future__ import annotations

import importlib
import subprocess
import sys
from pathlib import Path

import pytest


SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

probe_perf_events = importlib.import_module("probe_perf_events")
env_fingerprint = importlib.import_module("env_fingerprint")


def _completed(argv, returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(argv, returncode=returncode, stdout=stdout, stderr=stderr)


class _ScriptedRunner:
    """An injectable subprocess runner returning canned CompletedProcess
    objects keyed off a predicate over the argv, in registration order. Every
    invocation is recorded in `calls` so tests can assert on the command
    sequence and on how many times a given command ran, with no privileged
    access and no dependence on whether perf actually exists on this machine.
    """

    def __init__(self, default=None):
        self._rules: list[tuple] = []
        self._default = default if default is not None else _completed([], returncode=0)
        self.calls: list[list[str]] = []

    def when(self, predicate, completed):
        self._rules.append((predicate, completed))
        return self

    def __call__(self, argv):
        self.calls.append(argv)
        for predicate, completed in self._rules:
            if predicate(argv):
                return completed
        return self._default


def _contains(token):
    return lambda argv: any(token in part for part in argv)


# ---------------------------------------------------------------------------
# parse_perf_stat_output
# ---------------------------------------------------------------------------

def test_parse_perf_stat_output_not_supported_line_is_null_never_zero():
    text = "       <not supported>      cycles\n"
    entries = probe_perf_events.parse_perf_stat_output(text, ["cycles"])

    assert entries == [{
        "event": "cycles",
        "status": probe_perf_events.STATUS_NOT_SUPPORTED,
        "value": None,
        "raw_line": "       <not supported>      cycles",
    }]


def test_parse_perf_stat_output_permission_denied_line():
    text = "       <not counted>      cycles                    (Permission denied)\n"
    entries = probe_perf_events.parse_perf_stat_output(text, ["cycles"])

    assert entries[0]["status"] == probe_perf_events.STATUS_NOT_PERMITTED
    assert entries[0]["value"] is None
    assert "Permission denied" in entries[0]["raw_line"]


def test_parse_perf_stat_output_grouped_thousands_count():
    text = "         1,234,567      cache-references\n"
    entries = probe_perf_events.parse_perf_stat_output(text, ["cache-references"])

    assert entries[0]["status"] == probe_perf_events.STATUS_COUNTED
    assert entries[0]["value"] == 1234567


def test_parse_perf_stat_output_missing_event_is_unparsed_not_dropped():
    text = "         1,234,567      cache-references\n"
    entries = probe_perf_events.parse_perf_stat_output(text, ["cache-references", "branch-misses"])

    assert len(entries) == 2
    missing = next(entry for entry in entries if entry["event"] == "branch-misses")
    assert missing["status"] == probe_perf_events.STATUS_UNPARSED
    assert missing["value"] is None
    assert missing["raw_line"] is None


def test_parse_perf_stat_output_nonfinite_value_is_not_counted():
    text = "                 nan      cycles\n"
    entries = probe_perf_events.parse_perf_stat_output(text, ["cycles"])

    assert entries[0]["status"] == probe_perf_events.STATUS_UNPARSED
    assert entries[0]["value"] is None


def test_parse_perf_stat_output_does_not_cross_match_similar_event_names():
    text = (
        "         1,234,567      branches\n"
        "               400      branch-misses\n"
    )
    entries = probe_perf_events.parse_perf_stat_output(text, ["branches", "branch-misses"])
    by_event = {entry["event"]: entry for entry in entries}

    assert by_event["branches"]["value"] == 1234567
    assert by_event["branch-misses"]["value"] == 400


# ---------------------------------------------------------------------------
# read_paranoid_setting
# ---------------------------------------------------------------------------

def test_read_paranoid_setting_success():
    runner = _ScriptedRunner().when(
        _contains("perf_event_paranoid"), _completed([], returncode=0, stdout="4\n"),
    )

    value = probe_perf_events.read_paranoid_setting(runner=runner)

    assert value == 4


def test_read_paranoid_setting_failure_returns_unavailable_with_reason():
    errors: list[str] = []
    runner = _ScriptedRunner().when(
        _contains("perf_event_paranoid"),
        _completed([], returncode=1, stdout="", stderr="sysctl: permission denied"),
    )

    value = probe_perf_events.read_paranoid_setting(runner=runner, errors=errors)

    assert value == env_fingerprint.UNAVAILABLE
    assert any("paranoid" in entry.lower() for entry in errors)


def test_read_paranoid_setting_unparsable_output_returns_unavailable():
    errors: list[str] = []
    runner = _ScriptedRunner().when(
        _contains("perf_event_paranoid"), _completed([], returncode=0, stdout="not-a-number\n"),
    )

    value = probe_perf_events.read_paranoid_setting(runner=runner, errors=errors)

    assert value == env_fingerprint.UNAVAILABLE
    assert errors


# ---------------------------------------------------------------------------
# set_paranoid_setting / restore_paranoid_setting
# ---------------------------------------------------------------------------

def test_set_paranoid_setting_records_attempt_and_success():
    runner = _ScriptedRunner().when(_contains("perf_event_paranoid=0"), _completed([], returncode=0))

    result = probe_perf_events.set_paranoid_setting(0, runner=runner)

    assert result["attempted_value"] == 0
    assert result["exit_code"] == 0
    assert result["succeeded"] is True


def test_set_paranoid_setting_records_failure_never_raises():
    runner = _ScriptedRunner().when(
        _contains("perf_event_paranoid=0"),
        _completed([], returncode=1, stderr="sysctl: permission denied"),
    )

    result = probe_perf_events.set_paranoid_setting(0, runner=runner)

    assert result["succeeded"] is False
    assert result["exit_code"] == 1
    assert "permission denied" in result["stderr_excerpt"]


def test_restore_paranoid_setting_writes_back_original_value():
    runner = _ScriptedRunner().when(_contains("perf_event_paranoid=4"), _completed([], returncode=0))

    result = probe_perf_events.restore_paranoid_setting(4, runner=runner)

    assert result["attempted"] is True
    assert result["attempted_value"] == 4
    assert result["succeeded"] is True


def test_restore_paranoid_setting_skips_write_when_original_unavailable():
    runner = _ScriptedRunner()

    result = probe_perf_events.restore_paranoid_setting(env_fingerprint.UNAVAILABLE, runner=runner)

    assert result["attempted"] is False
    assert runner.calls == []


# ---------------------------------------------------------------------------
# install_perf_tooling
# ---------------------------------------------------------------------------

def test_install_perf_tooling_success_records_version_and_packages():
    runner = _ScriptedRunner(default=_completed([], returncode=0)).when(
        _contains("--version"), _completed([], returncode=0, stdout="perf version 6.17.0\n"),
    )

    result = probe_perf_events.install_perf_tooling(runner=runner, kernel_release="6.17.0-1022-azure")

    assert result["installed"] is True
    assert result["perf_version"] == "perf version 6.17.0"
    assert result["attempted_packages"] == [
        "linux-tools-common", "linux-tools-6.17.0-1022-azure", "linux-tools-generic",
    ]
    assert result["exit_code"] == 0


def test_install_perf_tooling_missing_kernel_matched_package_records_finding_never_raises():
    # apt-get install with multiple package arguments is transactional: a
    # missing kernel-matched package fails the whole combined install call,
    # which is exactly the finding this test records for that run rather than a crash.
    runner = _ScriptedRunner(default=_completed([], returncode=0)).when(
        _contains("install"),
        _completed(
            [], returncode=100,
            stderr="E: Unable to locate package linux-tools-6.17.0-1022-azure",
        ),
    ).when(_contains("--version"), _completed([], returncode=1, stdout="", stderr="not found"))

    result = probe_perf_events.install_perf_tooling(runner=runner, kernel_release="6.17.0-1022-azure")

    assert result["installed"] is False
    assert result["exit_code"] == 100
    assert result["perf_version"] == env_fingerprint.UNAVAILABLE
    assert "Unable to locate package" in result["stderr_excerpt"]


def test_install_perf_tooling_installed_reflects_working_binary_not_apt_exit_code():
    # apt reports success, but perf --version still fails to produce output:
    # `installed` must track the real binary check, not the apt exit code.
    runner = _ScriptedRunner(default=_completed([], returncode=0)).when(
        _contains("--version"), _completed([], returncode=1, stdout="", stderr="perf: not found"),
    )

    result = probe_perf_events.install_perf_tooling(runner=runner)

    assert result["exit_code"] == 0
    assert result["installed"] is False
    assert result["perf_version"] == env_fingerprint.UNAVAILABLE


def test_install_perf_tooling_apt_failure_but_perf_already_present():
    # The combined install call fails (e.g. already installed via a base
    # image, or a benign apt error), but perf --version still responds:
    # `installed` reflects that real capability, not the apt exit code.
    runner = _ScriptedRunner(default=_completed([], returncode=0)).when(
        _contains("install"), _completed([], returncode=100, stderr="Unable to locate package"),
    ).when(_contains("--version"), _completed([], returncode=0, stdout="perf version 6.8.0\n"))

    result = probe_perf_events.install_perf_tooling(runner=runner)

    assert result["exit_code"] == 100
    assert result["installed"] is True
    assert result["perf_version"] == "perf version 6.8.0"


# ---------------------------------------------------------------------------
# collect_perf_capability
# ---------------------------------------------------------------------------

def _fake_perf_stat_output(statuses):
    """Build a canned perf stat stderr block for the given
    {event: (status, value)} mapping, using the same textual markers
    parse_perf_stat_output understands."""
    lines = []
    for event, (status, value) in statuses.items():
        if status == probe_perf_events.STATUS_NOT_SUPPORTED:
            lines.append(f"       <not supported>      {event}")
        elif status == probe_perf_events.STATUS_NOT_PERMITTED:
            lines.append(f"       <not counted>      {event}                    (Permission denied)")
        elif status == probe_perf_events.STATUS_COUNTED:
            lines.append(f"         {value:,}      {event}")
    return "\n".join(lines) + "\n"


def _all_events():
    return list(probe_perf_events.PERF_HARDWARE_EVENTS) + list(probe_perf_events.PERF_SOFTWARE_EVENTS)


def _default_all_not_supported():
    return {event: (probe_perf_events.STATUS_NOT_SUPPORTED, None) for event in _all_events()}


def test_perf_hardware_and_software_event_tuples_are_disjoint():
    hardware = set(probe_perf_events.PERF_HARDWARE_EVENTS)
    software = set(probe_perf_events.PERF_SOFTWARE_EVENTS)

    assert hardware & software == set()


def test_collect_perf_capability_event_counted_in_default_state_is_gating_eligible():
    default_statuses = _default_all_not_supported()
    default_statuses["task-clock"] = (probe_perf_events.STATUS_COUNTED, 100)
    lowered_statuses = dict(default_statuses)

    outputs = iter([
        _fake_perf_stat_output(default_statuses),
        _fake_perf_stat_output(lowered_statuses),
    ])

    def runner(argv):
        if "stat" in argv:
            return _completed(argv, returncode=0, stderr=next(outputs))
        if "--version" in argv:
            return _completed(argv, returncode=0, stdout="perf version 6.17.0\n")
        if "perf_event_paranoid" in " ".join(argv) and "-w" not in argv:
            return _completed(argv, returncode=0, stdout="4\n")
        return _completed(argv, returncode=0)

    record = probe_perf_events.collect_perf_capability(runner=runner)

    task_clock_default = next(
        e for e in record["events"]
        if e["event"] == "task-clock" and e["paranoid_state"] == probe_perf_events.PARANOID_STATE_DEFAULT
    )
    assert task_clock_default["gating_eligible"] is True
    assert task_clock_default["reason"] is None
    assert record["paranoid_restored"] == record["paranoid_default"]


def test_collect_perf_capability_event_counted_only_when_lowered_is_ineligible_with_reason():
    default_statuses = _default_all_not_supported()
    lowered_statuses = dict(default_statuses)
    lowered_statuses["cycles"] = (probe_perf_events.STATUS_COUNTED, 555)

    outputs = iter([
        _fake_perf_stat_output(default_statuses),
        _fake_perf_stat_output(lowered_statuses),
    ])

    def runner(argv):
        if "stat" in argv:
            return _completed(argv, returncode=0, stderr=next(outputs))
        if "--version" in argv:
            return _completed(argv, returncode=0, stdout="perf version 6.17.0\n")
        if "perf_event_paranoid" in " ".join(argv) and "-w" not in argv:
            return _completed(argv, returncode=0, stdout="4\n")
        return _completed(argv, returncode=0)

    record = probe_perf_events.collect_perf_capability(runner=runner)

    cycles_entries = [e for e in record["events"] if e["event"] == "cycles"]
    assert all(e["gating_eligible"] is False for e in cycles_entries)
    assert all("lower" in e["reason"] for e in cycles_entries)


def test_collect_perf_capability_event_uncounted_in_either_state_is_ineligible_with_reason():
    default_statuses = _default_all_not_supported()
    lowered_statuses = dict(default_statuses)

    outputs = iter([
        _fake_perf_stat_output(default_statuses),
        _fake_perf_stat_output(lowered_statuses),
    ])

    def runner(argv):
        if "stat" in argv:
            return _completed(argv, returncode=0, stderr=next(outputs))
        if "--version" in argv:
            return _completed(argv, returncode=0, stdout="perf version 6.17.0\n")
        if "perf_event_paranoid" in " ".join(argv) and "-w" not in argv:
            return _completed(argv, returncode=0, stdout="4\n")
        return _completed(argv, returncode=0)

    record = probe_perf_events.collect_perf_capability(runner=runner)

    cycles_entries = [e for e in record["events"] if e["event"] == "cycles"]
    assert all(e["gating_eligible"] is False for e in cycles_entries)
    assert all("not counted" in e["reason"] for e in cycles_entries)


def test_collect_perf_capability_tooling_unavailable_still_emits_full_row_set():
    def runner(argv):
        if "--version" in argv:
            return _completed(argv, returncode=1, stderr="perf: command not found")
        if "install" in argv:
            return _completed(argv, returncode=100, stderr="Unable to locate package")
        if "perf_event_paranoid" in " ".join(argv) and "-w" not in argv:
            return _completed(argv, returncode=0, stdout="4\n")
        return _completed(argv, returncode=0)

    record = probe_perf_events.collect_perf_capability(runner=runner)

    assert record["perf_installed"] is False
    all_events = _all_events()
    for event in all_events:
        matching = [e for e in record["events"] if e["event"] == event]
        assert len(matching) == 2
        assert all(e["status"] == probe_perf_events.STATUS_UNAVAILABLE for e in matching)
        assert all(e["gating_eligible"] is False for e in matching)
        assert all(e["reason"] for e in matching)


def test_collect_perf_capability_restores_paranoid_setting_even_when_sweep_raises():
    calls: list[list[str]] = []

    def runner(argv):
        calls.append(argv)
        if "stat" in argv:
            if len(calls) > 0 and any("stat" in c for c in calls[:-1]):
                raise RuntimeError("perf stat crashed mid-sweep")
            return _completed(argv, returncode=0, stderr=_fake_perf_stat_output(_default_all_not_supported()))
        if "--version" in argv:
            return _completed(argv, returncode=0, stdout="perf version 6.17.0\n")
        if "perf_event_paranoid" in " ".join(argv) and "-w" not in argv:
            return _completed(argv, returncode=0, stdout="4\n")
        return _completed(argv, returncode=0)

    with pytest.raises(RuntimeError):
        probe_perf_events.collect_perf_capability(runner=runner)

    restore_calls = [c for c in calls if "perf_event_paranoid=4" in " ".join(c)]
    assert restore_calls, "expected a restore write attempting the original paranoid value"

    # And the value is read back afterward (a read call after the restore write).
    restore_index = calls.index(restore_calls[0])
    read_after_restore = [
        c for c in calls[restore_index + 1:]
        if "perf_event_paranoid" in " ".join(c) and "-w" not in c
    ]
    assert read_after_restore, "expected a read-back of the paranoid value after restoration"
