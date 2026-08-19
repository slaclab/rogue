# ----------------------------------------------------------------------------
# Title      : Perf Gate Evaluator Tests
# ----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
# ----------------------------------------------------------------------------

"""Unit tests for scripts/perf_gate_evaluator.py. Every test builds its own
small synthetic two-leg record and baseline, carrying only the keys the
evaluator reads, so none of these depend on the real committed population.
"""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

perf_gate_evaluator = importlib.import_module("perf_gate_evaluator")


def _metric_entry(value: float, n: int = 5) -> dict:
    return {"status": "ok", "reason": None, "samples": [value] * n}


def _inconclusive_entry(reason: str) -> dict:
    return {"status": "inconclusive", "reason": reason, "samples": []}


def _unstable_entry(values: list[float]) -> dict:
    return {"status": "ok", "reason": None, "samples": values}


def _bench(metrics: dict, measurement_windows: list | None = None, error: str | None = None) -> dict:
    entry = {"metrics": metrics}
    if measurement_windows is not None:
        entry["measurement_windows"] = measurement_windows
    if error is not None:
        entry["error"] = error
    return entry


def _gating_cell(observed_value) -> dict:
    return {"gate_rule": "exact-equality", "observed_value": observed_value}


def _non_gating_cell(reason: str = "varies-within-population") -> dict:
    return {"gate_rule": "non-gating", "non_gating_reason": reason}


def _baseline(cells: dict) -> dict:
    return {"cells": cells}


def _record(
    candidate_benchmarks: dict,
    merge_base_benchmarks: dict,
    tree_hash_pair_match: bool = True,
    merge_base_build_success: bool = True,
    candidate_build_success: bool = True,
) -> dict:
    return {
        "gate_ab_schema_version": 1,
        "run": {
            "declared_candidate_tree_hash": "cand",
            "declared_merge_base_tree_hash": "base",
            "candidate_tree_hash": "cand",
            "merge_base_tree_hash": "base",
            "tree_hash_pair_match": tree_hash_pair_match,
            "mode": "test",
            "label": "test",
        },
        "legs": {
            "candidate": {"build": {"success": candidate_build_success}, "benchmarks": candidate_benchmarks},
            "merge_base": {"build": {"success": merge_base_build_success}, "benchmarks": merge_base_benchmarks},
        },
        "timings": {}, "stages": {}, "errors": [],
    }


def _single_gating_baseline(observed_value=100) -> dict:
    return _baseline({"bench1": {"m1": _gating_cell(observed_value)}})


def _gating_cell_with_dispersion(
    observed_value,
    *,
    tier=1,
    n=120,
    spread=0.0,
    cv=0.0,
    mde_pct=0.0,
    minimum=None,
    maximum=None,
) -> dict:
    cell = {
        "gate_rule": "exact-equality",
        "observed_value": observed_value,
        "tier": tier,
        "n": n,
        "spread": spread,
        "cv": cv,
        "mde_two_sample_pct": mde_pct,
    }
    if minimum is not None:
        cell["minimum"] = minimum
    if maximum is not None:
        cell["maximum"] = maximum
    return cell


# --- PASS / FAIL on a gating cell ---------------------------------------------


def test_identical_legs_on_a_gating_cell_give_pass():
    baseline = _single_gating_baseline()
    candidate = {"bench1": _bench({"m1": _metric_entry(100)})}
    base = {"bench1": _bench({"m1": _metric_entry(100)})}

    result = perf_gate_evaluator.evaluate_run(_record(candidate, base), baseline)

    assert result["verdict"] == perf_gate_evaluator.VERDICT_PASS
    cell = result["cells"][0]
    assert cell["gating"] is True
    assert cell["delta"] == 0


def test_one_count_difference_on_a_gating_cell_gives_fail():
    baseline = _single_gating_baseline()
    candidate = {"bench1": _bench({"m1": _metric_entry(101)})}
    base = {"bench1": _bench({"m1": _metric_entry(100)})}

    result = perf_gate_evaluator.evaluate_run(_record(candidate, base), baseline)

    assert result["verdict"] == perf_gate_evaluator.VERDICT_FAIL
    cell = result["cells"][0]
    assert cell["delta"] == 1
    assert cell["delta_pct"] == 1.0


def test_base_value_zero_and_candidate_one_gives_fail_with_no_division_error():
    baseline = _single_gating_baseline(observed_value=0)
    candidate = {"bench1": _bench({"m1": _metric_entry(1)})}
    base = {"bench1": _bench({"m1": _metric_entry(0)})}

    result = perf_gate_evaluator.evaluate_run(_record(candidate, base), baseline)

    assert result["verdict"] == perf_gate_evaluator.VERDICT_FAIL
    cell = result["cells"][0]
    assert cell["delta_pct"] is None


def test_non_gating_cell_differing_does_not_change_verdict_from_pass():
    baseline = _baseline({
        "bench1": {"m1": _gating_cell(100), "m2": _non_gating_cell()},
    })
    candidate = {"bench1": _bench({"m1": _metric_entry(100), "m2": _metric_entry(999)})}
    base = {"bench1": _bench({"m1": _metric_entry(100), "m2": _metric_entry(1)})}

    result = perf_gate_evaluator.evaluate_run(_record(candidate, base), baseline)

    assert result["verdict"] == perf_gate_evaluator.VERDICT_PASS
    non_gating = [cell for cell in result["cells"] if cell["metric"] == "m2"][0]
    assert non_gating["gating"] is False


# --- every enumerated INCONCLUSIVE condition, never FAIL ----------------------


def test_condition_insufficient_clean_samples_gives_inconclusive_never_fail():
    baseline = _single_gating_baseline()
    candidate = {"bench1": _bench({"m1": _inconclusive_entry("insufficient-clean-samples")})}
    base = {"bench1": _bench({"m1": _metric_entry(100)})}

    result = perf_gate_evaluator.evaluate_run(_record(candidate, base), baseline)

    assert result["verdict"] == perf_gate_evaluator.VERDICT_INCONCLUSIVE
    assert result["cells"][0]["reason"] == perf_gate_evaluator.REASON_INSUFFICIENT_CLEAN_SAMPLES
    assert all(cell["verdict"] != perf_gate_evaluator.VERDICT_FAIL for cell in result["cells"])


def test_condition_guard_exceeded_gives_inconclusive_never_fail():
    baseline = _single_gating_baseline()
    candidate = {"bench1": _bench({"m1": _inconclusive_entry("guard-exceeded")})}
    base = {"bench1": _bench({"m1": _metric_entry(100)})}

    result = perf_gate_evaluator.evaluate_run(_record(candidate, base), baseline)

    assert result["verdict"] == perf_gate_evaluator.VERDICT_INCONCLUSIVE
    assert result["cells"][0]["reason"] == perf_gate_evaluator.REASON_GUARD_EXCEEDED
    assert all(cell["verdict"] != perf_gate_evaluator.VERDICT_FAIL for cell in result["cells"])


def test_condition_metric_absent_from_leg_gives_inconclusive_never_fail():
    baseline = _single_gating_baseline()
    candidate = {"bench1": _bench({})}
    base = {"bench1": _bench({"m1": _metric_entry(100)})}

    result = perf_gate_evaluator.evaluate_run(_record(candidate, base), baseline)

    assert result["verdict"] == perf_gate_evaluator.VERDICT_INCONCLUSIVE
    assert result["cells"][0]["reason"] == perf_gate_evaluator.REASON_METRIC_ABSENT
    assert all(cell["verdict"] != perf_gate_evaluator.VERDICT_FAIL for cell in result["cells"])


def test_condition_benchmark_errored_gives_inconclusive_never_fail():
    baseline = _single_gating_baseline()
    candidate = {"bench1": _bench({"m1": _metric_entry(100)}, error="benchmark crashed")}
    base = {"bench1": _bench({"m1": _metric_entry(100)})}

    result = perf_gate_evaluator.evaluate_run(_record(candidate, base), baseline)

    assert result["verdict"] == perf_gate_evaluator.VERDICT_INCONCLUSIVE
    assert result["cells"][0]["reason"] == perf_gate_evaluator.REASON_BENCHMARK_ERRORED
    assert all(cell["verdict"] != perf_gate_evaluator.VERDICT_FAIL for cell in result["cells"])


def test_condition_merge_base_build_failed_gives_inconclusive_never_fail():
    baseline = _single_gating_baseline()
    candidate = {"bench1": _bench({"m1": _metric_entry(100)})}
    base = {"bench1": _bench({"m1": _metric_entry(100)})}

    result = perf_gate_evaluator.evaluate_run(
        _record(candidate, base, merge_base_build_success=False), baseline,
    )

    assert result["verdict"] == perf_gate_evaluator.VERDICT_INCONCLUSIVE
    assert result["cells"][0]["reason"] == perf_gate_evaluator.REASON_MERGE_BASE_BUILD_FAILED
    assert all(cell["verdict"] != perf_gate_evaluator.VERDICT_FAIL for cell in result["cells"])


def test_condition_tree_hash_pair_mismatch_gives_inconclusive_never_fail():
    baseline = _single_gating_baseline()
    candidate = {"bench1": _bench({"m1": _metric_entry(100)})}
    base = {"bench1": _bench({"m1": _metric_entry(100)})}

    result = perf_gate_evaluator.evaluate_run(
        _record(candidate, base, tree_hash_pair_match=False), baseline,
    )

    assert result["verdict"] == perf_gate_evaluator.VERDICT_INCONCLUSIVE
    assert result["cells"][0]["reason"] == perf_gate_evaluator.REASON_TREE_HASH_PAIR_MISMATCH
    assert all(cell["verdict"] != perf_gate_evaluator.VERDICT_FAIL for cell in result["cells"])
    assert result["tree_hash_pair"]["tree_hash_pair_match"] is False


def test_condition_secondary_window_flag_gives_inconclusive_never_fail():
    baseline = _single_gating_baseline()
    windows = [{"secondary_flags": ["steal-nonzero"]}]
    candidate = {"bench1": _bench({"m1": _metric_entry(100)}, measurement_windows=windows)}
    base = {"bench1": _bench({"m1": _metric_entry(100)})}

    result = perf_gate_evaluator.evaluate_run(_record(candidate, base), baseline)

    assert result["verdict"] == perf_gate_evaluator.VERDICT_INCONCLUSIVE
    assert result["cells"][0]["reason"] == perf_gate_evaluator.REASON_SECONDARY_FLAG
    assert all(cell["verdict"] != perf_gate_evaluator.VERDICT_FAIL for cell in result["cells"])


def test_condition_within_run_nondeterminism_gives_inconclusive_never_fail():
    baseline = _single_gating_baseline()
    candidate = {"bench1": _bench({"m1": _unstable_entry([100, 100, 100, 100, 101])})}
    base = {"bench1": _bench({"m1": _metric_entry(100)})}

    result = perf_gate_evaluator.evaluate_run(_record(candidate, base), baseline)

    assert result["verdict"] == perf_gate_evaluator.VERDICT_INCONCLUSIVE
    assert result["cells"][0]["reason"] == perf_gate_evaluator.REASON_WITHIN_RUN_UNSTABLE
    assert all(cell["verdict"] != perf_gate_evaluator.VERDICT_FAIL for cell in result["cells"])


def test_condition_baseline_cell_missing_gives_inconclusive_never_fail():
    result = perf_gate_evaluator.evaluate_cell(
        "bench1", "m1", {"status": "ok", "reason": None, "samples": [100]}, {"status": "ok", "reason": None, "samples": [100]}, None,
    )

    assert result["verdict"] == perf_gate_evaluator.VERDICT_INCONCLUSIVE
    assert result["reason"] == perf_gate_evaluator.REASON_BASELINE_CELL_MISSING


def test_condition_no_gating_cell_evaluated_gives_inconclusive_never_pass():
    baseline = _baseline({"bench1": {"m1": _non_gating_cell()}})
    candidate = {"bench1": _bench({"m1": _metric_entry(100)})}
    base = {"bench1": _bench({"m1": _metric_entry(100)})}

    result = perf_gate_evaluator.evaluate_run(_record(candidate, base), baseline)

    assert result["verdict"] == perf_gate_evaluator.VERDICT_INCONCLUSIVE
    assert result["verdict_reason"] == perf_gate_evaluator.REASON_NO_GATING_CELL
    assert result["gating_cell_count"] == 0


# --- multi-failure listing, ordering, and stable condition_counts ------------


def test_failing_cells_lists_every_failing_gating_cell():
    baseline = _baseline({
        "bench1": {"m1": _gating_cell(100), "m2": _gating_cell(100), "m3": _gating_cell(100)},
    })
    candidate = {"bench1": _bench({
        "m1": _metric_entry(101), "m2": _metric_entry(101), "m3": _metric_entry(101),
    })}
    base = {"bench1": _bench({
        "m1": _metric_entry(100), "m2": _metric_entry(100), "m3": _metric_entry(100),
    })}

    result = perf_gate_evaluator.evaluate_run(_record(candidate, base), baseline)

    assert result["verdict"] == perf_gate_evaluator.VERDICT_FAIL
    assert len(result["failing_cells"]) == 3


def test_condition_counts_keys_equal_inconclusive_conditions_in_order():
    baseline = _single_gating_baseline()
    candidate = {"bench1": _bench({"m1": _metric_entry(100)})}
    base = {"bench1": _bench({"m1": _metric_entry(100)})}

    result = perf_gate_evaluator.evaluate_run(_record(candidate, base), baseline)

    assert list(result["condition_counts"].keys()) == list(perf_gate_evaluator.INCONCLUSIVE_CONDITIONS)
    # A PASS run fires no condition at all: every count starts at zero.
    assert all(count == 0 for count in result["condition_counts"].values())


def test_cells_are_returned_in_sorted_benchmark_metric_order():
    baseline = _baseline({
        "zeta": {"m2": _gating_cell(1), "m1": _gating_cell(1)},
        "alpha": {"m1": _gating_cell(1)},
    })
    candidate = {
        "zeta": _bench({"m1": _metric_entry(1), "m2": _metric_entry(1)}),
        "alpha": _bench({"m1": _metric_entry(1)}),
    }
    base = {
        "zeta": _bench({"m1": _metric_entry(1), "m2": _metric_entry(1)}),
        "alpha": _bench({"m1": _metric_entry(1)}),
    }

    result = perf_gate_evaluator.evaluate_run(_record(candidate, base), baseline)

    pairs = [(cell["benchmark"], cell["metric"]) for cell in result["cells"]]
    assert pairs == sorted(pairs)


def test_baseline_cell_requires_both_arguments():
    with pytest.raises(TypeError):
        perf_gate_evaluator.baseline_cell({"cells": {}})


def test_render_summary_markdown_is_deterministic_over_the_same_evaluation():
    baseline = _single_gating_baseline()
    candidate = {"bench1": _bench({"m1": _metric_entry(101)})}
    base = {"bench1": _bench({"m1": _metric_entry(100)})}
    result = perf_gate_evaluator.evaluate_run(_record(candidate, base), baseline)

    first = perf_gate_evaluator.render_summary_markdown(result)
    second = perf_gate_evaluator.render_summary_markdown(result)

    assert first == second


def test_malformed_record_missing_merge_base_leg_resolves_to_inconclusive_never_raises():
    baseline = _single_gating_baseline()
    malformed_record = {
        "run": {"tree_hash_pair_match": True},
        "legs": {
            "candidate": {"build": {"success": True}, "benchmarks": {"bench1": _bench({"m1": _metric_entry(100)})}},
        },
    }

    result = perf_gate_evaluator.evaluate_run(malformed_record, baseline)

    assert result["verdict"] == perf_gate_evaluator.VERDICT_INCONCLUSIVE
    assert all(cell["verdict"] != perf_gate_evaluator.VERDICT_FAIL for cell in result["cells"])


# --- main(): a broken baseline is "I do not know", never exit 2 --------------


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_main_nonexistent_baseline_path_returns_2(tmp_path):
    record_path = tmp_path / "record.json"
    _write_json(record_path, _record(
        {"bench1": _bench({"m1": _metric_entry(100)})},
        {"bench1": _bench({"m1": _metric_entry(100)})},
    ))
    out_json = tmp_path / "verdict.json"
    out_md = tmp_path / "verdict.md"

    exit_code = perf_gate_evaluator.main([
        "--record", str(record_path),
        "--baseline", str(tmp_path / "does-not-exist.json"),
        "--out-json", str(out_json),
        "--out-md", str(out_md),
    ])

    assert exit_code == 2
    assert not out_json.exists()
    assert not out_md.exists()


def test_main_malformed_baseline_json_returns_2(tmp_path):
    record_path = tmp_path / "record.json"
    _write_json(record_path, _record(
        {"bench1": _bench({"m1": _metric_entry(100)})},
        {"bench1": _bench({"m1": _metric_entry(100)})},
    ))
    baseline_path = tmp_path / "baseline.json"
    baseline_path.write_text("{not valid json", encoding="utf-8")
    out_json = tmp_path / "verdict.json"
    out_md = tmp_path / "verdict.md"

    exit_code = perf_gate_evaluator.main([
        "--record", str(record_path),
        "--baseline", str(baseline_path),
        "--out-json", str(out_json),
        "--out-md", str(out_md),
    ])

    assert exit_code == 2
    assert not out_json.exists()
    assert not out_md.exists()


def test_main_valid_baseline_with_zero_cells_yields_inconclusive_and_exit_zero(tmp_path):
    record_path = tmp_path / "record.json"
    _write_json(record_path, _record(
        {"bench1": _bench({"m1": _metric_entry(100)})},
        {"bench1": _bench({"m1": _metric_entry(100)})},
    ))
    baseline_path = tmp_path / "baseline.json"
    _write_json(baseline_path, _baseline({}))
    out_json = tmp_path / "verdict.json"

    exit_code = perf_gate_evaluator.main([
        "--record", str(record_path),
        "--baseline", str(baseline_path),
        "--out-json", str(out_json),
    ])

    assert exit_code == 0
    written = json.loads(out_json.read_text(encoding="utf-8"))
    assert written["verdict"] == perf_gate_evaluator.VERDICT_INCONCLUSIVE
    assert written["verdict_reason"] == perf_gate_evaluator.REASON_NO_GATING_CELL


def test_main_valid_baseline_with_only_non_gating_cells_yields_inconclusive_and_exit_zero(tmp_path):
    record_path = tmp_path / "record.json"
    _write_json(record_path, _record(
        {"bench1": _bench({"m1": _metric_entry(100)})},
        {"bench1": _bench({"m1": _metric_entry(100)})},
    ))
    baseline_path = tmp_path / "baseline.json"
    _write_json(baseline_path, _baseline({"bench1": {"m1": _non_gating_cell()}}))
    out_json = tmp_path / "verdict.json"

    exit_code = perf_gate_evaluator.main([
        "--record", str(record_path),
        "--baseline", str(baseline_path),
        "--out-json", str(out_json),
    ])

    assert exit_code == 0
    written = json.loads(out_json.read_text(encoding="utf-8"))
    assert written["verdict"] == perf_gate_evaluator.VERDICT_INCONCLUSIVE
    assert written["verdict_reason"] == perf_gate_evaluator.REASON_NO_GATING_CELL


def test_main_baseline_read_failure_writes_no_verdict_outputs(tmp_path):
    record_path = tmp_path / "record.json"
    _write_json(record_path, _record(
        {"bench1": _bench({"m1": _metric_entry(100)})},
        {"bench1": _bench({"m1": _metric_entry(100)})},
    ))
    out_json = tmp_path / "verdict.json"
    out_md = tmp_path / "verdict.md"
    stale_payload = '{"stale": "verdict from an earlier step"}'
    out_json.write_text(stale_payload, encoding="utf-8")

    exit_code = perf_gate_evaluator.main([
        "--record", str(record_path),
        "--baseline", str(tmp_path / "does-not-exist.json"),
        "--out-json", str(out_json),
        "--out-md", str(out_md),
    ])

    assert exit_code == 2
    assert not out_md.exists()
    assert out_json.read_text(encoding="utf-8") == stale_payload


def test_main_valid_baseline_and_matching_record_yields_pass_with_null_reason(tmp_path):
    record_path = tmp_path / "record.json"
    _write_json(record_path, _record(
        {"bench1": _bench({"m1": _metric_entry(100)})},
        {"bench1": _bench({"m1": _metric_entry(100)})},
    ))
    baseline_path = tmp_path / "baseline.json"
    _write_json(baseline_path, _single_gating_baseline())
    out_json = tmp_path / "verdict.json"

    exit_code = perf_gate_evaluator.main([
        "--record", str(record_path),
        "--baseline", str(baseline_path),
        "--out-json", str(out_json),
    ])

    assert exit_code == 0
    written = json.loads(out_json.read_text(encoding="utf-8"))
    assert written["verdict"] == perf_gate_evaluator.VERDICT_PASS
    assert written["baseline_unavailable_reason"] is None


def test_main_nonexistent_record_path_still_returns_2(tmp_path):
    baseline_path = tmp_path / "baseline.json"
    _write_json(baseline_path, _single_gating_baseline())

    exit_code = perf_gate_evaluator.main([
        "--record", str(tmp_path / "does-not-exist.json"),
        "--baseline", str(baseline_path),
    ])

    assert exit_code == 2


def test_main_exit_nonzero_on_fail_with_inconclusive_verdict_returns_zero(tmp_path):
    # A valid baseline declaring zero gate-eligible cells, not a broken one: this test pins
    # the guarantee that a non-blocking INCONCLUSIVE verdict never blocks, which is a
    # different fact from whether a broken baseline read is loud.
    record_path = tmp_path / "record.json"
    _write_json(record_path, _record(
        {"bench1": _bench({"m1": _metric_entry(100)})},
        {"bench1": _bench({"m1": _metric_entry(100)})},
    ))
    baseline_path = tmp_path / "baseline.json"
    _write_json(baseline_path, _baseline({}))

    exit_code = perf_gate_evaluator.main([
        "--record", str(record_path),
        "--baseline", str(baseline_path),
        "--exit-nonzero-on-fail",
    ])

    assert exit_code == 0


# --- main(): --baseline-unavailable-reason, an absent trusted baseline ------------------


def test_main_baseline_unavailable_reason_yields_inconclusive_and_exit_zero_with_no_record_or_baseline(tmp_path):
    # Neither --record nor --baseline points at a real file: the point of this flag is that
    # the outcome is robust even when the measurement also failed to produce a record.
    out_json = tmp_path / "verdict.json"
    out_md = tmp_path / "verdict.md"
    detail = "Trusted baseline blob is not present at deadbeef:docs/plans/perf-ci-hardening/gate-baseline.json"

    exit_code = perf_gate_evaluator.main([
        "--record", str(tmp_path / "does-not-exist-record.json"),
        "--baseline", str(tmp_path / "does-not-exist-baseline.json"),
        "--baseline-unavailable-reason", detail,
        "--out-json", str(out_json),
        "--out-md", str(out_md),
    ])

    assert exit_code == 0
    written = json.loads(out_json.read_text(encoding="utf-8"))
    assert written["verdict"] == perf_gate_evaluator.VERDICT_INCONCLUSIVE
    assert written["verdict_reason"] == perf_gate_evaluator.REASON_TRUSTED_BASELINE_ABSENT
    assert written["baseline_unavailable_reason"] == detail
    assert written["gating_cell_count"] == 0
    assert written["cells"] == []

    rendered = out_md.read_text(encoding="utf-8")
    assert "no trusted baseline exists yet" in rendered.lower()
    assert "This outcome does not block." in rendered
    assert detail in rendered


def test_main_baseline_unavailable_reason_never_exits_nonzero_on_fail(tmp_path):
    exit_code = perf_gate_evaluator.main([
        "--record", str(tmp_path / "does-not-exist-record.json"),
        "--baseline", str(tmp_path / "does-not-exist-baseline.json"),
        "--baseline-unavailable-reason", "trusted baseline absent",
        "--exit-nonzero-on-fail",
    ])

    assert exit_code == 0


def test_main_baseline_unavailable_reason_takes_effect_even_when_record_and_baseline_paths_are_valid(tmp_path):
    # A supplied --baseline-unavailable-reason short-circuits before either --record or
    # --baseline is opened at all, even when both happen to point at readable files.
    record_path = tmp_path / "record.json"
    _write_json(record_path, _record(
        {"bench1": _bench({"m1": _metric_entry(101)})},
        {"bench1": _bench({"m1": _metric_entry(100)})},
    ))
    baseline_path = tmp_path / "baseline.json"
    _write_json(baseline_path, _single_gating_baseline())
    out_json = tmp_path / "verdict.json"

    exit_code = perf_gate_evaluator.main([
        "--record", str(record_path),
        "--baseline", str(baseline_path),
        "--baseline-unavailable-reason", "trusted baseline absent",
        "--out-json", str(out_json),
    ])

    assert exit_code == 0
    written = json.loads(out_json.read_text(encoding="utf-8"))
    assert written["verdict"] == perf_gate_evaluator.VERDICT_INCONCLUSIVE
    assert written["verdict_reason"] == perf_gate_evaluator.REASON_TRUSTED_BASELINE_ABSENT


def test_main_corrupt_baseline_present_at_merge_base_still_returns_2_not_inconclusive(tmp_path):
    # Pins the preserved behavior this fix must not touch: a baseline that is present but
    # unparseable at the merge base is an upstream defect a human must fix, a different fact
    # from a baseline that is simply absent, and must keep failing loudly rather than
    # resolving to a non-blocking INCONCLUSIVE.
    record_path = tmp_path / "record.json"
    _write_json(record_path, _record(
        {"bench1": _bench({"m1": _metric_entry(100)})},
        {"bench1": _bench({"m1": _metric_entry(100)})},
    ))
    baseline_path = tmp_path / "baseline.json"
    baseline_path.write_text("{not valid json", encoding="utf-8")

    exit_code = perf_gate_evaluator.main([
        "--record", str(record_path),
        "--baseline", str(baseline_path),
    ])

    assert exit_code == 2


def test_render_inconclusive_baseline_absent_explains_the_situation_and_does_not_block():
    evaluation = perf_gate_evaluator._baseline_unavailable_evaluation(
        "Trusted baseline blob is not present at deadbeef:docs/plans/perf-ci-hardening/gate-baseline.json",
    )

    rendered = perf_gate_evaluator.render_summary_markdown(evaluation)

    assert "Verdict: INCONCLUSIVE" in rendered
    assert f"Verdict reason: {perf_gate_evaluator.REASON_TRUSTED_BASELINE_ABSENT}" in rendered
    assert "no trusted baseline exists yet" in rendered.lower()
    assert "expected, not a defect" in rendered
    assert "Trusted baseline blob is not present at deadbeef" in rendered
    assert "This outcome does not block." in rendered
    assert perf_gate_evaluator.DOC_POINTER_LINE in rendered


def test_render_inconclusive_baseline_absent_wall_clock_line_has_no_glued_placeholder_or_bare_none():
    # The absent-baseline evaluation carries no measurement record, so `budget.total_seconds`
    # and `budget.within_budget` are both None. The Wall clock line must read the absent
    # values as `n/a`, never glue a unit suffix onto that placeholder (`n/as`), and never
    # render the bare Python `None` literal for `within_budget`.
    evaluation = perf_gate_evaluator._baseline_unavailable_evaluation(
        "trusted baseline absent",
    )

    rendered = perf_gate_evaluator.render_summary_markdown(evaluation)

    assert "n/as" not in rendered
    assert "within budget: None" not in rendered
    wall_clock_line = next(line for line in rendered.splitlines() if line.startswith("Wall clock:"))
    budget_seconds = perf_gate_evaluator.GATE_BUDGET_SECONDS
    assert wall_clock_line == f"Wall clock: n/a against a {budget_seconds}s budget (within budget: n/a)."


# --- RETRY_ELIGIBLE_CONDITIONS / STRUCTURAL_CONDITIONS: the retry partition ---------------


def test_retry_eligible_and_structural_conditions_partition_inconclusive_exhaustively():
    combined = set(perf_gate_evaluator.RETRY_ELIGIBLE_CONDITIONS) | set(perf_gate_evaluator.STRUCTURAL_CONDITIONS)
    assert combined == set(perf_gate_evaluator.INCONCLUSIVE_CONDITIONS)


def test_retry_eligible_and_structural_conditions_are_disjoint():
    retry_eligible = set(perf_gate_evaluator.RETRY_ELIGIBLE_CONDITIONS)
    structural = set(perf_gate_evaluator.STRUCTURAL_CONDITIONS)
    assert not (retry_eligible & structural)


def test_retry_eligible_conditions_preserve_the_inconclusive_conditions_declared_order():
    ordered = [c for c in perf_gate_evaluator.INCONCLUSIVE_CONDITIONS if c in set(perf_gate_evaluator.RETRY_ELIGIBLE_CONDITIONS)]
    assert ordered == list(perf_gate_evaluator.RETRY_ELIGIBLE_CONDITIONS)


def test_structural_conditions_preserve_the_inconclusive_conditions_declared_order():
    ordered = [c for c in perf_gate_evaluator.INCONCLUSIVE_CONDITIONS if c in set(perf_gate_evaluator.STRUCTURAL_CONDITIONS)]
    assert ordered == list(perf_gate_evaluator.STRUCTURAL_CONDITIONS)


def test_metric_absent_from_leg_is_classified_retry_eligible_not_structural():
    # The one classification this plan makes rather than inherits from the locked decision:
    # a reviewer should confirm this rather than assume it (see the plan's own flagged
    # assumption). Pinned here so a future edit that flips it fails loudly.
    assert perf_gate_evaluator.REASON_METRIC_ABSENT in perf_gate_evaluator.RETRY_ELIGIBLE_CONDITIONS
    assert perf_gate_evaluator.REASON_METRIC_ABSENT not in perf_gate_evaluator.STRUCTURAL_CONDITIONS


def test_the_five_locked_retry_eligible_reasons_are_all_present():
    locked = {
        perf_gate_evaluator.REASON_INSUFFICIENT_CLEAN_SAMPLES,
        perf_gate_evaluator.REASON_GUARD_EXCEEDED,
        perf_gate_evaluator.REASON_SECONDARY_FLAG,
        perf_gate_evaluator.REASON_WITHIN_RUN_UNSTABLE,
        perf_gate_evaluator.REASON_BENCHMARK_ERRORED,
    }
    assert locked <= set(perf_gate_evaluator.RETRY_ELIGIBLE_CONDITIONS)


def test_the_five_locked_structural_reasons_are_all_present():
    locked = {
        perf_gate_evaluator.REASON_TREE_HASH_PAIR_MISMATCH,
        perf_gate_evaluator.REASON_MERGE_BASE_BUILD_FAILED,
        perf_gate_evaluator.REASON_BASELINE_CELL_MISSING,
        perf_gate_evaluator.REASON_NO_GATING_CELL,
        perf_gate_evaluator.REASON_TRUSTED_BASELINE_ABSENT,
    }
    assert locked == set(perf_gate_evaluator.STRUCTURAL_CONDITIONS)


def test_reason_trusted_baseline_absent_is_structural_not_retry_eligible():
    # An absent trusted baseline joins the structural side of the partition: a
    # re-measurement cannot make a baseline file that does not exist at the merge base
    # appear, so retrying it would only spend a full paired build on a foregone outcome.
    assert perf_gate_evaluator.REASON_TRUSTED_BASELINE_ABSENT in perf_gate_evaluator.INCONCLUSIVE_CONDITIONS
    assert perf_gate_evaluator.REASON_TRUSTED_BASELINE_ABSENT in perf_gate_evaluator.STRUCTURAL_CONDITIONS
    assert perf_gate_evaluator.REASON_TRUSTED_BASELINE_ABSENT not in perf_gate_evaluator.RETRY_ELIGIBLE_CONDITIONS


def test_evaluator_schema_version_and_inconclusive_conditions_are_unchanged_by_the_partition():
    assert perf_gate_evaluator.EVALUATOR_SCHEMA_VERSION == 1
    assert len(perf_gate_evaluator.INCONCLUSIVE_CONDITIONS) == 11


# --- the committed baseline itself -------------------------------------------


def test_committed_baseline_parses_and_declares_a_positive_exact_equality_cell_count():
    baseline_path = REPO_ROOT / "docs" / "plans" / "perf-ci-hardening" / "gate-baseline.json"
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))

    exact_equality_count = sum(
        1
        for benchmark_cells in baseline["cells"].values()
        for cell in benchmark_cells.values()
        if cell.get("gate_rule") == "exact-equality"
    )

    assert exact_equality_count > 0


# --- parse_override_trailer: absent / rejected / accepted --------------------


def test_parse_override_trailer_none_value_is_absent():
    result = perf_gate_evaluator.parse_override_trailer(None)
    assert result["status"] == perf_gate_evaluator.OVERRIDE_STATUS_ABSENT
    assert result["justification"] is None
    assert result["requested_cells"] == []
    assert result["rejection_reason"] is None


def test_parse_override_trailer_empty_value_is_absent():
    result = perf_gate_evaluator.parse_override_trailer("")
    assert result["status"] == perf_gate_evaluator.OVERRIDE_STATUS_ABSENT


def test_parse_override_trailer_whitespace_only_value_is_absent():
    result = perf_gate_evaluator.parse_override_trailer("   \t  ")
    assert result["status"] == perf_gate_evaluator.OVERRIDE_STATUS_ABSENT


def test_parse_override_trailer_no_semicolon_is_rejected():
    result = perf_gate_evaluator.parse_override_trailer("bench1.m1")
    assert result["status"] == perf_gate_evaluator.OVERRIDE_STATUS_REJECTED
    assert result["rejection_reason"] == perf_gate_evaluator.OVERRIDE_REJECTED_NO_SEMICOLON


def test_parse_override_trailer_empty_justification_is_rejected():
    result = perf_gate_evaluator.parse_override_trailer("bench1.m1;   ")
    assert result["status"] == perf_gate_evaluator.OVERRIDE_STATUS_REJECTED
    assert result["rejection_reason"] == perf_gate_evaluator.OVERRIDE_REJECTED_EMPTY_JUSTIFICATION


def test_parse_override_trailer_below_minimum_justification_is_rejected():
    result = perf_gate_evaluator.parse_override_trailer("bench1.m1;too short")
    assert result["status"] == perf_gate_evaluator.OVERRIDE_STATUS_REJECTED
    assert result["rejection_reason"] == perf_gate_evaluator.OVERRIDE_REJECTED_JUSTIFICATION_TOO_SHORT


def test_parse_override_trailer_empty_cell_list_is_rejected():
    result = perf_gate_evaluator.parse_override_trailer(";this is a real justification sentence")
    assert result["status"] == perf_gate_evaluator.OVERRIDE_STATUS_REJECTED
    assert result["rejection_reason"] == perf_gate_evaluator.OVERRIDE_REJECTED_EMPTY_CELL_LIST


def test_parse_override_trailer_malformed_cell_token_is_rejected():
    result = perf_gate_evaluator.parse_override_trailer(
        "bench1/../etc;this is a real justification sentence",
    )
    assert result["status"] == perf_gate_evaluator.OVERRIDE_STATUS_REJECTED
    assert result["rejection_reason"] == perf_gate_evaluator.OVERRIDE_REJECTED_MALFORMED_CELL_TOKEN


def test_parse_override_trailer_well_formed_is_accepted():
    result = perf_gate_evaluator.parse_override_trailer(
        "bench1.m1,bench2.m2;this justification is long enough to pass",
        author="Larry Ruckman",
    )
    assert result["status"] == perf_gate_evaluator.OVERRIDE_STATUS_ACCEPTED
    assert result["requested_cells"] == [("bench1", "m1"), ("bench2", "m2")]
    assert result["justification"] == "this justification is long enough to pass"
    assert result["author"] == "Larry Ruckman"
    assert result["rejection_reason"] is None


def test_parse_override_trailer_minimum_length_counts_unicode_code_points_not_bytes():
    # Twenty accented code points (each a multi-byte UTF-8 sequence) is accepted; a shorter
    # all-ASCII justification of the same or greater byte length is rejected.
    accented_justification = "é" * perf_gate_evaluator.OVERRIDE_MIN_JUSTIFICATION_CHARS
    accepted = perf_gate_evaluator.parse_override_trailer(f"bench1.m1;{accented_justification}")
    assert accepted["status"] == perf_gate_evaluator.OVERRIDE_STATUS_ACCEPTED
    assert len(accepted["justification"]) == perf_gate_evaluator.OVERRIDE_MIN_JUSTIFICATION_CHARS

    short_ascii = "a" * (perf_gate_evaluator.OVERRIDE_MIN_JUSTIFICATION_CHARS - 1)
    rejected = perf_gate_evaluator.parse_override_trailer(f"bench1.m1;{short_ascii}")
    assert rejected["status"] == perf_gate_evaluator.OVERRIDE_STATUS_REJECTED
    assert rejected["rejection_reason"] == perf_gate_evaluator.OVERRIDE_REJECTED_JUSTIFICATION_TOO_SHORT


def test_parse_override_trailer_preserves_interior_newlines_and_non_ascii_exactly():
    raw = "  bench1.m1;  line one\nligne deux avec des accents: é à ü  \n  "
    result = perf_gate_evaluator.parse_override_trailer(raw)
    assert result["status"] == perf_gate_evaluator.OVERRIDE_STATUS_ACCEPTED
    assert result["justification"] == "line one\nligne deux avec des accents: é à ü"


def test_parse_override_trailer_deduplicates_cell_tokens_preserving_first_appearance_order():
    result = perf_gate_evaluator.parse_override_trailer(
        "bench1.m1,bench2.m2,bench1.m1;this justification is long enough to pass",
    )
    assert result["status"] == perf_gate_evaluator.OVERRIDE_STATUS_ACCEPTED
    assert result["requested_cells"] == [("bench1", "m1"), ("bench2", "m2")]


def test_parse_override_trailer_unavailability_reason_recorded_verbatim():
    result = perf_gate_evaluator.parse_override_trailer(
        "", unavailable_reason="trailer-parser-subcommand-missing",
    )
    assert result["unavailable_reason"] == "trailer-parser-subcommand-missing"
    assert result["status"] == perf_gate_evaluator.OVERRIDE_STATUS_ABSENT


# --- evaluate_run(override=...): the no-override path stays byte-identical ---


def test_evaluate_run_with_no_override_matches_the_pre_override_shape_exactly():
    baseline = _single_gating_baseline()
    candidate = {"bench1": _bench({"m1": _metric_entry(101)})}
    base = {"bench1": _bench({"m1": _metric_entry(100)})}

    result = perf_gate_evaluator.evaluate_run(_record(candidate, base), baseline)

    assert result["verdict"] == perf_gate_evaluator.VERDICT_FAIL
    assert result["verdict_reason"] is None
    assert len(result["cells"]) == 1
    cell = result["cells"][0]
    assert cell["benchmark"] == "bench1"
    assert cell["metric"] == "m1"
    assert cell["gating"] is True
    assert cell["verdict"] == perf_gate_evaluator.VERDICT_FAIL
    assert cell["reason"] is None
    assert cell["candidate_value"] == 101
    assert cell["base_value"] == 100
    assert cell["delta"] == 1
    assert cell["delta_pct"] == 1.0
    assert cell["baseline_value"] == 100
    assert result["gating_cell_count"] == 1
    assert result["failing_cells"] == [cell]
    assert result["condition_counts"] == {c: 0 for c in perf_gate_evaluator.INCONCLUSIVE_CONDITIONS}
    assert result["tree_hash_pair"]["tree_hash_pair_match"] is True
    assert result["exempted_cells"] == []
    assert result["override"]["status"] == perf_gate_evaluator.OVERRIDE_STATUS_ABSENT


# --- evaluate_run(override=...): named-cells-only exemption -------------------


def _two_failing_gating_baseline() -> dict:
    return _baseline({
        "bench1": {"m1": _gating_cell(100)},
        "bench2": {"m1": _gating_cell(100)},
    })


def _accepted_override(cells_text: str, justification="this justification is long enough to pass"):
    return perf_gate_evaluator.parse_override_trailer(f"{cells_text};{justification}")


def test_override_naming_only_one_of_two_failing_cells_leaves_the_other_failing():
    baseline = _two_failing_gating_baseline()
    candidate = {
        "bench1": _bench({"m1": _metric_entry(101)}),
        "bench2": _bench({"m1": _metric_entry(101)}),
    }
    base = {
        "bench1": _bench({"m1": _metric_entry(100)}),
        "bench2": _bench({"m1": _metric_entry(100)}),
    }
    override = _accepted_override("bench1.m1")

    result = perf_gate_evaluator.evaluate_run(_record(candidate, base), baseline, override=override)

    assert result["verdict"] == perf_gate_evaluator.VERDICT_FAIL
    assert len(result["exempted_cells"]) == 1
    assert result["exempted_cells"][0]["benchmark"] == "bench1"
    assert len(result["failing_cells"]) == 1
    assert result["failing_cells"][0]["benchmark"] == "bench2"
    assert result["exempted_cells"][0]["override_applied"] is True
    assert result["failing_cells"][0]["override_applied"] is False


def test_override_naming_every_failing_cell_gives_pass_when_no_gating_cell_is_inconclusive():
    baseline = _single_gating_baseline()
    candidate = {"bench1": _bench({"m1": _metric_entry(101)})}
    base = {"bench1": _bench({"m1": _metric_entry(100)})}
    override = _accepted_override("bench1.m1")

    result = perf_gate_evaluator.evaluate_run(_record(candidate, base), baseline, override=override)

    assert result["verdict"] == perf_gate_evaluator.VERDICT_PASS
    assert result["failing_cells"] == []
    assert len(result["exempted_cells"]) == 1


def test_override_naming_every_failing_cell_gives_inconclusive_when_another_gating_cell_is_inconclusive():
    baseline = _baseline({
        "bench1": {"m1": _gating_cell(100)},
        "bench2": {"m1": _gating_cell(100)},
    })
    candidate = {
        "bench1": _bench({"m1": _metric_entry(101)}),
        "bench2": _bench({"m1": _inconclusive_entry("insufficient-clean-samples")}),
    }
    base = {
        "bench1": _bench({"m1": _metric_entry(100)}),
        "bench2": _bench({"m1": _metric_entry(100)}),
    }
    override = _accepted_override("bench1.m1")

    result = perf_gate_evaluator.evaluate_run(_record(candidate, base), baseline, override=override)

    assert result["verdict"] == perf_gate_evaluator.VERDICT_INCONCLUSIVE
    assert result["failing_cells"] == []


def test_override_naming_a_gating_cell_that_is_not_failing_is_unmatched_not_failing():
    baseline = _two_failing_gating_baseline()
    candidate = {
        "bench1": _bench({"m1": _metric_entry(101)}),
        "bench2": _bench({"m1": _metric_entry(100)}),
    }
    base = {
        "bench1": _bench({"m1": _metric_entry(100)}),
        "bench2": _bench({"m1": _metric_entry(100)}),
    }
    override = _accepted_override("bench1.m1,bench2.m1")

    result = perf_gate_evaluator.evaluate_run(_record(candidate, base), baseline, override=override)

    unmatched = result["override"]["unmatched_cells"]
    assert {"benchmark": "bench2", "metric": "m1", "reason": perf_gate_evaluator.OVERRIDE_UNMATCHED_NOT_FAILING} in unmatched
    assert result["verdict"] == perf_gate_evaluator.VERDICT_PASS


def test_override_naming_a_non_gating_cell_is_unmatched_not_gating():
    baseline = _baseline({
        "bench1": {"m1": _gating_cell(100), "m2": _non_gating_cell()},
    })
    candidate = {"bench1": _bench({"m1": _metric_entry(101), "m2": _metric_entry(1)})}
    base = {"bench1": _bench({"m1": _metric_entry(100), "m2": _metric_entry(2)})}
    override = _accepted_override("bench1.m1,bench1.m2")

    result = perf_gate_evaluator.evaluate_run(_record(candidate, base), baseline, override=override)

    unmatched = result["override"]["unmatched_cells"]
    assert {
        "benchmark": "bench1", "metric": "m2", "reason": perf_gate_evaluator.OVERRIDE_UNMATCHED_NOT_GATING,
    } in unmatched


def test_override_naming_a_cell_absent_from_the_baseline_is_unmatched_absent():
    baseline = _single_gating_baseline()
    candidate = {"bench1": _bench({"m1": _metric_entry(101)})}
    base = {"bench1": _bench({"m1": _metric_entry(100)})}
    override = _accepted_override("bench1.m1,nosuchbench.nosuchmetric")

    result = perf_gate_evaluator.evaluate_run(_record(candidate, base), baseline, override=override)

    unmatched = result["override"]["unmatched_cells"]
    assert {
        "benchmark": "nosuchbench", "metric": "nosuchmetric",
        "reason": perf_gate_evaluator.OVERRIDE_UNMATCHED_ABSENT_FROM_BASELINE,
    } in unmatched


def test_override_benchmark_name_differing_only_in_case_matches_nothing():
    baseline = _single_gating_baseline()
    candidate = {"bench1": _bench({"m1": _metric_entry(101)})}
    base = {"bench1": _bench({"m1": _metric_entry(100)})}
    override = _accepted_override("Bench1.m1")

    result = perf_gate_evaluator.evaluate_run(_record(candidate, base), baseline, override=override)

    assert result["verdict"] == perf_gate_evaluator.VERDICT_FAIL
    unmatched = result["override"]["unmatched_cells"]
    assert unmatched[0]["benchmark"] == "Bench1"
    assert unmatched[0]["reason"] == perf_gate_evaluator.OVERRIDE_UNMATCHED_ABSENT_FROM_BASELINE


def test_rejected_override_exempts_nothing_and_records_the_rejection_reason():
    baseline = _single_gating_baseline()
    candidate = {"bench1": _bench({"m1": _metric_entry(101)})}
    base = {"bench1": _bench({"m1": _metric_entry(100)})}
    override = perf_gate_evaluator.parse_override_trailer("bench1.m1;too short")

    with_override = perf_gate_evaluator.evaluate_run(_record(candidate, base), baseline, override=override)
    without_override = perf_gate_evaluator.evaluate_run(_record(candidate, base), baseline)

    assert with_override["verdict"] == without_override["verdict"] == perf_gate_evaluator.VERDICT_FAIL
    assert with_override["override"]["rejection_reason"] == (
        perf_gate_evaluator.OVERRIDE_REJECTED_JUSTIFICATION_TOO_SHORT
    )
    assert with_override["exempted_cells"] == []


def test_override_unavailability_reason_is_recorded_verbatim_and_exempts_nothing():
    baseline = _single_gating_baseline()
    candidate = {"bench1": _bench({"m1": _metric_entry(101)})}
    base = {"bench1": _bench({"m1": _metric_entry(100)})}
    override = perf_gate_evaluator.parse_override_trailer(
        "", unavailable_reason="trailer-parser-subcommand-missing",
    )

    result = perf_gate_evaluator.evaluate_run(_record(candidate, base), baseline, override=override)

    assert result["verdict"] == perf_gate_evaluator.VERDICT_FAIL
    assert result["exempted_cells"] == []
    assert result["override"]["unavailable_reason"] == "trailer-parser-subcommand-missing"


# --- main(): --exit-nonzero-on-fail with an override ---------------------------


def test_main_exit_nonzero_on_fail_returns_zero_when_override_downgrades_the_only_failing_cell(tmp_path):
    record_path = tmp_path / "record.json"
    _write_json(record_path, _record(
        {"bench1": _bench({"m1": _metric_entry(101)})},
        {"bench1": _bench({"m1": _metric_entry(100)})},
    ))
    baseline_path = tmp_path / "baseline.json"
    _write_json(baseline_path, _single_gating_baseline())

    exit_code = perf_gate_evaluator.main([
        "--record", str(record_path),
        "--baseline", str(baseline_path),
        "--exit-nonzero-on-fail",
        "--override-trailer", "bench1.m1;this justification is long enough to pass",
    ])

    assert exit_code == 0


def test_main_exit_nonzero_on_fail_returns_one_when_override_does_not_name_the_failing_cell(tmp_path):
    record_path = tmp_path / "record.json"
    _write_json(record_path, _record(
        {"bench1": _bench({"m1": _metric_entry(101)})},
        {"bench1": _bench({"m1": _metric_entry(100)})},
    ))
    baseline_path = tmp_path / "baseline.json"
    _write_json(baseline_path, _single_gating_baseline())

    exit_code = perf_gate_evaluator.main([
        "--record", str(record_path),
        "--baseline", str(baseline_path),
        "--exit-nonzero-on-fail",
        "--override-trailer", "unrelated.metric;this justification is long enough to pass",
    ])

    assert exit_code == 1


# --- Task 2: tier, dispersion, drift, contamination, budget, attempts --------


def test_every_cell_carries_baseline_tier_and_null_when_absent():
    baseline = _baseline({
        "bench1": {"m1": _gating_cell(100), "m2": _gating_cell_with_dispersion(100, tier=2)},
    })
    candidate = {"bench1": _bench({"m1": _metric_entry(100), "m2": _metric_entry(100)})}
    base = {"bench1": _bench({"m1": _metric_entry(100), "m2": _metric_entry(100)})}

    result = perf_gate_evaluator.evaluate_run(_record(candidate, base), baseline)

    cells = {cell["metric"]: cell for cell in result["cells"]}
    assert cells["m1"]["tier"] is None
    assert cells["m2"]["tier"] == 2


def test_every_cell_carries_dispersion_figures_and_null_when_absent():
    baseline = _baseline({
        "bench1": {
            "m1": _gating_cell(100),
            "m2": _gating_cell_with_dispersion(100, tier=1, n=120, spread=1.5, cv=0.01, mde_pct=2.0),
        },
    })
    candidate = {"bench1": _bench({"m1": _metric_entry(100), "m2": _metric_entry(100)})}
    base = {"bench1": _bench({"m1": _metric_entry(100), "m2": _metric_entry(100)})}

    result = perf_gate_evaluator.evaluate_run(_record(candidate, base), baseline)

    cells = {cell["metric"]: cell for cell in result["cells"]}
    assert cells["m1"]["baseline_n"] is None
    assert cells["m1"]["baseline_spread"] is None
    assert cells["m1"]["baseline_cv"] is None
    assert cells["m1"]["baseline_mde_pct"] is None
    assert cells["m2"]["baseline_n"] == 120
    assert cells["m2"]["baseline_spread"] == 1.5
    assert cells["m2"]["baseline_cv"] == 0.01
    assert cells["m2"]["baseline_mde_pct"] == 2.0


def test_equal_legs_outside_the_recorded_band_is_informational_drift_and_stays_pass():
    baseline = _baseline({
        "bench1": {"m1": _gating_cell_with_dispersion(250, minimum=200, maximum=200)},
    })
    candidate = {"bench1": _bench({"m1": _metric_entry(250)})}
    base = {"bench1": _bench({"m1": _metric_entry(250)})}

    result = perf_gate_evaluator.evaluate_run(_record(candidate, base), baseline)

    assert result["verdict"] == perf_gate_evaluator.VERDICT_PASS
    assert len(result["drift_cells"]) == 1
    assert result["drift_cells"][0]["informational_drift"] is True


def test_equal_legs_inside_the_recorded_band_is_not_drift():
    baseline = _baseline({
        "bench1": {"m1": _gating_cell_with_dispersion(150, minimum=100, maximum=200)},
    })
    candidate = {"bench1": _bench({"m1": _metric_entry(150)})}
    base = {"bench1": _bench({"m1": _metric_entry(150)})}

    result = perf_gate_evaluator.evaluate_run(_record(candidate, base), baseline)

    assert result["verdict"] == perf_gate_evaluator.VERDICT_PASS
    assert result["drift_cells"] == []
    assert result["cells"][0]["informational_drift"] is False


def test_absent_or_non_numeric_band_never_yields_drift():
    baseline = _baseline({
        "bench1": {"m1": _gating_cell(100)},
        "bench2": {"m1": _gating_cell_with_dispersion(100, minimum="n/a", maximum="n/a")},
    })
    candidate = {
        "bench1": _bench({"m1": _metric_entry(100)}),
        "bench2": _bench({"m1": _metric_entry(100)}),
    }
    base = {
        "bench1": _bench({"m1": _metric_entry(100)}),
        "bench2": _bench({"m1": _metric_entry(100)}),
    }

    result = perf_gate_evaluator.evaluate_run(_record(candidate, base), baseline)

    assert result["drift_cells"] == []


def test_contamination_benchmarks_lists_secondary_flagged_benchmarks_in_sorted_order():
    baseline = _baseline({
        "zeta": {"m1": _gating_cell(100)},
        "alpha": {"m1": _gating_cell(100)},
    })
    windows = [{"secondary_flags": ["steal-nonzero"]}]
    candidate = {
        "zeta": _bench({"m1": _metric_entry(100)}, measurement_windows=windows),
        "alpha": _bench({"m1": _metric_entry(100)}, measurement_windows=windows),
    }
    base = {
        "zeta": _bench({"m1": _metric_entry(100)}),
        "alpha": _bench({"m1": _metric_entry(100)}),
    }

    result = perf_gate_evaluator.evaluate_run(_record(candidate, base), baseline)

    assert result["contamination_benchmarks"] == ["alpha", "zeta"]


def test_budget_mapping_carries_total_declared_budget_and_within_budget():
    baseline = _single_gating_baseline()
    candidate = {"bench1": _bench({"m1": _metric_entry(100)})}
    base = {"bench1": _bench({"m1": _metric_entry(100)})}
    record = _record(candidate, base)
    record["timings"] = {"total": 300.0}

    result = perf_gate_evaluator.evaluate_run(record, baseline)

    assert result["budget"]["total_seconds"] == 300.0
    assert result["budget"]["budget_seconds"] == perf_gate_evaluator.GATE_BUDGET_SECONDS
    assert result["budget"]["within_budget"] is True
    assert result["budget"]["retried_total_seconds"] is None


def test_budget_mapping_carries_the_retried_total_when_a_retry_ran():
    baseline = _single_gating_baseline()
    candidate = {"bench1": _bench({"m1": _metric_entry(100)})}
    base = {"bench1": _bench({"m1": _metric_entry(100)})}
    record = _record(candidate, base)
    record["timings"] = {"total": 900.0}
    record["stages"] = {
        "gate_retry": {"ran": True, "elapsed_seconds": {"candidate": 90.0, "merge_base": 85.0}},
    }

    result = perf_gate_evaluator.evaluate_run(record, baseline)

    assert result["budget"]["within_budget"] is False
    assert result["budget"]["retried_total_seconds"] == 175.0


def test_attempts_rollup_is_empty_for_a_record_carrying_none():
    baseline = _single_gating_baseline()
    candidate = {"bench1": _bench({"m1": _metric_entry(100)})}
    base = {"bench1": _bench({"m1": _metric_entry(100)})}

    result = perf_gate_evaluator.evaluate_run(_record(candidate, base), baseline)

    assert result["attempts"] == []


def test_attempts_rollup_carries_one_entry_per_recorded_attempt():
    baseline = _single_gating_baseline()
    candidate = {"bench1": _bench({"m1": _metric_entry(100)})}
    base = {"bench1": _bench({"m1": _metric_entry(100)})}
    record = _record(candidate, base)
    record["run"]["attempts"] = [
        {"attempt": 1, "verdict": "INCONCLUSIVE", "retried": True},
        {"attempt": 2, "verdict": "PASS", "retried": False},
    ]

    result = perf_gate_evaluator.evaluate_run(record, baseline)

    assert result["attempts"] == [
        {"attempt": 1, "verdict": "INCONCLUSIVE", "retried": True},
        {"attempt": 2, "verdict": "PASS", "retried": False},
    ]


# --- render_summary_markdown: PASS / INCONCLUSIVE / FAIL shapes --------------


def test_render_pass_contains_gating_count_and_budget_and_no_failing_table():
    baseline = _single_gating_baseline()
    candidate = {"bench1": _bench({"m1": _metric_entry(100)})}
    base = {"bench1": _bench({"m1": _metric_entry(100)})}
    result = perf_gate_evaluator.evaluate_run(_record(candidate, base), baseline)

    rendered = perf_gate_evaluator.render_summary_markdown(result)

    assert "Verdict: PASS" in rendered
    assert "Gating cells evaluated: 1" in rendered
    assert "## Budget" in rendered
    assert "## Failing cells" not in rendered


def test_render_inconclusive_names_fired_conditions_lists_cells_and_states_no_block():
    baseline = _single_gating_baseline()
    candidate = {"bench1": _bench({"m1": _inconclusive_entry("insufficient-clean-samples")})}
    base = {"bench1": _bench({"m1": _metric_entry(100)})}
    record = _record(candidate, base)
    record["run"]["attempts"] = [{"attempt": 1, "verdict": "INCONCLUSIVE", "retried": True}]
    result = perf_gate_evaluator.evaluate_run(record, baseline)

    rendered = perf_gate_evaluator.render_summary_markdown(result)

    assert "insufficient-clean-samples: 1" in rendered
    assert "bench1" in rendered and "m1" in rendered
    assert "Retry ran: True" in rendered
    assert "This outcome does not block." in rendered


def test_render_fail_lists_every_failing_cell_with_tier_and_dispersion_and_exempted_table():
    baseline = _baseline({
        "bench1": {"m1": _gating_cell_with_dispersion(100, tier=1, n=50, spread=0.5, cv=0.01, mde_pct=1.0)},
        "bench2": {"m1": _gating_cell_with_dispersion(100, tier=2, n=60, spread=0.6, cv=0.02, mde_pct=2.0)},
    })
    candidate = {
        "bench1": _bench({"m1": _metric_entry(101)}),
        "bench2": _bench({"m1": _metric_entry(102)}),
    }
    base = {
        "bench1": _bench({"m1": _metric_entry(100)}),
        "bench2": _bench({"m1": _metric_entry(100)}),
    }
    override = _accepted_override("bench2.m1", "the second regression is a known and accepted tradeoff")
    result = perf_gate_evaluator.evaluate_run(_record(candidate, base), baseline, override=override)

    rendered = perf_gate_evaluator.render_summary_markdown(result)

    assert rendered.count("| bench1 | m1 |") == 1
    assert "| 1 | 50 | 0.5 | 0.01 | 1.0 |" in rendered
    assert "## Exempted cells" in rendered
    assert "the second regression is a known and accepted tradeoff" in rendered


def test_render_accepted_override_shows_justification_and_author_even_on_pass():
    # A doc-only pull request naming a cell that never actually failed still lands the
    # justification and author in the step summary: the must-have does not say "only on
    # FAIL" (confirmed against a real hosted run, PR ruck314/rogue#2, where the named cell
    # was gating-but-not-failing and the run verdict was PASS).
    baseline = _single_gating_baseline()
    candidate = {"bench1": _bench({"m1": _metric_entry(100)})}
    base = {"bench1": _bench({"m1": _metric_entry(100)})}
    override = _accepted_override("bench1.m1", "naming a cell that this doc-only commit cannot move")

    result = perf_gate_evaluator.evaluate_run(_record(candidate, base), baseline, override=override)
    rendered = perf_gate_evaluator.render_summary_markdown(result)

    assert result["verdict"] == perf_gate_evaluator.VERDICT_PASS
    assert "## Escape hatch" in rendered
    assert "naming a cell that this doc-only commit cannot move" in rendered
    assert "gating-but-not-failing" in rendered


def test_render_accepted_override_shows_justification_and_author_on_inconclusive():
    baseline = _baseline({
        "bench1": {"m1": _gating_cell(100)},
        "bench2": {"m1": _gating_cell(100)},
    })
    candidate = {
        "bench1": _bench({"m1": _metric_entry(100)}),
        "bench2": _bench({"m1": _inconclusive_entry("insufficient-clean-samples")}),
    }
    base = {
        "bench1": _bench({"m1": _metric_entry(100)}),
        "bench2": _bench({"m1": _metric_entry(100)}),
    }
    override = _accepted_override("bench1.m1", "naming a cell unrelated to the inconclusive one")

    result = perf_gate_evaluator.evaluate_run(_record(candidate, base), baseline, override=override)
    rendered = perf_gate_evaluator.render_summary_markdown(result)

    assert result["verdict"] == perf_gate_evaluator.VERDICT_INCONCLUSIVE
    assert "## Escape hatch" in rendered
    assert "naming a cell unrelated to the inconclusive one" in rendered


def test_render_report_only_fail_states_would_block_and_pass_inconclusive_do_not():
    baseline = _single_gating_baseline()
    fail_candidate = {"bench1": _bench({"m1": _metric_entry(101)})}
    base = {"bench1": _bench({"m1": _metric_entry(100)})}
    fail_result = perf_gate_evaluator.evaluate_run(_record(fail_candidate, base), baseline)
    fail_rendered = perf_gate_evaluator.render_summary_markdown(fail_result, report_only=True)
    assert "would have blocked" in fail_rendered

    pass_candidate = {"bench1": _bench({"m1": _metric_entry(100)})}
    pass_result = perf_gate_evaluator.evaluate_run(_record(pass_candidate, base), baseline)
    pass_rendered = perf_gate_evaluator.render_summary_markdown(pass_result, report_only=True)
    assert "would have blocked" not in pass_rendered

    inconclusive_candidate = {"bench1": _bench({"m1": _inconclusive_entry("insufficient-clean-samples")})}
    inconclusive_result = perf_gate_evaluator.evaluate_run(_record(inconclusive_candidate, base), baseline)
    inconclusive_rendered = perf_gate_evaluator.render_summary_markdown(inconclusive_result, report_only=True)
    assert "would have blocked" not in inconclusive_rendered


def test_render_summary_markdown_is_deterministic_over_the_same_evaluation_with_new_fields():
    baseline = _single_gating_baseline()
    candidate = {"bench1": _bench({"m1": _metric_entry(101)})}
    base = {"bench1": _bench({"m1": _metric_entry(100)})}
    result = perf_gate_evaluator.evaluate_run(_record(candidate, base), baseline)

    first = perf_gate_evaluator.render_summary_markdown(result)
    second = perf_gate_evaluator.render_summary_markdown(result)

    assert first == second


def test_render_fail_with_128_failing_cells_stays_well_under_one_mebibyte():
    cells = {f"m{i}": _gating_cell(100) for i in range(128)}
    baseline = _baseline({"bench1": cells})
    candidate_metrics = {f"m{i}": _metric_entry(101) for i in range(128)}
    base_metrics = {f"m{i}": _metric_entry(100) for i in range(128)}
    candidate = {"bench1": _bench(candidate_metrics)}
    base = {"bench1": _bench(base_metrics)}

    result = perf_gate_evaluator.evaluate_run(_record(candidate, base), baseline)
    assert len(result["failing_cells"]) == 128

    rendered = perf_gate_evaluator.render_summary_markdown(result)

    assert len(rendered.encode("utf-8")) < 1024 * 1024


# --- render_summary_markdown: the perf documentation pointer -----------------


def test_render_fail_points_at_the_perf_documentation():
    baseline = _single_gating_baseline()
    candidate = {"bench1": _bench({"m1": _metric_entry(101)})}
    base = {"bench1": _bench({"m1": _metric_entry(100)})}
    result = perf_gate_evaluator.evaluate_run(_record(candidate, base), baseline)

    rendered = perf_gate_evaluator.render_summary_markdown(result)

    assert result["verdict"] == perf_gate_evaluator.VERDICT_FAIL
    assert perf_gate_evaluator.DOC_POINTER_LINE in rendered


def test_render_pass_carries_no_documentation_pointer():
    baseline = _single_gating_baseline()
    candidate = {"bench1": _bench({"m1": _metric_entry(100)})}
    base = {"bench1": _bench({"m1": _metric_entry(100)})}
    result = perf_gate_evaluator.evaluate_run(_record(candidate, base), baseline)

    rendered = perf_gate_evaluator.render_summary_markdown(result)

    assert result["verdict"] == perf_gate_evaluator.VERDICT_PASS
    assert perf_gate_evaluator.PERF_DOC_PATH not in rendered


def test_render_inconclusive_points_at_the_perf_documentation():
    baseline = _single_gating_baseline()
    candidate = {"bench1": _bench({"m1": _inconclusive_entry("insufficient-clean-samples")})}
    base = {"bench1": _bench({"m1": _metric_entry(100)})}
    result = perf_gate_evaluator.evaluate_run(_record(candidate, base), baseline)

    rendered = perf_gate_evaluator.render_summary_markdown(result)

    assert result["verdict"] == perf_gate_evaluator.VERDICT_INCONCLUSIVE
    assert perf_gate_evaluator.DOC_POINTER_LINE in rendered


# --- render_summary_markdown: the rejected-override escape hatch -------------


def test_render_rejected_override_shows_the_rejection_reason_and_raw_trailer():
    baseline = _single_gating_baseline()
    candidate = {"bench1": _bench({"m1": _metric_entry(101)})}
    base = {"bench1": _bench({"m1": _metric_entry(100)})}
    override = perf_gate_evaluator.parse_override_trailer("bench1.m1;too short", author="Test Author")
    assert override["status"] == perf_gate_evaluator.OVERRIDE_STATUS_REJECTED

    result = perf_gate_evaluator.evaluate_run(_record(candidate, base), baseline, override=override)
    rendered = perf_gate_evaluator.render_summary_markdown(result)

    assert "## Escape hatch" in rendered
    assert "Status: rejected" in rendered
    assert perf_gate_evaluator.OVERRIDE_REJECTED_JUSTIFICATION_TOO_SHORT in rendered
    assert "Test Author" in rendered
    assert "bench1.m1;too short" in rendered


def test_render_rejected_override_raw_trailer_stays_on_one_line_and_is_bounded():
    # The embedded backtick (mid-way through the "x" run) is the one input shape that
    # actually exercises backtick neutralization: without it, `trailer_line.count("`") == 2`
    # below is satisfied trivially by the renderer's own two wrapping backticks regardless of
    # whether embedded backticks are handled at all.
    raw_value = (
        "bad!token;" + ("x" * 15) + "`" + ("x" * 14) + "\n## Fake heading\n" + ("y" * 200)
    )
    override = perf_gate_evaluator.parse_override_trailer(raw_value, author="Test Author")
    assert override["status"] == perf_gate_evaluator.OVERRIDE_STATUS_REJECTED
    assert override["rejection_reason"] == perf_gate_evaluator.OVERRIDE_REJECTED_MALFORMED_CELL_TOKEN

    baseline = _single_gating_baseline()
    candidate = {"bench1": _bench({"m1": _metric_entry(101)})}
    base = {"bench1": _bench({"m1": _metric_entry(100)})}
    result = perf_gate_evaluator.evaluate_run(_record(candidate, base), baseline, override=override)
    rendered = perf_gate_evaluator.render_summary_markdown(result)

    assert rendered.count("## Condition counts") == 1
    trailer_line = next(
        line for line in rendered.splitlines() if line.startswith("Trailer as written:")
    )
    assert "\n" not in trailer_line
    assert "## Fake heading" in trailer_line
    assert "(truncated)" in trailer_line
    assert trailer_line.count("`") == 2


def test_render_accepted_override_justification_stays_on_one_line_and_is_bounded():
    baseline = _single_gating_baseline()
    candidate = {"bench1": _bench({"m1": _metric_entry(101)})}
    base = {"bench1": _bench({"m1": _metric_entry(100)})}
    justification = (
        "this justification breaks structure\n"
        "## INJECTED HEADING\n"
        "| a | b |\n"
        "|---|---|\n"
        "| 1 | 2 |\n"
        + ("z" * 600)
    )
    override = _accepted_override("bench1.m1", justification)

    result = perf_gate_evaluator.evaluate_run(_record(candidate, base), baseline, override=override)
    rendered = perf_gate_evaluator.render_summary_markdown(result)

    lines = rendered.splitlines()
    justification_line = next(line for line in lines if line.startswith("Justification:"))
    assert "\n" not in justification_line
    assert "(truncated)" in justification_line
    assert "## INJECTED HEADING" in justification_line

    other_lines = [line.strip() for line in lines if line is not justification_line]
    assert "## INJECTED HEADING" not in other_lines
    assert "| a | b |" not in other_lines
    assert rendered.count("## Condition counts") == 1


def test_render_accepted_override_justification_neutralizes_embedded_backticks():
    baseline = _single_gating_baseline()
    candidate = {"bench1": _bench({"m1": _metric_entry(101)})}
    base = {"bench1": _bench({"m1": _metric_entry(100)})}
    justification = (
        "this justification breaks structure\n"
        "## INJECTED HEADING\n"
        "| a | b |\n"
        "|---|---|\n"
        "| 1 | 2 |\n"
        "a `sneaky` inline code span\n"
        + ("z" * 600)
    )
    override = _accepted_override("bench1.m1", justification)

    result = perf_gate_evaluator.evaluate_run(_record(candidate, base), baseline, override=override)
    rendered = perf_gate_evaluator.render_summary_markdown(result)

    lines = rendered.splitlines()
    justification_line = next(line for line in lines if line.startswith("Justification:"))
    assert "\n" not in justification_line
    assert "(truncated)" in justification_line
    assert "`" not in justification_line

    other_lines = [line.strip() for line in lines if line is not justification_line]
    assert "## INJECTED HEADING" not in other_lines
    assert "| a | b |" not in other_lines
    assert rendered.count("## Condition counts") == 1


def test_render_accepted_override_body_is_unchanged_by_the_rejected_branch():
    baseline = _single_gating_baseline()
    candidate = {"bench1": _bench({"m1": _metric_entry(101)})}
    base = {"bench1": _bench({"m1": _metric_entry(100)})}
    override = _accepted_override("bench1.m1", "naming a cell that this doc-only commit cannot move")

    result = perf_gate_evaluator.evaluate_run(_record(candidate, base), baseline, override=override)
    rendered = perf_gate_evaluator.render_summary_markdown(result)

    assert "## Escape hatch" in rendered
    assert "Justification: naming a cell that this doc-only commit cannot move" in rendered
    assert "Author: n/a" in rendered
    assert "Matched (exempted) cells: bench1.m1" in rendered
    assert "Status: rejected" not in rendered
    assert "Rejection reason:" not in rendered


# --- the single mirrored budget declaration -----------------------------------


def test_gate_budget_seconds_is_mirrored_by_the_validation_report_module():
    validation_report = importlib.import_module("perf_gate_validation_report")
    assert validation_report.DEFAULT_BUDGET_SECONDS == perf_gate_evaluator.GATE_BUDGET_SECONDS == 600.0
