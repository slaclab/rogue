#!/usr/bin/env python3
# ----------------------------------------------------------------------------
# Title      : ROGUE Perf Gate Evaluator
# ----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
# ----------------------------------------------------------------------------

"""Per-cell candidate-versus-merge-base gate decision.

Reads a two-leg record (a candidate build's benchmarks paired against a
merge-base build's benchmarks, both measured by the tests/perf/_perf_harness.py
harness under scripts/perf_gate_ab_runner.py) and scripts/perf_gate_baseline.py's
committed gate-baseline.json, and decides, cell by cell, whether the candidate
regressed. Only a cell whose baseline gate_rule is exact-equality can ever
carry a FAIL: a candidate and a merge-base value are compared exactly as
recorded, with no tolerance, epsilon, or rounding step anywhere on that path.
Every other input state this module can observe -- a missing metric, a
benchmark that errored, a merge-base build that failed, a declared tree-hash
pair mismatch, a secondary steal or cgroup flag on a contributing measurement
window, a within-run disagreement between a leg's own clean samples, or a
missing baseline cell -- resolves to a named INCONCLUSIVE reason rather than
raising or silently passing. Nothing here ever maps to FAIL except a real
gating-cell difference.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parent
TESTS_PERF_DIR = SCRIPTS_DIR.parent / "tests" / "perf"
if str(TESTS_PERF_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_PERF_DIR))

# Imported by bare module name (never `tests.perf._perf_harness`), exactly as
# scripts/perf_campaign_report.py imports it, so this module stays runnable on a machine
# where a stray top-level `tests` package shadows this repository's own `tests/` namespace
# package.
import _perf_harness  # noqa: E402  (flat sibling import, path inserted above)


EVALUATOR_SCHEMA_VERSION = 1

VERDICT_PASS = "PASS"
VERDICT_FAIL = "FAIL"
VERDICT_INCONCLUSIVE = "INCONCLUSIVE"

# The gate baseline's own gate-rule label naming a per-cell candidate-versus-merge-base
# comparison, mirrored here as a plain string rather than an import of
# scripts/perf_gate_baseline.py: this module reads only the baseline's committed JSON, never
# the generator module that produced it. Must stay equal to
# perf_gate_baseline.GATE_RULE_EXACT_EQUALITY's value.
_GATE_RULE_EXACT_EQUALITY = "exact-equality"

REASON_INSUFFICIENT_CLEAN_SAMPLES = _perf_harness.REASON_INSUFFICIENT_CLEAN_SAMPLES
REASON_GUARD_EXCEEDED = _perf_harness.REASON_GUARD_EXCEEDED
REASON_METRIC_ABSENT = "metric-absent-from-leg"
REASON_BENCHMARK_ERRORED = "benchmark-errored"
REASON_MERGE_BASE_BUILD_FAILED = "merge-base-build-failed"
REASON_TREE_HASH_PAIR_MISMATCH = "tree-hash-pair-mismatch"
REASON_SECONDARY_FLAG = "secondary-window-flag"
# A condition the phase context's own enumerated list did not name: surfaced under its own
# name and counted separately rather than folded into REASON_INSUFFICIENT_CLEAN_SAMPLES,
# because a deterministic leg whose own clean samples disagree with each other inside one
# run is a distinct fact from a leg that could not obtain enough samples at all. Like every
# other condition here, it is non-blocking: nothing maps to FAIL.
REASON_WITHIN_RUN_UNSTABLE = "within-run-nondeterminism"
REASON_NO_GATING_CELL = "no-gating-cell-evaluated"
REASON_BASELINE_CELL_MISSING = "baseline-cell-missing"
# The trusted baseline itself does not exist yet at the pull request's merge base -- not
# present but broken, simply not there at all. This is the normal, expected state for a
# pull request whose base branch predates the baseline file, most obviously the pull
# request that introduces it, so it resolves to a non-blocking INCONCLUSIVE rather than the
# loud, non-verdict failure a corrupt or unparseable baseline still gets from main() below.
REASON_TRUSTED_BASELINE_ABSENT = "trusted-baseline-absent"

# Declared in a fixed order so condition_counts' row order never depends on which
# conditions happened to fire in a given run, even when two conditions tie on count.
INCONCLUSIVE_CONDITIONS: tuple[str, ...] = (
    REASON_INSUFFICIENT_CLEAN_SAMPLES,
    REASON_GUARD_EXCEEDED,
    REASON_METRIC_ABSENT,
    REASON_BENCHMARK_ERRORED,
    REASON_MERGE_BASE_BUILD_FAILED,
    REASON_TREE_HASH_PAIR_MISMATCH,
    REASON_SECONDARY_FLAG,
    REASON_WITHIN_RUN_UNSTABLE,
    REASON_NO_GATING_CELL,
    REASON_BASELINE_CELL_MISSING,
    REASON_TRUSTED_BASELINE_ABSENT,
)

# The exhaustive, disjoint partition of INCONCLUSIVE_CONDITIONS the in-job retry decision
# (scripts/perf_gate_ab_runner.py) is taken against: it never retries on a condition outside
# this partition. Each tuple below is built by filtering INCONCLUSIVE_CONDITIONS itself
# against an explicit membership set, so both preserve the declared order by construction and
# neither can drift out of it as the vocabulary evolves.
#
# Retry-eligible: transient or contention-driven conditions a re-measurement can plausibly
# change. insufficient-clean-samples, guard-exceeded, secondary-window-flag, and
# within-run-nondeterminism are all noise on an otherwise-measurable cell; benchmark-errored
# is a benchmark process that crashed once and may not crash again.
#
# metric-absent-from-leg is also classified retry-eligible here, closing the one condition the
# locked five-retryable/four-structural split left unassigned. The dominant real cause of a
# metric missing from one leg is a round that was deadline-truncated or failed and so wrote no
# benchmark entry at all -- precisely the transient class a retry fixes. Being wrong in this
# direction costs one narrow retry pass that then reports the identical verdict; being wrong in
# the other direction (classifying it structural) would silently lose the retry on the most
# common transient failure this project's own campaign observed.
_RETRY_ELIGIBLE_REASONS = frozenset((
    REASON_INSUFFICIENT_CLEAN_SAMPLES,
    REASON_GUARD_EXCEEDED,
    REASON_SECONDARY_FLAG,
    REASON_WITHIN_RUN_UNSTABLE,
    REASON_BENCHMARK_ERRORED,
    REASON_METRIC_ABSENT,
))

# Structural: a re-measurement cannot change any of these, so retrying one would only burn
# budget to reach the identical verdict. A declared tree-hash-pair mismatch or a failed
# merge-base build describes the run itself, not any one measurement; a missing baseline cell
# or zero gating cells evaluated describes the baseline, not the measurement. An absent
# trusted baseline joins this side for the same reason: re-measuring cannot make a baseline
# file that does not exist at the merge base appear, so retrying would only spend a full
# paired build on a foregone outcome.
_STRUCTURAL_REASONS = frozenset((
    REASON_TREE_HASH_PAIR_MISMATCH,
    REASON_MERGE_BASE_BUILD_FAILED,
    REASON_BASELINE_CELL_MISSING,
    REASON_NO_GATING_CELL,
    REASON_TRUSTED_BASELINE_ABSENT,
))

RETRY_ELIGIBLE_CONDITIONS: tuple[str, ...] = tuple(
    condition for condition in INCONCLUSIVE_CONDITIONS if condition in _RETRY_ELIGIBLE_REASONS
)
STRUCTURAL_CONDITIONS: tuple[str, ...] = tuple(
    condition for condition in INCONCLUSIVE_CONDITIONS if condition in _STRUCTURAL_REASONS
)

DEFAULT_BASELINE_PATH = "docs/plans/perf-ci-hardening/gate-baseline.json"

# The single declaration of the documentation path rendered into every FAIL and
# INCONCLUSIVE step summary, so a contributor whose check went red always lands on the same
# file this module's own tests bind their quoted vocabulary against.
PERF_DOC_PATH = "tests/perf/README.md"
DOC_POINTER_LINE = f"See `{PERF_DOC_PATH}` for what this verdict means and how to reproduce it locally."

# Paired with the zero-cell baseline `_substituted_empty_baseline()` returns for the paired
# runner's own retry decision, when that read cannot read or parse the real baseline sidecar.
# This is not a new INCONCLUSIVE condition: `evaluate_run`'s own zero-gating-cells branch
# already resolves a zero-cell baseline to `REASON_NO_GATING_CELL`, so this constant only
# names the concrete cause behind that condition when the cause is a broken baseline rather
# than a baseline that legitimately declares no gating cells. `main()`'s own baseline read,
# below, no longer substitutes this: an unreadable or unparseable baseline there returns 2
# instead, because that read decides the published verdict rather than a cheap in-job retry.
BASELINE_UNAVAILABLE_REASON = "baseline-unreadable-or-unparseable"

# The single declaration of the gating job's ten minute wall-clock budget, in seconds.
# scripts/perf_gate_validation_report.py's own DEFAULT_BUDGET_SECONDS mirrors this constant
# rather than declaring the figure a second time, following the same pattern that module
# already uses for the two schema-version constants. The numeric value must never move
# without moving here first.
GATE_BUDGET_SECONDS = 600.0

# --- The commit-trailer escape hatch: grammar, statuses, and rejection reasons --------------
#
# A single trailer, `Perf-Gate-Override: <cell-list>;<justification>`, on the pull request's
# head commit only. The cell list is comma-separated `benchmark.metric` tokens; the
# first semicolon separates the cell list from the justification. Twenty Unicode code points
# was chosen as the minimum justification length because it rejects a bare affirmative ("yes"),
# a bare word ("known"), and a bare issue reference ("see #1234") -- exactly the values that
# would turn the hatch into a rubber stamp -- while accepting any real sentence.
OVERRIDE_TRAILER_KEY = "Perf-Gate-Override"
OVERRIDE_CELL_SEPARATOR = ","
OVERRIDE_JUSTIFICATION_SEPARATOR = ";"
OVERRIDE_MIN_JUSTIFICATION_CHARS = 20

# The rendered raw trailer is attacker-controlled content reaching the step summary verbatim.
# Bounding it keeps one rejected override from dominating the rendered output regardless of
# how long a crafted trailer value is.
OVERRIDE_RAW_VALUE_RENDER_MAX_CHARS = 200

# An accepted override's own justification is just as attacker-controlled as a rejected
# trailer's raw value (parse_override_trailer preserves it exactly, including any interior
# newline, and imposes no maximum length), so it needs the same kind of bound before it
# reaches the step summary. A legitimate justification is prose rather than a raw trailer, so
# it gets a more generous ceiling than the raw trailer value above.
OVERRIDE_JUSTIFICATION_RENDER_MAX_CHARS = 500

# Anchored at both ends: a benchmark component of letters, digits, and underscores (the
# transaction benchmark identities are camelCase, so letter case must be accepted) and a
# metric component of lowercase letters, digits, and underscores. Neither component can
# contain a dot or any shell metacharacter, path separator, leading dash, or wildcard, so
# nothing but a well-formed cell name can ever survive this pattern and reach a later argv.
OVERRIDE_CELL_TOKEN_PATTERN = re.compile(r"^([A-Za-z0-9_]+)\.([a-z0-9_]+)$")

OVERRIDE_STATUS_ABSENT = "absent"
OVERRIDE_STATUS_REJECTED = "rejected"
OVERRIDE_STATUS_ACCEPTED = "accepted"

OVERRIDE_REJECTED_NO_SEMICOLON = "no-semicolon-separator"
OVERRIDE_REJECTED_EMPTY_JUSTIFICATION = "empty-justification"
OVERRIDE_REJECTED_JUSTIFICATION_TOO_SHORT = "justification-below-minimum-length"
OVERRIDE_REJECTED_EMPTY_CELL_LIST = "empty-cell-list"
OVERRIDE_REJECTED_MALFORMED_CELL_TOKEN = "malformed-cell-token"

OVERRIDE_UNMATCHED_NOT_FAILING = "gating-but-not-failing"
OVERRIDE_UNMATCHED_NOT_GATING = "present-but-not-gating"
OVERRIDE_UNMATCHED_ABSENT_FROM_BASELINE = "absent-from-baseline"


def _numeric(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _substituted_empty_baseline() -> tuple[dict[str, Any], str]:
    """A zero-cell baseline mapping, paired with `BASELINE_UNAVAILABLE_REASON`, substituted
    by the paired runner's own single in-job retry decision (`_load_baseline_for_retry`) when
    the baseline sidecar it reads cannot be read or parsed. That read only decides whether one
    narrow re-measurement follows: degrading to no retry there is safe and cheap, since a
    measurement run whose build cost has already been paid should not be aborted over a
    baseline it does not strictly need. This module's own `main()` does not call this
    function: its baseline read decides the published verdict, so it fails loudly instead of
    substituting a zero-cell baseline in its place."""
    return {"cells": {}}, BASELINE_UNAVAILABLE_REASON


def _baseline_unavailable_evaluation(baseline_unavailable_reason: str) -> dict[str, Any]:
    """The full published verdict shape for a trusted baseline that does not exist yet at
    the pull request's merge base: a non-blocking INCONCLUSIVE carrying
    `REASON_TRUSTED_BASELINE_ABSENT`, with zero cells evaluated because there is nothing
    committed at the merge base to compare against. Distinct from `evaluate_run`'s own
    zero-gating-cell branch (which still runs a real, if trivial, evaluation over a baseline
    that parses but declares no cells) and from `main()`'s own loud `--baseline` read
    failure below (a baseline that is present at the merge base but corrupt or unparseable,
    an upstream defect a human must fix): this path never attempts to read `--record` or
    `--baseline` at all, so `main()` builds this shape directly rather than calling
    `evaluate_run`, which requires both to already be parsed."""
    return {
        "evaluator_schema_version": EVALUATOR_SCHEMA_VERSION,
        "verdict": VERDICT_INCONCLUSIVE,
        "verdict_reason": REASON_TRUSTED_BASELINE_ABSENT,
        "cells": [],
        "gating_cell_count": 0,
        "failing_cells": [],
        "exempted_cells": [],
        "override": _absent_override_section(),
        "condition_counts": condition_counts([]),
        "tree_hash_pair": {
            "declared_candidate_tree_hash": None,
            "declared_merge_base_tree_hash": None,
            "candidate_tree_hash": None,
            "merge_base_tree_hash": None,
            "tree_hash_pair_match": True,
        },
        "drift_cells": [],
        "contamination_benchmarks": [],
        "budget": {
            "total_seconds": None,
            "budget_seconds": GATE_BUDGET_SECONDS,
            "within_budget": None,
            "retried_total_seconds": None,
        },
        "attempts": [],
        "baseline_unavailable_reason": baseline_unavailable_reason,
    }


def baseline_cell(baseline: dict[str, Any], benchmark: str, metric: str) -> dict[str, Any] | None:
    """The baseline's own cell for `(benchmark, metric)`, or `None` when the baseline
    carries no such cell. Both keys are required positional arguments; there is no
    single-argument form."""
    cells = baseline.get("cells")
    if not isinstance(cells, dict):
        return None
    benchmark_cells = cells.get(benchmark)
    if not isinstance(benchmark_cells, dict):
        return None
    return benchmark_cells.get(metric)


def _leg(record: dict[str, Any], leg: str) -> dict[str, Any] | None:
    legs = record.get("legs")
    if not isinstance(legs, dict):
        return None
    leg_obj = legs.get(leg)
    return leg_obj if isinstance(leg_obj, dict) else None


def _leg_benchmark_entry(record: dict[str, Any], leg: str, benchmark: str) -> dict[str, Any] | None:
    """The raw per-benchmark dict for one leg (carrying `metrics` and
    `measurement_windows`), or `None` when that leg or benchmark is missing."""
    leg_obj = _leg(record, leg)
    if leg_obj is None:
        return None
    benchmarks = leg_obj.get("benchmarks")
    if not isinstance(benchmarks, dict):
        return None
    entry = benchmarks.get(benchmark)
    return entry if isinstance(entry, dict) else None


def leg_metric_entry(
    record: dict[str, Any], leg: str, benchmark: str, metric: str,
) -> dict[str, Any] | None:
    """The metric entry `record.legs.<leg>.benchmarks.<benchmark>.metrics.<metric>`, or
    `None` when any step of that path is missing or malformed. Never raises."""
    bench_entry = _leg_benchmark_entry(record, leg, benchmark)
    if bench_entry is None:
        return None
    metrics = bench_entry.get("metrics")
    if not isinstance(metrics, dict):
        return None
    entry = metrics.get(metric)
    return entry if isinstance(entry, dict) else None


def _has_secondary_flag(bench_entry: dict[str, Any] | None) -> bool:
    """True when any measurement window recorded on this benchmark entry carries a
    nonzero steal or cgroup-throttling secondary flag."""
    if not isinstance(bench_entry, dict):
        return False
    windows = bench_entry.get("measurement_windows")
    if not isinstance(windows, list):
        return False
    for window in windows:
        if isinstance(window, dict) and window.get("secondary_flags"):
            return True
    return False


def leg_value(metric_entry: dict[str, Any] | None) -> tuple[float | int | None, str | None]:
    """`(value, None)`: the single distinct clean sample value, when `metric_entry` is
    `status: ok` (`_perf_harness.STATUS_OK`) and every one of its clean samples is
    identical. Otherwise `(None, reason)` with a named reason: `REASON_METRIC_ABSENT` when
    `metric_entry` itself is missing or malformed, the entry's own recorded reason
    (`REASON_GUARD_EXCEEDED` or `REASON_INSUFFICIENT_CLEAN_SAMPLES`) when its status is not
    `ok`, or `REASON_WITHIN_RUN_UNSTABLE` when the status is `ok` but the clean samples
    themselves disagree."""
    if not isinstance(metric_entry, dict):
        return None, REASON_METRIC_ABSENT

    if metric_entry.get("status") != _perf_harness.STATUS_OK:
        reason = metric_entry.get("reason")
        if reason == REASON_GUARD_EXCEEDED:
            return None, REASON_GUARD_EXCEEDED
        return None, REASON_INSUFFICIENT_CLEAN_SAMPLES

    samples = metric_entry.get("samples")
    clean = [
        sample for sample in samples
        if isinstance(sample, (int, float)) and not isinstance(sample, bool)
    ] if isinstance(samples, list) else []
    if not clean:
        return None, REASON_INSUFFICIENT_CLEAN_SAMPLES
    if min(clean) != max(clean):
        return None, REASON_WITHIN_RUN_UNSTABLE
    return clean[0], None


def _cell_result(
    benchmark: str, metric: str, gate_rule: str | None, gating: bool,
    verdict: str, reason: str | None,
    candidate_value: Any, base_value: Any, delta: Any, delta_pct: Any,
    baseline_value: Any,
    *,
    tier: Any = None,
    baseline_n: Any = None,
    baseline_spread: Any = None,
    baseline_cv: Any = None,
    baseline_mde_pct: Any = None,
    informational_drift: bool = False,
    override_applied: bool = False,
) -> dict[str, Any]:
    return {
        "benchmark": benchmark,
        "metric": metric,
        "gate_rule": gate_rule,
        "gating": gating,
        "verdict": verdict,
        "reason": reason,
        "candidate_value": candidate_value,
        "base_value": base_value,
        "delta": delta,
        "delta_pct": delta_pct,
        "baseline_value": baseline_value,
        "tier": tier,
        "baseline_n": baseline_n,
        "baseline_spread": baseline_spread,
        "baseline_cv": baseline_cv,
        "baseline_mde_pct": baseline_mde_pct,
        "informational_drift": informational_drift,
        "override_applied": override_applied,
    }


def evaluate_cell(
    benchmark: str,
    metric: str,
    candidate_entry: dict[str, Any] | None,
    base_entry: dict[str, Any] | None,
    baseline_entry: dict[str, Any] | None,
) -> dict[str, Any]:
    """One cell's verdict: `PASS` when a gating cell's candidate and base values are
    equal, `FAIL` when they differ (no tolerance, epsilon, or rounding step anywhere on
    this path), and `INCONCLUSIVE` with a named reason for every other input state
    (a missing baseline cell, a missing metric on either leg, or either leg's own
    `leg_value` failing). A non-gating cell always reports `gating: false`; the verdict
    it carries is informational only, since `evaluate_run`'s roll-up ignores it."""
    if baseline_entry is None:
        return _cell_result(
            benchmark, metric, None, False,
            VERDICT_INCONCLUSIVE, REASON_BASELINE_CELL_MISSING,
            None, None, None, None, None,
        )

    gate_rule = baseline_entry.get("gate_rule")
    gating = gate_rule == _GATE_RULE_EXACT_EQUALITY
    baseline_value = baseline_entry.get("observed_value")
    # Pulled off the same baseline cell the gate rule and observed value already come from,
    # never from a render-time registry import: a registry re-bind must never change
    # what an already-published verdict renders as if the tier were resolved at render time.
    tier = baseline_entry.get("tier")
    baseline_n = baseline_entry.get("n")
    baseline_spread = baseline_entry.get("spread")
    baseline_cv = baseline_entry.get("cv")
    baseline_mde_pct = baseline_entry.get("mde_two_sample_pct")
    dispersion_kwargs: dict[str, Any] = {
        "tier": tier,
        "baseline_n": baseline_n,
        "baseline_spread": baseline_spread,
        "baseline_cv": baseline_cv,
        "baseline_mde_pct": baseline_mde_pct,
    }

    if candidate_entry is None or base_entry is None:
        return _cell_result(
            benchmark, metric, gate_rule, gating,
            VERDICT_INCONCLUSIVE, REASON_METRIC_ABSENT,
            None, None, None, None, baseline_value,
            **dispersion_kwargs,
        )

    candidate_value, candidate_reason = leg_value(candidate_entry)
    base_value, base_reason = leg_value(base_entry)

    if candidate_value is None:
        return _cell_result(
            benchmark, metric, gate_rule, gating,
            VERDICT_INCONCLUSIVE, candidate_reason,
            candidate_value, base_value, None, None, baseline_value,
            **dispersion_kwargs,
        )
    if base_value is None:
        return _cell_result(
            benchmark, metric, gate_rule, gating,
            VERDICT_INCONCLUSIVE, base_reason,
            candidate_value, base_value, None, None, baseline_value,
            **dispersion_kwargs,
        )

    delta = candidate_value - base_value
    delta_pct = None if base_value == 0 else (delta / base_value) * 100.0
    verdict = VERDICT_PASS if delta == 0 else VERDICT_FAIL

    # Informational drift: both legs moved together (delta == 0, so verdict is PASS)
    # but the candidate's own value falls outside the baseline cell's recorded minimum-to-
    # maximum band -- the population's own observed range, chosen over the single observed
    # value (which would flag any movement even inside the population's own spread) and over
    # the median (which would need a band width from somewhere this baseline does not
    # separately record). Never resolves to a verdict: an unrelated toolchain change would
    # otherwise silence the gate across the board and would need an eleventh condition.
    informational_drift = False
    if verdict == VERDICT_PASS and gating:
        baseline_min = baseline_entry.get("minimum")
        baseline_max = baseline_entry.get("maximum")
        if (
            _numeric(candidate_value) and _numeric(baseline_min) and _numeric(baseline_max)
            and (candidate_value < baseline_min or candidate_value > baseline_max)
        ):
            informational_drift = True

    return _cell_result(
        benchmark, metric, gate_rule, gating,
        verdict, None,
        candidate_value, base_value, delta, delta_pct, baseline_value,
        informational_drift=informational_drift,
        **dispersion_kwargs,
    )


def condition_counts(cells: list[dict[str, Any]]) -> dict[str, int]:
    """How many times each entry of `INCONCLUSIVE_CONDITIONS` fired, in that declared
    order, with `0` recorded for a condition that never fired -- so two conditions with
    equal counts keep a stable row order. No condition ever maps to FAIL."""
    counts = {condition: 0 for condition in INCONCLUSIVE_CONDITIONS}
    for cell in cells:
        if cell.get("verdict") != VERDICT_INCONCLUSIVE:
            continue
        reason = cell.get("reason")
        if reason in counts:
            counts[reason] += 1
    return counts


def parse_override_trailer(
    value: str | None, *, author: str | None = None, unavailable_reason: str | None = None,
) -> dict[str, Any]:
    """Parse a `Perf-Gate-Override` commit-trailer value into an override section. Never
    raises on any input string. An absent, empty, or whitespace-only `value` returns an
    absent status with no cells and no justification -- not using the hatch is the normal
    case, and no rejection is reported as an error for it. A well-formed value returns an
    accepted status carrying the requested `(benchmark, metric)` cell pairs in the order
    given with duplicates removed, and the justification with only its surrounding
    whitespace stripped -- interior text, including newlines and non-ASCII characters, is
    preserved exactly, since the recorded justification is the artifact a reviewer reads.
    `unavailable_reason`, when supplied by the caller, is carried through verbatim and never
    interpreted here; it is the workflow's own signal that the trailer parser itself was
    unavailable on the runner, not a property of `value`."""
    raw_value = value
    stripped = value.strip() if isinstance(value, str) else ""

    if not stripped:
        return {
            "raw_value": raw_value,
            "status": OVERRIDE_STATUS_ABSENT,
            "rejection_reason": None,
            "justification": None,
            "author": author,
            "requested_cells": [],
            "matched_cells": [],
            "unmatched_cells": [],
            "unavailable_reason": unavailable_reason,
        }

    if OVERRIDE_JUSTIFICATION_SEPARATOR not in stripped:
        return _rejected_override(raw_value, author, unavailable_reason, OVERRIDE_REJECTED_NO_SEMICOLON)

    cells_part, _, justification_part = stripped.partition(OVERRIDE_JUSTIFICATION_SEPARATOR)
    justification = justification_part.strip()
    if not justification:
        return _rejected_override(
            raw_value, author, unavailable_reason, OVERRIDE_REJECTED_EMPTY_JUSTIFICATION,
        )
    if len(justification) < OVERRIDE_MIN_JUSTIFICATION_CHARS:
        return _rejected_override(
            raw_value, author, unavailable_reason, OVERRIDE_REJECTED_JUSTIFICATION_TOO_SHORT,
        )

    raw_tokens = [token.strip() for token in cells_part.split(OVERRIDE_CELL_SEPARATOR)]
    raw_tokens = [token for token in raw_tokens if token]
    if not raw_tokens:
        return _rejected_override(raw_value, author, unavailable_reason, OVERRIDE_REJECTED_EMPTY_CELL_LIST)

    requested_cells: list[tuple[str, str]] = []
    seen_tokens: set[str] = set()
    for token in raw_tokens:
        match = OVERRIDE_CELL_TOKEN_PATTERN.match(token)
        if not match:
            return _rejected_override(
                raw_value, author, unavailable_reason, OVERRIDE_REJECTED_MALFORMED_CELL_TOKEN,
            )
        if token in seen_tokens:
            continue
        seen_tokens.add(token)
        requested_cells.append((match.group(1), match.group(2)))

    return {
        "raw_value": raw_value,
        "status": OVERRIDE_STATUS_ACCEPTED,
        "rejection_reason": None,
        "justification": justification,
        "author": author,
        "requested_cells": requested_cells,
        "matched_cells": [],
        "unmatched_cells": [],
        "unavailable_reason": unavailable_reason,
    }


def _rejected_override(
    raw_value: str | None, author: str | None, unavailable_reason: str | None, reason: str,
) -> dict[str, Any]:
    return {
        "raw_value": raw_value,
        "status": OVERRIDE_STATUS_REJECTED,
        "rejection_reason": reason,
        "justification": None,
        "author": author,
        "requested_cells": [],
        "matched_cells": [],
        "unmatched_cells": [],
        "unavailable_reason": unavailable_reason,
    }


def _absent_override_section() -> dict[str, Any]:
    return {
        "raw_value": None,
        "status": OVERRIDE_STATUS_ABSENT,
        "rejection_reason": None,
        "justification": None,
        "author": None,
        "matched_cells": [],
        "unmatched_cells": [],
        "unavailable_reason": None,
    }


def _apply_override(
    override: dict[str, Any] | None,
    cells_out: list[dict[str, Any]],
    all_failing_gating: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    """Partition `all_failing_gating` into exempted cells and still-failing cells against
    `override`, returning `(override_section, exempted_cells, still_failing_cells)`. When
    `override` is `None` or its status is not accepted, nothing is exempted and
    `still_failing_cells` is `all_failing_gating` unchanged -- byte-identical to the
    no-override roll-up. Every named token the exempted list did not consume is classified
    into exactly one of the three unmatched reasons and recorded; an unrecorded name is how a
    hatch quietly widens, so nothing here is silently accepted."""
    if override is None:
        return _absent_override_section(), [], list(all_failing_gating)

    section = {key: value for key, value in override.items() if key != "requested_cells"}

    if override.get("status") != OVERRIDE_STATUS_ACCEPTED:
        section.setdefault("matched_cells", [])
        section.setdefault("unmatched_cells", [])
        return section, [], list(all_failing_gating)

    requested_cells: list[tuple[str, str]] = override.get("requested_cells") or []
    exempted: list[dict[str, Any]] = []
    unmatched: list[dict[str, Any]] = []
    matched_pairs: set[tuple[str, str]] = set()

    for benchmark, metric in requested_cells:
        match = next(
            (
                cell for cell in all_failing_gating
                if cell["benchmark"] == benchmark and cell["metric"] == metric
            ),
            None,
        )
        if match is not None:
            match["override_applied"] = True
            exempted.append(match)
            matched_pairs.add((benchmark, metric))
            continue

        existing = next(
            (
                cell for cell in cells_out
                if cell["benchmark"] == benchmark and cell["metric"] == metric
            ),
            None,
        )
        if existing is None:
            unmatched_reason = OVERRIDE_UNMATCHED_ABSENT_FROM_BASELINE
        elif not existing["gating"]:
            unmatched_reason = OVERRIDE_UNMATCHED_NOT_GATING
        else:
            unmatched_reason = OVERRIDE_UNMATCHED_NOT_FAILING
        unmatched.append({"benchmark": benchmark, "metric": metric, "reason": unmatched_reason})

    still_failing = [
        cell for cell in all_failing_gating
        if (cell["benchmark"], cell["metric"]) not in matched_pairs
    ]

    section["matched_cells"] = [
        {"benchmark": benchmark, "metric": metric} for benchmark, metric in sorted(matched_pairs)
    ]
    section["unmatched_cells"] = unmatched
    return section, exempted, still_failing


def _budget_mapping(record: dict[str, Any]) -> dict[str, Any]:
    """The run's own measured total against `GATE_BUDGET_SECONDS`, plus the retried
    end-to-end total when the record's own `stages.gate_retry` reports a retry ran. Read
    defensively off the record: a record carrying none of these fields (every one of the
    already-committed records) yields null figures rather than raising."""
    timings = record.get("timings")
    timings = timings if isinstance(timings, dict) else {}
    total_seconds = timings.get("total")
    total_seconds = total_seconds if _numeric(total_seconds) else None

    within_budget = None if total_seconds is None else total_seconds <= GATE_BUDGET_SECONDS

    stages = record.get("stages")
    stages = stages if isinstance(stages, dict) else {}
    gate_retry = stages.get("gate_retry")
    gate_retry = gate_retry if isinstance(gate_retry, dict) else {}

    retried_total_seconds = None
    if gate_retry.get("ran"):
        elapsed = gate_retry.get("elapsed_seconds")
        elapsed = elapsed if isinstance(elapsed, dict) else {}
        numeric_values = [value for value in elapsed.values() if _numeric(value)]
        if numeric_values:
            retried_total_seconds = sum(numeric_values)

    return {
        "total_seconds": total_seconds,
        "budget_seconds": GATE_BUDGET_SECONDS,
        "within_budget": within_budget,
        "retried_total_seconds": retried_total_seconds,
    }


def _attempts_rollup(record: dict[str, Any]) -> list[dict[str, Any]]:
    """One entry per `record.run.attempts` entry, each carrying its attempt index, verdict,
    and whether a retry followed, read defensively so a record carrying no attempts array
    (every one of the already-committed records) yields an empty list rather than raising."""
    run_info = record.get("run")
    run_info = run_info if isinstance(run_info, dict) else {}
    attempts = run_info.get("attempts")
    if not isinstance(attempts, list):
        return []
    rollup = []
    for entry in attempts:
        if not isinstance(entry, dict):
            continue
        rollup.append({
            "attempt": entry.get("attempt"),
            "verdict": entry.get("verdict"),
            "retried": entry.get("retried"),
        })
    return rollup


def evaluate_run(
    record: dict[str, Any], baseline: dict[str, Any], *, override: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Evaluate every cell the baseline itself declares, in sorted (benchmark, metric)
    order, and roll up the run verdict: any gating `FAIL` gives `FAIL`; else any gating
    `INCONCLUSIVE` gives `INCONCLUSIVE`; else `PASS`. Zero gating cells evaluated gives
    `INCONCLUSIVE` with `REASON_NO_GATING_CELL`, never `PASS`.

    A declared tree-hash-pair mismatch (`record.run.tree_hash_pair_match` false) or a
    failed merge-base build (`record.legs.merge_base.build.success` false) resolves every
    cell to its own named INCONCLUSIVE reason without inspecting any individual metric: a
    run that measured the wrong tree, or never built the comparison side at all, cannot
    speak to any cell's outcome. A secondary steal or cgroup-throttling flag recorded on
    either leg's own measurement windows for a benchmark, or an `error` recorded against
    either leg's benchmark entry, likewise resolves every cell of that benchmark to its own
    named INCONCLUSIVE reason rather than comparing values that were measured under
    contention or never measured at all.
    """
    run_info = record.get("run")
    run_info = run_info if isinstance(run_info, dict) else {}
    tree_hash_pair_match = run_info.get("tree_hash_pair_match", True)

    merge_base_leg = _leg(record, "merge_base")
    merge_base_build = (merge_base_leg or {}).get("build")
    merge_base_build = merge_base_build if isinstance(merge_base_build, dict) else {}
    merge_base_build_failed = merge_base_build.get("success") is False

    baseline_cells = baseline.get("cells")
    baseline_cells = baseline_cells if isinstance(baseline_cells, dict) else {}

    cells_out: list[dict[str, Any]] = []
    for benchmark in sorted(baseline_cells):
        metric_map = baseline_cells[benchmark]
        if not isinstance(metric_map, dict):
            continue

        candidate_bench_entry = _leg_benchmark_entry(record, "candidate", benchmark)
        base_bench_entry = _leg_benchmark_entry(record, "merge_base", benchmark)
        benchmark_errored = bool(
            (candidate_bench_entry or {}).get("error") or (base_bench_entry or {}).get("error")
        )
        secondary_flag = _has_secondary_flag(candidate_bench_entry) or _has_secondary_flag(base_bench_entry)

        for metric in sorted(metric_map):
            baseline_entry = metric_map[metric]

            if not tree_hash_pair_match:
                cell = evaluate_cell(benchmark, metric, None, None, baseline_entry)
                cell["reason"] = REASON_TREE_HASH_PAIR_MISMATCH
                cell["verdict"] = VERDICT_INCONCLUSIVE
            elif merge_base_build_failed:
                cell = evaluate_cell(benchmark, metric, None, None, baseline_entry)
                cell["reason"] = REASON_MERGE_BASE_BUILD_FAILED
                cell["verdict"] = VERDICT_INCONCLUSIVE
            elif secondary_flag:
                cell = evaluate_cell(benchmark, metric, None, None, baseline_entry)
                cell["reason"] = REASON_SECONDARY_FLAG
                cell["verdict"] = VERDICT_INCONCLUSIVE
            elif benchmark_errored:
                cell = evaluate_cell(benchmark, metric, None, None, baseline_entry)
                cell["reason"] = REASON_BENCHMARK_ERRORED
                cell["verdict"] = VERDICT_INCONCLUSIVE
            else:
                candidate_entry = leg_metric_entry(record, "candidate", benchmark, metric)
                base_entry = leg_metric_entry(record, "merge_base", benchmark, metric)
                cell = evaluate_cell(benchmark, metric, candidate_entry, base_entry, baseline_entry)

            cells_out.append(cell)

    gating_cells = [cell for cell in cells_out if cell["gating"]]
    all_failing_gating = [cell for cell in gating_cells if cell["verdict"] == VERDICT_FAIL]

    # Additive: with no override (the default), override_section carries an absent status,
    # exempted_cells is empty, and failing_cells is all_failing_gating unchanged -- the
    # roll-up below is then byte-identical to the pre-override behaviour, which the published
    # validation report's own call site (two positional arguments, no keyword) depends on.
    override_section, exempted_cells, failing_cells = _apply_override(
        override, cells_out, all_failing_gating,
    )

    if failing_cells:
        verdict = VERDICT_FAIL
        verdict_reason = None
    elif not gating_cells:
        verdict = VERDICT_INCONCLUSIVE
        verdict_reason = REASON_NO_GATING_CELL
    elif any(cell["verdict"] == VERDICT_INCONCLUSIVE for cell in gating_cells):
        verdict = VERDICT_INCONCLUSIVE
        verdict_reason = None
    else:
        verdict = VERDICT_PASS
        verdict_reason = None

    drift_cells = [cell for cell in cells_out if cell.get("informational_drift")]
    contamination_benchmarks = sorted({
        cell["benchmark"] for cell in cells_out if cell.get("reason") == REASON_SECONDARY_FLAG
    })

    return {
        "evaluator_schema_version": EVALUATOR_SCHEMA_VERSION,
        "verdict": verdict,
        "verdict_reason": verdict_reason,
        "cells": cells_out,
        "gating_cell_count": len(gating_cells),
        "failing_cells": failing_cells,
        "exempted_cells": exempted_cells,
        "override": override_section,
        "condition_counts": condition_counts(cells_out),
        "tree_hash_pair": {
            "declared_candidate_tree_hash": run_info.get("declared_candidate_tree_hash"),
            "declared_merge_base_tree_hash": run_info.get("declared_merge_base_tree_hash"),
            "candidate_tree_hash": run_info.get("candidate_tree_hash"),
            "merge_base_tree_hash": run_info.get("merge_base_tree_hash"),
            "tree_hash_pair_match": tree_hash_pair_match,
        },
        "drift_cells": drift_cells,
        "contamination_benchmarks": contamination_benchmarks,
        "budget": _budget_mapping(record),
        "attempts": _attempts_rollup(record),
    }


def _fmt_cell(value: Any) -> str:
    return "n/a" if value is None else str(value)


def _fmt_seconds_cell(value: Any) -> str:
    """`_fmt_cell`, but the `s` unit suffix is only glued on when there is an actual number to
    glue it to; an absent value renders as the bare `n/a` placeholder rather than `n/as`."""
    return "n/a" if value is None else f"{value}s"


def _collapse_and_neutralize_for_summary(text: str) -> str:
    """Collapse any carriage return or newline in `text` onto a single space, and replace
    every backtick with a straight quote. Shared by every renderer below that wraps a
    contributor-controlled value in a single pair of backticks or places it inline in the
    step summary: without this, an embedded backtick in the value closes that code span
    early (or, unwrapped, still risks pairing with a later backtick in the same rendered
    paragraph), letting the remainder of the value be parsed as ordinary markdown instead of
    staying inert."""
    text = text.replace("\r\n", " ").replace("\r", " ").replace("\n", " ")
    return text.replace("`", "'")


def _render_raw_override_trailer(raw_value: Any) -> str:
    """Render a contributor-controlled `Perf-Gate-Override` trailer value safely inside a
    markdown step summary. `raw_value` reaches this renderer verbatim from the pull request's
    own commit message, and `parse_override_trailer` preserves any interior newline or
    markdown control character exactly, so rendering it unmodified would let a crafted commit
    message break the markdown structure of every section that follows it. Collapsed onto one
    line, with every backtick neutralized so it cannot break out of the caller's own wrapping
    code span, and truncated to `OVERRIDE_RAW_VALUE_RENDER_MAX_CHARS` with the truncation
    marked visibly when it fires."""
    text = _collapse_and_neutralize_for_summary(_fmt_cell(raw_value))
    if len(text) > OVERRIDE_RAW_VALUE_RENDER_MAX_CHARS:
        text = text[:OVERRIDE_RAW_VALUE_RENDER_MAX_CHARS] + " (truncated)"
    return text


def _render_override_justification(justification: Any) -> str:
    """Render an accepted override's contributor-controlled justification safely inside a
    markdown step summary. `justification` reaches this renderer verbatim from the accepted
    override section, and `parse_override_trailer` preserves any interior newline exactly and
    imposes no maximum length, so rendering it unmodified would let a crafted commit trailer
    inject a markdown heading, a table, or an unbounded block of text into the step summary --
    the same risk `_render_raw_override_trailer` above already guards its own value against.
    Collapsed onto one line, with every backtick neutralized for the same reason, and
    truncated to `OVERRIDE_JUSTIFICATION_RENDER_MAX_CHARS` with the truncation marked visibly
    when it fires."""
    text = _collapse_and_neutralize_for_summary(_fmt_cell(justification))
    if len(text) > OVERRIDE_JUSTIFICATION_RENDER_MAX_CHARS:
        text = text[:OVERRIDE_JUSTIFICATION_RENDER_MAX_CHARS] + " (truncated)"
    return text


def _cell_sort_key(cell: dict[str, Any]) -> tuple[str, str]:
    return (cell["benchmark"], cell["metric"])


def render_summary_markdown(evaluation: dict[str, Any], *, report_only: bool = False) -> str:
    """A byte-stable markdown block naming the verdict, the gating cell count, and the wall
    clock measured against the single declared budget, then an escape-hatch section whenever
    an override was accepted or rejected (on every verdict, not only FAIL: the escape-hatch
    outcome must land in the step summary regardless of what the run measured), then one of
    three verdict-shaped bodies: on FAIL, every failing gating cell (not only the first) with
    its tier and dispersion figures, the exempted-cells table, and the contamination list; on
    INCONCLUSIVE, every condition that fired, the inconclusive gating cells with their
    reasons, the retry outcome, and a plain statement that this does not block; on PASS, the
    informational drift table when drift exists. The FAIL and INCONCLUSIVE bodies each end
    with `DOC_POINTER_LINE`, naming the file that explains what the verdict means and how to
    reproduce it locally; a PASS summary carries no such pointer, since it names only the
    verdict, the gating cell count, the wall clock against the budget, and any informational
    drift. Every table renders in sorted (benchmark,
    metric) order and the condition-counts table keeps `INCONCLUSIVE_CONDITIONS`' own
    declared order even when two conditions tie. Deterministic over the same `evaluation`
    input: no wall-clock timestamp anywhere in the output. When `report_only` is true and the
    verdict is FAIL, a further line states this outcome would have blocked once the gate is
    flipped to blocking; a PASS or INCONCLUSIVE evaluation renders no such line regardless of
    `report_only`."""
    verdict = evaluation["verdict"]

    lines = [
        "<!-- generated by scripts/perf_gate_evaluator.py, do not edit by hand -->",
        "# Perf Gate Evaluation",
        "",
        f"Verdict: {verdict}",
    ]
    if evaluation.get("verdict_reason"):
        lines.append(f"Verdict reason: {evaluation['verdict_reason']}")
    lines.append(f"Gating cells evaluated: {evaluation['gating_cell_count']}")
    lines.append("")

    budget = evaluation.get("budget") or {}
    lines.append("## Budget")
    lines.append("")
    lines.append(
        f"Wall clock: {_fmt_seconds_cell(budget.get('total_seconds'))} against a "
        f"{_fmt_seconds_cell(budget.get('budget_seconds'))} budget "
        f"(within budget: {_fmt_cell(budget.get('within_budget'))})."
    )
    retried_total = budget.get("retried_total_seconds")
    if retried_total is not None:
        lines.append(f"Retried end-to-end total: {_fmt_cell(retried_total)}s.")
    lines.append("")

    override = evaluation.get("override") or {}
    override_status = override.get("status")
    if override_status == OVERRIDE_STATUS_ACCEPTED:
        lines.append("## Escape hatch")
        lines.append("")
        lines.append(f"Justification: {_render_override_justification(override.get('justification'))}")
        lines.append(f"Author: {_fmt_cell(override.get('author'))}")
        matched_cells = override.get("matched_cells") or []
        if matched_cells:
            matched_desc = ", ".join(
                f"{cell['benchmark']}.{cell['metric']}"
                for cell in sorted(matched_cells, key=lambda cell: (cell["benchmark"], cell["metric"]))
            )
            lines.append(f"Matched (exempted) cells: {matched_desc}")
        else:
            lines.append("Matched (exempted) cells: none")
        unmatched_cells = override.get("unmatched_cells") or []
        if unmatched_cells:
            lines.append("Unmatched cells:")
            for cell in sorted(unmatched_cells, key=lambda cell: (cell["benchmark"], cell["metric"])):
                lines.append(f"- {cell['benchmark']}.{cell['metric']} ({cell['reason']})")
        lines.append("")
    elif override_status == OVERRIDE_STATUS_REJECTED:
        # A rejected override carries none of the accepted body's justification or matched or
        # unmatched cell lists (parse_override_trailer leaves them empty or None on this
        # path), so this body renders only the fields a rejected override actually carries.
        lines.append("## Escape hatch")
        lines.append("")
        lines.append("Status: rejected")
        lines.append(f"Rejection reason: {_fmt_cell(override.get('rejection_reason'))}")
        lines.append(f"Author: {_fmt_cell(override.get('author'))}")
        lines.append(f"Trailer as written: `{_render_raw_override_trailer(override.get('raw_value'))}`")
        lines.append("")

    if verdict == VERDICT_FAIL:
        failing = evaluation.get("failing_cells", [])
        lines.append("## Failing cells")
        lines.append("")
        if failing:
            lines.append(
                "| Benchmark | Metric | Candidate | Base | Delta | Delta (%) | Tier | "
                "Baseline n | Spread | CV | MDE (%) |"
            )
            lines.append("|---|---|---|---|---|---|---|---|---|---|---|")
            for cell in sorted(failing, key=_cell_sort_key):
                delta_pct = cell.get("delta_pct")
                lines.append(
                    "| " + cell["benchmark"]
                    + " | " + cell["metric"]
                    + " | " + str(cell["candidate_value"])
                    + " | " + str(cell["base_value"])
                    + " | " + str(cell["delta"])
                    + " | " + (str(delta_pct) if delta_pct is not None else "n/a")
                    + " | " + _fmt_cell(cell.get("tier"))
                    + " | " + _fmt_cell(cell.get("baseline_n"))
                    + " | " + _fmt_cell(cell.get("baseline_spread"))
                    + " | " + _fmt_cell(cell.get("baseline_cv"))
                    + " | " + _fmt_cell(cell.get("baseline_mde_pct"))
                    + " |"
                )
        else:
            lines.append("No failing gating cell.")
        lines.append("")

        exempted = evaluation.get("exempted_cells", [])
        lines.append("## Exempted cells")
        lines.append("")
        if exempted:
            # The justification and author are already rendered above, unconditionally, in
            # the "Escape hatch" section: this table is the cell-by-cell detail only.
            lines.append("| Benchmark | Metric | Candidate | Base | Delta | Delta (%) |")
            lines.append("|---|---|---|---|---|---|")
            for cell in sorted(exempted, key=_cell_sort_key):
                delta_pct = cell.get("delta_pct")
                lines.append(
                    "| " + cell["benchmark"]
                    + " | " + cell["metric"]
                    + " | " + str(cell["candidate_value"])
                    + " | " + str(cell["base_value"])
                    + " | " + str(cell["delta"])
                    + " | " + (str(delta_pct) if delta_pct is not None else "n/a")
                    + " |"
                )
        else:
            lines.append("No cell exempted.")
        lines.append("")

        contamination = evaluation.get("contamination_benchmarks", [])
        if contamination:
            lines.append("## Contamination")
            lines.append("")
            for benchmark in contamination:
                lines.append(f"- {benchmark}")
            lines.append("")

        lines.append(DOC_POINTER_LINE)
        lines.append("")

    elif verdict == VERDICT_INCONCLUSIVE:
        lines.append("## Inconclusive")
        lines.append("")
        if evaluation.get("verdict_reason") == REASON_TRUSTED_BASELINE_ABSENT:
            lines.append(
                "No trusted baseline exists yet at this pull request's merge base, so no "
                "comparison against it was possible. This is expected, not a defect, on a "
                "pull request whose base branch predates the gate baseline file -- most "
                "obviously the pull request that introduces it -- and it resolves itself "
                "once the baseline exists on the base branch."
            )
            lines.append("")
            detail = evaluation.get("baseline_unavailable_reason")
            if detail:
                lines.append(f"Detail: {_collapse_and_neutralize_for_summary(_fmt_cell(detail))}")
                lines.append("")
        condition_totals = evaluation.get("condition_counts", {})
        fired = [
            condition for condition in INCONCLUSIVE_CONDITIONS if condition_totals.get(condition, 0) > 0
        ]
        if fired:
            lines.append("Conditions that fired:")
            lines.append("")
            for condition in fired:
                lines.append(f"- {condition}: {condition_totals[condition]}")
            lines.append("")
        else:
            lines.append("No enumerated condition fired.")
            lines.append("")

        inconclusive_gating = [
            cell for cell in evaluation.get("cells", [])
            if cell.get("gating") and cell.get("verdict") == VERDICT_INCONCLUSIVE
        ]
        if inconclusive_gating:
            lines.append("| Benchmark | Metric | Reason |")
            lines.append("|---|---|---|")
            for cell in sorted(inconclusive_gating, key=_cell_sort_key):
                lines.append(f"| {cell['benchmark']} | {cell['metric']} | {cell.get('reason')} |")
            lines.append("")

        attempts = evaluation.get("attempts", [])
        if attempts:
            retried = any(attempt.get("retried") for attempt in attempts)
            lines.append(f"Retry ran: {retried}. Last attempt verdict: {attempts[-1].get('verdict')}.")
        else:
            lines.append("Retry ran: False.")
        lines.append("")
        lines.append("This outcome does not block.")
        lines.append("")
        lines.append(DOC_POINTER_LINE)
        lines.append("")

    else:
        drift = evaluation.get("drift_cells", [])
        if drift:
            lines.append("## Drift (informational)")
            lines.append("")
            lines.append("| Benchmark | Metric | Value |")
            lines.append("|---|---|---|")
            for cell in sorted(drift, key=_cell_sort_key):
                lines.append(f"| {cell['benchmark']} | {cell['metric']} | {cell.get('candidate_value')} |")
            lines.append("")

    lines.append("## Condition counts")
    lines.append("")
    lines.append("| Condition | Count |")
    lines.append("|---|---|")
    condition_totals = evaluation.get("condition_counts", {})
    for condition in INCONCLUSIVE_CONDITIONS:
        lines.append(f"| {condition} | {condition_totals.get(condition, 0)} |")
    lines.append("")

    if report_only and verdict == VERDICT_FAIL:
        lines.append(
            "This check does not block. This verdict would have blocked once the gate is "
            "flipped to blocking."
        )
        lines.append("")

    return "\n".join(lines) + "\n"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--record",
        required=True,
        help="Path to a two-leg gate-ab record (candidate versus merge-base benchmarks)",
    )
    parser.add_argument(
        "--baseline",
        default=DEFAULT_BASELINE_PATH,
        help="Path to the committed gate-baseline.json sidecar",
    )
    parser.add_argument(
        "--out-json",
        default=None,
        help="Optional output path for the full evaluation as JSON",
    )
    parser.add_argument(
        "--out-md",
        default=None,
        help="Optional output path for the rendered markdown summary",
    )
    parser.add_argument(
        "--exit-nonzero-on-fail",
        action="store_true",
        default=False,
        help="Exit 1 when the run verdict is FAIL (default off: this phase runs report-only)",
    )
    parser.add_argument(
        "--override-trailer",
        default=None,
        help="The raw Perf-Gate-Override commit-trailer value, when one was read",
    )
    parser.add_argument(
        "--override-author",
        default=None,
        help="The head commit's author, recorded verbatim alongside the override",
    )
    parser.add_argument(
        "--override-unavailable-reason",
        default=None,
        help="Recorded verbatim when the trailer parser itself was unavailable on the runner",
    )
    parser.add_argument(
        "--baseline-unavailable-reason",
        default=None,
        help="When supplied, the trusted baseline itself does not exist at the merge base: "
        "skip reading --record and --baseline entirely and resolve to a non-blocking "
        "INCONCLUSIVE carrying this reason verbatim",
    )
    return parser.parse_args(argv)


def _write_evaluation_outputs(evaluation: dict[str, Any], markdown: str, args: argparse.Namespace) -> None:
    if args.out_json:
        out_json = Path(args.out_json)
        out_json.parent.mkdir(parents=True, exist_ok=True)
        out_json.write_text(json.dumps(evaluation, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if args.out_md:
        out_md = Path(args.out_md)
        out_md.parent.mkdir(parents=True, exist_ok=True)
        out_md.write_text(markdown, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if args.baseline_unavailable_reason:
        # The trusted baseline itself does not exist at the merge base -- resolved before
        # either --record or --baseline is even opened, so this outcome is robust even when
        # the paired measurement also failed to produce a record. Never a FAIL, so
        # --exit-nonzero-on-fail has nothing to act on here; always exit 0.
        evaluation = _baseline_unavailable_evaluation(args.baseline_unavailable_reason)
        markdown = render_summary_markdown(evaluation, report_only=not args.exit_nonzero_on_fail)
        _write_evaluation_outputs(evaluation, markdown, args)
        return 0

    try:
        record = json.loads(Path(args.record).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        print(f"Could not read or parse the two-leg record: {args.record}")
        return 2

    try:
        baseline = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        # An unreadable or unparseable baseline is the gate's own infrastructure failure, not
        # a verdict about the change under test: it says nothing about whether the candidate
        # regressed, so it must not be reported in the vocabulary of a measurement outcome.
        # This module previously substituted a zero-cell baseline here and returned 0, because
        # the baseline came from the pull request's own tree and a broken copy could otherwise
        # have been the developer's own doing; charging that to the developer risked a red
        # check for a reason unrelated to their change. Now that the baseline this module is
        # handed is read from the base branch rather than the pull request's own tree, a broken
        # baseline cannot be caused by the change under test, so failing loudly is the honest
        # response, exactly as an unreadable --record already does below.
        print(f"Could not read or parse the baseline sidecar: {args.baseline}")
        return 2

    override = None
    if args.override_trailer is not None or args.override_unavailable_reason is not None:
        override = parse_override_trailer(
            args.override_trailer or "",
            author=args.override_author,
            unavailable_reason=args.override_unavailable_reason,
        )

    evaluation = evaluate_run(record, baseline, override=override)
    # This key is retained on every path that reaches a real record and baseline read: it is
    # already present in the verdict artifacts of every recorded run, and removing a
    # published key is a subtractive change to a shape a reader may already parse. It is
    # always None here because --baseline-unavailable-reason, the one condition that
    # populates it with something else, is handled entirely above and returns before this
    # line is ever reached.
    evaluation["baseline_unavailable_reason"] = None
    markdown = render_summary_markdown(evaluation, report_only=not args.exit_nonzero_on_fail)
    _write_evaluation_outputs(evaluation, markdown, args)

    if args.exit_nonzero_on_fail and evaluation["verdict"] == VERDICT_FAIL:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
# ----------------------------------------------------------------------------
