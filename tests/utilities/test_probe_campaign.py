# ----------------------------------------------------------------------------
# Title      : Probe Campaign Driver Tests
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

probe_campaign = importlib.import_module("probe_campaign")


def _completed(argv, returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(argv, returncode=returncode, stdout=stdout, stderr=stderr)


class _ScriptedRunner:
    """Injectable subprocess runner returning canned CompletedProcess objects
    keyed off a predicate over the argv, in registration order. Every
    invocation is recorded in `calls` so a test can assert on the command
    sequence, with no real `gh` or `git` binary and no network access.
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
        "event": "push",
        "headSha": "deadbeef",
        "name": "Rogue Perf Probe",
        "status": "completed",
        "updatedAt": created_at,
        "url": f"https://example.invalid/runs/{database_id}",
        "workflowDatabaseId": 1,
    }
    entry.update(overrides)
    return entry


def _write_probe_run(path, *, tree_hash="tree-a", cpu_model="AMD EPYC 7763"):
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "probe_schema_version": 1,
        "run": {"git_tree_hash": tree_hash},
        "fingerprint": {"cpu_model": cpu_model},
        "calibration": {},
        "windows": [],
        "perf_events": {},
        "instruments": {},
        "interventions": {},
        "confirmation": {},
        "build": {},
        "errors": [],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


# ---------------------------------------------------------------------------
# GH_RUN_LIST_FIELDS
# ---------------------------------------------------------------------------

def test_gh_run_list_fields_matches_the_recorded_installed_field_set():
    assert set(probe_campaign.GH_RUN_LIST_FIELDS) == {
        "conclusion", "createdAt", "databaseId", "event", "headBranch",
        "headSha", "name", "status", "updatedAt", "url", "workflowDatabaseId",
    }


# ---------------------------------------------------------------------------
# correlate_runs
# ---------------------------------------------------------------------------

def test_correlate_runs_filters_by_branch_and_cutoff():
    entries = [
        _run_list_entry(1, "perf-probe/campaign", "2026-08-15T10:00:00Z"),
        _run_list_entry(2, "some-other-branch", "2026-08-15T10:01:00Z"),
        _run_list_entry(3, "perf-probe/campaign", "2026-08-15T09:00:00Z"),
    ]
    since_epoch = probe_campaign._parse_created_at("2026-08-15T09:30:00Z")

    kept, skipped = probe_campaign.correlate_runs(entries, "perf-probe/campaign", since_epoch)

    assert [entry["databaseId"] for entry in kept] == [1]
    assert skipped == 0


def test_correlate_runs_keeps_both_entries_sharing_a_head_commit_and_timestamp():
    entries = [
        _run_list_entry(102, "perf-probe/campaign", "2026-08-15T10:00:00Z", headSha="samesha"),
        _run_list_entry(101, "perf-probe/campaign", "2026-08-15T10:00:00Z", headSha="samesha"),
    ]

    kept, skipped = probe_campaign.correlate_runs(entries, "perf-probe/campaign", 0.0)

    assert [entry["databaseId"] for entry in kept] == [101, 102]
    assert skipped == 0


def test_correlate_runs_orders_by_created_at_then_database_id():
    entries = [
        _run_list_entry(5, "perf-probe/campaign", "2026-08-15T11:00:00Z"),
        _run_list_entry(4, "perf-probe/campaign", "2026-08-15T10:00:00Z"),
    ]

    kept, _ = probe_campaign.correlate_runs(entries, "perf-probe/campaign", 0.0)

    assert [entry["databaseId"] for entry in kept] == [4, 5]


def test_correlate_runs_excludes_and_counts_unparseable_timestamp():
    entries = [
        _run_list_entry(6, "perf-probe/campaign", "not-a-timestamp"),
        _run_list_entry(7, "perf-probe/campaign", "2026-08-15T10:00:00Z"),
    ]

    kept, skipped = probe_campaign.correlate_runs(entries, "perf-probe/campaign", 0.0)

    assert [entry["databaseId"] for entry in kept] == [7]
    assert skipped == 1


# ---------------------------------------------------------------------------
# cmd_collect
# ---------------------------------------------------------------------------

def _list_runner_for(entries):
    return _ScriptedRunner().when(
        _contains("list"),
        _completed(["gh", "run", "list"], returncode=0, stdout=json.dumps(entries)),
    )


def test_cmd_collect_second_invocation_skips_already_present_artifact(tmp_path):
    dest = tmp_path / "probe-runs"
    entries = [_run_list_entry(201, "perf-probe/campaign", "2026-08-15T10:00:00Z")]
    runner = _list_runner_for(entries)

    download_calls = []

    def fake_lister(repo, run_id, runner):
        return ["probe-results-1"]

    def fake_downloader(repo, run_id, artifact_name, dest_path, runner):
        download_calls.append((run_id, artifact_name))
        _write_probe_run(dest_path, tree_hash="tree-a")
        return dest_path

    first = probe_campaign.cmd_collect(
        repo="ruck314/rogue", branch="perf-probe/campaign", dest=dest,
        runner=runner, artifact_lister=fake_lister, downloader=fake_downloader,
    )
    second = probe_campaign.cmd_collect(
        repo="ruck314/rogue", branch="perf-probe/campaign", dest=dest,
        runner=runner, artifact_lister=fake_lister, downloader=fake_downloader,
    )

    assert first["downloaded"] == 1
    assert first["already_present"] == 0
    assert second["downloaded"] == 0
    assert second["already_present"] == 1
    assert len(download_calls) == 1


def test_cmd_collect_zero_correlated_runs_is_non_zero_exit():
    runner = _list_runner_for([_run_list_entry(1, "unrelated-branch", "2026-08-15T10:00:00Z")])

    result = probe_campaign.cmd_collect(
        repo="ruck314/rogue", branch="perf-probe/campaign", dest=Path("/tmp/unused"),
        runner=runner, artifact_lister=lambda repo, run_id, runner: [],
        downloader=lambda repo, run_id, artifact_name, dest_path, runner: None,
    )

    assert result["exit_code"] != 0
    assert result["reason"] == "no-runs-found"


def test_cmd_collect_skips_tree_hash_mismatch_and_continues(tmp_path):
    dest = tmp_path / "probe-runs"
    entries = [
        _run_list_entry(301, "perf-probe/campaign", "2026-08-15T10:00:00Z"),
        _run_list_entry(302, "perf-probe/campaign", "2026-08-15T10:00:01Z"),
    ]
    runner = _list_runner_for(entries)

    def fake_lister(repo, run_id, runner):
        return ["probe-results-1"]

    def fake_downloader(repo, run_id, artifact_name, dest_path, runner):
        tree_hash = "tree-a" if run_id == 301 else "tree-mismatch"
        _write_probe_run(dest_path, tree_hash=tree_hash)
        return dest_path

    result = probe_campaign.cmd_collect(
        repo="ruck314/rogue", branch="perf-probe/campaign", dest=dest,
        expected_tree_hash="tree-a", runner=runner,
        artifact_lister=fake_lister, downloader=fake_downloader,
    )

    assert result["downloaded"] == 1
    assert result["tree_hash_mismatches"] == 1
    assert result["exit_code"] == 0


# ---------------------------------------------------------------------------
# cmd_dispatch
# ---------------------------------------------------------------------------

def _status_returning(distinct_host_models):
    return lambda: {"distinct_host_models": distinct_host_models}


def test_cmd_dispatch_makes_one_commit_and_one_push_per_iteration_and_never_merges():
    runner = _ScriptedRunner()
    statuses = iter([{"distinct_host_models": 0}, {"distinct_host_models": 3}])

    result = probe_campaign.cmd_dispatch(
        remote="fork", branch="perf-probe/campaign",
        coverage_target=3, run_cap=24, jobs_per_push=4,
        status_fn=lambda: next(statuses),
        runner=runner, sleep_fn=lambda seconds: None,
    )

    commit_calls = [call for call in runner.calls if "commit" in call]
    push_calls = [call for call in runner.calls if "push" in call]
    merge_calls = [call for call in runner.calls if "merge" in call]

    assert len(commit_calls) == 1
    assert len(push_calls) == 1
    assert merge_calls == []
    assert result["pushes"] == 1
    assert result["dispatched_jobs"] == 4
    assert result["condition"] == probe_campaign.CONDITION_COVERAGE


def test_cmd_dispatch_zero_pushes_when_coverage_already_satisfied():
    runner = _ScriptedRunner()

    result = probe_campaign.cmd_dispatch(
        coverage_target=3, run_cap=24, status_fn=_status_returning(3),
        runner=runner, sleep_fn=lambda seconds: None,
    )

    assert runner.calls == []
    assert result["pushes"] == 0
    assert result["condition"] == probe_campaign.CONDITION_COVERAGE


def test_cmd_dispatch_zero_pushes_with_cap_of_zero():
    runner = _ScriptedRunner()

    result = probe_campaign.cmd_dispatch(
        coverage_target=3, run_cap=0, status_fn=_status_returning(0),
        runner=runner, sleep_fn=lambda seconds: None,
    )

    assert runner.calls == []
    assert result["pushes"] == 0
    assert result["condition"] == probe_campaign.CONDITION_CAP


def test_cmd_dispatch_stops_on_failed_push_with_exit_code_recorded_and_no_retry():
    runner = _ScriptedRunner().when(
        _contains("push"), _completed(["git", "push"], returncode=1, stderr="rejected"),
    )

    result = probe_campaign.cmd_dispatch(
        coverage_target=3, run_cap=24, status_fn=_status_returning(0),
        runner=runner, sleep_fn=lambda seconds: None,
    )

    push_calls = [call for call in runner.calls if "push" in call]

    assert result["condition"] == probe_campaign.CONDITION_FAILURE
    assert result["push_exit_code"] == 1
    assert result["dispatched_jobs"] == 0
    assert len(push_calls) == 1


# ---------------------------------------------------------------------------
# cmd_status
# ---------------------------------------------------------------------------

def test_cmd_status_over_empty_destination_reports_not_started(tmp_path):
    result = probe_campaign.cmd_status(tmp_path / "does-not-exist")

    assert result["run_count"] == 0
    assert result["condition"] == probe_campaign.CONDITION_NOT_STARTED


def test_cmd_status_reports_run_count_and_host_models(tmp_path):
    dest = tmp_path / "probe-runs"
    _write_probe_run(dest / "1-probe-results-1.json", tree_hash="tree-a", cpu_model="AMD EPYC 7763")
    _write_probe_run(dest / "2-probe-results-1.json", tree_hash="tree-a", cpu_model="AMD EPYC 7763")
    _write_probe_run(dest / "3-probe-results-1.json", tree_hash="tree-a", cpu_model="Intel Xeon Platinum")

    result = probe_campaign.cmd_status(dest, coverage_target=3, run_cap=24, expected_tree_hash="tree-a")

    assert result["run_count"] == 3
    assert result["host_models"] == {"AMD EPYC 7763": 2, "Intel Xeon Platinum": 1}
    assert result["distinct_host_models"] == 2
    assert result["condition"] == probe_campaign.CONDITION_IN_PROGRESS


def test_cmd_status_counts_tree_hash_mismatches_separately_from_run_count(tmp_path):
    dest = tmp_path / "probe-runs"
    _write_probe_run(dest / "1-probe-results-1.json", tree_hash="tree-a")
    _write_probe_run(dest / "2-probe-results-1.json", tree_hash="tree-stale")

    result = probe_campaign.cmd_status(dest, expected_tree_hash="tree-a")

    assert result["run_count"] == 1
    assert result["tree_hash_mismatches"] == 1


# ---------------------------------------------------------------------------
# cmd_smoke_test
# ---------------------------------------------------------------------------

def test_cmd_smoke_test_records_failed_verdict_and_still_runs_remaining_operations(tmp_path):
    runner = _ScriptedRunner().when(
        _contains("list"),
        _completed(["gh", "run", "list"], returncode=1, stderr="boom"),
    )
    out_path = tmp_path / "SMOKE.md"

    result = probe_campaign.cmd_smoke_test(runner=runner, out_path=out_path)

    verdicts = {operation["operation"]: operation["verdict"] for operation in result["operations"]}
    assert len(result["operations"]) == 3
    assert verdicts["list"] == "fail"
    assert verdicts["dispatch"] == "pass"
    assert verdicts["download"] == "pass"
    assert out_path.exists()


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
