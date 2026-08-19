#!/usr/bin/env python3
# ----------------------------------------------------------------------------
# Title      : ROGUE Perf Gate Validation Report
# ----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
# ----------------------------------------------------------------------------

"""Turns the collected gate validation population into the phase's published evidence: two
separately reported false-positive rates, an inconclusive rate reported apart from the fail
rate (and never without the non-gating-metric rate beside it), the smallest detected magnitude
per patch and metric, one run-level confusion matrix, the recorded derivation behind every
gating threshold, and the paired mechanism's measured cost against the gating job budget.

Every collected two-leg record is re-evaluated through scripts/perf_gate_evaluator.py against
the committed baseline rather than trusted from the verdict the job itself recorded (a
disagreement is counted and reported as a finding, never resolved silently). Every rate is
emitted as a numerator, a denominator, and a formatted percentage; a rate over an empty
population is reported as undefined with its zero denominator shown, never as zero percent.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import perf_campaign_report  # noqa: E402  (flat sibling import, path inserted above)
import perf_gate_ab_runner  # noqa: E402  (flat sibling import, path inserted above)
import perf_gate_baseline  # noqa: E402  (flat sibling import, path inserted above)
import perf_gate_evaluator  # noqa: E402  (flat sibling import, path inserted above)
import perf_gate_validation_campaign  # noqa: E402  (flat sibling import, path inserted above)

TESTS_PERF_DIR = SCRIPTS_DIR.parent / "tests" / "perf"
if str(TESTS_PERF_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_PERF_DIR))

# Imported by bare module name (never `tests.perf._perf_harness`), matching every other module
# in this effort's own import, so this module stays runnable on a machine where a stray
# top-level `tests` package shadows this repository's own `tests/` namespace package.
import _perf_harness  # noqa: E402  (flat sibling import, path inserted above)

REPORT_VERSION = 1

DEFAULT_RUNS_DIR = perf_gate_validation_campaign.DEFAULT_DEST
DEFAULT_BASELINE = perf_gate_baseline.DEFAULT_OUT_JSON
DEFAULT_OUT_MD = "docs/plans/perf-ci-hardening/GATE-VALIDATION-REPORT.md"
DEFAULT_OUT_JSON = "docs/plans/perf-ci-hardening/gate-validation-report.json"
# Points at the committed noise-floor sidecar (read through the existing loader rather than
# hardcoding min_n/mde_z/mde_gate_pct here).
DEFAULT_NOISE_FLOOR_PATH = perf_campaign_report.DEFAULT_NOISE_FLOOR_PATH

# The gating job budget: a declared limit, never a measured figure. Every measured
# figure this report compares against it is labelled as measured explicitly. Mirrors
# perf_gate_evaluator.GATE_BUDGET_SECONDS, the one place this figure is declared, following the
# same pattern this module already uses for GATE_AB_SCHEMA_VERSION and EVALUATOR_SCHEMA_VERSION
# below. The numeric value must never move without moving there first.
DEFAULT_BUDGET_SECONDS = perf_gate_evaluator.GATE_BUDGET_SECONDS

# A rate over an empty denominator is undefined, never zero: zero percent would read as "no
# spurious failures were possible", when the truth is "no run existed to be spurious about".
RATE_UNDEFINED = "undefined"

# The hand-authored companion document this generated report does not restate: the dispatch
# procedure, the frozen branches, and the two single-sample cost measurements this report's
# own budget section recomputes from the population rather than quoting.
SETUP_DOC = "docs/plans/perf-ci-hardening/GATE-VALIDATION-SETUP.md"

# One sentence explaining why a per-cell derivation differs from the pooled per-metric figure
# docs/plans/perf-ci-hardening/CAMPAIGN-REPORT.md's own metric table reports, with the concrete
# figures this reconciliation cites (measured_inputs): pooling mixes cells with genuinely
# different values into one distribution, while the per-cell figure is what the gate actually
# compares against.
POOLED_RECONCILIATION_NOTE = (
    "Every threshold in this section is derived from its own (benchmark, metric) cell, never "
    "from the pooled per-metric figure docs/plans/perf-ci-hardening/CAMPAIGN-REPORT.md's own "
    "metric table reports: that table pools every sample across every benchmark that collects "
    "a metric into one distribution, so gil_acquire_count reads a pooled coefficient of "
    "variation of 0.79 and a pooled two-sample minimum-detectable effect of 7.66 percent there, "
    "even though every one of its 14 individual cells in this campaign's own baseline is "
    "exactly constant. The two figures differ because pooling mixes cells with genuinely "
    "different values into one distribution; the per-cell figure this section cites is what "
    "the gate actually compares against."
)

CANONICAL_COMMAND = (
    "python3 scripts/perf_gate_validation_report.py "
    f"--runs-dir {DEFAULT_RUNS_DIR} --baseline {DEFAULT_BASELINE} "
    # DEFAULT_BUDGET_SECONDS now mirrors perf_gate_evaluator.GATE_BUDGET_SECONDS, a float
    # (600.0). Formatted with :g rather than a bare f-string substitution so this printed
    # command still reads "600", exactly as it did when DEFAULT_BUDGET_SECONDS was its own
    # int literal -- the mirrored value is unchanged, and the printed reproduction command
    # must not move just because its source moved.
    f"--budget-seconds {DEFAULT_BUDGET_SECONDS:g} --out-md {DEFAULT_OUT_MD} --out-json {DEFAULT_OUT_JSON}"
)

# Reused unchanged so this module and the campaign driver cannot drift on what a valid label
# or derived category is (see the module docstring's re-evaluation discipline).
LABEL_NULL = perf_gate_validation_campaign.LABEL_NULL
LABEL_UNRELATED = perf_gate_validation_campaign.LABEL_UNRELATED
LABEL_SEEDED_SEARCH = perf_gate_validation_campaign.LABEL_SEEDED_SEARCH
LABEL_SEEDED_CONFIRM = perf_gate_validation_campaign.LABEL_SEEDED_CONFIRM
LABEL_FORCED_INCONCLUSIVE = perf_gate_validation_campaign.LABEL_FORCED_INCONCLUSIVE
VALID_LABELS = perf_gate_validation_campaign.VALID_LABELS
CATEGORY_PATCH_FAILED = perf_gate_validation_campaign.CATEGORY_PATCH_FAILED
CATEGORY_UNCATEGORIZED = perf_gate_validation_campaign.CATEGORY_UNCATEGORIZED

OUTSIDE_MATRIX_CATEGORIES: tuple[str, ...] = (
    LABEL_FORCED_INCONCLUSIVE, LABEL_SEEDED_SEARCH, CATEGORY_PATCH_FAILED, CATEGORY_UNCATEGORIZED,
)

# The evaluator's own schema versions: a collected file carrying anything else is an
# unrecognized schema version, counted and skipped rather than trusted.
GATE_AB_SCHEMA_VERSION = perf_gate_ab_runner.GATE_AB_SCHEMA_VERSION
EVALUATOR_SCHEMA_VERSION = perf_gate_evaluator.EVALUATOR_SCHEMA_VERSION

# scripts/perf_gate_validation_campaign.py's own `{run_id}-{source_name}` destination-filename
# convention: the two files for one run share a run-id prefix and are told apart by these two
# already-distinct suffixes.
GATE_RECORD_SUFFIX = "-ab-record.json"
VERDICT_SUFFIX = "-verdict.json"

SKIP_RECORD_WITHOUT_VERDICT = "record-without-verdict"
SKIP_VERDICT_WITHOUT_RECORD = "verdict-without-record"
SKIP_UNPARSEABLE = "unparseable-file"
SKIP_UNRECOGNIZED_SCHEMA = "unrecognized-schema-version"
SKIP_REASONS: tuple[str, ...] = (
    SKIP_RECORD_WITHOUT_VERDICT, SKIP_VERDICT_WITHOUT_RECORD, SKIP_UNPARSEABLE, SKIP_UNRECOGNIZED_SCHEMA,
)

# The one source of the detection definition: a patch name (with or without its ".patch"
# suffix) maps to the observing metric tuple the seeded-regressions reference document names
# for it. The delay patch's tuple is empty by construction, which is what makes a gate
# detection for it structurally impossible -- see gate_detected below.
PATCH_OBSERVING_METRICS: dict[str, tuple[str, ...]] = {
    "extra-memcpy-per-frame": ("buffer_copy_count", "buffer_copy_bytes"),
    "extra-hotpath-allocation": ("pool_alloc_total_count", "pool_alloc_total_bytes"),
    "disable-frame-batching": ("combiner_count",),
    "extra-transaction-lock": ("transaction_lock_acquisitions",),
    "per-transaction-delay": (),
}

# The published deviation sentence for a patch whose contributing runs measured a module
# set narrower than the runner's own default: gate baseline cells are keyed per
# (benchmark, metric), so the observing cell's own lookup is unaffected by which other
# modules ran, and a narrowed run is therefore admissible evidence for the cell it
# observes -- but it is not a like-for-like replica of the full-module population runs and
# must not be read as one.
NARROWED_MODULE_SET_NOTE = (
    "One or more contributing runs measured a module set narrower than the runner's own "
    "default. Gate baseline cells are keyed per (benchmark, metric), so the observing "
    "cell's own lookup is unaffected by which other modules ran, and a narrowed run is "
    "therefore admissible evidence for the cell it observes. It is not a like-for-like "
    "replica of the full-module population runs and must not be read as one."
)

DELAY_PATCH_KEY = "per-transaction-delay"
DELAY_PATCH_NO_GATING_REASON = (
    "No gating metric observes this regression: elapsed time is exactly what the tier ladder "
    "deliberately refuses to gate, since wall-clock and dual-clock CPU-time figures are Tier "
    "2/3 and never gate by design. The regression is expected to be visible only in the "
    "wall-clock and dual-clock CPU-time figures for the benchmarks it reaches, never as a gate "
    "detection."
)

REPEATABILITY_BIT_IDENTICAL = "bit-identical"

# The rejection-band derivation's numeric inputs come from the harness module's own constants
# read at import (_perf_harness.DEFAULT_MAD_SIGMA_MULTIPLIER and _perf_harness.MAD_SIGMA_SCALE)
# rather than a new multiplier declared here, so this report's measurement-detection band and
# the harness's own rejection band cannot diverge. See tests/perf/_perf_harness.py's
# MAD_BAND_DERIVATION for the full prose derivation this number reproduces.
DISPERSION_BAND_MULTIPLIER = _perf_harness.DEFAULT_MAD_SIGMA_MULTIPLIER * _perf_harness.MAD_SIGMA_SCALE

# The non-gating-metric inconclusive rate observed on the harness population (855 of 5352
# measured metric entries across 24 clean records, every one with reason
# insufficient-clean-samples, spread over exactly 10 metrics), named here only as the
# comparison point this section's own recomputed figure is read beside -- never substituted
# for that recomputed figure.
HARNESS_NONGATING_INCONCLUSIVE_COMPARISON: dict[str, Any] = {
    "numerator": 855,
    "denominator": 5352,
    "percent": 16.0,
    "metric_count": 10,
    "reason": "insufficient-clean-samples",
    "source": "docs/plans/perf-ci-hardening/CAMPAIGN-REPORT.md (harness population, 24 clean records)",
}

SECTION_HEADINGS: tuple[str, ...] = (
    "## Reproducing this report",
    "## Source",
    "## Population",
    "## False-positive campaign",
    "## Inconclusive conditions",
    "## Non-gating metric inconclusive rate",
    "## Seeded regressions",
    "## Smallest detected magnitude",
    "## Confusion matrix",
    "## Runs outside the matrix",
    "## Gating threshold derivations",
    "## Paired mechanism cost and budget",
)


def _numeric(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _patch_key(patch_name: Any) -> Any:
    """Strip a trailing ".patch" suffix (the literal filename `run.patch_name` carries) so a
    caller passing either the filename or the bare key reaches the same
    `PATCH_OBSERVING_METRICS` entry."""
    if isinstance(patch_name, str) and patch_name.endswith(".patch"):
        return patch_name[: -len(".patch")]
    return patch_name


def _magnitude_sort_key(magnitude: Any) -> tuple[int, Any]:
    """Numeric magnitudes sort numerically; anything else (including None) sorts after every
    numeric magnitude, in a stable string order, rather than raising on a mixed-type compare."""
    try:
        return (0, float(magnitude))
    except (TypeError, ValueError):
        return (1, str(magnitude))


def _run_patch_info(record: dict[str, Any]) -> tuple[Any, Any, Any]:
    run_info = record.get("run")
    run_info = run_info if isinstance(run_info, dict) else {}
    return run_info.get("patch_name"), run_info.get("patch_magnitude"), run_info.get("patch_applied")


def _narrowed_module_runs(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One mapping per run in `runs` whose record declares `run.measured_modules_is_default`
    as exactly `False`, each carrying that run's id and its `run.measured_modules` list,
    sorted by run id. A record carrying neither field -- every one of the already-committed
    records -- is treated as a default-set run: absence is not narrowing, only an explicit
    `False` is."""
    narrowed: list[dict[str, Any]] = []
    for entry in runs:
        record = entry.get("record")
        record = record if isinstance(record, dict) else {}
        run_info = record.get("run")
        run_info = run_info if isinstance(run_info, dict) else {}
        if run_info.get("measured_modules_is_default") is False:
            narrowed.append({
                "run_id": entry.get("run_id"),
                "measured_modules": run_info.get("measured_modules"),
            })
    return sorted(narrowed, key=lambda item: item["run_id"])


# --- Task 1: population, false-positive rates, and the condition table ---------------------


def _read_json(path: Path) -> tuple[Any, str | None]:
    """Never raises: returns `(payload, None)` on success, `(None, reason)` otherwise, with
    `reason` one of "unreadable", "malformed-json", "non-mapping"."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None, "unreadable"
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return None, "malformed-json"
    if not isinstance(payload, dict):
        return None, "non-mapping"
    return payload, None


def load_gate_record(path: Path) -> dict[str, Any] | None:
    """The two-leg gate-ab record at `path`, or `None` for an unreadable file, malformed JSON,
    a non-mapping payload, or an unrecognized `gate_ab_schema_version`. Never raises."""
    payload, reason = _read_json(path)
    if reason is not None:
        return None
    version = payload.get("gate_ab_schema_version")
    if not isinstance(version, int) or version != GATE_AB_SCHEMA_VERSION:
        return None
    return payload


def load_verdict(path: Path) -> dict[str, Any] | None:
    """The evaluator's verdict sidecar at `path`, or `None` for an unreadable file, malformed
    JSON, a non-mapping payload, or an unrecognized `evaluator_schema_version`. Never raises."""
    payload, reason = _read_json(path)
    if reason is not None:
        return None
    version = payload.get("evaluator_schema_version")
    if not isinstance(version, int) or version != EVALUATOR_SCHEMA_VERSION:
        return None
    return payload


def _run_id_from_path(path: Path, suffix: str) -> str | None:
    name = path.name
    if not name.endswith(suffix):
        return None
    return name[: -len(suffix)]


def build_population(record_paths: list[Path], verdict_paths: list[Path]) -> dict[str, Any]:
    """Pair every collected two-leg record with its verdict sidecar by run-id prefix, in
    sorted filename order, and return accepted pairs plus separately counted skip reasons: a
    record with no verdict, a verdict with no record, an unparseable file, and an unrecognized
    schema version. Nothing is silently dropped."""
    records: dict[str, Path] = {}
    for path in sorted(record_paths, key=lambda p: p.name):
        run_id = _run_id_from_path(path, GATE_RECORD_SUFFIX)
        if run_id is not None:
            records[run_id] = path

    verdicts: dict[str, Path] = {}
    for path in sorted(verdict_paths, key=lambda p: p.name):
        run_id = _run_id_from_path(path, VERDICT_SUFFIX)
        if run_id is not None:
            verdicts[run_id] = path

    accepted: list[dict[str, Any]] = []
    skipped_details: dict[str, list[dict[str, Any]]] = {reason: [] for reason in SKIP_REASONS}

    for run_id in sorted(set(records) | set(verdicts)):
        record_path = records.get(run_id)
        verdict_path = verdicts.get(run_id)

        if record_path is None:
            skipped_details[SKIP_VERDICT_WITHOUT_RECORD].append(
                {"run_id": run_id, "path": str(verdict_path)},
            )
            continue
        if verdict_path is None:
            skipped_details[SKIP_RECORD_WITHOUT_VERDICT].append(
                {"run_id": run_id, "path": str(record_path)},
            )
            continue

        _record_payload, record_reason = _read_json(record_path)
        _verdict_payload, verdict_reason = _read_json(verdict_path)
        if record_reason is not None or verdict_reason is not None:
            skipped_details[SKIP_UNPARSEABLE].append(
                {"run_id": run_id, "record_path": str(record_path), "verdict_path": str(verdict_path)},
            )
            continue

        record = load_gate_record(record_path)
        verdict = load_verdict(verdict_path)
        if record is None or verdict is None:
            skipped_details[SKIP_UNRECOGNIZED_SCHEMA].append(
                {"run_id": run_id, "record_path": str(record_path), "verdict_path": str(verdict_path)},
            )
            continue

        record = dict(record)
        record["_run_id"] = run_id
        accepted.append({"run_id": run_id, "record": record, "verdict": verdict})

    return {
        "accepted": accepted,
        "skipped_counts": {reason: len(skipped_details[reason]) for reason in SKIP_REASONS},
        "skipped_details": skipped_details,
    }


def categorize(record: dict[str, Any]) -> tuple[str, Any]:
    """The declared label when it names a recognized category, `CATEGORY_PATCH_FAILED` when
    the record shows a requested patch did not apply, and `CATEGORY_UNCATEGORIZED` otherwise,
    paired with the observed label value carried through -- matching
    `perf_gate_validation_campaign.cmd_status`'s own derivation rule (a never-patched run is
    never promoted to patch-failed just because `patch_applied` is false)."""
    run_info = record.get("run")
    run_info = run_info if isinstance(run_info, dict) else {}
    label = run_info.get("label")
    if run_info.get("patch_name") and run_info.get("patch_applied") is False:
        return CATEGORY_PATCH_FAILED, label
    if label in VALID_LABELS:
        return label, label
    return CATEGORY_UNCATEGORIZED, label


def recompute_verdicts(population: dict[str, Any], baseline: dict[str, Any]) -> dict[str, Any]:
    """Re-evaluate every accepted record through the evaluator against the committed baseline,
    returning per run the recomputed verdict, the verdict the job recorded, whether they agree,
    plus a total disagreement count. The in-job verdict is never trusted on its own."""
    runs: list[dict[str, Any]] = []
    disagreement_count = 0
    for entry in population["accepted"]:
        record = entry["record"]
        verdict_payload = entry["verdict"]
        recorded_verdict = verdict_payload.get("verdict") if isinstance(verdict_payload, dict) else None
        evaluation = perf_gate_evaluator.evaluate_run(record, baseline)
        recomputed_verdict = evaluation["verdict"]
        agree = recomputed_verdict == recorded_verdict
        if not agree:
            disagreement_count += 1
        category, observed_label = categorize(record)
        runs.append({
            "run_id": entry["run_id"],
            "record": record,
            "evaluation": evaluation,
            "recomputed_verdict": recomputed_verdict,
            "recorded_verdict": recorded_verdict,
            "agree": agree,
            "category": category,
            "observed_label": observed_label,
        })
    return {"runs": runs, "disagreement_count": disagreement_count}


def rate(numerator: int, denominator: int) -> dict[str, Any]:
    """A rate triple: `numerator`, `denominator`, and `percent`, where `percent` is
    `RATE_UNDEFINED` for a zero denominator rather than a bare zero float."""
    if denominator == 0:
        return {"numerator": numerator, "denominator": denominator, "percent": RATE_UNDEFINED}
    return {"numerator": numerator, "denominator": denominator, "percent": (numerator / denominator) * 100.0}


def build_nongating_inconclusive_section(recomputed_runs: list[dict[str, Any]]) -> dict[str, Any]:
    """The non-gating-metric inconclusive rate over `recomputed_runs`, counted at the cell
    level (every non-gating cell the evaluator ever emits for these runs), computed from the
    collected records' own metric entries rather than quoted from the harness population. The
    harness population's own figure is carried only as a comparison point."""
    numerator = 0
    denominator = 0
    for entry in recomputed_runs:
        for cell in entry["evaluation"]["cells"]:
            if cell["gating"]:
                continue
            denominator += 1
            if cell["verdict"] == perf_gate_evaluator.VERDICT_INCONCLUSIVE:
                numerator += 1
    return {
        "rate": rate(numerator, denominator),
        "harness_comparison": HARNESS_NONGATING_INCONCLUSIVE_COMPARISON,
    }


def _population_verdict_stats(runs: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(runs)
    pass_count = sum(1 for r in runs if r["recomputed_verdict"] == perf_gate_evaluator.VERDICT_PASS)
    fail_count = sum(1 for r in runs if r["recomputed_verdict"] == perf_gate_evaluator.VERDICT_FAIL)
    inconclusive_count = sum(
        1 for r in runs if r["recomputed_verdict"] == perf_gate_evaluator.VERDICT_INCONCLUSIVE
    )
    failing_runs = [
        {
            "run_id": r["run_id"],
            "failing_cells": [
                {"benchmark": cell["benchmark"], "metric": cell["metric"]}
                for cell in r["evaluation"]["failing_cells"]
            ],
        }
        for r in sorted(runs, key=lambda item: item["run_id"])
        if r["recomputed_verdict"] == perf_gate_evaluator.VERDICT_FAIL
    ]
    return {
        "run_count": total,
        "pass_count": pass_count,
        "fail_count": fail_count,
        "inconclusive_count": inconclusive_count,
        "fail_rate": rate(fail_count, total),
        "inconclusive_rate": rate(inconclusive_count, total),
        "nongating_inconclusive": build_nongating_inconclusive_section(runs),
        "failing_runs": failing_runs,
    }


def build_false_positive_section(recomputed_runs: list[dict[str, Any]]) -> dict[str, Any]:
    """The null and unrelated unchanged-code populations, reported separately and then
    combined: run count, pass/fail/inconclusive counts, the fail rate and the inconclusive
    rate as rate triples, the non-gating-metric inconclusive rate beside them, and every
    failing run listed by id with its failing gating cells so a non-zero fail numerator is
    never a bare count. A run counts as a spurious failure when its recomputed verdict is
    FAIL, whatever number of gating cells it failed on (scoring is at run level)."""
    null_runs = [r for r in recomputed_runs if r["category"] == LABEL_NULL]
    unrelated_runs = [r for r in recomputed_runs if r["category"] == LABEL_UNRELATED]
    return {
        "null_population": _population_verdict_stats(null_runs),
        "unrelated_population": _population_verdict_stats(unrelated_runs),
        "combined": _population_verdict_stats(null_runs + unrelated_runs),
    }


def build_condition_section(recomputed_runs: list[dict[str, Any]]) -> dict[str, Any]:
    """One row per entry in `perf_gate_evaluator.INCONCLUSIVE_CONDITIONS`, in that declared
    order, with its count across `recomputed_runs`, including zero-count rows, so two
    conditions with equal counts keep a stable order."""
    all_cells: list[dict[str, Any]] = []
    for entry in recomputed_runs:
        all_cells.extend(entry["evaluation"]["cells"])
    counts = perf_gate_evaluator.condition_counts(all_cells)
    ordered = {
        condition: counts.get(condition, 0) for condition in perf_gate_evaluator.INCONCLUSIVE_CONDITIONS
    }
    return {"conditions": ordered}


# --- Task 2: detection, the confusion matrix, threshold derivations, and the budget ---------


def expected_metrics_for_patch(patch_name: Any) -> tuple[str, ...]:
    """The observing metric tuple `PATCH_OBSERVING_METRICS` names for `patch_name` (accepted
    with or without its ".patch" suffix), or an empty tuple for an unrecognized patch name."""
    return PATCH_OBSERVING_METRICS.get(_patch_key(patch_name), ())


def gate_detected(evaluation: dict[str, Any], patch_name: Any) -> bool:
    """True when `evaluation`'s recomputed verdict is FAIL and at least one failing gating
    cell's metric belongs to `patch_name`'s expected metric tuple. False for the delay patch by
    construction, since that tuple is empty."""
    expected = expected_metrics_for_patch(patch_name)
    if not expected:
        return False
    if evaluation.get("verdict") != perf_gate_evaluator.VERDICT_FAIL:
        return False
    return any(cell["metric"] in expected for cell in evaluation.get("failing_cells", []))


def measurement_detected(record: dict[str, Any], baseline: dict[str, Any], patch_name: Any) -> bool:
    """True when at least one non-gating (benchmark, metric) cell's candidate-leg median falls
    outside that cell's own recorded baseline dispersion band (median +/- DISPERSION_BAND_MULTIPLIER
    * mad), computed only against cells the baseline itself measured. `patch_name` is accepted
    for interface symmetry with `gate_detected`; the scan itself is patch-agnostic, since a
    regression can move a non-gating metric the seeded-regressions reference did not name."""
    del patch_name  # scan is patch-agnostic; see docstring
    baseline_cells = baseline.get("cells")
    baseline_cells = baseline_cells if isinstance(baseline_cells, dict) else {}
    legs = record.get("legs")
    legs = legs if isinstance(legs, dict) else {}
    candidate_leg = legs.get(perf_gate_ab_runner.LEG_CANDIDATE)
    candidate_leg = candidate_leg if isinstance(candidate_leg, dict) else {}
    candidate_benchmarks = candidate_leg.get("benchmarks")
    candidate_benchmarks = candidate_benchmarks if isinstance(candidate_benchmarks, dict) else {}

    for benchmark in sorted(baseline_cells):
        metric_map = baseline_cells[benchmark]
        if not isinstance(metric_map, dict):
            continue
        for metric in sorted(metric_map):
            baseline_cell = metric_map[metric]
            if not isinstance(baseline_cell, dict):
                continue
            if baseline_cell.get("gate_rule") != perf_gate_baseline.GATE_RULE_NON_GATING:
                continue
            if baseline_cell.get("status") != perf_gate_baseline.CELL_MEASURED:
                continue
            median = baseline_cell.get("median")
            mad = baseline_cell.get("mad")
            if not (_numeric(median) and _numeric(mad)):
                continue

            bench_entry = candidate_benchmarks.get(benchmark)
            metric_entry = (
                bench_entry.get("metrics", {}).get(metric) if isinstance(bench_entry, dict) else None
            )
            if not isinstance(metric_entry, dict):
                continue
            candidate_median = metric_entry.get("median")
            if not _numeric(candidate_median):
                continue

            band = DISPERSION_BAND_MULTIPLIER * mad
            if abs(candidate_median - median) > band:
                return True
    return False


def _cell_repeatability_verdict(cell: dict[str, Any]) -> Any:
    """`REASON_WITHIN_RUN_UNSTABLE` when that is the cell's own reason, the cell's own reason
    for any other INCONCLUSIVE verdict, or `REPEATABILITY_BIT_IDENTICAL` for a PASS/FAIL
    verdict (both legs produced a single deterministic clean value)."""
    if cell.get("reason") == perf_gate_evaluator.REASON_WITHIN_RUN_UNSTABLE:
        return perf_gate_evaluator.REASON_WITHIN_RUN_UNSTABLE
    if cell.get("verdict") == perf_gate_evaluator.VERDICT_INCONCLUSIVE:
        return cell.get("reason")
    return REPEATABILITY_BIT_IDENTICAL


def _patch_repeatability_verdicts(evaluation: dict[str, Any], patch_name: Any) -> list[Any]:
    expected = expected_metrics_for_patch(patch_name)
    if not expected:
        return []
    return [
        _cell_repeatability_verdict(cell)
        for cell in evaluation.get("cells", [])
        if cell["metric"] in expected
    ]


def build_seeded_section(recomputed_runs: list[dict[str, Any]], baseline: dict[str, Any]) -> dict[str, Any]:
    """One block per patch actually dispatched in `recomputed_runs` (seeded-search and
    seeded-confirm runs only): the run count at each magnitude in ascending magnitude order,
    the recomputed verdict at each, whether it was gate detected, whether it was measurement
    detected, and every contributing leg's within-run repeatability verdict."""
    by_patch: dict[str, dict[Any, list[dict[str, Any]]]] = {}
    for entry in recomputed_runs:
        if entry["category"] not in (LABEL_SEEDED_SEARCH, LABEL_SEEDED_CONFIRM):
            continue
        patch_name, magnitude, _patch_applied = _run_patch_info(entry["record"])
        if not patch_name:
            continue
        by_patch.setdefault(patch_name, {}).setdefault(magnitude, []).append(entry)

    patches_out: dict[str, Any] = {}
    for patch_name in sorted(by_patch):
        magnitudes_out: dict[Any, Any] = {}
        for magnitude in sorted(by_patch[patch_name], key=_magnitude_sort_key):
            runs = sorted(by_patch[patch_name][magnitude], key=lambda item: item["run_id"])
            run_entries = []
            for r in runs:
                _, _, patch_applied = _run_patch_info(r["record"])
                run_entries.append({
                    "run_id": r["run_id"],
                    "category": r["category"],
                    "patch_applied": patch_applied,
                    "recomputed_verdict": r["recomputed_verdict"],
                    "gate_detected": gate_detected(r["evaluation"], patch_name),
                    "measurement_detected": measurement_detected(r["record"], baseline, patch_name),
                    "repeatability_verdicts": _patch_repeatability_verdicts(r["evaluation"], patch_name),
                })
            magnitudes_out[magnitude] = {"run_count": len(runs), "runs": run_entries}
        patches_out[patch_name] = {"magnitudes": magnitudes_out}
    return {"patches": patches_out}


def _baseline_observed_value(baseline: dict[str, Any], benchmark: str, metric: str) -> Any:
    cells = baseline.get("cells")
    cells = cells if isinstance(cells, dict) else {}
    bench_cells = cells.get(benchmark)
    bench_cells = bench_cells if isinstance(bench_cells, dict) else {}
    cell = bench_cells.get(metric)
    if not isinstance(cell, dict):
        return None
    return cell.get("observed_value")


def _smallest_magnitude_for_metric(
    ordered_magnitudes: list[Any],
    magnitudes_for_patch: dict[Any, list[dict[str, Any]]],
    metric: str,
    baseline: dict[str, Any],
) -> dict[str, Any]:
    """Every magnitude, in ascending order, at which `metric` was gate detected (at least one
    contributing run's own cell for this metric verdicts FAIL), each carrying its own
    repeatability evidence, its absolute delta, and its percentage of that cell's baseline
    value. Repeatability is judged across every run dispatched at that magnitude, not only the
    FAIL cells: a FAIL cell is, by construction, always internally repeatable (both legs
    produced a single deterministic clean value), so a magnitude with one FAIL run and a
    second run whose own leg disagreed with itself on the same metric
    (`REASON_WITHIN_RUN_UNSTABLE`) is exactly the "detected but unstable" case this table must
    surface rather than silently pass as stable. `smallest_detected` is the first entry whose
    repeatability is bit-identical across every contributing run; a smaller magnitude detected
    with an unstable repeatability verdict stays in `candidates` with that verdict recorded as
    the reason it was not selected."""
    candidates: list[dict[str, Any]] = []
    for magnitude in ordered_magnitudes:
        runs = magnitudes_for_patch[magnitude]
        cells_for_metric = [
            cell for r in runs for cell in r["evaluation"]["cells"] if cell["metric"] == metric
        ]
        fail_cells = [
            cell for cell in cells_for_metric if cell["verdict"] == perf_gate_evaluator.VERDICT_FAIL
        ]
        if not fail_cells:
            continue

        # Only a FAIL cell (necessarily repeatable) or a cell this same metric's own within-run
        # instability check rejected speaks to repeatability; a cell INCONCLUSIVE for an
        # unrelated reason (metric absent from a leg, a failed merge-base build, and so on) is a
        # missing-data fact, not a repeatability fact, and is excluded from this judgement.
        repeatability_cells = [
            cell for cell in cells_for_metric
            if cell["verdict"] == perf_gate_evaluator.VERDICT_FAIL
            or cell.get("reason") == perf_gate_evaluator.REASON_WITHIN_RUN_UNSTABLE
        ]
        repeatability = [_cell_repeatability_verdict(cell) for cell in repeatability_cells]
        stable = all(v == REPEATABILITY_BIT_IDENTICAL for v in repeatability)
        benchmark = fail_cells[0]["benchmark"]
        baseline_value = _baseline_observed_value(baseline, benchmark, metric)
        delta = fail_cells[0]["delta"]
        if _numeric(baseline_value) and baseline_value != 0 and _numeric(delta):
            percent_of_baseline: Any = (delta / baseline_value) * 100.0
        else:
            percent_of_baseline = RATE_UNDEFINED

        candidates.append({
            "magnitude": magnitude,
            "benchmark": benchmark,
            "run_count": len(runs),
            "stable": stable,
            "repeatability_verdicts": repeatability,
            "absolute_delta": delta,
            "percent_of_baseline": percent_of_baseline,
        })

    smallest = next((candidate for candidate in candidates if candidate["stable"]), None)
    return {"candidates": candidates, "smallest_detected": smallest}


def _delay_measurement_magnitudes(
    magnitudes_for_patch: dict[Any, list[dict[str, Any]]], ordered_magnitudes: list[Any], baseline: dict[str, Any],
) -> dict[Any, Any]:
    out: dict[Any, Any] = {}
    for magnitude in ordered_magnitudes:
        runs = magnitudes_for_patch[magnitude]
        detected = any(measurement_detected(r["record"], baseline, DELAY_PATCH_KEY) for r in runs)
        out[magnitude] = {"run_count": len(runs), "measurement_detected": detected}
    return out


def build_smallest_magnitude_section(
    recomputed_runs: list[dict[str, Any]], baseline: dict[str, Any],
) -> dict[str, Any]:
    """Per patch and per observing metric, the smallest magnitude that was gate detected with
    every contributing repeatability verdict bit-identical, as an absolute count delta and a
    percentage of that cell's baseline value. The delay patch carries no gating metric at all
    (`PATCH_OBSERVING_METRICS[DELAY_PATCH_KEY]` is empty); its row instead reports the
    magnitudes at which its non-gating cells moved outside their own measured dispersion."""
    by_patch: dict[str, dict[Any, list[dict[str, Any]]]] = {}
    for entry in recomputed_runs:
        if entry["category"] not in (LABEL_SEEDED_SEARCH, LABEL_SEEDED_CONFIRM):
            continue
        patch_name, magnitude, _patch_applied = _run_patch_info(entry["record"])
        if not patch_name:
            continue
        by_patch.setdefault(patch_name, {}).setdefault(magnitude, []).append(entry)

    patches_out: dict[str, Any] = {}
    for patch_key in sorted(PATCH_OBSERVING_METRICS):
        expected = PATCH_OBSERVING_METRICS[patch_key]
        matching_patch_name = next(
            (name for name in by_patch if _patch_key(name) == patch_key), patch_key,
        )
        magnitudes_for_patch = by_patch.get(matching_patch_name, {})
        ordered_magnitudes = sorted(magnitudes_for_patch, key=_magnitude_sort_key)
        contributing_runs = [
            run for magnitude in magnitudes_for_patch for run in magnitudes_for_patch[magnitude]
        ]
        narrowed_module_runs = _narrowed_module_runs(contributing_runs)

        if not expected:
            entry: dict[str, Any] = {
                "metrics": {},
                "no_gating_metric_reason": DELAY_PATCH_NO_GATING_REASON,
                "measurement_only_magnitudes": _delay_measurement_magnitudes(
                    magnitudes_for_patch, ordered_magnitudes, baseline,
                ),
            }
            if narrowed_module_runs:
                entry["narrowed_module_runs"] = narrowed_module_runs
            patches_out[patch_key] = entry
            continue

        metrics_out = {
            metric: _smallest_magnitude_for_metric(ordered_magnitudes, magnitudes_for_patch, metric, baseline)
            for metric in expected
        }
        entry = {"metrics": metrics_out}
        if narrowed_module_runs:
            entry["narrowed_module_runs"] = narrowed_module_runs
        patches_out[patch_key] = entry
    return {"patches": patches_out}


def build_confusion_matrix_section(recomputed_runs: list[dict[str, Any]]) -> dict[str, Any]:
    """One run-level two-by-three matrix: rows are the ground truth (unchanged code -- the
    null and unrelated populations together; seeded regression -- the confirming runs only),
    columns are PASS/FAIL/INCONCLUSIVE, every cell present even when zero. The
    forced-inconclusive runs, the search runs, the patch-failed runs, and any uncategorized
    runs sit in a separate `outside_matrix` block so they cannot inflate any cell; the matrix
    total plus the outside-matrix total equals the accepted population count, emitted as a
    `reconciliation` field."""
    matrix = {
        "unchanged code": {
            perf_gate_evaluator.VERDICT_PASS: 0,
            perf_gate_evaluator.VERDICT_FAIL: 0,
            perf_gate_evaluator.VERDICT_INCONCLUSIVE: 0,
        },
        "seeded regression": {
            perf_gate_evaluator.VERDICT_PASS: 0,
            perf_gate_evaluator.VERDICT_FAIL: 0,
            perf_gate_evaluator.VERDICT_INCONCLUSIVE: 0,
        },
    }
    outside_counts: dict[str, int] = {category: 0 for category in OUTSIDE_MATRIX_CATEGORIES}
    outside_runs: list[dict[str, Any]] = []
    matrix_total = 0
    outside_total = 0

    for entry in sorted(recomputed_runs, key=lambda item: item["run_id"]):
        category = entry["category"]
        verdict = entry["recomputed_verdict"]
        if category in (LABEL_NULL, LABEL_UNRELATED):
            matrix["unchanged code"][verdict] += 1
            matrix_total += 1
        elif category == LABEL_SEEDED_CONFIRM:
            matrix["seeded regression"][verdict] += 1
            matrix_total += 1
        else:
            outside_counts[category] = outside_counts.get(category, 0) + 1
            outside_runs.append({"run_id": entry["run_id"], "category": category})
            outside_total += 1

    return {
        "matrix": matrix,
        "outside_matrix": {"counts": outside_counts, "runs": outside_runs},
        "reconciliation": {
            "matrix_total": matrix_total,
            "outside_total": outside_total,
            "accepted_total": matrix_total + outside_total,
        },
    }


def build_threshold_derivation_section(baseline: dict[str, Any]) -> dict[str, Any]:
    """Per gating cell (never per pooled metric): its observed value, sample count, spread,
    CPU models, and the derivation string the baseline sidecar itself recorded, plus the
    baseline's own census figures and the pooled reconciliation note."""
    cells = baseline.get("cells")
    cells = cells if isinstance(cells, dict) else {}
    rows: list[dict[str, Any]] = []
    for benchmark in sorted(cells):
        metric_map = cells[benchmark]
        if not isinstance(metric_map, dict):
            continue
        for metric in sorted(metric_map):
            cell = metric_map[metric]
            if not isinstance(cell, dict):
                continue
            if cell.get("gate_rule") != perf_gate_baseline.GATE_RULE_EXACT_EQUALITY:
                continue
            rows.append({
                "benchmark": benchmark,
                "metric": metric,
                "observed_value": cell.get("observed_value"),
                "n": cell.get("n"),
                "spread": cell.get("spread"),
                "cv": cell.get("cv"),
                "cpu_models": cell.get("cpu_models"),
                "derivation": cell.get("derivation"),
            })
    return {
        "cells": rows,
        "gating_metrics": baseline.get("gating_metrics", []),
        "census": baseline.get("census", {}),
        "pooled_reconciliation_note": POOLED_RECONCILIATION_NOTE,
    }


def _stage_stats(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"n": 0, "median": None, "minimum": None, "maximum": None}
    return {"n": len(values), "median": statistics.median(values), "minimum": min(values), "maximum": max(values)}


def build_budget_section(
    recomputed_runs: list[dict[str, Any]], budget_seconds: float = DEFAULT_BUDGET_SECONDS,
) -> dict[str, Any]:
    """Per-stage measured seconds across `recomputed_runs` (median, minimum, maximum, run
    count), the measured total against `budget_seconds` with a binding-or-not determination
    (a total exactly equal to the budget reports as at the boundary with both figures shown),
    the measured seconds per round per leg, how many additional rounds per leg the headroom to
    the budget buys, and a plain statement that no figure is given for additional benchmarks or
    magnitude rungs because this population measures no per-unit cost for either. A run with
    zero completed rounds contributes no seconds-per-round figure and is counted as excluded
    with the reason."""
    stage_values: dict[str, list[float]] = {stage: [] for stage in perf_gate_ab_runner.TIMING_STAGE_ORDER}
    per_round_seconds: dict[str, list[float]] = {
        perf_gate_ab_runner.LEG_CANDIDATE: [], perf_gate_ab_runner.LEG_MERGE_BASE: [],
    }
    excluded_runs: list[dict[str, Any]] = []

    for entry in sorted(recomputed_runs, key=lambda item: item["run_id"]):
        record = entry["record"]
        timings = record.get("timings")
        timings = timings if isinstance(timings, dict) else {}
        for stage in perf_gate_ab_runner.TIMING_STAGE_ORDER:
            value = timings.get(stage)
            if _numeric(value):
                stage_values[stage].append(value)

        legs = record.get("legs")
        legs = legs if isinstance(legs, dict) else {}
        for leg_name, timing_key in (
            (perf_gate_ab_runner.LEG_CANDIDATE, "measure_candidate"),
            (perf_gate_ab_runner.LEG_MERGE_BASE, "measure_merge_base"),
        ):
            leg = legs.get(leg_name)
            leg = leg if isinstance(leg, dict) else {}
            round_count = leg.get("round_count")
            measure_seconds = timings.get(timing_key)
            if not (_numeric(round_count) and round_count > 0 and _numeric(measure_seconds)):
                excluded_runs.append({
                    "run_id": entry["run_id"], "leg": leg_name, "reason": "zero completed rounds",
                })
                continue
            per_round_seconds[leg_name].append(measure_seconds / round_count)

    stages_out = {stage: _stage_stats(stage_values[stage]) for stage in perf_gate_ab_runner.TIMING_STAGE_ORDER}
    total_median = stages_out["total"]["median"]

    at_boundary = False
    if total_median is None:
        binding: Any = None
        reason = "no run in this population carries a measured total"
    elif total_median == budget_seconds:
        at_boundary = True
        binding = False
        reason = (
            f"measured median total {perf_campaign_report.fmt_float(total_median)}s equals the "
            f"{perf_campaign_report.fmt_float(budget_seconds)}s budget exactly"
        )
    elif total_median > budget_seconds:
        binding = True
        reason = (
            f"measured median total {perf_campaign_report.fmt_float(total_median)}s exceeds the "
            f"{perf_campaign_report.fmt_float(budget_seconds)}s budget"
        )
    else:
        binding = False
        reason = (
            f"measured median total {perf_campaign_report.fmt_float(total_median)}s is under the "
            f"{perf_campaign_report.fmt_float(budget_seconds)}s budget"
        )

    seconds_per_round_per_leg = {
        leg: (statistics.median(values) if values else None) for leg, values in per_round_seconds.items()
    }
    headroom_seconds = None if total_median is None else budget_seconds - total_median
    additional_rounds_affordable = None
    if headroom_seconds is not None and headroom_seconds > 0:
        per_leg_values = [v for v in seconds_per_round_per_leg.values() if v is not None]
        if per_leg_values:
            combined_seconds_per_round = sum(per_leg_values)
            additional_rounds_affordable = int(headroom_seconds // combined_seconds_per_round)

    return {
        "stages": stages_out,
        "budget_seconds": budget_seconds,
        "binding": binding,
        "at_boundary": at_boundary,
        "reason": reason,
        "seconds_per_round_per_leg": seconds_per_round_per_leg,
        "headroom_seconds": headroom_seconds,
        "additional_rounds_affordable": additional_rounds_affordable,
        "excluded_runs": excluded_runs,
        "no_projection_note": (
            "No figure is given for additional benchmarks or additional magnitude rungs: this "
            "population measures no per-unit cost for either, and giving one would be a "
            "speculation rather than a derivation. The only quantity this population measures "
            "a per-unit cost for directly and repeatedly is the interleaved round count "
            "(timings.measure_candidate and timings.measure_merge_base, each divided by "
            "round_count), which is what the seconds-per-round-per-leg figure above uses."
        ),
    }


def _category_counts(recomputed_runs: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for entry in recomputed_runs:
        counts[entry["category"]] = counts.get(entry["category"], 0) + 1
    for category in VALID_LABELS + (CATEGORY_PATCH_FAILED, CATEGORY_UNCATEGORIZED):
        counts.setdefault(category, 0)
    return dict(sorted(counts.items()))


def build_sidecar(
    *,
    population: dict[str, Any],
    recomputed: dict[str, Any],
    baseline: dict[str, Any],
    runs_dir: str,
    baseline_path: str,
    budget_seconds: float = DEFAULT_BUDGET_SECONDS,
    noise_floor_path: str | Path = DEFAULT_NOISE_FLOOR_PATH,
) -> dict[str, Any]:
    recomputed_runs = recomputed["runs"]
    noise_floor_params = perf_campaign_report.load_noise_floor_parameters(Path(noise_floor_path))

    return {
        "report_version": REPORT_VERSION,
        "source": {
            "runs_dir": runs_dir,
            "baseline": baseline_path,
            "accepted_count": len(recomputed_runs),
            "skipped_count": sum(population["skipped_counts"].values()),
            "skipped_reasons": population["skipped_counts"],
            "category_counts": _category_counts(recomputed_runs),
            "verdict_disagreement_count": recomputed["disagreement_count"],
            "noise_floor_parameters": noise_floor_params,
            "setup_doc": SETUP_DOC,
        },
        "false_positive": build_false_positive_section(recomputed_runs),
        "conditions": build_condition_section(recomputed_runs),
        "nongating_inconclusive": build_nongating_inconclusive_section(recomputed_runs),
        "seeded": build_seeded_section(recomputed_runs, baseline),
        "smallest_magnitude": build_smallest_magnitude_section(recomputed_runs, baseline),
        "confusion_matrix": build_confusion_matrix_section(recomputed_runs),
        "threshold_derivations": build_threshold_derivation_section(baseline),
        "budget": build_budget_section(recomputed_runs, budget_seconds),
    }


def _render_rate(rate_value: dict[str, Any]) -> str:
    percent = rate_value["percent"]
    percent_str = percent if percent == RATE_UNDEFINED else f"{perf_campaign_report.fmt_float(percent)}%"
    return f"{rate_value['numerator']}/{rate_value['denominator']} ({percent_str})"


def render_markdown(sidecar: dict[str, Any]) -> str:
    """Byte-identical for the same `sidecar` on two calls: no wall-clock timestamp, and every
    dict this function walks is walked in sorted key order."""
    fmt = perf_campaign_report.fmt_float
    cell = perf_campaign_report._cell
    source = sidecar["source"]
    noise_floor = source["noise_floor_parameters"]

    lines: list[str] = [
        "<!-- generated by scripts/perf_gate_validation_report.py, do not edit by hand -->",
        "# Perf Gate Validation Report",
        "",
        SECTION_HEADINGS[0], "",
        "```sh", CANONICAL_COMMAND, "```", "",
        SECTION_HEADINGS[1], "",
        f"- Runs directory: `{source['runs_dir']}`",
        f"- Baseline: `{source['baseline']}`",
        f"- Records accepted: {source['accepted_count']}",
        f"- Records skipped: {source['skipped_count']} ({source['skipped_reasons']})",
        f"- Verdict disagreement count (recorded vs recomputed): {source['verdict_disagreement_count']}",
        "- Noise floor parameters (min_n, mde_z, mde_gate_pct) source: "
        f"`{noise_floor['source_file']}` (loaded={noise_floor['loaded']}): "
        f"min_n={fmt(noise_floor['min_n'])}, mde_z={fmt(noise_floor['mde_z'])}, "
        f"mde_gate_pct={fmt(noise_floor['mde_gate_pct'])}",
        "- Setup document (hand-authored companion this generated report does not restate): "
        f"`{source['setup_doc']}`",
        "",
        SECTION_HEADINGS[2], "",
        "| Category | Count |",
        "|---|---|",
    ]
    for category in sorted(source["category_counts"]):
        lines.append(f"| {category} | {source['category_counts'][category]} |")
    lines.append("")

    fp = sidecar["false_positive"]
    lines.extend([
        SECTION_HEADINGS[3], "",
        "A run counts as a spurious failure when its recomputed verdict is FAIL, whatever "
        "number of gating cells it failed on. The two unchanged-code populations are reported "
        "separately, then combined; the combined denominator equals their sum.",
        "",
        "| Population | Runs | PASS | FAIL | INCONCLUSIVE | Fail rate | Inconclusive rate | "
        "Non-gating inconclusive rate |",
        "|---|---|---|---|---|---|---|---|",
    ])
    for name, key in (("null", "null_population"), ("unrelated", "unrelated_population"), ("combined", "combined")):
        stats = fp[key]
        lines.append(
            "| " + name
            + " | " + str(stats["run_count"])
            + " | " + str(stats["pass_count"])
            + " | " + str(stats["fail_count"])
            + " | " + str(stats["inconclusive_count"])
            + " | " + _render_rate(stats["fail_rate"])
            + " | " + _render_rate(stats["inconclusive_rate"])
            + " | " + _render_rate(stats["nongating_inconclusive"]["rate"])
            + " |"
        )
    lines.append("")
    for name, key in (("null", "null_population"), ("unrelated", "unrelated_population"), ("combined", "combined")):
        failing = fp[key]["failing_runs"]
        if not failing:
            continue
        lines.append(f"Failing runs in the {name} population:")
        lines.append("")
        for entry in failing:
            cells_desc = ", ".join(f"{c['benchmark']}/{c['metric']}" for c in entry["failing_cells"])
            lines.append(f"- `{entry['run_id']}`: {cells_desc}")
        lines.append("")

    lines.extend([SECTION_HEADINGS[4], "", "| Condition | Count |", "|---|---|"])
    for condition, count in sidecar["conditions"]["conditions"].items():
        lines.append(f"| {condition} | {count} |")
    lines.append("")

    nongating = sidecar["nongating_inconclusive"]
    harness_cmp = nongating["harness_comparison"]
    lines.extend([
        SECTION_HEADINGS[5], "",
        "Never reported alone: this rate sits beside the gate-level inconclusive rate above so "
        "a zero gate-level figure cannot read as nothing having been uncertain.",
        "",
        f"- This population: {_render_rate(nongating['rate'])}",
        "- Harness population comparison point (not this population's own result): "
        f"{harness_cmp['numerator']}/{harness_cmp['denominator']} "
        f"({fmt(harness_cmp['percent'])}%), reason `{harness_cmp['reason']}`, spread over "
        f"{harness_cmp['metric_count']} metrics ({harness_cmp['source']})",
        "",
    ])

    seeded = sidecar["seeded"]["patches"]
    lines.extend([SECTION_HEADINGS[6], ""])
    if seeded:
        for patch_name in sorted(seeded):
            lines.append(f"### {patch_name}")
            lines.append("")
            lines.append(
                "| Magnitude | Runs | Recomputed verdicts | Gate detected | Measurement detected | "
                "Repeatability |"
            )
            lines.append("|---|---|---|---|---|---|")
            magnitudes = seeded[patch_name]["magnitudes"]
            for magnitude in sorted(magnitudes, key=_magnitude_sort_key):
                entry = magnitudes[magnitude]
                verdicts = ", ".join(r["recomputed_verdict"] for r in entry["runs"])
                gate_flags = ", ".join(cell(r["gate_detected"]) for r in entry["runs"])
                measurement_flags = ", ".join(cell(r["measurement_detected"]) for r in entry["runs"])
                repeatability = ", ".join(
                    (",".join(r["repeatability_verdicts"]) or "n/a") for r in entry["runs"]
                )
                lines.append(
                    "| " + fmt(magnitude)
                    + " | " + str(entry["run_count"])
                    + " | " + verdicts
                    + " | " + gate_flags
                    + " | " + measurement_flags
                    + " | " + repeatability
                    + " |"
                )
            lines.append("")
    else:
        lines.append("No seeded-search or seeded-confirm run in this population.")
        lines.append("")

    smallest = sidecar["smallest_magnitude"]["patches"]
    lines.extend([SECTION_HEADINGS[7], ""])
    for patch_key in sorted(smallest):
        entry = smallest[patch_key]
        lines.append(f"### {patch_key}")
        lines.append("")
        narrowed_module_runs = entry.get("narrowed_module_runs")
        if narrowed_module_runs:
            lines.append(NARROWED_MODULE_SET_NOTE)
            lines.append("")
            for narrowed_run in narrowed_module_runs:
                modules_desc = ", ".join(narrowed_run.get("measured_modules") or [])
                lines.append(f"- `{narrowed_run['run_id']}`: {modules_desc}")
            lines.append("")
        if not entry["metrics"]:
            lines.append(entry["no_gating_metric_reason"])
            lines.append("")
            magnitudes = entry["measurement_only_magnitudes"]
            if magnitudes:
                lines.append("| Magnitude | Runs | Measurement detected (non-gating dispersion) |")
                lines.append("|---|---|---|")
                for magnitude in sorted(magnitudes, key=_magnitude_sort_key):
                    m_entry = magnitudes[magnitude]
                    lines.append(
                        f"| {fmt(magnitude)} | {m_entry['run_count']} | "
                        f"{cell(m_entry['measurement_detected'])} |"
                    )
                lines.append("")
            continue
        for metric in sorted(entry["metrics"]):
            metric_entry = entry["metrics"][metric]
            lines.append(f"**{metric}**")
            lines.append("")
            lines.append(
                "| Magnitude | Runs | Stable | Repeatability | Absolute delta | Percent of baseline |"
            )
            lines.append("|---|---|---|---|---|---|")
            for candidate in metric_entry["candidates"]:
                percent_value = candidate["percent_of_baseline"]
                percent_str = (
                    percent_value if percent_value == RATE_UNDEFINED else f"{fmt(percent_value)}%"
                )
                lines.append(
                    "| " + fmt(candidate["magnitude"])
                    + " | " + str(candidate["run_count"])
                    + " | " + cell(candidate["stable"])
                    + " | " + ",".join(str(v) for v in candidate["repeatability_verdicts"])
                    + " | " + fmt(candidate["absolute_delta"])
                    + " | " + percent_str
                    + " |"
                )
            smallest_detected = metric_entry["smallest_detected"]
            lines.append("")
            if smallest_detected:
                lines.append(
                    f"Smallest detected magnitude: {fmt(smallest_detected['magnitude'])} "
                    f"(repeatability {','.join(str(v) for v in smallest_detected['repeatability_verdicts'])})."
                )
            else:
                lines.append(
                    "No magnitude in this population was gate detected with a stable "
                    "repeatability verdict."
                )
            lines.append("")

    matrix_section = sidecar["confusion_matrix"]
    matrix = matrix_section["matrix"]
    reconciliation = matrix_section["reconciliation"]
    lines.extend([
        SECTION_HEADINGS[8], "",
        "One run-level 2x3 matrix. Rows are the ground truth the run was dispatched with; "
        "columns are the recomputed verdict.",
        "",
        "| Ground truth | PASS | FAIL | INCONCLUSIVE |",
        "|---|---|---|---|",
    ])
    for row_name in ("unchanged code", "seeded regression"):
        row = matrix[row_name]
        lines.append(
            f"| {row_name} | {row[perf_gate_evaluator.VERDICT_PASS]} | "
            f"{row[perf_gate_evaluator.VERDICT_FAIL]} | {row[perf_gate_evaluator.VERDICT_INCONCLUSIVE]} |"
        )
    lines.extend([
        "",
        f"Matrix total: {reconciliation['matrix_total']}; outside-matrix total: "
        f"{reconciliation['outside_total']}; accepted total: {reconciliation['accepted_total']}.",
        "",
    ])

    outside = matrix_section["outside_matrix"]
    lines.extend([SECTION_HEADINGS[9], "", "| Category | Count |", "|---|---|"])
    for category in sorted(outside["counts"]):
        lines.append(f"| {category} | {outside['counts'][category]} |")
    lines.append("")
    if outside["runs"]:
        lines.append("Runs held outside the matrix:")
        lines.append("")
        for entry in outside["runs"]:
            lines.append(f"- `{entry['run_id']}` ({entry['category']})")
        lines.append("")

    threshold = sidecar["threshold_derivations"]
    census = threshold["census"]
    lines.extend([
        SECTION_HEADINGS[10], "",
        threshold["pooled_reconciliation_note"],
        "",
        f"- Total cells: {census.get('total_cells')}",
        f"- Measured cells: {census.get('measured_cells')}",
        f"- Gating cells: {census.get('gating_cells')}",
        f"- Gating metrics: {census.get('gating_metrics')}",
        "",
        "| Benchmark | Metric | Observed value | n | Spread | CPU models | Derivation |",
        "|---|---|---|---|---|---|---|",
    ])
    for row in threshold["cells"]:
        lines.append(
            "| " + row["benchmark"]
            + " | " + row["metric"]
            + " | " + fmt(row["observed_value"])
            + " | " + str(row["n"])
            + " | " + fmt(row["spread"])
            + " | " + ", ".join(row["cpu_models"] or [])
            + " | " + row["derivation"]
            + " |"
        )
    lines.append("")

    budget = sidecar["budget"]
    boundary_note = " (at the boundary)" if budget["at_boundary"] else ""
    total_stats = budget["stages"]["total"]
    lines.extend([
        SECTION_HEADINGS[11], "",
        f"Budget: {fmt(budget['budget_seconds'])}s.",
        "",
        "| Stage | n | Median (s) | Min (s) | Max (s) |",
        "|---|---|---|---|---|",
    ])
    for stage in perf_gate_ab_runner.TIMING_STAGE_ORDER:
        stats = budget["stages"][stage]
        lines.append(
            f"| {stage} | {stats['n']} | {cell(stats['median'])} | {cell(stats['minimum'])} | "
            f"{cell(stats['maximum'])} |"
        )
    lines.extend([
        "",
        f"Measured total median {cell(total_stats['median'])}s against the {fmt(budget['budget_seconds'])}s "
        f"budget{boundary_note}: {budget['reason']}.",
        "",
        "Measured seconds per round per leg -- candidate: "
        f"{cell(budget['seconds_per_round_per_leg'].get(perf_gate_ab_runner.LEG_CANDIDATE))}, merge_base: "
        f"{cell(budget['seconds_per_round_per_leg'].get(perf_gate_ab_runner.LEG_MERGE_BASE))}.",
        f"Headroom to the budget: {cell(budget['headroom_seconds'])}s. Additional rounds per leg that "
        f"headroom buys: {cell(budget['additional_rounds_affordable'])}.",
        "",
        budget["no_projection_note"],
        "",
    ])
    if budget["excluded_runs"]:
        lines.append("Runs excluded from the per-round figure (zero completed rounds):")
        lines.append("")
        for entry in budget["excluded_runs"]:
            lines.append(f"- `{entry['run_id']}` ({entry['leg']}): {entry['reason']}")
        lines.append("")

    return "\n".join(lines) + "\n"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs-dir", default=DEFAULT_RUNS_DIR)
    parser.add_argument("--baseline", default=DEFAULT_BASELINE)
    parser.add_argument("--budget-seconds", type=float, default=DEFAULT_BUDGET_SECONDS)
    parser.add_argument("--out-md", default=DEFAULT_OUT_MD)
    parser.add_argument("--out-json", default=DEFAULT_OUT_JSON)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    runs_dir = Path(args.runs_dir)
    record_paths = sorted(runs_dir.glob(f"*{GATE_RECORD_SUFFIX}")) if runs_dir.is_dir() else []
    verdict_paths = sorted(runs_dir.glob(f"*{VERDICT_SUFFIX}")) if runs_dir.is_dir() else []
    population = build_population(record_paths, verdict_paths)

    if not population["accepted"]:
        print(
            "No gate-validation records survived population membership. "
            f"Skipped: {population['skipped_counts']}"
        )
        return 1

    try:
        baseline = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        print(f"Could not read or parse the baseline sidecar: {args.baseline}")
        return 1
    if not isinstance(baseline, dict):
        print(f"Baseline sidecar is not a JSON object: {args.baseline}")
        return 1

    recomputed = recompute_verdicts(population, baseline)
    sidecar = build_sidecar(
        population=population,
        recomputed=recomputed,
        baseline=baseline,
        runs_dir=str(runs_dir),
        baseline_path=str(args.baseline),
        budget_seconds=args.budget_seconds,
    )
    markdown = render_markdown(sidecar)

    perf_campaign_report.write_deterministic_json(Path(args.out_json), sidecar)
    out_md = Path(args.out_md)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown, encoding="utf-8")

    return 0


if __name__ == "__main__":
    sys.exit(main())
# ----------------------------------------------------------------------------
