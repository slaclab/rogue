#!/usr/bin/env python3
# ----------------------------------------------------------------------------
# Title      : ROGUE Performance Noise Floor Report
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

import argparse
import json
import math
import statistics
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SIDECAR_VERSION = 1
BENCH_COUNT = 100000
DEFAULT_MIN_N = 5
INSUFFICIENT_SAMPLES = "insufficient-samples"
UNDEFINED_ZERO_MEAN = "undefined-zero-mean"
UNDEFINED_ZERO_MEDIAN = "undefined-zero-median"
UNATTRIBUTED = "unattributed"
UNDEFINED_ZERO_VARIANCE = "undefined-zero-variance"
UNDEFINED_ZERO_WITHIN_CV = "undefined-zero-within-cv"
UNDEFINED_CONSTANT_INPUT = "undefined-constant-input"
DEFAULT_SHRINK_SPLIT = 2.0
DEFAULT_MDE_Z = 1.96
DEFAULT_MDE_GATE_PCT = 2.0
PUBLISHED_AT_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
CANCELLATION_EPSILON_RATIO = 1e-12
SUPPRESSIBLE_KEYS = (
    "cv", "cv_percent", "eta_squared", "within_cv", "within_cv_percent", "shrink_ratio",
)

DEFAULT_OUT_MD = "docs/plans/perf-ci-hardening/NOISE-FLOOR-REPORT.md"
DEFAULT_OUT_JSON = "docs/plans/perf-ci-hardening/noise-floor.json"

FETCH_COMMAND = "git fetch origin gh-pages"
CANONICAL_COMMAND = (
    "python3 scripts/perf_noise_report.py --gh-pages-ref origin/gh-pages "
    f"--out-md {DEFAULT_OUT_MD} --out-json {DEFAULT_OUT_JSON}"
)

FIELD_CLASSES: dict[str, set[str]] = {
    "measurement": {
        "avg_ns", "rate_hz", "cycles", "throughput_mb_s", "elapsed_sec",
        "baseline_s", "contended_s", "slowdown_ratio", "frames_received", "rx_errors",
    },
    "declared-limit": {"max_avg_ns", "max_cycles", "ceiling_s"},
    "fixed-parameter": {"frame_size", "frames_sent", "drain_count", "version"},
    "boolean-flag": {"drain_complete", "threshold_pass", "jumbo"},
    "provenance": {"timestamp", "name", "benchmark"},
}

REDUNDANT_PAIRS = [
    ("rate_hz", "avg_ns", "rate_hz is the reciprocal of avg_ns"),
    (
        "elapsed_sec", "throughput_mb_s",
        "elapsed_sec is determined by throughput_mb_s at fixed frame_size and frames_sent",
    ),
    ("slowdown_ratio", "contended_s", "slowdown_ratio is contended_s over baseline_s"),
]

DISPERSION_CLASSES = {"measurement", "declared-limit", "fixed-parameter"}


def classify_field(field: str) -> str:
    for field_class, names in FIELD_CLASSES.items():
        if field in names:
            return field_class
    return "unclassified"


def _coerce_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        coerced = float(value)
    except (TypeError, ValueError):
        return None
    return coerced if math.isfinite(coerced) else None


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--gh-pages-ref",
        default="origin/gh-pages",
        help="Git ref to read published perf JSON from, for example origin/gh-pages",
    )
    parser.add_argument(
        "--published-root",
        help="Local directory containing published perf JSON under perf/, used instead of --gh-pages-ref",
    )
    parser.add_argument(
        "--min-n",
        type=int,
        default=DEFAULT_MIN_N,
        help="Minimum sample count required before reporting a dispersion figure for a cell",
    )
    parser.add_argument(
        "--shrink-split",
        type=float,
        default=DEFAULT_SHRINK_SPLIT,
        help="Pooled shrink ratio at or above which a metric joins the host-dominated population",
    )
    parser.add_argument(
        "--mde-z",
        type=float,
        default=DEFAULT_MDE_Z,
        help="Two-sided normal-approximation z value for the provisional minimum detectable effect",
    )
    parser.add_argument(
        "--mde-gate-pct",
        type=float,
        default=DEFAULT_MDE_GATE_PCT,
        help="Within-host-group minimum detectable effect, in percent, at or below which a metric "
        "qualifies for a tight-dispersion tier recommendation",
    )
    parser.add_argument(
        "--out-md",
        default=DEFAULT_OUT_MD,
        help="Output path for the generated markdown report",
    )
    parser.add_argument(
        "--out-json",
        default=DEFAULT_OUT_JSON,
        help="Output path for the generated JSON sidecar",
    )
    return parser.parse_args(argv)


def resolve_ref(git_ref: str) -> str | None:
    completed = subprocess.run(
        ["git", "rev-parse", "--verify", f"{git_ref}^{{commit}}"],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return None
    return completed.stdout.strip()


def list_history_paths(git_ref: str) -> list[str]:
    completed = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", git_ref, "--", "perf/branches/"],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return []
    paths = [
        line
        for line in completed.stdout.splitlines()
        if "/history/" in line and line.endswith(".json")
    ]
    return sorted(paths)


def list_history_paths_from_root(published_root: Path) -> list[str]:
    root = published_root / "perf" / "branches"
    if not root.is_dir():
        return []
    paths = [
        path.relative_to(published_root).as_posix()
        for path in root.glob("*/history/*.json")
    ]
    return sorted(paths)


def list_all_perf_paths(git_ref: str) -> list[str]:
    completed = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", git_ref, "--", "perf/"],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return []
    return sorted(line for line in completed.stdout.splitlines() if line)


def list_all_perf_paths_from_root(published_root: Path) -> list[str]:
    root = published_root / "perf"
    if not root.is_dir():
        return []
    paths = [
        path.relative_to(published_root).as_posix()
        for path in root.rglob("*")
        if path.is_file()
    ]
    return sorted(paths)


def _load_record_text(
    relative_path: str,
    git_ref: str | None,
    published_root: Path | None,
) -> str | None:
    if published_root is not None:
        target = published_root / relative_path
        if not target.is_file():
            return None
        try:
            return target.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return None
    try:
        completed = subprocess.run(
            ["git", "show", f"{git_ref}:{relative_path}"],
            check=False,
            capture_output=True,
            encoding="utf-8",
        )
    except UnicodeDecodeError:
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout


def load_record(
    relative_path: str,
    git_ref: str | None = None,
    published_root: Path | None = None,
) -> dict[str, Any] | None:
    text = _load_record_text(relative_path, git_ref, published_root)
    if text is None:
        return None
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    schema_version = payload.get("schema_version")
    if not isinstance(schema_version, int) or schema_version != 1:
        return None
    benchmarks = payload.get("benchmarks")
    if not isinstance(benchmarks, list):
        return None
    return payload


def flatten_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for record in records:
        branch = record.get("ref_name", "")
        sha = record.get("sha", "")
        published_at = record.get("published_at", "")
        path = record.get("_path", "")
        for benchmark in record.get("benchmarks", []):
            if not isinstance(benchmark, dict):
                continue
            series = benchmark.get("name")
            raw = benchmark.get("raw")
            if not isinstance(series, str) or not isinstance(raw, dict):
                continue
            for field, value in raw.items():
                rows.append(
                    {
                        "metric_key": f"{series}.{field}",
                        "series": series,
                        "field": field,
                        "value": value,
                        "branch": branch,
                        "sha": sha,
                        "published_at": published_at,
                        "path": path,
                    }
                )
    rows.sort(key=lambda row: (row["metric_key"], row["branch"], row["published_at"], row["sha"]))
    return rows


def derived_rate_hz(record: dict[str, Any]) -> float | None:
    """Median implied clock rate across a record's qualifying variable_rate_perf_* series.

    A series qualifies when it has a non-null `cycles` and an `avg_ns` strictly greater
    than zero. `cycles` is the raw whole-loop total, never divided by BENCH_COUNT, while
    `avg_ns` is per-operation, so the BENCH_COUNT factor below is mandatory: omitting it
    yields a rate five orders of magnitude wrong.
    """
    rates: list[float] = []
    for benchmark in record.get("benchmarks", []):
        if not isinstance(benchmark, dict):
            continue
        series = benchmark.get("name")
        raw = benchmark.get("raw")
        if not isinstance(series, str) or not series.startswith("variable_rate_perf_"):
            continue
        if not isinstance(raw, dict):
            continue
        cycles = raw.get("cycles")
        avg_ns = raw.get("avg_ns")
        if cycles is None or isinstance(cycles, bool) or not isinstance(cycles, (int, float)):
            continue
        if avg_ns is None or isinstance(avg_ns, bool) or not isinstance(avg_ns, (int, float)):
            continue
        if not math.isfinite(cycles) or not math.isfinite(avg_ns):
            continue
        if avg_ns <= 0:
            continue
        elapsed_s = avg_ns * BENCH_COUNT * 1e-9
        rates.append(cycles / elapsed_s)
    if not rates:
        return None
    return statistics.median(rates)


def host_group_id(rate_hz: float) -> str:
    """Half-up bucket a derived rate to two decimal places of GHz.

    `math.floor(rate_hz / 1e7 + 0.5)` is half-up rounding rather than `round`'s
    half-to-even, so behaviour at an exact bucket boundary is the expected one:
    a rate exactly on the boundary between two buckets rounds up.
    """
    centi = math.floor(rate_hz / 1e7 + 0.5)
    return f"tsc-{centi / 100.0:.2f}GHz"


def assign_host_groups(
    rows: list[dict[str, Any]],
    records: list[dict[str, Any]],
) -> dict[str, str]:
    """Attach a host_group to every flattened row, derived from the row's own record.

    Returns the path-to-group-id mapping so callers building the sidecar's host_groups
    block never need to recompute the derivation.
    """
    group_by_path: dict[str, str] = {}
    for record in records:
        rate = derived_rate_hz(record)
        group_by_path[record.get("_path", "")] = (
            UNATTRIBUTED if rate is None else host_group_id(rate)
        )
    for row in rows:
        row["host_group"] = group_by_path.get(row["path"], UNATTRIBUTED)
    return group_by_path


def build_host_groups(
    records: list[dict[str, Any]],
    group_by_path: dict[str, str],
) -> list[dict[str, Any]]:
    info: dict[str, dict[str, Any]] = {}
    for record in records:
        group_id = group_by_path.get(record.get("_path", ""), UNATTRIBUTED)
        bucket = info.setdefault(group_id, {"record_count": 0, "branches": set()})
        bucket["record_count"] += 1
        bucket["branches"].add(record.get("ref_name", ""))

    groups: list[dict[str, Any]] = []
    for group_id, bucket in info.items():
        if group_id == UNATTRIBUTED:
            rate_ghz = None
        else:
            rate_ghz = float(group_id[len("tsc-"):-len("GHz")])
        groups.append(
            {
                "host_group": group_id,
                "rate_ghz": rate_ghz,
                "record_count": bucket["record_count"],
                "branches": sorted(bucket["branches"]),
            }
        )

    def sort_key(group: dict[str, Any]) -> tuple[int, float]:
        if group["host_group"] == UNATTRIBUTED:
            return (1, 0.0)
        return (0, group["rate_ghz"])

    groups.sort(key=sort_key)
    return groups


def variance_split(values_by_group: dict[str, list[float]]) -> dict[str, Any]:
    """One-way sum-of-squares decomposition of pooled samples into host groups.

    `eta_squared` is the between-group share of total variance, `undefined-zero-variance`
    when the total sum of squares is exactly zero. `within_stdev` is the pooled
    within-group standard deviation, `insufficient-samples` when the total sample count
    does not exceed the group count. `within_cv` divides `within_stdev` by the absolute
    grand mean, propagating whichever marker applies. Sum-of-squares cancellation below
    `CANCELLATION_EPSILON_RATIO` of the total is treated as exactly zero.
    """
    groups = {group: values for group, values in values_by_group.items() if values}
    all_values = [value for values in groups.values() for value in values]
    n_total = len(all_values)
    k = len(groups)

    grand_mean = statistics.fmean(all_values) if all_values else 0.0
    ss_total = sum((value - grand_mean) ** 2 for value in all_values)
    ss_between = sum(
        len(values) * (statistics.fmean(values) - grand_mean) ** 2
        for values in groups.values()
    )
    ss_within = ss_total - ss_between
    if ss_total != 0.0 and abs(ss_within) < CANCELLATION_EPSILON_RATIO * ss_total:
        ss_within = 0.0

    if ss_total == 0.0:
        eta_squared: Any = UNDEFINED_ZERO_VARIANCE
    else:
        eta_squared = ss_between / ss_total

    if n_total <= k:
        within_stdev: Any = INSUFFICIENT_SAMPLES
    else:
        within_stdev = math.sqrt(ss_within / (n_total - k))

    if not isinstance(within_stdev, (int, float)):
        within_cv: Any = INSUFFICIENT_SAMPLES
    elif grand_mean == 0.0:
        within_cv = UNDEFINED_ZERO_MEAN
    else:
        within_cv = within_stdev / abs(grand_mean)

    return {
        "n": n_total,
        "k": k,
        "grand_mean": grand_mean,
        "eta_squared": eta_squared,
        "within_stdev": within_stdev,
        "within_cv": within_cv,
    }


def published_epoch(value: Any) -> float | None:
    """Parse a published_at timestamp to an epoch number under the one documented format.

    `scripts/perf_data.py:utc_now_iso` is the only emitter of this field, so
    `PUBLISHED_AT_FORMAT` is the only form these records carry. Any value that is not a
    string, or that fails to parse under that exact format, returns None rather than
    raising, so a malformed or absent timestamp can be counted by the caller instead of
    aborting the run.
    """
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.strptime(value, PUBLISHED_AT_FORMAT).replace(tzinfo=timezone.utc)
    except ValueError:
        return None
    return parsed.timestamp()


def pearson(xs: list[float], ys: list[float], min_n: int) -> Any:
    """Pearson correlation with the documented guards, in order.

    Below `min_n` samples: `INSUFFICIENT_SAMPLES`, the correlation is never attempted.
    Fewer than 2 distinct values, or exactly zero variance, in either input:
    `UNDEFINED_CONSTANT_INPUT`. `statistics.StatisticsError` is never allowed to escape;
    a constant input is exactly what that exception means here, so it converts to the
    same marker rather than propagating.
    """
    n = len(xs)
    if n < min_n:
        return INSUFFICIENT_SAMPLES
    if len(set(xs)) < 2 or len(set(ys)) < 2:
        return UNDEFINED_CONSTANT_INPUT
    if statistics.pvariance(xs) == 0.0 or statistics.pvariance(ys) == 0.0:
        return UNDEFINED_CONSTANT_INPUT
    try:
        return statistics.correlation(xs, ys)
    except statistics.StatisticsError:
        return UNDEFINED_CONSTANT_INPUT


def correlations(group: list[dict[str, Any]], field_class: str, min_n: int) -> dict[str, Any]:
    """Correlate one metric cell's values against the three covariates the published
    records actually carry: publication time and the derived host rate as Pearson
    coefficients, and branch as a categorical share of total variance, since a Pearson
    coefficient is not applicable to a covariate with no numeric ordering.

    Pairs are formed only from rows where both the cell's own value and the covariate
    are defined, so an unparsable timestamp or an unattributed host group excludes a
    row from that one covariate without excluding it from the others.

    A numeric branch variance share requires the branch-grouped sample count to reach
    min_n; a share the decomposition itself could not define keeps its own marker
    rather than being overwritten by the minimum-sample gate.
    """
    time_pairs: list[tuple[float, float]] = []
    rate_pairs: list[tuple[float, float]] = []
    branch_values: dict[str, list[float]] = {}

    for row in group:
        value = row["value"]
        if field_class == "boolean-flag":
            coerced: float | None = None
            if isinstance(value, bool):
                coerced = 1.0 if value else 0.0
        else:
            coerced = _coerce_float(value)
        if coerced is None:
            continue

        epoch = published_epoch(row.get("published_at"))
        if epoch is not None:
            time_pairs.append((epoch, coerced))

        host_group = row.get("host_group", UNATTRIBUTED)
        if host_group != UNATTRIBUTED and host_group.startswith("tsc-"):
            rate_ghz = float(host_group[len("tsc-"):-len("GHz")])
            rate_pairs.append((rate_ghz, coerced))

        branch_values.setdefault(row.get("branch", ""), []).append(coerced)

    published_at_corr = pearson([x for x, _ in time_pairs], [y for _, y in time_pairs], min_n)
    host_rate_corr = pearson([x for x, _ in rate_pairs], [y for _, y in rate_pairs], min_n)
    split_result = variance_split(branch_values)
    branch_share = split_result["eta_squared"]
    if isinstance(branch_share, float) and split_result["n"] < min_n:
        branch_share = INSUFFICIENT_SAMPLES

    return {
        "published_at": _sidecar_float(published_at_corr) if isinstance(published_at_corr, float) else published_at_corr,
        "host_rate_ghz": _sidecar_float(host_rate_corr) if isinstance(host_rate_corr, float) else host_rate_corr,
        "branch_variance_share": _sidecar_float(branch_share) if isinstance(branch_share, float) else branch_share,
    }


def recorded_covariate_evidence(records: list[dict[str, Any]]) -> dict[str, Any]:
    """The sorted union and intersection of top-level keys observed across every
    published record, evidence for the claim that no runner characteristic other than
    the derived rate was ever recorded. `_path` is this generator's own bookkeeping
    key, added after loading, and is excluded so it never appears as if it were part
    of the published schema.
    """
    key_sets = [set(record.keys()) - {"_path"} for record in records]
    if not key_sets:
        return {"key_union": [], "key_intersection": []}
    return {
        "key_union": sorted(set().union(*key_sets)),
        "key_intersection": sorted(set.intersection(*key_sets)),
    }


def _timestamp_audit(records: list[dict[str, Any]]) -> tuple[int, list[str], dict[str, Any]]:
    """Count and name every record whose published_at fails to parse, and compute the
    earliest and latest published timestamp among the records that do parse. A record
    named here is excluded from the time correlation only; it still contributes to
    every other statistic."""
    unparsable: list[str] = []
    parsed: list[tuple[float, str]] = []
    for record in records:
        published_at = record.get("published_at")
        epoch = published_epoch(published_at)
        if epoch is None:
            unparsable.append(record.get("sha") or record.get("_path", ""))
        else:
            parsed.append((epoch, published_at))
    if parsed:
        earliest = min(parsed, key=lambda pair: pair[0])[1]
        latest = max(parsed, key=lambda pair: pair[0])[1]
        span = {"earliest": earliest, "latest": latest}
    else:
        span = {"earliest": None, "latest": None}
    return len(unparsable), sorted(unparsable), span


def provisional_mde(cv: Any, n: int, z: float) -> Any:
    """`z * cv * 100.0 / sqrt(n)`, the two-sided normal-approximation half-width with
    no power term. A marker input (any non-numeric coefficient of variation) yields
    the same marker as output rather than a number or an exception."""
    if not isinstance(cv, (int, float)) or isinstance(cv, bool):
        return cv
    if not isinstance(n, int) or n <= 0:
        return INSUFFICIENT_SAMPLES
    return z * float(cv) * 100.0 / math.sqrt(n)


def tier_recommendation(
    mde_pooled: Any,
    mde_within: Any,
    spread: Any,
    shrink_ratio: Any,
    gate_pct: float,
    shrink_split: float,
) -> tuple[str, str]:
    """Apply the five ordered tier rules, returning (recommendation, rule name) so
    every recommendation is traceable to the rule that produced it rather than to
    judgement."""
    if not isinstance(mde_pooled, (int, float)) or not isinstance(mde_within, (int, float)):
        return INSUFFICIENT_SAMPLES, "below-minimum-n"
    if isinstance(spread, (int, float)) and spread == 0.0:
        return "invariant-candidate", "zero-spread"
    shrink_numeric = isinstance(shrink_ratio, (int, float))
    if mde_within <= gate_pct and shrink_numeric and shrink_ratio >= shrink_split:
        return "stratified-candidate", "host-dominated-tight-within"
    if mde_within <= gate_pct:
        return "normalization-candidate", "host-insensitive-tight"
    return "informational", "dispersion-too-large"


def suppress_below_min_n(cell: dict[str, Any], min_n: int) -> dict[str, Any]:
    """Mark, never remove: below `min_n`, replace only the figures that need enough
    samples to mean anything, keeping the row, its sample count, minimum, maximum, and
    spread untouched."""
    n = cell.get("n")
    if not isinstance(n, int) or n >= min_n:
        return cell
    suppressed = dict(cell)
    for key in SUPPRESSIBLE_KEYS:
        if key in suppressed and suppressed[key] != INSUFFICIENT_SAMPLES:
            suppressed[key] = INSUFFICIENT_SAMPLES
    return suppressed


def split_populations(
    metrics: dict[str, dict[str, Any]],
    shrink_split: float,
) -> dict[str, Any]:
    """Sort measured metrics into host-dominated, intrinsic-noise, or unclassified-dispersion
    by their pooled shrink ratio against `shrink_split`, and report the margin on both sides
    of the threshold."""
    host_dominated: list[str] = []
    intrinsic_noise: list[str] = []
    unclassified_dispersion: list[str] = []
    below_values: list[float] = []
    at_or_above_values: list[float] = []

    for metric_key, entry in metrics.items():
        if entry.get("field_class") != "measurement":
            continue
        shrink_ratio = entry.get("shrink_ratio")
        if not isinstance(shrink_ratio, (int, float)):
            unclassified_dispersion.append(metric_key)
            continue
        if shrink_ratio >= shrink_split:
            host_dominated.append(metric_key)
            at_or_above_values.append(float(shrink_ratio))
        else:
            intrinsic_noise.append(metric_key)
            below_values.append(float(shrink_ratio))

    return {
        "threshold": shrink_split,
        "host-dominated": sorted(host_dominated),
        "intrinsic-noise": sorted(intrinsic_noise),
        "unclassified-dispersion": sorted(unclassified_dispersion),
        "largest_below": max(below_values) if below_values else None,
        "smallest_at_or_above": min(at_or_above_values) if at_or_above_values else None,
    }


def fmt_float(value: float) -> str:
    return f"{value:.6g}"


def _sidecar_float(value: float) -> float:
    return float(fmt_float(value))


def dispersion(values: list[float]) -> dict[str, Any]:
    n = len(values)
    minimum = min(values)
    maximum = max(values)
    spread = maximum - minimum
    median = statistics.median(values)
    mad = statistics.median([abs(x - median) for x in values])

    if n < 2:
        cv = INSUFFICIENT_SAMPLES
        cv_percent: Any = INSUFFICIENT_SAMPLES
        stdev = INSUFFICIENT_SAMPLES
        mean = values[0]
        iqr: Any = INSUFFICIENT_SAMPLES
    else:
        mean = statistics.fmean(values)
        stdev_value = statistics.stdev(values)
        stdev = stdev_value
        if mean == 0.0:
            cv = UNDEFINED_ZERO_MEAN
            cv_percent = UNDEFINED_ZERO_MEAN
        else:
            cv_value = stdev_value / abs(mean)
            cv = cv_value
            cv_percent = cv_value * 100.0
        if n >= 4:
            q1, _, q3 = statistics.quantiles(values, n=4, method="inclusive")
            iqr = q3 - q1
        else:
            iqr = INSUFFICIENT_SAMPLES

    if median == 0.0:
        spread_pct: Any = UNDEFINED_ZERO_MEDIAN
    else:
        spread_pct = spread / abs(median) * 100.0

    return {
        "n": n,
        "median": median,
        "mad": mad,
        "iqr": iqr,
        "mean": mean,
        "stdev": stdev,
        "cv": cv,
        "cv_percent": cv_percent,
        "minimum": minimum,
        "maximum": maximum,
        "spread": spread,
        "spread_pct": spread_pct,
    }


def _round_dispersion(stats: dict[str, Any]) -> dict[str, Any]:
    rounded: dict[str, Any] = {}
    for key, value in stats.items():
        if isinstance(value, float):
            rounded[key] = _sidecar_float(value)
        else:
            rounded[key] = value
    return rounded


def _values_by_host_group(group: list[dict[str, Any]], field_class: str) -> dict[str, list[float]]:
    """Coerce each row's value to a float, keyed by the row's own host_group.

    Booleans coerce to 1.0/0.0 for `boolean-flag` fields so a per-group proportion is
    computable; every other class uses the same coercion the pooled statistics use, so a
    group's sample count and the pooled sample count are computed by the identical rule.
    """
    values_by_group: dict[str, list[float]] = {}
    for row in group:
        value = row["value"]
        if field_class == "boolean-flag":
            coerced: float | None = None
            if isinstance(value, bool):
                coerced = 1.0 if value else 0.0
        else:
            coerced = _coerce_float(value)
        if coerced is None:
            continue
        values_by_group.setdefault(row.get("host_group", UNATTRIBUTED), []).append(coerced)
    return values_by_group


def build_field_inventory(
    rows: list[dict[str, Any]],
    history_record_count: int = 0,
    min_n: int = DEFAULT_MIN_N,
    shrink_split: float = DEFAULT_SHRINK_SPLIT,
    mde_z: float = DEFAULT_MDE_Z,
    mde_gate_pct: float = DEFAULT_MDE_GATE_PCT,
) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(row["metric_key"], []).append(row)

    metrics: dict[str, dict[str, Any]] = {}
    for metric_key, group in grouped.items():
        series = group[0]["series"]
        field = group[0]["field"]
        field_class = classify_field(field)

        if field_class in DISPERSION_CLASSES:
            values: list[float] = []
            skipped_non_numeric = 0
            for row in group:
                coerced = _coerce_float(row["value"])
                if coerced is None:
                    skipped_non_numeric += 1
                else:
                    values.append(coerced)
            entry: dict[str, Any] = {"series": series, "field": field, "field_class": field_class}
            if values:
                entry.update(_round_dispersion(dispersion(values)))
            else:
                entry["n"] = 0
            if skipped_non_numeric:
                entry["skipped_non_numeric"] = skipped_non_numeric
        elif field_class == "boolean-flag":
            n = 0
            true_count = 0
            for row in group:
                value = row["value"]
                if isinstance(value, bool):
                    n += 1
                    if value:
                        true_count += 1
            entry = {
                "series": series,
                "field": field,
                "field_class": field_class,
                "n": n,
                "true_count": true_count,
            }
        elif field_class == "provenance":
            reason = "wall-clock publication artifact, never emitted" if field == "timestamp" else \
                "identifying label, not a measurement"
            entry = {
                "series": series,
                "field": field,
                "field_class": field_class,
                "n": len(group),
                "note": reason,
            }
        else:
            entry = {
                "series": series,
                "field": field,
                "field_class": field_class,
                "n": len(group),
                "note": "needs classification",
            }

        values_by_group = _values_by_host_group(group, field_class)
        split = variance_split(values_by_group)

        eta_squared = split["eta_squared"]
        entry["eta_squared"] = _sidecar_float(eta_squared) if isinstance(eta_squared, float) else eta_squared

        within_cv = split["within_cv"]
        if isinstance(within_cv, float):
            entry["within_cv"] = _sidecar_float(within_cv)
            entry["within_cv_percent"] = _sidecar_float(within_cv * 100.0)
        else:
            entry["within_cv"] = within_cv
            entry["within_cv_percent"] = within_cv

        pooled_cv = entry.get("cv")
        if not isinstance(pooled_cv, (int, float)) or not isinstance(within_cv, (int, float)):
            shrink_ratio: Any = INSUFFICIENT_SAMPLES
        elif within_cv == 0.0:
            shrink_ratio = UNDEFINED_ZERO_WITHIN_CV
        else:
            shrink_ratio = _sidecar_float(pooled_cv / within_cv)
        entry["shrink_ratio"] = shrink_ratio

        by_host_group: dict[str, Any] = {}
        for group_id, values in values_by_group.items():
            if not values:
                continue
            group_stats = _round_dispersion(dispersion(values))
            by_host_group[group_id] = suppress_below_min_n(group_stats, min_n)
        entry["by_host_group"] = by_host_group

        entry["correlations"] = correlations(group, field_class, min_n)

        entry = suppress_below_min_n(entry, min_n)
        entry["records_missing_cell"] = history_record_count - entry.get("n", 0)

        mde_pooled = provisional_mde(entry.get("cv", INSUFFICIENT_SAMPLES), entry.get("n", 0), mde_z)
        mde_within = provisional_mde(entry.get("within_cv", INSUFFICIENT_SAMPLES), entry.get("n", 0), mde_z)
        entry["mde_pooled_pct"] = _sidecar_float(mde_pooled) if isinstance(mde_pooled, float) else mde_pooled
        entry["mde_within_pct"] = _sidecar_float(mde_within) if isinstance(mde_within, float) else mde_within

        recommendation, rule = tier_recommendation(
            entry["mde_pooled_pct"],
            entry["mde_within_pct"],
            entry.get("spread"),
            entry.get("shrink_ratio"),
            mde_gate_pct,
            shrink_split,
        )
        entry["tier_recommendation"] = recommendation
        entry["tier_rule"] = rule

        metrics[metric_key] = entry

    return metrics


def per_branch_medians(
    rows: list[dict[str, Any]],
    host_groups: list[dict[str, Any]],
    min_n: int,
) -> dict[str, Any]:
    """The evidence that pooling across branches is safe, rather than pooling being
    assumed: within the largest observed host group, per branch, the median of each
    measured metric and its deviation from that group's overall median."""
    if not host_groups:
        return {"host_group": None, "record_count": 0, "per_branch": {}, "max_relative_deviation": {}}

    dominant = max(host_groups, key=lambda group: group["record_count"])
    dominant_id = dominant["host_group"]

    all_branches = sorted({row["branch"] for row in rows})
    group_rows = [
        row for row in rows
        if row.get("host_group") == dominant_id and classify_field(row["field"]) == "measurement"
    ]

    by_metric: dict[str, list[tuple[str, float]]] = {}
    for row in group_rows:
        coerced = _coerce_float(row["value"])
        if coerced is None:
            continue
        by_metric.setdefault(row["metric_key"], []).append((row["branch"], coerced))

    per_branch: dict[str, dict[str, Any]] = {branch: {"metrics": {}} for branch in all_branches}
    max_relative_deviation: dict[str, Any] = {}

    for metric_key in sorted(by_metric):
        pairs = by_metric[metric_key]
        overall_median = statistics.median(value for _, value in pairs)

        values_by_branch: dict[str, list[float]] = {}
        for branch, value in pairs:
            values_by_branch.setdefault(branch, []).append(value)

        deviations: list[float] = []
        for branch in all_branches:
            branch_values = values_by_branch.get(branch)
            if not branch_values:
                continue
            n = len(branch_values)
            branch_median = statistics.median(branch_values)
            if overall_median == 0.0:
                relative_deviation: Any = UNDEFINED_ZERO_MEDIAN
            elif n < min_n:
                relative_deviation = INSUFFICIENT_SAMPLES
            else:
                relative_deviation = abs(branch_median - overall_median) / abs(overall_median)
                deviations.append(relative_deviation)
            per_branch[branch]["metrics"][metric_key] = {
                "n": n,
                "median": _sidecar_float(branch_median),
                "relative_deviation": (
                    _sidecar_float(relative_deviation)
                    if isinstance(relative_deviation, float)
                    else relative_deviation
                ),
            }
        if deviations:
            max_relative_deviation[metric_key] = _sidecar_float(max(deviations))

    return {
        "host_group": dominant_id,
        "record_count": dominant["record_count"],
        "per_branch": per_branch,
        "max_relative_deviation": max_relative_deviation,
    }


def repeated_commits(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The code-constant exhibit: commits published more than once from separate CI
    runs. Both members of every repeated commit stay in the pooled population; neither
    is averaged nor dropped, so any spread between members is measurement noise on an
    identical commit rather than a code change."""
    rows_by_sha: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        rows_by_sha.setdefault(row["sha"], []).append(row)

    entries: list[dict[str, Any]] = []
    for sha in sorted(rows_by_sha):
        sha_rows = rows_by_sha[sha]
        paths = sorted({row["path"] for row in sha_rows})
        if len(paths) < 2:
            continue

        member_by_path: dict[str, dict[str, Any]] = {}
        for row in sha_rows:
            member_by_path.setdefault(
                row["path"],
                {
                    "branch": row["branch"],
                    "path": row["path"],
                    "host_group": row.get("host_group", UNATTRIBUTED),
                },
            )
        members = [member_by_path[path] for path in paths]

        by_metric: dict[str, dict[str, float]] = {}
        for row in sha_rows:
            coerced = _coerce_float(row["value"])
            if coerced is None:
                continue
            by_metric.setdefault(row["metric_key"], {})[row["path"]] = coerced

        measurements: dict[str, Any] = {}
        for metric_key in sorted(by_metric):
            value_by_path = by_metric[metric_key]
            if len(value_by_path) < 2:
                continue
            metric_members: list[dict[str, Any]] = []
            base_value: float | None = None
            for path in paths:
                if path not in value_by_path:
                    continue
                value = value_by_path[path]
                if base_value is None:
                    base_value = value
                if base_value == 0.0:
                    relative_delta: Any = UNDEFINED_ZERO_MEAN
                else:
                    relative_delta = _sidecar_float((value - base_value) / abs(base_value))
                metric_members.append(
                    {
                        "branch": member_by_path[path]["branch"],
                        "path": path,
                        "value": _sidecar_float(value),
                        "host_group": member_by_path[path]["host_group"],
                        "relative_delta": relative_delta,
                    }
                )
            measurements[metric_key] = metric_members

        if not measurements:
            continue

        entries.append({"sha": sha, "members": members, "measurements": measurements})

    return entries


def build_population(
    history_paths: list[str],
    all_paths: list[str],
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    per_branch: dict[str, int] = {}
    for record in records:
        branch = record.get("ref_name", "")
        per_branch[branch] = per_branch.get(branch, 0) + 1

    return {
        "history_record_count": len(history_paths),
        "perf_file_count": len(all_paths),
        "per_branch_record_count": per_branch,
    }


def build_sidecar(
    gh_pages_commit: str,
    record_count: int,
    records_skipped: int,
    min_n: int,
    shrink_split: float,
    mde_z: float,
    mde_gate_pct: float,
    metrics: dict[str, dict[str, Any]],
    population: dict[str, Any],
    host_groups: list[dict[str, Any]],
    populations: dict[str, Any],
    pooling_evidence: dict[str, Any],
    repeated_commit_entries: list[dict[str, Any]],
    timestamps_unparsable: int,
    unparsable_record_shas: list[str],
    published_at_span: dict[str, Any],
    recorded_covariates: dict[str, Any],
) -> dict[str, Any]:
    return {
        "sidecar_version": SIDECAR_VERSION,
        "source": {
            "gh_pages_commit": gh_pages_commit,
            "record_count": record_count,
            "records_skipped": records_skipped,
            "timestamps_unparsable": timestamps_unparsable,
            "unparsable_record_shas": unparsable_record_shas,
            "published_at_span": published_at_span,
        },
        "parameters": {
            "min_n": min_n,
            "shrink_split": shrink_split,
            "mde_z": mde_z,
            "mde_gate_pct": mde_gate_pct,
            "float_format": ".6g",
        },
        "metrics": metrics,
        "population": population,
        "host_groups": host_groups,
        "populations": populations,
        "pooling_evidence": pooling_evidence,
        "repeated_commits": repeated_commit_entries,
        "recorded_covariates": recorded_covariates,
    }


def write_deterministic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def render_markdown(sidecar: dict[str, Any]) -> str:
    source = sidecar["source"]
    metrics = sidecar["metrics"]
    population = sidecar["population"]

    lines = [
        "<!-- generated by scripts/perf_noise_report.py, do not edit by hand -->",
        "# Noise Floor Report",
        "",
        "## Reproducing this report",
        "",
        "One-time, if the local clone has never fetched `gh-pages`:",
        "",
        "```sh",
        FETCH_COMMAND,
        "```",
        "",
        "Canonical invocation, tracking the moving `origin/gh-pages` branch:",
        "",
        "```sh",
        CANONICAL_COMMAND,
        "```",
        "",
        "Pinned invocation, reproducing this exact artifact byte-identically forever "
        "(the canonical form above tracks the moving branch and will diverge as new "
        "records publish):",
        "",
        "```sh",
        CANONICAL_COMMAND.replace(
            "--gh-pages-ref origin/gh-pages", f"--gh-pages-ref {source['gh_pages_commit']}"
        ),
        "```",
        "",
        "## Source",
        "",
        f"- Resolved commit: `{source['gh_pages_commit']}`",
        "- Only the resolved commit is recorded, not the literal `--gh-pages-ref` "
        "argument: the canonical invocation (tracking `origin/gh-pages`) and the "
        "pinned invocation (naming this exact commit) both resolve to the same "
        "commit and therefore reproduce byte-identical artifacts.",
        f"- Records parsed: {source['record_count']}",
        f"- Records skipped: {source['records_skipped']}",
        "- Timestamps unparsable: "
        + str(source["timestamps_unparsable"])
        + (
            " (" + ", ".join(source["unparsable_record_shas"]) + ")"
            if source["unparsable_record_shas"]
            else " (none)"
        ),
        "- Published span: "
        + (
            f"{source['published_at_span']['earliest']} to {source['published_at_span']['latest']}"
            if source["published_at_span"]["earliest"] is not None
            else "n/a (no parseable timestamps)"
        ),
        "",
        "## Statistical definitions",
        "",
        "- `n`: count of records that actually contain the cell, never a global record count.",
        "- `median`, `mad`: `statistics.median`, and the median of absolute deviations from it.",
        "- `iqr`: `q3 - q1` from `statistics.quantiles(values, n=4, method=\"inclusive\")`.",
        "- `mean`, `stdev`: `statistics.fmean`, and the sample standard deviation "
        "(`statistics.stdev`, `n - 1` denominator).",
        "- `cv`: `stdev / abs(mean)`, as a fraction and as a percent. "
        f"`{UNDEFINED_ZERO_MEAN}` when the mean is exactly zero, "
        f"`{INSUFFICIENT_SAMPLES}` when `n < 2`.",
        "- `minimum`, `maximum`, `spread`: `min(values)`, `max(values)`, `maximum - minimum`.",
        f"- `spread_pct`: `spread / abs(median) * 100.0`, or `{UNDEFINED_ZERO_MEDIAN}` "
        "when the median is exactly zero.",
        "- Every numeric value in both artifacts is produced by the float formatter `f\"{value:.6g}\"`.",
        "- `eta_squared`: the between-host-group share of total variance from a one-way "
        f"sum-of-squares decomposition, or `{UNDEFINED_ZERO_VARIANCE}` when the pooled "
        "total sum of squares is exactly zero.",
        "- `within_cv`: the pooled within-host-group coefficient of variation, as a "
        f"fraction and as a percent. `{INSUFFICIENT_SAMPLES}` when the sample count does "
        f"not exceed the host-group count, `{UNDEFINED_ZERO_MEAN}` when the grand mean is "
        "exactly zero.",
        "- `shrink_ratio`: pooled `cv` divided by `within_cv`, the headline result showing "
        "how much the pooled figure overstates dispersion once host stratification is "
        f"applied. `{UNDEFINED_ZERO_WITHIN_CV}` when `within_cv` is exactly zero, "
        f"`{INSUFFICIENT_SAMPLES}` when either input is itself a marker.",
        "- `records_missing_cell`: the count of published records that do not contain "
        "this cell; `n + records_missing_cell` always equals the recomputed history "
        "record count, enforced by the generator itself.",
        "- `by_host_group`: the same dispersion set computed within each host group "
        "alone, suppressed independently of the pooled figure.",
        "",
        "### Marker legend",
        "",
        "Every marker string either artifact can contain, in place of a number the data "
        "cannot support:",
        "",
        f"- `{INSUFFICIENT_SAMPLES}`: too few samples to compute this figure meaningfully "
        "(fewer than 2 for a pooled or host-group `cv`, or at or below the min-n threshold, "
        "or the sample count does not exceed the host-group count for `within_cv`).",
        f"- `{UNDEFINED_ZERO_MEAN}`: the mean (pooled or grand) is exactly zero, so a "
        "coefficient of variation is undefined.",
        f"- `{UNDEFINED_ZERO_MEDIAN}`: the median is exactly zero, so a percent spread is "
        "undefined.",
        f"- `{UNDEFINED_ZERO_VARIANCE}`: the total sum of squares is exactly zero, so a "
        "between-group variance share is undefined.",
        f"- `{UNDEFINED_ZERO_WITHIN_CV}`: the within-host-group coefficient of variation "
        "is exactly zero, so a shrink ratio would divide by zero.",
        f"- `{UNDEFINED_CONSTANT_INPUT}`: a correlation input has fewer than two "
        "distinct values, or exactly zero variance, so a Pearson coefficient is "
        "undefined.",
        "",
        "## Population",
        "",
        f"- History records (`perf/branches/*/history/*.json`): {population['history_record_count']}",
        f"- Records skipped as unparsable: {source['records_skipped']}",
        f"- Total files under `perf/`: {population['perf_file_count']}",
        "- The larger file count under `perf/` comprises the history records plus the "
        "per-branch `latest.json` files (each duplicating a history entry), the per-branch "
        "and top level `index.json` files, and `perf/index.html`.",
        "",
        "Per-branch record counts:",
        "",
        "| Branch | Records |",
        "|---|---|",
    ]
    for branch in sorted(population["per_branch_record_count"]):
        lines.append(f"| {branch} | {population['per_branch_record_count'][branch]} |")

    host_groups = sidecar.get("host_groups", [])
    unattributed_count = sum(
        group["record_count"] for group in host_groups if group["host_group"] == UNATTRIBUTED
    )
    lines.extend(
        [
            "",
            "## Host groups",
            "",
            "Every published record is assigned a host group derived from its own data: no "
            "runner ever recorded a CPU model, so a TSC-derived implied clock rate stands in "
            "as the host-attribution signal until a live probe captures both together.",
            "",
            "Derivation: for a record, take every `variable_rate_perf_*` series with a "
            "non-null `cycles` and an `avg_ns` strictly greater than zero, compute "
            "`cycles / (avg_ns * BENCH_COUNT * 1e-9)` for each, and take the median. "
            "A record with no qualifying series has no derived rate.",
            "",
            "Bucketing: `centi = math.floor(rate_hz / 1e7 + 0.5)`, then the group "
            "identifier is `tsc-{centi / 100.0:.2f}GHz`. This is half-up rounding to two "
            "decimal places of GHz, chosen over `round`'s half-to-even behaviour so a rate "
            "landing exactly on a bucket boundary has an unambiguous, stated outcome: it "
            "rounds up into the higher bucket rather than tying to whichever bucket is even.",
            "",
            f"Records with no derivable rate are assigned the `{UNATTRIBUTED}` group: "
            f"{unattributed_count} such record(s) in this population, counted here rather "
            "than dropped.",
            "",
            "Groups are reported by rate and sample count only. No CPU vendor, family, "
            "microarchitecture, or cloud SKU is named anywhere in this report: attributing "
            "a rate to a named CPU family from external fleet documentation would be "
            "inference, not measurement.",
            "",
            "| Host group | Rate (GHz) | Records |",
            "|---|---|---|",
        ]
    )
    for group in host_groups:
        rate_cell = fmt_float(group["rate_ghz"]) if group["rate_ghz"] is not None else "n/a"
        lines.append(f"| {group['host_group']} | {rate_cell} | {group['record_count']} |")

    lines.extend(
        [
            "",
            "Hand-off: the runner capability probe work must capture this derived rate "
            "alongside the CPU model in its per-run environment fingerprint. Doing so "
            "would retroactively label these groups with the host attribution they "
            "currently lack.",
        ]
    )

    lines.extend(
        [
            "",
            "## Metrics",
            "",
            "| Metric | n | median | mad | iqr | cv % | min | max | spread |",
            "|---|---|---|---|---|---|---|---|---|",
        ]
    )

    for metric_key in sorted(metrics):
        stats = metrics[metric_key]
        if stats.get("field_class") not in DISPERSION_CLASSES:
            continue

        def cell(key: str, stats: dict[str, Any] = stats) -> str:
            value = stats.get(key)
            if isinstance(value, str):
                return value
            if isinstance(value, (int, float)):
                return fmt_float(float(value))
            return "n/a"

        lines.append(
            "| {metric} | {n} | {median} | {mad} | {iqr} | {cv} | {minimum} | {maximum} | {spread} |".format(
                metric=metric_key,
                n=stats.get("n", "n/a"),
                median=cell("median"),
                mad=cell("mad"),
                iqr=cell("iqr"),
                cv=cell("cv_percent"),
                minimum=cell("minimum"),
                maximum=cell("maximum"),
                spread=cell("spread"),
            )
        )

    populations = sidecar.get(
        "populations",
        {
            "threshold": DEFAULT_SHRINK_SPLIT,
            "host-dominated": [],
            "intrinsic-noise": [],
            "unclassified-dispersion": [],
            "largest_below": None,
            "smallest_at_or_above": None,
        },
    )

    def _shrink_sort_key(item: tuple[str, dict[str, Any]]) -> tuple[int, Any]:
        metric_key, entry = item
        ratio = entry.get("shrink_ratio")
        if isinstance(ratio, (int, float)):
            return (0, -ratio)
        return (1, metric_key)

    def _fmt_cell(value: Any) -> str:
        if isinstance(value, str):
            return value
        if isinstance(value, (int, float)):
            return fmt_float(float(value))
        return "n/a"

    shrink_entries = [
        (metric_key, entry)
        for metric_key, entry in metrics.items()
        if entry.get("field_class") == "measurement"
    ]

    lines.extend(
        [
            "",
            "## Shrink table",
            "",
            "Pooled coefficient of variation against within-host-group coefficient of "
            "variation, per measured metric, sorted by shrink ratio descending. This is "
            "the pooled-to-stratified shrink ratio computed, not asserted.",
            "",
            "| Metric | pooled cv % | within cv % | between-group share | shrink ratio | n |",
            "|---|---|---|---|---|---|",
        ]
    )
    for metric_key, entry in sorted(shrink_entries, key=_shrink_sort_key):
        lines.append(
            "| {metric} | {pooled} | {within} | {between} | {shrink} | {n} |".format(
                metric=metric_key,
                pooled=_fmt_cell(entry.get("cv_percent")),
                within=_fmt_cell(entry.get("within_cv_percent")),
                between=_fmt_cell(entry.get("eta_squared")),
                shrink=_fmt_cell(entry.get("shrink_ratio")),
                n=entry.get("n", "n/a"),
            )
        )

    threshold = populations["threshold"]
    largest_below = populations["largest_below"]
    smallest_at_or_above = populations["smallest_at_or_above"]
    lines.extend(
        [
            "",
            "## Two populations",
            "",
            "Measured metrics split into two named populations by whether their pooled "
            f"shrink ratio clears {fmt_float(threshold)}x. `host-dominated` metrics need "
            "host stratification as their remedy. `intrinsic-noise` metrics need a "
            "different remedy: stratifying by host does not reduce this population's "
            "dispersion, so pooling across hosts is not the source of their spread.",
            "",
            f"- Threshold: {fmt_float(threshold)}x",
            "- Largest shrink ratio strictly below the threshold: "
            + (fmt_float(largest_below) if largest_below is not None else "n/a"),
            "- Smallest shrink ratio at or above the threshold: "
            + (fmt_float(smallest_at_or_above) if smallest_at_or_above is not None else "n/a"),
            "",
            "**host-dominated:**",
            "",
        ]
    )
    for metric_key in populations["host-dominated"]:
        lines.append(f"- `{metric_key}`")
    lines.extend(["", "**intrinsic-noise:**", ""])
    for metric_key in populations["intrinsic-noise"]:
        lines.append(f"- `{metric_key}`")
    if populations["unclassified-dispersion"]:
        lines.extend(["", "**unclassified-dispersion:**", ""])
        for metric_key in populations["unclassified-dispersion"]:
            lines.append(f"- `{metric_key}`")

    lines.extend(
        [
            "",
            "## Correlations",
            "",
            "Values, not opinions: whether a metric tracks publication time or the only "
            "host characteristic the published records ever carry is answered with a "
            "number, never with yes, no, correlated, or uncorrelated. `published_at` and "
            "`host_rate_ghz` are Pearson coefficients (`statistics.correlation`) between "
            "the cell's values and, respectively, the epoch-converted publication "
            "timestamp and the TSC-derived host rate in GHz. Branch is a categorical "
            "covariate: it has no natural numeric ordering, so a Pearson coefficient is "
            "not applicable to it, and `branch_variance_share` instead reports branch's "
            "share of total variance from the same one-way sum-of-squares decomposition "
            "used for host-group stratification above.",
            "",
            "| Metric | published_at | host_rate_ghz | branch_variance_share |",
            "|---|---|---|---|",
        ]
    )
    for metric_key, entry in sorted(shrink_entries, key=lambda item: item[0]):
        corr = entry.get("correlations", {})
        lines.append(
            "| {metric} | {published_at} | {host_rate} | {branch} |".format(
                metric=metric_key,
                published_at=_fmt_cell(corr.get("published_at")),
                host_rate=_fmt_cell(corr.get("host_rate_ghz")),
                branch=_fmt_cell(corr.get("branch_variance_share")),
            )
        )

    unparsable_shas = source["unparsable_record_shas"]
    recorded_covariates = sidecar.get("recorded_covariates", {"key_union": [], "key_intersection": []})
    key_union = recorded_covariates.get("key_union", [])
    key_intersection = recorded_covariates.get("key_intersection", [])
    lines.extend(
        [
            "",
            "## Recorded covariates",
            "",
            "The claim that no runner characteristic other than the derived rate was ever "
            "recorded is stated here with evidence, not by assertion.",
            "",
            f"- Key union across every published record: "
            f"{', '.join(f'`{key}`' for key in key_union) if key_union else 'none'}",
            f"- Key intersection across every published record: "
            f"{', '.join(f'`{key}`' for key in key_intersection) if key_intersection else 'none'}",
            "- Neither set contains a CPU, host, runner, or architecture field: the "
            "published record schema never carried one.",
            f"- Records with an unparsable `published_at`, excluded from the time "
            f"correlation only: {len(unparsable_shas)}"
            + (f" ({', '.join(unparsable_shas)})" if unparsable_shas else " (none)"),
            "",
            "The CI perf job in `.github/workflows/rogue_ci.yml` never captures CPU "
            "information into its log. The only CPU-count expression inside that job is "
            "a `cmake --build` parallelism argument whose value is consumed by the build "
            "and never printed; the job contains no `lscpu` call and no read of the "
            "kernel CPU information file.",
            "",
            "No back-fill of run metadata from the CI provider API was attempted, for "
            "three reasons: hosted runner names are generic, so no CPU model would come "
            "back; the oldest published records predate the provider's log retention "
            "window; and the locally available provider CLI predates the commands such a "
            "back-fill would need.",
        ]
    )

    mde_z = sidecar["parameters"]["mde_z"]
    mde_gate_pct = sidecar["parameters"]["mde_gate_pct"]
    lines.extend(
        [
            "",
            "## Provisional minimum detectable effect (non-binding)",
            "",
            "Provisional, non-binding formula: `mde_pct = z * cv * 100.0 / math.sqrt(n)`, "
            "the two-sided 95 percent normal-approximation half-width with no power "
            f"term. Provisional, non-binding z value: {fmt_float(mde_z)}. This figure is "
            "provisional and non-binding: the authoritative minimum detectable effect "
            "belongs to the later harness and measurement campaign work, not to this "
            "report.",
            "",
            f"Provisional, non-binding tier gate: {fmt_float(mde_gate_pct)}% "
            "(`--mde-gate-pct`), applied to the within-host-group figure below. Every "
            "recommendation is provisional and non-binding, traceable to the named rule "
            "that produced it; the binding tier assignment belongs to the later harness "
            "and measurement campaign work, not to this report.",
            "",
            "| Metric | n | mde pooled % (provisional, non-binding) | "
            "mde within % (provisional, non-binding) | "
            "recommendation (provisional, non-binding) | rule |",
            "|---|---|---|---|---|---|",
        ]
    )
    for metric_key, entry in sorted(shrink_entries, key=lambda item: item[0]):
        lines.append(
            "| {metric} | {n} | {pooled} | {within} | {rec} | {rule} |".format(
                metric=metric_key,
                n=entry.get("n", "n/a"),
                pooled=_fmt_cell(entry.get("mde_pooled_pct")),
                within=_fmt_cell(entry.get("mde_within_pct")),
                rec=f"{entry.get('tier_recommendation')} (provisional, non-binding)",
                rule=entry.get("tier_rule"),
            )
        )

    lines.extend(
        [
            "",
            "## Inventory",
            "",
            "Every key found in any benchmark `raw` object, classified by explicit key name so a "
            "newly published key is never silently absorbed. Cells marked "
            f"`{INSUFFICIENT_SAMPLES}` have too few samples for a coefficient of variation.",
            "",
            "| Metric | Series | Field | Class | n |",
            "|---|---|---|---|---|",
        ]
    )
    for metric_key in sorted(metrics):
        stats = metrics[metric_key]
        lines.append(
            "| {metric} | {series} | {field} | {field_class} | {n} |".format(
                metric=metric_key,
                series=stats["series"],
                field=stats["field"],
                field_class=stats["field_class"],
                n=stats.get("n", "n/a"),
            )
        )

    lines.extend(
        [
            "",
            "### Algebraically redundant pairs",
            "",
            "Named here so they are not double counted as independent findings:",
            "",
        ]
    )
    for field_a, field_b, reason in REDUNDANT_PAIRS:
        lines.append(f"- `{field_a}` against `{field_b}`: {reason}")

    pooling_evidence = sidecar.get("pooling_evidence", {"host_group": None, "record_count": 0, "per_branch": {}})
    lines.extend(
        [
            "",
            "## Pooling evidence",
            "",
            "This is the evidence that pooling across branches is safe, rather than "
            "pooling being safe by assumption. Within the largest observed host group "
            f"(`{pooling_evidence.get('host_group')}`, "
            f"{pooling_evidence.get('record_count', 0)} records), the per-branch median "
            "of each measured metric is compared against that group's overall median.",
            "",
            "| Metric | Branch | n | median | relative deviation |",
            "|---|---|---|---|---|",
        ]
    )
    per_branch = pooling_evidence.get("per_branch", {})
    for branch in sorted(per_branch):
        branch_metrics = per_branch[branch].get("metrics", {})
        for metric_key in sorted(branch_metrics):
            cell = branch_metrics[metric_key]
            deviation = cell.get("relative_deviation")
            deviation_cell = fmt_float(deviation) if isinstance(deviation, float) else deviation
            lines.append(
                f"| {metric_key} | {branch} | {cell.get('n', 'n/a')} | "
                f"{fmt_float(cell['median']) if isinstance(cell.get('median'), float) else 'n/a'} | "
                f"{deviation_cell} |"
            )

    repeated = sidecar.get("repeated_commits", [])
    lines.extend(
        [
            "",
            "## Repeated commits",
            "",
            f"{len(repeated)} commit(s) were published more than once from separate CI "
            "runs. Identical commit, separate CI runs: any spread between members is "
            "measurement noise, not a code change. Both members of every repeated commit "
            "stay in the pooled population; neither is averaged away nor dropped.",
            "",
        ]
    )
    for entry in repeated:
        short_sha = entry["sha"][:7]
        lines.append(f"### `{short_sha}`")
        lines.append("")
        lines.append("| Branch | Host group |")
        lines.append("|---|---|")
        for member in entry["members"]:
            lines.append(f"| {member['branch']} | {member['host_group']} |")
        lines.append("")
        lines.append("| Metric | Branch | Value | Relative delta |")
        lines.append("|---|---|---|---|")
        for metric_key in sorted(entry["measurements"]):
            for member in entry["measurements"][metric_key]:
                delta = member["relative_delta"]
                delta_cell = fmt_float(delta) if isinstance(delta, float) else delta
                lines.append(
                    f"| {metric_key} | {member['branch']} | {fmt_float(member['value'])} | "
                    f"{delta_cell} |"
                )
        lines.append("")

    lines.append("")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    published_root = Path(args.published_root).resolve() if args.published_root else None
    out_md = Path(args.out_md)
    out_json = Path(args.out_json)

    if published_root is not None:
        gh_pages_commit = ""
        history_paths = list_history_paths_from_root(published_root)
        all_paths = list_all_perf_paths_from_root(published_root)
    else:
        gh_pages_commit = resolve_ref(args.gh_pages_ref) or ""
        if not gh_pages_commit:
            print(f"Could not resolve ref: {args.gh_pages_ref}")
            print(f"Run: {FETCH_COMMAND}")
            return 1
        history_paths = list_history_paths(args.gh_pages_ref)
        all_paths = list_all_perf_paths(args.gh_pages_ref)

    records: list[dict[str, Any]] = []
    records_skipped = 0
    git_ref = None if published_root is not None else args.gh_pages_ref
    for relative_path in history_paths:
        record = load_record(relative_path, git_ref=git_ref, published_root=published_root)
        if record is None:
            records_skipped += 1
            continue
        record = dict(record)
        record["_path"] = relative_path
        records.append(record)

    if not records:
        print(f"No records parsed. Skipped: {records_skipped}")
        return 1

    rows = flatten_records(records)
    group_by_path = assign_host_groups(rows, records)
    host_groups = build_host_groups(records, group_by_path)
    population = build_population(history_paths, all_paths, records)
    metrics = build_field_inventory(
        rows,
        history_record_count=population["history_record_count"],
        min_n=args.min_n,
        shrink_split=args.shrink_split,
        mde_z=args.mde_z,
        mde_gate_pct=args.mde_gate_pct,
    )
    populations = split_populations(metrics, args.shrink_split)
    pooling_evidence = per_branch_medians(rows, host_groups, args.min_n)
    repeated_commit_entries = repeated_commits(rows)
    timestamps_unparsable, unparsable_record_shas, published_at_span = _timestamp_audit(records)
    recorded_covariates = recorded_covariate_evidence(records)

    for metric_key, entry in metrics.items():
        n = entry.get("n")
        missing = entry.get("records_missing_cell")
        if not isinstance(n, int) or not isinstance(missing, int) or (
            n + missing != population["history_record_count"]
        ):
            print(
                f"No-discard invariant violated for {metric_key}: "
                f"n={n} records_missing_cell={missing} "
                f"history_record_count={population['history_record_count']}"
            )
            return 1

    sidecar = build_sidecar(
        gh_pages_commit=gh_pages_commit,
        record_count=len(records),
        records_skipped=records_skipped,
        min_n=args.min_n,
        shrink_split=args.shrink_split,
        mde_z=args.mde_z,
        mde_gate_pct=args.mde_gate_pct,
        metrics=metrics,
        population=population,
        host_groups=host_groups,
        populations=populations,
        pooling_evidence=pooling_evidence,
        repeated_commit_entries=repeated_commit_entries,
        timestamps_unparsable=timestamps_unparsable,
        unparsable_record_shas=unparsable_record_shas,
        published_at_span=published_at_span,
        recorded_covariates=recorded_covariates,
    )

    markdown = render_markdown(sidecar)

    write_deterministic_json(out_json, sidecar)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown, encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
