# ----------------------------------------------------------------------------
# Title      : Perf Gate Validation Report Tests
# ----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
# ----------------------------------------------------------------------------

"""Unit tests for scripts/perf_gate_validation_report.py, following
tests/utilities/test_perf_campaign_report.py's fixture style: small, hand-built two-leg
records and verdict sidecars rather than a real population, with the real
scripts/perf_gate_evaluator.py doing the actual per-cell comparison every test relies on.
"""

from __future__ import annotations

import importlib
import json
import re
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

perf_gate_validation_report = importlib.import_module("perf_gate_validation_report")
perf_gate_evaluator = importlib.import_module("perf_gate_evaluator")

R = perf_gate_validation_report
E = perf_gate_evaluator


# --- fixture helpers ---------------------------------------------------------------------


def _baseline_cell_gating(observed_value: Any, n: int = 10) -> dict[str, Any]:
    return {
        "status": "measured",
        "n": n,
        "minimum": observed_value,
        "maximum": observed_value,
        "spread": 0,
        "median": observed_value,
        "mad": 0.0,
        "cv": 0.0,
        "cpu_models": ["Model A", "Model B"],
        "observed_value": observed_value,
        "gate_rule": "exact-equality",
        "derivation": f"grouped per cell; n={n}, observed value {observed_value}",
    }


def _baseline_cell_nongating(median: float, mad: float, n: int = 10) -> dict[str, Any]:
    return {
        "status": "measured",
        "n": n,
        "minimum": median - mad,
        "maximum": median + mad,
        "spread": 2 * mad,
        "median": median,
        "mad": mad,
        "cv": 0.1,
        "cpu_models": ["Model A", "Model B"],
        "gate_rule": "non-gating",
        "non_gating_reason": "varies-within-population",
        "derivation": f"grouped per cell; n={n}; non-gating",
    }


def make_baseline(cells: dict[str, dict[str, Any]]) -> dict[str, Any]:
    gating_metrics = sorted({
        metric for metric_map in cells.values() for metric, cell in metric_map.items()
        if cell.get("gate_rule") == "exact-equality"
    })
    return {
        "baseline_version": 1,
        "cells": cells,
        "gating_metrics": gating_metrics,
        "non_gating_metrics": [],
        "census": {"total_cells": sum(len(m) for m in cells.values()), "gating_cells": len(gating_metrics)},
    }


BASIC_BASELINE = make_baseline({"bench_a": {"count_metric": _baseline_cell_gating(100)}})


def _benchmarks_for(cell_map: dict[tuple[str, str], Any]) -> dict[str, Any]:
    benchmarks: dict[str, Any] = {}
    for (bench, metric), value in cell_map.items():
        entry = benchmarks.setdefault(bench, {"metrics": {}})
        if value is None:
            continue
        samples = list(value) if isinstance(value, (list, tuple)) else [value]
        # Real merged leg entries (perf_gate_ab_runner._merge_metric_rounds) carry a `median`
        # field whenever the merged status is clean; measurement_detected reads that field
        # directly rather than recomputing it from `samples`.
        entry["metrics"][metric] = {
            "status": "ok", "samples": samples, "n_clean": len(samples),
            "median": sorted(float(v) for v in samples)[len(samples) // 2],
        }
    return benchmarks


def make_ab_record(
    run_id: str,
    *,
    label: str = "null-population",
    mode: str = "null",
    patch_name: str | None = None,
    patch_magnitude: str | None = None,
    patch_applied: bool = False,
    candidate_cells: dict[tuple[str, str], Any] | None = None,
    merge_base_cells: dict[tuple[str, str], Any] | None = None,
    timings: dict[str, Any] | None = None,
    round_count_candidate: int = 2,
    round_count_merge_base: int = 2,
    tree_hash_pair_match: bool = True,
    measured_modules: list[str] | None = None,
    measured_modules_is_default: bool | None = None,
) -> dict[str, Any]:
    run_info: dict[str, Any] = {
        "github_run_id": run_id,
        "github_run_attempt": "1",
        "campaign_branch": "test",
        "dispatch_index": "1",
        "mode": mode,
        "label": label,
        "rounds": 2,
        "patch_name": patch_name,
        "patch_sha256": None,
        "patch_magnitude": patch_magnitude,
        "patch_applied": patch_applied,
        "forced_condition": None,
        "declared_candidate_ref": "a" * 40,
        "declared_merge_base_ref": "a" * 40,
        "declared_candidate_tree_hash": "t1",
        "declared_merge_base_tree_hash": "t1",
        "candidate_sha": "a" * 40,
        "merge_base_sha": "a" * 40,
        "candidate_tree_hash": "t1",
        "merge_base_tree_hash": "t1",
        "tree_hash_pair_match": tree_hash_pair_match,
    }
    # Only set when the caller asks: a real pre-existing record carries neither field, and
    # that absence (not a default value here) is exactly what R._narrowed_module_runs must
    # treat as a default-set run.
    if measured_modules is not None:
        run_info["measured_modules"] = measured_modules
    if measured_modules_is_default is not None:
        run_info["measured_modules_is_default"] = measured_modules_is_default
    return {
        "gate_ab_schema_version": 1,
        "run": run_info,
        "environment": {"cpu_model": "Model A"},
        "legs": {
            "candidate": {
                "benchmarks": _benchmarks_for(candidate_cells or {}),
                "round_count": round_count_candidate,
            },
            "merge_base": {
                "benchmarks": _benchmarks_for(merge_base_cells or {}),
                "round_count": round_count_merge_base,
            },
        },
        "timings": timings or {
            "worktree_candidate": 0.1,
            "worktree_merge_base": 0.1,
            "patch_candidate": {"value": "unavailable", "reason": "no patch requested"},
            "build_candidate": 10.0,
            "build_merge_base": 10.0,
            "measure_candidate": 20.0,
            "measure_merge_base": 20.0,
            "total": 60.0,
        },
        "stages": {},
        "errors": [],
    }


def make_verdict(verdict: str = "PASS") -> dict[str, Any]:
    return {"evaluator_schema_version": 1, "verdict": verdict, "cells": [], "condition_counts": {}}


def write_population(root: Path, run_id: str, record: dict[str, Any], verdict: dict[str, Any]) -> None:
    (root / f"{run_id}-ab-record.json").write_text(json.dumps(record), encoding="utf-8")
    (root / f"{run_id}-verdict.json").write_text(json.dumps(verdict), encoding="utf-8")


def read_population(root: Path) -> dict[str, Any]:
    record_paths = sorted(root.glob(f"*{R.GATE_RECORD_SUFFIX}"))
    verdict_paths = sorted(root.glob(f"*{R.VERDICT_SUFFIX}"))
    return R.build_population(record_paths, verdict_paths)


# --- population, pairing, and skip reasons ------------------------------------------------


def test_build_population_pairs_by_run_id_and_counts_each_skip_reason_separately(tmp_path):
    good = make_ab_record("good", candidate_cells={("bench_a", "count_metric"): 100},
                          merge_base_cells={("bench_a", "count_metric"): 100})
    write_population(tmp_path, "good", good, make_verdict("PASS"))

    (tmp_path / "orphanrecord-ab-record.json").write_text(json.dumps(good), encoding="utf-8")
    (tmp_path / "orphanverdict-verdict.json").write_text(json.dumps(make_verdict("PASS")), encoding="utf-8")
    (tmp_path / "broken-ab-record.json").write_text("{not json", encoding="utf-8")
    (tmp_path / "broken-verdict.json").write_text(json.dumps(make_verdict("PASS")), encoding="utf-8")
    (tmp_path / "oldschema-ab-record.json").write_text(
        json.dumps({**good, "gate_ab_schema_version": 999}), encoding="utf-8",
    )
    (tmp_path / "oldschema-verdict.json").write_text(json.dumps(make_verdict("PASS")), encoding="utf-8")

    population = read_population(tmp_path)

    assert len(population["accepted"]) == 1
    assert population["accepted"][0]["run_id"] == "good"
    assert population["skipped_counts"][R.SKIP_RECORD_WITHOUT_VERDICT] == 1
    assert population["skipped_counts"][R.SKIP_VERDICT_WITHOUT_RECORD] == 1
    assert population["skipped_counts"][R.SKIP_UNPARSEABLE] == 1
    assert population["skipped_counts"][R.SKIP_UNRECOGNIZED_SCHEMA] == 1


def test_load_gate_record_returns_none_for_missing_malformed_nonmapping_and_bad_schema(tmp_path):
    assert R.load_gate_record(tmp_path / "does-not-exist.json") is None

    malformed = tmp_path / "malformed.json"
    malformed.write_text("{not valid json", encoding="utf-8")
    assert R.load_gate_record(malformed) is None

    non_mapping = tmp_path / "list.json"
    non_mapping.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
    assert R.load_gate_record(non_mapping) is None

    bad_schema = tmp_path / "bad_schema.json"
    bad_schema.write_text(json.dumps({"gate_ab_schema_version": 999}), encoding="utf-8")
    assert R.load_gate_record(bad_schema) is None

    good = tmp_path / "good.json"
    good.write_text(json.dumps(make_ab_record("x")), encoding="utf-8")
    assert R.load_gate_record(good) is not None


def test_load_verdict_returns_none_for_missing_malformed_nonmapping_and_bad_schema(tmp_path):
    assert R.load_verdict(tmp_path / "does-not-exist.json") is None

    malformed = tmp_path / "malformed.json"
    malformed.write_text("{not valid json", encoding="utf-8")
    assert R.load_verdict(malformed) is None

    non_mapping = tmp_path / "list.json"
    non_mapping.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
    assert R.load_verdict(non_mapping) is None

    bad_schema = tmp_path / "bad_schema.json"
    bad_schema.write_text(json.dumps({"evaluator_schema_version": 999}), encoding="utf-8")
    assert R.load_verdict(bad_schema) is None

    good = tmp_path / "good.json"
    good.write_text(json.dumps(make_verdict("PASS")), encoding="utf-8")
    assert R.load_verdict(good) is not None


def test_categorize_promotes_patch_failed_only_when_a_patch_was_actually_requested():
    never_patched = make_ab_record("n1")
    assert R.categorize(never_patched)[0] != R.CATEGORY_PATCH_FAILED

    patch_failed = make_ab_record(
        "p1", patch_name="extra-memcpy-per-frame.patch", patch_applied=False,
    )
    assert R.categorize(patch_failed)[0] == R.CATEGORY_PATCH_FAILED

    unrecognized_label = make_ab_record("u1", label="something-else")
    category, observed_label = R.categorize(unrecognized_label)
    assert category == R.CATEGORY_UNCATEGORIZED
    assert observed_label == "something-else"


# --- rates and the false-positive campaign ------------------------------------------------


def test_20_null_runs_all_pass_reports_zero_fail_and_inconclusive_rate_over_20(tmp_path):
    for i in range(20):
        record = make_ab_record(f"run{i}", candidate_cells={("bench_a", "count_metric"): 100},
                                merge_base_cells={("bench_a", "count_metric"): 100})
        write_population(tmp_path, f"run{i}", record, make_verdict("PASS"))

    population = read_population(tmp_path)
    recomputed = R.recompute_verdicts(population, BASIC_BASELINE)
    section = R.build_false_positive_section(recomputed["runs"])

    assert section["null_population"]["fail_rate"] == {"numerator": 0, "denominator": 20, "percent": 0.0}
    assert section["null_population"]["inconclusive_rate"]["numerator"] == 0
    assert section["null_population"]["inconclusive_rate"]["denominator"] == 20


def test_one_failing_null_run_is_listed_by_id_with_its_failing_gating_cells(tmp_path):
    record = make_ab_record("failrun", candidate_cells={("bench_a", "count_metric"): 101},
                            merge_base_cells={("bench_a", "count_metric"): 100})
    write_population(tmp_path, "failrun", record, make_verdict("FAIL"))

    population = read_population(tmp_path)
    recomputed = R.recompute_verdicts(population, BASIC_BASELINE)
    section = R.build_false_positive_section(recomputed["runs"])

    assert section["null_population"]["fail_count"] == 1
    assert section["null_population"]["failing_runs"] == [
        {"run_id": "failrun", "failing_cells": [{"benchmark": "bench_a", "metric": "count_metric"}]},
    ]


def test_null_and_unrelated_populations_reported_separately_then_combined(tmp_path):
    for i in range(3):
        record = make_ab_record(f"null{i}", label=R.LABEL_NULL,
                                candidate_cells={("bench_a", "count_metric"): 100},
                                merge_base_cells={("bench_a", "count_metric"): 100})
        write_population(tmp_path, f"null{i}", record, make_verdict("PASS"))
    for i in range(2):
        record = make_ab_record(f"unrel{i}", label=R.LABEL_UNRELATED,
                                candidate_cells={("bench_a", "count_metric"): 100},
                                merge_base_cells={("bench_a", "count_metric"): 100})
        write_population(tmp_path, f"unrel{i}", record, make_verdict("PASS"))

    population = read_population(tmp_path)
    recomputed = R.recompute_verdicts(population, BASIC_BASELINE)
    section = R.build_false_positive_section(recomputed["runs"])

    assert section["null_population"]["run_count"] == 3
    assert section["unrelated_population"]["run_count"] == 2
    assert section["combined"]["run_count"] == 5
    assert (
        section["combined"]["run_count"]
        == section["null_population"]["run_count"] + section["unrelated_population"]["run_count"]
    )


def test_a_category_with_zero_runs_reports_an_undefined_rate_with_zero_denominator():
    section = R.build_false_positive_section([])
    assert section["unrelated_population"]["fail_rate"]["percent"] == R.RATE_UNDEFINED
    assert section["unrelated_population"]["fail_rate"]["denominator"] == 0
    assert section["null_population"]["inconclusive_rate"]["percent"] == R.RATE_UNDEFINED


def test_recorded_and_recomputed_verdict_disagreement_is_counted_and_both_are_reported(tmp_path):
    record = make_ab_record("run1", candidate_cells={("bench_a", "count_metric"): 100},
                            merge_base_cells={("bench_a", "count_metric"): 100})
    write_population(tmp_path, "run1", record, make_verdict("FAIL"))

    population = read_population(tmp_path)
    recomputed = R.recompute_verdicts(population, BASIC_BASELINE)

    assert recomputed["disagreement_count"] == 1
    assert recomputed["runs"][0]["recorded_verdict"] == "FAIL"
    assert recomputed["runs"][0]["recomputed_verdict"] == "PASS"
    assert recomputed["runs"][0]["agree"] is False


def test_condition_table_keeps_declared_order_and_includes_zero_count_entries(tmp_path):
    baseline = make_baseline({
        "bench_a": {
            "count_metric": _baseline_cell_gating(100),
            "extra_metric": _baseline_cell_nongating(50.0, 1.0),
        },
    })
    record = make_ab_record("run1", candidate_cells={("bench_a", "count_metric"): 100},
                            merge_base_cells={("bench_a", "count_metric"): 100})
    write_population(tmp_path, "run1", record, make_verdict("PASS"))

    population = read_population(tmp_path)
    recomputed = R.recompute_verdicts(population, baseline)
    section = R.build_condition_section(recomputed["runs"])

    assert list(section["conditions"]) == list(E.INCONCLUSIVE_CONDITIONS)
    assert section["conditions"][E.REASON_METRIC_ABSENT] == 1
    assert section["conditions"][E.REASON_GUARD_EXCEEDED] == 0


def test_nongating_inconclusive_rate_is_recomputed_not_copied_from_the_harness_figure(tmp_path):
    record = make_ab_record("run1", candidate_cells={("bench_a", "count_metric"): 100},
                            merge_base_cells={("bench_a", "count_metric"): 100})
    write_population(tmp_path, "run1", record, make_verdict("PASS"))

    population = read_population(tmp_path)
    recomputed = R.recompute_verdicts(population, BASIC_BASELINE)
    section = R.build_nongating_inconclusive_section(recomputed["runs"])

    assert section["harness_comparison"]["numerator"] == 855
    assert section["harness_comparison"]["denominator"] == 5352
    assert section["rate"]["denominator"] != 5352


def test_gate_level_and_nongating_inconclusive_rates_appear_in_adjacent_markdown_sections(tmp_path):
    record = make_ab_record("run1", candidate_cells={("bench_a", "count_metric"): 100},
                            merge_base_cells={("bench_a", "count_metric"): 100})
    write_population(tmp_path, "run1", record, make_verdict("PASS"))

    population = read_population(tmp_path)
    recomputed = R.recompute_verdicts(population, BASIC_BASELINE)
    sidecar = R.build_sidecar(
        population=population, recomputed=recomputed, baseline=BASIC_BASELINE,
        runs_dir=str(tmp_path), baseline_path="baseline.json",
    )
    markdown = R.render_markdown(sidecar)

    gate_index = markdown.index("## Inconclusive conditions")
    nongating_index = markdown.index("## Non-gating metric inconclusive rate")
    assert gate_index < nongating_index
    assert markdown[gate_index:nongating_index].count("## ") == 1


# --- detection --------------------------------------------------------------------------


def test_seeded_confirm_run_is_gate_detected_for_its_own_patch_not_a_different_one(tmp_path):
    baseline = make_baseline({"fifo_perf": {"buffer_copy_count": _baseline_cell_gating(100)}})
    record = make_ab_record(
        "confirm1", label=R.LABEL_SEEDED_CONFIRM, mode="seeded-regression",
        patch_name="extra-memcpy-per-frame.patch", patch_magnitude="1", patch_applied=True,
        candidate_cells={("fifo_perf", "buffer_copy_count"): 200},
        merge_base_cells={("fifo_perf", "buffer_copy_count"): 100},
    )
    write_population(tmp_path, "confirm1", record, make_verdict("FAIL"))

    population = read_population(tmp_path)
    recomputed = R.recompute_verdicts(population, baseline)
    evaluation = recomputed["runs"][0]["evaluation"]

    assert R.gate_detected(evaluation, "extra-memcpy-per-frame.patch") is True
    assert R.gate_detected(evaluation, "disable-frame-batching.patch") is False


def test_delay_patch_run_that_fails_for_an_unrelated_reason_is_never_gate_detected(tmp_path):
    baseline = make_baseline({"fifo_perf": {"buffer_copy_count": _baseline_cell_gating(100)}})
    record = make_ab_record(
        "delay1", label=R.LABEL_SEEDED_CONFIRM, mode="seeded-regression",
        patch_name="per-transaction-delay.patch", patch_magnitude="1000", patch_applied=True,
        candidate_cells={("fifo_perf", "buffer_copy_count"): 200},
        merge_base_cells={("fifo_perf", "buffer_copy_count"): 100},
    )
    write_population(tmp_path, "delay1", record, make_verdict("FAIL"))

    population = read_population(tmp_path)
    recomputed = R.recompute_verdicts(population, baseline)
    evaluation = recomputed["runs"][0]["evaluation"]

    assert evaluation["verdict"] == E.VERDICT_FAIL
    assert R.gate_detected(evaluation, "per-transaction-delay.patch") is False
    assert R.expected_metrics_for_patch("per-transaction-delay.patch") == ()


def test_measurement_detected_true_when_candidate_median_moves_outside_the_dispersion_band(tmp_path):
    baseline = make_baseline({"bench_a": {"soft_metric": _baseline_cell_nongating(50.0, 1.0)}})
    record = make_ab_record(
        "m1", candidate_cells={("bench_a", "soft_metric"): 500.0},
        merge_base_cells={("bench_a", "soft_metric"): 50.0},
    )
    assert R.measurement_detected(record, baseline, "any-patch") is True


def test_measurement_detected_false_when_candidate_median_stays_within_the_dispersion_band(tmp_path):
    baseline = make_baseline({"bench_a": {"soft_metric": _baseline_cell_nongating(50.0, 1.0)}})
    record = make_ab_record(
        "m2", candidate_cells={("bench_a", "soft_metric"): 50.5},
        merge_base_cells={("bench_a", "soft_metric"): 50.0},
    )
    assert R.measurement_detected(record, baseline, "any-patch") is False


# --- smallest detected magnitude ----------------------------------------------------------


def test_smallest_detected_magnitude_skips_an_unstable_magnitude_but_keeps_it_in_the_table(tmp_path):
    baseline = make_baseline({"fifo_perf": {"buffer_copy_count": _baseline_cell_gating(100)}})

    stable_at_1 = make_ab_record(
        "m1a", label=R.LABEL_SEEDED_CONFIRM, mode="seeded-regression",
        patch_name="extra-memcpy-per-frame.patch", patch_magnitude="1", patch_applied=True,
        candidate_cells={("fifo_perf", "buffer_copy_count"): 200},
        merge_base_cells={("fifo_perf", "buffer_copy_count"): 100},
    )
    unstable_at_1 = make_ab_record(
        "m1b", label=R.LABEL_SEEDED_CONFIRM, mode="seeded-regression",
        patch_name="extra-memcpy-per-frame.patch", patch_magnitude="1", patch_applied=True,
        candidate_cells={("fifo_perf", "buffer_copy_count"): [200, 205]},
        merge_base_cells={("fifo_perf", "buffer_copy_count"): 100},
    )
    stable_at_2 = make_ab_record(
        "m2a", label=R.LABEL_SEEDED_CONFIRM, mode="seeded-regression",
        patch_name="extra-memcpy-per-frame.patch", patch_magnitude="2", patch_applied=True,
        candidate_cells={("fifo_perf", "buffer_copy_count"): 200},
        merge_base_cells={("fifo_perf", "buffer_copy_count"): 100},
    )
    for run_id, record in (("m1a", stable_at_1), ("m1b", unstable_at_1), ("m2a", stable_at_2)):
        write_population(tmp_path, run_id, record, make_verdict("FAIL"))

    population = read_population(tmp_path)
    recomputed = R.recompute_verdicts(population, baseline)
    section = R.build_smallest_magnitude_section(recomputed["runs"], baseline)
    entry = section["patches"]["extra-memcpy-per-frame"]["metrics"]["buffer_copy_count"]
    by_magnitude = {c["magnitude"]: c for c in entry["candidates"]}

    assert by_magnitude["1"]["stable"] is False
    assert E.REASON_WITHIN_RUN_UNSTABLE in by_magnitude["1"]["repeatability_verdicts"]
    assert by_magnitude["2"]["stable"] is True
    assert entry["smallest_detected"]["magnitude"] == "2"
    assert entry["smallest_detected"]["absolute_delta"] == 100
    assert entry["smallest_detected"]["percent_of_baseline"] == 100.0


def test_baseline_value_of_zero_yields_undefined_percentage_not_a_division_error(tmp_path):
    baseline = make_baseline({"fifo_perf": {"transaction_lock_acquisitions": _baseline_cell_gating(0)}})
    record = make_ab_record(
        "z1", label=R.LABEL_SEEDED_CONFIRM, mode="seeded-regression",
        patch_name="extra-transaction-lock.patch", patch_magnitude="1", patch_applied=True,
        candidate_cells={("fifo_perf", "transaction_lock_acquisitions"): 5},
        merge_base_cells={("fifo_perf", "transaction_lock_acquisitions"): 0},
    )
    write_population(tmp_path, "z1", record, make_verdict("FAIL"))

    population = read_population(tmp_path)
    recomputed = R.recompute_verdicts(population, baseline)
    section = R.build_smallest_magnitude_section(recomputed["runs"], baseline)
    entry = section["patches"]["extra-transaction-lock"]["metrics"]["transaction_lock_acquisitions"]

    assert entry["smallest_detected"]["percent_of_baseline"] == R.RATE_UNDEFINED
    assert entry["smallest_detected"]["absolute_delta"] == 5


def test_delay_patch_reports_no_gating_metric_and_no_metrics_table(tmp_path):
    baseline = make_baseline({"bench_a": {"count_metric": _baseline_cell_gating(100)}})
    section = R.build_smallest_magnitude_section([], baseline)
    entry = section["patches"][R.DELAY_PATCH_KEY]
    assert entry["metrics"] == {}
    assert "no gating metric" in entry["no_gating_metric_reason"].lower()


# --- module-set deviation ------------------------------------------------------------------


def test_smallest_magnitude_section_adds_no_narrowed_key_when_every_run_used_the_default_module_set(tmp_path):
    baseline = make_baseline({"fifo_perf": {"buffer_copy_count": _baseline_cell_gating(100)}})
    record = make_ab_record(
        "confirm1", label=R.LABEL_SEEDED_CONFIRM, mode="seeded-regression",
        patch_name="extra-memcpy-per-frame.patch", patch_magnitude="1", patch_applied=True,
        candidate_cells={("fifo_perf", "buffer_copy_count"): 200},
        merge_base_cells={("fifo_perf", "buffer_copy_count"): 100},
    )
    write_population(tmp_path, "confirm1", record, make_verdict("FAIL"))

    population = read_population(tmp_path)
    recomputed = R.recompute_verdicts(population, baseline)
    section = R.build_smallest_magnitude_section(recomputed["runs"], baseline)
    entry = section["patches"]["extra-memcpy-per-frame"]

    assert "narrowed_module_runs" not in entry


def test_smallest_magnitude_section_records_a_narrowed_run_with_its_module_set(tmp_path):
    baseline = make_baseline({"fifo_perf": {"buffer_copy_count": _baseline_cell_gating(100)}})
    record = make_ab_record(
        "confirm1", label=R.LABEL_SEEDED_CONFIRM, mode="seeded-regression",
        patch_name="extra-memcpy-per-frame.patch", patch_magnitude="1", patch_applied=True,
        candidate_cells={("fifo_perf", "buffer_copy_count"): 200},
        merge_base_cells={("fifo_perf", "buffer_copy_count"): 100},
        measured_modules=["tests/perf/test_fifo_perf.py"],
        measured_modules_is_default=False,
    )
    write_population(tmp_path, "confirm1", record, make_verdict("FAIL"))

    population = read_population(tmp_path)
    recomputed = R.recompute_verdicts(population, baseline)
    section = R.build_smallest_magnitude_section(recomputed["runs"], baseline)
    entry = section["patches"]["extra-memcpy-per-frame"]

    assert entry["narrowed_module_runs"] == [
        {"run_id": "confirm1", "measured_modules": ["tests/perf/test_fifo_perf.py"]},
    ]


def test_a_record_with_no_module_set_field_counts_as_a_default_set_run(tmp_path):
    baseline = make_baseline({"fifo_perf": {"buffer_copy_count": _baseline_cell_gating(100)}})
    record = make_ab_record(
        "confirm1", label=R.LABEL_SEEDED_CONFIRM, mode="seeded-regression",
        patch_name="extra-memcpy-per-frame.patch", patch_magnitude="1", patch_applied=True,
        candidate_cells={("fifo_perf", "buffer_copy_count"): 200},
        merge_base_cells={("fifo_perf", "buffer_copy_count"): 100},
    )
    write_population(tmp_path, "confirm1", record, make_verdict("FAIL"))

    population = read_population(tmp_path)
    recomputed = R.recompute_verdicts(population, baseline)

    assert R._narrowed_module_runs(recomputed["runs"]) == []


def test_rendered_markdown_states_the_narrowed_run_is_not_a_like_for_like_replica(tmp_path):
    baseline = make_baseline({"fifo_perf": {"buffer_copy_count": _baseline_cell_gating(100)}})
    record = make_ab_record(
        "confirm1", label=R.LABEL_SEEDED_CONFIRM, mode="seeded-regression",
        patch_name="extra-memcpy-per-frame.patch", patch_magnitude="1", patch_applied=True,
        candidate_cells={("fifo_perf", "buffer_copy_count"): 200},
        merge_base_cells={("fifo_perf", "buffer_copy_count"): 100},
        measured_modules=["tests/perf/test_fifo_perf.py"],
        measured_modules_is_default=False,
    )
    write_population(tmp_path, "confirm1", record, make_verdict("FAIL"))

    population = read_population(tmp_path)
    recomputed = R.recompute_verdicts(population, baseline)
    sidecar = R.build_sidecar(
        population=population, recomputed=recomputed, baseline=baseline,
        runs_dir=str(tmp_path), baseline_path="baseline.json",
    )
    markdown = R.render_markdown(sidecar)

    assert "not a like-for-like replica" in markdown
    assert "confirm1" in markdown
    assert "tests/perf/test_fifo_perf.py" in markdown


# --- confusion matrix ----------------------------------------------------------------------


def test_forced_inconclusive_run_never_appears_in_any_matrix_cell(tmp_path):
    record = make_ab_record(
        "fi1", label=R.LABEL_FORCED_INCONCLUSIVE, mode="forced-inconclusive",
        tree_hash_pair_match=False,
    )
    write_population(tmp_path, "fi1", record, make_verdict("INCONCLUSIVE"))

    population = read_population(tmp_path)
    recomputed = R.recompute_verdicts(population, BASIC_BASELINE)
    section = R.build_confusion_matrix_section(recomputed["runs"])

    total_in_matrix = sum(sum(row.values()) for row in section["matrix"].values())
    assert total_in_matrix == 0
    assert section["outside_matrix"]["counts"][R.LABEL_FORCED_INCONCLUSIVE] == 1


def test_confusion_matrix_counts_confirm_runs_seeded_row_and_null_unrelated_unchanged_row(tmp_path):
    null_run = make_ab_record("n1", label=R.LABEL_NULL,
                              candidate_cells={("bench_a", "count_metric"): 100},
                              merge_base_cells={("bench_a", "count_metric"): 100})
    unrelated_run = make_ab_record("u1", label=R.LABEL_UNRELATED,
                                   candidate_cells={("bench_a", "count_metric"): 100},
                                   merge_base_cells={("bench_a", "count_metric"): 100})
    confirm_run = make_ab_record("c1", label=R.LABEL_SEEDED_CONFIRM, mode="seeded-regression",
                                 patch_name="extra-memcpy-per-frame.patch", patch_applied=True,
                                 candidate_cells={("bench_a", "count_metric"): 100},
                                 merge_base_cells={("bench_a", "count_metric"): 100})
    search_run = make_ab_record("s1", label=R.LABEL_SEEDED_SEARCH, mode="seeded-regression",
                                patch_name="extra-memcpy-per-frame.patch", patch_applied=True,
                                candidate_cells={("bench_a", "count_metric"): 100},
                                merge_base_cells={("bench_a", "count_metric"): 100})
    for run_id, record in (
        ("n1", null_run), ("u1", unrelated_run), ("c1", confirm_run), ("s1", search_run),
    ):
        write_population(tmp_path, run_id, record, make_verdict("PASS"))

    population = read_population(tmp_path)
    recomputed = R.recompute_verdicts(population, BASIC_BASELINE)
    section = R.build_confusion_matrix_section(recomputed["runs"])

    assert section["matrix"]["unchanged code"]["PASS"] == 2
    assert section["matrix"]["seeded regression"]["PASS"] == 1
    assert section["outside_matrix"]["counts"][R.LABEL_SEEDED_SEARCH] == 1


def test_matrix_total_plus_outside_total_equals_the_accepted_population_count(tmp_path):
    null_run = make_ab_record("n1", label=R.LABEL_NULL,
                              candidate_cells={("bench_a", "count_metric"): 100},
                              merge_base_cells={("bench_a", "count_metric"): 100})
    forced_run = make_ab_record("f1", label=R.LABEL_FORCED_INCONCLUSIVE, mode="forced-inconclusive",
                                tree_hash_pair_match=False)
    for run_id, record in (("n1", null_run), ("f1", forced_run)):
        write_population(tmp_path, run_id, record, make_verdict("PASS"))

    population = read_population(tmp_path)
    recomputed = R.recompute_verdicts(population, BASIC_BASELINE)
    section = R.build_confusion_matrix_section(recomputed["runs"])
    reconciliation = section["reconciliation"]

    assert reconciliation["matrix_total"] + reconciliation["outside_total"] == reconciliation["accepted_total"]
    assert reconciliation["accepted_total"] == len(recomputed["runs"]) == 2


# --- threshold derivations -------------------------------------------------------------


def test_threshold_derivation_section_carries_a_derivation_for_every_gating_cell():
    baseline = make_baseline({
        "bench_a": {
            "count_metric": _baseline_cell_gating(100),
            "soft_metric": _baseline_cell_nongating(50.0, 1.0),
        },
    })
    section = R.build_threshold_derivation_section(baseline)

    assert len(section["cells"]) == 1
    assert section["cells"][0]["benchmark"] == "bench_a"
    assert section["cells"][0]["metric"] == "count_metric"
    assert section["cells"][0]["derivation"]
    assert section["pooled_reconciliation_note"] == R.POOLED_RECONCILIATION_NOTE


# --- budget --------------------------------------------------------------------------


def test_budget_seconds_per_round_equals_measured_seconds_divided_by_round_count(tmp_path):
    record = make_ab_record(
        "b1", candidate_cells={("bench_a", "count_metric"): 100},
        merge_base_cells={("bench_a", "count_metric"): 100},
        timings={
            "worktree_candidate": 0.1, "worktree_merge_base": 0.1,
            "patch_candidate": {"value": "unavailable", "reason": "no patch requested"},
            "build_candidate": 10.0, "build_merge_base": 10.0,
            "measure_candidate": 40.0, "measure_merge_base": 30.0,
            "total": 100.0,
        },
        round_count_candidate=2, round_count_merge_base=3,
    )
    write_population(tmp_path, "b1", record, make_verdict("PASS"))

    population = read_population(tmp_path)
    recomputed = R.recompute_verdicts(population, BASIC_BASELINE)
    budget = R.build_budget_section(recomputed["runs"], budget_seconds=600)

    assert budget["seconds_per_round_per_leg"]["candidate"] == 20.0
    assert budget["seconds_per_round_per_leg"]["merge_base"] == 10.0
    assert budget["stages"]["total"]["median"] == 100.0
    assert budget["stages"]["total"]["n"] == 1


def test_budget_total_exactly_equal_to_the_budget_renders_at_the_boundary(tmp_path):
    record = make_ab_record(
        "b1", candidate_cells={("bench_a", "count_metric"): 100},
        merge_base_cells={("bench_a", "count_metric"): 100},
        timings={
            "worktree_candidate": 0.1, "worktree_merge_base": 0.1,
            "patch_candidate": {"value": "unavailable", "reason": "no patch requested"},
            "build_candidate": 10.0, "build_merge_base": 10.0,
            "measure_candidate": 40.0, "measure_merge_base": 40.0,
            "total": 600.0,
        },
    )
    write_population(tmp_path, "b1", record, make_verdict("PASS"))

    population = read_population(tmp_path)
    recomputed = R.recompute_verdicts(population, BASIC_BASELINE)
    budget = R.build_budget_section(recomputed["runs"], budget_seconds=600)

    assert budget["at_boundary"] is True
    assert budget["binding"] is False
    assert budget["stages"]["total"]["median"] == 600.0
    assert budget["budget_seconds"] == 600


def test_budget_run_with_zero_completed_rounds_is_excluded_with_a_reason(tmp_path):
    record = make_ab_record(
        "b1", candidate_cells={("bench_a", "count_metric"): 100},
        merge_base_cells={("bench_a", "count_metric"): 100},
        round_count_candidate=0,
    )
    write_population(tmp_path, "b1", record, make_verdict("PASS"))

    population = read_population(tmp_path)
    recomputed = R.recompute_verdicts(population, BASIC_BASELINE)
    budget = R.build_budget_section(recomputed["runs"], budget_seconds=600)

    assert budget["seconds_per_round_per_leg"]["candidate"] is None
    assert budget["excluded_runs"] == [{"run_id": "b1", "leg": "candidate", "reason": "zero completed rounds"}]


# --- byte stability, timestamps, and main() ---------------------------------------------


def test_main_writes_no_iso_timestamp_and_two_runs_write_byte_identical_files(tmp_path):
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    record = make_ab_record("run1", candidate_cells={("bench_a", "count_metric"): 100},
                            merge_base_cells={("bench_a", "count_metric"): 100})
    write_population(runs_dir, "run1", record, make_verdict("PASS"))

    baseline_path = tmp_path / "baseline.json"
    baseline_path.write_text(json.dumps(BASIC_BASELINE), encoding="utf-8")

    out_md1, out_json1 = tmp_path / "out1.md", tmp_path / "out1.json"
    out_md2, out_json2 = tmp_path / "out2.md", tmp_path / "out2.json"

    exit_code_1 = R.main([
        "--runs-dir", str(runs_dir), "--baseline", str(baseline_path),
        "--out-md", str(out_md1), "--out-json", str(out_json1),
    ])
    exit_code_2 = R.main([
        "--runs-dir", str(runs_dir), "--baseline", str(baseline_path),
        "--out-md", str(out_md2), "--out-json", str(out_json2),
    ])

    assert exit_code_1 == 0
    assert exit_code_2 == 0

    timestamp_re = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")
    assert timestamp_re.search(out_md1.read_text(encoding="utf-8")) is None
    assert timestamp_re.search(out_json1.read_text(encoding="utf-8")) is None
    assert out_md1.read_bytes() == out_md2.read_bytes()
    assert out_json1.read_bytes() == out_json2.read_bytes()


def test_main_writes_report_version(tmp_path):
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    record = make_ab_record("run1", candidate_cells={("bench_a", "count_metric"): 100},
                            merge_base_cells={("bench_a", "count_metric"): 100})
    write_population(runs_dir, "run1", record, make_verdict("PASS"))
    baseline_path = tmp_path / "baseline.json"
    baseline_path.write_text(json.dumps(BASIC_BASELINE), encoding="utf-8")
    out_md, out_json = tmp_path / "out.md", tmp_path / "out.json"

    exit_code = R.main([
        "--runs-dir", str(runs_dir), "--baseline", str(baseline_path),
        "--out-md", str(out_md), "--out-json", str(out_json),
    ])

    assert exit_code == 0
    sidecar = json.loads(out_json.read_text(encoding="utf-8"))
    assert sidecar["report_version"] == 1


def test_main_exits_1_and_writes_nothing_over_an_empty_population(tmp_path):
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    out_md, out_json = tmp_path / "out.md", tmp_path / "out.json"

    exit_code = R.main([
        "--runs-dir", str(empty_dir), "--out-md", str(out_md), "--out-json", str(out_json),
    ])

    assert exit_code == 1
    assert not out_md.exists()
    assert not out_json.exists()


# --- canonical reproduce command: executed for real, not paraphrased -------------------


def test_canonical_command_reproduces_byte_identically_over_a_fixture_population(tmp_path):
    argv = shlex.split(R.CANONICAL_COMMAND)

    assert argv[0].startswith("python")
    assert argv[1] == "scripts/perf_gate_validation_report.py"

    runs_dir_index = argv.index("--runs-dir") + 1
    out_md_index = argv.index("--out-md") + 1
    out_json_index = argv.index("--out-json") + 1
    assert argv[runs_dir_index] == R.DEFAULT_RUNS_DIR
    assert argv[out_md_index] == R.DEFAULT_OUT_MD
    assert argv[out_json_index] == R.DEFAULT_OUT_JSON

    fixture_runs_dir = tmp_path / "runs"
    fixture_runs_dir.mkdir()
    record = make_ab_record("fx1", candidate_cells={("bench_a", "count_metric"): 1},
                            merge_base_cells={("bench_a", "count_metric"): 1})
    write_population(fixture_runs_dir, "fx1", record, make_verdict("PASS"))

    scratch_md1, scratch_json1 = tmp_path / "r1.md", tmp_path / "r1.json"
    scratch_md2, scratch_json2 = tmp_path / "r2.md", tmp_path / "r2.json"

    argv[0] = sys.executable
    argv[runs_dir_index] = str(fixture_runs_dir)

    argv[out_md_index] = str(scratch_md1)
    argv[out_json_index] = str(scratch_json1)
    result1 = subprocess.run(argv, cwd=REPO_ROOT, capture_output=True, text=True)
    assert result1.returncode == 0, result1.stderr

    argv[out_md_index] = str(scratch_md2)
    argv[out_json_index] = str(scratch_json2)
    result2 = subprocess.run(argv, cwd=REPO_ROOT, capture_output=True, text=True)
    assert result2.returncode == 0, result2.stderr

    assert scratch_md1.read_bytes() == scratch_md2.read_bytes()
    assert scratch_json1.read_bytes() == scratch_json2.read_bytes()
# ----------------------------------------------------------------------------
