#!/usr/bin/env python3
# ----------------------------------------------------------------------------
# Title      : ROGUE Perf Gate Baseline
# ----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
# ----------------------------------------------------------------------------

"""Per (benchmark, metric) gate baseline sidecar generator.

Aggregates the committed tests/perf/_perf_harness.py records under
docs/plans/perf-ci-hardening/harness-runs/ into a baseline keyed by the exact
cell a later gate decision compares at: one benchmark and one metric
together, never a metric pooled across every benchmark that measures it. A
metric constant on one benchmark and varying on another must not gate just
because some other benchmark's cell happened to look stable; grouping at the
pooled-metric level would hide exactly that failure mode. Each cell records
its own observed sample count, spread, and CPU model coverage, so
scripts/perf_gate_evaluator.py's later candidate-versus-merge-base comparison
rests on a documented, reproducible per-cell derivation rather than a number
with no traceable origin.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import perf_campaign_report  # noqa: E402  (flat sibling import, path inserted above)
import perf_noise_report  # noqa: E402  (flat sibling import, path inserted above)
import perf_tier_registry  # noqa: E402  (flat sibling import, path inserted above)


# Left at 1 even though this cell gains a new `tier` key: nothing in production reads
# baseline_version, the evaluator reads `tier` defensively (a baseline written before this
# change simply carries no tier per cell rather than being rejected), and bumping this
# constant would mint a version number with no reader while adding a new rejection mode.
BASELINE_VERSION = 1

DEFAULT_RUNS_DIR = "docs/plans/perf-ci-hardening/harness-runs"
DEFAULT_OUT_JSON = "docs/plans/perf-ci-hardening/gate-baseline.json"
DEFAULT_OUT_MD = "docs/plans/perf-ci-hardening/GATE-BASELINE.md"

# One constant pins the population this baseline is generated from, so a
# retargeted campaign_report tree hash and this baseline's tree hash can
# never silently diverge.
DEFAULT_EXPECTED_TREE_HASH = perf_campaign_report.DEFAULT_EXPECTED_TREE_HASH

# min_n comes from the committed docs/plans/perf-ci-hardening/noise-floor.json sidecar
# rather than a literal number written at a use site here, matching perf_campaign_report.py's
# own convention.
_NOISE_FLOOR_DEFAULTS = perf_campaign_report.load_noise_floor_parameters(
    Path(perf_campaign_report.DEFAULT_NOISE_FLOOR_PATH)
)
DEFAULT_MIN_N = _NOISE_FLOOR_DEFAULTS["min_n"]

# Exists only to reconcile this baseline's recomputed constant-cell count against the 137
# the phase's own planning notes state (the recomputed figure is 138); never used to gate
# anything and never substituted for DEFAULT_MIN_N anywhere in the admission path.
REFERENCE_MIN_N = 20

CELL_MEASURED = "measured"
CELL_NO_SAMPLES = "no-samples"
CELL_INSUFFICIENT_SAMPLES = "insufficient-samples"

GATE_RULE_EXACT_EQUALITY = "exact-equality"
GATE_RULE_NON_GATING = "non-gating"

NON_GATING_VARIES = "varies-within-population"
NON_GATING_ONE_MODEL = "insufficient-cpu-model-coverage"
NON_GATING_NO_SAMPLES = "no-clean-sample-in-population"

CANONICAL_COMMAND = (
    "python3 scripts/perf_gate_baseline.py "
    f"--runs-dir {DEFAULT_RUNS_DIR} --expected-tree-hash {DEFAULT_EXPECTED_TREE_HASH} "
    f"--min-n {DEFAULT_MIN_N} --out-json {DEFAULT_OUT_JSON} --out-md {DEFAULT_OUT_MD}"
)


def _cpu_model_of(record: dict[str, Any]) -> str:
    """The recorded `environment.cpu_model` string, or the shared MISSING_FIELD sentinel
    when absent or not a string, mirroring perf_campaign_report._cpu_model_of's own
    derivation without reaching across the module boundary for a private helper."""
    environment = record.get("environment")
    environment = environment if isinstance(environment, dict) else {}
    cpu_model = environment.get("cpu_model")
    return cpu_model if isinstance(cpu_model, str) and cpu_model else perf_campaign_report.MISSING_FIELD


def _collect_cell_samples(records: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    """Every clean numeric sample recorded for each (benchmark, metric) pair across every
    accepted record, plus the set of CPU models any of those samples were observed on.
    Benchmarks and metrics are walked in sorted order so this is deterministic regardless
    of dict insertion order. A non-numeric sample (the counter-regressed sentinel string)
    is excluded rather than coerced, exactly as
    perf_campaign_report._collect_metric_samples excludes one."""
    collected: dict[tuple[str, str], dict[str, Any]] = {}
    for record in records:
        model = _cpu_model_of(record)
        benchmarks = record.get("benchmarks")
        if not isinstance(benchmarks, dict):
            continue
        for bench_name in sorted(benchmarks):
            bench_entry = benchmarks[bench_name]
            if not isinstance(bench_entry, dict):
                continue
            metrics = bench_entry.get("metrics")
            if not isinstance(metrics, dict):
                continue
            for metric_name in sorted(metrics):
                metric_entry = metrics[metric_name]
                if not isinstance(metric_entry, dict):
                    continue
                for sample in metric_entry.get("samples", []) or []:
                    if isinstance(sample, (int, float)) and not isinstance(sample, bool):
                        key = (bench_name, metric_name)
                        cell = collected.setdefault(key, {"samples": [], "cpu_models": set()})
                        cell["samples"].append(float(sample))
                        cell["cpu_models"].add(model)
    return collected


def _build_cell(samples: list[float], cpu_models: set[str], min_n: int) -> dict[str, Any]:
    """One cell's sentinel or measured statistics, never a mean (matching
    perf_noise_report.dispersion's own no-mean convention)."""
    n = len(samples)
    if n == 0:
        return {"status": CELL_NO_SAMPLES, "n": 0}
    if n < min_n:
        return {"status": CELL_INSUFFICIENT_SAMPLES, "n": n}

    stats = perf_noise_report.dispersion(samples)
    minimum = stats["minimum"]
    maximum = stats["maximum"]
    cell: dict[str, Any] = {
        "status": CELL_MEASURED,
        "n": n,
        "minimum": minimum,
        "maximum": maximum,
        "spread": stats["spread"],
        "median": stats["median"],
        "mad": stats["mad"],
        "cv": stats["cv"],
        "cpu_models": sorted(cpu_models),
    }
    if minimum == maximum:
        cell["observed_value"] = minimum
    cv = stats["cv"]
    if isinstance(cv, (int, float)) and not isinstance(cv, bool):
        cell["mde_two_sample_pct"] = perf_campaign_report.two_sample_mde_pct(cv, n)
    else:
        cell["mde_two_sample_pct"] = cv
    return cell


def gate_rule_for_metric(metric_cells: dict[str, dict[str, Any]]) -> tuple[str, str | None]:
    """`(GATE_RULE_EXACT_EQUALITY, None)` only when `metric_cells` (every benchmark cell
    registered for one metric) has at least one measured cell, every measured cell has
    minimum equal to maximum, and at least one measured cell was observed on 2 or more
    distinct CPU models. Otherwise `(GATE_RULE_NON_GATING, reason)` with exactly one of the
    three declared non-gating reasons. A metric constant on some benchmarks and varying on
    others is non-gating: admission is decided over every one of the metric's own cells
    together, never cell by cell."""
    measured = [cell for cell in metric_cells.values() if cell["status"] == CELL_MEASURED]
    if not measured:
        return GATE_RULE_NON_GATING, NON_GATING_NO_SAMPLES
    if any(cell["minimum"] != cell["maximum"] for cell in measured):
        return GATE_RULE_NON_GATING, NON_GATING_VARIES
    if not any(len(cell["cpu_models"]) >= 2 for cell in measured):
        return GATE_RULE_NON_GATING, NON_GATING_ONE_MODEL
    return GATE_RULE_EXACT_EQUALITY, None


def _cell_derivation(
    cell: dict[str, Any], benchmark: str, metric: str, gate_rule: str, non_gating_reason: str | None,
) -> str:
    """A derivation string naming the grouping the figure was computed at, the cell's own
    `n`, its observed spread, and the CPU models covered. A non-gating cell's derivation
    additionally names its own per-cell two-sample MDE as the recorded reason it cannot
    gate, when that figure is computable at this cell's own sample count."""
    grouping = f"grouped per (benchmark={benchmark!r}, metric={metric!r})"
    if cell["status"] == CELL_MEASURED:
        cpu_models = ", ".join(cell["cpu_models"]) or "none"
        base = (
            f"{grouping}; n={cell['n']}, observed minimum={perf_campaign_report.fmt_float(cell['minimum'])}, "
            f"maximum={perf_campaign_report.fmt_float(cell['maximum'])}, "
            f"spread={perf_campaign_report.fmt_float(cell['spread'])}; CPU models observed: {cpu_models}"
        )
        if gate_rule == GATE_RULE_NON_GATING:
            mde = perf_campaign_report.fmt_float(cell.get("mde_two_sample_pct"))
            base += (
                f"; non-gating ({non_gating_reason}); this cell's own two-sample MDE is {mde}%, "
                "the recorded reason it cannot gate on its own"
            )
        return base

    status_note = "no clean sample recorded" if cell["status"] == CELL_NO_SAMPLES else (
        f"only {cell['n']} clean sample(s) recorded, below the configured minimum"
    )
    base = f"{grouping}; n={cell['n']} ({status_note}); no CPU models observed"
    if gate_rule == GATE_RULE_NON_GATING:
        base += f"; non-gating ({non_gating_reason}); no per-cell MDE is computable at n={cell['n']}"
    return base


def build_cells(records: list[dict[str, Any]], min_n: int) -> dict[str, dict[str, Any]]:
    """Every one of `perf_tier_registry`'s 525 registered (benchmark, metric) pairs, keyed
    `[benchmark][metric]`, never keyed by metric alone at any point. Each cell carries its
    own status/statistics from `_build_cell`, plus a `gate_rule`, `non_gating_reason` (when
    non-gating), and `derivation` stamped from that metric's own `gate_rule_for_metric`
    verdict, so every cell of one metric agrees on whether that metric gates."""
    collected = _collect_cell_samples(records)

    cells: dict[str, dict[str, Any]] = {}
    for metric in sorted(perf_tier_registry.METRICS):
        descriptor = perf_tier_registry.METRICS[metric]
        for benchmark in sorted(descriptor["benchmarks"]):
            entry = collected.get((benchmark, metric))
            samples = entry["samples"] if entry else []
            cpu_models = entry["cpu_models"] if entry else set()
            cells.setdefault(benchmark, {})[metric] = _build_cell(samples, cpu_models, min_n)

    for metric in sorted(perf_tier_registry.METRICS):
        descriptor = perf_tier_registry.METRICS[metric]
        metric_cells = {benchmark: cells[benchmark][metric] for benchmark in descriptor["benchmarks"]}
        gate_rule, non_gating_reason = gate_rule_for_metric(metric_cells)
        for benchmark, cell in metric_cells.items():
            if gate_rule == GATE_RULE_EXACT_EQUALITY and cell["status"] != CELL_MEASURED:
                # This metric gates through its other benchmarks, but this one cell was
                # never itself measured: never stamp exact-equality (and the observed_value
                # contract that implies) onto a cell carrying no observed statistics.
                cell_gate_rule = GATE_RULE_NON_GATING
                cell_non_gating_reason: str | None = NON_GATING_NO_SAMPLES
            else:
                cell_gate_rule = gate_rule
                cell_non_gating_reason = non_gating_reason
            cell["gate_rule"] = cell_gate_rule
            if cell_gate_rule == GATE_RULE_NON_GATING:
                cell["non_gating_reason"] = cell_non_gating_reason
            # The registry's own tier value, stamped once at generation time: display
            # information beside gate_rule, never an input to gate_rule_for_metric itself. A
            # descriptor carrying no tier records null rather than guessing one.
            cell["tier"] = descriptor.get("tier")
            cell["derivation"] = _cell_derivation(cell, benchmark, metric, cell_gate_rule, cell_non_gating_reason)

    return cells


def _metric_gate_rules(cells: dict[str, dict[str, Any]]) -> dict[str, str]:
    """One `gate_rule` per metric, recomputed fresh from that metric's own cell statistics
    (never read back from a single cell's own possibly-relabeled `gate_rule` field, since an
    unmeasured cell belonging to an otherwise-gating metric is relabeled non-gating in
    `build_cells` itself)."""
    result: dict[str, str] = {}
    for metric in sorted(perf_tier_registry.METRICS):
        descriptor = perf_tier_registry.METRICS[metric]
        metric_cells = {benchmark: cells[benchmark][metric] for benchmark in descriptor["benchmarks"]}
        gate_rule, _ = gate_rule_for_metric(metric_cells)
        result[metric] = gate_rule
    return result


def build_census(cells: dict[str, dict[str, Any]], min_n: int, reference_min_n: int) -> dict[str, Any]:
    """Total, measured, no-samples, insufficient-samples, constant, varying, and gating
    cell counts; the count of gating metrics; the minimum and maximum `n` observed across
    measured cells; and the same measured/constant/varying counts recomputed at
    `reference_min_n` so the recomputed constant-cell figure can be reconciled against the
    137 the phase's own planning notes state."""
    total_cells = 0
    measured_cells = 0
    no_sample_cells = 0
    insufficient_sample_cells = 0
    constant_cells = 0
    varying_cells = 0
    gating_cells = 0
    gating_metric_names: set[str] = set()
    measured_n_values: list[int] = []
    measured_at_reference = 0
    constant_at_reference = 0
    varying_at_reference = 0

    for benchmark in sorted(cells):
        for metric in sorted(cells[benchmark]):
            cell = cells[benchmark][metric]
            total_cells += 1
            status = cell["status"]
            if status == CELL_NO_SAMPLES:
                no_sample_cells += 1
                continue
            if status == CELL_INSUFFICIENT_SAMPLES:
                insufficient_sample_cells += 1
                continue

            measured_cells += 1
            measured_n_values.append(cell["n"])
            constant = cell["minimum"] == cell["maximum"]
            if constant:
                constant_cells += 1
            else:
                varying_cells += 1
            if cell["gate_rule"] == GATE_RULE_EXACT_EQUALITY:
                gating_cells += 1
                gating_metric_names.add(metric)
            if cell["n"] >= reference_min_n:
                measured_at_reference += 1
                if constant:
                    constant_at_reference += 1
                else:
                    varying_at_reference += 1

    return {
        "total_cells": total_cells,
        "measured_cells": measured_cells,
        "no_sample_cells": no_sample_cells,
        "insufficient_sample_cells": insufficient_sample_cells,
        "constant_cells": constant_cells,
        "varying_cells": varying_cells,
        "gating_cells": gating_cells,
        "gating_metrics": len(gating_metric_names),
        "min_n_observed": min(measured_n_values) if measured_n_values else None,
        "max_n_observed": max(measured_n_values) if measured_n_values else None,
        "min_n": min_n,
        "reference_min_n": reference_min_n,
        "measured_cells_at_reference_min_n": measured_at_reference,
        "constant_cells_at_reference_min_n": constant_at_reference,
        "varying_cells_at_reference_min_n": varying_at_reference,
    }


def build_sidecar(
    *,
    population: dict[str, Any],
    min_n: int,
    expected_tree_hash: str | None,
    runs_dir: str,
    noise_floor_path: str | Path = perf_campaign_report.DEFAULT_NOISE_FLOOR_PATH,
) -> dict[str, Any]:
    accepted = population["accepted"]
    # The injected-load demonstration run is excluded from every cell, exactly as
    # perf_campaign_report.build_sidecar excludes it from every dispersion figure: laundering
    # it into the baseline would defeat the demonstration's own purpose.
    injected_records = [record for record in accepted if perf_campaign_report.is_injected_load_run(record)]
    clean_records = [record for record in accepted if not perf_campaign_report.is_injected_load_run(record)]

    noise_floor_params = perf_campaign_report.load_noise_floor_parameters(Path(noise_floor_path))

    cells = build_cells(clean_records, min_n)
    census = build_census(cells, min_n, REFERENCE_MIN_N)
    gate_rules = _metric_gate_rules(cells)
    gating_metrics = sorted(name for name, rule in gate_rules.items() if rule == GATE_RULE_EXACT_EQUALITY)
    non_gating_metrics = sorted(name for name, rule in gate_rules.items() if rule == GATE_RULE_NON_GATING)

    return {
        "baseline_version": BASELINE_VERSION,
        "source": {
            "runs_dir": runs_dir,
            "expected_tree_hash": expected_tree_hash,
            "record_count": len(accepted),
            "records_skipped": population["records_skipped"],
            "records_rejected": population["records_rejected"],
            "records_injected_demonstration": len(injected_records),
            "record_count_clean": len(clean_records),
            "injected_demonstration_run_ids": sorted(
                record.get("_run_id", perf_campaign_report.MISSING_FIELD) for record in injected_records
            ),
            "noise_floor_parameters": noise_floor_params,
        },
        "census": census,
        "gating_metrics": gating_metrics,
        "non_gating_metrics": non_gating_metrics,
        "cells": cells,
    }


def render_markdown(sidecar: dict[str, Any]) -> str:
    source = sidecar["source"]
    census = sidecar["census"]
    noise_floor = source["noise_floor_parameters"]
    fmt = perf_campaign_report.fmt_float

    lines = [
        "<!-- generated by scripts/perf_gate_baseline.py, do not edit by hand -->",
        "# Perf Gate Baseline",
        "",
        "## Reproducing this baseline",
        "",
        "```sh",
        CANONICAL_COMMAND,
        "```",
        "",
        "## Source",
        "",
        f"- Runs directory: `{source['runs_dir']}`",
        f"- Expected tree hash: `{source['expected_tree_hash']}`",
        f"- Records accepted: {source['record_count']}",
        f"- Records skipped (malformed/unrecognized schema): {source['records_skipped']}",
        f"- Records rejected (tree hash mismatch): {source['records_rejected']}",
        f"- Records dispatched as an injected-load demonstration: "
        f"{source['records_injected_demonstration']} "
        f"({', '.join(source['injected_demonstration_run_ids']) or 'none'}), excluded from every cell below",
        f"- Clean records feeding every cell below: {source['record_count_clean']}",
        "- Noise floor parameters (min_n, mde_z, mde_gate_pct) source: "
        f"`{noise_floor['source_file']}` (loaded={noise_floor['loaded']}): "
        f"min_n={fmt(noise_floor['min_n'])}, mde_z={fmt(noise_floor['mde_z'])}, "
        f"mde_gate_pct={fmt(noise_floor['mde_gate_pct'])}",
        "",
        "## Census",
        "",
        f"- Total cells: {census['total_cells']}",
        f"- Measured cells: {census['measured_cells']}",
        f"- No-sample cells: {census['no_sample_cells']}",
        f"- Insufficient-sample cells: {census['insufficient_sample_cells']}",
        f"- Constant cells: {census['constant_cells']}",
        f"- Varying cells: {census['varying_cells']}",
        f"- Gating cells: {census['gating_cells']}",
        f"- Gating metrics: {census['gating_metrics']}",
        f"- Minimum n observed (measured cells): {fmt(census['min_n_observed'])}",
        f"- Maximum n observed (measured cells): {fmt(census['max_n_observed'])}",
        f"- Configured min_n: {census['min_n']}",
        f"- Reference floor for reconciliation against the phase's own recorded figure: "
        f"{census['reference_min_n']} (measured at this floor: "
        f"{census['measured_cells_at_reference_min_n']}, constant: "
        f"{census['constant_cells_at_reference_min_n']}, varying: "
        f"{census['varying_cells_at_reference_min_n']})",
        "",
        "## Gating cells",
        "",
        f"Metrics admitted to `{GATE_RULE_EXACT_EQUALITY}`: constant across every one of their "
        "own measured cells and observed on 2 or more distinct CPU models on at least one of them.",
        "",
        "The observed value recorded below is provenance, not the comparand: with same-job "
        "paired measurement the gate compares the candidate leg against the merge-base leg, "
        "so this baseline decides which cells gate and under which rule, and regenerating "
        "this baseline is how the gating cell set changes, not how a threshold is updated. A "
        "one-time intentional change is handled by the commit-trailer override, never by "
        "editing this file.",
        "",
    ]

    if sidecar["gating_metrics"]:
        lines.append("| Metric | Benchmark | n | Observed value | Tier | CPU models |")
        lines.append("|---|---|---|---|---|---|")
        for metric in sidecar["gating_metrics"]:
            for benchmark in sorted(sidecar["cells"]):
                cell = sidecar["cells"][benchmark].get(metric)
                if cell is None or cell["status"] != CELL_MEASURED:
                    continue
                lines.append(
                    "| " + metric
                    + " | " + benchmark
                    + " | " + str(cell["n"])
                    + " | " + fmt(cell.get("observed_value"))
                    + " | " + fmt(cell.get("tier"))
                    + " | " + ", ".join(cell["cpu_models"])
                    + " |"
                )
    else:
        lines.append("No metric is currently admitted to gate.")
    lines.append("")

    lines.extend([
        "## Non-gating cells",
        "",
        "Metrics not admitted to gate, with the reason recorded against the metric as a whole:",
        "",
        "| Metric | Reason |",
        "|---|---|",
    ])
    for metric in sidecar["non_gating_metrics"]:
        reason = None
        for benchmark in sorted(sidecar["cells"]):
            cell = sidecar["cells"][benchmark].get(metric)
            if cell is not None and cell.get("non_gating_reason"):
                reason = cell["non_gating_reason"]
                break
        lines.append(f"| {metric} | {reason or ''} |")
    lines.append("")

    return "\n".join(lines) + "\n"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--runs-dir",
        default=DEFAULT_RUNS_DIR,
        help="Directory containing committed per-run harness JSON files",
    )
    parser.add_argument(
        "--expected-tree-hash",
        default=DEFAULT_EXPECTED_TREE_HASH,
        help="git rev-parse HEAD^{tree} the population is pinned to",
    )
    parser.add_argument(
        "--min-n",
        type=int,
        default=DEFAULT_MIN_N,
        help="Minimum clean sample count before a cell is measured rather than suppressed",
    )
    parser.add_argument(
        "--out-json",
        default=DEFAULT_OUT_JSON,
        help="Output path for the generated JSON sidecar",
    )
    parser.add_argument(
        "--out-md",
        default=DEFAULT_OUT_MD,
        help="Output path for the generated markdown companion",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    runs_dir = Path(args.runs_dir)
    paths = sorted(runs_dir.glob("*.json")) if runs_dir.is_dir() else []
    population = perf_campaign_report.build_population(paths, args.expected_tree_hash)

    if not population["accepted"]:
        print(
            "No harness-run records survived population membership. "
            f"Skipped (malformed/unrecognized schema): {population['records_skipped']}, "
            f"Rejected (tree hash mismatch): {population['records_rejected']}"
        )
        return 1

    sidecar = build_sidecar(
        population=population,
        min_n=args.min_n,
        expected_tree_hash=args.expected_tree_hash,
        runs_dir=str(runs_dir),
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
