#!/usr/bin/env python3
# ----------------------------------------------------------------------------
# Title      : ROGUE Perf Harness Measurement Campaign Driver
# ----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
# ----------------------------------------------------------------------------

"""Drive the perf harness measurement campaign against the fork.

Criterion 2's "at least 20 workflow_dispatch runs" is read here as 20
distinct dispatches, so unlike scripts/probe_campaign.py (which dispatches by pushing
empty commits to fire a push event), every campaign run here is issued as
its own `gh workflow run --ref <frozen-branch>` call. `gh workflow run`
prints neither a run identifier nor a URL at the installed version, so a
dispatch and identifying which run it started are always two separate
steps: a dispatch is followed by a `gh run list --json` call, and the
resulting run is picked out by matching campaign branch, dispatch event,
and creation time, never by reading anything the dispatch command itself
printed.

`GH_RUN_LIST_FIELDS` is the one module constant holding the exact field
names the installed `gh` version accepts for `gh run list --json`, recorded
live against the fork during Phase 2's own smoke test. No field name
literal outside that constant appears anywhere else in this module.

This module's capability surface is deliberately narrow: workflow
list, workflow run (with --ref and the injected_load input), run list, run
view, and run download. It never reaches for a re-run, a blocking watch, a
cancel, or the raw REST passthrough that matrix opts out of.
"""

from __future__ import annotations

import argparse
import json
import shutil
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

import perf_campaign_report  # noqa: E402  (flat sibling import, path inserted above)


# The complete gh run list --json field set the installed gh 2.4.0 binary
# accepts, recorded live in GH-CLI-SMOKE-TEST.md. See the module docstring.
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
DEFAULT_BRANCH = "perf-harness/campaign"
DEFAULT_WORKFLOW = "perf_harness.yml"
DEFAULT_WORKFLOW_DISPLAY_NAME = "Rogue Perf Harness"
DEFAULT_DEST = "docs/plans/perf-ci-hardening/harness-runs"
DEFAULT_LIST_LIMIT = 200

# The artifact the workflow uploads (actions/upload-artifact `name:` in
# .github/workflows/perf_harness.yml) and the subdirectory inside it that
# holds the harness record this driver cares about (PERF_HARNESS_RESULTS_DIR,
# distinct from the unrelated Tier 3 perf-results/*.json files also present
# in the same artifact).
ARTIFACT_NAME_PREFIX = "harness-results-"
HARNESS_RESULTS_DIRNAME = "perf-harness-results"

# PERF_HARNESS_RESULTS_DIR holds one raw per-benchmark record per
# tests/perf/ module call (e.g. block_gil_contention_drain.json,
# remoteSetRate.json -- 14 files total) PLUS the one aggregated run-record
# scripts/perf_harness_runner.py writes via `--out perf-harness-results/
# run-record.json` (perf_harness.yml's literal invocation): the file
# carrying harness_run_schema_version, the full 13/14-entry `benchmarks`
# mapping, and `build.ccache`/`build.targets`/`build.timing`. Only that
# aggregated file is this driver's concern; a raw per-benchmark record
# carries none of build/ccache/targets/timing and only its own single
# benchmark entry. Named explicitly rather than picked by sorted-glob
# order, since alphabetical order does not reliably put the aggregated
# file first among the per-benchmark siblings it is collected alongside.
RUN_RECORD_FILENAME = "run-record.json"

# The workflow_dispatch input name declared in perf_harness.yml.
INJECTED_LOAD_INPUT = "injected_load"

UNKNOWN_HOST_MODEL = "unknown"
DISPATCH_EVENT = "workflow_dispatch"

SUBPROCESS_TIMEOUT_SECONDS = 30

# Wait between issuing a dispatch and polling for its correlated run.
# Conservative for the same reason scripts/probe_campaign.py's own default
# is conservative: personal-fork Actions quota behavior is unverified, and a
# tight loop is the expensive way to find that out.
DEFAULT_INTERVAL_SECONDS = 300

# Number of distinct CPU models to wait for; matches the 3 host models
# scripts/probe_campaign.py's own campaign actually observed on this same
# hosted-runner fleet, recorded in CAMPAIGN-SETUP.md.
DEFAULT_COVERAGE_TARGET = 3

# The floor: the campaign is not "20 workflow_dispatch runs" until at
# least this many distinct dispatches have been issued.
DEFAULT_DISPATCH_TARGET = 20

# DEFAULT_RUN_CAP derivation: DEFAULT_DISPATCH_TARGET (20, the required floor)
# plus a 20% margin (4 additional dispatches) to absorb failed, cancelled,
# or tree-hash-rejected runs without leaving the campaign short of the
# floor: ceil(20 * 1.2) = 24. This matches scripts/probe_campaign.py's own
# DEFAULT_RUN_CAP for the identical 20-run floor.
DEFAULT_RUN_CAP = 24

# Stopping/reporting conditions. cmd_status can report the two non-terminal
# conditions (a caller has not started, or is mid-campaign); cmd_dispatch's
# loop only ever returns one of the two terminal conditions below it, or
# CONDITION_FAILURE if the gh invocation itself failed, or CONDITION_
# DISPATCHED for a single injected-load dispatch that is not part of the
# bounded loop at all.
CONDITION_NOT_STARTED = "not-started"
CONDITION_IN_PROGRESS = "in-progress"
CONDITION_COVERAGE = "coverage"
CONDITION_CAP = "cap"
CONDITION_FAILURE = "failure"
CONDITION_DISPATCHED = "dispatched"

DEFAULT_SMOKE_TEST_OUT = "docs/plans/perf-ci-hardening/GH-CLI-SMOKE-TEST-HARNESS.md"
SMOKE_TEST_OUTPUT_MAX_CHARS = 4000


def _run_subprocess(argv: list[str]) -> subprocess.CompletedProcess:
    """Injectable module-level default runner for every `gh` call this
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
    ascending and then by database identifier ascending. An entry whose
    creation timestamp does not parse is excluded and counted in the
    returned skipped tally instead of raising, so one malformed entry
    cannot abort a campaign-long listing. Reports an uncorrelated dispatch
    rather than guessing: the caller decides what an empty result means.
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


def cmd_register(
    *,
    repo: str = DEFAULT_REPO,
    workflow_name: str = DEFAULT_WORKFLOW_DISPLAY_NAME,
    runner: Callable[[list[str]], subprocess.CompletedProcess] = _run_subprocess,
) -> dict[str, Any]:
    """Confirm the harness workflow is dispatchable on the fork via `gh
    workflow list`, the registration half of getting this campaign running. Reports a clear
    not-registered result rather than raising when the workflow is absent
    or disabled, and states the fix plainly: push the workflow file to the
    fork's default branch once.
    """
    fix = f"Push {DEFAULT_WORKFLOW} to {repo}'s default branch once so the Actions API registers it."
    argv = ["gh", "workflow", "list", "--repo", repo, "--all"]
    completed = runner(argv)

    if completed.returncode != 0:
        return {
            "registered": False, "state": None,
            "reason": f"gh workflow list exited {completed.returncode}: {(completed.stderr or '').strip()}",
            "fix": fix,
        }

    for line in (completed.stdout or "").splitlines():
        fields = [field.strip() for field in line.split("\t")]
        if not fields or fields[0] != workflow_name:
            continue
        state = fields[1] if len(fields) > 1 else ""
        registered = state == "active"
        return {
            "registered": registered, "state": state, "reason": None,
            "fix": None if registered else fix,
        }

    return {
        "registered": False, "state": None,
        "reason": f"{workflow_name!r} not found in gh workflow list output",
        "fix": fix,
    }


def _dispatch_one(
    *,
    repo: str,
    branch: str,
    workflow: str,
    injected_load: bool,
    runner: Callable[[list[str]], subprocess.CompletedProcess],
    sleep_fn: Callable[[float], None],
    epoch_fn: Callable[[], float],
    interval_seconds: int,
) -> dict[str, Any]:
    """Issue one `gh workflow run` against the frozen campaign branch, wait
    a bounded interval, then correlate the resulting run via `gh run list`.
    Never raises: a dispatch or correlation failure comes back as a result
    field for the caller to act on rather than an exception.
    """
    dispatch_epoch = epoch_fn()
    argv = ["gh", "workflow", "run", workflow, "--repo", repo, "--ref", branch]
    if injected_load:
        argv.extend(["-f", f"{INJECTED_LOAD_INPUT}=true"])

    dispatch_completed = runner(argv)
    result: dict[str, Any] = {
        "run_id": None, "conclusion": None, "status": None, "correlated": False,
        "injected_load": injected_load, "dispatch_exit_code": dispatch_completed.returncode,
    }
    if dispatch_completed.returncode != 0:
        result["dispatch_error"] = (dispatch_completed.stderr or "").strip()
        return result

    sleep_fn(interval_seconds)

    entries, list_error = list_runs(repo, runner=runner)
    if list_error is not None:
        result["list_error"] = list_error
        return result

    correlated, _skipped_timestamps = correlate_runs(entries, branch, dispatch_epoch)
    dispatch_entries = [entry for entry in correlated if entry.get("event") == DISPATCH_EVENT]
    if not dispatch_entries:
        return result

    entry = max(dispatch_entries, key=lambda e: (e.get("createdAt") or "", e.get("databaseId") or 0))
    result.update({
        "run_id": entry.get("databaseId"),
        "conclusion": entry.get("conclusion"),
        "status": entry.get("status"),
        "correlated": True,
    })
    return result


def cmd_dispatch(
    *,
    repo: str = DEFAULT_REPO,
    branch: str = DEFAULT_BRANCH,
    workflow: str = DEFAULT_WORKFLOW,
    dest: Path = Path(DEFAULT_DEST),
    interval_seconds: int = DEFAULT_INTERVAL_SECONDS,
    coverage_target: int = DEFAULT_COVERAGE_TARGET,
    run_cap: int = DEFAULT_RUN_CAP,
    expected_tree_hash: str | None = None,
    injected_load: bool = False,
    status_fn: Callable[[], int] | None = None,
    runner: Callable[[list[str]], subprocess.CompletedProcess] = _run_subprocess,
    sleep_fn: Callable[[float], None] = time.sleep,
    epoch_fn: Callable[[], float] = time.time,
) -> dict[str, Any]:
    """Drive the campaign's dispatch half.

    With `injected_load=True`, issues exactly one dispatch carrying the
    `injected_load` input set true for the contamination demonstration, and returns without entering
    the bounded loop at all; callers must not make this the default and
    must not call it more than once per campaign.

    Otherwise runs the bounded loop: dispatch one `workflow_dispatch` run,
    wait, correlate it, and repeat. Every dispatched run is counted in the
    total regardless of its conclusion (a failed or cancelled run stays in
    the count with its conclusion recorded rather than being dropped), and
    the loop stops on whichever of two conditions fires first: the observed
    distinct CPU-model count reaching `coverage_target`, or the number of
    runs this call has dispatched reaching `run_cap`. A failed `gh workflow
    run` invocation itself stops the loop immediately with its exit code
    recorded.

    The coverage figure is read via `status_fn`, which defaults to
    `cmd_status`'s own collected-records read (the same function the
    standalone `status` subcommand calls), so this loop's stopping
    condition and that subcommand's report can never disagree about the
    observed model count.
    """
    if status_fn is None:
        def status_fn() -> int:
            return cmd_status(
                dest, coverage_target=coverage_target, run_cap=run_cap,
                expected_tree_hash=expected_tree_hash,
            )["distinct_host_models"]

    if injected_load:
        record = _dispatch_one(
            repo=repo, branch=branch, workflow=workflow, injected_load=True,
            runner=runner, sleep_fn=sleep_fn, epoch_fn=epoch_fn, interval_seconds=interval_seconds,
        )
        condition = CONDITION_DISPATCHED if record["dispatch_exit_code"] == 0 else CONDITION_FAILURE
        return {
            "condition": condition, "dispatched": [record],
            "injected_load_run_id": record.get("run_id"),
        }

    dispatched: list[dict[str, Any]] = []

    while True:
        distinct_host_models = status_fn()

        if distinct_host_models >= coverage_target:
            return {
                "condition": CONDITION_COVERAGE, "dispatched": dispatched,
                "dispatched_count": len(dispatched), "distinct_host_models": distinct_host_models,
            }
        if len(dispatched) >= run_cap:
            return {
                "condition": CONDITION_CAP, "dispatched": dispatched,
                "dispatched_count": len(dispatched), "distinct_host_models": distinct_host_models,
            }

        record = _dispatch_one(
            repo=repo, branch=branch, workflow=workflow, injected_load=False,
            runner=runner, sleep_fn=sleep_fn, epoch_fn=epoch_fn, interval_seconds=interval_seconds,
        )
        if record["dispatch_exit_code"] != 0:
            return {
                "condition": CONDITION_FAILURE, "dispatched": dispatched,
                "dispatched_count": len(dispatched), "distinct_host_models": distinct_host_models,
                "dispatch_exit_code": record["dispatch_exit_code"],
            }
        dispatched.append(record)


def download_run_artifacts(
    repo: str,
    run_id: Any,
    runner: Callable[[list[str]], subprocess.CompletedProcess] = _run_subprocess,
) -> Path | None:
    """Download every artifact attached to one run into a scratch temporary
    directory, returning its path, or None on a nonzero exit. The workflow
    uploads exactly one artifact per run, so no artifact-name argument and
    no separate artifact-listing call are needed: omitting `-n` on `gh run
    download` fetches everything the run produced, matching the literal
    collection command already proven in HARNESS-SETUP.md.
    """
    tmp_dir = Path(tempfile.mkdtemp(prefix="perf-harness-campaign-"))
    argv = ["gh", "run", "download", str(run_id), "--repo", repo, "--dir", str(tmp_dir)]
    completed = runner(argv)
    if completed.returncode != 0:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return None
    return tmp_dir


def _find_harness_json_files(root: Path) -> list[Path]:
    """The aggregated run-record lives at `HARNESS_RESULTS_DIRNAME
    /RUN_RECORD_FILENAME` inside the downloaded artifact, beside 13-14 raw
    per-benchmark sibling files (from each tests/perf/ module's own
    _perf_harness.emit_harness_result call) and an unrelated Tier 3
    `perf-results/` directory the same artifact carries. Only the
    aggregated file is this driver's concern: a raw per-benchmark sibling
    carries no `build` block and only one `benchmarks` entry, so collecting
    one of those instead (as an earlier, alphabetical-sort-order version of
    this function did) would silently drop every other benchmark and all
    build/ccache evidence from the committed record.
    """
    return sorted(root.glob(f"**/{HARNESS_RESULTS_DIRNAME}/{RUN_RECORD_FILENAME}"))


def _destination_filename(run_id: Any, source_name: str) -> str:
    return f"{run_id}-{source_name}"


def cmd_collect(
    *,
    repo: str = DEFAULT_REPO,
    branch: str = DEFAULT_BRANCH,
    dest: Path = Path(DEFAULT_DEST),
    since_epoch: float = 0.0,
    expected_tree_hash: str | None,
    limit: int = DEFAULT_LIST_LIMIT,
    runner: Callable[[list[str]], subprocess.CompletedProcess] = _run_subprocess,
    downloader: Callable[..., "Path | None"] = download_run_artifacts,
) -> dict[str, Any]:
    """List, correlate, and idempotently download this campaign's harness
    artifacts.

    `expected_tree_hash` is required: omitting it is a caller bug, not an
    invitation to accept every record sight unseen, so this raises
    rather than defaulting to accept-anything. Collection is idempotent by
    run-id-derived destination filename: a run already present on disk is
    reported as already collected rather than re-downloaded. A downloaded
    record whose `run.git_tree_hash` differs from `expected_tree_hash` is
    rejected with the reason recorded (matching
    `perf_campaign_report.TREE_HASH_MISMATCH`, so this driver's accounting
    and the report's population accounting agree) and is never written to
    `dest`. A missing, empty, or unparseable artifact is recorded as
    skipped with its reason, and collection continues with the remaining
    runs.
    """
    if not expected_tree_hash:
        raise ValueError(
            "expected_tree_hash is required; an omitted hash would accept every "
            "record regardless of code state"
        )

    entries, list_error = list_runs(repo, limit=limit, runner=runner)
    if list_error is not None:
        return {
            "exit_code": 1, "reason": "list-failed", "collected": 0,
            "already_present": 0, "rejected": [], "skipped": [], "skipped_timestamps": 0,
        }

    correlated, skipped_timestamps = correlate_runs(entries, branch, since_epoch)
    correlated = [entry for entry in correlated if entry.get("event") == DISPATCH_EVENT]

    if not correlated:
        return {
            "exit_code": 1, "reason": "no-runs-found", "collected": 0,
            "already_present": 0, "rejected": [], "skipped": [],
            "skipped_timestamps": skipped_timestamps,
        }

    dest.mkdir(parents=True, exist_ok=True)

    collected = 0
    already_present = 0
    rejected: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    for entry in correlated:
        run_id = entry.get("databaseId")

        if list(dest.glob(f"{run_id}-*.json")):
            already_present += 1
            continue

        artifact_root = downloader(repo, run_id, runner)
        if artifact_root is None:
            skipped.append({"run_id": run_id, "reason": "artifact download failed"})
            continue

        try:
            harness_files = _find_harness_json_files(Path(artifact_root))
            if not harness_files:
                skipped.append({"run_id": run_id, "reason": f"no {RUN_RECORD_FILENAME} present"})
                continue

            source_path = harness_files[0]
            try:
                raw_text = source_path.read_text(encoding="utf-8")
            except OSError as exc:
                skipped.append({"run_id": run_id, "reason": f"unreadable artifact: {exc}"})
                continue
            if not raw_text.strip():
                skipped.append({"run_id": run_id, "reason": "empty artifact"})
                continue

            record = perf_campaign_report.load_harness_run(source_path)
            if record is None:
                skipped.append({"run_id": run_id, "reason": "unparseable or unrecognized schema version"})
                continue

            run_info = record.get("run")
            run_info = run_info if isinstance(run_info, dict) else {}
            actual_tree_hash = run_info.get("git_tree_hash")
            if actual_tree_hash != expected_tree_hash:
                rejected.append({
                    "run_id": run_id, "reason": perf_campaign_report.TREE_HASH_MISMATCH,
                    "expected_tree_hash": expected_tree_hash, "actual_tree_hash": actual_tree_hash,
                })
                continue

            dest_path = dest / _destination_filename(run_id, source_path.name)
            dest_path.write_text(raw_text, encoding="utf-8")
            collected += 1
        finally:
            shutil.rmtree(artifact_root, ignore_errors=True)

    return {
        "exit_code": 0, "reason": "collected", "collected": collected,
        "already_present": already_present, "rejected": rejected, "skipped": skipped,
        "skipped_timestamps": skipped_timestamps,
    }


def cmd_status(
    dest: Path,
    *,
    coverage_target: int = DEFAULT_COVERAGE_TARGET,
    run_cap: int = DEFAULT_RUN_CAP,
    expected_tree_hash: str | None = None,
) -> dict[str, Any]:
    """Read the collected records under `dest` once, reporting the
    collected count, the distinct CPU models observed with a count each,
    the rejected count with reasons, the skipped count with reasons, and
    which run id (if any) carries the injected-load label. A missing or
    empty destination directory reports zero runs and the not-yet-started
    condition without raising, so `cmd_dispatch` can poll this before the
    first dispatch has ever landed.

    `cmd_dispatch`'s stopping condition calls this same function for its
    coverage figure, so the loop and this standalone report can never
    disagree about it.
    """
    if not dest.is_dir():
        return {
            "collected_count": 0, "host_models": {}, "distinct_host_models": 0,
            "rejected_count": 0, "rejected": [], "skipped_count": 0, "skipped": [],
            "injected_load_run_id": None, "condition": CONDITION_NOT_STARTED,
        }

    host_models: dict[str, int] = {}
    rejected: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    collected_count = 0
    injected_load_run_id = None

    for path in sorted(dest.glob("*.json")):
        record = perf_campaign_report.load_harness_run(path)
        if record is None:
            skipped.append({"path": str(path), "reason": "missing, empty, or unparseable"})
            continue

        run_info = record.get("run")
        run_info = run_info if isinstance(run_info, dict) else {}
        run_id = run_info.get("github_run_id", path.stem.split("-", 1)[0])

        if expected_tree_hash is not None and run_info.get("git_tree_hash") != expected_tree_hash:
            rejected.append({
                "path": str(path), "run_id": run_id, "reason": perf_campaign_report.TREE_HASH_MISMATCH,
            })
            continue

        collected_count += 1

        if str(run_info.get("injected_load")).lower() == "true":
            injected_load_run_id = run_id

        environment = record.get("environment")
        environment = environment if isinstance(environment, dict) else {}
        model = environment.get("cpu_model") or UNKNOWN_HOST_MODEL
        host_models[model] = host_models.get(model, 0) + 1

    distinct_host_models = len(host_models)
    if collected_count == 0:
        condition = CONDITION_NOT_STARTED
    elif distinct_host_models >= coverage_target:
        condition = CONDITION_COVERAGE
    elif collected_count >= run_cap:
        condition = CONDITION_CAP
    else:
        condition = CONDITION_IN_PROGRESS

    return {
        "collected_count": collected_count, "host_models": host_models,
        "distinct_host_models": distinct_host_models,
        "rejected_count": len(rejected), "rejected": rejected,
        "skipped_count": len(skipped), "skipped": skipped,
        "injected_load_run_id": injected_load_run_id,
        "condition": condition,
    }


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
        "<!-- generated by scripts/perf_harness_campaign.py smoke-test, do not edit by hand -->",
        "# gh CLI Harness Campaign Smoke Test (generated)",
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
    runner: Callable[[list[str]], subprocess.CompletedProcess] = _run_subprocess,
    out_path: Path = Path(DEFAULT_SMOKE_TEST_OUT),
) -> dict[str, Any]:
    """Record the outcome of each gh capability this campaign driver depends
    on against the installed `gh`: `workflow list`, `workflow run` (which also
    exercises the `workflow_dispatch` input surface via the `injected_load`
    input), `run list`, `run view`, and `run download`. Each command, exit
    code, and a bounded output summary is recorded with a pass/fail verdict,
    into `DEFAULT_SMOKE_TEST_OUT`, a filename of this module's own rather
    than either smoke-test record Phase 2 already committed under
    docs/plans/perf-ci-hardening/. A failing operation is recorded and the
    remaining operations still run, since a partial record is more useful
    than none.
    """
    operations: list[dict[str, Any]] = []

    workflow_list_argv = ["gh", "workflow", "list", "--repo", repo, "--all"]
    operations.append(_record_operation("workflow list", workflow_list_argv, runner(workflow_list_argv)))

    dispatch_argv = [
        "gh", "workflow", "run", workflow, "--repo", repo, "--ref", branch,
        "-f", f"{INJECTED_LOAD_INPUT}=false",
    ]
    operations.append(_record_operation("workflow run", dispatch_argv, runner(dispatch_argv)))

    list_argv = [
        "gh", "run", "list", "--repo", repo,
        "--json", ",".join(GH_RUN_LIST_FIELDS), "--limit", "20",
    ]
    run_list_completed = runner(list_argv)
    operations.append(_record_operation("run list", list_argv, run_list_completed))

    view_run_id: Any = None
    try:
        entries = json.loads(run_list_completed.stdout or "[]")
        if isinstance(entries, list) and entries:
            view_run_id = entries[0].get("databaseId")
    except json.JSONDecodeError:
        view_run_id = None

    view_argv = ["gh", "run", "view", str(view_run_id if view_run_id is not None else ""), "--repo", repo]
    operations.append(_record_operation("run view", view_argv, runner(view_argv)))

    download_dir = tempfile.mkdtemp(prefix="perf-harness-campaign-smoke-")
    download_argv = [
        "gh", "run", "download", str(view_run_id if view_run_id is not None else ""),
        "--repo", repo, "--dir", download_dir,
    ]
    operations.append(_record_operation("run download", download_argv, runner(download_argv)))
    shutil.rmtree(download_dir, ignore_errors=True)

    markdown = _render_smoke_test_markdown(operations)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(markdown, encoding="utf-8")

    return {"operations": operations, "out_path": str(out_path)}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    register = subparsers.add_parser(
        "register", help="Confirm the harness workflow is dispatchable on the fork",
    )
    register.add_argument("--repo", default=DEFAULT_REPO)
    register.add_argument("--workflow-name", default=DEFAULT_WORKFLOW_DISPLAY_NAME)

    dispatch = subparsers.add_parser(
        "dispatch", help="Dispatch workflow_dispatch runs until a stopping condition fires",
    )
    dispatch.add_argument("--repo", default=DEFAULT_REPO)
    dispatch.add_argument("--branch", default=DEFAULT_BRANCH)
    dispatch.add_argument("--workflow", default=DEFAULT_WORKFLOW)
    dispatch.add_argument("--dest", default=DEFAULT_DEST)
    dispatch.add_argument("--interval-seconds", type=int, default=DEFAULT_INTERVAL_SECONDS)
    dispatch.add_argument("--coverage-target", type=int, default=DEFAULT_COVERAGE_TARGET)
    dispatch.add_argument("--run-cap", type=int, default=DEFAULT_RUN_CAP)
    dispatch.add_argument(
        "--tree-hash", default=None,
        help="Expected git tree hash, forwarded to the default status_fn's cmd_status read",
    )
    dispatch.add_argument(
        "--injected-load", action="store_true",
        help="Issue exactly one dispatch with the injected_load input set true, "
        "for the contamination demonstration",
    )

    collect = subparsers.add_parser(
        "collect", help="Correlate this campaign's runs and download their artifacts idempotently",
    )
    collect.add_argument("--repo", default=DEFAULT_REPO)
    collect.add_argument("--branch", default=DEFAULT_BRANCH)
    collect.add_argument("--dest", default=DEFAULT_DEST)
    collect.add_argument(
        "--tree-hash", required=True,
        help="Expected git tree hash for population membership (required, no accept-anything default)",
    )

    status = subparsers.add_parser(
        "status", help="Report the currently collected runs and the stopping condition",
    )
    status.add_argument("--dest", default=DEFAULT_DEST)
    status.add_argument("--coverage-target", type=int, default=DEFAULT_COVERAGE_TARGET)
    status.add_argument("--run-cap", type=int, default=DEFAULT_RUN_CAP)
    status.add_argument("--tree-hash", default=None)

    smoke_test = subparsers.add_parser(
        "smoke-test", help="Run every INTEGRATE gh operation once each and record the outcome",
    )
    smoke_test.add_argument("--repo", default=DEFAULT_REPO)
    smoke_test.add_argument("--branch", default=DEFAULT_BRANCH)
    smoke_test.add_argument("--workflow", default=DEFAULT_WORKFLOW)
    smoke_test.add_argument("--out", default=DEFAULT_SMOKE_TEST_OUT)

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if args.command == "register":
        result = cmd_register(repo=args.repo, workflow_name=args.workflow_name)
        print(f"registered: {result['registered']} state: {result['state']}")
        if not result["registered"]:
            print(f"fix: {result['fix']}")
        return 0 if result["registered"] else 1

    if args.command == "dispatch":
        result = cmd_dispatch(
            repo=args.repo, branch=args.branch, workflow=args.workflow, dest=Path(args.dest),
            interval_seconds=args.interval_seconds, coverage_target=args.coverage_target,
            run_cap=args.run_cap, expected_tree_hash=args.tree_hash, injected_load=args.injected_load,
        )
        print(f"condition: {result['condition']}")
        return 0 if result["condition"] != CONDITION_FAILURE else 1

    if args.command == "collect":
        result = cmd_collect(
            repo=args.repo, branch=args.branch, dest=Path(args.dest),
            expected_tree_hash=args.tree_hash,
        )
        print(
            f"collected: {result['collected']} already_present: {result['already_present']} "
            f"rejected: {len(result['rejected'])} skipped: {len(result['skipped'])}"
        )
        return result["exit_code"]

    if args.command == "status":
        result = cmd_status(
            Path(args.dest), coverage_target=args.coverage_target,
            run_cap=args.run_cap, expected_tree_hash=args.tree_hash,
        )
        print(f"collected_count: {result['collected_count']}")
        print(f"distinct_host_models: {result['distinct_host_models']}")
        for model, count in sorted(result["host_models"].items()):
            print(f"  {model}: {count}")
        print(f"rejected_count: {result['rejected_count']}")
        print(f"skipped_count: {result['skipped_count']}")
        print(f"injected_load_run_id: {result['injected_load_run_id']}")
        print(f"condition: {result['condition']}")
        return 0

    if args.command == "smoke-test":
        result = cmd_smoke_test(
            repo=args.repo, branch=args.branch, workflow=args.workflow, out_path=Path(args.out),
        )
        for operation in result["operations"]:
            print(f"{operation['operation']}: {operation['verdict']} (exit {operation['exit_code']})")
        return 0 if all(op["verdict"] == "pass" for op in result["operations"]) else 1

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
