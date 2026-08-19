#!/usr/bin/env python3
# ----------------------------------------------------------------------------
# Title      : Runner Capability Probe Entry Point Tests
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
import json
import subprocess
import sys
from pathlib import Path

import pytest


SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

probe_runner = importlib.import_module("probe_runner")
env_fingerprint = importlib.import_module("env_fingerprint")
probe_instruments = importlib.import_module("probe_instruments")
probe_interventions = importlib.import_module("probe_interventions")
probe_perf_events = importlib.import_module("probe_perf_events")


def _completed(argv, returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(argv, returncode=returncode, stdout=stdout, stderr=stderr)


class _ScriptedRunner:
    """An injectable subprocess runner returning canned CompletedProcess
    objects keyed off a predicate over the argv, in registration order.
    Accepts (and ignores) a `timeout` keyword so it is a drop-in replacement
    for probe_runner._run_subprocess in both the build and confirmation
    collectors.
    """

    def __init__(self, default=None):
        self._rules: list[tuple] = []
        self._default = default if default is not None else _completed([], returncode=0)
        self.calls: list[list[str]] = []

    def when(self, predicate, completed):
        self._rules.append((predicate, completed))
        return self

    def __call__(self, argv, timeout=None):
        self.calls.append(argv)
        for predicate, completed in self._rules:
            if predicate(argv):
                return completed
        return self._default


def _contains(token):
    return lambda argv: any(token in part for part in argv)


def _fake_window_sampler(label: str, fn):
    return {"label": label, "wall_seconds": 0.01, "result": fn()}


def _instrument_entry(name, verdict, install=None):
    return {"name": name, "verdict": verdict, "install": install or {}}


ALL_TOP_LEVEL_KEYS = {
    "probe_schema_version", "run", "fingerprint", "calibration", "windows",
    "perf_events", "instruments", "interventions", "confirmation", "build", "errors",
}


class _FakeArgs:
    def __init__(self, repeats: int = 1) -> None:
        self.repeats = repeats


# --- stage ordering --------------------------------------------------------


def test_build_stage_runs_before_confirmation_stage():
    # The confirmation leg needs the library the build stage produces to be
    # importable, so build must be selected (and therefore executed) before
    # confirmation in STAGES' own iteration order.
    names = list(probe_runner.STAGES)
    assert names.index("build") < names.index("confirmation")


def test_fingerprint_stage_runs_before_interventions_stage():
    names = list(probe_runner.STAGES)
    assert names.index("fingerprint") < names.index("interventions")


# --- run_stage ----------------------------------------------------------


def test_run_stage_returns_collector_result_on_success():
    result = probe_runner.run_stage("alpha", lambda: {"value": 42})
    assert result == {"value": 42}


def test_run_stage_contains_exception_into_failure_mapping():
    def _raising():
        raise RuntimeError("boom")

    result = probe_runner.run_stage("alpha", _raising)
    assert result["status"] == "failed"
    assert result["exception_class"] == "RuntimeError"
    assert "boom" in result["message"]


def test_run_stage_bounds_the_exception_message():
    def _raising():
        raise RuntimeError("x" * 10000)

    result = probe_runner.run_stage("alpha", _raising)
    assert len(result["message"]) <= probe_runner.STAGE_ERROR_MESSAGE_MAX_CHARS


# --- collect_stage_results: containment and error recording -------------


def _custom_stages(raising: bool = True) -> dict:
    def _alpha_factory(ctx):
        return lambda: {"alpha": "ok"}

    def _beta_factory(ctx):
        def _fn():
            raise ValueError("beta failed")
        return _fn

    def _beta_ok_factory(ctx):
        return lambda: {"beta": "ok"}

    def _gamma_factory(ctx):
        return lambda: {"gamma": "ok"}

    return {
        "alpha": ("alpha_key", _alpha_factory),
        "beta": ("beta_key", _beta_factory if raising else _beta_ok_factory),
        "gamma": ("gamma_key", _gamma_factory),
    }


def test_collect_stage_results_raising_stage_does_not_prevent_later_stages():
    stages = _custom_stages(raising=True)
    results, errors, _windows = probe_runner.collect_stage_results(
        ["alpha", "beta", "gamma"], _FakeArgs(), stages=stages,
    )
    assert results["alpha_key"] == {"alpha": "ok"}
    assert results["beta_key"]["status"] == "failed"
    assert results["beta_key"]["exception_class"] == "ValueError"
    assert results["gamma_key"] == {"gamma": "ok"}


def test_collect_stage_results_records_one_error_entry_per_raising_stage():
    stages = _custom_stages(raising=True)
    _results, errors, _windows = probe_runner.collect_stage_results(
        ["alpha", "beta", "gamma"], _FakeArgs(), stages=stages,
    )
    assert len(errors) == 1
    assert errors[0]["stage"] == "beta"
    assert errors[0]["exception_class"] == "ValueError"


def test_collect_stage_results_no_error_entry_when_nothing_raises():
    stages = _custom_stages(raising=False)
    _results, errors, _windows = probe_runner.collect_stage_results(
        ["alpha", "beta", "gamma"], _FakeArgs(), stages=stages,
    )
    assert errors == []


def test_collect_stage_results_domain_failure_mapping_is_not_logged_as_error():
    # A collector's own recorded domain failure (e.g. a build that exited
    # non-zero) carries status=="failed" but no exception_class, and must
    # never be mistaken for a caught exception.
    def _domain_failure_factory(ctx):
        return lambda: {"status": "failed", "reason": "non-zero exit"}

    stages = {"alpha": ("alpha_key", _domain_failure_factory)}
    results, errors, _windows = probe_runner.collect_stage_results(
        ["alpha"], _FakeArgs(), stages=stages,
    )
    assert results["alpha_key"] == {"status": "failed", "reason": "non-zero exit"}
    assert errors == []


def test_collect_stage_results_only_runs_selected_stages():
    stages = _custom_stages(raising=False)
    results, _errors, _windows = probe_runner.collect_stage_results(
        ["alpha", "gamma"], _FakeArgs(), stages=stages,
    )
    assert set(results) == {"alpha_key", "gamma_key"}


# --- build_probe_record: unselected stages are empty mappings -----------


def test_build_probe_record_has_all_top_level_keys_even_with_no_stage_results():
    record = probe_runner.build_probe_record(
        job_index="1", github_run_id="1", github_run_attempt="1", github_sha="deadbeef",
        git_tree_hash="treehash", git_tree_hash_source="explicit",
        campaign_branch="perf-probe/campaign", runner_os="Linux",
    )
    assert set(record) == ALL_TOP_LEVEL_KEYS
    for key in ("calibration", "perf_events", "instruments", "interventions", "confirmation", "build"):
        assert record[key] == {}
    assert record["fingerprint"] == {}
    assert record["windows"] == []
    assert record["errors"] == []


def test_build_probe_record_fills_only_the_stages_that_ran():
    record = probe_runner.build_probe_record(
        job_index="1", github_run_id="1", github_run_attempt="1", github_sha="deadbeef",
        git_tree_hash="treehash", git_tree_hash_source="explicit",
        campaign_branch="perf-probe/campaign", runner_os="Linux",
        stage_results={"fingerprint": {"cpu_model": "x"}, "calibration": {"components": {}}},
    )
    assert record["fingerprint"] == {"cpu_model": "x"}
    assert record["calibration"] == {"components": {}}
    assert record["perf_events"] == {}
    assert record["instruments"] == {}


# --- windows: deterministic concatenation --------------------------------


def test_make_window_collector_appends_every_sampled_window():
    windows: list[dict] = []
    sampler = probe_runner._make_window_collector(windows)
    sampler("first", lambda: None)
    sampler("second", lambda: None)
    assert [w["label"] for w in windows] == ["first", "second"]


def test_make_window_collector_strips_a_non_json_serializable_result():
    # A stage's workload_fn may return a raw subprocess.CompletedProcess
    # (the instrument and confirmation stages both do); the shared window
    # list must stay JSON-serializable even though the stage's own return
    # value (from the sampler call itself) still carries the raw result.
    windows: list[dict] = []
    sampler = probe_runner._make_window_collector(windows)
    returned = sampler("subprocess_leg", lambda: _completed(["true"], returncode=0))
    assert returned["result"].returncode == 0
    assert "result" not in windows[0]
    json.dumps(windows)  # must not raise


def test_windows_from_real_stage_wiring_concatenate_across_stages(monkeypatch):
    def _fake_instrument_sweep(*, repeats, window_sampler):
        window_sampler("instrument_a", lambda: None)
        return []

    def _fake_collect_interventions(workload_fn, observed_units, **kwargs):
        kwargs["window_sampler"]("intervention_a", lambda: None)
        return []

    monkeypatch.setattr(probe_instruments, "collect_instrument_sweep", _fake_instrument_sweep)
    monkeypatch.setattr(probe_interventions, "collect_interventions", _fake_collect_interventions)

    stages = {
        "fingerprint": ("fingerprint", probe_runner._fingerprint_stage_fn),
        "instruments": ("instruments", probe_runner._instruments_stage_fn),
        "interventions": ("interventions", probe_runner._interventions_stage_fn),
    }
    monkeypatch.setattr(env_fingerprint, "collect_fingerprint", lambda: {"systemd_timers": []})

    _results, _errors, windows = probe_runner.collect_stage_results(
        ["fingerprint", "instruments", "interventions"], _FakeArgs(), stages=stages,
    )
    assert {w["label"] for w in windows} == {"instrument_a", "intervention_a"}
    ordered = env_fingerprint.order_windows(windows)
    assert len(ordered) == 2


# --- observed units from the fingerprint's timer listing -----------------


def test_observed_units_from_fingerprint_parses_timer_names():
    fingerprint = {
        "systemd_timers": [
            "Mon 2024-01-01 00:00:00 UTC 6h left  n/a  n/a  apt-daily.timer  apt-daily.service",
            "n/a                          n/a     n/a  n/a  fstrim.timer     fstrim.service",
        ],
    }
    units = probe_runner._observed_units_from_fingerprint(fingerprint)
    assert units == ["apt-daily.timer", "fstrim.timer"]


def test_observed_units_from_fingerprint_empty_when_unavailable():
    assert probe_runner._observed_units_from_fingerprint({"systemd_timers": env_fingerprint.UNAVAILABLE}) == []
    assert probe_runner._observed_units_from_fingerprint({}) == []


def test_interventions_stage_fn_receives_observed_units_from_the_same_run_fingerprint(monkeypatch):
    captured = {}

    def _fake_collect_interventions(workload_fn, observed_units, **kwargs):
        captured["observed_units"] = observed_units
        return []

    monkeypatch.setattr(probe_interventions, "collect_interventions", _fake_collect_interventions)

    ctx = {
        "record": {"fingerprint": {"systemd_timers": ["x x x x foo.timer foo.service"]}},
        "args": _FakeArgs(),
        "windows": [],
    }
    fn = probe_runner._interventions_stage_fn(ctx)
    fn()
    assert captured["observed_units"] == ["foo.timer"]


# --- CLI: unknown stage name and stage-subset key completeness -----------


def test_main_unknown_stage_name_exits_nonzero_and_lists_valid_names(tmp_path, capsys):
    out_path = tmp_path / "probe.json"
    rc = probe_runner.main(["--out", str(out_path), "--stages", "not_a_real_stage"])
    assert rc != 0
    captured = capsys.readouterr()
    assert "not_a_real_stage" in captured.err
    for stage_name in probe_runner.STAGES:
        assert stage_name in captured.err
    assert not out_path.exists()


def test_main_stage_subset_writes_full_key_set_with_unselected_stages_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(
        env_fingerprint, "collect_fingerprint", lambda: {"cpu_model": "fake"},
    )
    monkeypatch.setattr(
        env_fingerprint, "collect_calibration_vector", lambda **kwargs: {"components": {}},
    )
    out_path = tmp_path / "probe.json"
    rc = probe_runner.main([
        "--out", str(out_path), "--stages", "fingerprint,calibration",
        "--repeats", "1", "--tree-hash", "deadbeef",
    ])
    assert rc == 0
    record = json.loads(out_path.read_text(encoding="utf-8"))
    assert set(record) == ALL_TOP_LEVEL_KEYS
    assert record["fingerprint"] == {"cpu_model": "fake"}
    assert record["calibration"] == {"components": {}}
    for key in ("perf_events", "instruments", "interventions", "confirmation", "build"):
        assert record[key] == {}
    assert record["run"]["git_tree_hash"] == "deadbeef"
    assert record["run"]["git_tree_hash_source"] == "explicit"


# --- collect_build_timing -------------------------------------------------


def test_collect_build_timing_success_records_separate_seconds_and_parallelism():
    runner = _ScriptedRunner(default=_completed([], returncode=0))
    result = probe_runner.collect_build_timing(runner=runner, parallelism=4)
    assert result["status"] == "ok"
    assert result["parallelism"] == 4
    assert isinstance(result["configure_seconds"], float)
    assert isinstance(result["compile_seconds"], float)
    assert result["configure_exit_code"] == 0
    assert result["compile_exit_code"] == 0
    assert result["install_exit_code"] == 0


def test_collect_build_timing_configure_failure_is_a_failure_mapping_not_a_raise():
    runner = _ScriptedRunner(default=_completed([], returncode=0))
    runner.when(_contains("-S"), _completed([], returncode=1, stderr="cmake configure error"))
    result = probe_runner.collect_build_timing(runner=runner, parallelism=2)
    assert result["status"] == "failed"
    assert result["step"] == "configure"
    assert result["configure_exit_code"] == 1
    assert "cmake configure error" in result["stderr_excerpt"]


def test_collect_build_timing_compile_failure_is_a_failure_mapping_not_a_raise():
    runner = _ScriptedRunner(default=_completed([], returncode=0))
    runner.when(_contains("-j"), _completed([], returncode=2, stderr="compile error"))
    result = probe_runner.collect_build_timing(runner=runner, parallelism=2)
    assert result["status"] == "failed"
    assert result["step"] == "compile"
    assert result["compile_exit_code"] == 2
    assert result["configure_exit_code"] == 0


# --- _rogue_setup_env ------------------------------------------------------


def test_rogue_setup_env_reads_back_pythonpath_and_ld_library_path():
    def _runner(argv, timeout=None):
        assert argv == ["bash", "-c", f"source {probe_runner.ROGUE_SETUP_SCRIPT} && env"]
        return _completed(
            argv, returncode=0,
            stdout="PATH=/usr/bin\nPYTHONPATH=/opt/rogue/python\nLD_LIBRARY_PATH=/opt/rogue/lib\nHOME=/root\n",
        )

    env_vars = probe_runner._rogue_setup_env(_runner)
    assert env_vars == {"PYTHONPATH": "/opt/rogue/python", "LD_LIBRARY_PATH": "/opt/rogue/lib"}


def test_rogue_setup_env_empty_when_sourcing_fails():
    runner = _ScriptedRunner(default=_completed([], returncode=1, stderr="no such file"))
    assert probe_runner._rogue_setup_env(runner) == {}


# --- collect_confirmation_leg ---------------------------------------------


def test_collect_confirmation_leg_never_invokes_callgrind_and_states_exclusion():
    entries = [_instrument_entry(probe_instruments.INSTRUMENT_CALLGRIND, probe_instruments.VERDICT_USABLE)]
    runner = _ScriptedRunner(default=_completed([], returncode=0))
    confirmation = probe_runner.collect_confirmation_leg(
        entries, repeats=1, runner=runner, window_sampler=_fake_window_sampler,
    )
    assert probe_instruments.INSTRUMENT_CALLGRIND not in confirmation["modules"][probe_runner.CONFIRMATION_TRANSACTION_MODULE]["instruments"]
    for call in runner.calls:
        assert not any("valgrind" in part or "callgrind" in part for part in call)
    assert confirmation["excluded_instruments"][probe_instruments.INSTRUMENT_CALLGRIND] == probe_runner.CALLGRIND_EXCLUSION_REASON


def test_collect_confirmation_leg_non_usable_verdict_is_skipped_with_verdict_as_reason():
    entries = [_instrument_entry(probe_instruments.INSTRUMENT_STRACE, probe_instruments.VERDICT_COUNT_UNSTABLE)]
    runner = _ScriptedRunner(default=_completed([], returncode=0))
    confirmation = probe_runner.collect_confirmation_leg(
        entries, repeats=1, runner=runner, window_sampler=_fake_window_sampler,
    )
    for module_path in probe_runner.CONFIRMATION_MODULES:
        entry = confirmation["modules"][module_path]["instruments"][probe_instruments.INSTRUMENT_STRACE]
        assert entry == {"status": "skipped", "reason": probe_instruments.VERDICT_COUNT_UNSTABLE}


def test_collect_confirmation_leg_missing_instrument_entry_is_skipped_with_reason():
    runner = _ScriptedRunner(default=_completed([], returncode=0))
    confirmation = probe_runner.collect_confirmation_leg(
        [], repeats=1, runner=runner, window_sampler=_fake_window_sampler,
    )
    entry = confirmation["modules"][probe_runner.CONFIRMATION_TRANSACTION_MODULE]["instruments"][probe_instruments.INSTRUMENT_STRACE]
    assert entry == {"status": "skipped", "reason": probe_runner.SKIP_REASON_INSTRUMENTS_STAGE_NOT_RUN}


def test_collect_confirmation_leg_structurally_unconfirmable_instruments_are_skipped():
    entries = [
        _instrument_entry(probe_instruments.INSTRUMENT_PYTHON_TRACEMALLOC, probe_instruments.VERDICT_USABLE),
        _instrument_entry(probe_instruments.INSTRUMENT_ALLOCATOR_STATS, probe_instruments.VERDICT_USABLE),
        _instrument_entry(probe_instruments.INSTRUMENT_RESOURCE_USAGE, probe_instruments.VERDICT_USABLE),
    ]
    runner = _ScriptedRunner(default=_completed([], returncode=0))
    confirmation = probe_runner.collect_confirmation_leg(
        entries, repeats=1, runner=runner, window_sampler=_fake_window_sampler,
    )
    instruments = confirmation["modules"][probe_runner.CONFIRMATION_TRANSACTION_MODULE]["instruments"]
    for name in (
        probe_instruments.INSTRUMENT_PYTHON_TRACEMALLOC,
        probe_instruments.INSTRUMENT_ALLOCATOR_STATS,
        probe_instruments.INSTRUMENT_RESOURCE_USAGE,
    ):
        assert instruments[name] == {"status": "skipped", "reason": probe_runner.STRUCTURAL_SKIP_REASON}


def test_collect_confirmation_leg_both_module_paths_present_when_both_invocations_fail():
    entries = [_instrument_entry(probe_instruments.INSTRUMENT_STRACE, probe_instruments.VERDICT_USABLE)]
    runner = _ScriptedRunner(default=_completed([], returncode=1, stderr="everything failed"))
    confirmation = probe_runner.collect_confirmation_leg(
        entries, repeats=1, runner=runner, window_sampler=_fake_window_sampler,
    )
    assert set(confirmation["modules"]) == set(probe_runner.CONFIRMATION_MODULES)
    for module_path in probe_runner.CONFIRMATION_MODULES:
        module_result = confirmation["modules"][module_path]
        assert module_result["baseline_status"] == "failed"
        assert module_result["instruments"][probe_instruments.INSTRUMENT_STRACE]["status"] == "failed"


def test_collect_confirmation_leg_usable_wrappable_instrument_runs_and_measures():
    entries = [_instrument_entry(probe_instruments.INSTRUMENT_STRACE, probe_instruments.VERDICT_USABLE)]

    def _strace_stderr(argv):
        return _completed(
            argv, returncode=0,
            stderr="% time     seconds  usecs/call     calls    errors syscall\n"
                   "------ ----------- ----------- --------- --------- ----------------\n"
                   "100.00    0.000100           1       100           total\n",
        )

    class _StraceAwareRunner:
        def __call__(self, argv, timeout=None):
            if any("strace" in part for part in argv):
                return _strace_stderr(argv)
            return _completed(argv, returncode=0)

    confirmation = probe_runner.collect_confirmation_leg(
        entries, repeats=2, runner=_StraceAwareRunner(), window_sampler=_fake_window_sampler,
    )
    for module_path in probe_runner.CONFIRMATION_MODULES:
        result = confirmation["modules"][module_path]["instruments"][probe_instruments.INSTRUMENT_STRACE]
        assert result["status"] == "ok"
        assert result["counts"] == [100, 100]
        assert result["repeatability"]["verdict"] == probe_instruments.INSUFFICIENT_SAMPLES  # 2 < MIN_REPEATS_FOR_VERDICT
        assert isinstance(result["overhead_multiplier"], (int, float)) or result["overhead_multiplier"] == env_fingerprint.UNAVAILABLE


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
