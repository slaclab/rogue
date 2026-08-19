#!/usr/bin/env python3
# ----------------------------------------------------------------------------
# Title      : ROGUE Runner Capability Probe Campaign Driver
# ----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
# ----------------------------------------------------------------------------

"""Drive the runner capability probe campaign against the fork.

The installed `gh` binary is version 2.4.0 (March 2022), years older than
the release that first printed a run identifier on `gh workflow run`.
Dispatching a run and identifying which run was dispatched are therefore
always two separate steps here: a dispatch is followed by a `gh run list
--json` call, and the resulting run is picked out by matching campaign
branch and creation time, never by reading anything the dispatch command
itself printed.

`GH_RUN_LIST_FIELDS` is the one module constant holding the exact field
names this installed `gh` version accepts for `gh run list --json`,
recorded live in docs/plans/perf-ci-hardening/GH-CLI-SMOKE-TEST.md. This
version predates several fields present in current `gh` releases; asking
for a newer field this version does not know about returns nothing useful
rather than raising an error partway through a multi-day campaign. No field
name literal outside that constant appears anywhere else in this module;
every `gh run list --json` call is built by joining this constant.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import probe_capability_report  # noqa: E402  (flat sibling import, path inserted above)


# The complete gh run list --json field set the installed gh 2.4.0 binary
# accepts. See the module docstring above.
GH_RUN_LIST_FIELDS: tuple[str, ...] = (
    "conclusion",
    "createdAt",
    "databaseId",
    "event",
    "headBranch",
    "headSha",
    "name",
    "status",
    "updatedAt",
    "url",
    "workflowDatabaseId",
)

# gh 2.4.0's createdAt shape, confirmed in the recorded smoke test. Parsed
# with this exact format rather than a permissive fallback, so a shape this
# version does not actually emit is treated as unparseable, not guessed at.
CREATED_AT_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

DEFAULT_REPO = "ruck314/rogue"
DEFAULT_REMOTE = "fork"
DEFAULT_BRANCH = "perf-probe/campaign"
DEFAULT_WORKFLOW = "perf_probe.yml"
DEFAULT_DEST = "docs/plans/perf-ci-hardening/probe-runs"
DEFAULT_LIST_LIMIT = 200

ARTIFACT_NAME_PREFIX = "probe-results"
UNKNOWN_HOST_MODEL = "unknown"

SUBPROCESS_TIMEOUT_SECONDS = 30

# Dispatch loop defaults. The interval defaults conservatively because a
# personal fork's Actions quota behavior is unverified going into the
# campaign, and a tight loop is the expensive way to find that out.
DEFAULT_INTERVAL_SECONDS = 300
DEFAULT_JOBS_PER_PUSH = 4
DEFAULT_COVERAGE_TARGET = 3
DEFAULT_RUN_CAP = 24

DISPATCH_COMMIT_MESSAGE = "probe campaign dispatch push"

# The dispatch loop's stopping conditions, and the report cmd_status derives
# from the same collected-records read the loop polls between pushes.
CONDITION_NOT_STARTED = "not-started"
CONDITION_IN_PROGRESS = "in-progress"
CONDITION_COVERAGE = "coverage"
CONDITION_CAP = "cap"
CONDITION_FAILURE = "failure"

DEFAULT_SMOKE_TEST_ARTIFACT_NAME = f"{ARTIFACT_NAME_PREFIX}-1"
DEFAULT_SMOKE_TEST_OUT = "docs/plans/perf-ci-hardening/GH-CLI-SMOKE-TEST-CAMPAIGN.md"
SMOKE_TEST_OUTPUT_MAX_CHARS = 4000


def _run_subprocess(argv: list[str]) -> subprocess.CompletedProcess:
    """Injectable module-level default runner for every `gh`/`git` call this
    module makes. Never raises: a missing binary or a timeout comes back as
    a nonzero-returncode result instead, so every unit test can drive
    canned JSON and canned exit codes through this one seam without a real
    binary or network access.
    """
    try:
        return subprocess.run(
            argv, capture_output=True, text=True, timeout=SUBPROCESS_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return subprocess.CompletedProcess(argv, returncode=1, stdout="", stderr=str(exc))


def _parse_created_at(value: Any) -> float | None:
    """Parse a `createdAt` value against the one recorded gh 2.4.0 format.
    Returns None for anything that does not match exactly, so the caller
    can exclude and count it rather than raising or silently guessing at a
    looser format.
    """
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.strptime(value, CREATED_AT_FORMAT)
    except ValueError:
        return None
    return parsed.replace(tzinfo=timezone.utc).timestamp()


def correlate_runs(
    entries: list[dict[str, Any]], branch: str, since_epoch: float,
) -> tuple[list[dict[str, Any]], int]:
    """Pick this campaign's runs out of a `gh run list --json` result.

    Keeps only entries whose head branch equals `branch` and whose creation
    timestamp is at or after `since_epoch`, ordered by creation timestamp
    ascending and then by database identifier ascending. Two runs
    dispatched by the same push share a head commit and can share a
    creation second; both are real runs from different matrix jobs, and
    both are kept here, disambiguated by identifier rather than one being
    dropped as a duplicate. An entry whose creation timestamp does not
    parse is excluded and counted in the returned skipped tally instead of
    raising, so one malformed entry cannot abort a campaign-long listing.
    """
    matched: list[tuple[float, Any, dict[str, Any]]] = []
    skipped_timestamps = 0
    for entry in entries:
        if entry.get("headBranch") != branch:
            continue
        created_epoch = _parse_created_at(entry.get("createdAt"))
        if created_epoch is None:
            skipped_timestamps += 1
            continue
        if created_epoch < since_epoch:
            continue
        matched.append((created_epoch, entry.get("databaseId"), entry))

    matched.sort(key=lambda item: (item[0], item[1]))
    return [entry for _, _, entry in matched], skipped_timestamps


def list_runs(
    repo: str,
    *,
    limit: int = DEFAULT_LIST_LIMIT,
    runner: Callable[[list[str]], subprocess.CompletedProcess] = _run_subprocess,
) -> tuple[list[dict[str, Any]], str | None]:
    """Call `gh run list --json <GH_RUN_LIST_FIELDS>` and return the parsed
    entries plus an error string (None on success). Never raises: a
    nonzero exit or unparsable output comes back as an error string for the
    caller to report, rather than propagating an exception.
    """
    argv = [
        "gh", "run", "list", "--repo", repo,
        "--json", ",".join(GH_RUN_LIST_FIELDS),
        "--limit", str(limit),
    ]
    completed = runner(argv)
    if completed.returncode != 0:
        return [], f"gh run list exited {completed.returncode}: {(completed.stderr or '').strip()}"
    try:
        entries = json.loads(completed.stdout or "[]")
    except json.JSONDecodeError as exc:
        return [], f"gh run list produced unparsable JSON: {exc}"
    if not isinstance(entries, list):
        return [], "gh run list produced a non-list JSON payload"
    return entries, None


def list_artifact_names(
    repo: str,
    run_id: Any,
    runner: Callable[[list[str]], subprocess.CompletedProcess] = _run_subprocess,
) -> list[str]:
    """List artifact names attached to one run via the raw REST endpoint
    through `gh api`, bypassing gh's own `--json` field-projection layer
    entirely so this call carries none of that layer's version-skew risk.
    """
    argv = ["gh", "api", f"repos/{repo}/actions/runs/{run_id}/artifacts", "--jq", ".artifacts[].name"]
    completed = runner(argv)
    if completed.returncode != 0:
        return []
    return [line for line in (completed.stdout or "").splitlines() if line.strip()]


def download_artifact(
    repo: str,
    run_id: Any,
    artifact_name: str,
    dest_path: Path,
    runner: Callable[[list[str]], subprocess.CompletedProcess] = _run_subprocess,
) -> Path | None:
    """Download one named artifact for one run into `dest_path`, staging
    through a scratch temporary directory so a failed or partial download
    never leaves a partial file at `dest_path`.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        argv = ["gh", "run", "download", str(run_id), "--repo", repo, "-n", artifact_name, "-D", tmp_dir]
        completed = runner(argv)
        if completed.returncode != 0:
            return None
        candidates = sorted(Path(tmp_dir).glob("*.json"))
        if not candidates:
            return None
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        dest_path.write_bytes(candidates[0].read_bytes())
        return dest_path


def _destination_filename(run_id: Any, artifact_name: str) -> str:
    return f"{run_id}-{artifact_name}.json"


def cmd_collect(
    *,
    repo: str = DEFAULT_REPO,
    branch: str = DEFAULT_BRANCH,
    dest: Path = Path(DEFAULT_DEST),
    since_epoch: float = 0.0,
    expected_tree_hash: str | None = None,
    limit: int = DEFAULT_LIST_LIMIT,
    runner: Callable[[list[str]], subprocess.CompletedProcess] = _run_subprocess,
    artifact_lister: Callable[..., list[str]] = list_artifact_names,
    downloader: Callable[..., "Path | None"] = download_artifact,
) -> dict[str, Any]:
    """List, correlate, and idempotently download this campaign's probe
    artifacts. A campaign spans days and will be interrupted and resumed:
    a destination file that already exists is never re-downloaded, and a
    downloaded record whose recorded tree hash does not match
    `expected_tree_hash` is rejected from the population with the reason
    logged, without aborting collection of the remaining runs. Zero
    correlated runs is reported as a clear no-runs-found outcome with a
    non-zero exit code, never a silent empty success.
    """
    entries, list_error = list_runs(repo, limit=limit, runner=runner)
    if list_error is not None:
        print(f"gh run list failed: {list_error}")
        return {
            "exit_code": 1, "reason": "list-failed", "downloaded": 0,
            "already_present": 0, "tree_hash_mismatches": 0, "skipped_timestamps": 0,
        }

    correlated, skipped_timestamps = correlate_runs(entries, branch, since_epoch)

    if not correlated:
        print(
            f"No runs found for branch {branch!r} at or after epoch {since_epoch:.0f}. "
            "Nothing collected."
        )
        return {
            "exit_code": 1, "reason": "no-runs-found", "downloaded": 0,
            "already_present": 0, "tree_hash_mismatches": 0,
            "skipped_timestamps": skipped_timestamps,
        }

    dest.mkdir(parents=True, exist_ok=True)

    downloaded = 0
    already_present = 0
    tree_hash_mismatches = 0

    for entry in correlated:
        run_id = entry.get("databaseId")
        for artifact_name in artifact_lister(repo, run_id, runner):
            if not artifact_name.startswith(ARTIFACT_NAME_PREFIX):
                continue

            dest_path = dest / _destination_filename(run_id, artifact_name)
            if dest_path.exists():
                already_present += 1
                continue

            downloaded_path = downloader(repo, run_id, artifact_name, dest_path, runner)
            if downloaded_path is None:
                continue

            if expected_tree_hash is not None:
                actual_tree_hash = None
                record = probe_capability_report.load_probe_run(downloaded_path)
                if record is not None:
                    run_info = record.get("run")
                    if isinstance(run_info, dict):
                        actual_tree_hash = run_info.get("git_tree_hash")
                if actual_tree_hash != expected_tree_hash:
                    tree_hash_mismatches += 1
                    print(
                        f"Rejecting run {run_id} artifact {artifact_name}: tree hash "
                        f"mismatch (expected {expected_tree_hash!r}, got {actual_tree_hash!r})"
                    )
                    downloaded_path.unlink(missing_ok=True)
                    continue

            downloaded += 1

    return {
        "exit_code": 0,
        "reason": "collected",
        "downloaded": downloaded,
        "already_present": already_present,
        "tree_hash_mismatches": tree_hash_mismatches,
        "skipped_timestamps": skipped_timestamps,
    }


def cmd_status(
    dest: Path,
    *,
    coverage_target: int = DEFAULT_COVERAGE_TARGET,
    run_cap: int = DEFAULT_RUN_CAP,
    expected_tree_hash: str | None = None,
) -> dict[str, Any]:
    """Read the collected records under `dest` and report the run count,
    the distinct host models observed with a count each, the number of
    records rejected for a tree hash mismatch, and which stopping condition
    currently holds. A missing or empty destination directory reports zero
    runs and the not-yet-started condition without raising, so `dispatch`
    can poll this before the first push has ever landed.
    """
    if not dest.is_dir():
        return {
            "run_count": 0, "host_models": {}, "distinct_host_models": 0,
            "tree_hash_mismatches": 0, "condition": CONDITION_NOT_STARTED,
        }

    host_models: dict[str, int] = {}
    tree_hash_mismatches = 0
    run_count = 0

    for path in sorted(dest.glob("*.json")):
        record = probe_capability_report.load_probe_run(path)
        if record is None:
            continue

        run_info = record.get("run")
        run_info = run_info if isinstance(run_info, dict) else {}
        if expected_tree_hash is not None and run_info.get("git_tree_hash") != expected_tree_hash:
            tree_hash_mismatches += 1
            continue

        run_count += 1
        fingerprint = record.get("fingerprint")
        fingerprint = fingerprint if isinstance(fingerprint, dict) else {}
        model = fingerprint.get("cpu_model") or UNKNOWN_HOST_MODEL
        host_models[model] = host_models.get(model, 0) + 1

    distinct_host_models = len(host_models)
    if run_count == 0:
        condition = CONDITION_NOT_STARTED
    elif distinct_host_models >= coverage_target:
        condition = CONDITION_COVERAGE
    elif run_count >= run_cap:
        condition = CONDITION_CAP
    else:
        condition = CONDITION_IN_PROGRESS

    return {
        "run_count": run_count,
        "host_models": host_models,
        "distinct_host_models": distinct_host_models,
        "tree_hash_mismatches": tree_hash_mismatches,
        "condition": condition,
    }


def cmd_dispatch(
    *,
    remote: str = DEFAULT_REMOTE,
    branch: str = DEFAULT_BRANCH,
    dest: Path = Path(DEFAULT_DEST),
    interval_seconds: int = DEFAULT_INTERVAL_SECONDS,
    jobs_per_push: int = DEFAULT_JOBS_PER_PUSH,
    coverage_target: int = DEFAULT_COVERAGE_TARGET,
    run_cap: int = DEFAULT_RUN_CAP,
    status_fn: Callable[[], dict[str, Any]] | None = None,
    runner: Callable[[list[str]], subprocess.CompletedProcess] = _run_subprocess,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    """Dispatch one push-triggered probe run per iteration by making one
    empty commit on `branch` and pushing it to `remote`; never a merge, so
    the campaign branch's recorded tree hash never changes. Both stopping
    conditions are checked before every push: the observed distinct host
    model count reaching `coverage_target`, or the dispatched job count
    reaching `run_cap`, whichever fires first, and the returned result
    names which one fired. A failed push stops the loop immediately with
    its exit code recorded; there is no silent retry.
    """
    if status_fn is None:
        def status_fn() -> dict[str, Any]:
            return cmd_status(dest, coverage_target=coverage_target, run_cap=run_cap)

    dispatched_jobs = 0
    pushes = 0

    while True:
        distinct_host_models = status_fn()["distinct_host_models"]

        if distinct_host_models >= coverage_target:
            return {
                "condition": CONDITION_COVERAGE, "pushes": pushes,
                "dispatched_jobs": dispatched_jobs, "distinct_host_models": distinct_host_models,
            }
        if dispatched_jobs >= run_cap:
            return {
                "condition": CONDITION_CAP, "pushes": pushes,
                "dispatched_jobs": dispatched_jobs, "distinct_host_models": distinct_host_models,
            }

        commit_completed = runner(["git", "commit", "--allow-empty", "-m", DISPATCH_COMMIT_MESSAGE])
        push_completed = runner(["git", "push", remote, branch])
        pushes += 1

        if push_completed.returncode != 0:
            return {
                "condition": CONDITION_FAILURE, "pushes": pushes,
                "dispatched_jobs": dispatched_jobs, "distinct_host_models": distinct_host_models,
                "push_exit_code": push_completed.returncode,
                "commit_exit_code": commit_completed.returncode,
            }

        dispatched_jobs += jobs_per_push
        sleep_fn(interval_seconds)


def _bounded_excerpt(text: str, limit: int = SMOKE_TEST_OUTPUT_MAX_CHARS) -> str:
    return (text or "")[:limit]


def _record_operation(
    name: str, argv: list[str], completed: subprocess.CompletedProcess,
) -> dict[str, Any]:
    combined_output = (completed.stdout or "") + (completed.stderr or "")
    return {
        "operation": name,
        "command": " ".join(argv),
        "exit_code": completed.returncode,
        "output_summary": _bounded_excerpt(combined_output),
        "verdict": "pass" if completed.returncode == 0 else "fail",
    }


def _render_smoke_test_markdown(operations: list[dict[str, Any]]) -> str:
    lines = [
        "<!-- generated by scripts/probe_campaign.py smoke-test, do not edit by hand -->",
        "# gh CLI Campaign Smoke Test (generated)",
        "",
    ]
    for operation in operations:
        lines.extend([
            f"## {operation['operation']}",
            "",
            "```sh",
            operation["command"],
            "```",
            "",
            f"- Exit code: {operation['exit_code']}",
            f"- Verdict: {operation['verdict']}",
            "",
            "Output summary:",
            "",
            "```",
            operation["output_summary"],
            "```",
            "",
        ])
    return "\n".join(lines) + "\n"


def cmd_smoke_test(
    *,
    repo: str = DEFAULT_REPO,
    branch: str = DEFAULT_BRANCH,
    workflow: str = DEFAULT_WORKFLOW,
    artifact_name: str = DEFAULT_SMOKE_TEST_ARTIFACT_NAME,
    runner: Callable[[list[str]], subprocess.CompletedProcess] = _run_subprocess,
    out_path: Path = Path(DEFAULT_SMOKE_TEST_OUT),
) -> dict[str, Any]:
    """Run the dispatch, list, and download operations once each against
    the fork, recording each command, exit code, and a bounded output
    summary, plus a pass or fail verdict per operation. A failing operation
    is recorded and the remaining operations still run, since a partial
    record is more useful than none. No tokens and no full command logs
    are written into the record, only the bounded summary above.
    """
    operations: list[dict[str, Any]] = []

    dispatch_argv = ["gh", "workflow", "run", workflow, "--repo", repo, "--ref", branch]
    operations.append(_record_operation("dispatch", dispatch_argv, runner(dispatch_argv)))

    list_argv = [
        "gh", "run", "list", "--repo", repo,
        "--json", ",".join(GH_RUN_LIST_FIELDS), "--limit", "20",
    ]
    operations.append(_record_operation("list", list_argv, runner(list_argv)))

    download_argv = ["gh", "run", "download", "--repo", repo, "-n", artifact_name]
    operations.append(_record_operation("download", download_argv, runner(download_argv)))

    markdown = _render_smoke_test_markdown(operations)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(markdown, encoding="utf-8")

    return {"operations": operations, "out_path": str(out_path)}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    smoke = subparsers.add_parser(
        "smoke-test", help="Run the dispatch/list/download operations once each and record the outcome",
    )
    smoke.add_argument("--repo", default=DEFAULT_REPO)
    smoke.add_argument("--branch", default=DEFAULT_BRANCH, help="Campaign branch, used as the dispatch ref")
    smoke.add_argument("--workflow", default=DEFAULT_WORKFLOW)
    smoke.add_argument("--artifact-name", default=DEFAULT_SMOKE_TEST_ARTIFACT_NAME)
    smoke.add_argument("--out", default=DEFAULT_SMOKE_TEST_OUT)

    dispatch = subparsers.add_parser(
        "dispatch", help="Push one empty commit per iteration until a stopping condition fires",
    )
    dispatch.add_argument("--remote", default=DEFAULT_REMOTE)
    dispatch.add_argument("--branch", default=DEFAULT_BRANCH)
    dispatch.add_argument("--dest", default=DEFAULT_DEST)
    dispatch.add_argument("--interval-seconds", type=int, default=DEFAULT_INTERVAL_SECONDS)
    dispatch.add_argument("--jobs-per-push", type=int, default=DEFAULT_JOBS_PER_PUSH)
    dispatch.add_argument("--coverage-target", type=int, default=DEFAULT_COVERAGE_TARGET)
    dispatch.add_argument("--run-cap", type=int, default=DEFAULT_RUN_CAP)

    collect = subparsers.add_parser(
        "collect", help="Correlate this campaign's runs and download their artifacts idempotently",
    )
    collect.add_argument("--repo", default=DEFAULT_REPO)
    collect.add_argument("--branch", default=DEFAULT_BRANCH)
    collect.add_argument("--dest", default=DEFAULT_DEST)
    collect.add_argument("--tree-hash", default=None, help="Expected git tree hash for population membership")

    status = subparsers.add_parser(
        "status", help="Report the currently collected runs and the stopping condition",
    )
    status.add_argument("--dest", default=DEFAULT_DEST)
    status.add_argument("--coverage-target", type=int, default=DEFAULT_COVERAGE_TARGET)
    status.add_argument("--run-cap", type=int, default=DEFAULT_RUN_CAP)
    status.add_argument("--tree-hash", default=None, help="Expected git tree hash for population membership")

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if args.command == "smoke-test":
        result = cmd_smoke_test(
            repo=args.repo, branch=args.branch, workflow=args.workflow,
            artifact_name=args.artifact_name, out_path=Path(args.out),
        )
        for operation in result["operations"]:
            print(f"{operation['operation']}: {operation['verdict']} (exit {operation['exit_code']})")
        return 0 if all(op["verdict"] == "pass" for op in result["operations"]) else 1

    if args.command == "dispatch":
        result = cmd_dispatch(
            remote=args.remote, branch=args.branch, dest=Path(args.dest),
            interval_seconds=args.interval_seconds, jobs_per_push=args.jobs_per_push,
            coverage_target=args.coverage_target, run_cap=args.run_cap,
        )
        print(
            f"condition: {result['condition']} pushes: {result['pushes']} "
            f"dispatched_jobs: {result['dispatched_jobs']}"
        )
        return 0 if result["condition"] != CONDITION_FAILURE else 1

    if args.command == "collect":
        result = cmd_collect(
            repo=args.repo, branch=args.branch, dest=Path(args.dest),
            expected_tree_hash=args.tree_hash,
        )
        print(
            f"downloaded: {result['downloaded']} already_present: {result['already_present']} "
            f"tree_hash_mismatches: {result['tree_hash_mismatches']}"
        )
        return result["exit_code"]

    if args.command == "status":
        result = cmd_status(
            Path(args.dest), coverage_target=args.coverage_target,
            run_cap=args.run_cap, expected_tree_hash=args.tree_hash,
        )
        print(f"run_count: {result['run_count']}")
        print(f"distinct_host_models: {result['distinct_host_models']}")
        for model, count in sorted(result["host_models"].items()):
            print(f"  {model}: {count}")
        print(f"tree_hash_mismatches: {result['tree_hash_mismatches']}")
        print(f"condition: {result['condition']}")
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
