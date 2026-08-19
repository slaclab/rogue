#!/usr/bin/env python3
# ----------------------------------------------------------------------------
# Title      : Perf Gate A/B Runner Tests
# ----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
# ----------------------------------------------------------------------------

"""Behavioural coverage for scripts/perf_gate_ab_runner.py, driven entirely through an
injectable scripted subprocess runner: no real `git`, `cmake`, `ccache`, or pytest
subprocess ever runs. Every test builds its own small synthetic input, following
tests/utilities/test_perf_harness_runner.py's and
tests/utilities/test_perf_harness_campaign.py's conventions.
"""

from __future__ import annotations

import argparse
import importlib
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

perf_gate_ab_runner = importlib.import_module("perf_gate_ab_runner")
perf_gate_evaluator = importlib.import_module("perf_gate_evaluator")


CAND_SHA = "a" * 40
BASE_SHA = "b" * 40


def _completed(argv, returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(argv, returncode=returncode, stdout=stdout, stderr=stderr)


class _ScriptedRunner:
    """An injectable subprocess runner returning canned CompletedProcess objects (or, for
    a matched rule whose response is callable, the result of calling that callable with
    `(argv, cwd)` -- used to simulate a measurement subprocess writing its own output
    file), keyed off a predicate over `(argv, cwd)`, in registration order. Every
    invocation is recorded in `calls` (each a `{"argv", "cwd", "timeout"}` mapping) so both
    the interleaving order and the worktree cleanup can be asserted from the call log."""

    def __init__(self, default=None):
        self._rules: list[tuple] = []
        self._default = default if default is not None else _completed([], returncode=0)
        self.calls: list[dict] = []

    def when(self, predicate, response):
        self._rules.append((predicate, response))
        return self

    def __call__(self, argv, timeout=None, cwd=None):
        self.calls.append({"argv": argv, "cwd": cwd, "timeout": timeout})
        # Most-recently-registered rule wins: tests build a general-purpose runner via
        # _happy_runner() and then layer a more specific `.when(...)` override on top,
        # which must take precedence over the earlier general rule.
        for predicate, response in reversed(self._rules):
            if predicate(argv, cwd):
                if callable(response) and not isinstance(response, subprocess.CompletedProcess):
                    return response(argv, cwd)
                return response
        return self._default


def _argv_contains(token):
    return lambda argv, cwd: any(token in part for part in argv)


def _cwd_is(path):
    path = str(path)
    return lambda argv, cwd: cwd == path


def _all(*predicates):
    return lambda argv, cwd: all(predicate(argv, cwd) for predicate in predicates)


def _modules_arg_value(argv):
    for index, part in enumerate(argv):
        if part == "--modules" and index + 1 < len(argv):
            return argv[index + 1]
    return None


def _modules_arg_has_comma(argv, cwd):
    """True for the main measurement loop's own invocation (the full, comma-joined
    module set) and false for the retry's narrowed single-module invocation -- used to
    give the candidate leg's first attempt and its retry two different scripted
    responses without the module argument's own value needing to be spelled out."""
    value = _modules_arg_value(argv)
    return value is not None and "," in value


def _modules_arg_has_no_comma(argv, cwd):
    value = _modules_arg_value(argv)
    return value is not None and "," not in value


def _write_measurement_record(benchmark="bench1", metric="m1", value=100.0, n=5):
    """A response callable simulating a successful
    scripts/perf_harness_runner.py --stages measurement invocation: writes a small,
    real-shaped harness-run record to the path following `--out` in argv, and returns a
    zero-exit CompletedProcess."""
    def _respond(argv, cwd):
        out_path = None
        for index, part in enumerate(argv):
            if part == "--out" and index + 1 < len(argv):
                out_path = Path(argv[index + 1])
                break
        record = {
            "harness_run_schema_version": 1,
            "run": {"git_sha": "deadbeef"},
            "environment": {"cpu_model": "fake"},
            "build": {},
            "benchmarks": {
                benchmark: {
                    "metrics": {
                        metric: {
                            "tier_candidate": 1,
                            "status": "ok",
                            "reason": None,
                            "samples": [value] * n,
                            "rejected_samples": [],
                            "n_clean": n,
                            "median": value,
                            "mad": 0.0,
                        },
                    },
                    "measurement_windows": [],
                },
            },
            "stages": {"measurement": {"status": "ok"}},
            "errors": [],
        }
        if out_path is not None:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(json.dumps(record), encoding="utf-8")
        return _completed(argv, returncode=0)
    return _respond


def _failing_measurement_response(argv, cwd):
    return _completed(argv, returncode=1, stderr="pytest failed")


def _happy_runner() -> _ScriptedRunner:
    """Every git/cmake/ccache call succeeds via the zero-exit default; the measurement
    subprocess writes a real record via _write_measurement_record()."""
    runner = _ScriptedRunner(default=_completed([], returncode=0))
    runner.when(_argv_contains("perf_harness_runner.py"), _write_measurement_record())
    return runner


def _base_argv(out_path, worktree_root, repo_root, *, rounds=2, extra=None):
    """The shared argv builder every test in this file starts from. `--baseline` defaults
    to a path inside `worktree_root` that is guaranteed never to exist (a fresh tmp_path
    subtree, per test): perf_gate_ab_runner._load_baseline_for_retry's own defensive read
    substitutes a zero-cell baseline for it, which resolves to a structural INCONCLUSIVE
    (no-gating-cell-evaluated) and never retries. Without this default, every test here
    would fall through to the evaluator's own DEFAULT_BASELINE_PATH -- the real committed
    gate-baseline.json -- whose real benchmark names never match this file's synthetic
    "bench1"/"m1" data, making every one of its ~525 baseline cells metric-absent (now
    retry-eligible) and firing an unwanted extra retry pass on every pre-existing test in
    this file. A test that wants to exercise the retry passes its own `--baseline` via
    `extra`, which -- appearing after this default in argv -- overrides it, since argparse
    keeps the last-seen value for a repeated option."""
    argv = [
        "--out", str(out_path),
        "--candidate-ref", CAND_SHA,
        "--merge-base-ref", BASE_SHA,
        "--mode", "null",
        "--rounds", str(rounds),
        "--worktree-root", str(worktree_root),
        "--repo-root", str(repo_root),
        "--baseline", str(Path(worktree_root) / "no-such-baseline.json"),
    ]
    if extra:
        argv.extend(extra)
    return argv


# --- full pipeline: happy path -------------------------------------------------------


def test_happy_pipeline_produces_two_legs_with_matching_round_count_and_tree_hash_pair(tmp_path):
    runner = _happy_runner()
    out_path = tmp_path / "ab.json"
    rc = perf_gate_ab_runner.main(
        _base_argv(out_path, tmp_path / "wt", tmp_path), runner=runner,
    )
    assert rc == 0
    record = json.loads(out_path.read_text(encoding="utf-8"))
    assert set(record["legs"]) == {"candidate", "merge_base"}
    assert record["legs"]["candidate"]["round_count"] == 2
    assert record["legs"]["merge_base"]["round_count"] == 2
    assert record["run"]["tree_hash_pair_match"] is True


def test_happy_pipeline_measurement_invocations_alternate_by_cwd(tmp_path):
    runner = _happy_runner()
    out_path = tmp_path / "ab.json"
    worktree_root = tmp_path / "wt"
    perf_gate_ab_runner.main(_base_argv(out_path, worktree_root, tmp_path), runner=runner)

    measurement_calls = [call for call in runner.calls if any("perf_harness_runner.py" in p for p in call["argv"])]
    cwds = [call["cwd"] for call in measurement_calls]
    expected = [
        str(worktree_root / "candidate") if leg == "candidate" else str(worktree_root / "merge_base")
        for leg in perf_gate_ab_runner.interleave_order(2)
    ]
    assert cwds == expected


def test_happy_pipeline_both_worktrees_are_removed_on_success(tmp_path):
    runner = _happy_runner()
    out_path = tmp_path / "ab.json"
    worktree_root = tmp_path / "wt"
    perf_gate_ab_runner.main(_base_argv(out_path, worktree_root, tmp_path), runner=runner)

    remove_calls = [call["argv"] for call in runner.calls if "remove" in call["argv"]]
    joined = [" ".join(argv) for argv in remove_calls]
    assert any(str(worktree_root / "candidate") in line for line in joined)
    assert any(str(worktree_root / "merge_base") in line for line in joined)


# --- failure containment --------------------------------------------------------------


def test_failing_merge_base_build_still_measures_candidate_and_does_not_abort(tmp_path):
    runner = _happy_runner()
    worktree_root = tmp_path / "wt"
    merge_base_worktree = str(worktree_root / "merge_base")
    runner.when(
        _all(_argv_contains("-S"), _cwd_is(merge_base_worktree)),
        _completed([], returncode=1, stderr="cmake configure error"),
    )
    out_path = tmp_path / "ab.json"
    rc = perf_gate_ab_runner.main(_base_argv(out_path, worktree_root, tmp_path), runner=runner)

    assert rc == 0
    record = json.loads(out_path.read_text(encoding="utf-8"))
    merge_base_build = record["legs"]["merge_base"]["build"]
    assert merge_base_build["success"] is False
    assert merge_base_build["timing"]["status"] == "failed"
    assert "cmake configure error" in merge_base_build["timing"]["stderr_excerpt"]
    assert record["legs"]["candidate"]["build"]["success"] is True
    assert record["legs"]["candidate"]["round_count"] == 2


def test_failing_worktree_add_for_merge_base_records_failure_and_still_removes_both(tmp_path):
    runner = _happy_runner()
    worktree_root = tmp_path / "wt"
    merge_base_worktree = str(worktree_root / "merge_base")
    runner.when(
        _all(_argv_contains("worktree"), _argv_contains("add"), lambda argv, cwd: merge_base_worktree in argv),
        _completed([], returncode=1, stderr="fatal: could not add worktree"),
    )
    out_path = tmp_path / "ab.json"
    rc = perf_gate_ab_runner.main(_base_argv(out_path, worktree_root, tmp_path), runner=runner)

    assert rc == 0
    record = json.loads(out_path.read_text(encoding="utf-8"))
    assert record["stages"]["worktree_merge_base"]["status"] == "failed"

    remove_calls = [" ".join(call["argv"]) for call in runner.calls if "remove" in call["argv"]]
    assert any(str(worktree_root / "candidate") in line for line in remove_calls)
    assert any(merge_base_worktree in line for line in remove_calls)


def test_worktrees_removed_even_when_a_build_stage_raises(tmp_path, monkeypatch):
    runner = _happy_runner()
    worktree_root = tmp_path / "wt"

    def _raising_build_leg(leg, worktree, runner_arg):
        raise RuntimeError("build exploded")

    monkeypatch.setattr(perf_gate_ab_runner, "build_leg", _raising_build_leg)

    out_path = tmp_path / "ab.json"
    rc = perf_gate_ab_runner.main(_base_argv(out_path, worktree_root, tmp_path), runner=runner)

    assert rc == 0
    remove_calls = [" ".join(call["argv"]) for call in runner.calls if "remove" in call["argv"]]
    assert any(str(worktree_root / "candidate") in line for line in remove_calls)
    assert any(str(worktree_root / "merge_base") in line for line in remove_calls)

    record = json.loads(out_path.read_text(encoding="utf-8"))
    assert record["legs"]["candidate"]["build"]["success"] is False


def test_patch_failing_check_is_a_failed_patch_stage_and_apply_is_never_invoked(tmp_path):
    patch_dir = tmp_path / "patches"
    patch_dir.mkdir()
    patch_file = patch_dir / "regression.patch"
    patch_file.write_text("--- a\n+++ b\n", encoding="utf-8")

    runner = _happy_runner()
    worktree_root = tmp_path / "wt"
    candidate_worktree = str(worktree_root / "candidate")
    runner.when(
        _all(_argv_contains("apply"), _argv_contains("--check"), _cwd_is(candidate_worktree)),
        _completed([], returncode=1, stderr="patch does not apply"),
    )
    out_path = tmp_path / "ab.json"
    argv = _base_argv(
        out_path, worktree_root, tmp_path,
        extra=["--patch-name", "regression.patch", "--patch-dir", str(patch_dir)],
    )
    rc = perf_gate_ab_runner.main(argv, runner=runner)

    assert rc == 0
    record = json.loads(out_path.read_text(encoding="utf-8"))
    patch_stage = record["stages"]["patch_candidate"]
    assert patch_stage["status"] == "failed"
    assert patch_stage["patch_path"] == str(patch_file)
    assert patch_stage["patch_sha256"]

    apply_without_check = [
        call for call in runner.calls
        if "apply" in call["argv"] and "--check" not in call["argv"]
    ]
    assert apply_without_check == []


# --- CCACHE_BASEDIR: per-leg build environment ----------------------------------------


def test_cwd_bound_runner_with_no_env_vars_leaves_argv_unmodified(tmp_path):
    runner = _ScriptedRunner()
    bound = perf_gate_ab_runner._cwd_bound_runner(str(tmp_path), runner)
    bound(["git", "status"])
    assert runner.calls[0]["argv"] == ["git", "status"]
    assert runner.calls[0]["cwd"] == str(tmp_path)


def test_cwd_bound_runner_with_env_vars_prefixes_argv_with_env_command(tmp_path):
    runner = _ScriptedRunner()
    bound = perf_gate_ab_runner._cwd_bound_runner(
        str(tmp_path), runner, env_vars={"CCACHE_BASEDIR": str(tmp_path)},
    )
    bound(["cmake", "-S", ".", "-B", "build"])
    assert runner.calls[0]["argv"] == [
        "env", f"CCACHE_BASEDIR={tmp_path}", "cmake", "-S", ".", "-B", "build",
    ]
    assert runner.calls[0]["cwd"] == str(tmp_path)


def test_build_leg_prefixes_every_subprocess_with_ccache_basedir_set_to_its_own_worktree(tmp_path):
    runner = _happy_runner()
    worktree = tmp_path / "candidate"
    perf_gate_ab_runner.build_leg("candidate", str(worktree), runner)

    expected_env = f"{perf_gate_ab_runner.CCACHE_BASEDIR_ENV}={worktree}"
    build_calls = [call for call in runner.calls if call["cwd"] == str(worktree)]
    assert build_calls, "build_leg should have issued at least one subprocess call"
    for call in build_calls:
        assert call["argv"][0] == "env"
        assert expected_env in call["argv"]


def test_build_leg_never_sets_ccache_nohashdir(tmp_path):
    """CCACHE_NOHASHDIR is deliberately not required: ccache's own base_dir behavior
    already relativizes the compiler's working directory once it is under base_dir, which
    holds here since the build directory is always a direct 'build' subdirectory of the
    worktree root, and this build's default Release configuration carries no -g."""
    runner = _happy_runner()
    worktree = tmp_path / "candidate"
    perf_gate_ab_runner.build_leg("candidate", str(worktree), runner)

    for call in runner.calls:
        assert not any(part.startswith("CCACHE_NOHASHDIR") for part in call["argv"])


def test_build_leg_each_leg_gets_its_own_worktree_as_ccache_basedir(tmp_path):
    """Through the full pipeline: the candidate leg's build commands carry CCACHE_BASEDIR
    set to the candidate worktree, and the merge-base leg's build commands carry
    CCACHE_BASEDIR set to the merge-base worktree -- never the other leg's path, and never
    one shared value, so the two legs' otherwise-identical compiles can hash identically
    to each other without either leg's own build ever pointing at the wrong root."""
    runner = _happy_runner()
    worktree_root = tmp_path / "wt"
    out_path = tmp_path / "ab.json"
    rc = perf_gate_ab_runner.main(_base_argv(out_path, worktree_root, tmp_path), runner=runner)
    assert rc == 0

    candidate_worktree = str(worktree_root / "candidate")
    merge_base_worktree = str(worktree_root / "merge_base")

    candidate_configure_calls = [
        call for call in runner.calls if call["cwd"] == candidate_worktree and "-S" in call["argv"]
    ]
    merge_base_configure_calls = [
        call for call in runner.calls if call["cwd"] == merge_base_worktree and "-S" in call["argv"]
    ]
    assert candidate_configure_calls, "expected at least one candidate configure call"
    assert merge_base_configure_calls, "expected at least one merge-base configure call"

    for call in candidate_configure_calls:
        assert f"{perf_gate_ab_runner.CCACHE_BASEDIR_ENV}={candidate_worktree}" in call["argv"]
    for call in merge_base_configure_calls:
        assert f"{perf_gate_ab_runner.CCACHE_BASEDIR_ENV}={merge_base_worktree}" in call["argv"]


# --- merge_leg_rounds ------------------------------------------------------------------


def _metric_entry(value, n=5, status="ok", reason=None, tier_candidate=1):
    entry = {
        "tier_candidate": tier_candidate,
        "status": status,
        "reason": reason,
        "rejected_samples": [],
    }
    if status == "ok":
        entry["samples"] = [value] * n
        entry["n_clean"] = n
        entry["median"] = value
        entry["mad"] = 0.0
    else:
        entry["samples"] = []
        entry["n_clean"] = 0
    return entry


def _round_record(benchmark, metric, entry, windows=None):
    return {
        "benchmarks": {
            benchmark: {"metrics": {metric: entry}, "measurement_windows": windows or []},
        },
    }


def test_merge_leg_rounds_concatenates_clean_samples_and_recomputes_median_and_mad():
    round_a = _round_record("bench1", "m1", _metric_entry(10.0, n=5))
    round_b = _round_record("bench1", "m1", _metric_entry(10.0, n=5))

    merged = perf_gate_ab_runner.merge_leg_rounds([round_a, round_b])

    metric = merged["bench1"]["metrics"]["m1"]
    assert metric["status"] == "ok"
    assert metric["n_clean"] == 10
    assert metric["samples"] == [10.0] * 10
    assert metric["median"] == 10.0
    assert metric["mad"] == 0.0


def test_merge_leg_rounds_one_clean_one_inconclusive_yields_not_clean_with_no_median_or_mad():
    round_a = _round_record("bench1", "m1", _metric_entry(10.0, n=5))
    round_b = _round_record(
        "bench1", "m1", _metric_entry(0, n=0, status="inconclusive", reason="insufficient-clean-samples"),
    )

    merged = perf_gate_ab_runner.merge_leg_rounds([round_a, round_b])

    metric = merged["bench1"]["metrics"]["m1"]
    assert metric["status"] == "inconclusive"
    assert metric["reason"] == "insufficient-clean-samples"
    assert "median" not in metric
    assert "mad" not in metric


def test_merge_leg_rounds_benchmark_present_in_one_round_absent_in_other_records_rounds_missing():
    round_a = _round_record("bench1", "m1", _metric_entry(10.0, n=5))
    round_b: dict = {"benchmarks": {}}

    merged = perf_gate_ab_runner.merge_leg_rounds([round_a, round_b])

    assert merged["bench1"]["rounds_missing"] == 1


def test_merge_leg_rounds_carries_tier_demoted_to_when_any_round_carried_it():
    entry_demoted = _metric_entry(10.0, n=5)
    entry_demoted["tier_demoted_to"] = 2
    round_a = _round_record("bench1", "m1", entry_demoted)
    round_b = _round_record("bench1", "m1", _metric_entry(10.0, n=5))

    merged = perf_gate_ab_runner.merge_leg_rounds([round_a, round_b])

    assert merged["bench1"]["metrics"]["m1"]["tier_demoted_to"] == 2


# --- interleave_order --------------------------------------------------------------


def test_interleave_order_lengths_and_alternation():
    assert perf_gate_ab_runner.interleave_order(0) == []
    assert perf_gate_ab_runner.interleave_order(1) == ["candidate", "merge_base"]
    assert perf_gate_ab_runner.interleave_order(3) == [
        "candidate", "merge_base", "candidate", "merge_base", "candidate", "merge_base",
    ]


# --- zero completed rounds -----------------------------------------------------------


def test_zero_completed_candidate_rounds_yields_unavailable_measure_timing_not_zero(tmp_path):
    runner = _happy_runner()
    worktree_root = tmp_path / "wt"
    candidate_worktree = str(worktree_root / "candidate")
    runner.when(
        _all(_argv_contains("perf_harness_runner.py"), _cwd_is(candidate_worktree)),
        _failing_measurement_response,
    )
    out_path = tmp_path / "ab.json"
    rc = perf_gate_ab_runner.main(_base_argv(out_path, worktree_root, tmp_path), runner=runner)

    assert rc == 0
    record = json.loads(out_path.read_text(encoding="utf-8"))
    measure_candidate = record["timings"]["measure_candidate"]
    assert not isinstance(measure_candidate, (int, float))
    assert measure_candidate != 0.0
    assert measure_candidate["reason"]
    assert record["legs"]["candidate"]["round_count"] == 0


def _write_well_formed_but_internally_failed_record():
    """A response callable simulating exactly what a real hosted run against this
    planning machine produces: scripts/perf_harness_runner.py's own main() returns 0 and
    writes a well-formed --out record even when its internal "measurement" stage itself
    failed (e.g. Rogue could not be built). Regression pin for the real defect this
    behaviour surfaced: a round record being parseable is not the same fact as a round
    having actually measured anything."""
    def _respond(argv, cwd):
        out_path = None
        for index, part in enumerate(argv):
            if part == "--out" and index + 1 < len(argv):
                out_path = Path(argv[index + 1])
                break
        record = {
            "harness_run_schema_version": 1,
            "run": {"git_sha": "deadbeef"},
            "environment": {},
            "build": {},
            "benchmarks": {},
            "stages": {"measurement": {"status": "failed", "exit_code": 1}},
            "errors": [],
        }
        if out_path is not None:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(json.dumps(record), encoding="utf-8")
        return _completed(argv, returncode=0)
    return _respond


def test_a_well_formed_record_whose_own_measurement_stage_failed_does_not_count_as_completed(tmp_path):
    runner = _happy_runner()
    worktree_root = tmp_path / "wt"
    runner.when(_argv_contains("perf_harness_runner.py"), _write_well_formed_but_internally_failed_record())
    out_path = tmp_path / "ab.json"
    rc = perf_gate_ab_runner.main(_base_argv(out_path, worktree_root, tmp_path), runner=runner)

    assert rc == 0
    record = json.loads(out_path.read_text(encoding="utf-8"))
    assert record["legs"]["candidate"]["round_count"] == 0
    assert record["legs"]["merge_base"]["round_count"] == 0
    assert not isinstance(record["timings"]["measure_candidate"], (int, float))
    assert not isinstance(record["timings"]["measure_merge_base"], (int, float))


def test_is_successful_round_rejects_a_parseable_record_with_a_failed_measurement_stage():
    parseable_but_failed = {
        "harness_run_schema_version": 1,
        "stages": {"measurement": {"status": "failed"}},
    }
    assert perf_gate_ab_runner._is_successful_round(parseable_but_failed) is False

    genuinely_completed = {
        "harness_run_schema_version": 1,
        "stages": {"measurement": {"status": "ok"}},
    }
    assert perf_gate_ab_runner._is_successful_round(genuinely_completed) is True


# --- build_ab_record: tree-hash-pair logic (direct, no scripted runner needed) -------


def _minimal_leg():
    return {"build": {"success": True}, "benchmarks": {}, "rounds": [], "round_count": 1}


def test_build_ab_record_mismatched_merge_base_tree_hash_gives_false_pair_match():
    record = perf_gate_ab_runner.build_ab_record(
        github_run_id="1", github_run_attempt="1", campaign_branch="b", dispatch_index="1",
        mode="unrelated", label=None, rounds=1,
        patch_name=None, patch_sha256=None, patch_magnitude=None, patch_applied=False,
        forced_condition=None,
        declared_candidate_ref=CAND_SHA, declared_merge_base_ref=BASE_SHA,
        declared_candidate_tree_hash="tree-cand", declared_merge_base_tree_hash="tree-base-declared",
        candidate_sha=CAND_SHA, merge_base_sha=BASE_SHA,
        candidate_tree_hash="tree-cand", merge_base_tree_hash="tree-base-measured",
        candidate_leg=_minimal_leg(), merge_base_leg=_minimal_leg(),
        environment={}, timings={}, stages={}, errors=[],
    )
    assert record["run"]["tree_hash_pair_match"] is False
    assert record["run"]["declared_merge_base_tree_hash"] == "tree-base-declared"
    assert record["run"]["merge_base_tree_hash"] == "tree-base-measured"


def test_build_ab_record_patched_candidate_leaves_match_decided_by_merge_base_half_alone():
    record = perf_gate_ab_runner.build_ab_record(
        github_run_id="1", github_run_attempt="1", campaign_branch="b", dispatch_index="1",
        mode="seeded-regression", label=None, rounds=1,
        patch_name="regression.patch", patch_sha256="deadbeef" * 8, patch_magnitude="1",
        patch_applied=True, forced_condition=None,
        declared_candidate_ref=CAND_SHA, declared_merge_base_ref=BASE_SHA,
        declared_candidate_tree_hash="tree-cand-prepatch", declared_merge_base_tree_hash="tree-base",
        candidate_sha=CAND_SHA, merge_base_sha=BASE_SHA,
        candidate_tree_hash="tree-cand-postpatch", merge_base_tree_hash="tree-base",
        candidate_leg=_minimal_leg(), merge_base_leg=_minimal_leg(),
        environment={}, timings={}, stages={}, errors=[],
    )
    # Post-patch candidate tree hash differs from its declared (pre-patch) value, yet the
    # pair still reports True because the candidate half never enters the comparison once
    # patch_applied is True -- the merge-base half alone decides it.
    assert record["run"]["tree_hash_pair_match"] is True
    assert record["run"]["patch_applied"] is True
    assert record["run"]["patch_sha256"] == "deadbeef" * 8
    assert record["run"]["candidate_sha"] == CAND_SHA


def test_build_ab_record_timings_key_order_is_identical_across_two_calls():
    kwargs = dict(
        github_run_id="1", github_run_attempt="1", campaign_branch="b", dispatch_index="1",
        mode="null", label=None, rounds=1,
        patch_name=None, patch_sha256=None, patch_magnitude=None, patch_applied=False,
        forced_condition=None,
        declared_candidate_ref=CAND_SHA, declared_merge_base_ref=BASE_SHA,
        declared_candidate_tree_hash="t", declared_merge_base_tree_hash="t",
        candidate_sha=CAND_SHA, merge_base_sha=BASE_SHA,
        candidate_tree_hash="t", merge_base_tree_hash="t",
        candidate_leg=_minimal_leg(), merge_base_leg=_minimal_leg(),
        environment={}, stages={}, errors=[],
    )
    timings_unordered_a = {"total": 9.0, "measure_merge_base": 2.0, "worktree_candidate": 1.0}
    timings_unordered_b = {"worktree_candidate": 1.0, "total": 9.0, "measure_merge_base": 2.0}

    record_a = perf_gate_ab_runner.build_ab_record(timings=timings_unordered_a, **kwargs)
    record_b = perf_gate_ab_runner.build_ab_record(timings=timings_unordered_b, **kwargs)

    assert list(record_a["timings"]) == list(record_b["timings"])
    assert list(record_a["timings"]) == list(perf_gate_ab_runner.TIMING_STAGE_ORDER)


# --- forced conditions: proven against the real evaluator ---------------------------


def _synthetic_baseline():
    return {"cells": {"bench1": {"m1": {"gate_rule": "exact-equality", "observed_value": 100.0}}}}


def test_forced_condition_merge_base_build_failed_maps_to_named_evaluator_condition(tmp_path):
    runner = _happy_runner()
    worktree_root = tmp_path / "wt"
    out_path = tmp_path / "ab.json"
    argv = _base_argv(
        out_path, worktree_root, tmp_path,
        extra=["--forced-condition", "merge-base-build-failed"],
    )
    rc = perf_gate_ab_runner.main(argv, runner=runner)
    assert rc == 0

    record = json.loads(out_path.read_text(encoding="utf-8"))
    assert record["legs"]["merge_base"]["build"]["success"] is False

    evaluation = perf_gate_evaluator.evaluate_run(record, _synthetic_baseline())
    assert evaluation["condition_counts"][perf_gate_evaluator.REASON_MERGE_BASE_BUILD_FAILED] >= 1
    assert evaluation["verdict"] != perf_gate_evaluator.VERDICT_FAIL


def test_forced_condition_metric_absent_from_leg_maps_to_named_evaluator_condition(tmp_path):
    runner = _happy_runner()
    worktree_root = tmp_path / "wt"
    out_path = tmp_path / "ab.json"
    argv = _base_argv(
        out_path, worktree_root, tmp_path,
        extra=["--forced-condition", "metric-absent-from-leg"],
    )
    rc = perf_gate_ab_runner.main(argv, runner=runner)
    assert rc == 0

    record = json.loads(out_path.read_text(encoding="utf-8"))
    assert record["legs"]["merge_base"]["benchmarks"] == {}

    evaluation = perf_gate_evaluator.evaluate_run(record, _synthetic_baseline())
    assert evaluation["condition_counts"][perf_gate_evaluator.REASON_METRIC_ABSENT] >= 1
    assert evaluation["verdict"] != perf_gate_evaluator.VERDICT_FAIL


def test_forced_condition_tree_hash_pair_mismatch_maps_to_named_evaluator_condition(tmp_path):
    runner = _happy_runner()
    worktree_root = tmp_path / "wt"
    out_path = tmp_path / "ab.json"
    argv = _base_argv(
        out_path, worktree_root, tmp_path,
        extra=["--forced-condition", "tree-hash-pair-mismatch"],
    )
    rc = perf_gate_ab_runner.main(argv, runner=runner)
    assert rc == 0

    record = json.loads(out_path.read_text(encoding="utf-8"))
    assert record["run"]["tree_hash_pair_match"] is False

    evaluation = perf_gate_evaluator.evaluate_run(record, _synthetic_baseline())
    assert evaluation["condition_counts"][perf_gate_evaluator.REASON_TREE_HASH_PAIR_MISMATCH] >= 1
    assert evaluation["verdict"] != perf_gate_evaluator.VERDICT_FAIL


def test_unrecognized_forced_condition_is_recorded_and_induces_nothing(tmp_path):
    runner = _happy_runner()
    worktree_root = tmp_path / "wt"
    out_path = tmp_path / "ab.json"
    argv = _base_argv(
        out_path, worktree_root, tmp_path,
        extra=["--forced-condition", "not-a-real-condition"],
    )
    rc = perf_gate_ab_runner.main(argv, runner=runner)
    assert rc == 0

    record = json.loads(out_path.read_text(encoding="utf-8"))
    assert record["run"]["forced_condition"] == "not-a-real-condition"
    assert record["legs"]["merge_base"]["build"]["success"] is True
    assert record["run"]["tree_hash_pair_match"] is True


# --- CLI-level validation ---------------------------------------------------------------


# --- _clamped_timeout -------------------------------------------------------------------


def test_clamped_timeout_returns_the_stage_timeout_when_the_deadline_is_far():
    result = perf_gate_ab_runner._clamped_timeout(1800, deadline_monotonic=10_000.0, clock=lambda: 0.0)
    assert result == 1800


def test_clamped_timeout_returns_the_remaining_seconds_when_the_deadline_is_near():
    result = perf_gate_ab_runner._clamped_timeout(1800, deadline_monotonic=1050.0, clock=lambda: 1000.0)
    assert result == 50


def test_clamped_timeout_returns_none_once_the_deadline_has_passed():
    result = perf_gate_ab_runner._clamped_timeout(1800, deadline_monotonic=999.0, clock=lambda: 1000.0)
    assert result is None


def test_clamped_timeout_with_no_deadline_returns_the_stage_timeout_unchanged():
    result = perf_gate_ab_runner._clamped_timeout(1800, deadline_monotonic=None, clock=lambda: 1000.0)
    assert result == 1800


# --- build_leg deadline clamping ----------------------------------------------------------


def test_build_leg_clamps_its_subprocess_timeout_to_the_remaining_deadline(tmp_path):
    runner = _happy_runner()
    worktree = tmp_path / "candidate"
    perf_gate_ab_runner.build_leg(
        "candidate", str(worktree), runner,
        deadline_monotonic=1050.0, clock=lambda: 1000.0,
    )
    build_calls = [call for call in runner.calls if call["cwd"] == str(worktree)]
    assert build_calls, "build_leg should have issued at least one subprocess call"
    for call in build_calls:
        assert call["timeout"] == 50


# --- measure_leg_round deadline handling ---------------------------------------------------


def test_measure_leg_round_records_a_named_reason_when_the_deadline_has_already_passed(tmp_path):
    runner = _ScriptedRunner(default=_completed([], returncode=0))
    result = perf_gate_ab_runner.measure_leg_round(
        str(tmp_path / "candidate"), str(tmp_path / "results"), runner,
        checkout_root=str(tmp_path),
        deadline_monotonic=999.0, clock=lambda: 1000.0,
    )
    assert result == {
        "status": "failed",
        "reason": perf_gate_ab_runner.REASON_DEADLINE_ALREADY_PASSED,
    }
    assert runner.calls == []


def test_measure_leg_round_writes_a_hang_snapshot_and_the_full_stderr_when_its_bounded_call_fails(tmp_path):
    long_stderr = "x" * 3000

    def _fail(argv, cwd):
        return _completed(argv, returncode=1, stderr=long_stderr)

    runner = _ScriptedRunner(default=_completed([], returncode=0))
    runner.when(_argv_contains("perf_harness_runner.py"), _fail)

    diagnostics_dir = tmp_path / "hang-diagnostics"
    results_dir = tmp_path / "results" / "candidate" / "0"
    now = perf_gate_ab_runner.time.monotonic()
    result = perf_gate_ab_runner.measure_leg_round(
        str(tmp_path / "candidate"), str(results_dir), runner,
        checkout_root=str(tmp_path),
        deadline_monotonic=now + perf_gate_ab_runner.GATE_RUNNER_DEADLINE_SECONDS,
        diagnostics_dir=str(diagnostics_dir),
    )

    assert result["status"] == "failed"
    assert result["reason"] == perf_gate_ab_runner.REASON_DEADLINE_BOUNDED_SUBPROCESS
    assert len(result["stderr_excerpt"]) <= perf_gate_ab_runner.perf_harness_runner.STDERR_EXCERPT_MAX_CHARS
    hang_path = Path(result["hang_diagnostics_path"])
    stderr_path = Path(result["hang_diagnostics_stderr_path"])
    assert hang_path.parent == diagnostics_dir
    assert "candidate" in hang_path.name and "round0" in hang_path.name
    assert stderr_path.read_text(encoding="utf-8") == long_stderr


def test_measure_leg_round_exports_the_faulthandler_variable_to_the_measurement_subprocess(tmp_path):
    runner = _happy_runner()
    perf_gate_ab_runner.measure_leg_round(
        str(tmp_path / "candidate"), str(tmp_path / "results"), runner,
        checkout_root=str(tmp_path),
    )
    measurement_calls = [call for call in runner.calls if any("perf_harness_runner.py" in p for p in call["argv"])]
    assert measurement_calls
    assert any("PYTHONFAULTHANDLER=1" in part for part in measurement_calls[0]["argv"])


# --- main(): every round deadline-truncated -------------------------------------------------


def test_main_writes_a_two_leg_record_when_every_measurement_round_is_deadline_truncated(tmp_path):
    runner = _happy_runner()
    runner.when(_argv_contains("perf_harness_runner.py"), _failing_measurement_response)
    worktree_root = tmp_path / "wt"
    out_path = tmp_path / "ab.json"
    rc = perf_gate_ab_runner.main(_base_argv(out_path, worktree_root, tmp_path), runner=runner)

    assert rc == 0
    record = json.loads(out_path.read_text(encoding="utf-8"))
    assert record["legs"]["candidate"]["round_count"] == 0
    assert record["legs"]["merge_base"]["round_count"] == 0

    runner_deadline = record["stages"]["runner_deadline"]
    assert runner_deadline["deadline_seconds"] == perf_gate_ab_runner.GATE_RUNNER_DEADLINE_SECONDS
    assert runner_deadline["exceeded"] is True
    assert runner_deadline["truncated_stages"]

    for round_record in record["stages"]["measure_candidate"] + record["stages"]["measure_merge_base"]:
        assert round_record["reason"] == perf_gate_ab_runner.REASON_DEADLINE_BOUNDED_SUBPROCESS


def test_a_deadline_truncated_record_evaluates_to_inconclusive_rather_than_pass(tmp_path):
    runner = _happy_runner()
    runner.when(_argv_contains("perf_harness_runner.py"), _failing_measurement_response)
    worktree_root = tmp_path / "wt"
    out_path = tmp_path / "ab.json"
    rc = perf_gate_ab_runner.main(_base_argv(out_path, worktree_root, tmp_path), runner=runner)
    assert rc == 0

    record = json.loads(out_path.read_text(encoding="utf-8"))
    evaluation = perf_gate_evaluator.evaluate_run(record, _synthetic_baseline())
    assert evaluation["verdict"] == perf_gate_evaluator.VERDICT_INCONCLUSIVE
    assert evaluation["verdict"] != perf_gate_evaluator.VERDICT_PASS


def test_main_rejects_a_non_sha_candidate_ref_and_runs_no_subprocess(tmp_path, capsys):
    out_path = tmp_path / "ab.json"
    runner = _ScriptedRunner(default=_completed([], returncode=0))
    try:
        perf_gate_ab_runner.main(
            ["--out", str(out_path), "--candidate-ref", "notasha", "--merge-base-ref", BASE_SHA],
            runner=runner,
        )
        raised = False
    except SystemExit as exc:
        raised = True
        assert exc.code == 2
    assert raised
    assert runner.calls == []
    assert not out_path.exists()


# --- _partitioned_timeout ---------------------------------------------------------------


def test_partitioned_timeout_with_no_deadline_returns_the_stage_timeout_unchanged():
    result = perf_gate_ab_runner._partitioned_timeout(1800, None, 4)
    assert result == (1800, None)


def test_partitioned_timeout_splits_the_remaining_budget_across_the_remaining_units():
    result = perf_gate_ab_runner._partitioned_timeout(1800, 1000.0 + 1260.0, 4, clock=lambda: 1000.0)
    assert result == (315, None)


def test_partitioned_timeout_caps_the_share_at_the_stage_timeout():
    result = perf_gate_ab_runner._partitioned_timeout(100, 1000.0 + 5000.0, 1, clock=lambda: 1000.0)
    assert result == (100, None)


def test_partitioned_timeout_runs_a_share_exactly_equal_to_the_floor():
    floor = perf_gate_ab_runner.GATE_ROUND_SHARE_FLOOR_SECONDS
    result = perf_gate_ab_runner._partitioned_timeout(1800, 1000.0 + floor, 1, clock=lambda: 1000.0)
    assert result == (floor, None)


def test_partitioned_timeout_skips_a_share_one_second_below_the_floor_with_the_floor_reason():
    floor = perf_gate_ab_runner.GATE_ROUND_SHARE_FLOOR_SECONDS
    result = perf_gate_ab_runner._partitioned_timeout(1800, 1000.0 + floor - 1, 1, clock=lambda: 1000.0)
    assert result == (None, perf_gate_ab_runner.REASON_DEADLINE_SHARE_BELOW_FLOOR)


def test_partitioned_timeout_runs_a_share_one_second_above_the_floor():
    floor = perf_gate_ab_runner.GATE_ROUND_SHARE_FLOOR_SECONDS
    result = perf_gate_ab_runner._partitioned_timeout(1800, 1000.0 + floor + 1, 1, clock=lambda: 1000.0)
    assert result == (floor + 1, None)


def test_partitioned_timeout_reports_the_already_passed_reason_rather_than_the_floor_reason():
    result = perf_gate_ab_runner._partitioned_timeout(1800, 999.0, 4, clock=lambda: 1000.0)
    assert result == (None, perf_gate_ab_runner.REASON_DEADLINE_ALREADY_PASSED)


def test_partitioned_timeout_treats_zero_remaining_units_as_one():
    result = perf_gate_ab_runner._partitioned_timeout(1800, 1000.0 + 400.0, 0, clock=lambda: 1000.0)
    assert result == (400, None)


def test_partitioned_timeout_truncates_the_share_toward_zero():
    result = perf_gate_ab_runner._partitioned_timeout(1800, 1000.0 + 237.9, 1, clock=lambda: 1000.0)
    assert result == (237, None)


def test_partitioned_timeout_with_a_zero_floor_never_skips():
    result = perf_gate_ab_runner._partitioned_timeout(1800, 1000.0 + 5.0, 1, floor_seconds=0, clock=lambda: 1000.0)
    assert result == (5, None)


# --- _diagnostics_arm_lead ----------------------------------------------------------------


def test_diagnostics_arm_lead_is_the_timeout_minus_the_lead_when_that_is_positive():
    assert perf_gate_ab_runner._diagnostics_arm_lead(300, 60) == 240


def test_diagnostics_arm_lead_never_returns_zero_for_a_positive_timeout():
    assert perf_gate_ab_runner._diagnostics_arm_lead(60, 60) > 0
    assert perf_gate_ab_runner._diagnostics_arm_lead(1, 60) > 0


# --- measure_leg_round: partitioning and the floor skip ----------------------------------


def test_measure_leg_round_skips_with_the_floor_reason_and_starts_no_subprocess(tmp_path):
    runner = _ScriptedRunner(default=_completed([], returncode=0))
    floor = perf_gate_ab_runner.GATE_ROUND_SHARE_FLOOR_SECONDS
    result = perf_gate_ab_runner.measure_leg_round(
        str(tmp_path / "candidate"), str(tmp_path / "results"), runner,
        checkout_root=str(tmp_path),
        deadline_monotonic=1000.0 + floor - 1, remaining_units=1, clock=lambda: 1000.0,
    )
    assert result == {
        "status": "failed",
        "reason": perf_gate_ab_runner.REASON_DEADLINE_SHARE_BELOW_FLOOR,
    }
    assert runner.calls == []


def test_measure_leg_round_skip_mapping_carries_only_status_and_reason(tmp_path):
    runner = _ScriptedRunner(default=_completed([], returncode=0))
    floor = perf_gate_ab_runner.GATE_ROUND_SHARE_FLOOR_SECONDS
    result = perf_gate_ab_runner.measure_leg_round(
        str(tmp_path / "candidate"), str(tmp_path / "results"), runner,
        checkout_root=str(tmp_path),
        deadline_monotonic=1000.0 + floor - 1, remaining_units=1, clock=lambda: 1000.0,
    )
    assert set(result.keys()) == {"status", "reason"}


def test_measure_leg_round_partitions_its_timeout_across_the_remaining_units(tmp_path):
    runner = _happy_runner()
    fixed_now = 1000.0
    result = perf_gate_ab_runner.measure_leg_round(
        str(tmp_path / "candidate"), str(tmp_path / "results"), runner,
        checkout_root=str(tmp_path),
        deadline_monotonic=fixed_now + 1260.0, remaining_units=4, clock=lambda: fixed_now,
    )
    assert result["harness_run_schema_version"] == 1
    measurement_calls = [call for call in runner.calls if any("perf_harness_runner.py" in p for p in call["argv"])]
    assert measurement_calls[0]["timeout"] == 315


# --- main(): a long first round does not starve the control rounds -----------------------


def test_main_a_long_first_candidate_round_still_leaves_the_merge_base_rounds_a_usable_share(
    tmp_path, monkeypatch,
):
    clock_state = {"now": 0.0}

    def _stub_clock():
        return clock_state["now"]

    call_count = {"n": 0}

    def _measurement_response(argv, cwd):
        call_count["n"] += 1
        # The first candidate round consumes its full partitioned share (a "long" round);
        # every later round takes negligible simulated time, exactly as the action's
        # injected-clock instruction describes.
        clock_state["now"] += 315.0 if call_count["n"] == 1 else 1.0
        return _write_measurement_record()(argv, cwd)

    monkeypatch.setattr(perf_gate_ab_runner.time, "monotonic", _stub_clock)

    runner = _happy_runner()
    runner.when(_argv_contains("perf_harness_runner.py"), _measurement_response)
    worktree_root = tmp_path / "wt"
    out_path = tmp_path / "ab.json"
    rc = perf_gate_ab_runner.main(_base_argv(out_path, worktree_root, tmp_path), runner=runner)
    assert rc == 0

    measurement_calls = [call for call in runner.calls if any("perf_harness_runner.py" in p for p in call["argv"])]
    assert len(measurement_calls) == 4
    assert measurement_calls[0]["timeout"] == 315
    for call in measurement_calls[1:]:
        assert call["timeout"] >= perf_gate_ab_runner.GATE_ROUND_SHARE_FLOOR_SECONDS

    record = json.loads(out_path.read_text(encoding="utf-8"))
    assert record["legs"]["merge_base"]["round_count"] == 2


def test_main_records_the_floor_and_the_unit_count_on_the_runner_deadline_stage(tmp_path):
    runner = _happy_runner()
    worktree_root = tmp_path / "wt"
    out_path = tmp_path / "ab.json"
    rc = perf_gate_ab_runner.main(_base_argv(out_path, worktree_root, tmp_path), runner=runner)
    assert rc == 0

    record = json.loads(out_path.read_text(encoding="utf-8"))
    runner_deadline = record["stages"]["runner_deadline"]
    assert runner_deadline["round_share_floor_seconds"] == perf_gate_ab_runner.GATE_ROUND_SHARE_FLOOR_SECONDS
    assert runner_deadline["partitioned_units"] == 4


# --- a floor-skipped candidate leg with a completed merge_base leg -----------------------


def test_a_floor_skipped_candidate_leg_with_a_completed_merge_base_leg_evaluates_to_inconclusive():
    record = perf_gate_ab_runner.build_ab_record(
        github_run_id="1", github_run_attempt="1", campaign_branch="b", dispatch_index="1",
        mode="null", label=None, rounds=1,
        patch_name=None, patch_sha256=None, patch_magnitude=None, patch_applied=False,
        forced_condition=None,
        declared_candidate_ref=CAND_SHA, declared_merge_base_ref=BASE_SHA,
        declared_candidate_tree_hash="t", declared_merge_base_tree_hash="t",
        candidate_sha=CAND_SHA, merge_base_sha=BASE_SHA,
        candidate_tree_hash="t", merge_base_tree_hash="t",
        candidate_leg={"build": {"success": True}, "benchmarks": {}, "rounds": [], "round_count": 0},
        merge_base_leg={
            "build": {"success": True},
            "benchmarks": {
                "bench1": {
                    "metrics": {
                        "m1": {
                            "tier_candidate": 1, "status": "ok", "reason": None,
                            "samples": [100.0] * 5, "rejected_samples": [], "n_clean": 5,
                            "median": 100.0, "mad": 0.0,
                        },
                    },
                    "measurement_windows": [],
                },
            },
            "rounds": [], "round_count": 1,
        },
        environment={}, timings={}, stages={}, errors=[],
    )
    evaluation = perf_gate_evaluator.evaluate_run(record, _synthetic_baseline())
    assert evaluation["verdict"] == perf_gate_evaluator.VERDICT_INCONCLUSIVE
    assert evaluation["verdict"] != perf_gate_evaluator.VERDICT_FAIL
    assert evaluation["verdict"] != perf_gate_evaluator.VERDICT_PASS


# --- _modules_arg -------------------------------------------------------------------------


def test_modules_arg_rejects_a_path_outside_tests_perf():
    try:
        perf_gate_ab_runner._modules_arg("/etc/passwd")
        raised = False
    except argparse.ArgumentTypeError:
        raised = True
    assert raised


def test_modules_arg_rejects_a_parent_directory_component():
    try:
        perf_gate_ab_runner._modules_arg("tests/perf/../../setup.py")
        raised = False
    except argparse.ArgumentTypeError:
        raised = True
    assert raised


def test_modules_arg_rejects_an_element_beginning_with_a_dash():
    try:
        perf_gate_ab_runner._modules_arg("-p no:cacheprovider")
        raised = False
    except argparse.ArgumentTypeError:
        raised = True
    assert raised


def test_modules_arg_preserves_element_order_and_duplicates():
    value = (
        "tests/perf/test_batcher_combine_perf.py,"
        "tests/perf/test_fifo_perf.py,"
        "tests/perf/test_batcher_combine_perf.py"
    )
    kept = perf_gate_ab_runner._modules_arg(value)
    assert kept.split(",") == value.split(",")


# --- measured module set on every record -------------------------------------------------


def test_build_ab_record_carries_the_measured_module_set_and_the_default_flag():
    record = perf_gate_ab_runner.build_ab_record(
        github_run_id="1", github_run_attempt="1", campaign_branch="b", dispatch_index="1",
        mode="null", label=None, rounds=1,
        patch_name=None, patch_sha256=None, patch_magnitude=None, patch_applied=False,
        forced_condition=None,
        declared_candidate_ref=CAND_SHA, declared_merge_base_ref=BASE_SHA,
        declared_candidate_tree_hash="t", declared_merge_base_tree_hash="t",
        candidate_sha=CAND_SHA, merge_base_sha=BASE_SHA,
        candidate_tree_hash="t", merge_base_tree_hash="t",
        candidate_leg=_minimal_leg(), merge_base_leg=_minimal_leg(),
        environment={}, timings={}, stages={}, errors=[],
        measured_modules=list(perf_gate_ab_runner.perf_harness_runner.DEFAULT_PERF_MODULES),
        measured_modules_is_default=True,
    )
    assert record["run"]["measured_modules"] == list(
        perf_gate_ab_runner.perf_harness_runner.DEFAULT_PERF_MODULES,
    )
    assert record["run"]["measured_modules_is_default"] is True


def test_build_ab_record_narrowed_module_set_is_flagged_not_default():
    record = perf_gate_ab_runner.build_ab_record(
        github_run_id="1", github_run_attempt="1", campaign_branch="b", dispatch_index="1",
        mode="null", label=None, rounds=1,
        patch_name=None, patch_sha256=None, patch_magnitude=None, patch_applied=False,
        forced_condition=None,
        declared_candidate_ref=CAND_SHA, declared_merge_base_ref=BASE_SHA,
        declared_candidate_tree_hash="t", declared_merge_base_tree_hash="t",
        candidate_sha=CAND_SHA, merge_base_sha=BASE_SHA,
        candidate_tree_hash="t", merge_base_tree_hash="t",
        candidate_leg=_minimal_leg(), merge_base_leg=_minimal_leg(),
        environment={}, timings={}, stages={}, errors=[],
        measured_modules=["tests/perf/test_batcher_combine_perf.py"],
        measured_modules_is_default=False,
    )
    assert record["run"]["measured_modules"] == ["tests/perf/test_batcher_combine_perf.py"]
    assert record["run"]["measured_modules_is_default"] is False


def test_main_records_the_narrowed_module_set_it_was_given_in_the_order_given(tmp_path):
    runner = _happy_runner()
    worktree_root = tmp_path / "wt"
    out_path = tmp_path / "ab.json"
    modules_value = "tests/perf/test_fifo_perf.py,tests/perf/test_batcher_combine_perf.py"
    argv = _base_argv(out_path, worktree_root, tmp_path, extra=["--modules", modules_value])
    rc = perf_gate_ab_runner.main(argv, runner=runner)
    assert rc == 0

    record = json.loads(out_path.read_text(encoding="utf-8"))
    assert record["run"]["measured_modules"] == modules_value.split(",")
    assert record["run"]["measured_modules_is_default"] is False

    # Default-set counterpart: no --modules override at all.
    out_path_default = tmp_path / "ab-default.json"
    rc_default = perf_gate_ab_runner.main(
        _base_argv(out_path_default, worktree_root, tmp_path), runner=_happy_runner(),
    )
    assert rc_default == 0
    default_record = json.loads(out_path_default.read_text(encoding="utf-8"))
    assert default_record["run"]["measured_modules"] == list(
        perf_gate_ab_runner.perf_harness_runner.DEFAULT_PERF_MODULES,
    )
    assert default_record["run"]["measured_modules_is_default"] is True


def test_render_summary_markdown_names_the_measured_module_set():
    record = perf_gate_ab_runner.build_ab_record(
        github_run_id="1", github_run_attempt="1", campaign_branch="b", dispatch_index="1",
        mode=perf_gate_ab_runner.MODE_SEEDED, label="seeded-search", rounds=2,
        patch_name="disable-frame-batching.patch", patch_sha256="x", patch_magnitude="200",
        patch_applied=True, forced_condition=None,
        declared_candidate_ref=CAND_SHA, declared_merge_base_ref=BASE_SHA,
        declared_candidate_tree_hash="a", declared_merge_base_tree_hash="b",
        candidate_sha="c", merge_base_sha="d", candidate_tree_hash="a", merge_base_tree_hash="b",
        candidate_leg=_minimal_leg(), merge_base_leg=_minimal_leg(),
        environment={}, timings={}, stages={}, errors=[],
        measured_modules=["tests/perf/test_batcher_combine_perf.py"],
        measured_modules_is_default=False,
    )
    text = perf_gate_ab_runner.render_summary_markdown(record)
    assert "test_batcher_combine_perf.py" in text
    assert perf_gate_ab_runner.render_summary_markdown(record) == text


# --- MODULE_BENCHMARKS / modules_for_benchmarks ---------------------------------------


def test_module_benchmarks_union_equals_all_benchmarks():
    perf_tier_registry = importlib.import_module("perf_tier_registry")
    union = set().union(*[set(v) for v in perf_gate_ab_runner.MODULE_BENCHMARKS.values()])
    assert union == set(perf_tier_registry.ALL_BENCHMARKS)


def test_module_benchmarks_keys_are_a_subset_of_default_perf_modules():
    perf_harness_runner = importlib.import_module("perf_harness_runner")
    assert set(perf_gate_ab_runner.MODULE_BENCHMARKS) <= set(perf_harness_runner.DEFAULT_PERF_MODULES)


def test_modules_for_benchmarks_empty_input_returns_empty_tuple():
    assert perf_gate_ab_runner.modules_for_benchmarks(()) == ()


def test_modules_for_benchmarks_single_known_benchmark():
    assert perf_gate_ab_runner.modules_for_benchmarks(("fifo_perf",)) == ("tests/perf/test_fifo_perf.py",)


def test_modules_for_benchmarks_two_identities_from_one_module_deduplicate_to_one_module():
    result = perf_gate_ab_runner.modules_for_benchmarks(
        ("udp_packetizer_perf_v1_std", "udp_packetizer_perf_v2_jumbo"),
    )
    assert result == ("tests/perf/test_udp_packetizer_perf.py",)


def test_modules_for_benchmarks_unknown_identity_returns_no_module_rather_than_raising():
    assert perf_gate_ab_runner.modules_for_benchmarks(("nope",)) == ()


def test_modules_for_benchmarks_preserves_default_perf_modules_order():
    perf_harness_runner = importlib.import_module("perf_harness_runner")
    all_benchmarks = set().union(*[set(v) for v in perf_gate_ab_runner.MODULE_BENCHMARKS.values()])
    result = perf_gate_ab_runner.modules_for_benchmarks(all_benchmarks)
    assert result == perf_harness_runner.DEFAULT_PERF_MODULES


def test_validate_module_benchmarks_raises_named_error_on_an_incomplete_map(monkeypatch):
    incomplete = dict(perf_gate_ab_runner.MODULE_BENCHMARKS)
    del incomplete["tests/perf/test_fifo_perf.py"]
    try:
        perf_gate_ab_runner._validate_module_benchmarks(incomplete)
        raised = False
    except perf_gate_ab_runner.ModuleBenchmarkMapError:
        raised = True
    assert raised


def test_validate_module_benchmarks_raises_named_error_on_an_unknown_module_key():
    invalid = dict(perf_gate_ab_runner.MODULE_BENCHMARKS)
    invalid["tests/perf/test_not_a_real_module.py"] = ("fifo_perf",)
    try:
        perf_gate_ab_runner._validate_module_benchmarks(invalid)
        raised = False
    except perf_gate_ab_runner.ModuleBenchmarkMapError:
        raised = True
    assert raised


def test_validate_module_benchmarks_accepts_the_real_module_benchmarks_map():
    # Should not raise: this is exactly what import time already validated.
    perf_gate_ab_runner._validate_module_benchmarks(perf_gate_ab_runner.MODULE_BENCHMARKS)


# --- the single in-job retry: decision, execution, and merge ---------------------------


def _fifo_baseline_path(tmp_path):
    baseline_path = tmp_path / "baseline.json"
    baseline_path.write_text(json.dumps({
        "cells": {"fifo_perf": {"m1": {"gate_rule": "exact-equality", "observed_value": 100.0}}},
    }), encoding="utf-8")
    return baseline_path


def test_pass_first_attempt_yields_one_attempt_and_retry_stage_records_it_did_not_run(tmp_path):
    baseline_path = _fifo_baseline_path(tmp_path)
    runner = _ScriptedRunner(default=_completed([], returncode=0))
    runner.when(
        _argv_contains("perf_harness_runner.py"),
        _write_measurement_record(benchmark="fifo_perf", metric="m1", value=100.0),
    )
    out_path = tmp_path / "ab.json"
    worktree_root = tmp_path / "wt"
    argv = _base_argv(out_path, worktree_root, tmp_path, extra=["--baseline", str(baseline_path)])
    rc = perf_gate_ab_runner.main(argv, runner=runner)
    assert rc == 0

    record = json.loads(out_path.read_text(encoding="utf-8"))
    attempts = record["run"]["attempts"]
    assert len(attempts) == 1
    assert attempts[0]["verdict"] == perf_gate_evaluator.VERDICT_PASS
    assert attempts[0]["retried"] is False
    assert record["run"]["final_verdict"] == perf_gate_evaluator.VERDICT_PASS
    gate_retry = record["stages"]["gate_retry"]
    assert gate_retry["ran"] is False
    assert perf_gate_evaluator.VERDICT_PASS in gate_retry["reason"]


def test_fail_first_attempt_yields_one_attempt(tmp_path):
    baseline_path = _fifo_baseline_path(tmp_path)
    worktree_root = tmp_path / "wt"
    candidate_worktree = str(worktree_root / "candidate")
    merge_base_worktree = str(worktree_root / "merge_base")

    runner = _ScriptedRunner(default=_completed([], returncode=0))
    runner.when(
        _all(_argv_contains("perf_harness_runner.py"), _cwd_is(candidate_worktree)),
        _write_measurement_record(benchmark="fifo_perf", metric="m1", value=101.0),
    )
    runner.when(
        _all(_argv_contains("perf_harness_runner.py"), _cwd_is(merge_base_worktree)),
        _write_measurement_record(benchmark="fifo_perf", metric="m1", value=100.0),
    )
    out_path = tmp_path / "ab.json"
    argv = _base_argv(out_path, worktree_root, tmp_path, extra=["--baseline", str(baseline_path)])
    rc = perf_gate_ab_runner.main(argv, runner=runner)
    assert rc == 0

    record = json.loads(out_path.read_text(encoding="utf-8"))
    attempts = record["run"]["attempts"]
    assert len(attempts) == 1
    assert attempts[0]["verdict"] == perf_gate_evaluator.VERDICT_FAIL
    assert record["run"]["final_verdict"] == perf_gate_evaluator.VERDICT_FAIL


def test_structural_only_inconclusive_first_attempt_yields_one_attempt_with_structural_reason(tmp_path):
    baseline_path = tmp_path / "baseline.json"
    baseline_path.write_text(json.dumps({
        "cells": {"bench1": {"m1": {"gate_rule": "exact-equality", "observed_value": 100.0}}},
    }), encoding="utf-8")
    runner = _happy_runner()
    out_path = tmp_path / "ab.json"
    worktree_root = tmp_path / "wt"
    argv = _base_argv(
        out_path, worktree_root, tmp_path,
        extra=["--baseline", str(baseline_path), "--forced-condition", "tree-hash-pair-mismatch"],
    )
    rc = perf_gate_ab_runner.main(argv, runner=runner)
    assert rc == 0

    record = json.loads(out_path.read_text(encoding="utf-8"))
    attempts = record["run"]["attempts"]
    assert len(attempts) == 1
    assert attempts[0]["verdict"] == perf_gate_evaluator.VERDICT_INCONCLUSIVE
    gate_retry = record["stages"]["gate_retry"]
    assert gate_retry["ran"] is False
    assert perf_gate_evaluator.REASON_TREE_HASH_PAIR_MISMATCH in gate_retry["reason"]


def test_retry_eligible_inconclusive_first_attempt_yields_two_attempts_and_narrows_to_affected_module(tmp_path):
    baseline_path = _fifo_baseline_path(tmp_path)
    worktree_root = tmp_path / "wt"
    candidate_worktree = str(worktree_root / "candidate")
    merge_base_worktree = str(worktree_root / "merge_base")

    runner = _ScriptedRunner(default=_completed([], returncode=0))
    # merge_base always measures fifo_perf/m1 = 100.0, both the first pass and the retry.
    runner.when(
        _all(_argv_contains("perf_harness_runner.py"), _cwd_is(merge_base_worktree)),
        _write_measurement_record(benchmark="fifo_perf", metric="m1", value=100.0),
    )
    # candidate's first pass (the full, comma-joined default module set) produces no
    # benchmark at all; candidate's retry (the narrowed, comma-free single-module set)
    # produces fifo_perf/m1 = 100.0.
    runner.when(
        _all(_argv_contains("perf_harness_runner.py"), _cwd_is(candidate_worktree), _modules_arg_has_comma),
        _write_well_formed_but_internally_failed_record(),
    )
    runner.when(
        _all(_argv_contains("perf_harness_runner.py"), _cwd_is(candidate_worktree), _modules_arg_has_no_comma),
        _write_measurement_record(benchmark="fifo_perf", metric="m1", value=100.0),
    )

    out_path = tmp_path / "ab.json"
    argv = _base_argv(out_path, worktree_root, tmp_path, extra=["--baseline", str(baseline_path)])
    rc = perf_gate_ab_runner.main(argv, runner=runner)
    assert rc == 0

    record = json.loads(out_path.read_text(encoding="utf-8"))
    attempts = record["run"]["attempts"]
    assert len(attempts) == 2
    assert attempts[0]["retried"] is True
    assert attempts[1]["retried"] is False
    assert record["run"]["final_verdict"] == perf_gate_evaluator.VERDICT_PASS

    gate_retry = record["stages"]["gate_retry"]
    assert gate_retry["ran"] is True
    assert gate_retry["affected_benchmarks"] == ["fifo_perf"]
    assert gate_retry["modules"] == ["tests/perf/test_fifo_perf.py"]

    # the retry issued exactly two measurement invocations: candidate then merge base, each
    # narrowed to the single module that emits the affected benchmark.
    retry_calls = [
        call for call in runner.calls
        if any("perf_harness_runner.py" in p for p in call["argv"]) and _modules_arg_has_no_comma(call["argv"], call["cwd"])
    ]
    assert len(retry_calls) == 2
    assert retry_calls[0]["cwd"] == candidate_worktree
    assert retry_calls[1]["cwd"] == merge_base_worktree
    assert _modules_arg_value(retry_calls[0]["argv"]) == "tests/perf/test_fifo_perf.py"
    assert _modules_arg_value(retry_calls[1]["argv"]) == "tests/perf/test_fifo_perf.py"

    # the retry started no worktree-add and no build invocation.
    retry_calls_and_around = [
        call for call in runner.calls
        if _modules_arg_value(call["argv"]) is not None and not _modules_arg_has_comma(call["argv"], call["cwd"])
    ]
    assert all("perf_harness_runner.py" in " ".join(call["argv"]) for call in retry_calls_and_around)
    assert not any("worktree" in call["argv"] and "add" in call["argv"] for call in retry_calls_and_around)

    # every round record from both attempts remains on each leg's own rounds list.
    assert len(record["legs"]["candidate"]["rounds"]) == 3  # 2 first-pass rounds + 1 retry round
    assert len(record["legs"]["merge_base"]["rounds"]) == 3

    # both worktrees were removed.
    remove_calls = [" ".join(call["argv"]) for call in runner.calls if "remove" in call["argv"]]
    assert any(candidate_worktree in line for line in remove_calls)
    assert any(merge_base_worktree in line for line in remove_calls)

    # re-evaluating the written record against the same baseline reproduces the final verdict.
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    reevaluation = perf_gate_evaluator.evaluate_run(record, baseline)
    assert reevaluation["verdict"] == record["run"]["final_verdict"]


def test_round_count_after_a_successful_retry_equals_the_successful_round_tally(tmp_path):
    baseline_path = _fifo_baseline_path(tmp_path)
    worktree_root = tmp_path / "wt"
    candidate_worktree = str(worktree_root / "candidate")
    merge_base_worktree = str(worktree_root / "merge_base")

    runner = _ScriptedRunner(default=_completed([], returncode=0))
    # merge_base always measures fifo_perf/m1 = 100.0, both the first pass and the retry.
    runner.when(
        _all(_argv_contains("perf_harness_runner.py"), _cwd_is(merge_base_worktree)),
        _write_measurement_record(benchmark="fifo_perf", metric="m1", value=100.0),
    )
    # candidate's first pass fails internally on both rounds; candidate's retry succeeds.
    runner.when(
        _all(_argv_contains("perf_harness_runner.py"), _cwd_is(candidate_worktree), _modules_arg_has_comma),
        _write_well_formed_but_internally_failed_record(),
    )
    runner.when(
        _all(_argv_contains("perf_harness_runner.py"), _cwd_is(candidate_worktree), _modules_arg_has_no_comma),
        _write_measurement_record(benchmark="fifo_perf", metric="m1", value=100.0),
    )

    out_path = tmp_path / "ab.json"
    argv = _base_argv(out_path, worktree_root, tmp_path, extra=["--baseline", str(baseline_path)])
    rc = perf_gate_ab_runner.main(argv, runner=runner)
    assert rc == 0

    record = json.loads(out_path.read_text(encoding="utf-8"))
    attempts = record["run"]["attempts"]
    assert len(attempts) == 2

    # each leg's recorded round_count equals that same leg's own successful-round tally,
    # taken with the module's own success predicate over the rounds list beside it.
    pre_retry_completed = {}
    for leg_name in ("candidate", "merge_base"):
        leg = record["legs"][leg_name]
        pre_retry_completed[leg_name] = sum(
            1 for r in leg["rounds"][:-1] if perf_gate_ab_runner._is_successful_round(r)
        )
        successful_tally = sum(1 for r in leg["rounds"] if perf_gate_ab_runner._is_successful_round(r))
        assert leg["round_count"] == successful_tally

    # the recomputation must actually have run: a stale pre-retry value cannot satisfy this.
    assert record["legs"]["candidate"]["round_count"] > pre_retry_completed["candidate"]
    assert record["legs"]["merge_base"]["round_count"] > pre_retry_completed["merge_base"]

    # the second attempt's own record was not broken by this change.
    second_attempt = attempts[1]
    assert second_attempt["retried"] is False
    assert second_attempt["verdict"] == perf_gate_evaluator.VERDICT_PASS
    assert second_attempt["gating_cell_count"] == 1


def test_retry_replaces_rather_than_appends_and_leaves_an_unaffected_benchmark_unchanged(tmp_path):
    baseline_path = tmp_path / "baseline.json"
    baseline_path.write_text(json.dumps({
        "cells": {
            "fifo_perf": {"m1": {"gate_rule": "exact-equality", "observed_value": 100.0}},
            "stream_bridge_perf": {"m1": {"gate_rule": "exact-equality", "observed_value": 50.0}},
        },
    }), encoding="utf-8")
    worktree_root = tmp_path / "wt"
    candidate_worktree = str(worktree_root / "candidate")
    merge_base_worktree = str(worktree_root / "merge_base")

    def _first_pass_candidate(argv, cwd):
        # Candidate's first pass measures both benchmarks: fifo_perf is unstable
        # (within-run-nondeterminism, retry-eligible), stream_bridge_perf is clean and
        # matches the baseline (PASS on that cell, so it must stay untouched by the retry).
        out_path = None
        for index, part in enumerate(argv):
            if part == "--out" and index + 1 < len(argv):
                out_path = Path(argv[index + 1])
                break
        record = {
            "harness_run_schema_version": 1,
            "run": {"git_sha": "deadbeef"},
            "environment": {"cpu_model": "fake"},
            "build": {},
            "benchmarks": {
                "fifo_perf": {
                    "metrics": {"m1": {
                        "tier_candidate": 1, "status": "ok", "reason": None,
                        "samples": [100.0, 101.0], "rejected_samples": [], "n_clean": 2,
                    }},
                    "measurement_windows": [],
                },
                "stream_bridge_perf": {
                    "metrics": {"m1": {
                        "tier_candidate": 1, "status": "ok", "reason": None,
                        "samples": [50.0] * 5, "rejected_samples": [], "n_clean": 5,
                        "median": 50.0, "mad": 0.0,
                    }},
                    "measurement_windows": [],
                },
            },
            "stages": {"measurement": {"status": "ok"}},
            "errors": [],
        }
        if out_path is not None:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(json.dumps(record), encoding="utf-8")
        return _completed(argv, returncode=0)

    def _retry_candidate(argv, cwd):
        return _write_measurement_record(benchmark="fifo_perf", metric="m1", value=100.0)(argv, cwd)

    def _first_pass_merge_base(argv, cwd):
        # merge_base's first pass measures both benchmarks too, matching candidate's clean
        # stream_bridge_perf value so that cell is a genuine PASS, never affected.
        out_path = None
        for index, part in enumerate(argv):
            if part == "--out" and index + 1 < len(argv):
                out_path = Path(argv[index + 1])
                break
        record = {
            "harness_run_schema_version": 1,
            "run": {"git_sha": "deadbeef"},
            "environment": {"cpu_model": "fake"},
            "build": {},
            "benchmarks": {
                "fifo_perf": {
                    "metrics": {"m1": {
                        "tier_candidate": 1, "status": "ok", "reason": None,
                        "samples": [100.0] * 5, "rejected_samples": [], "n_clean": 5,
                        "median": 100.0, "mad": 0.0,
                    }},
                    "measurement_windows": [],
                },
                "stream_bridge_perf": {
                    "metrics": {"m1": {
                        "tier_candidate": 1, "status": "ok", "reason": None,
                        "samples": [50.0] * 5, "rejected_samples": [], "n_clean": 5,
                        "median": 50.0, "mad": 0.0,
                    }},
                    "measurement_windows": [],
                },
            },
            "stages": {"measurement": {"status": "ok"}},
            "errors": [],
        }
        if out_path is not None:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(json.dumps(record), encoding="utf-8")
        return _completed(argv, returncode=0)

    runner = _ScriptedRunner(default=_completed([], returncode=0))
    runner.when(
        _all(_argv_contains("perf_harness_runner.py"), _cwd_is(merge_base_worktree), _modules_arg_has_comma),
        _first_pass_merge_base,
    )
    runner.when(
        _all(_argv_contains("perf_harness_runner.py"), _cwd_is(merge_base_worktree), _modules_arg_has_no_comma),
        _write_measurement_record(benchmark="fifo_perf", metric="m1", value=100.0),
    )
    runner.when(
        _all(_argv_contains("perf_harness_runner.py"), _cwd_is(candidate_worktree), _modules_arg_has_comma),
        _first_pass_candidate,
    )
    runner.when(
        _all(_argv_contains("perf_harness_runner.py"), _cwd_is(candidate_worktree), _modules_arg_has_no_comma),
        _retry_candidate,
    )

    out_path = tmp_path / "ab.json"
    argv = _base_argv(out_path, worktree_root, tmp_path, extra=["--baseline", str(baseline_path)])
    rc = perf_gate_ab_runner.main(argv, runner=runner)
    assert rc == 0

    record = json.loads(out_path.read_text(encoding="utf-8"))
    gate_retry = record["stages"]["gate_retry"]
    assert gate_retry["ran"] is True
    assert gate_retry["affected_benchmarks"] == ["fifo_perf"]

    candidate_benchmarks = record["legs"]["candidate"]["benchmarks"]
    # fifo_perf's post-retry samples equal the retry round's samples alone (5 clean samples
    # of 100.0), never the first attempt's unstable [100.0, 101.0] samples concatenated in.
    assert candidate_benchmarks["fifo_perf"]["metrics"]["m1"]["samples"] == [100.0] * 5
    # stream_bridge_perf was not an affected benchmark: its first-attempt entry is untouched
    # (2 default rounds x 5 samples each, concatenated exactly as the first pass produced it).
    assert candidate_benchmarks["stream_bridge_perf"]["metrics"]["m1"]["samples"] == [50.0] * 10


def test_second_inconclusive_after_retry_still_yields_exactly_two_attempts(tmp_path):
    baseline_path = _fifo_baseline_path(tmp_path)
    worktree_root = tmp_path / "wt"
    candidate_worktree = str(worktree_root / "candidate")
    merge_base_worktree = str(worktree_root / "merge_base")

    runner = _ScriptedRunner(default=_completed([], returncode=0))
    runner.when(
        _all(_argv_contains("perf_harness_runner.py"), _cwd_is(merge_base_worktree)),
        _write_measurement_record(benchmark="fifo_perf", metric="m1", value=100.0),
    )
    # candidate never produces fifo_perf, in the first pass or the retry.
    runner.when(
        _all(_argv_contains("perf_harness_runner.py"), _cwd_is(candidate_worktree)),
        _write_well_formed_but_internally_failed_record(),
    )

    out_path = tmp_path / "ab.json"
    argv = _base_argv(out_path, worktree_root, tmp_path, extra=["--baseline", str(baseline_path)])
    rc = perf_gate_ab_runner.main(argv, runner=runner)
    assert rc == 0

    record = json.loads(out_path.read_text(encoding="utf-8"))
    attempts = record["run"]["attempts"]
    assert len(attempts) == 2
    assert attempts[1]["verdict"] == perf_gate_evaluator.VERDICT_INCONCLUSIVE
    assert record["run"]["final_verdict"] == perf_gate_evaluator.VERDICT_INCONCLUSIVE

    # the retry ran exactly once: exactly two measurement invocations with the narrowed,
    # comma-free module argument (never a second retry pass).
    retry_calls = [
        call for call in runner.calls
        if any("perf_harness_runner.py" in p for p in call["argv"]) and _modules_arg_has_no_comma(call["argv"], call["cwd"])
    ]
    assert len(retry_calls) == 2


def test_retry_round_below_floor_is_skipped_and_still_yields_two_attempts_with_no_subprocess(tmp_path):
    baseline_path = _fifo_baseline_path(tmp_path)
    runner = _happy_runner()
    worktree_root = tmp_path / "wt"
    out_path = tmp_path / "ab.json"
    # A deadline smaller than GATE_ROUND_SHARE_FLOOR_SECONDS: every partitioned round share,
    # in the main loop and in the retry, falls below the floor regardless of how many units
    # remain, so no measurement subprocess is ever started.
    small_deadline = perf_gate_ab_runner.GATE_ROUND_SHARE_FLOOR_SECONDS - 10
    argv = _base_argv(
        out_path, worktree_root, tmp_path,
        extra=["--baseline", str(baseline_path), "--deadline-seconds", str(small_deadline)],
    )
    rc = perf_gate_ab_runner.main(argv, runner=runner)
    assert rc == 0

    measurement_calls = [call for call in runner.calls if any("perf_harness_runner.py" in p for p in call["argv"])]
    assert measurement_calls == []

    record = json.loads(out_path.read_text(encoding="utf-8"))
    assert len(record["run"]["attempts"]) == 2
    gate_retry = record["stages"]["gate_retry"]
    assert gate_retry["ran"] is True
    assert gate_retry["modules"] == ["tests/perf/test_fifo_perf.py"]


def test_both_worktrees_removed_when_the_retry_ran(tmp_path):
    baseline_path = _fifo_baseline_path(tmp_path)
    worktree_root = tmp_path / "wt"
    candidate_worktree = str(worktree_root / "candidate")
    merge_base_worktree = str(worktree_root / "merge_base")

    runner = _ScriptedRunner(default=_completed([], returncode=0))
    runner.when(
        _all(_argv_contains("perf_harness_runner.py"), _cwd_is(merge_base_worktree)),
        _write_measurement_record(benchmark="fifo_perf", metric="m1", value=100.0),
    )
    runner.when(
        _all(_argv_contains("perf_harness_runner.py"), _cwd_is(candidate_worktree), _modules_arg_has_comma),
        _write_well_formed_but_internally_failed_record(),
    )
    runner.when(
        _all(_argv_contains("perf_harness_runner.py"), _cwd_is(candidate_worktree), _modules_arg_has_no_comma),
        _write_measurement_record(benchmark="fifo_perf", metric="m1", value=100.0),
    )

    out_path = tmp_path / "ab.json"
    argv = _base_argv(out_path, worktree_root, tmp_path, extra=["--baseline", str(baseline_path)])
    rc = perf_gate_ab_runner.main(argv, runner=runner)
    assert rc == 0

    remove_calls = [" ".join(call["argv"]) for call in runner.calls if "remove" in call["argv"]]
    assert any(candidate_worktree in line for line in remove_calls)
    assert any(merge_base_worktree in line for line in remove_calls)


def test_no_retry_flag_suppresses_retry_even_when_retry_eligible(tmp_path):
    baseline_path = _fifo_baseline_path(tmp_path)
    worktree_root = tmp_path / "wt"
    candidate_worktree = str(worktree_root / "candidate")
    merge_base_worktree = str(worktree_root / "merge_base")

    runner = _ScriptedRunner(default=_completed([], returncode=0))
    runner.when(
        _all(_argv_contains("perf_harness_runner.py"), _cwd_is(candidate_worktree)),
        _write_well_formed_but_internally_failed_record(),
    )
    runner.when(
        _all(_argv_contains("perf_harness_runner.py"), _cwd_is(merge_base_worktree)),
        _write_measurement_record(benchmark="fifo_perf", metric="m1", value=100.0),
    )

    out_path = tmp_path / "ab.json"
    argv = _base_argv(
        out_path, worktree_root, tmp_path,
        extra=["--baseline", str(baseline_path), "--no-retry"],
    )
    rc = perf_gate_ab_runner.main(argv, runner=runner)
    assert rc == 0

    record = json.loads(out_path.read_text(encoding="utf-8"))
    assert len(record["run"]["attempts"]) == 1
    gate_retry = record["stages"]["gate_retry"]
    assert gate_retry["ran"] is False
    assert gate_retry["no_retry_flag"] is True
    assert "no-retry" in gate_retry["reason"]


def test_build_ab_record_and_render_summary_markdown_carry_the_new_retry_fields():
    record = perf_gate_ab_runner.build_ab_record(
        github_run_id="1", github_run_attempt="1", campaign_branch="b", dispatch_index="1",
        mode="null", label=None, rounds=1,
        patch_name=None, patch_sha256=None, patch_magnitude=None, patch_applied=False,
        forced_condition=None,
        declared_candidate_ref=CAND_SHA, declared_merge_base_ref=BASE_SHA,
        declared_candidate_tree_hash="t", declared_merge_base_tree_hash="t",
        candidate_sha=CAND_SHA, merge_base_sha=BASE_SHA,
        candidate_tree_hash="t", merge_base_tree_hash="t",
        candidate_leg=_minimal_leg(), merge_base_leg=_minimal_leg(),
        environment={}, timings={}, stages={}, errors=[],
        attempts=[{"attempt": 1, "verdict": "PASS"}],
        final_verdict="PASS",
        merge_base_source="pull_request_base_sha",
        cold_cache=True,
        cold_cache_reason="candidate leg's ccache hit rate was zero",
    )
    assert record["run"]["attempts"] == [{"attempt": 1, "verdict": "PASS"}]
    assert record["run"]["final_verdict"] == "PASS"
    assert record["run"]["merge_base_source"] == "pull_request_base_sha"
    assert record["run"]["cold_cache"] is True
    assert record["run"]["cold_cache_reason"] == "candidate leg's ccache hit rate was zero"

    text = perf_gate_ab_runner.render_summary_markdown(record)
    assert "Attempts: 1" in text
    assert "Final verdict: PASS" in text
    assert "Merge-base source: pull_request_base_sha" in text
    assert "Cold cache: True" in text


def test_build_ab_record_defaults_attempts_to_empty_list_and_final_verdict_to_none():
    record = perf_gate_ab_runner.build_ab_record(
        github_run_id="1", github_run_attempt="1", campaign_branch="b", dispatch_index="1",
        mode="null", label=None, rounds=1,
        patch_name=None, patch_sha256=None, patch_magnitude=None, patch_applied=False,
        forced_condition=None,
        declared_candidate_ref=CAND_SHA, declared_merge_base_ref=BASE_SHA,
        declared_candidate_tree_hash="t", declared_merge_base_tree_hash="t",
        candidate_sha=CAND_SHA, merge_base_sha=BASE_SHA,
        candidate_tree_hash="t", merge_base_tree_hash="t",
        candidate_leg=_minimal_leg(), merge_base_leg=_minimal_leg(),
        environment={}, timings={}, stages={}, errors=[],
    )
    assert record["run"]["attempts"] == []
    assert record["run"]["final_verdict"] is None
    assert record["run"]["merge_base_source"] is None
    assert record["run"]["cold_cache"] is None
    assert record["run"]["cold_cache_reason"] is None


# --- workflow smoke: the exact flag spellings .github/workflows/perf_gate.yml uses -----


def test_workflow_flag_spellings_smoke_invocation_exits_zero(tmp_path):
    """Builds its argv from the same flag spellings the paired-run step in
    .github/workflows/perf_gate.yml uses (--baseline, --merge-base-source, plus the
    existing --deadline-seconds/--round-share-floor-seconds/--hang-diagnostics-* flags),
    driven entirely through the scripted runner. A local end-to-end smoke proof that the
    workflow's own argv shape is accepted and exits 0."""
    runner = _happy_runner()
    worktree_root = tmp_path / "wt"
    out_path = tmp_path / "ab.json"
    hang_diagnostics_dir = tmp_path / "hang-diagnostics"
    argv = [
        "--out", str(out_path),
        "--candidate-ref", CAND_SHA,
        "--merge-base-ref", BASE_SHA,
        "--mode", "null",
        "--label", "perf-gate",
        "--rounds", "2",
        "--worktree-root", str(worktree_root),
        "--repo-root", str(tmp_path),
        "--baseline", str(tmp_path / "no-such-baseline.json"),
        "--merge-base-source", "pull_request_base_sha",
        "--deadline-seconds", "1260",
        "--round-share-floor-seconds", "180",
        "--hang-diagnostics-dir", str(hang_diagnostics_dir),
        "--hang-diagnostics-lead-seconds", "60",
        "--print-summary",
    ]
    rc = perf_gate_ab_runner.main(argv, runner=runner)
    assert rc == 0

    record = json.loads(out_path.read_text(encoding="utf-8"))
    assert record["run"]["merge_base_source"] == "pull_request_base_sha"
    assert len(record["run"]["attempts"]) == 1


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
# ----------------------------------------------------------------------------
