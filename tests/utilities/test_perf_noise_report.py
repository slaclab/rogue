# ----------------------------------------------------------------------------
# Title      : Performance Noise Floor Report Tests
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

import importlib
import json
import math
import re
import statistics
import sys
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

perf_noise_report = importlib.import_module("perf_noise_report")


def _write_history_json(
    root: Path,
    ref_name: str,
    sha: str,
    benchmarks: list[dict],
    published_at: str = "2026-01-01T00:00:00Z",
) -> Path:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "_", ref_name.strip()) or "unknown"
    target_dir = root / "perf" / "branches" / slug / "history"
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / f"{sha}.json"
    payload = {
        "schema_version": 1,
        "ref_name": ref_name,
        "ref_slug": slug,
        "sha": sha,
        "short_sha": sha[:7],
        "run_id": "1",
        "run_url": "",
        "published_at": published_at,
        "benchmarks": benchmarks,
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def _write_history_bytes(root: Path, ref_name: str, sha: str, raw_bytes: bytes) -> Path:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "_", ref_name.strip()) or "unknown"
    target_dir = root / "perf" / "branches" / slug / "history"
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / f"{sha}.json"
    path.write_bytes(raw_bytes)
    return path


def _synthetic_record(ref_name, sha, published_at, raw, series="sample_metric", path="synthetic"):
    return {
        "ref_name": ref_name,
        "sha": sha,
        "published_at": published_at,
        "_path": path,
        "benchmarks": [{"name": series, "primary_metric": None, "raw": raw}],
    }


def _synthetic_sidecar():
    return {
        "sidecar_version": 1,
        "source": {
            "gh_pages_commit": "deadbeef",
            "record_count": 2,
            "records_skipped": 0,
            "timestamps_unparsable": 0,
            "unparsable_record_shas": [],
            "published_at_span": {"earliest": "2026-01-01T00:00:00Z", "latest": "2026-01-02T00:00:00Z"},
        },
        "parameters": {"min_n": 5, "mde_z": 1.96, "mde_gate_pct": 2.0, "float_format": ".6g"},
        "metrics": {
            "sample_metric.avg_ns": {
                "series": "sample_metric",
                "field": "avg_ns",
                "field_class": "measurement",
                "n": 2,
                "median": 5.0,
                "mad": 0.5,
                "iqr": 1.0,
                "mean": 5.0,
                "stdev": 0.5,
                "cv": 0.1,
                "cv_percent": 10.0,
                "minimum": 4.0,
                "maximum": 6.0,
                "spread": 2.0,
                "spread_pct": 40.0,
                "correlations": {
                    "published_at": "insufficient-samples",
                    "host_rate_ghz": "insufficient-samples",
                    "branch_variance_share": "undefined-zero-variance",
                },
                "mde_pooled_pct": 13.859292911256333,
                "mde_within_pct": "insufficient-samples",
                "tier_recommendation": "informational",
                "tier_rule": "dispersion-too-large",
            }
        },
        "population": {
            "history_record_count": 2,
            "perf_file_count": 3,
            "per_branch_record_count": {"main": 2},
        },
        "recorded_covariates": {"key_union": ["sha"], "key_intersection": ["sha"]},
    }


def test_dispersion_stats_known_sample():
    values = [2.0, 4.0, 4.0, 4.0, 5.0, 5.0, 7.0, 9.0]
    stats = perf_noise_report.dispersion(values)

    assert stats["n"] == 8
    assert stats["median"] == 4.5
    assert stats["minimum"] == 2.0
    assert stats["maximum"] == 9.0
    assert stats["spread"] == 7.0

    expected_cv = statistics.stdev(values) / statistics.fmean(values)
    assert abs(stats["cv"] - expected_cv) < 1e-12


def test_single_sample_reports_insufficient():
    stats = perf_noise_report.dispersion([5.0])

    assert stats["n"] == 1
    assert stats["minimum"] == stats["maximum"] == 5.0
    assert stats["spread"] == 0.0
    assert stats["cv"] == perf_noise_report.INSUFFICIENT_SAMPLES


def test_zero_mean_reports_undefined():
    values = [-3.0, 1.0, 1.0, 1.0]
    stats = perf_noise_report.dispersion(values)

    assert stats["cv"] == perf_noise_report.UNDEFINED_ZERO_MEAN
    for value in stats.values():
        if isinstance(value, float):
            assert not math.isnan(value)
            assert not math.isinf(value)


def test_zero_median_reports_undefined_spread_pct():
    values = [-1.0, 0.0, 2.0]
    stats = perf_noise_report.dispersion(values)

    assert stats["median"] == 0.0
    assert stats["spread_pct"] == perf_noise_report.UNDEFINED_ZERO_MEDIAN


def test_non_finite_value_is_skipped_not_averaged():
    records = [
        _synthetic_record("main", "sha-0", "2026-01-01T00:00:00Z", {"avg_ns": 100.0}, path="p0"),
        _synthetic_record("main", "sha-1", "2026-01-02T00:00:00Z", {"avg_ns": float("nan")}, path="p1"),
    ]
    rows = perf_noise_report.flatten_records(records)

    metrics = perf_noise_report.build_field_inventory(rows, history_record_count=2, min_n=1)
    entry = metrics["sample_metric.avg_ns"]

    assert entry["n"] == 1
    assert entry["skipped_non_numeric"] == 1
    for key in ("mean", "median", "minimum", "maximum"):
        assert math.isfinite(entry[key])


def test_non_finite_record_writes_strict_json(tmp_path):
    root = tmp_path / "published"
    _write_history_json(
        root,
        ref_name="main",
        sha="sha-nan",
        benchmarks=[{"name": "sample_metric", "primary_metric": None, "raw": {"avg_ns": float("nan")}}],
        published_at="2026-01-01T00:00:00Z",
    )
    _write_history_json(
        root,
        ref_name="main",
        sha="sha-ok-0",
        benchmarks=[{"name": "sample_metric", "primary_metric": None, "raw": {"avg_ns": 100.0}}],
        published_at="2026-01-02T00:00:00Z",
    )
    _write_history_json(
        root,
        ref_name="main",
        sha="sha-ok-1",
        benchmarks=[{"name": "sample_metric", "primary_metric": None, "raw": {"avg_ns": 101.0}}],
        published_at="2026-01-03T00:00:00Z",
    )

    out_md = tmp_path / "out.md"
    out_json = tmp_path / "out.json"
    exit_code = perf_noise_report.main(
        ["--published-root", str(root), "--out-md", str(out_md), "--out-json", str(out_json)]
    )

    assert exit_code == 0
    sidecar_text = out_json.read_text(encoding="utf-8")
    assert "NaN" not in sidecar_text
    assert "Infinity" not in sidecar_text

    def _raise_on_constant(token):
        raise ValueError(f"non-standard JSON constant encountered: {token}")

    json.loads(sidecar_text, parse_constant=_raise_on_constant)


def test_non_finite_derived_rate_is_unattributed():
    record = _synthetic_record(
        "main", "sha-nan-rate", "2026-01-01T00:00:00Z",
        {"avg_ns": float("nan"), "cycles": 2.5e8},
        series="variable_rate_perf_testOp",
    )

    assert perf_noise_report.derived_rate_hz(record) is None

    rows = perf_noise_report.flatten_records([record])
    group_by_path = perf_noise_report.assign_host_groups(rows, [record])

    assert group_by_path[record["_path"]] == perf_noise_report.UNATTRIBUTED
    assert all(row["host_group"] == perf_noise_report.UNATTRIBUTED for row in rows)


def test_published_root_fallback_reads_records(tmp_path):
    root = tmp_path / "published"
    _write_history_json(
        root,
        ref_name="main",
        sha="abc1234",
        benchmarks=[{"name": "sample_metric", "primary_metric": None, "raw": {"avg_ns": 100.0}}],
    )

    out_md = tmp_path / "out.md"
    out_json = tmp_path / "out.json"
    exit_code = perf_noise_report.main(
        [
            "--published-root", str(root),
            "--out-md", str(out_md),
            "--out-json", str(out_json),
        ]
    )

    assert exit_code == 0
    assert out_md.is_file()
    assert out_json.is_file()
    payload = json.loads(out_json.read_text(encoding="utf-8"))
    assert payload["metrics"]["sample_metric.avg_ns"]["n"] == 1


def test_non_utf8_record_is_skipped_not_fatal(tmp_path):
    # Coverage is on the --published-root read path only. The git read path takes the
    # identical UnicodeDecodeError through the identical handler, but exercising it
    # would require a temporary git repository, which this suite deliberately avoids
    # so it stays build-free and git-free.
    root = tmp_path / "published"
    _write_history_json(
        root,
        ref_name="main",
        sha="sha-good",
        benchmarks=[{"name": "sample_metric", "primary_metric": None, "raw": {"avg_ns": 100.0}}],
    )
    _write_history_bytes(root, ref_name="main", sha="sha-bad-bytes", raw_bytes=b"\xff\xfe\xfd not valid utf-8")

    out_md = tmp_path / "out.md"
    out_json = tmp_path / "out.json"
    exit_code = perf_noise_report.main(
        [
            "--published-root", str(root),
            "--out-md", str(out_md),
            "--out-json", str(out_json),
        ]
    )

    assert exit_code == 0
    assert out_md.is_file()
    assert out_json.is_file()
    payload = json.loads(out_json.read_text(encoding="utf-8"))
    assert payload["source"]["records_skipped"] == 1
    assert payload["source"]["record_count"] == 1


def test_unclassified_field_is_listed_not_dropped():
    record = _synthetic_record("main", "sha-a", "2026-01-01T00:00:00Z", {"mystery_field": 42.0})

    rows = perf_noise_report.flatten_records([record])
    metrics = perf_noise_report.build_field_inventory(rows)

    entry = metrics["sample_metric.mystery_field"]
    assert entry["field_class"] == "unclassified"
    assert entry["n"] == 1


def test_output_is_deterministic():
    sidecar = _synthetic_sidecar()

    markdown_a = perf_noise_report.render_markdown(sidecar)
    markdown_b = perf_noise_report.render_markdown(sidecar)
    assert markdown_a == markdown_b

    json_a = json.dumps(sidecar, indent=2, sort_keys=True)
    json_b = json.dumps(sidecar, indent=2, sort_keys=True)
    assert json_a == json_b


def test_row_order_is_total_and_stable():
    record_a = _synthetic_record("main", "sha-a", "2026-01-02T00:00:00Z", {"avg_ns": 1.0}, path="a")
    record_b = _synthetic_record("main", "sha-b", "2026-01-01T00:00:00Z", {"avg_ns": 2.0}, path="b")

    rows_forward = perf_noise_report.flatten_records([record_a, record_b])
    rows_reverse = perf_noise_report.flatten_records([record_b, record_a])

    assert [row["sha"] for row in rows_forward] == [row["sha"] for row in rows_reverse]
    assert [row["sha"] for row in rows_forward] == ["sha-b", "sha-a"]


def test_float_format_contract():
    values = [
        100000.123456789, 100000.987654321, 100000.555555555,
        100000.222222222, 100000.888888888,
    ]
    records = [
        _synthetic_record("main", f"sha-{i}", f"2026-01-0{i + 1}T00:00:00Z", {"avg_ns": value}, path=f"p{i}")
        for i, value in enumerate(values)
    ]

    rows = perf_noise_report.flatten_records(records)
    metrics = perf_noise_report.build_field_inventory(rows)
    entry = metrics["sample_metric.avg_ns"]

    raw_stats = perf_noise_report.dispersion(values)
    for key, value in raw_stats.items():
        if isinstance(value, float):
            assert entry[key] == float(f"{value:.6g}")


def test_host_group_bucketing_merges_and_separates():
    # Both land in the same two-decimal-GHz bucket.
    assert (
        perf_noise_report.host_group_id(2.451e9)
        == perf_noise_report.host_group_id(2.454e9)
        == "tsc-2.45GHz"
    )
    # These straddle the boundary between the 2.45GHz and 2.46GHz buckets (at 2.455e9).
    below = perf_noise_report.host_group_id(2.4549e9)
    above = perf_noise_report.host_group_id(2.4551e9)
    assert below == "tsc-2.45GHz"
    assert above == "tsc-2.46GHz"
    assert below != above


def test_host_group_bucketing_is_half_up():
    # 244.5 is a half-to-even tie that Python's round() sends to 244 (the nearest even
    # integer). The half-up bucketing rule must send it to 245 instead.
    assert round(244.5) == 244
    assert perf_noise_report.host_group_id(244.5e7) == "tsc-2.45GHz"


def test_derived_rate_uses_bench_count_factor():
    # avg_ns=1000.0 (per-operation) and cycles=2.5e8 (raw whole-loop total) imply
    # elapsed_s = 1000.0 * BENCH_COUNT * 1e-9 = 0.1s, so rate_hz = cycles / elapsed_s = 2.5e9.
    record = _synthetic_record(
        "main", "sha-rate", "2026-01-01T00:00:00Z",
        {"avg_ns": 1000.0, "cycles": 2.5e8},
        series="variable_rate_perf_testOp",
    )

    rate = perf_noise_report.derived_rate_hz(record)

    assert rate is not None
    assert abs(rate - 2.5e9) < 1.0
    naive_rate = 2.5e8 / 1000.0
    assert abs(rate - naive_rate) > 1e4


def test_record_without_cycles_is_unattributed():
    record = _synthetic_record("main", "sha-nogroup", "2026-01-01T00:00:00Z", {"avg_ns": 100.0})

    assert perf_noise_report.derived_rate_hz(record) is None

    rows = perf_noise_report.flatten_records([record])
    group_by_path = perf_noise_report.assign_host_groups(rows, [record])

    assert group_by_path[record["_path"]] == perf_noise_report.UNATTRIBUTED
    assert all(row["host_group"] == perf_noise_report.UNATTRIBUTED for row in rows)

    metrics = perf_noise_report.build_field_inventory(rows, history_record_count=1, min_n=1)
    entry = metrics["sample_metric.avg_ns"]
    assert entry["n"] == 1


def test_variance_split_matches_hand_computed():
    values_by_group = {"a": [1.0, 2.0, 3.0], "b": [5.0, 7.0]}

    result = perf_noise_report.variance_split(values_by_group)

    # Hand-computed: grand_mean=3.6, ss_total=23.2, ss_between=19.2, ss_within=4.0.
    expected_eta_squared = 19.2 / 23.2
    expected_within_stdev = math.sqrt(4.0 / 3.0)
    expected_within_cv = expected_within_stdev / 3.6

    assert abs(result["eta_squared"] - expected_eta_squared) < 1e-12
    assert abs(result["within_stdev"] - expected_within_stdev) < 1e-12
    assert abs(result["within_cv"] - expected_within_cv) < 1e-12


def test_variance_split_zero_variance_marker():
    values_by_group = {"a": [5.0, 5.0], "b": [5.0]}

    result = perf_noise_report.variance_split(values_by_group)

    assert result["eta_squared"] == perf_noise_report.UNDEFINED_ZERO_VARIANCE


def test_min_n_boundary_at_and_below():
    cell_at_min = {"n": 5, "cv": 0.1, "minimum": 1.0, "maximum": 2.0}
    cell_below_min = {"n": 4, "cv": 0.1, "minimum": 1.0, "maximum": 2.0}

    at_min = perf_noise_report.suppress_below_min_n(dict(cell_at_min), min_n=5)
    below_min = perf_noise_report.suppress_below_min_n(dict(cell_below_min), min_n=5)

    assert at_min["cv"] == 0.1
    assert below_min["cv"] == perf_noise_report.INSUFFICIENT_SAMPLES
    assert below_min["n"] == 4
    assert below_min["minimum"] == 1.0
    assert below_min["maximum"] == 2.0


def test_suppression_never_removes_a_row(tmp_path):
    root = tmp_path / "published"
    for i in range(3):
        _write_history_json(
            root,
            ref_name="main",
            sha=f"sha{i}",
            benchmarks=[{"name": "sample_metric", "primary_metric": None, "raw": {"avg_ns": 100.0 + i}}],
        )

    out_md = tmp_path / "out.md"
    out_json_default = tmp_path / "out_default.json"
    out_json_strict = tmp_path / "out_strict.json"

    perf_noise_report.main(
        ["--published-root", str(root), "--out-md", str(out_md), "--out-json", str(out_json_default)]
    )
    perf_noise_report.main(
        [
            "--published-root", str(root), "--out-md", str(out_md), "--out-json", str(out_json_strict),
            "--min-n", "999",
        ]
    )

    default_metrics = json.loads(out_json_default.read_text(encoding="utf-8"))["metrics"]
    strict_metrics = json.loads(out_json_strict.read_text(encoding="utf-8"))["metrics"]
    assert set(default_metrics) == set(strict_metrics)


def test_repeated_commit_members_both_retained():
    record_main = _synthetic_record(
        "main", "shared-sha", "2026-01-01T00:00:00Z", {"avg_ns": 100.0}, path="main-path"
    )
    record_pre = _synthetic_record(
        "pre-release", "shared-sha", "2026-01-02T00:00:00Z", {"avg_ns": 120.0}, path="pre-path"
    )
    records = [record_main, record_pre]

    rows = perf_noise_report.flatten_records(records)
    perf_noise_report.assign_host_groups(rows, records)

    entries = perf_noise_report.repeated_commits(rows)

    assert len(entries) == 1
    entry = entries[0]
    assert entry["sha"] == "shared-sha"
    branches = {member["branch"] for member in entry["members"]}
    assert branches == {"main", "pre-release"}

    metrics = perf_noise_report.build_field_inventory(rows, history_record_count=2, min_n=1)
    cell = metrics["sample_metric.avg_ns"]
    assert cell["n"] == 2
    assert cell["n"] + cell["records_missing_cell"] == 2


def test_no_discard_invariant():
    records = [
        _synthetic_record("main", f"sha-{i}", f"2026-01-0{i + 1}T00:00:00Z", {"avg_ns": 100.0 + i}, path=f"p{i}")
        for i in range(4)
    ]
    records.append(_synthetic_record("main", "sha-missing", "2026-01-05T00:00:00Z", {}, path="p-missing"))

    rows = perf_noise_report.flatten_records(records)
    perf_noise_report.assign_host_groups(rows, records)
    metrics = perf_noise_report.build_field_inventory(rows, history_record_count=len(records), min_n=1)

    for entry in metrics.values():
        assert entry["n"] + entry["records_missing_cell"] == len(records)


def test_mde_formula_known_values():
    mde = perf_noise_report.provisional_mde(0.10, 25, 1.96)

    assert abs(mde - 3.92) < 1e-9


def test_mde_propagates_markers():
    marker = perf_noise_report.INSUFFICIENT_SAMPLES

    assert perf_noise_report.provisional_mde(marker, 10, 1.96) == marker
    assert perf_noise_report.provisional_mde(perf_noise_report.UNDEFINED_ZERO_MEAN, 10, 1.96) \
        == perf_noise_report.UNDEFINED_ZERO_MEAN


def test_mde_z_flag_changes_result():
    base = perf_noise_report.provisional_mde(0.10, 25, 1.96)
    doubled = perf_noise_report.provisional_mde(0.10, 25, 3.92)

    assert abs(doubled - 2 * base) < 1e-9


def test_pearson_constant_input_marker():
    xs = [1.0, 1.0, 1.0, 1.0, 1.0]
    ys = [1.0, 2.0, 3.0, 4.0, 5.0]

    result = perf_noise_report.pearson(xs, ys, min_n=1)

    assert result == perf_noise_report.UNDEFINED_CONSTANT_INPUT


def test_pearson_below_min_n_marker():
    xs = [1.0, 2.0, 3.0]
    ys = [1.0, 2.0, 3.0]

    result = perf_noise_report.pearson(xs, ys, min_n=5)

    assert result == perf_noise_report.INSUFFICIENT_SAMPLES


def test_pearson_perfect_correlation():
    xs = [1.0, 2.0, 3.0, 4.0, 5.0]
    ys_positive = [2.0, 4.0, 6.0, 8.0, 10.0]
    ys_inverse = [10.0, 8.0, 6.0, 4.0, 2.0]

    assert abs(perf_noise_report.pearson(xs, ys_positive, min_n=1) - 1.0) < 1e-9
    assert abs(perf_noise_report.pearson(xs, ys_inverse, min_n=1) - (-1.0)) < 1e-9


def test_branch_variance_share_below_min_n_is_suppressed():
    records = [
        _synthetic_record("branch-a", "sha-0", "2026-01-01T00:00:00Z", {"avg_ns": 1.0}, path="p0"),
        _synthetic_record("branch-a", "sha-1", "2026-01-02T00:00:00Z", {"avg_ns": 2.0}, path="p1"),
        _synthetic_record("branch-b", "sha-2", "2026-01-03T00:00:00Z", {"avg_ns": 10.0}, path="p2"),
        _synthetic_record("branch-b", "sha-3", "2026-01-04T00:00:00Z", {"avg_ns": 12.0}, path="p3"),
    ]
    rows = perf_noise_report.flatten_records(records)

    result = perf_noise_report.correlations(rows, "measurement", min_n=5)

    assert result["branch_variance_share"] == perf_noise_report.INSUFFICIENT_SAMPLES


def test_branch_variance_share_at_min_n_is_numeric():
    records = [
        _synthetic_record("branch-a", "sha-0", "2026-01-01T00:00:00Z", {"avg_ns": 1.0}, path="p0"),
        _synthetic_record("branch-a", "sha-1", "2026-01-02T00:00:00Z", {"avg_ns": 2.0}, path="p1"),
        _synthetic_record("branch-a", "sha-2", "2026-01-03T00:00:00Z", {"avg_ns": 3.0}, path="p2"),
        _synthetic_record("branch-b", "sha-3", "2026-01-04T00:00:00Z", {"avg_ns": 10.0}, path="p3"),
        _synthetic_record("branch-b", "sha-4", "2026-01-05T00:00:00Z", {"avg_ns": 12.0}, path="p4"),
    ]
    rows = perf_noise_report.flatten_records(records)

    result = perf_noise_report.correlations(rows, "measurement", min_n=5)

    branch_values = {"branch-a": [1.0, 2.0, 3.0], "branch-b": [10.0, 12.0]}
    expected = float(f"{perf_noise_report.variance_split(branch_values)['eta_squared']:.6g}")

    assert isinstance(result["branch_variance_share"], float)
    assert result["branch_variance_share"] == expected


def test_branch_variance_share_keeps_zero_variance_marker():
    records = [
        _synthetic_record("branch-a", "sha-0", "2026-01-01T00:00:00Z", {"avg_ns": 5.0}, path="p0"),
        _synthetic_record("branch-a", "sha-1", "2026-01-02T00:00:00Z", {"avg_ns": 5.0}, path="p1"),
        _synthetic_record("branch-b", "sha-2", "2026-01-03T00:00:00Z", {"avg_ns": 5.0}, path="p2"),
        _synthetic_record("branch-b", "sha-3", "2026-01-04T00:00:00Z", {"avg_ns": 5.0}, path="p3"),
    ]
    rows = perf_noise_report.flatten_records(records)

    result = perf_noise_report.correlations(rows, "measurement", min_n=5)

    assert result["branch_variance_share"] == perf_noise_report.UNDEFINED_ZERO_VARIANCE


def test_published_epoch_parses_and_counts_failures(tmp_path):
    epoch = perf_noise_report.published_epoch("2026-01-01T00:00:00Z")
    assert epoch is not None
    assert abs(epoch - 1767225600.0) < 1e-6

    assert perf_noise_report.published_epoch("not-a-timestamp") is None
    assert perf_noise_report.published_epoch(None) is None

    root = tmp_path / "published"
    _write_history_json(
        root,
        ref_name="main",
        sha="sha-bad-ts",
        benchmarks=[{"name": "sample_metric", "primary_metric": None, "raw": {"avg_ns": 100.0}}],
        published_at="not-a-timestamp",
    )

    out_md = tmp_path / "out.md"
    out_json = tmp_path / "out.json"
    exit_code = perf_noise_report.main(
        ["--published-root", str(root), "--out-md", str(out_md), "--out-json", str(out_json)]
    )

    assert exit_code == 0
    payload = json.loads(out_json.read_text(encoding="utf-8"))
    assert payload["source"]["timestamps_unparsable"] == 1
    assert payload["source"]["unparsable_record_shas"] == ["sha-bad-ts"]
    # The record with the unparsable timestamp still contributes to every other statistic.
    assert payload["metrics"]["sample_metric.avg_ns"]["n"] == 1


def test_tier_rule_zero_spread_is_invariant_candidate():
    recommendation, rule = perf_noise_report.tier_recommendation(
        mde_pooled=0.0, mde_within=0.0, spread=0.0, shrink_ratio=1.0,
        gate_pct=2.0, shrink_split=2.0,
    )

    assert recommendation == "invariant-candidate"
    assert rule == "zero-spread"


def test_tier_rule_host_dominated_tight_within():
    recommendation, rule = perf_noise_report.tier_recommendation(
        mde_pooled=5.0, mde_within=1.0, spread=1.0, shrink_ratio=3.0,
        gate_pct=2.0, shrink_split=2.0,
    )

    assert recommendation == "stratified-candidate"
    assert rule == "host-dominated-tight-within"


def test_tier_rule_host_insensitive_tight():
    recommendation, rule = perf_noise_report.tier_recommendation(
        mde_pooled=5.0, mde_within=1.0, spread=1.0, shrink_ratio=1.0,
        gate_pct=2.0, shrink_split=2.0,
    )

    assert recommendation == "normalization-candidate"
    assert rule == "host-insensitive-tight"


def test_tier_rule_dispersion_too_large_is_informational():
    recommendation, rule = perf_noise_report.tier_recommendation(
        mde_pooled=10.0, mde_within=5.0, spread=1.0, shrink_ratio=1.0,
        gate_pct=2.0, shrink_split=2.0,
    )

    assert recommendation == "informational"
    assert rule == "dispersion-too-large"


def test_tier_rule_below_minimum_n_takes_priority_over_zero_spread():
    recommendation, rule = perf_noise_report.tier_recommendation(
        mde_pooled=perf_noise_report.INSUFFICIENT_SAMPLES,
        mde_within=perf_noise_report.INSUFFICIENT_SAMPLES,
        spread=0.0, shrink_ratio=1.0,
        gate_pct=2.0, shrink_split=2.0,
    )

    assert recommendation == perf_noise_report.INSUFFICIENT_SAMPLES
    assert rule == "below-minimum-n"


def test_every_recommendation_carries_a_rule_name(tmp_path):
    root = tmp_path / "published"
    for i in range(6):
        _write_history_json(
            root,
            ref_name="main",
            sha=f"sha{i}",
            benchmarks=[
                {
                    "name": "sample_metric",
                    "primary_metric": None,
                    "raw": {"avg_ns": 100.0 + (i % 3)},
                }
            ],
        )

    out_md = tmp_path / "out.md"
    out_json = tmp_path / "out.json"
    perf_noise_report.main(
        [
            "--published-root", str(root), "--out-md", str(out_md), "--out-json", str(out_json),
            "--min-n", "1",
        ]
    )

    payload = json.loads(out_json.read_text(encoding="utf-8"))
    recommendation_names = {
        "insufficient-samples", "invariant-candidate", "stratified-candidate",
        "normalization-candidate", "informational",
    }
    rule_names = {
        "below-minimum-n", "zero-spread", "host-dominated-tight-within",
        "host-insensitive-tight", "dispersion-too-large",
    }
    for metric_key, entry in payload["metrics"].items():
        assert entry.get("tier_rule") in rule_names, (metric_key, entry.get("tier_rule"))
        assert entry.get("tier_recommendation") in recommendation_names, \
            (metric_key, entry.get("tier_recommendation"))
