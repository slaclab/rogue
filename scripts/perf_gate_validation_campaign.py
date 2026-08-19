#!/usr/bin/env python3
# ----------------------------------------------------------------------------
# Title      : ROGUE Perf Gate Validation Campaign Driver
# ----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
# ----------------------------------------------------------------------------

"""Drive the perf gate validation campaign against the fork.

Dispatches the paired A/B validation workflow
(.github/workflows/perf_gate_validation.yml) once per declared run category,
correlates and idempotently collects the resulting two-leg records and their
verdict sidecars, rejects a collected run whose measured tree-hash pair
contradicts its own declared pair, and reports the population against its
stopping conditions.

This module never uses the raw GitHub API endpoint helper: every operation
goes through the CLI's own subcommands (`gh workflow run`, `gh run list`,
`gh run download`), exactly like scripts/perf_harness_campaign.py, whose
`GH_RUN_LIST_FIELDS`, `correlate_runs`, `list_runs`, `cmd_register`, and
`download_run_artifacts` this driver reuses unchanged as flat sibling
imports rather than reimplementing them.

A run's category comes from its own declared `label` field, set as a
workflow_dispatch input before the run is issued, never from its outcome,
its conclusion, or the order it was collected in. Rejection is per run
against that run's own declared candidate/merge-base tree-hash pair, not
against one campaign-wide expected hash, and the comparison is recomputed
from the record's own fields rather than trusting the record's own
self-reported match flag.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import perf_campaign_report  # noqa: E402  (flat sibling import, path inserted above)
import perf_gate_ab_runner  # noqa: E402  (flat sibling import, path inserted above)
import perf_gate_evaluator  # noqa: E402  (flat sibling import, path inserted above)
import perf_harness_campaign  # noqa: E402  (flat sibling import, path inserted above)

# Reused unchanged, never reimplemented (see module docstring).
GH_RUN_LIST_FIELDS = perf_harness_campaign.GH_RUN_LIST_FIELDS
CREATED_AT_FORMAT = perf_harness_campaign.CREATED_AT_FORMAT
_parse_created_at = perf_harness_campaign._parse_created_at
correlate_runs = perf_harness_campaign.correlate_runs
list_runs = perf_harness_campaign.list_runs
cmd_register = perf_harness_campaign.cmd_register
download_run_artifacts = perf_harness_campaign.download_run_artifacts
DISPATCH_EVENT = perf_harness_campaign.DISPATCH_EVENT
UNKNOWN_HOST_MODEL = perf_harness_campaign.UNKNOWN_HOST_MODEL

VALID_MODES = perf_gate_ab_runner.VALID_MODES
SHA_PATTERN = perf_gate_ab_runner.SHA_PATTERN

VERDICT_PASS = perf_gate_evaluator.VERDICT_PASS
VERDICT_FAIL = perf_gate_evaluator.VERDICT_FAIL
VERDICT_INCONCLUSIVE = perf_gate_evaluator.VERDICT_INCONCLUSIVE

TREE_HASH_MISMATCH = perf_campaign_report.TREE_HASH_MISMATCH

DEFAULT_REPO = "ruck314/rogue"
# perf-gate/validation carries the pre-fix workflow and pre-fix runner and is
# deliberately frozen so the run already collected against it stays
# attributable; the corrected CCACHE_BASEDIR mechanism (plan 04-05a) lives on
# this second, separately frozen branch instead. A campaign must dispatch
# against the corrected mechanism, never the pre-fix branch.
DEFAULT_BRANCH = "perf-gate/validation-v2"
DEFAULT_WORKFLOW = "perf_gate_validation.yml"
DEFAULT_WORKFLOW_DISPLAY_NAME = "Rogue Perf Gate Validation"
DEFAULT_DEST = "docs/plans/perf-ci-hardening/gate-validation-runs"

# Measured reason (scripts/perf_harness_campaign.py's own campaign finding):
# GitHub queues and runs workflow_dispatch runs against a shared pool
# concurrently, producing 24 dispatches in about 8 minutes rather than the
# roughly 2 hours a serial 300 second interval would take.
DEFAULT_INTERVAL_SECONDS = 20

DEFAULT_COVERAGE_TARGET = 3
DEFAULT_DISPATCH_TARGET = 20
# DEFAULT_RUN_CAP derivation: DEFAULT_DISPATCH_TARGET (20) plus a 20% margin
# (4 additional dispatches) to absorb failed, cancelled, or
# tree-hash-pair-rejected runs without leaving the campaign short of the
# floor: ceil(20 * 1.2) = 24. Matches perf_harness_campaign.DEFAULT_RUN_CAP's
# own derivation for the identical floor.
DEFAULT_RUN_CAP = 24
# Three confirming runs at the smallest detected magnitude is sufficient for
# an exact-equality gate rule: flakiness surfaces as an INCONCLUSIVE verdict
# rather than as a missed detection, and a single run per magnitude cannot
# distinguish a real detection from a coincidence.
DEFAULT_CONFIRMING_RUNS = 3
DEFAULT_ROUNDS = 2

LABEL_NULL = "null-population"
LABEL_UNRELATED = "unrelated-population"
LABEL_SEEDED_SEARCH = "seeded-search"
LABEL_SEEDED_CONFIRM = "seeded-confirm"
LABEL_FORCED_INCONCLUSIVE = "forced-inconclusive"
VALID_LABELS: tuple[str, ...] = (
    LABEL_NULL, LABEL_UNRELATED, LABEL_SEEDED_SEARCH, LABEL_SEEDED_CONFIRM, LABEL_FORCED_INCONCLUSIVE,
)

CATEGORY_PATCH_FAILED = "patch-failed"
CATEGORY_UNCATEGORIZED = "uncategorized"

# The workflow_dispatch modules input value meaning "keep the runner's own
# default module set" (perf_harness_runner.DEFAULT_PERF_MODULES). This
# driver never expands the sentinel into that list itself: doing so would
# create a second source of truth for the default set beside the harness
# runner's own constant, and the two could drift.
MODULES_INPUT_ALL = "all"

# The known subpath inside the uploaded artifact holding the aggregated
# two-leg record and its verdict sidecar (perf_gate_validation.yml's own
# `gate-validation-results/{ab-record,verdict}.json`). Discovery globs this
# known subpath rather than sorting a directory listing and taking the
# first entry, because an earlier harness-campaign version of that mistake
# silently dropped 13 of 14 benchmarks and all build evidence from every
# collected record by selecting the alphabetically first per-benchmark file
# instead of the aggregated one.
GATE_RECORD_DIRNAME = "gate-validation-results"
GATE_RECORD_FILENAME = "ab-record.json"
VERDICT_RECORD_FILENAME = "verdict.json"

SUBPROCESS_TIMEOUT_SECONDS = 30

CONDITION_NOT_STARTED = "not-started"
CONDITION_IN_PROGRESS = "in-progress"
CONDITION_COVERAGE = "coverage"
CONDITION_CAP = "cap"
CONDITION_FAILURE = "failure"


def _run_subprocess(argv: list[str]) -> subprocess.CompletedProcess:
    """Injectable module-level default runner for every `gh` call this
    module makes. Never raises: a missing binary or a timeout comes back as
    a nonzero-returncode result instead, matching
    perf_harness_campaign._run_subprocess's own convention."""
    try:
        return subprocess.run(
            argv, capture_output=True, text=True, timeout=SUBPROCESS_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return subprocess.CompletedProcess(argv, returncode=1, stdout="", stderr=str(exc))


def _validate_dispatch_inputs(
    candidate_ref: str, merge_base_ref: str, mode: str, label: str,
    modules: str = MODULES_INPUT_ALL,
) -> str | None:
    """Reject a malformed ref, mode, label, or module set before any
    subprocess runs. Returns None when every input is acceptable, or a
    bounded reason string naming the first rejected input otherwise. Reuses
    perf_gate_ab_runner.SHA_PATTERN, perf_gate_ab_runner.VALID_MODES, and
    perf_gate_ab_runner.PERF_MODULE_PATTERN so this driver and the runner
    cannot drift on what is acceptable: the module check is the runner's own
    compiled pattern applied per comma-separated element, never a second
    copy of that expression."""
    if not SHA_PATTERN.match(candidate_ref):
        return "candidate_ref is not a 40-character lowercase hex git sha"
    if not SHA_PATTERN.match(merge_base_ref):
        return "merge_base_ref is not a 40-character lowercase hex git sha"
    if mode not in VALID_MODES:
        return f"mode {mode!r} is not one of {VALID_MODES}"
    if label not in VALID_LABELS:
        return f"label {label!r} is not one of {VALID_LABELS}"
    if modules != MODULES_INPUT_ALL:
        elements = [element.strip() for element in modules.split(",")]
        if not all(perf_gate_ab_runner.PERF_MODULE_PATTERN.match(element) for element in elements):
            return f"modules {modules!r} does not match the runner's own module pattern"
    return None


def _dispatch_one(
    *,
    repo: str,
    branch: str,
    workflow: str,
    candidate_ref: str,
    merge_base_ref: str,
    mode: str,
    patch_name: str | None,
    patch_magnitude: str | None,
    forced_condition: str | None,
    rounds: int,
    label: str,
    modules: str = MODULES_INPUT_ALL,
    runner: Callable[[list[str]], subprocess.CompletedProcess],
    sleep_fn: Callable[[float], None],
    epoch_fn: Callable[[], float],
    interval_seconds: int,
) -> dict[str, Any]:
    """Issue one `gh workflow run` carrying every one of the nine workflow
    inputs as a separate argument, wait a bounded interval, then correlate
    the resulting run by branch plus the dispatch epoch through the reused
    `correlate_runs` and `list_runs`. Never parses the dispatch command's
    own stdout for a run id, since the installed `gh` version prints
    neither a run id nor a URL. Never raises: a dispatch or correlation
    failure comes back as a result field for the caller to act on."""
    validation_error = _validate_dispatch_inputs(candidate_ref, merge_base_ref, mode, label, modules)
    if validation_error is not None:
        return {
            "run_id": None, "conclusion": None, "status": None, "correlated": False,
            "label": label, "mode": mode, "dispatch_exit_code": 1,
            "dispatch_error": validation_error,
        }

    dispatch_epoch = epoch_fn()
    argv = ["gh", "workflow", "run", workflow, "--repo", repo, "--ref", branch]
    for name, value in (
        ("candidate_ref", candidate_ref),
        ("merge_base_ref", merge_base_ref),
        ("mode", mode),
        ("patch_name", patch_name if patch_name is not None else "none"),
        ("patch_magnitude", patch_magnitude if patch_magnitude is not None else "0"),
        ("forced_condition", forced_condition if forced_condition is not None else "none"),
        ("rounds", str(rounds)),
        ("label", label),
        ("modules", modules),
    ):
        argv.extend(["-f", f"{name}={value}"])

    dispatch_completed = runner(argv)
    result: dict[str, Any] = {
        "run_id": None, "conclusion": None, "status": None, "correlated": False,
        "label": label, "mode": mode, "dispatch_exit_code": dispatch_completed.returncode,
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


def cmd_status(
    dest: Path,
    *,
    coverage_target: int = DEFAULT_COVERAGE_TARGET,
    run_cap: int = DEFAULT_RUN_CAP,
) -> dict[str, Any]:
    """Read the collected records under `dest` once, reporting the
    collected count, the distinct CPU models with a count each, the
    per-category counts derived from each record's own `run.label` field,
    the rejected count with reasons, the skipped count with reasons, the
    uncategorized count, and the stopping condition. A missing or empty
    destination directory returns zeros and the not-started condition
    without raising, so `cmd_dispatch` can poll this before the first
    dispatch has ever landed.

    A record's category is derived from `run.label` when that label is a
    member of VALID_LABELS; a record that requested a patch
    (`run.patch_name` set) whose `run.patch_applied` is false is promoted
    to CATEGORY_PATCH_FAILED regardless of its label, because a patch that
    did not apply measured nothing about the gate. A record that never
    requested a patch at all (the null, unrelated, and forced-inconclusive
    categories never set `patch_name`) also carries `patch_applied: false`
    on every real record, but that is "no patch was asked for", not "a
    patch failed", so it is never promoted on that basis alone. Anything
    else is reported as CATEGORY_UNCATEGORIZED with the observed label
    value recorded, rather than silently folded into the null population.

    A collected record whose measured tree-hash pair does not match its
    own declared pair is rejected here too, even though `cmd_collect`
    already filters at collection time: `dest` may also hold a record
    placed there by hand (see docs/plans/perf-ci-hardening/
    GATE-VALIDATION-SETUP.md's own collection commands), so this read
    re-checks rather than trusting that every file on disk already passed
    that filter.
    """
    if not dest.is_dir():
        return {
            "collected_count": 0, "host_models": {}, "distinct_host_models": 0,
            "categories": {}, "rejected_count": 0, "rejected": [],
            "skipped_count": 0, "skipped": [], "uncategorized_count": 0,
            "uncategorized": [], "condition": CONDITION_NOT_STARTED,
        }

    host_models: dict[str, int] = {}
    categories: dict[str, int] = {}
    rejected: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    uncategorized: list[dict[str, Any]] = []
    collected_count = 0

    for path in sorted(dest.glob(f"*-{GATE_RECORD_FILENAME}")):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            skipped.append({"path": str(path), "reason": f"unreadable: {exc}"})
            continue
        if not text.strip():
            skipped.append({"path": str(path), "reason": "empty file"})
            continue
        try:
            record = json.loads(text)
        except json.JSONDecodeError as exc:
            skipped.append({"path": str(path), "reason": f"unparseable: {exc}"})
            continue
        if not isinstance(record, dict):
            skipped.append({"path": str(path), "reason": "non-mapping JSON payload"})
            continue

        run_info = record.get("run")
        run_info = run_info if isinstance(run_info, dict) else {}
        run_id = run_info.get("github_run_id", path.stem.split("-", 1)[0])

        mismatch = _tree_hash_pair_mismatch(record)
        if mismatch is not None:
            rejected.append({"path": str(path), "run_id": run_id, "reason": TREE_HASH_MISMATCH, **mismatch})
            continue

        collected_count += 1

        label = run_info.get("label")
        if run_info.get("patch_name") and run_info.get("patch_applied") is False:
            category = CATEGORY_PATCH_FAILED
        elif label in VALID_LABELS:
            category = label
        else:
            category = CATEGORY_UNCATEGORIZED
            uncategorized.append({"path": str(path), "run_id": run_id, "label": label})
        categories[category] = categories.get(category, 0) + 1

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
        "distinct_host_models": distinct_host_models, "categories": categories,
        "rejected_count": len(rejected), "rejected": rejected,
        "skipped_count": len(skipped), "skipped": skipped,
        "uncategorized_count": len(uncategorized), "uncategorized": uncategorized,
        "condition": condition,
    }


def cmd_dispatch(
    *,
    repo: str = DEFAULT_REPO,
    branch: str = DEFAULT_BRANCH,
    workflow: str = DEFAULT_WORKFLOW,
    dest: Path = Path(DEFAULT_DEST),
    interval_seconds: int = DEFAULT_INTERVAL_SECONDS,
    coverage_target: int = DEFAULT_COVERAGE_TARGET,
    run_cap: int = DEFAULT_RUN_CAP,
    candidate_ref: str = "",
    merge_base_ref: str = "",
    mode: str = perf_gate_ab_runner.MODE_NULL,
    patch_name: str | None = None,
    patch_magnitude: str | None = None,
    forced_condition: str | None = None,
    rounds: int = DEFAULT_ROUNDS,
    label: str = LABEL_NULL,
    status_fn: Callable[[], int] | None = None,
    runner: Callable[[list[str]], subprocess.CompletedProcess] = _run_subprocess,
    sleep_fn: Callable[[float], None] = time.sleep,
    epoch_fn: Callable[[], float] = time.time,
) -> dict[str, Any]:
    """Drive the campaign's bounded dispatch loop: dispatch one
    workflow_dispatch run carrying `label` (setting its category before it
    runs), wait, correlate it, and repeat. Every dispatched run is counted
    in the total regardless of its conclusion -- a failed or cancelled run
    stays in the count with its conclusion recorded rather than being
    dropped -- and the loop stops on whichever of three conditions fires
    first: the observed distinct CPU-model count reaching `coverage_target`,
    the number of runs this call has dispatched reaching `run_cap`, or a
    failed `gh workflow run` invocation itself (recorded with its exit
    code, with the runs already dispatched staying in the returned list).

    The coverage figure is read via `status_fn`, which defaults to a
    closure over `cmd_status`'s own collected-records read (the same
    function the standalone `status` subcommand calls), so this loop's
    stopping condition and that subcommand's report can never disagree.
    """
    if status_fn is None:
        def status_fn() -> int:
            return cmd_status(dest, coverage_target=coverage_target, run_cap=run_cap)["distinct_host_models"]

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
            repo=repo, branch=branch, workflow=workflow,
            candidate_ref=candidate_ref, merge_base_ref=merge_base_ref, mode=mode,
            patch_name=patch_name, patch_magnitude=patch_magnitude, forced_condition=forced_condition,
            rounds=rounds, label=label,
            runner=runner, sleep_fn=sleep_fn, epoch_fn=epoch_fn, interval_seconds=interval_seconds,
        )
        if record["dispatch_exit_code"] != 0:
            return {
                "condition": CONDITION_FAILURE, "dispatched": dispatched,
                "dispatched_count": len(dispatched), "distinct_host_models": distinct_host_models,
                "dispatch_exit_code": record["dispatch_exit_code"],
            }
        dispatched.append(record)


def cmd_sweep(
    patch_name: str,
    magnitudes: list[str],
    *,
    repo: str = DEFAULT_REPO,
    branch: str = DEFAULT_BRANCH,
    workflow: str = DEFAULT_WORKFLOW,
    candidate_ref: str = "",
    merge_base_ref: str = "",
    rounds: int = DEFAULT_ROUNDS,
    modules: str = MODULES_INPUT_ALL,
    runner: Callable[[list[str]], subprocess.CompletedProcess] = _run_subprocess,
    sleep_fn: Callable[[float], None] = time.sleep,
    epoch_fn: Callable[[], float] = time.time,
    interval_seconds: int = DEFAULT_INTERVAL_SECONDS,
) -> list[dict[str, Any]]:
    """Dispatch one run per magnitude, in the given order, each labelled
    LABEL_SEEDED_SEARCH and each carrying `patch_name`, that magnitude, and
    the module set. Returns the dispatch list. Makes no judgement about
    whether any magnitude was detected: deciding which magnitude was the
    smallest detected one is the report generator's job, since that
    decision reads verdicts and determinism evidence this driver does not
    interpret."""
    dispatched: list[dict[str, Any]] = []
    for magnitude in magnitudes:
        record = _dispatch_one(
            repo=repo, branch=branch, workflow=workflow,
            candidate_ref=candidate_ref, merge_base_ref=merge_base_ref, mode=perf_gate_ab_runner.MODE_SEEDED,
            patch_name=patch_name, patch_magnitude=magnitude, forced_condition=None,
            rounds=rounds, label=LABEL_SEEDED_SEARCH, modules=modules,
            runner=runner, sleep_fn=sleep_fn, epoch_fn=epoch_fn, interval_seconds=interval_seconds,
        )
        dispatched.append(record)
    return dispatched


def cmd_confirm(
    patch_name: str,
    magnitude: str,
    count: int = DEFAULT_CONFIRMING_RUNS,
    *,
    repo: str = DEFAULT_REPO,
    branch: str = DEFAULT_BRANCH,
    workflow: str = DEFAULT_WORKFLOW,
    candidate_ref: str = "",
    merge_base_ref: str = "",
    rounds: int = DEFAULT_ROUNDS,
    modules: str = MODULES_INPUT_ALL,
    runner: Callable[[list[str]], subprocess.CompletedProcess] = _run_subprocess,
    sleep_fn: Callable[[float], None] = time.sleep,
    epoch_fn: Callable[[], float] = time.time,
    interval_seconds: int = DEFAULT_INTERVAL_SECONDS,
) -> list[dict[str, Any]]:
    """Dispatch exactly `count` runs at one `magnitude`, each labelled
    LABEL_SEEDED_CONFIRM and each carrying the module set, and return the
    dispatch list. Makes no judgement about detection, exactly like
    cmd_sweep."""
    dispatched: list[dict[str, Any]] = []
    for _ in range(count):
        record = _dispatch_one(
            repo=repo, branch=branch, workflow=workflow,
            candidate_ref=candidate_ref, merge_base_ref=merge_base_ref, mode=perf_gate_ab_runner.MODE_SEEDED,
            patch_name=patch_name, patch_magnitude=magnitude, forced_condition=None,
            rounds=rounds, label=LABEL_SEEDED_CONFIRM, modules=modules,
            runner=runner, sleep_fn=sleep_fn, epoch_fn=epoch_fn, interval_seconds=interval_seconds,
        )
        dispatched.append(record)
    return dispatched


def _tree_hash_pair_mismatch(record: dict[str, Any]) -> dict[str, Any] | None:
    """Recompute the tree-hash-pair comparison from the record's own
    declared and measured hash fields (`declared_candidate_tree_hash`,
    `declared_merge_base_tree_hash`, `candidate_tree_hash`,
    `merge_base_tree_hash`), returning None when the pair holds and
    otherwise a mapping naming the mismatching leg, its declared value, and
    its measured value.

    Trusting the record's own `tree_hash_pair_match` flag instead would
    defeat the point of the check: that flag is written by the same
    process that could have built the wrong tree and reported success
    anyway, so this function never reads it and recomputes the comparison
    from the four hash fields directly.

    When the candidate leg was patched (`run.patch_applied` true), only the
    merge-base leg's half of the comparison is judged, since a patched tree
    deliberately no longer equals its own pre-patch tree hash; the
    candidate leg's provenance is instead its pre-patch commit sha
    (`candidate_sha`) and the patch file's own sha256 (`patch_sha256`).

    When the run's own `forced_condition` is
    `perf_gate_ab_runner.FORCED_TREE_HASH_PAIR_MISMATCH`, the mismatch is
    the deliberately induced evaluator condition this run exists to force
    (`perf_gate_ab_runner.build_ab_record` sets `declared_merge_base_tree_hash`
    to a bogus value for exactly this reason), not evidence of a corrupted
    collection -- this function returns `None` for that record so it is
    admitted rather than rejected, and the evaluator's own
    `tree_hash_pair_match` field (already `False` on the record) is what
    resolves every gating cell to INCONCLUSIVE downstream. Trusting
    `forced_condition` here is safe in a way trusting `tree_hash_pair_match`
    is not: `forced_condition` is copied verbatim from this run's own
    dispatch input (set before the run, never derived from its outcome),
    while `tree_hash_pair_match` is a boolean the same process computed
    from the fields this function is deliberately re-checking.
    """
    run_info = record.get("run")
    run_info = run_info if isinstance(run_info, dict) else {}

    if run_info.get("forced_condition") == perf_gate_ab_runner.FORCED_TREE_HASH_PAIR_MISMATCH:
        return None

    merge_base_declared = run_info.get("declared_merge_base_tree_hash")
    merge_base_measured = run_info.get("merge_base_tree_hash")
    if merge_base_declared != merge_base_measured:
        return {"leg": "merge_base", "declared": merge_base_declared, "measured": merge_base_measured}

    if run_info.get("patch_applied"):
        return None

    candidate_declared = run_info.get("declared_candidate_tree_hash")
    candidate_measured = run_info.get("candidate_tree_hash")
    if candidate_declared != candidate_measured:
        return {"leg": "candidate", "declared": candidate_declared, "measured": candidate_measured}
    return None


def _find_gate_record_files(root: Path) -> list[Path]:
    """The aggregated two-leg record lives at
    GATE_RECORD_DIRNAME/GATE_RECORD_FILENAME inside the downloaded
    artifact. Globs that known subpath rather than sorting a directory
    listing and taking the first entry -- see GATE_RECORD_DIRNAME's own
    comment for the earlier harness-campaign selection bug that mistake
    caused."""
    return list(root.glob(f"**/{GATE_RECORD_DIRNAME}/{GATE_RECORD_FILENAME}"))


def _find_verdict_files(root: Path) -> list[Path]:
    """The verdict sidecar lives at
    GATE_RECORD_DIRNAME/VERDICT_RECORD_FILENAME inside the downloaded
    artifact, beside the aggregated two-leg record. Globs that known
    subpath, exactly like _find_gate_record_files."""
    return list(root.glob(f"**/{GATE_RECORD_DIRNAME}/{VERDICT_RECORD_FILENAME}"))


def _destination_filename(run_id: Any, source_name: str) -> str:
    """Run-id-prefix convention copied from
    perf_harness_campaign._destination_filename, so idempotence works by
    filename alone. GATE_RECORD_FILENAME and VERDICT_RECORD_FILENAME are
    already distinct names, so this one convention gives both files for one
    run a distinct, never-confused suffix (e.g. `123-ab-record.json` and
    `123-verdict.json`)."""
    return f"{run_id}-{source_name}"


def cmd_collect(
    *,
    repo: str = DEFAULT_REPO,
    branch: str = DEFAULT_BRANCH,
    dest: Path = Path(DEFAULT_DEST),
    since_epoch: float = 0.0,
    runner: Callable[[list[str]], subprocess.CompletedProcess] = _run_subprocess,
    downloader: Callable[..., "Path | None"] = download_run_artifacts,
) -> dict[str, Any]:
    """List, correlate, and idempotently collect this campaign's gate
    validation artifacts.

    Takes no campaign-wide expected-hash argument: the tree-hash-pair
    comparison is per run against that run's own declared pair
    (`_tree_hash_pair_mismatch`), never against one shared value. Requires
    only the destination directory.

    Collection is idempotent by run-id-derived destination filename: a run
    already present on disk is reported as already collected rather than
    re-downloaded. A rejected run's files are never written into `dest`. A
    record whose `run.patch_applied` is false is admitted and written,
    because a patch that failed to apply is a scored outcome rather than an
    invalid measurement -- `cmd_status` reports it under its own
    CATEGORY_PATCH_FAILED category regardless of the run's label. The
    scratch download directory is removed in a `finally` block for every
    run, whether the run was collected, skipped, or rejected.
    """
    entries, list_error = list_runs(repo, runner=runner)
    if list_error is not None:
        return {
            "exit_code": 1, "reason": "list-failed", "collected": 0,
            "already_present": 0, "rejected": [], "skipped": [],
        }

    correlated, _skipped_timestamps = correlate_runs(entries, branch, since_epoch)
    correlated = [entry for entry in correlated if entry.get("event") == DISPATCH_EVENT]

    if not correlated:
        return {
            "exit_code": 1, "reason": "no-runs-found", "collected": 0,
            "already_present": 0, "rejected": [], "skipped": [],
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
            record_files = _find_gate_record_files(Path(artifact_root))
            if not record_files:
                skipped.append({"run_id": run_id, "reason": f"no {GATE_RECORD_FILENAME} present"})
                continue
            record_path = record_files[0]

            try:
                raw_text = record_path.read_text(encoding="utf-8")
            except OSError as exc:
                skipped.append({"run_id": run_id, "reason": f"unreadable artifact: {exc}"})
                continue
            if not raw_text.strip():
                skipped.append({"run_id": run_id, "reason": "empty artifact"})
                continue
            try:
                record = json.loads(raw_text)
            except json.JSONDecodeError as exc:
                skipped.append({"run_id": run_id, "reason": f"unparseable artifact: {exc}"})
                continue
            if not isinstance(record, dict):
                skipped.append({"run_id": run_id, "reason": "non-mapping JSON payload"})
                continue

            mismatch = _tree_hash_pair_mismatch(record)
            if mismatch is not None:
                rejected.append({"run_id": run_id, "reason": TREE_HASH_MISMATCH, **mismatch})
                continue

            dest_path = dest / _destination_filename(run_id, record_path.name)
            dest_path.write_text(raw_text, encoding="utf-8")

            verdict_files = _find_verdict_files(Path(artifact_root))
            if verdict_files:
                verdict_path = verdict_files[0]
                try:
                    verdict_text: str | None = verdict_path.read_text(encoding="utf-8")
                except OSError:
                    verdict_text = None
                if verdict_text is not None and verdict_text.strip():
                    verdict_dest_path = dest / _destination_filename(run_id, verdict_path.name)
                    verdict_dest_path.write_text(verdict_text, encoding="utf-8")

            collected += 1
        finally:
            shutil.rmtree(artifact_root, ignore_errors=True)

    return {
        "exit_code": 0, "reason": "collected", "collected": collected,
        "already_present": already_present, "rejected": rejected, "skipped": skipped,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    register = subparsers.add_parser(
        "register", help="Confirm the validation workflow is dispatchable on the fork",
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
    dispatch.add_argument("--candidate-ref", default="")
    dispatch.add_argument("--merge-base-ref", default="")
    dispatch.add_argument("--mode", default=perf_gate_ab_runner.MODE_NULL, choices=VALID_MODES)
    dispatch.add_argument("--label", default=LABEL_NULL, choices=VALID_LABELS)
    dispatch.add_argument("--rounds", type=int, default=DEFAULT_ROUNDS)
    dispatch.add_argument(
        "--forced-condition", default=None,
        help="Deliberately induce one named evaluator INCONCLUSIVE condition on every "
        "dispatched run in this call (see perf_gate_ab_runner.FORCED_CONDITIONS); forwarded "
        "unchanged to cmd_dispatch, which already accepts this parameter but the CLI did not "
        "expose it",
    )

    collect = subparsers.add_parser(
        "collect", help="Correlate this campaign's runs and download their artifacts idempotently",
    )
    collect.add_argument("--repo", default=DEFAULT_REPO)
    collect.add_argument("--branch", default=DEFAULT_BRANCH)
    collect.add_argument("--dest", default=DEFAULT_DEST)

    status = subparsers.add_parser(
        "status", help="Report the currently collected population and the stopping condition",
    )
    status.add_argument("--dest", default=DEFAULT_DEST)
    status.add_argument("--coverage-target", type=int, default=DEFAULT_COVERAGE_TARGET)
    status.add_argument("--run-cap", type=int, default=DEFAULT_RUN_CAP)

    sweep = subparsers.add_parser(
        "sweep", help="Dispatch one seeded-search run per magnitude while searching for detection",
    )
    sweep.add_argument("--repo", default=DEFAULT_REPO)
    sweep.add_argument("--branch", default=DEFAULT_BRANCH)
    sweep.add_argument("--workflow", default=DEFAULT_WORKFLOW)
    sweep.add_argument("--candidate-ref", default="")
    sweep.add_argument("--merge-base-ref", default="")
    sweep.add_argument("--rounds", type=int, default=DEFAULT_ROUNDS)
    sweep.add_argument("--patch-name", required=True)
    sweep.add_argument(
        "--magnitudes", required=True,
        help="Comma-separated ordered list of magnitudes to dispatch, one seeded-search run each",
    )
    sweep.add_argument("--modules", default=MODULES_INPUT_ALL)

    confirm = subparsers.add_parser(
        "confirm", help="Dispatch the declared confirming run count at one detected magnitude",
    )
    confirm.add_argument("--repo", default=DEFAULT_REPO)
    confirm.add_argument("--branch", default=DEFAULT_BRANCH)
    confirm.add_argument("--workflow", default=DEFAULT_WORKFLOW)
    confirm.add_argument("--candidate-ref", default="")
    confirm.add_argument("--merge-base-ref", default="")
    confirm.add_argument("--rounds", type=int, default=DEFAULT_ROUNDS)
    confirm.add_argument("--patch-name", required=True)
    confirm.add_argument("--magnitude", required=True)
    confirm.add_argument("--confirming-runs", type=int, default=DEFAULT_CONFIRMING_RUNS)
    confirm.add_argument("--modules", default=MODULES_INPUT_ALL)

    return parser.parse_args(argv)


def _print_status_summary(result: dict[str, Any]) -> None:
    print(f"collected_count: {result['collected_count']}")
    print(f"distinct_host_models: {result['distinct_host_models']}")
    for model, count in sorted(result["host_models"].items()):
        print(f"  {model}: {count}")
    print("categories:")
    for category, count in sorted(result["categories"].items()):
        print(f"  {category}: {count}")
    print(f"rejected_count: {result['rejected_count']}")
    print(f"skipped_count: {result['skipped_count']}")
    print(f"uncategorized_count: {result['uncategorized_count']}")
    print(f"condition: {result['condition']}")


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
            run_cap=args.run_cap, candidate_ref=args.candidate_ref, merge_base_ref=args.merge_base_ref,
            mode=args.mode, label=args.label, rounds=args.rounds,
            forced_condition=args.forced_condition,
        )
        print(f"condition: {result['condition']}")
        print(f"dispatched_count: {result['dispatched_count']}")
        return 0 if result["condition"] != CONDITION_FAILURE else 1

    if args.command == "collect":
        result = cmd_collect(repo=args.repo, branch=args.branch, dest=Path(args.dest))
        print(
            f"collected: {result['collected']} already_present: {result['already_present']} "
            f"rejected: {len(result['rejected'])} skipped: {len(result['skipped'])}"
        )
        return result["exit_code"]

    if args.command == "status":
        result = cmd_status(Path(args.dest), coverage_target=args.coverage_target, run_cap=args.run_cap)
        _print_status_summary(result)
        return 0

    if args.command == "sweep":
        magnitudes = [m.strip() for m in args.magnitudes.split(",") if m.strip()]
        dispatched = cmd_sweep(
            args.patch_name, magnitudes, repo=args.repo, branch=args.branch, workflow=args.workflow,
            candidate_ref=args.candidate_ref, merge_base_ref=args.merge_base_ref, rounds=args.rounds,
            modules=args.modules,
        )
        print(f"dispatched: {len(dispatched)}")
        return 0 if all(record["dispatch_exit_code"] == 0 for record in dispatched) else 1

    if args.command == "confirm":
        dispatched = cmd_confirm(
            args.patch_name, args.magnitude, args.confirming_runs,
            repo=args.repo, branch=args.branch, workflow=args.workflow,
            candidate_ref=args.candidate_ref, merge_base_ref=args.merge_base_ref, rounds=args.rounds,
            modules=args.modules,
        )
        print(f"dispatched: {len(dispatched)}")
        return 0 if all(record["dispatch_exit_code"] == 0 for record in dispatched) else 1

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
# ----------------------------------------------------------------------------
