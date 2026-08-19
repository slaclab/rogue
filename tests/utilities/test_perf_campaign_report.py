# ----------------------------------------------------------------------------
# Title      : Perf Campaign Report Tests
# ----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
# ----------------------------------------------------------------------------

"""Unit tests for scripts/perf_campaign_report.py, following
tests/utilities/test_probe_capability_report.py's fixture style: every test
below is injectable and needs no Rogue build.
"""

from __future__ import annotations

import importlib
import json
import math
import shlex
import statistics
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

perf_campaign_report = importlib.import_module("perf_campaign_report")


def _write_harness_run(
    root: Path,
    filename: str,
    harness_run_schema_version: int = 1,
    run: dict | None = None,
    benchmarks: dict | None = None,
    environment: dict | None = None,
) -> Path:
    payload = {
        "harness_run_schema_version": harness_run_schema_version,
        "run": run
        or {
            "github_run_id": "1",
            "github_run_attempt": "1",
            "git_sha": "abc123",
            "git_tree_hash": "expected",
            "campaign_branch": "perf-harness/campaign",
            "dispatch_index": "1",
            "injected_load": "false",
        },
        "environment": environment if environment is not None else {},
        "build": {},
        "benchmarks": benchmarks
        if benchmarks is not None
        else {
            "remoteSetRate": {
                "metrics": {
                    "transaction_lock_acquisitions": {
                        "samples": [2000, 2000, 2000, 2000, 2000],
                        "median": 2000.0,
                        "mad": 0.0,
                        "n_clean": 5,
                        "tier_candidate": 1,
                        "within_run_repeatability": {"verdict": "bit-identical", "n": 5},
                        "status": "ok",
                        "reason": None,
                    },
                },
                "workload": {},
            },
        },
        "errors": [],
    }
    path = root / filename
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


# --- two_sample_mde_pct ------------------------------------------------


def test_two_sample_mde_pct_matches_the_normal_approximation_formula():
    result = perf_campaign_report.two_sample_mde_pct(0.05, 5)
    expected = (
        (perf_campaign_report.Z_ALPHA_2 + perf_campaign_report.Z_BETA)
        * math.sqrt(2.0 / 5)
        * 0.05
        * 100.0
    )
    assert result == expected


def test_two_sample_mde_pct_zero_cv_returns_exactly_zero():
    assert perf_campaign_report.two_sample_mde_pct(0.0, 5) == 0.0


# --- load_harness_run ----------------------------------------------------


def test_load_harness_run_invalid_json_returns_none(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{not valid json", encoding="utf-8")
    assert perf_campaign_report.load_harness_run(path) is None


def test_load_harness_run_unrecognized_schema_version_returns_none(tmp_path):
    path = _write_harness_run(tmp_path, "wrong-version.json", harness_run_schema_version=999)
    assert perf_campaign_report.load_harness_run(path) is None


def test_load_harness_run_missing_file_returns_none(tmp_path):
    assert perf_campaign_report.load_harness_run(tmp_path / "missing.json") is None


def test_load_harness_run_accepts_a_well_formed_record(tmp_path):
    path = _write_harness_run(tmp_path, "good.json")
    record = perf_campaign_report.load_harness_run(path)
    assert record is not None
    assert record["harness_run_schema_version"] == 1


# --- build_population ------------------------------------------------------


def test_build_population_rejects_tree_hash_mismatch(tmp_path):
    _write_harness_run(tmp_path, "good.json", run={"git_tree_hash": "expected"})
    _write_harness_run(tmp_path, "mismatch.json", run={"git_tree_hash": "other"})

    paths = sorted(tmp_path.glob("*.json"))
    population = perf_campaign_report.build_population(paths, "expected")

    assert len(population["accepted"]) == 1
    assert population["accepted"][0]["_run_id"] == "good"
    assert population["records_rejected"] == 1
    assert population["rejected_reasons"][0]["reason"] == perf_campaign_report.TREE_HASH_MISMATCH


def test_build_population_skips_malformed_records(tmp_path):
    (tmp_path / "bad.json").write_text("not json", encoding="utf-8")
    _write_harness_run(tmp_path, "good.json")

    paths = sorted(tmp_path.glob("*.json"))
    population = perf_campaign_report.build_population(paths, None)

    assert len(population["accepted"]) == 1
    assert population["records_skipped"] == 1


def test_build_population_with_no_expected_hash_accepts_everything(tmp_path):
    _write_harness_run(tmp_path, "a.json", run={"git_tree_hash": "one"})
    _write_harness_run(tmp_path, "b.json", run={"git_tree_hash": "two"})

    paths = sorted(tmp_path.glob("*.json"))
    population = perf_campaign_report.build_population(paths, None)

    assert len(population["accepted"]) == 2
    assert population["records_rejected"] == 0


# --- build_metric_section ----------------------------------------------


def test_build_metric_section_suppresses_below_min_n(tmp_path):
    path = _write_harness_run(tmp_path, "good.json")
    record = perf_campaign_report.load_harness_run(path)
    record["_run_id"] = "good"

    rows = perf_campaign_report.build_metric_section([record], min_n=10)

    row = rows["transaction_lock_acquisitions"]
    assert row["n"] == 5
    assert row["median"] == perf_campaign_report.INSUFFICIENT_SAMPLES
    assert row["tier_candidate"] == 1


def test_build_metric_section_computes_dispersion_at_or_above_min_n(tmp_path):
    path = _write_harness_run(tmp_path, "good.json")
    record = perf_campaign_report.load_harness_run(path)
    record["_run_id"] = "good"

    rows = perf_campaign_report.build_metric_section([record], min_n=3)

    row = rows["transaction_lock_acquisitions"]
    assert row["n"] == 5
    assert row["median"] == 2000.0
    assert row["mad"] == 0.0
    assert row["mde_two_sample_pct"] == 0.0


def test_build_metric_section_pools_samples_across_records(tmp_path):
    path_a = _write_harness_run(tmp_path, "a.json")
    path_b = _write_harness_run(tmp_path, "b.json")
    record_a = perf_campaign_report.load_harness_run(path_a)
    record_b = perf_campaign_report.load_harness_run(path_b)

    rows = perf_campaign_report.build_metric_section([record_a, record_b], min_n=3)

    assert rows["transaction_lock_acquisitions"]["n"] == 10


# --- Task 07-1: MDE side by side, candidate tier from records, non-gating -----------


def test_build_metric_section_reports_mde_one_sample_provisional_pct(tmp_path):
    path = _write_harness_run(tmp_path, "good.json")
    record = perf_campaign_report.load_harness_run(path)
    record["_run_id"] = "good"

    rows = perf_campaign_report.build_metric_section([record], min_n=3, mde_z=1.96)

    row = rows["transaction_lock_acquisitions"]
    assert "mde_one_sample_provisional_pct" in row
    # cv is 0.0 (bit-identical samples), so both MDE figures are exactly 0.0.
    assert row["mde_one_sample_provisional_pct"] == 0.0
    assert "mean" not in row


def test_build_metric_section_mde_one_sample_matches_perf_noise_report_formula(tmp_path):
    import importlib
    import sys as _sys
    from pathlib import Path as _Path

    scripts_dir = _Path(__file__).resolve().parents[2] / "scripts"
    if str(scripts_dir) not in _sys.path:
        _sys.path.insert(0, str(scripts_dir))
    perf_noise_report = importlib.import_module("perf_noise_report")

    benchmarks = {
        "remoteSetRate": {
            "metrics": {
                "transaction_lock_acquisitions": {
                    "samples": [1990, 2000, 2010, 1995, 2005],
                    "median": 2000.0,
                    "mad": 5.0,
                    "n_clean": 5,
                    "tier_candidate": 1,
                    "status": "ok",
                    "reason": None,
                },
            },
            "workload": {},
        },
    }
    path = _write_harness_run(tmp_path, "good.json", benchmarks=benchmarks)
    record = perf_campaign_report.load_harness_run(path)
    record["_run_id"] = "good"

    rows = perf_campaign_report.build_metric_section([record], min_n=3, mde_z=1.96)
    row = rows["transaction_lock_acquisitions"]

    expected = perf_noise_report.provisional_mde(row["cv"], row["n"], 1.96)
    assert row["mde_one_sample_provisional_pct"] == expected


def test_build_metric_section_marks_non_gating_when_mde_exceeds_gate_pct(tmp_path):
    benchmarks = {
        "remoteSetRate": {
            "metrics": {
                "transaction_lock_acquisitions": {
                    "samples": [1000, 2000, 3000, 4000, 5000],
                    "median": 3000.0,
                    "mad": 1000.0,
                    "n_clean": 5,
                    "tier_candidate": 1,
                    "status": "ok",
                    "reason": None,
                },
            },
            "workload": {},
        },
    }
    path = _write_harness_run(tmp_path, "good.json", benchmarks=benchmarks)
    record = perf_campaign_report.load_harness_run(path)
    record["_run_id"] = "good"

    rows = perf_campaign_report.build_metric_section([record], min_n=3, mde_gate_pct=0.001)

    row = rows["transaction_lock_acquisitions"]
    assert row["non_gating"] is True


def test_build_metric_section_not_non_gating_when_mde_is_zero(tmp_path):
    path = _write_harness_run(tmp_path, "good.json")
    record = perf_campaign_report.load_harness_run(path)
    record["_run_id"] = "good"

    rows = perf_campaign_report.build_metric_section([record], min_n=3, mde_gate_pct=2.0)

    row = rows["transaction_lock_acquisitions"]
    assert row["non_gating"] is False


def test_build_metric_section_suppresses_mde_fields_and_carries_a_reason_below_min_n(tmp_path):
    path = _write_harness_run(tmp_path, "good.json")
    record = perf_campaign_report.load_harness_run(path)
    record["_run_id"] = "good"

    rows = perf_campaign_report.build_metric_section([record], min_n=10)

    row = rows["transaction_lock_acquisitions"]
    assert row["mde_two_sample_pct"] == perf_campaign_report.INSUFFICIENT_SAMPLES
    assert row["mde_one_sample_provisional_pct"] == perf_campaign_report.INSUFFICIENT_SAMPLES
    assert row["non_gating"] is None
    assert isinstance(row["reason"], str) and row["reason"]


def test_build_metric_section_zero_sample_metric_is_not_omitted_and_carries_a_reason(tmp_path):
    path = _write_harness_run(tmp_path, "good.json")
    record = perf_campaign_report.load_harness_run(path)
    record["_run_id"] = "good"

    rows = perf_campaign_report.build_metric_section([record], min_n=3)

    # frame_lock_acquisitions is registered but this fixture record never measured it.
    row = rows["frame_lock_acquisitions"]
    assert row["n"] == 0
    assert isinstance(row["reason"], str) and row["reason"]


def test_build_metric_section_candidate_tier_sourced_from_record_not_registry(tmp_path):
    path = _write_harness_run(tmp_path, "good.json")
    record = perf_campaign_report.load_harness_run(path)
    record["_run_id"] = "good"

    rows = perf_campaign_report.build_metric_section([record], min_n=3)

    assert rows["transaction_lock_acquisitions"]["tier_candidate"] == 1


def test_build_metric_section_candidate_tier_not_recorded_when_absent_from_population(tmp_path):
    path = _write_harness_run(tmp_path, "good.json")
    record = perf_campaign_report.load_harness_run(path)
    record["_run_id"] = "good"

    rows = perf_campaign_report.build_metric_section([record], min_n=3)

    assert rows["frame_lock_acquisitions"]["tier_candidate"] == perf_campaign_report.TIER_CANDIDATE_NOT_RECORDED


def test_build_metric_section_suppresses_a_zero_sample_metric_even_with_an_unguarded_min_n():
    for min_n in (0, -1):
        rows = perf_campaign_report.build_metric_section([], min_n=min_n)
        row = rows["frame_lock_acquisitions"]
        assert row["n"] == 0
        for key in (
            "median", "mad", "cv", "minimum", "maximum",
            "mde_two_sample_pct", "mde_one_sample_provisional_pct",
        ):
            assert row[key] == perf_campaign_report.INSUFFICIENT_SAMPLES
        assert row["non_gating"] is None
        assert isinstance(row["reason"], str) and row["reason"]


def test_build_metric_section_threshold_matches_the_dispersion_cell_helper(tmp_path):
    benchmarks_at_min_n = {
        "remoteSetRate": {
            "metrics": {
                "transaction_lock_acquisitions": {
                    "samples": [2000, 2000, 2000],
                    "median": 2000.0,
                    "mad": 0.0,
                    "n_clean": 3,
                    "tier_candidate": 1,
                    "status": "ok",
                    "reason": None,
                },
            },
            "workload": {},
        },
    }
    benchmarks_below_min_n = {
        "remoteSetRate": {
            "metrics": {
                "transaction_lock_acquisitions": {
                    "samples": [2000, 2000],
                    "median": 2000.0,
                    "mad": 0.0,
                    "n_clean": 2,
                    "tier_candidate": 1,
                    "status": "ok",
                    "reason": None,
                },
            },
            "workload": {},
        },
    }

    path_at = _write_harness_run(tmp_path, "at_min_n.json", benchmarks=benchmarks_at_min_n)
    record_at = perf_campaign_report.load_harness_run(path_at)
    record_at["_run_id"] = "at_min_n"
    rows_at = perf_campaign_report.build_metric_section([record_at], min_n=3)
    assert rows_at["transaction_lock_acquisitions"]["median"] == 2000.0

    path_below = _write_harness_run(tmp_path, "below_min_n.json", benchmarks=benchmarks_below_min_n)
    record_below = perf_campaign_report.load_harness_run(path_below)
    record_below["_run_id"] = "below_min_n"
    rows_below = perf_campaign_report.build_metric_section([record_below], min_n=3)
    assert rows_below["transaction_lock_acquisitions"]["median"] == perf_campaign_report.INSUFFICIENT_SAMPLES


def test_report_is_byte_stable_when_the_live_registry_tier_changes(tmp_path):
    path = _write_harness_run(tmp_path, "good.json")
    record = perf_campaign_report.load_harness_run(path)
    record["_run_id"] = "good"
    population = {
        "accepted": [record], "records_skipped": 0, "skipped_reasons": [],
        "records_rejected": 0, "rejected_reasons": [],
    }

    sidecar_before = perf_campaign_report.build_sidecar(
        population=population, min_n=3, expected_tree_hash="expected", runs_dir=str(tmp_path),
    )
    markdown_before = perf_campaign_report.render_markdown(sidecar_before)

    original_tier = perf_campaign_report.perf_tier_registry.METRICS["transaction_lock_acquisitions"]["tier"]
    try:
        perf_campaign_report.perf_tier_registry.METRICS["transaction_lock_acquisitions"]["tier"] = 2
        sidecar_after = perf_campaign_report.build_sidecar(
            population=population, min_n=3, expected_tree_hash="expected", runs_dir=str(tmp_path),
        )
        markdown_after = perf_campaign_report.render_markdown(sidecar_after)
    finally:
        perf_campaign_report.perf_tier_registry.METRICS["transaction_lock_acquisitions"]["tier"] = original_tier

    assert sidecar_before["metrics"]["transaction_lock_acquisitions"]["tier_candidate"] == 1
    assert sidecar_after["metrics"]["transaction_lock_acquisitions"]["tier_candidate"] == 1
    assert markdown_before == markdown_after


def test_load_noise_floor_parameters_reads_the_real_committed_sidecar():
    from pathlib import Path as _Path

    params = perf_campaign_report.load_noise_floor_parameters(
        _Path(perf_campaign_report.DEFAULT_NOISE_FLOOR_PATH)
    )
    assert params["loaded"] is True
    assert params["min_n"] == 5
    assert params["mde_z"] == 1.96
    assert params["mde_gate_pct"] == 2.0


def test_load_noise_floor_parameters_falls_back_when_file_missing(tmp_path):
    params = perf_campaign_report.load_noise_floor_parameters(tmp_path / "missing.json")
    assert params["loaded"] is False
    assert params["min_n"] == perf_campaign_report.FALLBACK_MIN_N
    assert params["mde_gate_pct"] == perf_campaign_report.FALLBACK_MDE_GATE_PCT


# --- build_source_coverage_section --------------------------------------


def test_source_coverage_reports_covered_when_samples_exist(tmp_path):
    path = _write_harness_run(tmp_path, "good.json")
    record = perf_campaign_report.load_harness_run(path)

    coverage = perf_campaign_report.build_source_coverage_section([record])

    family = coverage["mutex_acquisitions"]
    assert family["status"] == "covered"
    # mutex_acquisitions now names two metrics (plan 03-03 registered
    # frame_lock_acquisitions alongside transaction_lock_acquisitions);
    # build_source_coverage_section reports the first family member in
    # sorted metric-name order as the representative source.
    assert family["source"] == "rogue.PerfCounters.getFrameLockCount"
    assert "transaction_lock_acquisitions" in family["metrics"]
    assert "frame_lock_acquisitions" in family["metrics"]


def test_source_coverage_reports_uncovered_with_no_records():
    coverage = perf_campaign_report.build_source_coverage_section([])

    family = coverage["mutex_acquisitions"]
    assert family["status"] == "uncovered"
    assert family["reason"] is not None


# --- render_markdown is byte-stable over the same sidecar --------------------


def test_render_markdown_is_byte_identical_over_the_same_sidecar(tmp_path):
    path = _write_harness_run(tmp_path, "good.json")
    record = perf_campaign_report.load_harness_run(path)
    record["_run_id"] = "good"
    population = {
        "accepted": [record],
        "records_skipped": 0,
        "skipped_reasons": [],
        "records_rejected": 0,
        "rejected_reasons": [],
    }
    sidecar = perf_campaign_report.build_sidecar(
        population=population, min_n=3, expected_tree_hash="expected", runs_dir=str(tmp_path),
    )

    first = perf_campaign_report.render_markdown(sidecar)
    second = perf_campaign_report.render_markdown(sidecar)

    assert first == second


# --- Task 07-2: cross-CPU-model invariance verdicts and recorded demotions --------


def _tier1_record(root, filename, run_id, cpu_model, values, run=None, extra_metric_fields=None):
    metric_entry = {
        "samples": values,
        "median": float(values[len(values) // 2]) if values else 0.0,
        "mad": 0.0,
        "n_clean": len(values),
        "tier_candidate": 1,
        "status": "ok",
        "reason": None,
    }
    if extra_metric_fields:
        metric_entry.update(extra_metric_fields)
    benchmarks = {
        "remoteSetRate": {
            "metrics": {"transaction_lock_acquisitions": metric_entry},
            "workload": {},
        },
    }
    default_run = {
        "github_run_id": run_id,
        "github_run_attempt": "1",
        "git_sha": "abc123",
        "git_tree_hash": "expected",
        "campaign_branch": "perf-harness/campaign",
        "dispatch_index": "1",
        "injected_load": "false",
    }
    if run:
        default_run.update(run)
    path = _write_harness_run(
        root, filename, run=default_run, benchmarks=benchmarks,
        environment={"cpu_model": cpu_model},
    )
    record = perf_campaign_report.load_harness_run(path)
    record["_run_id"] = path.stem
    return record


def test_build_invariance_section_groups_models_in_sorted_order(tmp_path):
    r_z = _tier1_record(tmp_path, "z.json", "1", "Zeta Model", [2000] * 5)
    r_a = _tier1_record(tmp_path, "a.json", "2", "Alpha Model", [2000] * 5)

    section = perf_campaign_report.build_invariance_section([r_z, r_a])

    coverage = section["coverage"]
    assert coverage["observed_cpu_models"] == ["Alpha Model", "Zeta Model"]
    assert coverage["observed_count"] == 2


def test_build_invariance_section_bit_identical_when_counts_equal_across_models(tmp_path):
    r1 = _tier1_record(tmp_path, "a.json", "1", "Model A", [2000] * 5)
    r2 = _tier1_record(tmp_path, "b.json", "2", "Model B", [2000] * 5)

    section = perf_campaign_report.build_invariance_section([r1, r2])
    entry = section["metrics"]["transaction_lock_acquisitions"]

    assert entry["verdict"] == perf_campaign_report.CROSS_MODEL_VERDICT_BIT_IDENTICAL
    assert entry["binding_tier"] == perf_campaign_report.perf_tier_registry.TIER_1


def test_build_invariance_section_single_model_is_insufficient_samples_not_promoted(tmp_path):
    r1 = _tier1_record(tmp_path, "a.json", "1", "Model A", [2000] * 5)

    section = perf_campaign_report.build_invariance_section([r1])
    entry = section["metrics"]["transaction_lock_acquisitions"]

    assert entry["verdict"] == perf_campaign_report.INSUFFICIENT_SAMPLES
    assert entry["binding_tier"] == perf_campaign_report.NOT_YET_DETERMINED


def test_build_invariance_section_demotes_when_counts_differ_across_models(tmp_path):
    r1 = _tier1_record(tmp_path, "a.json", "1", "Model A", [2000] * 5)
    r2 = _tier1_record(tmp_path, "b.json", "2", "Model B", [2001] * 5)

    section = perf_campaign_report.build_invariance_section([r1, r2])
    entry = section["metrics"]["transaction_lock_acquisitions"]

    assert entry["verdict"] == perf_campaign_report.CROSS_MODEL_VERDICT_DEMOTED
    assert entry["binding_tier"] == perf_campaign_report.perf_tier_registry.TIER_2
    assert entry["minimum"] == 2000
    assert entry["maximum"] == 2001
    assert entry["spread"] == 1


def test_build_invariance_section_within_run_demotion_overrides_cross_model_agreement(tmp_path):
    r1 = _tier1_record(
        tmp_path, "a.json", "1", "Model A", [2000] * 5,
        extra_metric_fields={"tier_demoted_to": 2, "min": 1999, "max": 2000, "spread": 1},
    )
    r2 = _tier1_record(tmp_path, "b.json", "2", "Model B", [2000] * 5)

    section = perf_campaign_report.build_invariance_section([r1, r2])
    entry = section["metrics"]["transaction_lock_acquisitions"]

    assert entry["binding_tier"] == perf_campaign_report.perf_tier_registry.TIER_2
    assert entry["within_run_demotions"]


def test_build_invariance_section_reports_coverage_against_phase_2(tmp_path):
    r1 = _tier1_record(tmp_path, "a.json", "1", "Model A", [2000] * 5)

    section = perf_campaign_report.build_invariance_section([r1])
    coverage = section["coverage"]

    assert coverage["phase_2_observed_count"] == 3
    assert coverage["reduced_coverage"] is True


def test_build_invariance_section_non_invariant_direction_metric_is_not_applicable_and_uncompared(tmp_path):
    path = _write_harness_run(tmp_path, "good.json", environment={"cpu_model": "Model A"})
    record = perf_campaign_report.load_harness_run(path)
    record["_run_id"] = "good"

    assert perf_campaign_report.perf_tier_registry.METRICS["avg_ns"]["direction"] != (
        perf_campaign_report.perf_tier_registry.DIRECTION_INVARIANT
    )

    section = perf_campaign_report.build_invariance_section([record])
    entry = section["metrics"]["avg_ns"]  # a Tier 3, non-invariant-direction registry metric

    assert entry["verdict"] == perf_campaign_report.NOT_APPLICABLE_NOT_INVARIANT
    assert entry["binding_tier"] == perf_campaign_report.TIER_CANDIDATE_NOT_RECORDED
    assert "minimum" not in entry
    assert "per_benchmark" not in entry


def test_build_sidecar_binding_tier_is_a_distinct_key_from_candidate_tier(tmp_path):
    r1 = _tier1_record(tmp_path, "a.json", "1", "Model A", [2000] * 5)
    population = {
        "accepted": [r1], "records_skipped": 0, "skipped_reasons": [],
        "records_rejected": 0, "rejected_reasons": [],
    }

    sidecar = perf_campaign_report.build_sidecar(
        population=population, min_n=3, expected_tree_hash="expected", runs_dir=str(tmp_path),
    )

    assert sidecar["metrics"]["transaction_lock_acquisitions"]["tier_candidate"] == 1
    invariance_entry = sidecar["invariance"]["metrics"]["transaction_lock_acquisitions"]
    assert "binding_tier" in invariance_entry
    assert invariance_entry["binding_tier"] != sidecar["metrics"]["transaction_lock_acquisitions"]["tier_candidate"]


# --- Per (benchmark, CPU model) invariance comparison, replacing the pooled comparison ----


def _multi_bench_record(
    root, filename, run_id, cpu_model, benchmark_samples,
    metric_name="transaction_lock_acquisitions", tier_candidate=1, run=None,
    extra_metric_fields=None,
):
    """A harness-run record carrying `metric_name` on several benchmarks at once, one clean
    sample list per benchmark name in `benchmark_samples`, all recorded under the same CPU
    model. Mirrors `_tier1_record`'s shape but supports more than its one hardcoded
    benchmark: the per-benchmark grouping defect this plan corrects is invisible on a
    population where a metric is only ever measured on a single benchmark.
    `extra_metric_fields` is an optional `{benchmark_name: {field: value}}` mapping applied
    to that benchmark's own metric entry only."""
    benchmarks = {}
    for bench_name, values in benchmark_samples.items():
        metric_entry = {
            "samples": values,
            "median": float(values[len(values) // 2]) if values else 0.0,
            "mad": 0.0,
            "n_clean": len(values),
            "tier_candidate": tier_candidate,
            "status": "ok",
            "reason": None,
        }
        if extra_metric_fields and bench_name in extra_metric_fields:
            metric_entry.update(extra_metric_fields[bench_name])
        benchmarks[bench_name] = {"metrics": {metric_name: metric_entry}, "workload": {}}

    default_run = {
        "github_run_id": run_id,
        "github_run_attempt": "1",
        "git_sha": "abc123",
        "git_tree_hash": "expected",
        "campaign_branch": "perf-harness/campaign",
        "dispatch_index": "1",
        "injected_load": "false",
    }
    if run:
        default_run.update(run)
    path = _write_harness_run(
        root, filename, run=default_run, benchmarks=benchmarks,
        environment={"cpu_model": cpu_model},
    )
    record = perf_campaign_report.load_harness_run(path)
    record["_run_id"] = path.stem
    return record


def test_build_invariance_section_per_benchmark_grouping_fixes_the_pooled_defect(tmp_path):
    # Constant on fifo_perf at 100 and constant on stream_bridge_perf at 200, observed on two
    # CPU models. Pooled across benchmarks this is 100 vs 200 (varying), which is exactly the
    # defect: a metric collected on several benchmarks with legitimately differing counts
    # could never pass a pooled exact-equality bar however deterministic each benchmark's own
    # cell was. Grouped per benchmark, each cell is separately constant, so the metric is
    # bit-identical.
    r1 = _multi_bench_record(
        tmp_path, "a.json", "1", "Model A",
        {"fifo_perf": [100] * 5, "stream_bridge_perf": [200] * 5},
    )
    r2 = _multi_bench_record(
        tmp_path, "b.json", "2", "Model B",
        {"fifo_perf": [100] * 5, "stream_bridge_perf": [200] * 5},
    )

    section = perf_campaign_report.build_invariance_section([r1, r2])
    entry = section["metrics"]["transaction_lock_acquisitions"]

    assert entry["verdict"] == perf_campaign_report.CROSS_MODEL_VERDICT_BIT_IDENTICAL
    assert entry["binding_tier"] == perf_campaign_report.perf_tier_registry.TIER_1
    assert entry["per_benchmark"]["fifo_perf"]["agrees"] is True
    assert entry["per_benchmark"]["stream_bridge_perf"]["agrees"] is True


def test_build_invariance_section_single_model_per_benchmark_is_insufficient_samples(tmp_path):
    # Constant within every benchmark, but each benchmark is only ever observed on one CPU
    # model (even though two models exist overall, each confined to a different benchmark).
    r1 = _multi_bench_record(tmp_path, "a.json", "1", "Model A", {"fifo_perf": [100] * 5})
    r2 = _multi_bench_record(tmp_path, "b.json", "2", "Model B", {"stream_bridge_perf": [100] * 5})

    section = perf_campaign_report.build_invariance_section([r1, r2])
    entry = section["metrics"]["transaction_lock_acquisitions"]

    assert entry["verdict"] == perf_campaign_report.INSUFFICIENT_SAMPLES
    assert entry["binding_tier"] == perf_campaign_report.NOT_YET_DETERMINED
    assert entry["per_benchmark"]["fifo_perf"]["comparable"] is False
    assert entry["per_benchmark"]["stream_bridge_perf"]["comparable"] is False


def test_build_invariance_section_names_the_disagreeing_benchmark_and_the_agreeing_one(tmp_path):
    r1 = _multi_bench_record(
        tmp_path, "a.json", "1", "Model A",
        {"fifo_perf": [100] * 5, "stream_bridge_perf": [200] * 5},
    )
    r2 = _multi_bench_record(
        tmp_path, "b.json", "2", "Model B",
        {"fifo_perf": [100] * 5, "stream_bridge_perf": [201] * 5},
    )

    section = perf_campaign_report.build_invariance_section([r1, r2])
    entry = section["metrics"]["transaction_lock_acquisitions"]

    assert entry["verdict"] == perf_campaign_report.CROSS_MODEL_VERDICT_DEMOTED
    assert entry["per_benchmark"]["fifo_perf"]["agrees"] is True
    assert entry["per_benchmark"]["stream_bridge_perf"]["agrees"] is False
    assert entry["minimum"] == 200
    assert entry["maximum"] == 201


def test_build_invariance_section_evaluates_invariant_metric_regardless_of_demoted_candidate_tier(tmp_path):
    # Every one of the nine metrics this plan promotes carries `tier_candidate: 2` on every
    # committed record, because the registry was already demoted when the population was
    # measured. The eligibility test must key off the registry's own `direction`, not the
    # recorded candidate tier, or the corrected grouping is never reached for any of them.
    r1 = _multi_bench_record(
        tmp_path, "a.json", "1", "Model A", {"fifo_perf": [2000] * 5}, tier_candidate=2,
    )
    r2 = _multi_bench_record(
        tmp_path, "b.json", "2", "Model B", {"fifo_perf": [2000] * 5}, tier_candidate=2,
    )

    section = perf_campaign_report.build_invariance_section([r1, r2])
    entry = section["metrics"]["transaction_lock_acquisitions"]

    assert entry["verdict"] == perf_campaign_report.CROSS_MODEL_VERDICT_BIT_IDENTICAL
    assert entry["binding_tier"] == perf_campaign_report.perf_tier_registry.TIER_1

    # The recorded candidate tier is never overwritten by the computed binding tier: it is
    # still reported, unchanged, in build_metric_section's own field.
    tier_candidates = perf_campaign_report._collect_metric_tier_candidates(
        [r1, r2], "transaction_lock_acquisitions",
    )
    assert tier_candidates == [2, 2]


def test_build_invariance_section_within_run_demotion_overrides_multi_benchmark_agreement(tmp_path):
    r1 = _multi_bench_record(
        tmp_path, "a.json", "1", "Model A",
        {"fifo_perf": [2000] * 5, "stream_bridge_perf": [2000] * 5},
        extra_metric_fields={
            "fifo_perf": {"tier_demoted_to": 2, "min": 1999, "max": 2000, "spread": 1},
        },
    )
    r2 = _multi_bench_record(
        tmp_path, "b.json", "2", "Model B",
        {"fifo_perf": [2000] * 5, "stream_bridge_perf": [2000] * 5},
    )

    section = perf_campaign_report.build_invariance_section([r1, r2])
    entry = section["metrics"]["transaction_lock_acquisitions"]

    assert entry["verdict"] == perf_campaign_report.CROSS_MODEL_VERDICT_WITHIN_RUN_DEMOTED
    assert entry["binding_tier"] == perf_campaign_report.perf_tier_registry.TIER_2
    assert entry["within_run_demotions"]


def test_build_invariance_section_per_benchmark_breakdown_is_sorted(tmp_path):
    r1 = _multi_bench_record(
        tmp_path, "a.json", "1", "Zeta Model",
        {"stream_bridge_perf": [2000] * 5, "fifo_perf": [2000] * 5},
    )
    r2 = _multi_bench_record(
        tmp_path, "b.json", "2", "Alpha Model",
        {"stream_bridge_perf": [2000] * 5, "fifo_perf": [2000] * 5},
    )

    section = perf_campaign_report.build_invariance_section([r1, r2])
    entry = section["metrics"]["transaction_lock_acquisitions"]

    assert list(entry["per_benchmark"]) == ["fifo_perf", "stream_bridge_perf"]
    for cell in entry["per_benchmark"].values():
        assert list(cell["per_model"]) == ["Alpha Model", "Zeta Model"]
        assert cell["cpu_models"] == ["Alpha Model", "Zeta Model"]


# --- Task 07-3: calibration flattening, contamination, and the reproduce contract -------


def _cpu_metric_record(
    root, filename, run_id, cpu_model, base_metric, raw_values, component_medians,
    injected_load="false",
):
    components = {
        name: {"median": median, "samples": [median] * 3, "repeats": 3, "unit": "u"}
        for name, median in component_medians.items()
    }
    benchmarks = {
        "remoteSetRate": {
            "metrics": {
                base_metric: {
                    "samples": raw_values,
                    "median": statistics.median(raw_values),
                    "mad": 0.0,
                    "n_clean": len(raw_values),
                    "tier_candidate": 2,
                    "status": "ok",
                    "reason": None,
                },
            },
            "workload": {},
        },
    }
    run = {
        "github_run_id": run_id,
        "github_run_attempt": "1",
        "git_sha": "abc123",
        "git_tree_hash": "expected",
        "campaign_branch": "perf-harness/campaign",
        "dispatch_index": "1",
        "injected_load": injected_load,
    }
    environment = {
        "cpu_model": cpu_model,
        "calibration_vector": {"components": components},
    }
    path = _write_harness_run(
        root, filename, run=run, benchmarks=benchmarks, environment=environment,
    )
    record = perf_campaign_report.load_harness_run(path)
    record["_run_id"] = path.stem
    return record


def test_build_flattening_section_records_a_qualifying_pairing(tmp_path):
    records = []
    # Host A: raw ~100, tsc median 1000 (scales with the raw metric's host difference);
    # alu/memcpy/syscall held constant across hosts so only tsc can flatten.
    for i, value in enumerate([100.0, 102.0, 98.0, 101.0, 99.0]):
        records.append(_cpu_metric_record(
            tmp_path, f"a{i}.json", f"a{i}", "Model A", "cpu_process_ns_per_byte", [value],
            {"alu": 500.0, "memcpy": 500.0, "syscall": 500.0, "tsc": 1000.0},
        ))
    # Host B: raw ~200, tsc median 2000 (same ratio as host A, so dividing by tsc flattens
    # the across-host difference); alu/memcpy/syscall still constant and host-insensitive.
    for i, value in enumerate([200.0, 204.0, 196.0, 202.0, 198.0]):
        records.append(_cpu_metric_record(
            tmp_path, f"b{i}.json", f"b{i}", "Model B", "cpu_process_ns_per_byte", [value],
            {"alu": 500.0, "memcpy": 500.0, "syscall": 500.0, "tsc": 2000.0},
        ))

    section = perf_campaign_report.build_flattening_section(records, min_n=2)
    entry = section["metrics"]["cpu_process_ns_per_byte"]

    assert entry["chosen_pairing"] == "tsc"
    assert entry["non_gating"] is False
    assert entry["pairings"]["tsc"]["qualifies"] is True


def test_build_flattening_section_records_no_qualifying_pairing_as_the_finding(tmp_path):
    records = []
    for i, value in enumerate([100.0, 102.0, 98.0, 101.0, 99.0]):
        records.append(_cpu_metric_record(
            tmp_path, f"a{i}.json", f"a{i}", "Model A", "cpu_process_ns_per_byte", [value],
            {"alu": 500.0, "memcpy": 500.0, "syscall": 500.0, "tsc": 500.0},
        ))
    for i, value in enumerate([200.0, 204.0, 196.0, 202.0, 198.0]):
        records.append(_cpu_metric_record(
            tmp_path, f"b{i}.json", f"b{i}", "Model B", "cpu_process_ns_per_byte", [value],
            {"alu": 500.0, "memcpy": 500.0, "syscall": 500.0, "tsc": 500.0},
        ))

    section = perf_campaign_report.build_flattening_section(records, min_n=2)
    entry = section["metrics"]["cpu_process_ns_per_byte"]

    assert entry["chosen_pairing"] is None
    assert entry["non_gating"] is True
    assert "stratification" in entry["note"]


def test_build_flattening_section_single_model_suppresses_via_dispersion_branch(tmp_path):
    records = [
        _cpu_metric_record(
            tmp_path, f"a{i}.json", f"a{i}", "Model A", "cpu_process_ns_per_byte", [value],
            {"alu": 500.0, "memcpy": 500.0, "syscall": 500.0, "tsc": 1000.0},
        )
        for i, value in enumerate([100.0, 102.0, 98.0])
    ]

    section = perf_campaign_report.build_flattening_section(records, min_n=1)
    entry = section["metrics"]["cpu_process_ns_per_byte"]["pairings"]["tsc"]

    assert entry["raw_across"]["cv"] == perf_campaign_report.INSUFFICIENT_SAMPLES


def test_flattening_table_renders_a_non_qualifying_pairing_as_the_absent_value_token(tmp_path):
    records = []
    # Host A/B pair whose tsc pairing qualifies for cpu_process_ns_per_byte (same setup
    # as test_build_flattening_section_records_a_qualifying_pairing); every other
    # DUAL_CLOCK_METRIC_NAMES base metric carries no sample at all, so it has no
    # qualifying pairing either.
    for i, value in enumerate([100.0, 102.0, 98.0, 101.0, 99.0]):
        records.append(_cpu_metric_record(
            tmp_path, f"a{i}.json", f"a{i}", "Model A", "cpu_process_ns_per_byte", [value],
            {"alu": 500.0, "memcpy": 500.0, "syscall": 500.0, "tsc": 1000.0},
        ))
    for i, value in enumerate([200.0, 204.0, 196.0, 202.0, 198.0]):
        records.append(_cpu_metric_record(
            tmp_path, f"b{i}.json", f"b{i}", "Model B", "cpu_process_ns_per_byte", [value],
            {"alu": 500.0, "memcpy": 500.0, "syscall": 500.0, "tsc": 2000.0},
        ))

    population = {
        "accepted": records, "records_skipped": 0, "skipped_reasons": [],
        "records_rejected": 0, "rejected_reasons": [],
    }
    sidecar = perf_campaign_report.build_sidecar(
        population=population, min_n=2, expected_tree_hash="expected", runs_dir=str(tmp_path),
    )
    markdown = perf_campaign_report.render_markdown(sidecar)

    flattening = sidecar["flattening"]["metrics"]
    qualifying_base = next(b for b, e in flattening.items() if e["chosen_pairing"] is not None)
    non_qualifying_base = next(b for b, e in flattening.items() if e["chosen_pairing"] is None)

    absent_token = perf_campaign_report._cell(None)
    non_gating_true_token = perf_campaign_report._cell(True)
    non_gating_false_token = perf_campaign_report._cell(False)

    # Isolate the flattening summary table (header "Base metric | Chosen pairing |
    # Non-gating") from every other table in the document, since the per-base-metric
    # detail sections below it repeat the same base metric names as headings.
    lines = markdown.splitlines()
    header_index = lines.index("| Base metric | Chosen pairing | Non-gating |")
    summary_rows = []
    for line in lines[header_index + 2:]:
        if not line.startswith("|"):
            break
        summary_rows.append(line)

    non_qual_lines = [line for line in summary_rows if line.startswith(f"| {non_qualifying_base} |")]
    assert len(non_qual_lines) == 1
    assert non_qual_lines[0] == f"| {non_qualifying_base} | {absent_token} | {non_gating_true_token} |"

    qual_lines = [line for line in summary_rows if line.startswith(f"| {qualifying_base} |")]
    assert len(qual_lines) == 1
    chosen_component = flattening[qualifying_base]["chosen_pairing"]
    assert qual_lines[0] == f"| {qualifying_base} | {chosen_component} | {non_gating_false_token} |"

    # No cell anywhere in the document is the raw Python singleton's own str() output,
    # derived from the singleton itself so this assertion cannot be satisfied by a
    # paraphrase.
    forbidden = str(None)
    for line in markdown.splitlines():
        if not line.startswith("|"):
            continue
        for cell in line.split("|"):
            assert cell.strip() != forbidden


def test_build_contamination_section_reports_rejected_and_inconclusive_per_run(tmp_path):
    benchmarks = {
        "remoteSetRate": {
            "metrics": {
                "cpu_process_ns_per_byte": {
                    "samples": [10.0, 11.0],
                    "median": 10.5,
                    "mad": 0.5,
                    "n_clean": 2,
                    "tier_candidate": 2,
                    "status": "inconclusive",
                    "reason": "guard-exceeded",
                    "rejected_samples": [
                        {"index": 2, "value": 999.0, "reason": "mad-band"},
                    ],
                },
            },
            "workload": {},
        },
    }
    path = _write_harness_run(tmp_path, "good.json", benchmarks=benchmarks)
    record = perf_campaign_report.load_harness_run(path)
    record["_run_id"] = "good"

    section = perf_campaign_report.build_contamination_section([record])
    run_entry = section["runs"]["good"]

    assert run_entry["rejected_sample_count"] == 1
    assert run_entry["rejected_reasons"] == {"mad-band": 1}
    assert run_entry["inconclusive_metric_count"] == 1
    assert run_entry["inconclusive_reasons"] == {"guard-exceeded": 1}


def test_build_contamination_section_quotes_harness_threshold_derivations(tmp_path):
    path = _write_harness_run(tmp_path, "good.json")
    record = perf_campaign_report.load_harness_run(path)
    record["_run_id"] = "good"

    section = perf_campaign_report.build_contamination_section([record])

    assert section["thresholds"]["mad_band_derivation"] == perf_campaign_report._perf_harness.MAD_BAND_DERIVATION
    assert (
        section["thresholds"]["steal_derivation"]
        == perf_campaign_report._perf_harness.STEAL_DELTA_THRESHOLD_DERIVATION
    )


def test_build_contamination_section_marks_injected_demonstration_run(tmp_path):
    path = _write_harness_run(
        tmp_path, "injected.json",
        run={
            "github_run_id": "9", "github_run_attempt": "1", "git_sha": "abc123",
            "git_tree_hash": "expected", "campaign_branch": "perf-harness/campaign",
            "dispatch_index": "9", "injected_load": "true",
        },
    )
    record = perf_campaign_report.load_harness_run(path)
    record["_run_id"] = "injected"

    section = perf_campaign_report.build_contamination_section([record])

    assert section["runs"]["injected"]["is_injected_demonstration"] is True


def test_is_injected_load_run_reads_the_run_field():
    assert perf_campaign_report.is_injected_load_run({"run": {"injected_load": "true"}}) is True
    assert perf_campaign_report.is_injected_load_run({"run": {"injected_load": "false"}}) is False
    assert perf_campaign_report.is_injected_load_run({"run": {}}) is False


def test_build_sidecar_excludes_injected_demonstration_run_from_metrics(tmp_path):
    clean = _tier1_record(tmp_path, "clean.json", "1", "Model A", [2000] * 5)
    injected_path = _write_harness_run(
        tmp_path, "injected.json",
        run={
            "github_run_id": "9", "github_run_attempt": "1", "git_sha": "abc123",
            "git_tree_hash": "expected", "campaign_branch": "perf-harness/campaign",
            "dispatch_index": "9", "injected_load": "true",
        },
        benchmarks={
            "remoteSetRate": {
                "metrics": {
                    "transaction_lock_acquisitions": {
                        "samples": [9999] * 5,
                        "median": 9999.0,
                        "mad": 0.0,
                        "n_clean": 5,
                        "tier_candidate": 1,
                        "status": "ok",
                        "reason": None,
                    },
                },
                "workload": {},
            },
        },
        environment={"cpu_model": "Model A"},
    )
    injected = perf_campaign_report.load_harness_run(injected_path)
    injected["_run_id"] = "injected"

    population = {
        "accepted": [clean, injected], "records_skipped": 0, "skipped_reasons": [],
        "records_rejected": 0, "rejected_reasons": [],
    }
    sidecar = perf_campaign_report.build_sidecar(
        population=population, min_n=3, expected_tree_hash="expected", runs_dir=str(tmp_path),
    )

    # The injected run's 9999 value must not pollute the clean metric's dispersion.
    assert sidecar["metrics"]["transaction_lock_acquisitions"]["maximum"] == 2000
    assert sidecar["source"]["records_injected_demonstration"] == 1
    assert sidecar["source"]["record_count_clean"] == 1
    assert "injected" in sidecar["contamination"]["runs"]
    assert sidecar["contamination"]["runs"]["injected"]["is_injected_demonstration"] is True


def test_build_source_coverage_section_carries_registry_note_for_uncovered_families(tmp_path):
    coverage = perf_campaign_report.build_source_coverage_section([])
    family = coverage["bytes_on_wire"]
    assert family["registry_note"] == perf_campaign_report.perf_tier_registry.UNCOVERED_FAMILIES["bytes_on_wire"]


def test_main_neither_output_contains_a_wall_clock_timestamp(tmp_path):
    import re

    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    _write_harness_run(runs_dir, "good.json")
    out_md = tmp_path / "out.md"
    out_json = tmp_path / "out.json"

    perf_campaign_report.main(
        ["--runs-dir", str(runs_dir), "--out-md", str(out_md), "--out-json", str(out_json)]
    )

    timestamp_re = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")
    assert timestamp_re.search(out_md.read_text(encoding="utf-8")) is None
    assert timestamp_re.search(out_json.read_text(encoding="utf-8")) is None


def test_main_writes_sidecar_version(tmp_path):
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    _write_harness_run(runs_dir, "good.json")
    out_md = tmp_path / "out.md"
    out_json = tmp_path / "out.json"

    exit_code = perf_campaign_report.main(
        ["--runs-dir", str(runs_dir), "--out-md", str(out_md), "--out-json", str(out_json)]
    )

    assert exit_code == 0
    sidecar = json.loads(out_json.read_text(encoding="utf-8"))
    assert sidecar["sidecar_version"] == 1


# --- canonical reproduce command: executed for real, not paraphrased -------


def test_reproduce_command_includes_expected_tree_hash_argument():
    assert "--expected-tree-hash" in perf_campaign_report.CANONICAL_COMMAND


def test_canonical_command_reproduces_committed_report_byte_identically(tmp_path):
    argv = shlex.split(perf_campaign_report.CANONICAL_COMMAND)

    # The interpreter token is asserted before substitution so a future edit
    # that changes CANONICAL_COMMAND to invoke something other than a python
    # interpreter is caught here rather than silently substituted away.
    assert argv[0].startswith("python")
    assert argv[1] == "scripts/perf_campaign_report.py"

    out_md_index = argv.index("--out-md") + 1
    out_json_index = argv.index("--out-json") + 1
    # Assert the published output paths target the committed artifacts before
    # anything is redirected, so the redirection below cannot mask a command
    # that points at the wrong files.
    assert argv[out_md_index] == perf_campaign_report.DEFAULT_OUT_MD
    assert argv[out_json_index] == perf_campaign_report.DEFAULT_OUT_JSON

    scratch_md = tmp_path / "regen.md"
    scratch_json = tmp_path / "regen.json"
    argv[0] = sys.executable
    argv[out_md_index] = str(scratch_md)
    argv[out_json_index] = str(scratch_json)

    result = subprocess.run(argv, cwd=REPO_ROOT, capture_output=True, text=True)

    assert result.returncode == 0, result.stderr

    committed_md = (REPO_ROOT / perf_campaign_report.DEFAULT_OUT_MD).read_bytes()
    committed_json = (REPO_ROOT / perf_campaign_report.DEFAULT_OUT_JSON).read_bytes()
    assert scratch_md.read_bytes() == committed_md
    assert scratch_json.read_bytes() == committed_json
