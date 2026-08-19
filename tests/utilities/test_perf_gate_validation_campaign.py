# ----------------------------------------------------------------------------
# Title      : Perf Gate Validation Campaign Driver Tests
# ----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
# ----------------------------------------------------------------------------

"""Unit tests for scripts/perf_gate_validation_campaign.py, following
tests/utilities/test_perf_harness_campaign.py's injection style: every `gh`
invocation goes through a scripted fake and every artifact download goes
through a fake downloader that materializes the known subpath, so nothing
here touches the network or a real CLI binary.
"""

from __future__ import annotations

import importlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

perf_gate_validation_campaign = importlib.import_module("perf_gate_validation_campaign")


def _completed(argv, returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(argv, returncode=returncode, stdout=stdout, stderr=stderr)


class _ScriptedGateRunner:
    """Injectable subprocess runner returning canned CompletedProcess objects
    keyed off a predicate over the argv, in registration order. Every
    invocation is recorded in `calls`, with no real `gh` binary and no
    network access. Named distinctly from
    test_perf_harness_campaign.py's own `_ScriptedRunner` so a reader
    comparing the two files sees the same shape under a module-specific
    name.
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


def _run_list_entry(database_id, head_branch, created_at, **overrides):
    entry = {
        "databaseId": database_id,
        "headBranch": head_branch,
        "createdAt": created_at,
        "conclusion": "success",
        "event": "workflow_dispatch",
        "headSha": "deadbeef",
        "name": "Rogue Perf Gate Validation",
        "status": "completed",
        "updatedAt": created_at,
        "url": f"https://example.invalid/runs/{database_id}",
        "workflowDatabaseId": 1,
    }
    entry.update(overrides)
    return entry


def _run_list_runner(entries, **extra_rules):
    runner = _ScriptedGateRunner().when(
        _contains("list"),
        _completed(["gh", "run", "list"], returncode=0, stdout=json.dumps(entries)),
    )
    for predicate, completed in extra_rules.items():
        runner.when(predicate, completed)
    return runner


_FULL_SHA = "a" * 40
_OTHER_SHA = "b" * 40


def _gate_ab_record(
    *, run_id="401", label="null-population", mode="null", cpu_model="AMD EPYC 7763",
    declared_candidate_tree_hash="tree-a", declared_merge_base_tree_hash="tree-a",
    candidate_tree_hash="tree-a", merge_base_tree_hash="tree-a",
    patch_applied=False, patch_name=None, forced_condition=None,
):
    return {
        "gate_ab_schema_version": 1,
        "run": {
            "github_run_id": run_id,
            "label": label,
            "mode": mode,
            "patch_applied": patch_applied,
            "patch_name": patch_name,
            "forced_condition": forced_condition,
            "declared_candidate_tree_hash": declared_candidate_tree_hash,
            "declared_merge_base_tree_hash": declared_merge_base_tree_hash,
            "candidate_tree_hash": candidate_tree_hash,
            "merge_base_tree_hash": merge_base_tree_hash,
            "tree_hash_pair_match": True,
        },
        "environment": {"cpu_model": cpu_model},
        "legs": {}, "timings": {}, "stages": {}, "errors": [],
    }


def _write_gate_record(path, record):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record), encoding="utf-8")


def _fake_downloader_for(record_factory):
    """A downloader that materializes GATE_RECORD_DIRNAME/GATE_RECORD_FILENAME
    (and a verdict sidecar) under a fresh scratch directory, exactly the
    known subpath the real workflow's artifact carries, so
    _find_gate_record_files' glob finds it with no network call ever
    happening."""
    def downloader(repo, run_id, runner):
        root = Path(tempfile.mkdtemp(prefix="test-perf-gate-validation-campaign-"))
        results_dir = root / perf_gate_validation_campaign.GATE_RECORD_DIRNAME
        results_dir.mkdir(parents=True, exist_ok=True)
        record = record_factory(run_id)
        (results_dir / perf_gate_validation_campaign.GATE_RECORD_FILENAME).write_text(
            json.dumps(record), encoding="utf-8",
        )
        (results_dir / perf_gate_validation_campaign.VERDICT_RECORD_FILENAME).write_text(
            json.dumps({"verdict": "PASS"}), encoding="utf-8",
        )
        return root
    return downloader


# ---------------------------------------------------------------------------
# Module constants
# ---------------------------------------------------------------------------

def test_default_run_cap_exceeds_the_dispatch_target_with_recorded_margin():
    C = perf_gate_validation_campaign
    assert C.DEFAULT_DISPATCH_TARGET == 20
    assert C.DEFAULT_RUN_CAP > C.DEFAULT_DISPATCH_TARGET


def test_default_branch_points_at_the_ccache_basedir_fixed_branch():
    assert perf_gate_validation_campaign.DEFAULT_BRANCH == "perf-gate/validation-v2"


# ---------------------------------------------------------------------------
# _validate_dispatch_inputs
# ---------------------------------------------------------------------------

def test_validate_dispatch_inputs_rejects_a_ref_that_is_not_a_full_forty_character_sha():
    C = perf_gate_validation_campaign
    error = C._validate_dispatch_inputs("not-a-sha", _FULL_SHA, "null", C.LABEL_NULL)
    assert error is not None
    assert "candidate_ref" in error


def test_validate_dispatch_inputs_rejects_a_mode_outside_the_declared_set():
    C = perf_gate_validation_campaign
    error = C._validate_dispatch_inputs(_FULL_SHA, _FULL_SHA, "not-a-mode", C.LABEL_NULL)
    assert error is not None
    assert "mode" in error


def test_validate_dispatch_inputs_rejects_a_label_outside_the_declared_set():
    C = perf_gate_validation_campaign
    error = C._validate_dispatch_inputs(_FULL_SHA, _FULL_SHA, "null", "not-a-label")
    assert error is not None
    assert "label" in error


def test_validate_dispatch_inputs_accepts_every_valid_combination():
    C = perf_gate_validation_campaign
    assert C._validate_dispatch_inputs(_FULL_SHA, _OTHER_SHA, "null", C.LABEL_NULL) is None


def test_dispatch_one_never_runs_a_subprocess_when_validation_rejects_the_inputs():
    C = perf_gate_validation_campaign
    runner = _ScriptedGateRunner()

    result = C._dispatch_one(
        repo="ruck314/rogue", branch=C.DEFAULT_BRANCH, workflow=C.DEFAULT_WORKFLOW,
        candidate_ref="not-a-sha", merge_base_ref=_FULL_SHA, mode="null",
        patch_name=None, patch_magnitude=None, forced_condition=None,
        rounds=2, label=C.LABEL_NULL,
        runner=runner, sleep_fn=lambda seconds: None, epoch_fn=lambda: 0.0, interval_seconds=0,
    )

    assert runner.calls == []
    assert result["dispatch_exit_code"] != 0


def test_the_driver_validates_a_module_value_with_the_runners_own_compiled_pattern(monkeypatch):
    import re

    import perf_gate_ab_runner as R

    C = perf_gate_validation_campaign
    value = "tests/perf/test_something_unusual.py"

    assert C._validate_dispatch_inputs(_FULL_SHA, _OTHER_SHA, "null", C.LABEL_NULL, modules=value) is None

    monkeypatch.setattr(R, "PERF_MODULE_PATTERN", re.compile(r"^never-matches$"))
    error = C._validate_dispatch_inputs(_FULL_SHA, _OTHER_SHA, "null", C.LABEL_NULL, modules=value)
    assert error is not None and "modules" in error


def test_dispatch_one_passes_the_default_module_set_input_when_none_is_given():
    C = perf_gate_validation_campaign
    entries = [_run_list_entry(910, C.DEFAULT_BRANCH, "2026-08-16T10:00:00Z")]
    runner = _run_list_runner(entries)

    result = C._dispatch_one(
        repo="ruck314/rogue", branch=C.DEFAULT_BRANCH, workflow=C.DEFAULT_WORKFLOW,
        candidate_ref=_FULL_SHA, merge_base_ref=_OTHER_SHA, mode="null",
        patch_name=None, patch_magnitude=None, forced_condition=None,
        rounds=2, label=C.LABEL_NULL,
        runner=runner, sleep_fn=lambda seconds: None, epoch_fn=lambda: 0.0, interval_seconds=0,
    )

    dispatch_calls = [call for call in runner.calls if "workflow" in call and "run" in call]
    assert len(dispatch_calls) == 1
    assert f"modules={C.MODULES_INPUT_ALL}" in dispatch_calls[0]
    assert result["dispatch_exit_code"] == 0


def test_dispatch_one_passes_a_narrowed_module_set_as_a_named_input():
    C = perf_gate_validation_campaign
    entries = [_run_list_entry(911, C.DEFAULT_BRANCH, "2026-08-16T10:00:00Z")]
    runner = _run_list_runner(entries)

    C._dispatch_one(
        repo="ruck314/rogue", branch=C.DEFAULT_BRANCH, workflow=C.DEFAULT_WORKFLOW,
        candidate_ref=_FULL_SHA, merge_base_ref=_OTHER_SHA, mode="null",
        patch_name=None, patch_magnitude=None, forced_condition=None,
        rounds=2, label=C.LABEL_NULL, modules="tests/perf/test_batcher_combine_perf.py",
        runner=runner, sleep_fn=lambda seconds: None, epoch_fn=lambda: 0.0, interval_seconds=0,
    )

    dispatch_calls = [call for call in runner.calls if "workflow" in call and "run" in call]
    assert len(dispatch_calls) == 1
    assert "modules=tests/perf/test_batcher_combine_perf.py" in dispatch_calls[0]


def test_dispatch_one_refuses_a_module_value_the_runner_pattern_rejects_and_runs_no_subprocess():
    C = perf_gate_validation_campaign
    runner = _ScriptedGateRunner()

    result = C._dispatch_one(
        repo="ruck314/rogue", branch=C.DEFAULT_BRANCH, workflow=C.DEFAULT_WORKFLOW,
        candidate_ref=_FULL_SHA, merge_base_ref=_OTHER_SHA, mode="null",
        patch_name=None, patch_magnitude=None, forced_condition=None,
        rounds=2, label=C.LABEL_NULL, modules="../../etc/passwd",
        runner=runner, sleep_fn=lambda seconds: None, epoch_fn=lambda: 0.0, interval_seconds=0,
    )

    assert runner.calls == []
    assert result["dispatch_exit_code"] != 0
    assert "modules" in result["dispatch_error"]


# ---------------------------------------------------------------------------
# cmd_dispatch: stopping conditions
# ---------------------------------------------------------------------------

def test_cmd_dispatch_stops_on_coverage_stopping_condition():
    C = perf_gate_validation_campaign
    entries = [_run_list_entry(501, C.DEFAULT_BRANCH, "2026-08-16T10:00:00Z")]
    runner = _run_list_runner(entries)
    statuses = iter([1, 3])

    result = C.cmd_dispatch(
        repo="ruck314/rogue", branch=C.DEFAULT_BRANCH, coverage_target=3, run_cap=24,
        candidate_ref=_FULL_SHA, merge_base_ref=_FULL_SHA, mode="null", label=C.LABEL_NULL,
        status_fn=lambda: next(statuses), runner=runner, sleep_fn=lambda seconds: None,
        epoch_fn=lambda: 0.0,
    )

    dispatch_calls = [call for call in runner.calls if "workflow" in call and "run" in call]

    assert len(dispatch_calls) == 1
    assert result["condition"] == C.CONDITION_COVERAGE
    assert result["dispatched_count"] == 1


def test_cmd_dispatch_zero_dispatches_when_coverage_already_satisfied():
    C = perf_gate_validation_campaign
    runner = _ScriptedGateRunner()

    result = C.cmd_dispatch(
        coverage_target=3, run_cap=24, status_fn=lambda: 3,
        candidate_ref=_FULL_SHA, merge_base_ref=_FULL_SHA,
        runner=runner, sleep_fn=lambda seconds: None,
    )

    assert runner.calls == []
    assert result["dispatched_count"] == 0
    assert result["condition"] == C.CONDITION_COVERAGE


def test_cmd_dispatch_stops_on_the_run_cap_stopping_condition():
    C = perf_gate_validation_campaign
    entries = [_run_list_entry(n, C.DEFAULT_BRANCH, "2026-08-16T10:00:00Z") for n in range(600, 603)]
    runner = _run_list_runner(entries)

    result = C.cmd_dispatch(
        repo="ruck314/rogue", branch=C.DEFAULT_BRANCH, coverage_target=99, run_cap=2,
        candidate_ref=_FULL_SHA, merge_base_ref=_FULL_SHA,
        status_fn=lambda: 0, runner=runner, sleep_fn=lambda seconds: None, epoch_fn=lambda: 0.0,
    )

    dispatch_calls = [call for call in runner.calls if "workflow" in call and "run" in call]

    assert result["condition"] == C.CONDITION_CAP
    assert result["dispatched_count"] == 2
    assert len(dispatch_calls) == 2


def test_cmd_dispatch_stops_on_a_failed_gh_workflow_run_invocation_and_keeps_prior_dispatches():
    C = perf_gate_validation_campaign
    entries = [_run_list_entry(701, C.DEFAULT_BRANCH, "2026-08-16T10:00:00Z")]
    call_count = {"n": 0}

    def runner(argv):
        if "workflow" in argv and "run" in argv:
            call_count["n"] += 1
            if call_count["n"] == 1:
                return _completed(argv, returncode=0)
            return _completed(argv, returncode=1, stderr="not found")
        if "list" in argv:
            return _completed(argv, returncode=0, stdout=json.dumps(entries))
        return _completed(argv, returncode=0)

    statuses = iter([0, 0, 0])
    result = C.cmd_dispatch(
        repo="ruck314/rogue", branch=C.DEFAULT_BRANCH, coverage_target=99, run_cap=24,
        candidate_ref=_FULL_SHA, merge_base_ref=_FULL_SHA,
        status_fn=lambda: next(statuses), runner=runner, sleep_fn=lambda seconds: None,
        epoch_fn=lambda: 0.0,
    )

    assert result["condition"] == C.CONDITION_FAILURE
    assert result["dispatched_count"] == 1
    assert result["dispatch_exit_code"] == 1


def test_cmd_dispatch_a_dispatch_that_never_correlates_is_counted_with_no_run_id():
    C = perf_gate_validation_campaign
    runner = _run_list_runner([])
    statuses = iter([0, 3])

    result = C.cmd_dispatch(
        repo="ruck314/rogue", branch=C.DEFAULT_BRANCH, coverage_target=3, run_cap=24,
        candidate_ref=_FULL_SHA, merge_base_ref=_FULL_SHA,
        status_fn=lambda: next(statuses), runner=runner, sleep_fn=lambda seconds: None,
        epoch_fn=lambda: 0.0,
    )

    assert result["dispatched_count"] == 1
    assert result["dispatched"][0]["correlated"] is False
    assert result["dispatched"][0]["run_id"] is None


def test_every_dispatch_argv_carries_one_flag_per_workflow_input_and_the_label_appears():
    C = perf_gate_validation_campaign
    entries = [_run_list_entry(801, C.DEFAULT_BRANCH, "2026-08-16T10:00:00Z")]
    runner = _run_list_runner(entries)
    statuses = iter([0, 3])

    C.cmd_dispatch(
        repo="ruck314/rogue", branch=C.DEFAULT_BRANCH, coverage_target=3, run_cap=24,
        candidate_ref=_FULL_SHA, merge_base_ref=_OTHER_SHA, mode="null", label=C.LABEL_NULL, rounds=2,
        status_fn=lambda: next(statuses), runner=runner, sleep_fn=lambda seconds: None,
        epoch_fn=lambda: 0.0,
    )

    dispatch_calls = [call for call in runner.calls if "workflow" in call and "run" in call]
    assert len(dispatch_calls) == 1
    argv = dispatch_calls[0]

    for name, value in (
        ("candidate_ref", _FULL_SHA), ("merge_base_ref", _OTHER_SHA), ("mode", "null"),
        ("patch_name", "none"), ("patch_magnitude", "0"), ("forced_condition", "none"),
        ("rounds", "2"), ("label", C.LABEL_NULL),
    ):
        assert f"{name}={value}" in argv


def test_dispatch_cli_exposes_forced_condition_and_defaults_to_none():
    C = perf_gate_validation_campaign
    args = C.parse_args(["dispatch"])
    assert args.forced_condition is None


def test_dispatch_cli_forced_condition_flag_is_forwarded_into_the_dispatch_argv():
    """The `dispatch` subcommand accepts `--forced-condition` and forwards it into every
    dispatched run's own argv, exactly like `mode` or `label`, closing the gap where
    `cmd_dispatch` already accepted the parameter but the CLI never exposed it -- the only
    way to dispatch a forced-inconclusive run's forced condition through the campaign
    driver rather than by hand-rolling a `gh workflow run` call."""
    C = perf_gate_validation_campaign
    entries = [_run_list_entry(802, C.DEFAULT_BRANCH, "2026-08-16T10:00:00Z")]
    runner = _run_list_runner(entries)
    statuses = iter([0, 3])

    result = C.cmd_dispatch(
        repo="ruck314/rogue", branch=C.DEFAULT_BRANCH, coverage_target=3, run_cap=24,
        candidate_ref=_FULL_SHA, merge_base_ref=_FULL_SHA, mode="forced-inconclusive",
        label=C.LABEL_FORCED_INCONCLUSIVE, forced_condition="tree-hash-pair-mismatch",
        status_fn=lambda: next(statuses), runner=runner, sleep_fn=lambda seconds: None,
        epoch_fn=lambda: 0.0,
    )

    dispatch_calls = [call for call in runner.calls if "workflow" in call and "run" in call]
    assert len(dispatch_calls) == 1
    assert "forced_condition=tree-hash-pair-mismatch" in dispatch_calls[0]
    assert result["dispatched_count"] == 1


# ---------------------------------------------------------------------------
# cmd_sweep / cmd_confirm
# ---------------------------------------------------------------------------

def test_cmd_sweep_over_three_magnitudes_issues_three_dispatches_in_order_with_the_search_label():
    C = perf_gate_validation_campaign
    entries = [_run_list_entry(901, C.DEFAULT_BRANCH, "2026-08-16T10:00:00Z")]
    runner = _run_list_runner(entries)

    dispatched = C.cmd_sweep(
        "extra-memcpy-per-frame", ["1", "2", "4"],
        repo="ruck314/rogue", branch=C.DEFAULT_BRANCH,
        candidate_ref=_FULL_SHA, merge_base_ref=_OTHER_SHA,
        runner=runner, sleep_fn=lambda seconds: None, epoch_fn=lambda: 0.0,
    )

    assert len(dispatched) == 3
    assert [record["label"] for record in dispatched] == [C.LABEL_SEEDED_SEARCH] * 3

    dispatch_calls = [call for call in runner.calls if "workflow" in call and "run" in call]
    assert len(dispatch_calls) == 3
    for expected_magnitude, argv in zip(["1", "2", "4"], dispatch_calls):
        assert f"patch_magnitude={expected_magnitude}" in argv
        assert "patch_name=extra-memcpy-per-frame" in argv
        assert f"label={C.LABEL_SEEDED_SEARCH}" in argv


def test_cmd_confirm_issues_exactly_the_confirming_count_with_the_confirm_label():
    C = perf_gate_validation_campaign
    entries = [_run_list_entry(902, C.DEFAULT_BRANCH, "2026-08-16T10:00:00Z")]
    runner = _run_list_runner(entries)

    dispatched = C.cmd_confirm(
        "extra-memcpy-per-frame", "2", 3,
        repo="ruck314/rogue", branch=C.DEFAULT_BRANCH,
        candidate_ref=_FULL_SHA, merge_base_ref=_OTHER_SHA,
        runner=runner, sleep_fn=lambda seconds: None, epoch_fn=lambda: 0.0,
    )

    assert len(dispatched) == 3
    assert [record["label"] for record in dispatched] == [C.LABEL_SEEDED_CONFIRM] * 3

    dispatch_calls = [call for call in runner.calls if "workflow" in call and "run" in call]
    assert len(dispatch_calls) == 3
    for argv in dispatch_calls:
        assert "patch_magnitude=2" in argv
        assert f"label={C.LABEL_SEEDED_CONFIRM}" in argv


def test_sweep_forwards_its_module_set_to_every_dispatch():
    C = perf_gate_validation_campaign
    entries = [_run_list_entry(912, C.DEFAULT_BRANCH, "2026-08-16T10:00:00Z")]
    runner = _run_list_runner(entries)

    dispatched = C.cmd_sweep(
        "extra-memcpy-per-frame", ["1", "2"],
        repo="ruck314/rogue", branch=C.DEFAULT_BRANCH,
        candidate_ref=_FULL_SHA, merge_base_ref=_OTHER_SHA,
        modules="tests/perf/test_batcher_combine_perf.py",
        runner=runner, sleep_fn=lambda seconds: None, epoch_fn=lambda: 0.0,
    )

    assert len(dispatched) == 2
    dispatch_calls = [call for call in runner.calls if "workflow" in call and "run" in call]
    assert len(dispatch_calls) == 2
    for argv in dispatch_calls:
        assert "modules=tests/perf/test_batcher_combine_perf.py" in argv


def test_confirm_forwards_its_module_set_to_every_dispatch():
    C = perf_gate_validation_campaign
    entries = [_run_list_entry(913, C.DEFAULT_BRANCH, "2026-08-16T10:00:00Z")]
    runner = _run_list_runner(entries)

    dispatched = C.cmd_confirm(
        "extra-memcpy-per-frame", "2", 3,
        repo="ruck314/rogue", branch=C.DEFAULT_BRANCH,
        candidate_ref=_FULL_SHA, merge_base_ref=_OTHER_SHA,
        modules="tests/perf/test_batcher_combine_perf.py",
        runner=runner, sleep_fn=lambda seconds: None, epoch_fn=lambda: 0.0,
    )

    assert len(dispatched) == 3
    dispatch_calls = [call for call in runner.calls if "workflow" in call and "run" in call]
    assert len(dispatch_calls) == 3
    for argv in dispatch_calls:
        assert "modules=tests/perf/test_batcher_combine_perf.py" in argv


# ---------------------------------------------------------------------------
# _tree_hash_pair_mismatch
# ---------------------------------------------------------------------------

def test_tree_hash_pair_mismatch_returns_none_for_a_matching_pair():
    C = perf_gate_validation_campaign
    record = _gate_ab_record()
    assert C._tree_hash_pair_mismatch(record) is None


def test_tree_hash_pair_mismatch_recomputes_rather_than_trusting_the_match_flag():
    C = perf_gate_validation_campaign
    record = _gate_ab_record(merge_base_tree_hash="tree-mismatch")
    record["run"]["tree_hash_pair_match"] = True

    mismatch = C._tree_hash_pair_mismatch(record)

    assert mismatch is not None
    assert mismatch["leg"] == "merge_base"


def test_tree_hash_pair_mismatch_judges_a_patched_candidate_on_the_merge_base_half_only():
    C = perf_gate_validation_campaign
    record = _gate_ab_record(
        candidate_tree_hash="patched-tree", patch_applied=True, patch_name="extra-memcpy-per-frame",
    )
    assert C._tree_hash_pair_mismatch(record) is None


def test_tree_hash_pair_mismatch_admits_a_deliberately_forced_mismatch():
    """A forced-inconclusive run dispatched with --forced-condition
    tree-hash-pair-mismatch deliberately carries a declared_merge_base_tree_hash
    that disagrees with its measured merge_base_tree_hash
    (perf_gate_ab_runner.build_ab_record's own FORCED_TREE_HASH_PAIR_MISMATCH
    handling) -- that disagreement is the condition this run exists to force,
    not evidence of a corrupted collection, so it must not be rejected the
    way an accidental mismatch is."""
    C = perf_gate_validation_campaign
    record = _gate_ab_record(
        label=C.LABEL_FORCED_INCONCLUSIVE, mode="forced-inconclusive",
        declared_merge_base_tree_hash="0" * 40, merge_base_tree_hash="tree-a",
        forced_condition="tree-hash-pair-mismatch",
    )
    assert C._tree_hash_pair_mismatch(record) is None


def test_tree_hash_pair_mismatch_still_rejects_an_unforced_mismatch_with_the_same_label():
    """The exemption is keyed on forced_condition, not on label or mode alone:
    a forced-inconclusive run whose forced_condition names a different
    condition (or none) is judged exactly like any other record."""
    C = perf_gate_validation_campaign
    record = _gate_ab_record(
        label=C.LABEL_FORCED_INCONCLUSIVE, mode="forced-inconclusive",
        declared_merge_base_tree_hash="0" * 40, merge_base_tree_hash="tree-a",
        forced_condition="merge-base-build-failed",
    )
    assert C._tree_hash_pair_mismatch(record) is not None


# ---------------------------------------------------------------------------
# cmd_status: category derivation
# ---------------------------------------------------------------------------

def test_cmd_status_derives_category_from_label(tmp_path):
    C = perf_gate_validation_campaign
    dest = tmp_path / "gate-validation-runs"
    _write_gate_record(dest / "1-ab-record.json", _gate_ab_record(run_id="1", label=C.LABEL_NULL))

    result = C.cmd_status(dest)

    assert result["categories"] == {C.LABEL_NULL: 1}


def test_cmd_status_reports_an_unrecognized_label_as_uncategorized_with_the_observed_value(tmp_path):
    C = perf_gate_validation_campaign
    dest = tmp_path / "gate-validation-runs"
    _write_gate_record(dest / "1-ab-record.json", _gate_ab_record(run_id="1", label="not-a-real-label"))

    result = C.cmd_status(dest)

    assert result["categories"] == {C.CATEGORY_UNCATEGORIZED: 1}
    assert result["uncategorized"][0]["label"] == "not-a-real-label"


def test_cmd_status_promotes_a_patch_failed_record_regardless_of_label(tmp_path):
    C = perf_gate_validation_campaign
    dest = tmp_path / "gate-validation-runs"
    _write_gate_record(
        dest / "1-ab-record.json",
        _gate_ab_record(
            run_id="1", label=C.LABEL_SEEDED_SEARCH, patch_name="extra-memcpy-per-frame", patch_applied=False,
        ),
    )

    result = C.cmd_status(dest)

    assert result["categories"] == {C.CATEGORY_PATCH_FAILED: 1}


def test_cmd_status_never_promotes_a_never_patched_run_to_patch_failed(tmp_path):
    """Regression test: every real null/unrelated/forced-inconclusive run
    carries patch_applied: false simply because no patch was ever
    requested (patch_name is None). Promoting on patch_applied alone would
    miscategorize every one of them."""
    C = perf_gate_validation_campaign
    dest = tmp_path / "gate-validation-runs"
    _write_gate_record(
        dest / "1-ab-record.json",
        _gate_ab_record(run_id="1", label=C.LABEL_NULL, patch_name=None, patch_applied=False),
    )

    result = C.cmd_status(dest)

    assert result["categories"] == {C.LABEL_NULL: 1}


def test_cmd_status_counts_distinct_cpu_models(tmp_path):
    C = perf_gate_validation_campaign
    dest = tmp_path / "gate-validation-runs"
    _write_gate_record(dest / "1-ab-record.json", _gate_ab_record(run_id="1", cpu_model="AMD EPYC 7763"))
    _write_gate_record(dest / "2-ab-record.json", _gate_ab_record(run_id="2", cpu_model="AMD EPYC 7763"))
    _write_gate_record(dest / "3-ab-record.json", _gate_ab_record(run_id="3", cpu_model="Intel Xeon Platinum"))

    result = C.cmd_status(dest)

    assert result["host_models"] == {"AMD EPYC 7763": 2, "Intel Xeon Platinum": 1}
    assert result["distinct_host_models"] == 2


def test_cmd_status_over_empty_destination_reports_not_started(tmp_path):
    C = perf_gate_validation_campaign
    result = C.cmd_status(tmp_path / "does-not-exist")

    assert result["collected_count"] == 0
    assert result["condition"] == C.CONDITION_NOT_STARTED


def test_cmd_status_rejects_a_tree_hash_pair_mismatch_read_from_disk(tmp_path):
    C = perf_gate_validation_campaign
    dest = tmp_path / "gate-validation-runs"
    _write_gate_record(
        dest / "1-ab-record.json",
        _gate_ab_record(run_id="1", merge_base_tree_hash="tree-mismatch"),
    )

    result = C.cmd_status(dest)

    assert result["collected_count"] == 0
    assert result["rejected_count"] == 1
    assert result["rejected"][0]["reason"] == C.TREE_HASH_MISMATCH


def test_cmd_status_skips_an_unparseable_record_and_counts_it(tmp_path):
    C = perf_gate_validation_campaign
    dest = tmp_path / "gate-validation-runs"
    dest.mkdir(parents=True)
    (dest / "1-ab-record.json").write_text("not json", encoding="utf-8")

    result = C.cmd_status(dest)

    assert result["collected_count"] == 0
    assert result["skipped_count"] == 1


# ---------------------------------------------------------------------------
# cmd_collect: idempotency
# ---------------------------------------------------------------------------

def test_cmd_collect_writes_both_the_record_and_the_verdict_sidecar_under_run_id_prefixed_names(tmp_path):
    C = perf_gate_validation_campaign
    dest = tmp_path / "gate-validation-runs"
    entries = [_run_list_entry(950, C.DEFAULT_BRANCH, "2026-08-16T10:00:00Z")]
    runner = _run_list_runner(entries)
    downloader = _fake_downloader_for(lambda run_id: _gate_ab_record(run_id=str(run_id)))

    result = C.cmd_collect(repo="ruck314/rogue", branch=C.DEFAULT_BRANCH, dest=dest, runner=runner, downloader=downloader)

    assert result["collected"] == 1
    assert (dest / "950-ab-record.json").exists()
    assert (dest / "950-verdict.json").exists()


def test_cmd_collect_second_invocation_reports_already_present_and_collects_zero(tmp_path):
    C = perf_gate_validation_campaign
    dest = tmp_path / "gate-validation-runs"
    entries = [_run_list_entry(951, C.DEFAULT_BRANCH, "2026-08-16T10:00:00Z")]
    runner = _run_list_runner(entries)
    downloader = _fake_downloader_for(lambda run_id: _gate_ab_record(run_id=str(run_id)))

    first = C.cmd_collect(repo="ruck314/rogue", branch=C.DEFAULT_BRANCH, dest=dest, runner=runner, downloader=downloader)
    second = C.cmd_collect(repo="ruck314/rogue", branch=C.DEFAULT_BRANCH, dest=dest, runner=runner, downloader=downloader)

    assert first["collected"] == 1
    assert first["already_present"] == 0
    assert second["collected"] == 0
    assert second["already_present"] == 1
    assert len(list(dest.glob("951-*.json"))) == 2


# ---------------------------------------------------------------------------
# cmd_collect: tree-hash-pair rejection
# ---------------------------------------------------------------------------

def test_cmd_collect_rejects_a_pair_mismatched_run_and_writes_nothing_for_it(tmp_path):
    C = perf_gate_validation_campaign
    dest = tmp_path / "gate-validation-runs"
    entries = [_run_list_entry(952, C.DEFAULT_BRANCH, "2026-08-16T10:00:00Z")]
    runner = _run_list_runner(entries)
    downloader = _fake_downloader_for(
        lambda run_id: _gate_ab_record(run_id=str(run_id), merge_base_tree_hash="tree-mismatch"),
    )

    result = C.cmd_collect(repo="ruck314/rogue", branch=C.DEFAULT_BRANCH, dest=dest, runner=runner, downloader=downloader)

    assert result["collected"] == 0
    assert len(result["rejected"]) == 1
    assert result["rejected"][0]["reason"] == C.TREE_HASH_MISMATCH
    assert list(dest.glob("*.json")) == []


def test_cmd_collect_admits_a_patch_failed_record(tmp_path):
    C = perf_gate_validation_campaign
    dest = tmp_path / "gate-validation-runs"
    entries = [_run_list_entry(953, C.DEFAULT_BRANCH, "2026-08-16T10:00:00Z")]
    runner = _run_list_runner(entries)
    downloader = _fake_downloader_for(
        lambda run_id: _gate_ab_record(
            run_id=str(run_id), label=C.LABEL_SEEDED_SEARCH,
            patch_name="extra-memcpy-per-frame", patch_applied=False,
        ),
    )

    result = C.cmd_collect(repo="ruck314/rogue", branch=C.DEFAULT_BRANCH, dest=dest, runner=runner, downloader=downloader)

    assert result["collected"] == 1
    status = C.cmd_status(dest)
    assert status["categories"] == {C.CATEGORY_PATCH_FAILED: 1}


# ---------------------------------------------------------------------------
# cmd_collect: skip reasons
# ---------------------------------------------------------------------------

def test_cmd_collect_skips_a_run_whose_download_fails_and_continues(tmp_path):
    C = perf_gate_validation_campaign
    dest = tmp_path / "gate-validation-runs"
    entries = [
        _run_list_entry(954, C.DEFAULT_BRANCH, "2026-08-16T10:00:00Z"),
        _run_list_entry(955, C.DEFAULT_BRANCH, "2026-08-16T10:00:01Z"),
    ]
    runner = _run_list_runner(entries)
    good_downloader = _fake_downloader_for(lambda run_id: _gate_ab_record(run_id=str(run_id)))

    def flaky_downloader(repo, run_id, runner):
        if run_id == 954:
            return None
        return good_downloader(repo, run_id, runner)

    result = C.cmd_collect(repo="ruck314/rogue", branch=C.DEFAULT_BRANCH, dest=dest, runner=runner, downloader=flaky_downloader)

    assert result["collected"] == 1
    assert len(result["skipped"]) == 1
    assert result["skipped"][0]["run_id"] == 954


def test_cmd_collect_skips_a_run_with_no_gate_record_file_present(tmp_path):
    C = perf_gate_validation_campaign
    dest = tmp_path / "gate-validation-runs"
    entries = [_run_list_entry(956, C.DEFAULT_BRANCH, "2026-08-16T10:00:00Z")]
    runner = _run_list_runner(entries)

    def wrong_dir_downloader(repo, run_id, runner):
        root = Path(tempfile.mkdtemp(prefix="test-perf-gate-validation-campaign-"))
        (root / "unrelated").mkdir(parents=True, exist_ok=True)
        (root / "unrelated" / "unrelated.json").write_text("{}", encoding="utf-8")
        return root

    result = C.cmd_collect(repo="ruck314/rogue", branch=C.DEFAULT_BRANCH, dest=dest, runner=runner, downloader=wrong_dir_downloader)

    assert result["collected"] == 0
    assert len(result["skipped"]) == 1


def test_cmd_collect_skips_an_empty_artifact_and_continues(tmp_path):
    C = perf_gate_validation_campaign
    dest = tmp_path / "gate-validation-runs"
    entries = [_run_list_entry(957, C.DEFAULT_BRANCH, "2026-08-16T10:00:00Z")]
    runner = _run_list_runner(entries)

    def empty_downloader(repo, run_id, runner):
        root = Path(tempfile.mkdtemp(prefix="test-perf-gate-validation-campaign-"))
        results_dir = root / C.GATE_RECORD_DIRNAME
        results_dir.mkdir(parents=True, exist_ok=True)
        (results_dir / C.GATE_RECORD_FILENAME).write_text("", encoding="utf-8")
        return root

    result = C.cmd_collect(repo="ruck314/rogue", branch=C.DEFAULT_BRANCH, dest=dest, runner=runner, downloader=empty_downloader)

    assert result["collected"] == 0
    assert len(result["skipped"]) == 1


def test_cmd_collect_skips_an_unparseable_artifact_and_continues(tmp_path):
    C = perf_gate_validation_campaign
    dest = tmp_path / "gate-validation-runs"
    entries = [_run_list_entry(958, C.DEFAULT_BRANCH, "2026-08-16T10:00:00Z")]
    runner = _run_list_runner(entries)

    def malformed_downloader(repo, run_id, runner):
        root = Path(tempfile.mkdtemp(prefix="test-perf-gate-validation-campaign-"))
        results_dir = root / C.GATE_RECORD_DIRNAME
        results_dir.mkdir(parents=True, exist_ok=True)
        (results_dir / C.GATE_RECORD_FILENAME).write_text("not json", encoding="utf-8")
        return root

    result = C.cmd_collect(repo="ruck314/rogue", branch=C.DEFAULT_BRANCH, dest=dest, runner=runner, downloader=malformed_downloader)

    assert result["collected"] == 0
    assert len(result["skipped"]) == 1


# ---------------------------------------------------------------------------
# cmd_collect: scratch directory cleanup
# ---------------------------------------------------------------------------

def test_cmd_collect_removes_the_scratch_directory_on_the_collected_path(tmp_path):
    C = perf_gate_validation_campaign
    dest = tmp_path / "gate-validation-runs"
    entries = [_run_list_entry(959, C.DEFAULT_BRANCH, "2026-08-16T10:00:00Z")]
    runner = _run_list_runner(entries)
    scratch_roots: list[Path] = []
    inner_downloader = _fake_downloader_for(lambda run_id: _gate_ab_record(run_id=str(run_id)))

    def tracking_downloader(repo, run_id, runner):
        root = inner_downloader(repo, run_id, runner)
        scratch_roots.append(root)
        return root

    C.cmd_collect(repo="ruck314/rogue", branch=C.DEFAULT_BRANCH, dest=dest, runner=runner, downloader=tracking_downloader)

    assert scratch_roots and not scratch_roots[0].exists()


def test_cmd_collect_removes_the_scratch_directory_on_the_skipped_path(tmp_path):
    C = perf_gate_validation_campaign
    dest = tmp_path / "gate-validation-runs"
    entries = [_run_list_entry(960, C.DEFAULT_BRANCH, "2026-08-16T10:00:00Z")]
    runner = _run_list_runner(entries)
    scratch_roots: list[Path] = []

    def empty_downloader(repo, run_id, runner):
        root = Path(tempfile.mkdtemp(prefix="test-perf-gate-validation-campaign-"))
        results_dir = root / C.GATE_RECORD_DIRNAME
        results_dir.mkdir(parents=True, exist_ok=True)
        (results_dir / C.GATE_RECORD_FILENAME).write_text("", encoding="utf-8")
        scratch_roots.append(root)
        return root

    C.cmd_collect(repo="ruck314/rogue", branch=C.DEFAULT_BRANCH, dest=dest, runner=runner, downloader=empty_downloader)

    assert scratch_roots and not scratch_roots[0].exists()


def test_cmd_collect_removes_the_scratch_directory_on_the_rejected_path(tmp_path):
    C = perf_gate_validation_campaign
    dest = tmp_path / "gate-validation-runs"
    entries = [_run_list_entry(961, C.DEFAULT_BRANCH, "2026-08-16T10:00:00Z")]
    runner = _run_list_runner(entries)
    scratch_roots: list[Path] = []
    inner_downloader = _fake_downloader_for(
        lambda run_id: _gate_ab_record(run_id=str(run_id), merge_base_tree_hash="tree-mismatch"),
    )

    def tracking_downloader(repo, run_id, runner):
        root = inner_downloader(repo, run_id, runner)
        scratch_roots.append(root)
        return root

    C.cmd_collect(repo="ruck314/rogue", branch=C.DEFAULT_BRANCH, dest=dest, runner=runner, downloader=tracking_downloader)

    assert scratch_roots and not scratch_roots[0].exists()


# ---------------------------------------------------------------------------
# _find_gate_record_files / _find_verdict_files
# ---------------------------------------------------------------------------

def test_find_gate_record_files_globs_the_known_nested_subpath(tmp_path):
    C = perf_gate_validation_campaign
    nested = tmp_path / "gate-validation-results-1" / "rogue" / "rogue" / C.GATE_RECORD_DIRNAME
    nested.mkdir(parents=True)
    (nested / C.GATE_RECORD_FILENAME).write_text("{}", encoding="utf-8")

    found = C._find_gate_record_files(tmp_path)

    assert len(found) == 1
    assert found[0].name == C.GATE_RECORD_FILENAME


def test_find_verdict_files_globs_the_known_nested_subpath(tmp_path):
    C = perf_gate_validation_campaign
    nested = tmp_path / "gate-validation-results-1" / "rogue" / "rogue" / C.GATE_RECORD_DIRNAME
    nested.mkdir(parents=True)
    (nested / C.VERDICT_RECORD_FILENAME).write_text("{}", encoding="utf-8")

    found = C._find_verdict_files(tmp_path)

    assert len(found) == 1
    assert found[0].name == C.VERDICT_RECORD_FILENAME


# ---------------------------------------------------------------------------
# argparse / CLI scaffold
# ---------------------------------------------------------------------------

def test_parse_args_exposes_all_six_subcommands():
    C = perf_gate_validation_campaign
    for command, extra in (
        ("register", []),
        ("dispatch", []),
        ("collect", []),
        ("status", []),
        ("sweep", ["--patch-name", "extra-memcpy-per-frame", "--magnitudes", "1,2"]),
        ("confirm", ["--patch-name", "extra-memcpy-per-frame", "--magnitude", "1"]),
    ):
        args = C.parse_args([command] + extra)
        assert args.command == command


def test_parse_args_sweep_requires_patch_name_and_magnitudes():
    with pytest.raises(SystemExit):
        perf_gate_validation_campaign.parse_args(["sweep"])


def test_parse_args_confirm_requires_patch_name_and_magnitude():
    with pytest.raises(SystemExit):
        perf_gate_validation_campaign.parse_args(["confirm"])


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
