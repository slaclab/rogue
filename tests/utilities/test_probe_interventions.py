# ----------------------------------------------------------------------------
# Title      : Probe Interventions Tests
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
import os
import subprocess
import sys
from pathlib import Path

import pytest


SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

probe_interventions = importlib.import_module("probe_interventions")


def _direct_sampler(label, fn):
    """A window_sampler stand-in that just runs fn() and reports no steal
    flag, so measure_aba's tests never touch real /proc/stat or cgroup
    files.
    """
    return {"label": label, "result": fn(), "steal_flagged": False}


# ---------------------------------------------------------------------------
# measure_aba
# ---------------------------------------------------------------------------

def test_measure_aba_calls_workload_three_times_with_correct_ordering():
    events: list[str] = []

    def workload():
        events.append("workload")
        return 10.0

    def intervene():
        events.append("intervene")

    def revert():
        events.append("revert")

    probe_interventions.measure_aba(workload, intervene, revert, window_sampler=_direct_sampler)

    assert events == ["workload", "intervene", "workload", "revert", "workload"]


def test_measure_aba_identical_baselines_zero_drift_not_contaminated():
    values = iter([10.0, 12.0, 10.0])

    def workload():
        return next(values)

    result = probe_interventions.measure_aba(
        workload, lambda: None, lambda: None, window_sampler=_direct_sampler,
    )

    assert result["drift_ratio"] == 0.0
    assert result["contaminated"] is False
    assert result["effect_ratio"] == pytest.approx(1.2)
    assert result["drift_comparison"] == probe_interventions.DRIFT_COMPARISON_OPERATOR


def test_measure_aba_drift_exactly_at_threshold_is_contaminated():
    # baseline_1=100, baseline_2=110 -> drift_ratio == 0.10 == ABA_DRIFT_THRESHOLD
    values = iter([100.0, 105.0, 110.0])

    def workload():
        return next(values)

    result = probe_interventions.measure_aba(
        workload, lambda: None, lambda: None, window_sampler=_direct_sampler,
    )

    assert result["drift_ratio"] == pytest.approx(probe_interventions.ABA_DRIFT_THRESHOLD)
    assert result["contaminated"] is True
    assert result["drift_comparison"] == ">="
    assert result["effect_ratio"] == probe_interventions.CONTAMINATED


def test_measure_aba_zero_first_baseline_yields_unavailable_drift_not_a_crash():
    values = iter([0.0, 5.0, 0.0])

    def workload():
        return next(values)

    result = probe_interventions.measure_aba(
        workload, lambda: None, lambda: None, window_sampler=_direct_sampler,
    )

    assert result["drift_ratio"] == probe_interventions.env_fingerprint.UNAVAILABLE
    assert result["contaminated"] is True
    assert result["effect_ratio"] == probe_interventions.CONTAMINATED


def test_measure_aba_windows_are_included_and_notes_flag_steal():
    def flagged_sampler(label, fn):
        return {"label": label, "result": fn(), "steal_flagged": label == "treatment"}

    values = iter([1.0, 1.0, 1.0])

    def workload():
        return next(values)

    result = probe_interventions.measure_aba(
        workload, lambda: None, lambda: None, window_sampler=flagged_sampler,
    )

    assert len(result["windows"]) == 3
    assert any("treatment" in note for note in result["notes"])


# ---------------------------------------------------------------------------
# taskset_intervention
# ---------------------------------------------------------------------------

def test_taskset_intervention_not_applicable_when_binary_missing():
    result = probe_interventions.taskset_intervention(
        lambda: 1.0, which_fn=lambda name: None, window_sampler=_direct_sampler,
    )

    assert result["status"] == probe_interventions.NOT_APPLICABLE
    assert "reason" in result
    assert result["effect_ratio"] == probe_interventions.NOT_APPLICABLE


def test_taskset_intervention_pins_during_treatment_and_restores_after():
    original = os.sched_getaffinity(0)
    if len(original) < 2:
        pytest.skip("need at least 2 available CPUs to exercise a real affinity change")
    target_cpu = sorted(original)[0]
    observed_during_treatment: dict[str, set[int]] = {}

    def workload():
        return 1.0

    def fake_sampler(label, fn):
        result = fn()
        if label == "treatment":
            observed_during_treatment["value"] = os.sched_getaffinity(0)
        return {"label": label, "result": result, "steal_flagged": False}

    result = probe_interventions.taskset_intervention(
        workload,
        cpu_set=(target_cpu,),
        which_fn=lambda name: "/usr/bin/taskset",
        window_sampler=fake_sampler,
    )

    assert observed_during_treatment["value"] == {target_cpu}
    assert os.sched_getaffinity(0) == original
    assert result["status"] == "measured"
    assert result["cpu_set"] == [target_cpu]


# ---------------------------------------------------------------------------
# service_stop_intervention
# ---------------------------------------------------------------------------

def test_service_stop_intervention_empty_units_not_applicable():
    result = probe_interventions.service_stop_intervention(
        [], lambda: 1.0, window_sampler=_direct_sampler,
    )

    assert result["status"] == probe_interventions.NOT_APPLICABLE
    assert "reason" in result
    assert result["effect_ratio"] == probe_interventions.NOT_APPLICABLE


def test_service_stop_intervention_records_stop_and_restart_exit_codes():
    def fake_run_cmd(argv):
        return subprocess.CompletedProcess(argv, returncode=0, stdout="", stderr="")

    values = iter([10.0, 10.0, 10.0])

    result = probe_interventions.service_stop_intervention(
        ["a.service"], lambda: next(values),
        run_cmd=fake_run_cmd, window_sampler=_direct_sampler,
    )

    assert result["status"] == "measured"
    assert result["stop_records"] == [{"unit": "a.service", "returncode": 0, "stderr": ""}]
    assert result["restart_records"] == [{"unit": "a.service", "returncode": 0, "stderr": ""}]


def test_service_stop_intervention_restarts_every_stopped_unit_when_treatment_raises():
    commands: list[list[str]] = []

    def fake_run_cmd(argv):
        commands.append(argv)
        return subprocess.CompletedProcess(argv, returncode=0, stdout="", stderr="")

    call_count = {"n": 0}

    def workload():
        call_count["n"] += 1
        if call_count["n"] == 2:
            raise RuntimeError("treatment failed")
        return 1.0

    with pytest.raises(RuntimeError):
        probe_interventions.service_stop_intervention(
            ["a.service", "b.timer"], workload,
            run_cmd=fake_run_cmd, window_sampler=_direct_sampler,
        )

    stopped = [cmd[-1] for cmd in commands if cmd[2] == "stop"]
    started = [cmd[-1] for cmd in commands if cmd[2] == "start"]
    assert stopped == ["a.service", "b.timer"]
    assert started == ["a.service", "b.timer"]


def test_service_stop_intervention_skips_a_unit_that_fails_to_stop():
    def fake_run_cmd(argv):
        if argv[2] == "stop" and argv[-1] == "flaky.service":
            return subprocess.CompletedProcess(argv, returncode=1, stdout="", stderr="no such unit")
        return subprocess.CompletedProcess(argv, returncode=0, stdout="", stderr="")

    values = iter([1.0, 1.0, 1.0])

    result = probe_interventions.service_stop_intervention(
        ["flaky.service", "good.service"], lambda: next(values),
        run_cmd=fake_run_cmd, window_sampler=_direct_sampler,
    )

    restarted_units = [record["unit"] for record in result["restart_records"]]
    assert "flaky.service" not in restarted_units
    assert "good.service" in restarted_units


# ---------------------------------------------------------------------------
# collect_interventions
# ---------------------------------------------------------------------------

def test_collect_interventions_name_sorted_order():
    entries = probe_interventions.collect_interventions(
        lambda: 1.0, [], which_fn=lambda name: None, window_sampler=_direct_sampler,
    )

    names = [entry["intervention"] for entry in entries]
    assert names == ["service_stop", "taskset"]
