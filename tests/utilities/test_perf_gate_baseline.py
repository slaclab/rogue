# ----------------------------------------------------------------------------
# Title      : Perf Gate Baseline Tests
# ----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
# ----------------------------------------------------------------------------

"""Unit tests for scripts/perf_gate_baseline.py, following
tests/utilities/test_perf_campaign_report.py's fixture style: every test
below is injectable and needs no Rogue build. Fixtures use small hand-built
records (2 to 4 entries) rather than the real 25-record population, except
for the canonical-command test, which regenerates and compares against the
real committed artifacts.
"""

from __future__ import annotations

import importlib
import json
import re
import shlex
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

perf_gate_baseline = importlib.import_module("perf_gate_baseline")
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


def _metric_entry(samples: list[float]) -> dict:
    return {
        "samples": samples,
        "median": float(samples[len(samples) // 2]),
        "mad": 0.0,
        "n_clean": len(samples),
        "tier_candidate": 2,
        "status": "ok",
        "reason": None,
    }


def _record(root: Path, filename: str, cpu_model: str, benchmarks: dict, run: dict | None = None) -> dict:
    default_run = {
        "github_run_id": filename,
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
        root, filename, run=default_run, benchmarks=benchmarks, environment={"cpu_model": cpu_model},
    )
    record = perf_campaign_report.load_harness_run(path)
    record["_run_id"] = path.stem
    return record


# --- gate_rule_for_metric / build_cells admission behaviour -----------------


def test_metric_constant_across_two_cpu_models_admits_exact_equality(tmp_path):
    benchmarks = {"remoteSetRate": {"metrics": {"transaction_lock_acquisitions": _metric_entry([2000] * 5)}}}
    record_a = _record(tmp_path, "a.json", "Model A", benchmarks)
    record_b = _record(tmp_path, "b.json", "Model B", benchmarks)

    cells = perf_gate_baseline.build_cells([record_a, record_b], min_n=5)

    cell = cells["remoteSetRate"]["transaction_lock_acquisitions"]
    assert cell["status"] == perf_gate_baseline.CELL_MEASURED
    assert cell["gate_rule"] == perf_gate_baseline.GATE_RULE_EXACT_EQUALITY
    assert cell["observed_value"] == 2000.0
    assert cell["cpu_models"] == ["Model A", "Model B"]


def test_one_sample_changed_makes_the_metric_non_gating_and_every_benchmark_agrees(tmp_path):
    benchmarks_a = {"remoteSetRate": {"metrics": {"transaction_lock_acquisitions": _metric_entry([2000] * 5)}}}
    benchmarks_b = {
        "remoteSetRate": {"metrics": {"transaction_lock_acquisitions": _metric_entry([2000, 2000, 2000, 2000, 2001])}},
    }
    record_a = _record(tmp_path, "a.json", "Model A", benchmarks_a)
    record_b = _record(tmp_path, "b.json", "Model B", benchmarks_b)

    cells = perf_gate_baseline.build_cells([record_a, record_b], min_n=5)

    remote_cell = cells["remoteSetRate"]["transaction_lock_acquisitions"]
    assert remote_cell["gate_rule"] == perf_gate_baseline.GATE_RULE_NON_GATING
    assert remote_cell["non_gating_reason"] == perf_gate_baseline.NON_GATING_VARIES

    # Admission is decided per metric, over every one of its own cells together: a
    # benchmark that never measured this metric at all still agrees it is non-gating.
    other_cell = cells["linkedGetRate"]["transaction_lock_acquisitions"]
    assert other_cell["gate_rule"] == perf_gate_baseline.GATE_RULE_NON_GATING
    assert other_cell["non_gating_reason"] == perf_gate_baseline.NON_GATING_VARIES


def test_metric_constant_on_one_benchmark_and_varying_on_another_is_non_gating(tmp_path):
    benchmarks = {
        "remoteSetRate": {"metrics": {"transaction_lock_acquisitions": _metric_entry([2000] * 5)}},
        "linkedGetRate": {"metrics": {"transaction_lock_acquisitions": _metric_entry([3000, 3000, 3000, 3000, 3001])}},
    }
    record_a = _record(tmp_path, "a.json", "Model A", benchmarks)
    record_b = _record(tmp_path, "b.json", "Model B", benchmarks)

    cells = perf_gate_baseline.build_cells([record_a, record_b], min_n=5)

    # remoteSetRate's own cell is individually constant, but the metric as a whole must
    # not gate just because this one benchmark looks stable: this is the exact pooling
    # failure mode the per-metric admission rule exists to prevent.
    remote_cell = cells["remoteSetRate"]["transaction_lock_acquisitions"]
    assert remote_cell["minimum"] == remote_cell["maximum"]
    assert remote_cell["gate_rule"] == perf_gate_baseline.GATE_RULE_NON_GATING
    assert remote_cell["non_gating_reason"] == perf_gate_baseline.NON_GATING_VARIES


def test_metric_observed_on_exactly_one_cpu_model_is_non_gating(tmp_path):
    benchmarks = {"remoteSetRate": {"metrics": {"transaction_lock_acquisitions": _metric_entry([2000] * 5)}}}
    record_a = _record(tmp_path, "a.json", "Model A", benchmarks)
    record_b = _record(tmp_path, "b.json", "Model A", benchmarks)

    cells = perf_gate_baseline.build_cells([record_a, record_b], min_n=5)

    cell = cells["remoteSetRate"]["transaction_lock_acquisitions"]
    assert cell["minimum"] == cell["maximum"]
    assert cell["gate_rule"] == perf_gate_baseline.GATE_RULE_NON_GATING
    assert cell["non_gating_reason"] == perf_gate_baseline.NON_GATING_ONE_MODEL


def test_gating_metric_with_an_unmeasured_sibling_benchmark_does_not_stamp_that_cell_gating(tmp_path):
    # transaction_lock_acquisitions is only measured on remoteSetRate here; the metric
    # still gates (one measured, constant, multi-model cell), but a sibling benchmark
    # this fixture never measured must not inherit exact-equality without an
    # observed_value to back it.
    benchmarks = {"remoteSetRate": {"metrics": {"transaction_lock_acquisitions": _metric_entry([2000] * 5)}}}
    record_a = _record(tmp_path, "a.json", "Model A", benchmarks)
    record_b = _record(tmp_path, "b.json", "Model B", benchmarks)

    cells = perf_gate_baseline.build_cells([record_a, record_b], min_n=5)

    gating_cell = cells["remoteSetRate"]["transaction_lock_acquisitions"]
    assert gating_cell["gate_rule"] == perf_gate_baseline.GATE_RULE_EXACT_EQUALITY

    unmeasured_cell = cells["linkedGetRate"]["transaction_lock_acquisitions"]
    assert unmeasured_cell["status"] == perf_gate_baseline.CELL_NO_SAMPLES
    assert unmeasured_cell["gate_rule"] == perf_gate_baseline.GATE_RULE_NON_GATING
    assert "observed_value" not in unmeasured_cell
    assert unmeasured_cell["derivation"]
    # A cell whose metric gates but which was itself never measured still carries its tier:
    # the tier is display information beside the gate rule, stamped regardless of status.
    import perf_tier_registry
    expected_tier = perf_tier_registry.METRICS["transaction_lock_acquisitions"]["tier"]
    assert unmeasured_cell["tier"] == expected_tier
    assert gating_cell["tier"] == expected_tier


# --- sentinel cells ----------------------------------------------------------


def test_zero_sample_pair_yields_no_samples_and_is_present(tmp_path):
    cells = perf_gate_baseline.build_cells([], min_n=5)

    cell = cells["fifo_perf"]["core_drop_count"]
    assert cell["status"] == perf_gate_baseline.CELL_NO_SAMPLES
    assert cell["n"] == 0
    for key in ("median", "mad", "cv", "minimum", "maximum", "observed_value", "mde_two_sample_pct", "cpu_models"):
        assert key not in cell


def test_below_min_n_is_insufficient_and_at_min_n_is_measured(tmp_path):
    benchmarks_below = {"remoteSetRate": {"metrics": {"transaction_lock_acquisitions": _metric_entry([2000])}}}
    record_below = _record(tmp_path, "below.json", "Model A", benchmarks_below)
    cells_below = perf_gate_baseline.build_cells([record_below], min_n=5)
    cell_below = cells_below["remoteSetRate"]["transaction_lock_acquisitions"]
    assert cell_below["status"] == perf_gate_baseline.CELL_INSUFFICIENT_SAMPLES
    assert cell_below["n"] == 1
    for key in ("median", "mad", "cv", "minimum", "maximum", "observed_value", "mde_two_sample_pct", "cpu_models"):
        assert key not in cell_below

    benchmarks_at = {"remoteSetRate": {"metrics": {"transaction_lock_acquisitions": _metric_entry([2000] * 5)}}}
    record_at = _record(tmp_path, "at.json", "Model A", benchmarks_at)
    cells_at = perf_gate_baseline.build_cells([record_at], min_n=5)
    cell_at = cells_at["remoteSetRate"]["transaction_lock_acquisitions"]
    assert cell_at["status"] == perf_gate_baseline.CELL_MEASURED
    assert cell_at["n"] == 5
    assert cell_at["median"] == 2000.0


# --- tier stamped from the live registry at generation time ------------------


def test_every_cell_carries_the_tier_the_registry_descriptor_itself_records(tmp_path):
    benchmarks = {
        "remoteSetRate": {"metrics": {"transaction_lock_acquisitions": _metric_entry([2000] * 5)}},
        "fifo_perf": {"metrics": {"core_drop_count": _metric_entry([0] * 5)}},
    }
    record_a = _record(tmp_path, "a.json", "Model A", benchmarks)
    record_b = _record(tmp_path, "b.json", "Model B", benchmarks)

    cells = perf_gate_baseline.build_cells([record_a, record_b], min_n=5)

    import perf_tier_registry
    for metric in ("transaction_lock_acquisitions", "core_drop_count"):
        expected_tier = perf_tier_registry.METRICS[metric]["tier"]
        for benchmark in perf_tier_registry.METRICS[metric]["benchmarks"]:
            assert cells[benchmark][metric]["tier"] == expected_tier


def test_a_descriptor_with_no_tier_value_yields_a_null_tier(tmp_path):
    benchmarks = {"remoteSetRate": {"metrics": {"transaction_lock_acquisitions": _metric_entry([2000] * 5)}}}
    record_a = _record(tmp_path, "a.json", "Model A", benchmarks)
    record_b = _record(tmp_path, "b.json", "Model B", benchmarks)

    import perf_tier_registry
    original_tier = perf_tier_registry.METRICS["transaction_lock_acquisitions"].pop("tier")
    try:
        cells = perf_gate_baseline.build_cells([record_a, record_b], min_n=5)
    finally:
        perf_tier_registry.METRICS["transaction_lock_acquisitions"]["tier"] = original_tier

    cell = cells["remoteSetRate"]["transaction_lock_acquisitions"]
    assert cell["tier"] is None
    # A guessed integer would be worse than an honest null.
    assert not isinstance(cell["tier"], int)


def test_tier_field_tracks_the_live_registry_at_generation_time_and_moves_no_other_key(tmp_path):
    benchmarks = {"remoteSetRate": {"metrics": {"transaction_lock_acquisitions": _metric_entry([2000] * 5)}}}
    record_a = _record(tmp_path, "a.json", "Model A", benchmarks)
    record_b = _record(tmp_path, "b.json", "Model B", benchmarks)
    population = {
        "accepted": [record_a, record_b], "records_skipped": 0, "skipped_reasons": [],
        "records_rejected": 0, "rejected_reasons": [],
    }

    sidecar_before = perf_gate_baseline.build_sidecar(
        population=population, min_n=5, expected_tree_hash="expected", runs_dir=str(tmp_path),
    )
    cell_before = dict(sidecar_before["cells"]["remoteSetRate"]["transaction_lock_acquisitions"])

    import perf_tier_registry
    original_tier = perf_tier_registry.METRICS["transaction_lock_acquisitions"]["tier"]
    changed_tier = original_tier + 1 if original_tier < perf_tier_registry.TIER_3 else original_tier - 1
    try:
        perf_tier_registry.METRICS["transaction_lock_acquisitions"]["tier"] = changed_tier
        sidecar_after = perf_gate_baseline.build_sidecar(
            population=population, min_n=5, expected_tree_hash="expected", runs_dir=str(tmp_path),
        )
    finally:
        perf_tier_registry.METRICS["transaction_lock_acquisitions"]["tier"] = original_tier
    cell_after = dict(sidecar_after["cells"]["remoteSetRate"]["transaction_lock_acquisitions"])

    # The tier is baked in from whatever the registry reports at generation time: a
    # regeneration against a re-bound registry carries the newly bound tier, not the value
    # frozen into a previously generated artifact.
    assert cell_before["tier"] == original_tier
    assert cell_after["tier"] == changed_tier
    # Nothing else about the cell moves: the tier is display information beside gate_rule,
    # never an input to it.
    for key in cell_before:
        if key == "tier":
            continue
        assert cell_after[key] == cell_before[key]


def test_stamping_the_tier_changes_no_pre_existing_key(tmp_path):
    benchmarks = {"remoteSetRate": {"metrics": {"transaction_lock_acquisitions": _metric_entry([2000] * 5)}}}
    record_a = _record(tmp_path, "a.json", "Model A", benchmarks)
    record_b = _record(tmp_path, "b.json", "Model B", benchmarks)

    cells = perf_gate_baseline.build_cells([record_a, record_b], min_n=5)
    cell = cells["remoteSetRate"]["transaction_lock_acquisitions"]

    assert cell["status"] == perf_gate_baseline.CELL_MEASURED
    assert cell["gate_rule"] == perf_gate_baseline.GATE_RULE_EXACT_EQUALITY
    assert "non_gating_reason" not in cell
    # 10, not 5: both records' samples pool into the same (benchmark, metric) cell.
    assert cell["n"] == 10
    assert cell["observed_value"] == 2000.0
    assert cell["median"] == 2000.0
    assert cell["mad"] == 0.0
    assert cell["minimum"] == 2000.0
    assert cell["maximum"] == 2000.0
    assert cell["spread"] == 0.0
    assert cell["cv"] == 0.0
    assert cell["mde_two_sample_pct"] == 0.0
    assert cell["cpu_models"] == ["Model A", "Model B"]
    # The derivation string still names the grouping, sample count, and observed statistics
    # it always has: adding tier alongside it does not fold tier into the derivation prose.
    assert "grouped per (benchmark='remoteSetRate', metric='transaction_lock_acquisitions')" in cell["derivation"]
    assert "n=10" in cell["derivation"]
    assert "Model A, Model B" in cell["derivation"]


# --- injected-load exclusion --------------------------------------------------


def test_injected_load_record_is_excluded_and_its_run_id_recorded(tmp_path):
    clean_benchmarks = {"remoteSetRate": {"metrics": {"transaction_lock_acquisitions": _metric_entry([2000] * 5)}}}
    injected_benchmarks = {
        "remoteSetRate": {"metrics": {"transaction_lock_acquisitions": _metric_entry([2000, 2000, 2000, 2000, 9999])}},
    }
    clean = _record(tmp_path, "clean.json", "Model A", clean_benchmarks)
    injected = _record(
        tmp_path, "injected.json", "Model A", injected_benchmarks, run={"injected_load": "true"},
    )
    population = {
        "accepted": [clean, injected], "records_skipped": 0, "skipped_reasons": [],
        "records_rejected": 0, "rejected_reasons": [],
    }

    sidecar = perf_gate_baseline.build_sidecar(
        population=population, min_n=5, expected_tree_hash="expected", runs_dir=str(tmp_path),
    )

    assert sidecar["source"]["records_injected_demonstration"] == 1
    assert sidecar["source"]["injected_demonstration_run_ids"] == ["injected"]
    assert sidecar["source"]["record_count_clean"] == 1
    # The injected record's 9999 sample must never appear in the pooled cell.
    cell = sidecar["cells"]["remoteSetRate"]["transaction_lock_acquisitions"]
    assert cell["maximum"] == 2000.0


# --- tree hash rejection -------------------------------------------------------


def test_tree_hash_mismatch_is_rejected_and_counted(tmp_path):
    benchmarks = {"remoteSetRate": {"metrics": {"transaction_lock_acquisitions": _metric_entry([2000] * 5)}}}
    _record(tmp_path, "good.json", "Model A", benchmarks, run={"git_tree_hash": "expected"})
    _record(tmp_path, "mismatch.json", "Model A", benchmarks, run={"git_tree_hash": "other"})

    out_json = tmp_path / "out.json"
    out_md = tmp_path / "out.md"
    exit_code = perf_gate_baseline.main(
        ["--runs-dir", str(tmp_path), "--expected-tree-hash", "expected",
         "--out-json", str(out_json), "--out-md", str(out_md)]
    )

    assert exit_code == 0
    sidecar = json.loads(out_json.read_text(encoding="utf-8"))
    assert sidecar["source"]["record_count"] == 1
    assert sidecar["source"]["records_rejected"] == 1


# --- mde_two_sample_pct reused, not reimplemented -----------------------------


def test_mde_two_sample_pct_matches_the_imported_formula(tmp_path):
    benchmarks = {
        "remoteSetRate": {"metrics": {"transaction_lock_acquisitions": _metric_entry([1990, 2000, 2010, 1995, 2005])}},
    }
    record = _record(tmp_path, "a.json", "Model A", benchmarks)

    cells = perf_gate_baseline.build_cells([record], min_n=5)
    cell = cells["remoteSetRate"]["transaction_lock_acquisitions"]

    expected = perf_campaign_report.two_sample_mde_pct(cell["cv"], cell["n"])
    assert cell["mde_two_sample_pct"] == expected


# --- main(): no output on empty population ------------------------------------


def test_main_exits_1_and_writes_nothing_on_an_empty_population(tmp_path):
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    out_json = tmp_path / "none.json"
    out_md = tmp_path / "none.md"

    exit_code = perf_gate_baseline.main(
        ["--runs-dir", str(empty_dir), "--out-json", str(out_json), "--out-md", str(out_md)]
    )

    assert exit_code == 1
    assert not out_json.exists()
    assert not out_md.exists()


def test_main_neither_output_contains_a_wall_clock_timestamp(tmp_path):
    benchmarks = {"remoteSetRate": {"metrics": {"transaction_lock_acquisitions": _metric_entry([2000] * 5)}}}
    _record(tmp_path, "a.json", "Model A", benchmarks)
    out_json = tmp_path / "out.json"
    out_md = tmp_path / "out.md"

    perf_gate_baseline.main(
        ["--runs-dir", str(tmp_path), "--expected-tree-hash", "expected",
         "--out-json", str(out_json), "--out-md", str(out_md)]
    )

    timestamp_re = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")
    assert timestamp_re.search(out_json.read_text(encoding="utf-8")) is None
    assert timestamp_re.search(out_md.read_text(encoding="utf-8")) is None


def test_render_markdown_headings_present(tmp_path):
    benchmarks = {"remoteSetRate": {"metrics": {"transaction_lock_acquisitions": _metric_entry([2000] * 5)}}}
    record_a = _record(tmp_path, "a.json", "Model A", benchmarks)
    record_b = _record(tmp_path, "b.json", "Model B", benchmarks)
    population = {
        "accepted": [record_a, record_b], "records_skipped": 0, "skipped_reasons": [],
        "records_rejected": 0, "rejected_reasons": [],
    }
    sidecar = perf_gate_baseline.build_sidecar(
        population=population, min_n=5, expected_tree_hash="expected", runs_dir=str(tmp_path),
    )
    markdown = perf_gate_baseline.render_markdown(sidecar)

    for heading in (
        "## Reproducing this baseline", "## Census", "## Gating cells", "## Non-gating cells",
    ):
        assert heading in markdown


def test_render_markdown_gating_table_header_carries_a_tier_column(tmp_path):
    benchmarks = {"remoteSetRate": {"metrics": {"transaction_lock_acquisitions": _metric_entry([2000] * 5)}}}
    record_a = _record(tmp_path, "a.json", "Model A", benchmarks)
    record_b = _record(tmp_path, "b.json", "Model B", benchmarks)
    population = {
        "accepted": [record_a, record_b], "records_skipped": 0, "skipped_reasons": [],
        "records_rejected": 0, "rejected_reasons": [],
    }
    sidecar = perf_gate_baseline.build_sidecar(
        population=population, min_n=5, expected_tree_hash="expected", runs_dir=str(tmp_path),
    )
    markdown = perf_gate_baseline.render_markdown(sidecar)

    assert "| Metric | Benchmark | n | Observed value | Tier | CPU models |" in markdown


def test_render_markdown_is_deterministic_across_two_calls(tmp_path):
    benchmarks = {"remoteSetRate": {"metrics": {"transaction_lock_acquisitions": _metric_entry([2000] * 5)}}}
    record_a = _record(tmp_path, "a.json", "Model A", benchmarks)
    record_b = _record(tmp_path, "b.json", "Model B", benchmarks)
    population = {
        "accepted": [record_a, record_b], "records_skipped": 0, "skipped_reasons": [],
        "records_rejected": 0, "rejected_reasons": [],
    }
    sidecar = perf_gate_baseline.build_sidecar(
        population=population, min_n=5, expected_tree_hash="expected", runs_dir=str(tmp_path),
    )

    first = perf_gate_baseline.render_markdown(sidecar)
    second = perf_gate_baseline.render_markdown(sidecar)

    assert first == second


def test_render_markdown_states_the_observed_value_is_provenance_not_the_comparand(tmp_path):
    benchmarks = {"remoteSetRate": {"metrics": {"transaction_lock_acquisitions": _metric_entry([2000] * 5)}}}
    record_a = _record(tmp_path, "a.json", "Model A", benchmarks)
    record_b = _record(tmp_path, "b.json", "Model B", benchmarks)
    population = {
        "accepted": [record_a, record_b], "records_skipped": 0, "skipped_reasons": [],
        "records_rejected": 0, "rejected_reasons": [],
    }
    sidecar = perf_gate_baseline.build_sidecar(
        population=population, min_n=5, expected_tree_hash="expected", runs_dir=str(tmp_path),
    )
    markdown = perf_gate_baseline.render_markdown(sidecar)

    assert "is provenance, not the comparand" in markdown
    assert "gate compares the candidate leg against the merge-base leg" in markdown


# --- canonical reproduce command: executed for real, not paraphrased -------


def test_reproduce_command_includes_expected_tree_hash_argument():
    assert "--expected-tree-hash" in perf_gate_baseline.CANONICAL_COMMAND


def test_canonical_command_reproduces_committed_baseline_byte_identically(tmp_path):
    argv = shlex.split(perf_gate_baseline.CANONICAL_COMMAND)

    # The interpreter and script tokens are asserted before substitution so a future edit
    # that changes CANONICAL_COMMAND to invoke something other than this module is caught
    # here rather than silently substituted away.
    assert argv[0].startswith("python")
    assert argv[1] == "scripts/perf_gate_baseline.py"

    out_json_index = argv.index("--out-json") + 1
    out_md_index = argv.index("--out-md") + 1
    # Assert the published output paths target the committed artifacts before anything is
    # redirected, so the redirection below cannot mask a command that points elsewhere.
    assert argv[out_json_index] == perf_gate_baseline.DEFAULT_OUT_JSON
    assert argv[out_md_index] == perf_gate_baseline.DEFAULT_OUT_MD

    scratch_json = tmp_path / "regen.json"
    scratch_md = tmp_path / "regen.md"
    argv[0] = sys.executable
    argv[out_json_index] = str(scratch_json)
    argv[out_md_index] = str(scratch_md)

    result = subprocess.run(argv, cwd=REPO_ROOT, capture_output=True, text=True)

    assert result.returncode == 0, result.stderr

    committed_json = (REPO_ROOT / perf_gate_baseline.DEFAULT_OUT_JSON).read_bytes()
    committed_md = (REPO_ROOT / perf_gate_baseline.DEFAULT_OUT_MD).read_bytes()
    assert scratch_json.read_bytes() == committed_json
    assert scratch_md.read_bytes() == committed_md
