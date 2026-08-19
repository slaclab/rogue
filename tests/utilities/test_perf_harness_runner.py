#!/usr/bin/env python3
# ----------------------------------------------------------------------------
# Title      : Perf Harness In-Job Runner Tests
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

perf_harness_runner = importlib.import_module("perf_harness_runner")
env_fingerprint = importlib.import_module("env_fingerprint")


def _completed(argv, returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(argv, returncode=returncode, stdout=stdout, stderr=stderr)


class _ScriptedRunner:
    """An injectable subprocess runner returning canned CompletedProcess
    objects keyed off a predicate over the argv, in registration order.
    Accepts (and ignores) a `timeout` keyword so it is a drop-in replacement
    for perf_harness_runner._run_subprocess everywhere it is threaded."""

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


class _FakeArgs:
    def __init__(self, modules=None, parallelism=None):
        self.modules = ",".join(modules) if modules else ",".join(perf_harness_runner.DEFAULT_PERF_MODULES)
        self.parallelism = parallelism


# --- run_stage / containment -----------------------------------------------


def test_run_stage_returns_collector_result_on_success():
    result = perf_harness_runner.run_stage("alpha", lambda: {"value": 42})
    assert result == {"value": 42}


def test_run_stage_contains_exception_into_failure_mapping():
    def _raising():
        raise RuntimeError("boom")

    result = perf_harness_runner.run_stage("alpha", _raising)
    assert result["status"] == "failed"
    assert result["exception_class"] == "RuntimeError"
    assert "boom" in result["message"]


def test_run_stage_bounds_the_exception_message():
    def _raising():
        raise RuntimeError("x" * 10000)

    result = perf_harness_runner.run_stage("alpha", _raising)
    assert len(result["message"]) <= perf_harness_runner.STAGE_ERROR_MESSAGE_MAX_CHARS


def _custom_stages(raising: bool = True) -> dict:
    def _alpha_factory(ctx):
        return lambda: {"alpha": "ok"}

    def _beta_raising_factory(ctx):
        def _fn():
            raise ValueError("beta failed")
        return _fn

    def _beta_ok_factory(ctx):
        return lambda: {"beta": "ok"}

    def _gamma_factory(ctx):
        return lambda: {"gamma": "ok"}

    return {
        "alpha": ("alpha_key", _alpha_factory),
        "beta": ("beta_key", _beta_raising_factory if raising else _beta_ok_factory),
        "gamma": ("gamma_key", _gamma_factory),
    }


def test_collect_stage_results_raising_stage_does_not_prevent_later_stages():
    stages = _custom_stages(raising=True)
    results, errors = perf_harness_runner.collect_stage_results(
        ["alpha", "beta", "gamma"], _FakeArgs(), stages=stages,
    )
    assert results["alpha_key"] == {"alpha": "ok"}
    assert results["beta_key"]["status"] == "failed"
    assert results["beta_key"]["exception_class"] == "ValueError"
    assert results["gamma_key"] == {"gamma": "ok"}


def test_collect_stage_results_records_one_error_entry_per_raising_stage_and_contains_it():
    stages = _custom_stages(raising=True)
    _results, errors = perf_harness_runner.collect_stage_results(
        ["alpha", "beta", "gamma"], _FakeArgs(), stages=stages,
    )
    assert len(errors) == 1
    assert errors[0]["stage"] == "beta"
    assert errors[0]["exception_class"] == "ValueError"


def test_collect_stage_results_only_runs_selected_stages():
    stages = _custom_stages(raising=False)
    results, _errors = perf_harness_runner.collect_stage_results(
        ["alpha", "gamma"], _FakeArgs(), stages=stages,
    )
    assert set(results) == {"alpha_key", "gamma_key"}


def test_stages_registry_runs_build_before_measurement():
    names = list(perf_harness_runner.STAGES)
    assert names.index("build") < names.index("measurement")


# --- collect_build_timing ---------------------------------------------------


def test_collect_build_timing_success_records_separate_seconds_and_parallelism():
    runner = _ScriptedRunner(default=_completed([], returncode=0))
    result = perf_harness_runner.collect_build_timing(runner=runner, parallelism=4)
    assert result["status"] == "ok"
    assert result["parallelism"] == 4
    assert isinstance(result["configure_seconds"], float)
    assert isinstance(result["compile_seconds"], float)
    assert result["configure_exit_code"] == 0
    assert result["compile_exit_code"] == 0
    assert result["install_exit_code"] == 0


def test_collect_build_timing_configure_command_carries_the_two_required_flags():
    runner = _ScriptedRunner(default=_completed([], returncode=0))
    perf_harness_runner.collect_build_timing(runner=runner, parallelism=2)
    configure_call = runner.calls[0]
    assert "-DROGUE_BUILD_TESTS=OFF" in configure_call
    assert "-DCMAKE_CXX_COMPILER_LAUNCHER=ccache" in configure_call


def test_collect_build_timing_configure_failure_is_a_failure_mapping_not_a_raise():
    runner = _ScriptedRunner(default=_completed([], returncode=0))
    runner.when(_contains("-S"), _completed([], returncode=1, stderr="cmake configure error"))
    result = perf_harness_runner.collect_build_timing(runner=runner, parallelism=2)
    assert result["status"] == "failed"
    assert result["step"] == "configure"
    assert result["configure_exit_code"] == 1
    assert "cmake configure error" in result["stderr_excerpt"]


def test_collect_build_timing_compile_failure_is_a_failure_mapping_not_a_raise():
    runner = _ScriptedRunner(default=_completed([], returncode=0))
    runner.when(_contains("-j"), _completed([], returncode=2, stderr="compile error"))
    result = perf_harness_runner.collect_build_timing(runner=runner, parallelism=2)
    assert result["status"] == "failed"
    assert result["step"] == "compile"
    assert result["compile_exit_code"] == 2
    assert result["configure_exit_code"] == 0


# --- collect_ccache_stats ----------------------------------------------------


def _print_stats_stdout(direct_hits=0, preprocessed_hits=0, misses=0):
    return (
        f"direct_cache_hit\t{direct_hits}\n"
        f"preprocessed_cache_hit\t{preprocessed_hits}\n"
        f"cache_miss\t{misses}\n"
        "files_in_cache\t0\n"
    )


def test_collect_ccache_stats_derives_hit_rate_from_raw_counters():
    runner = _ScriptedRunner(default=_completed([], returncode=0))
    runner.when(_contains("--version"), _completed([], returncode=0, stdout="ccache version 4.9.1\n"))
    runner.when(
        _contains("--print-stats"),
        _completed([], returncode=0, stdout=_print_stats_stdout(direct_hits=3, preprocessed_hits=1, misses=1)),
    )
    runner.when(_contains("-s"), _completed([], returncode=0, stdout="human readable stats\n"))
    result = perf_harness_runner.collect_ccache_stats(runner=runner)
    assert result["status"] == "ok"
    assert result["hit_count"] == 4
    assert result["miss_count"] == 1
    assert result["hit_rate_percent"] == pytest.approx(80.0)
    assert result["version"] == "ccache version 4.9.1"
    assert "human readable stats" in result["human_readable"]


def test_collect_ccache_stats_exact_zero_hit_rate_when_every_compilation_missed():
    runner = _ScriptedRunner(default=_completed([], returncode=0))
    runner.when(_contains("--version"), _completed([], returncode=0, stdout="ccache version 4.9.1\n"))
    runner.when(
        _contains("--print-stats"),
        _completed([], returncode=0, stdout=_print_stats_stdout(direct_hits=0, preprocessed_hits=0, misses=7)),
    )
    result = perf_harness_runner.collect_ccache_stats(runner=runner)
    assert result["status"] == "ok"
    assert result["hit_count"] == 0
    assert result["miss_count"] == 7
    assert result["hit_rate_percent"] == 0.0


def test_collect_ccache_stats_unavailable_when_binary_absent():
    runner = _ScriptedRunner(default=_completed([], returncode=1, stderr="ccache: command not found"))
    result = perf_harness_runner.collect_ccache_stats(runner=runner)
    assert result["status"] == perf_harness_runner.CCACHE_STATUS_UNAVAILABLE
    assert "hit_rate_percent" not in result
    assert "reason" in result


def test_collect_ccache_stats_unavailable_when_print_stats_unsupported():
    runner = _ScriptedRunner(default=_completed([], returncode=0))
    runner.when(_contains("--version"), _completed([], returncode=0, stdout="ccache version 3.7.0\n"))
    runner.when(_contains("--print-stats"), _completed([], returncode=1, stderr="unrecognized option"))
    result = perf_harness_runner.collect_ccache_stats(runner=runner)
    assert result["status"] == perf_harness_runner.CCACHE_STATUS_UNAVAILABLE
    assert "hit_rate_percent" not in result


def test_collect_ccache_stats_zero_hit_rate_is_distinguishable_from_unavailable():
    zero_runner = _ScriptedRunner(default=_completed([], returncode=0))
    zero_runner.when(_contains("--version"), _completed([], returncode=0, stdout="ccache version 4.9.1\n"))
    zero_runner.when(
        _contains("--print-stats"),
        _completed([], returncode=0, stdout=_print_stats_stdout(misses=5)),
    )
    unavailable_runner = _ScriptedRunner(default=_completed([], returncode=1))

    zero_result = perf_harness_runner.collect_ccache_stats(runner=zero_runner)
    unavailable_result = perf_harness_runner.collect_ccache_stats(runner=unavailable_runner)

    assert zero_result["status"] == "ok"
    assert zero_result["hit_rate_percent"] == 0.0
    assert unavailable_result["status"] == perf_harness_runner.CCACHE_STATUS_UNAVAILABLE
    assert zero_result["status"] != unavailable_result["status"]


def test_collect_ccache_stats_does_not_parse_the_human_readable_percentage():
    # A ccache -s block whose human-readable percentage would round differently than the
    # raw-counter derivation must never leak into hit_rate_percent.
    runner = _ScriptedRunner(default=_completed([], returncode=0))
    runner.when(_contains("--version"), _completed([], returncode=0, stdout="ccache version 4.9.1\n"))
    runner.when(
        _contains("--print-stats"),
        _completed([], returncode=0, stdout=_print_stats_stdout(direct_hits=1, preprocessed_hits=0, misses=2)),
    )
    runner.when(_contains("-s"), _completed([], returncode=0, stdout="Hits: 99.9 %    (rounded, misleading)\n"))
    result = perf_harness_runner.collect_ccache_stats(runner=runner)
    assert result["hit_rate_percent"] == pytest.approx(100.0 / 3.0)


def test_run_build_stage_zeroes_ccache_before_timing_the_build():
    runner = _ScriptedRunner(default=_completed([], returncode=0))
    runner.when(_contains("--print-stats"), _completed([], returncode=0, stdout=_print_stats_stdout(misses=1)))
    perf_harness_runner._run_build_stage(runner=runner, parallelism=2)
    zero_index = next(i for i, call in enumerate(runner.calls) if "--zero-stats" in call)
    configure_index = next(i for i, call in enumerate(runner.calls) if "-S" in call)
    assert zero_index < configure_index


# --- collect_build_targets ---------------------------------------------------

# A dry run (-n) against an already-built tree: real evidence from a hosted-runner run showed
# cmake --build build --target help lists every per-source-file convenience target Unix
# Makefiles generates (hundreds of .o/.i/.s targets), which is NOT what "all" resolves to; only
# the dry-run's "Built target <name>" lines name what actually gets built.
_DRY_RUN_STDOUT = """\
/usr/bin/cmake -E cmake_progress_start build/CMakeFiles build/CMakeFiles/progress.marks
/usr/bin/gmake -s -f CMakeFiles/Makefile2 all
/usr/bin/cmake -E cmake_echo_color --switch= --progress-dir=build/CMakeFiles --progress-num=1,2 "Built target rogue-core"
/usr/bin/cmake -E cmake_echo_color --switch= --progress-dir=build/CMakeFiles --progress-num=3 "Built target rogue-core-shared"
/usr/bin/cmake -E cmake_echo_color --switch= --progress-dir=build/CMakeFiles --progress-num=4 "Built target rogue"
"""


def test_collect_build_targets_captures_resolved_target_set_and_rogue_build_tests_budget():
    runner = _ScriptedRunner(default=_completed([], returncode=0))
    runner.when(_contains("--target"), _completed([], returncode=0, stdout=_DRY_RUN_STDOUT))
    runner.when(
        _contains("-L"),
        _completed([], returncode=0, stdout="ROGUE_BUILD_TESTS:BOOL=OFF\nCMAKE_BUILD_TYPE:STRING=Release\n"),
    )
    result = perf_harness_runner.collect_build_targets(runner=runner)
    assert result["status"] == "ok"
    assert result["resolved_targets"] == ["rogue", "rogue-core", "rogue-core-shared"]
    assert result["rogue_build_tests"] == "OFF"


def test_collect_build_targets_does_not_include_per_source_file_convenience_targets():
    # Regression pin for the real defect found via a hosted-runner run: --target help's output
    # (hundreds of .o/.i/.s per-source targets) must never leak into resolved_targets.
    runner = _ScriptedRunner(default=_completed([], returncode=0))
    runner.when(_contains("--target"), _completed([], returncode=0, stdout=_DRY_RUN_STDOUT))
    runner.when(_contains("-L"), _completed([], returncode=0, stdout="ROGUE_BUILD_TESTS:BOOL=OFF\n"))
    result = perf_harness_runner.collect_build_targets(runner=runner)
    assert not any(name.endswith((".o", ".i", ".s")) for name in result["resolved_targets"])


def test_collect_build_targets_failed_dry_run_is_a_failure_mapping():
    # A dry run against a bare/unconfigured tree fails partway (missing-prerequisite error)
    # rather than enumerating every target; that must be recorded as a failure, never partial.
    runner = _ScriptedRunner(default=_completed([], returncode=2, stderr="no rule to make target"))
    result = perf_harness_runner.collect_build_targets(runner=runner)
    assert result["status"] == "failed"


def test_collect_build_targets_unreadable_rogue_build_tests_records_unavailable():
    runner = _ScriptedRunner(default=_completed([], returncode=0))
    runner.when(_contains("--target"), _completed([], returncode=0, stdout=_DRY_RUN_STDOUT))
    runner.when(_contains("-L"), _completed([], returncode=1, stderr="cache read failed"))
    result = perf_harness_runner.collect_build_targets(runner=runner)
    assert result["rogue_build_tests"] == env_fingerprint.UNAVAILABLE


# --- collect_measurement -----------------------------------------------------


def test_collect_measurement_success_records_modules_and_exit_code():
    runner = _ScriptedRunner(default=_completed([], returncode=0))
    result = perf_harness_runner.collect_measurement(runner=runner, modules=("tests/perf/test_fifo_perf.py",))
    assert result["status"] == "ok"
    assert result["exit_code"] == 0
    assert result["modules"] == ["tests/perf/test_fifo_perf.py"]


def test_collect_measurement_failure_is_a_failure_mapping_not_a_raise():
    runner = _ScriptedRunner(default=_completed([], returncode=1, stderr="pytest failed"))
    result = perf_harness_runner.collect_measurement(runner=runner)
    assert result["status"] == "failed"
    assert result["exit_code"] == 1
    assert "pytest failed" in result["stderr_excerpt"]


def test_collect_measurement_prefixes_extra_env_onto_the_pytest_argv():
    runner = _ScriptedRunner(default=_completed([], returncode=0))
    perf_harness_runner.collect_measurement(
        runner=runner, modules=("tests/perf/test_fifo_perf.py",),
        extra_env={"PYTHONPATH": "/opt/rogue/python"},
    )
    call = runner.calls[0]
    assert call[0] == "env"
    assert "PYTHONPATH=/opt/rogue/python" in call
    assert "pytest" in call


# --- _rogue_setup_env ---------------------------------------------------------


def test_rogue_setup_env_reads_back_pythonpath_and_ld_library_path():
    def _runner(argv, timeout=None):
        assert argv == ["bash", "-c", f"source {perf_harness_runner.ROGUE_SETUP_SCRIPT} && env"]
        return _completed(
            argv, returncode=0,
            stdout="PATH=/usr/bin\nPYTHONPATH=/opt/rogue/python\nLD_LIBRARY_PATH=/opt/rogue/lib\nHOME=/root\n",
        )

    env_vars = perf_harness_runner._rogue_setup_env(_runner)
    assert env_vars == {"PYTHONPATH": "/opt/rogue/python", "LD_LIBRARY_PATH": "/opt/rogue/lib"}


def test_rogue_setup_env_empty_when_sourcing_fails():
    runner = _ScriptedRunner(default=_completed([], returncode=1, stderr="no such file"))
    assert perf_harness_runner._rogue_setup_env(runner) == {}


def test_measurement_stage_fn_threads_rogue_setup_env_into_the_pytest_invocation():
    runner = _ScriptedRunner(default=_completed([], returncode=0))
    runner.when(
        _contains("setup_rogue.sh"),
        _completed([], returncode=0, stdout="PYTHONPATH=/opt/rogue/python\n"),
    )
    ctx = {"args": _FakeArgs(modules=("tests/perf/test_fifo_perf.py",)), "runner": runner, "record": {}}
    fn = perf_harness_runner._measurement_stage_fn(ctx)
    fn()
    pytest_call = next(call for call in runner.calls if "pytest" in call)
    assert "PYTHONPATH=/opt/rogue/python" in pytest_call


# --- collect_benchmarks -------------------------------------------------------


def _write_benchmark_file(directory: Path, filename: str, benchmark_name: str, environment=None):
    record = {
        "harness_schema_version": 1,
        "run": {"git_sha": "deadbeef"},
        "environment": environment if environment is not None else {"cpu_model": "fake"},
        "build": {},
        "benchmarks": {benchmark_name: {"metrics": {}, "workload": {}}},
        "errors": [],
    }
    (directory / filename).write_text(json.dumps(record))


def test_collect_benchmarks_aggregates_every_file_keyed_by_benchmark_name(tmp_path):
    _write_benchmark_file(tmp_path, "a.json", "remoteSetRate")
    _write_benchmark_file(tmp_path, "b.json", "fifo_perf")
    benchmarks, environment, errors = perf_harness_runner.collect_benchmarks(tmp_path)
    assert set(benchmarks) == {"remoteSetRate", "fifo_perf"}
    assert environment == {"cpu_model": "fake"}
    assert errors == []


def test_collect_benchmarks_skips_unparseable_file_and_records_it_in_errors(tmp_path):
    (tmp_path / "broken.json").write_text("{ not valid json")
    _write_benchmark_file(tmp_path, "ok.json", "fifo_perf")
    benchmarks, _environment, errors = perf_harness_runner.collect_benchmarks(tmp_path)
    assert set(benchmarks) == {"fifo_perf"}
    assert len(errors) == 1
    assert errors[0]["file"] == "broken.json"


def test_collect_benchmarks_missing_benchmarks_key_is_skipped_and_recorded(tmp_path):
    (tmp_path / "malformed.json").write_text(json.dumps({"not_benchmarks": {}}))
    benchmarks, _environment, errors = perf_harness_runner.collect_benchmarks(tmp_path)
    assert benchmarks == {}
    assert len(errors) == 1
    assert errors[0]["file"] == "malformed.json"


def test_collect_benchmarks_returns_empty_when_results_dir_is_none():
    benchmarks, environment, errors = perf_harness_runner.collect_benchmarks(None)
    assert benchmarks == {} and environment == {} and errors == []


def test_collect_benchmarks_returns_empty_when_results_dir_does_not_exist(tmp_path):
    benchmarks, environment, errors = perf_harness_runner.collect_benchmarks(tmp_path / "nope")
    assert benchmarks == {} and environment == {} and errors == []


# --- build_run_record ---------------------------------------------------------


def test_build_run_record_has_the_fixed_seven_key_shape():
    record = perf_harness_runner.build_run_record(
        git_tree_hash="treehash", git_tree_hash_source="explicit",
        environment={"cpu_model": "fake"}, build={"timing": {}}, benchmarks={"a": {}},
        stages={"build": {}}, errors=[],
    )
    assert set(record) == {
        "harness_run_schema_version", "run", "environment", "build", "benchmarks", "stages", "errors",
    }
    assert record["harness_run_schema_version"] == perf_harness_runner.HARNESS_RUN_SCHEMA_VERSION
    assert record["run"]["git_tree_hash"] == "treehash"
    assert record["run"]["git_tree_hash_source"] == "explicit"


# --- behavior: a failed build stage still yields a populated benchmarks block ----


def test_a_failing_build_stage_still_yields_a_populated_benchmarks_block(tmp_path):
    _write_benchmark_file(tmp_path, "a.json", "remoteSetRate")

    def _raising_build_factory(ctx):
        def _fn():
            raise RuntimeError("configure exploded")
        return _fn

    stages = {"build": ("build", _raising_build_factory)}

    stage_results, errors = perf_harness_runner.collect_stage_results(
        ["build"], _FakeArgs(), stages=stages,
    )
    assert stage_results["build"]["status"] == "failed"

    benchmarks, environment, benchmark_errors = perf_harness_runner.collect_benchmarks(tmp_path)
    record = perf_harness_runner.build_run_record(
        git_tree_hash="treehash", git_tree_hash_source="explicit",
        environment=environment, build=stage_results["build"], benchmarks=benchmarks,
        stages=stage_results, errors=errors + benchmark_errors,
    )
    assert record["build"]["status"] == "failed"
    assert record["benchmarks"] == {"remoteSetRate": {"metrics": {}, "workload": {}}}


# --- format_ccache_summary_markdown ------------------------------------------


def test_format_ccache_summary_markdown_ok_case_includes_hit_rate_and_counts():
    text = perf_harness_runner.format_ccache_summary_markdown({
        "status": "ok", "version": "ccache version 4.9.1",
        "hit_rate_percent": 42.5, "hit_count": 17, "miss_count": 23,
    })
    assert "42.50%" in text
    assert "17" in text
    assert "23" in text


def test_format_ccache_summary_markdown_unavailable_case_states_the_reason():
    text = perf_harness_runner.format_ccache_summary_markdown({
        "status": "unavailable", "reason": "ccache binary not found or --version failed",
    })
    assert "unavailable" in text
    assert "ccache binary not found" in text


def test_format_build_targets_summary_markdown_ok_case_includes_targets_and_rogue_build_tests():
    text = perf_harness_runner.format_build_targets_summary_markdown({
        "status": "ok", "resolved_targets": ["rogue", "rogue-core", "rogue-core-shared"],
        "rogue_build_tests": "OFF",
    })
    assert "OFF" in text
    assert "rogue-core-shared" in text


def test_format_build_targets_summary_markdown_unavailable_case_states_the_reason():
    text = perf_harness_runner.format_build_targets_summary_markdown({
        "status": "failed", "reason": "cmake --build build --target help failed",
    })
    assert "unavailable" in text
    assert "cmake --build build --target help failed" in text


def test_main_print_build_targets_summary_mode_does_not_require_out(monkeypatch, capsys):
    monkeypatch.setattr(
        perf_harness_runner, "collect_build_targets",
        lambda **kwargs: {"status": "ok", "resolved_targets": ["rogue"], "rogue_build_tests": "OFF"},
    )
    rc = perf_harness_runner.main(["--print-build-targets-summary"])
    assert rc == 0
    assert "OFF" in capsys.readouterr().out


# --- CLI ----------------------------------------------------------------------


def test_main_unknown_stage_name_exits_nonzero_and_lists_valid_names(tmp_path, capsys):
    out_path = tmp_path / "run.json"
    rc = perf_harness_runner.main(["--out", str(out_path), "--stages", "not_a_real_stage"])
    assert rc != 0
    captured = capsys.readouterr()
    assert "not_a_real_stage" in captured.err
    for stage_name in perf_harness_runner.STAGES:
        assert stage_name in captured.err
    assert not out_path.exists()


def test_main_requires_out_unless_print_ccache_summary(capsys):
    rc = perf_harness_runner.main([])
    assert rc != 0
    assert "--out" in capsys.readouterr().err


def test_main_print_ccache_summary_mode_does_not_require_out(monkeypatch, capsys):
    monkeypatch.setattr(
        perf_harness_runner, "collect_ccache_stats",
        lambda **kwargs: {"status": "unavailable", "reason": "ccache not installed in this test"},
    )
    rc = perf_harness_runner.main(["--print-ccache-summary"])
    assert rc == 0
    assert "ccache not installed in this test" in capsys.readouterr().out


def test_main_empty_stage_selection_writes_full_shape_with_empty_stages(tmp_path):
    out_path = tmp_path / "run.json"
    rc = perf_harness_runner.main([
        "--out", str(out_path), "--stages", "", "--tree-hash", "deadbeef",
        "--results-dir", str(tmp_path / "no-such-dir"),
    ])
    assert rc == 0
    record = json.loads(out_path.read_text(encoding="utf-8"))
    assert record["stages"] == {}
    assert record["build"] == {}
    assert record["benchmarks"] == {}
    assert record["run"]["git_tree_hash"] == "deadbeef"
    assert record["run"]["git_tree_hash_source"] == "explicit"


def test_main_aggregates_benchmarks_from_results_dir_with_no_stages_selected(tmp_path):
    results_dir = tmp_path / "harness-results"
    results_dir.mkdir()
    _write_benchmark_file(results_dir, "a.json", "remoteSetRate")
    out_path = tmp_path / "run.json"
    rc = perf_harness_runner.main([
        "--out", str(out_path), "--stages", "", "--tree-hash", "deadbeef",
        "--results-dir", str(results_dir),
    ])
    assert rc == 0
    record = json.loads(out_path.read_text(encoding="utf-8"))
    assert record["benchmarks"] == {"remoteSetRate": {"metrics": {}, "workload": {}}}
    assert record["environment"] == {"cpu_model": "fake"}


def test_help_exits_zero():
    with pytest.raises(SystemExit) as exc_info:
        perf_harness_runner.main(["--help"])
    assert exc_info.value.code == 0


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
