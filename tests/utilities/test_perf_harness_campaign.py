# ----------------------------------------------------------------------------
# Title      : Perf Harness Campaign Driver Tests
# ----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
# ----------------------------------------------------------------------------

"""Unit tests for scripts/perf_harness_campaign.py, following
tests/utilities/test_probe_campaign.py's injection style: every `gh`
invocation goes through a scripted fake so nothing here touches the network.
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

perf_harness_campaign = importlib.import_module("perf_harness_campaign")
perf_campaign_report = importlib.import_module("perf_campaign_report")


def _completed(argv, returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(argv, returncode=returncode, stdout=stdout, stderr=stderr)


class _ScriptedRunner:
    """Injectable subprocess runner returning canned CompletedProcess objects
    keyed off a predicate over the argv, in registration order. Every
    invocation is recorded in `calls`, with no real `gh` or `git` binary and
    no network access.
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
        "name": "Rogue Perf Harness",
        "status": "completed",
        "updatedAt": created_at,
        "url": f"https://example.invalid/runs/{database_id}",
        "workflowDatabaseId": 1,
    }
    entry.update(overrides)
    return entry


def _run_list_runner(entries, **extra_rules):
    runner = _ScriptedRunner().when(
        _contains("list"),
        _completed(["gh", "run", "list"], returncode=0, stdout=json.dumps(entries)),
    )
    for predicate, completed in extra_rules.items():
        runner.when(predicate, completed)
    return runner


def _write_harness_run(
    path, *, tree_hash="tree-a", cpu_model="AMD EPYC 7763", run_id="201", injected_load="false",
):
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "harness_run_schema_version": 1,
        "run": {
            "campaign_branch": "perf-harness/campaign",
            "git_tree_hash": tree_hash,
            "github_run_id": run_id,
            "injected_load": injected_load,
        },
        "environment": {"cpu_model": cpu_model},
        "benchmarks": {},
        "build": {},
        "errors": [],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


# ---------------------------------------------------------------------------
# Module constants
# ---------------------------------------------------------------------------

def test_default_run_cap_exceeds_the_dispatch_target_with_recorded_margin():
    assert perf_harness_campaign.DEFAULT_DISPATCH_TARGET == 20
    assert perf_harness_campaign.DEFAULT_RUN_CAP > perf_harness_campaign.DEFAULT_DISPATCH_TARGET


def test_module_source_never_reaches_for_an_opted_out_gh_capability():
    source = Path(perf_harness_campaign.__file__).read_text(encoding="utf-8")
    non_comment_lines = [
        line for line in source.splitlines() if not line.strip().startswith("#")
    ]
    joined = "\n".join(non_comment_lines)
    for token in ("run rerun", "run watch", "run cancel"):
        assert token not in joined
    assert "shell=True" not in joined
    assert "import probe_campaign" not in joined


# ---------------------------------------------------------------------------
# correlate_runs
# ---------------------------------------------------------------------------

def test_correlate_runs_filters_by_branch_and_cutoff():
    entries = [
        _run_list_entry(1, "perf-harness/campaign", "2026-08-16T10:00:00Z"),
        _run_list_entry(2, "some-other-branch", "2026-08-16T10:01:00Z"),
        _run_list_entry(3, "perf-harness/campaign", "2026-08-16T09:00:00Z"),
    ]
    since_epoch = perf_harness_campaign._parse_created_at("2026-08-16T09:30:00Z")

    kept, skipped = perf_harness_campaign.correlate_runs(entries, "perf-harness/campaign", since_epoch)

    assert [entry["databaseId"] for entry in kept] == [1]
    assert skipped == 0


def test_correlate_runs_orders_by_created_at_then_database_id():
    entries = [
        _run_list_entry(5, "perf-harness/campaign", "2026-08-16T11:00:00Z"),
        _run_list_entry(4, "perf-harness/campaign", "2026-08-16T10:00:00Z"),
    ]

    kept, _ = perf_harness_campaign.correlate_runs(entries, "perf-harness/campaign", 0.0)

    assert [entry["databaseId"] for entry in kept] == [4, 5]


def test_correlate_runs_excludes_and_counts_unparseable_timestamp():
    entries = [
        _run_list_entry(6, "perf-harness/campaign", "not-a-timestamp"),
        _run_list_entry(7, "perf-harness/campaign", "2026-08-16T10:00:00Z"),
    ]

    kept, skipped = perf_harness_campaign.correlate_runs(entries, "perf-harness/campaign", 0.0)

    assert [entry["databaseId"] for entry in kept] == [7]
    assert skipped == 1


# ---------------------------------------------------------------------------
# cmd_register
# ---------------------------------------------------------------------------

def test_cmd_register_reports_registered_when_workflow_is_active():
    runner = _ScriptedRunner().when(
        _contains("list"),
        _completed(
            ["gh", "workflow", "list"], returncode=0,
            stdout="Rogue Perf Harness\tactive\t335249900\nRogue Perf Probe\tactive\t335249800\n",
        ),
    )

    result = perf_harness_campaign.cmd_register(repo="ruck314/rogue", runner=runner)

    assert result["registered"] is True
    assert result["state"] == "active"
    assert result["fix"] is None


def test_cmd_register_reports_not_registered_plainly_when_workflow_absent():
    runner = _ScriptedRunner().when(
        _contains("list"),
        _completed(["gh", "workflow", "list"], returncode=0, stdout="Rogue Perf Probe\tactive\t335249800\n"),
    )

    result = perf_harness_campaign.cmd_register(repo="ruck314/rogue", runner=runner)

    assert result["registered"] is False
    assert result["fix"] is not None
    assert "perf_harness.yml" in result["fix"]


def test_cmd_register_does_not_raise_on_a_failing_gh_invocation():
    runner = _ScriptedRunner().when(
        _contains("list"),
        _completed(["gh", "workflow", "list"], returncode=1, stderr="not authenticated"),
    )

    result = perf_harness_campaign.cmd_register(repo="ruck314/rogue", runner=runner)

    assert result["registered"] is False
    assert result["reason"] is not None


# ---------------------------------------------------------------------------
# cmd_dispatch: stopping conditions
# ---------------------------------------------------------------------------

def test_cmd_dispatch_stops_on_coverage_stopping_condition():
    entries = [_run_list_entry(401, "perf-harness/campaign", "2026-08-16T10:00:00Z")]
    runner = _run_list_runner(entries)
    statuses = iter([1, 3])

    result = perf_harness_campaign.cmd_dispatch(
        repo="ruck314/rogue", branch="perf-harness/campaign", coverage_target=3, run_cap=24,
        status_fn=lambda: next(statuses), runner=runner, sleep_fn=lambda seconds: None,
    )

    dispatch_calls = [call for call in runner.calls if "workflow" in call and "run" in call]

    assert len(dispatch_calls) == 1
    assert result["condition"] == perf_harness_campaign.CONDITION_COVERAGE
    assert result["dispatched_count"] == 1


def test_cmd_dispatch_zero_dispatches_when_coverage_already_satisfied():
    runner = _ScriptedRunner()

    result = perf_harness_campaign.cmd_dispatch(
        coverage_target=3, run_cap=24, status_fn=lambda: 3,
        runner=runner, sleep_fn=lambda seconds: None,
    )

    assert runner.calls == []
    assert result["dispatched_count"] == 0
    assert result["condition"] == perf_harness_campaign.CONDITION_COVERAGE


def test_cmd_dispatch_stops_on_the_run_cap_stopping_condition():
    entries = [_run_list_entry(n, "perf-harness/campaign", "2026-08-16T10:00:00Z") for n in range(500, 503)]
    runner = _run_list_runner(entries)

    result = perf_harness_campaign.cmd_dispatch(
        repo="ruck314/rogue", branch="perf-harness/campaign", coverage_target=99, run_cap=2,
        status_fn=lambda: 0, runner=runner, sleep_fn=lambda seconds: None,
    )

    dispatch_calls = [call for call in runner.calls if "workflow" in call and "run" in call]

    assert result["condition"] == perf_harness_campaign.CONDITION_CAP
    assert result["dispatched_count"] == 2
    assert len(dispatch_calls) == 2


def test_cmd_dispatch_zero_dispatches_with_cap_of_zero():
    runner = _ScriptedRunner()

    result = perf_harness_campaign.cmd_dispatch(
        coverage_target=3, run_cap=0, status_fn=lambda: 0,
        runner=runner, sleep_fn=lambda seconds: None,
    )

    assert runner.calls == []
    assert result["condition"] == perf_harness_campaign.CONDITION_CAP


def test_cmd_dispatch_stops_on_a_failed_gh_workflow_run_invocation():
    runner = _ScriptedRunner().when(
        _contains("workflow"),
        _completed(["gh", "workflow", "run"], returncode=1, stderr="not found"),
    )

    result = perf_harness_campaign.cmd_dispatch(
        coverage_target=3, run_cap=24, status_fn=lambda: 0,
        runner=runner, sleep_fn=lambda seconds: None,
    )

    assert result["condition"] == perf_harness_campaign.CONDITION_FAILURE
    assert result["dispatched_count"] == 0


def test_cmd_dispatch_counts_a_failed_or_cancelled_run_and_keeps_looping():
    entries = [
        _run_list_entry(601, "perf-harness/campaign", "2026-08-16T10:00:00Z", conclusion="failure"),
    ]
    runner = _run_list_runner(entries)
    statuses = iter([0, 0, 3])

    result = perf_harness_campaign.cmd_dispatch(
        repo="ruck314/rogue", branch="perf-harness/campaign", coverage_target=3, run_cap=24,
        status_fn=lambda: next(statuses), runner=runner, sleep_fn=lambda seconds: None,
        epoch_fn=lambda: 0.0,
    )

    assert result["dispatched_count"] == 2
    assert all(record["conclusion"] == "failure" for record in result["dispatched"])
    assert result["condition"] == perf_harness_campaign.CONDITION_COVERAGE


def test_cmd_dispatch_never_calls_workflow_run_when_the_loop_never_iterates():
    runner = _ScriptedRunner()

    perf_harness_campaign.cmd_dispatch(
        coverage_target=1, run_cap=24, status_fn=lambda: 1,
        runner=runner, sleep_fn=lambda seconds: None,
    )

    rerun_calls = [call for call in runner.calls if "rerun" in call]
    watch_calls = [call for call in runner.calls if "watch" in call]
    cancel_calls = [call for call in runner.calls if "cancel" in call]

    assert rerun_calls == []
    assert watch_calls == []
    assert cancel_calls == []


# ---------------------------------------------------------------------------
# cmd_dispatch: injected load
# ---------------------------------------------------------------------------

def test_cmd_dispatch_injected_load_issues_exactly_one_dispatch_with_the_input_set_true():
    entries = [_run_list_entry(701, "perf-harness/campaign", "2026-08-16T10:00:00Z")]
    runner = _run_list_runner(entries)

    result = perf_harness_campaign.cmd_dispatch(
        repo="ruck314/rogue", branch="perf-harness/campaign", injected_load=True,
        runner=runner, sleep_fn=lambda seconds: None, epoch_fn=lambda: 0.0,
    )

    workflow_run_calls = [call for call in runner.calls if "workflow" in call and "run" in call]

    assert len(workflow_run_calls) == 1
    assert f"{perf_harness_campaign.INJECTED_LOAD_INPUT}=true" in " ".join(workflow_run_calls[0])
    assert result["injected_load_run_id"] == 701
    assert len(result["dispatched"]) == 1


def test_cmd_dispatch_injected_load_reports_uncorrelated_dispatch_rather_than_guessing():
    runner = _run_list_runner([])

    result = perf_harness_campaign.cmd_dispatch(
        repo="ruck314/rogue", branch="perf-harness/campaign", injected_load=True,
        runner=runner, sleep_fn=lambda seconds: None,
    )

    assert result["injected_load_run_id"] is None
    assert result["dispatched"][0]["correlated"] is False


# ---------------------------------------------------------------------------
# argparse / CLI scaffold
# ---------------------------------------------------------------------------

def test_parse_args_exposes_all_four_subcommands():
    for command, extra in (
        ("register", []),
        ("dispatch", []),
        ("collect", ["--tree-hash", "abc"]),
        ("status", []),
    ):
        args = perf_harness_campaign.parse_args([command] + extra)
        assert args.command == command


def test_parse_args_collect_requires_tree_hash():
    with pytest.raises(SystemExit):
        perf_harness_campaign.parse_args(["collect"])


# ---------------------------------------------------------------------------
# cmd_collect: idempotency
# ---------------------------------------------------------------------------

def _fake_downloader_for(tree_hash="tree-a", run_id_to_tree_hash=None):
    run_id_to_tree_hash = run_id_to_tree_hash or {}

    def downloader(repo, run_id, runner):
        root = Path(tempfile.mkdtemp(prefix="test-perf-harness-campaign-"))
        this_tree_hash = run_id_to_tree_hash.get(run_id, tree_hash)
        _write_harness_run(
            root / perf_harness_campaign.HARNESS_RESULTS_DIRNAME / perf_harness_campaign.RUN_RECORD_FILENAME,
            tree_hash=this_tree_hash, run_id=str(run_id),
        )
        return root

    return downloader


def test_cmd_collect_selects_the_aggregated_run_record_beside_raw_benchmark_siblings(tmp_path):
    """Regression test for a real campaign finding: a downloaded artifact
    holds 13-14 raw per-benchmark sibling files (one per tests/perf/
    module's own _perf_harness.emit_harness_result call, e.g.
    block_gil_contention_drain.json) alongside the one aggregated
    RUN_RECORD_FILENAME scripts/perf_harness_runner.py writes.
    Alphabetical sort order does not reliably put the aggregated file
    first (a name starting with 'b' sorts before 'run-record.json'), so
    collection must select RUN_RECORD_FILENAME by name, never the
    sorted-glob's first entry. A raw sibling carries an empty `build` and
    only its own single `benchmarks` entry; only the aggregated file
    carries every benchmark and the build/ccache/targets/timing evidence.
    """
    dest = tmp_path / "harness-runs"
    entries = [_run_list_entry(950, "perf-harness/campaign", "2026-08-16T10:00:00Z")]
    runner = _run_list_runner(entries)

    def downloader(repo, run_id, runner):
        root = Path(tempfile.mkdtemp(prefix="test-perf-harness-campaign-"))
        results_dir = root / perf_harness_campaign.HARNESS_RESULTS_DIRNAME
        results_dir.mkdir(parents=True, exist_ok=True)
        # A raw per-benchmark sibling sorting alphabetically before the
        # aggregated file, with only one benchmark and no build block.
        (results_dir / "block_gil_contention_drain.json").write_text(
            json.dumps({
                "harness_run_schema_version": 1,
                "run": {"git_tree_hash": "tree-a", "github_run_id": str(run_id)},
                "environment": {"cpu_model": "AMD EPYC 7763"},
                "benchmarks": {"block_gil_contention_drain": {"metrics": {}}},
                "build": {},
                "errors": [],
            }),
            encoding="utf-8",
        )
        # The aggregated run-record: every benchmark, and a populated build block.
        (results_dir / perf_harness_campaign.RUN_RECORD_FILENAME).write_text(
            json.dumps({
                "harness_run_schema_version": 1,
                "run": {"git_tree_hash": "tree-a", "github_run_id": str(run_id)},
                "environment": {"cpu_model": "AMD EPYC 7763"},
                "benchmarks": {
                    "block_gil_contention_drain": {"metrics": {}},
                    "remoteSetRate": {"metrics": {}},
                },
                "build": {"ccache": {"hit_rate_percent": 98.9}},
                "errors": [],
            }),
            encoding="utf-8",
        )
        return root

    result = perf_harness_campaign.cmd_collect(
        repo="ruck314/rogue", branch="perf-harness/campaign", dest=dest,
        expected_tree_hash="tree-a", runner=runner, downloader=downloader,
    )

    assert result["collected"] == 1
    written = list(dest.glob("950-*.json"))
    assert len(written) == 1
    assert written[0].name == f"950-{perf_harness_campaign.RUN_RECORD_FILENAME}"
    payload = json.loads(written[0].read_text(encoding="utf-8"))
    assert sorted(payload["benchmarks"]) == ["block_gil_contention_drain", "remoteSetRate"]
    assert payload["build"]["ccache"]["hit_rate_percent"] == 98.9


def test_cmd_collect_second_invocation_reports_already_present_and_downloads_nothing(tmp_path):
    dest = tmp_path / "harness-runs"
    entries = [_run_list_entry(801, "perf-harness/campaign", "2026-08-16T10:00:00Z")]
    runner = _run_list_runner(entries)
    downloader = _fake_downloader_for()

    first = perf_harness_campaign.cmd_collect(
        repo="ruck314/rogue", branch="perf-harness/campaign", dest=dest,
        expected_tree_hash="tree-a", runner=runner, downloader=downloader,
    )
    second = perf_harness_campaign.cmd_collect(
        repo="ruck314/rogue", branch="perf-harness/campaign", dest=dest,
        expected_tree_hash="tree-a", runner=runner, downloader=downloader,
    )

    assert first["collected"] == 1
    assert first["already_present"] == 0
    assert second["collected"] == 0
    assert second["already_present"] == 1
    assert len(list(dest.glob("801-*.json"))) == 1


def test_cmd_collect_running_the_same_completed_run_twice_writes_no_second_copy(tmp_path):
    dest = tmp_path / "harness-runs"
    entries = [_run_list_entry(802, "perf-harness/campaign", "2026-08-16T10:00:00Z")]
    runner = _run_list_runner(entries)
    downloader = _fake_downloader_for()

    perf_harness_campaign.cmd_collect(
        repo="ruck314/rogue", branch="perf-harness/campaign", dest=dest,
        expected_tree_hash="tree-a", runner=runner, downloader=downloader,
    )
    files_after_first = sorted(p.name for p in dest.glob("*.json"))

    perf_harness_campaign.cmd_collect(
        repo="ruck314/rogue", branch="perf-harness/campaign", dest=dest,
        expected_tree_hash="tree-a", runner=runner, downloader=downloader,
    )
    files_after_second = sorted(p.name for p in dest.glob("*.json"))

    assert files_after_first == files_after_second
    assert len(files_after_second) == 1


# ---------------------------------------------------------------------------
# cmd_collect: tree-hash rejection
# ---------------------------------------------------------------------------

def test_cmd_collect_rejects_a_tree_hash_mismatch_and_does_not_write_it(tmp_path):
    dest = tmp_path / "harness-runs"
    entries = [_run_list_entry(901, "perf-harness/campaign", "2026-08-16T10:00:00Z")]
    runner = _run_list_runner(entries)
    downloader = _fake_downloader_for(run_id_to_tree_hash={901: "tree-mismatch"})

    result = perf_harness_campaign.cmd_collect(
        repo="ruck314/rogue", branch="perf-harness/campaign", dest=dest,
        expected_tree_hash="tree-a", runner=runner, downloader=downloader,
    )

    assert result["collected"] == 0
    assert len(result["rejected"]) == 1
    assert result["rejected"][0]["reason"] == perf_campaign_report.TREE_HASH_MISMATCH
    assert list(dest.glob("*.json")) == []


def test_cmd_collect_continues_past_one_mismatch_to_collect_the_next_run(tmp_path):
    dest = tmp_path / "harness-runs"
    entries = [
        _run_list_entry(902, "perf-harness/campaign", "2026-08-16T10:00:00Z"),
        _run_list_entry(903, "perf-harness/campaign", "2026-08-16T10:00:01Z"),
    ]
    runner = _run_list_runner(entries)
    downloader = _fake_downloader_for(run_id_to_tree_hash={902: "tree-mismatch", 903: "tree-a"})

    result = perf_harness_campaign.cmd_collect(
        repo="ruck314/rogue", branch="perf-harness/campaign", dest=dest,
        expected_tree_hash="tree-a", runner=runner, downloader=downloader,
    )

    assert result["collected"] == 1
    assert len(result["rejected"]) == 1


def test_cmd_collect_missing_expected_tree_hash_raises_rather_than_accepting_everything(tmp_path):
    dest = tmp_path / "harness-runs"

    with pytest.raises(ValueError):
        perf_harness_campaign.cmd_collect(
            repo="ruck314/rogue", branch="perf-harness/campaign", dest=dest,
            expected_tree_hash=None, runner=_run_list_runner([]),
        )


# ---------------------------------------------------------------------------
# cmd_collect: skip on missing/empty/unparseable artifact
# ---------------------------------------------------------------------------

def test_cmd_collect_skips_a_run_whose_download_fails_and_continues(tmp_path):
    dest = tmp_path / "harness-runs"
    entries = [
        _run_list_entry(904, "perf-harness/campaign", "2026-08-16T10:00:00Z"),
        _run_list_entry(905, "perf-harness/campaign", "2026-08-16T10:00:01Z"),
    ]
    runner = _run_list_runner(entries)
    good_downloader = _fake_downloader_for()

    def flaky_downloader(repo, run_id, runner):
        if run_id == 904:
            return None
        return good_downloader(repo, run_id, runner)

    result = perf_harness_campaign.cmd_collect(
        repo="ruck314/rogue", branch="perf-harness/campaign", dest=dest,
        expected_tree_hash="tree-a", runner=runner, downloader=flaky_downloader,
    )

    assert result["collected"] == 1
    assert len(result["skipped"]) == 1
    assert result["skipped"][0]["run_id"] == 904


def test_cmd_collect_skips_an_unparseable_artifact_and_continues(tmp_path):
    dest = tmp_path / "harness-runs"
    entries = [_run_list_entry(906, "perf-harness/campaign", "2026-08-16T10:00:00Z")]
    runner = _run_list_runner(entries)

    def malformed_downloader(repo, run_id, runner):
        root = Path(tempfile.mkdtemp(prefix="test-perf-harness-campaign-"))
        malformed = root / perf_harness_campaign.HARNESS_RESULTS_DIRNAME / perf_harness_campaign.RUN_RECORD_FILENAME
        malformed.parent.mkdir(parents=True, exist_ok=True)
        malformed.write_text("not json", encoding="utf-8")
        return root

    result = perf_harness_campaign.cmd_collect(
        repo="ruck314/rogue", branch="perf-harness/campaign", dest=dest,
        expected_tree_hash="tree-a", runner=runner, downloader=malformed_downloader,
    )

    assert result["collected"] == 0
    assert len(result["skipped"]) == 1


def test_cmd_collect_skips_an_empty_artifact_and_continues(tmp_path):
    dest = tmp_path / "harness-runs"
    entries = [_run_list_entry(907, "perf-harness/campaign", "2026-08-16T10:00:00Z")]
    runner = _run_list_runner(entries)

    def empty_downloader(repo, run_id, runner):
        root = Path(tempfile.mkdtemp(prefix="test-perf-harness-campaign-"))
        empty = root / perf_harness_campaign.HARNESS_RESULTS_DIRNAME / perf_harness_campaign.RUN_RECORD_FILENAME
        empty.parent.mkdir(parents=True, exist_ok=True)
        empty.write_text("", encoding="utf-8")
        return root

    result = perf_harness_campaign.cmd_collect(
        repo="ruck314/rogue", branch="perf-harness/campaign", dest=dest,
        expected_tree_hash="tree-a", runner=runner, downloader=empty_downloader,
    )

    assert result["collected"] == 0
    assert len(result["skipped"]) == 1


def test_cmd_collect_skips_a_run_with_no_harness_artifact_directory(tmp_path):
    dest = tmp_path / "harness-runs"
    entries = [_run_list_entry(908, "perf-harness/campaign", "2026-08-16T10:00:00Z")]
    runner = _run_list_runner(entries)

    def wrong_dir_downloader(repo, run_id, runner):
        root = Path(tempfile.mkdtemp(prefix="test-perf-harness-campaign-"))
        (root / "perf-results").mkdir(parents=True, exist_ok=True)
        (root / "perf-results" / "unrelated.json").write_text("{}", encoding="utf-8")
        return root

    result = perf_harness_campaign.cmd_collect(
        repo="ruck314/rogue", branch="perf-harness/campaign", dest=dest,
        expected_tree_hash="tree-a", runner=runner, downloader=wrong_dir_downloader,
    )

    assert result["collected"] == 0
    assert len(result["skipped"]) == 1


# ---------------------------------------------------------------------------
# cmd_status
# ---------------------------------------------------------------------------

def test_cmd_status_over_empty_destination_reports_not_started(tmp_path):
    result = perf_harness_campaign.cmd_status(tmp_path / "does-not-exist")

    assert result["collected_count"] == 0
    assert result["condition"] == perf_harness_campaign.CONDITION_NOT_STARTED


def test_cmd_status_reports_collected_count_and_host_models(tmp_path):
    dest = tmp_path / "harness-runs"
    _write_harness_run(dest / "1-remoteSetRate.json", tree_hash="tree-a", cpu_model="AMD EPYC 7763", run_id="1")
    _write_harness_run(dest / "2-remoteSetRate.json", tree_hash="tree-a", cpu_model="AMD EPYC 7763", run_id="2")
    _write_harness_run(
        dest / "3-remoteSetRate.json", tree_hash="tree-a", cpu_model="Intel Xeon Platinum", run_id="3",
    )

    result = perf_harness_campaign.cmd_status(dest, coverage_target=3, run_cap=24, expected_tree_hash="tree-a")

    assert result["collected_count"] == 3
    assert result["host_models"] == {"AMD EPYC 7763": 2, "Intel Xeon Platinum": 1}
    assert result["distinct_host_models"] == 2
    assert result["condition"] == perf_harness_campaign.CONDITION_IN_PROGRESS


def test_cmd_status_reports_coverage_condition_once_the_target_is_met(tmp_path):
    dest = tmp_path / "harness-runs"
    _write_harness_run(dest / "1-remoteSetRate.json", cpu_model="AMD EPYC 7763", run_id="1")
    _write_harness_run(dest / "2-remoteSetRate.json", cpu_model="AMD EPYC 9V74", run_id="2")
    _write_harness_run(dest / "3-remoteSetRate.json", cpu_model="Intel Xeon Platinum", run_id="3")

    result = perf_harness_campaign.cmd_status(dest, coverage_target=3, run_cap=24)

    assert result["condition"] == perf_harness_campaign.CONDITION_COVERAGE


def test_cmd_status_reports_cap_condition_once_the_run_cap_is_reached(tmp_path):
    dest = tmp_path / "harness-runs"
    _write_harness_run(dest / "1-remoteSetRate.json", cpu_model="AMD EPYC 7763", run_id="1")
    _write_harness_run(dest / "2-remoteSetRate.json", cpu_model="AMD EPYC 7763", run_id="2")

    result = perf_harness_campaign.cmd_status(dest, coverage_target=99, run_cap=2)

    assert result["condition"] == perf_harness_campaign.CONDITION_CAP


def test_cmd_status_counts_tree_hash_mismatches_separately_from_collected_count(tmp_path):
    dest = tmp_path / "harness-runs"
    _write_harness_run(dest / "1-remoteSetRate.json", tree_hash="tree-a", run_id="1")
    _write_harness_run(dest / "2-remoteSetRate.json", tree_hash="tree-stale", run_id="2")

    result = perf_harness_campaign.cmd_status(dest, expected_tree_hash="tree-a")

    assert result["collected_count"] == 1
    assert result["rejected_count"] == 1
    assert result["rejected"][0]["reason"] == perf_campaign_report.TREE_HASH_MISMATCH


def test_cmd_status_skips_an_unparseable_record_and_counts_it(tmp_path):
    dest = tmp_path / "harness-runs"
    dest.mkdir(parents=True)
    (dest / "1-remoteSetRate.json").write_text("not json", encoding="utf-8")

    result = perf_harness_campaign.cmd_status(dest)

    assert result["collected_count"] == 0
    assert result["skipped_count"] == 1


def test_cmd_status_reports_which_run_carries_the_injected_load_label(tmp_path):
    dest = tmp_path / "harness-runs"
    _write_harness_run(dest / "1-remoteSetRate.json", run_id="1", injected_load="false")
    _write_harness_run(dest / "2-remoteSetRate.json", run_id="2", injected_load="true")

    result = perf_harness_campaign.cmd_status(dest)

    assert result["injected_load_run_id"] == "2"


def test_cmd_dispatch_default_status_fn_now_reuses_cmd_status(tmp_path, monkeypatch):
    dest = tmp_path / "harness-runs"
    _write_harness_run(dest / "1-remoteSetRate.json", cpu_model="AMD EPYC 7763", run_id="1")
    _write_harness_run(dest / "2-remoteSetRate.json", cpu_model="AMD EPYC 9V74", run_id="2")
    _write_harness_run(dest / "3-remoteSetRate.json", cpu_model="Intel Xeon Platinum", run_id="3")

    calls = []
    original = perf_harness_campaign.cmd_status

    def spying_cmd_status(*args, **kwargs):
        calls.append((args, kwargs))
        return original(*args, **kwargs)

    monkeypatch.setattr(perf_harness_campaign, "cmd_status", spying_cmd_status)

    result = perf_harness_campaign.cmd_dispatch(
        dest=dest, coverage_target=3, run_cap=24, runner=_ScriptedRunner(),
        sleep_fn=lambda seconds: None,
    )

    assert calls, "cmd_dispatch's default status_fn must call cmd_status"
    assert result["condition"] == perf_harness_campaign.CONDITION_COVERAGE


# ---------------------------------------------------------------------------
# cmd_smoke_test
# ---------------------------------------------------------------------------

def test_cmd_smoke_test_records_every_integrate_operation_and_writes_its_own_file(tmp_path):
    entries = [_run_list_entry(999, "perf-harness/campaign", "2026-08-16T10:00:00Z")]
    runner = _run_list_runner(entries)
    out_path = tmp_path / "SMOKE.md"

    result = perf_harness_campaign.cmd_smoke_test(runner=runner, out_path=out_path)

    operation_names = {operation["operation"] for operation in result["operations"]}
    assert {"workflow list", "workflow run", "run list", "run view", "run download"} <= operation_names
    assert out_path.exists()


def test_cmd_smoke_test_never_overwrites_a_phase_2_smoke_test_artifact():
    assert perf_harness_campaign.DEFAULT_SMOKE_TEST_OUT not in (
        "docs/plans/perf-ci-hardening/GH-CLI-SMOKE-TEST.md",
        "docs/plans/perf-ci-hardening/GH-CLI-SMOKE-TEST-CAMPAIGN.md",
    )


def test_cmd_smoke_test_records_failed_verdict_and_still_runs_remaining_operations(tmp_path):
    runner = _ScriptedRunner().when(
        _contains("list"),
        _completed(["gh", "run", "list"], returncode=1, stderr="boom"),
    )
    out_path = tmp_path / "SMOKE.md"

    result = perf_harness_campaign.cmd_smoke_test(runner=runner, out_path=out_path)

    verdicts = {operation["operation"]: operation["verdict"] for operation in result["operations"]}
    assert verdicts["run list"] == "fail"
    assert out_path.exists()


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
