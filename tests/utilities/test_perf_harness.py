# ----------------------------------------------------------------------------
# Title      : Perf Harness Tests
# ----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
# ----------------------------------------------------------------------------

"""Unit tests for tests/perf/_perf_harness.py and scripts/perf_tier_registry.py,
injecting fake counter readers so both are unit-testable without a Rogue
build, exactly as the seven scripts/probe_*.py modules are tested today.
"""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

import pytest

# tests/perf/ is not a regular package reachable as `tests.perf` on every machine: some
# environments have a stray top-level `tests` regular package installed system-wide (from an
# unrelated third-party package), which shadows this repository's own `tests/` namespace
# package ahead of it in Python's import-precedence rules regardless of sys.path order.
# Reached instead through the same insert-then-import
# convention its 16 tests/utilities/ siblings use (e.g. test_perf_noise_report.py,
# test_perf_tools.py), which is locally runnable everywhere the cross-package import is not.
REPO_ROOT = Path(__file__).resolve().parents[2]
PERF_DIR = REPO_ROOT / "tests" / "perf"
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(PERF_DIR) not in sys.path:
    sys.path.insert(0, str(PERF_DIR))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

_perf_harness = importlib.import_module("_perf_harness")
perf_tier_registry = importlib.import_module("perf_tier_registry")


def test_tier_for_transaction_lock_acquisitions_is_a_valid_tier():
    # Relaxed from a pinned TIER_1 assertion to a structural one: a real 24-run
    # campaign (docs/plans/perf-ci-hardening/CAMPAIGN-REPORT.md, Cross-CPU-model invariance
    # section) found transaction_lock_acquisitions is not bit-identical across the 4 observed
    # CPU models (spread 0-2000) and demoted it to TIER_2 in a binding-tier update. Pinning
    # a specific tier here would make this test re-fail on every future campaign that
    # legitimately changes the binding tier; only tier_for's structural contract (a valid,
    # resolvable tier) is asserted going forward. See
    # tests/utilities/test_perf_tier_registry.py's identically-motivated relaxation.
    assert perf_tier_registry.tier_for("transaction_lock_acquisitions") in (
        perf_tier_registry.TIER_1, perf_tier_registry.TIER_2, perf_tier_registry.TIER_3,
    )


def test_validate_registry_raises_on_duplicate_metric_name():
    descriptor = {
        "tier": perf_tier_registry.TIER_1,
        "direction": perf_tier_registry.DIRECTION_INVARIANT,
        "comparison": perf_tier_registry.COMPARISON_BIT_IDENTICAL,
        "calibration_pairing": perf_tier_registry.CALIBRATION_NONE,
        "unit": "count",
        "family": "mutex_acquisitions",
        "source": "rogue.PerfCounters.getTransactionLockCount",
        "benchmarks": ("remoteSetRate",),
    }
    duplicated_entries = (
        ("transaction_lock_acquisitions", descriptor),
        ("transaction_lock_acquisitions", descriptor),
    )
    with pytest.raises(perf_tier_registry.RegistryError):
        perf_tier_registry.validate_registry(duplicated_entries)


def test_validate_registry_raises_on_unknown_tier():
    bad_entries = (
        ("bogus_metric", {
            "tier": "not-a-real-tier",
            "direction": perf_tier_registry.DIRECTION_INVARIANT,
            "comparison": perf_tier_registry.COMPARISON_BIT_IDENTICAL,
            "calibration_pairing": perf_tier_registry.CALIBRATION_NONE,
            "unit": "count",
            "family": "mutex_acquisitions",
            "source": "rogue.PerfCounters.getTransactionLockCount",
            "benchmarks": ("remoteSetRate",),
        }),
    )
    with pytest.raises(perf_tier_registry.RegistryError):
        perf_tier_registry.validate_registry(bad_entries)


def test_median_and_mad_never_returns_a_bare_mean():
    median, mad = _perf_harness.median_and_mad([1.0, 2.0, 3.0, 4.0, 100.0])
    # Mean would be 22.0; the median absolute deviation construction must
    # never collapse to it.
    assert median == 3.0
    assert mad == 1.0


def test_counter_deltas_flags_a_decreasing_counter_as_regressed():
    # A monotonic counter that reads lower after the measured region than
    # before it is an anomaly: it must be reported as COUNTER_REGRESSED,
    # never as a bare negative delta (here the naive after-before is -2).
    after = {"a": 3}
    before = {"a": 5}
    assert _perf_harness.counter_deltas(after, before) == {"a": _perf_harness.COUNTER_REGRESSED}


def test_counter_deltas_returns_a_plain_int_for_an_increasing_counter():
    after = {"a": 5}
    before = {"a": 3}
    assert _perf_harness.counter_deltas(after, before) == {"a": 2}


def test_within_run_repeatability_bit_identical():
    result = _perf_harness.within_run_repeatability([7, 7, 7, 7, 7])
    assert result["verdict"] == _perf_harness.VERDICT_BIT_IDENTICAL


def test_within_run_repeatability_unstable_carries_min_max_spread():
    result = _perf_harness.within_run_repeatability([7, 7, 8, 7, 7])
    assert result["verdict"] == _perf_harness.VERDICT_UNSTABLE
    assert result["min"] == 7
    assert result["max"] == 8
    assert result["spread"] == 1


def test_within_run_repeatability_insufficient_below_two_samples():
    result = _perf_harness.within_run_repeatability([7])
    assert result["verdict"] == _perf_harness.INSUFFICIENT_SAMPLES


def test_snapshot_counters_reads_every_reader():
    readers = {"a": lambda: 1, "b": lambda: 2}
    assert _perf_harness.snapshot_counters(readers) == {"a": 1, "b": 2}


def test_measure_benchmark_reports_tier_candidate_and_five_clean_samples():
    counts = {"transaction_lock_acquisitions": 0}

    def workload():
        counts["transaction_lock_acquisitions"] += 1

    def reader():
        return counts["transaction_lock_acquisitions"]

    metrics = _perf_harness.measure_benchmark(
        "remoteSetRate", workload, {"transaction_lock_acquisitions": reader},
    )
    entry = metrics["transaction_lock_acquisitions"]
    # Reads the live registry rather than pinning TIER_1 literally: this test exercises
    # tier_candidate stamping from a constant-count series, not any tier-specific routing
    # behavior (a constant series produces the same rejected_samples/n_clean/median outcome
    # whichever path it routes through), so it must not re-fail every time a real campaign
    # legitimately changes this metric's binding tier (see test_tier_for_transaction_lock_
    # acquisitions_is_a_valid_tier's identical reasoning).
    assert entry["tier_candidate"] == perf_tier_registry.tier_for("transaction_lock_acquisitions")
    assert entry["n_clean"] == _perf_harness.DEFAULT_TARGET_CLEAN_SAMPLES
    assert len(entry["samples"]) == _perf_harness.DEFAULT_TARGET_CLEAN_SAMPLES
    assert entry["status"] == _perf_harness.STATUS_OK
    assert entry["median"] == 1.0


def _quiet_window_sampler(label, fn):
    """A fake window_sampler with no steal/cgroup contamination, so guard and
    rejection tests exercise only the behaviour under test."""
    result = fn()
    return {
        "label": label,
        "wall_seconds": 0.0,
        "steal_jiffies_delta": 0,
        "cgroup_nr_throttled_delta": 0,
        "result": result,
    }


def _sequenced_reader(values):
    """A counter reader returning the next value from `values` on each call,
    so a test can script an exact before/after delta sequence."""
    iterator = iter(values)
    return lambda: next(iterator)


# -- mad_band_rejections() (primary contamination detector) ---------------------------------


def test_mad_band_rejections_flags_exactly_the_outlier():
    assert _perf_harness.mad_band_rejections([10.0, 10.1, 9.9, 10.0, 50.0]) == [4]


def test_mad_band_rejections_flags_none_when_every_sample_is_identical():
    assert _perf_harness.mad_band_rejections([10.0, 10.0, 10.0, 10.0, 10.0]) == []


# -- contamination rejection is routed by metric kind, never uniformly ----------------------


def test_measure_benchmark_rejects_a_mad_band_outlier_for_a_continuous_metric():
    # avg_ns is a registered Tier 3 continuous metric. Ten sequential snapshot reads (before,
    # after per repeat) produce the five deltas 100,100,100,100,4600.
    reader = _sequenced_reader([0, 100, 100, 200, 200, 300, 300, 400, 400, 5000])
    metrics = _perf_harness.measure_benchmark(
        "remoteSetRate", lambda: None, {"avg_ns": reader}, window_sampler=_quiet_window_sampler,
    )
    entry = metrics["avg_ns"]
    assert entry["rejected_samples"] == [
        {"index": 4, "value": 4600.0, "reason": _perf_harness.REJECTION_MAD_BAND},
    ]
    assert 4600.0 not in entry["samples"]
    assert entry["n_clean"] == 4


def test_measure_benchmark_never_mad_band_rejects_a_tier1_count_demotes_instead():
    # A single differing count among five Tier 1 repeats must produce a tier
    # verdict (demotion), never a rejected sample: rejecting it would smooth
    # away exactly the nondeterminism that disqualifies the Tier 1 candidate.
    # Ten sequential snapshot reads produce the five deltas 1,1,2,1,1.
    #
    # Uses prbs_rx_count rather than transaction_lock_acquisitions: this test exercises the
    # Tier-1-specific within_run_repeatability routing path itself (measure_benchmark reads
    # the live registry's tier to decide bit-identical-vs-mad-band routing), so it needs a
    # metric the post-campaign registry still binds at TIER_1. Plan 03-09's real campaign
    # (docs/plans/perf-ci-hardening/CAMPAIGN-REPORT.md) demoted transaction_lock_acquisitions
    # to TIER_2, but found prbs_rx_count bit-identical across all 4 observed CPU models, so it
    # remains a genuine TIER_1/COMPARISON_BIT_IDENTICAL registry entry this test can rely on.
    reader = _sequenced_reader([0, 1, 1, 2, 2, 4, 4, 5, 5, 6])
    metrics = _perf_harness.measure_benchmark(
        "remoteSetRate", lambda: None, {"prbs_rx_count": reader},
        window_sampler=_quiet_window_sampler,
    )
    entry = metrics["prbs_rx_count"]
    assert entry["rejected_samples"] == []
    assert entry["tier_demoted_to"] == perf_tier_registry.TIER_2
    assert entry["demotion_reason"] == _perf_harness.DEMOTED_TO_TIER_2
    assert entry["min"] == 1
    assert entry["max"] == 2
    assert entry["spread"] == 1
    assert entry["status"] == _perf_harness.STATUS_OK


# -- INCONCLUSIVE: no median/mad key at all, never a null one -------------------------------


def test_measure_benchmark_reports_inconclusive_with_no_median_or_mad_key():
    # Ten sequential snapshot reads produce the five deltas 100,100,100,30000,60300; a MAD of
    # exactly zero from the three tied 100s means both large deltas fall outside the
    # (zero-width) band, dropping n_clean to 3, below DEFAULT_TARGET_CLEAN_SAMPLES.
    reader = _sequenced_reader([0, 100, 100, 200, 200, 300, 300, 30300, 30300, 90600])
    metrics = _perf_harness.measure_benchmark(
        "remoteSetRate", lambda: None, {"avg_ns": reader}, window_sampler=_quiet_window_sampler,
    )
    entry = metrics["avg_ns"]
    assert entry["status"] == _perf_harness.STATUS_INCONCLUSIVE
    assert entry["reason"] == _perf_harness.REASON_INSUFFICIENT_CLEAN_SAMPLES
    assert "median" not in entry
    assert "mad" not in entry


def test_measure_benchmark_guard_exceeded_reports_inconclusive_with_guard_reason():
    clock_values = iter([0.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0])
    reader = _sequenced_reader(range(20))
    metrics = _perf_harness.measure_benchmark(
        "remoteSetRate", lambda: None, {"avg_ns": reader},
        guard_seconds=1.0, clock=lambda: next(clock_values), window_sampler=_quiet_window_sampler,
    )
    entry = metrics["avg_ns"]
    assert entry["status"] == _perf_harness.STATUS_INCONCLUSIVE
    assert entry["reason"] == _perf_harness.REASON_GUARD_EXCEEDED
    assert entry["n_clean"] < _perf_harness.DEFAULT_TARGET_CLEAN_SAMPLES


# -- steal/cgroup secondary flags, recorded regardless of whether MAD-band fired ------------


def test_measure_benchmark_records_secondary_flags_from_a_contaminated_window():
    def contaminated_window_sampler(label, fn):
        result = fn()
        return {
            "label": label,
            "wall_seconds": 0.0,
            "steal_jiffies_delta": 5,
            "cgroup_nr_throttled_delta": 2,
            "result": result,
        }

    reader = _sequenced_reader([0, 1, 1, 2, 2, 3, 3, 4, 4, 5])
    metrics = _perf_harness.measure_benchmark(
        "remoteSetRate", lambda: None, {"transaction_lock_acquisitions": reader},
        window_sampler=contaminated_window_sampler,
    )
    windows = metrics[_perf_harness.MEASUREMENT_WINDOWS_KEY]
    assert len(windows) == _perf_harness.DEFAULT_TARGET_CLEAN_SAMPLES
    for window in windows:
        assert _perf_harness.REJECTION_STEAL_NONZERO in window["secondary_flags"]
        assert _perf_harness.REJECTION_CGROUP_THROTTLED in window["secondary_flags"]


def test_measure_benchmark_records_no_secondary_flags_from_a_clean_window():
    reader = _sequenced_reader([0, 1, 1, 2, 2, 3, 3, 4, 4, 5])
    metrics = _perf_harness.measure_benchmark(
        "remoteSetRate", lambda: None, {"transaction_lock_acquisitions": reader},
        window_sampler=_quiet_window_sampler,
    )
    windows = metrics[_perf_harness.MEASUREMENT_WINDOWS_KEY]
    assert all(window["secondary_flags"] == [] for window in windows)


# -- structural enforcement: never a bare mean -----------------------------------------------


def test_perf_harness_module_never_calls_a_bare_mean():
    source = Path(_perf_harness.__file__).read_text()
    for line in source.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        assert "statistics.mean(" not in stripped
        assert "statistics.fmean(" not in stripped


# -- derived constants carry a paired derivation string --------------------------------------


def test_every_derived_constant_carries_a_derivation_string():
    assert len(_perf_harness.MAD_BAND_DERIVATION.strip()) > 0
    assert len(_perf_harness.STEAL_DELTA_THRESHOLD_DERIVATION.strip()) > 0
    assert len(_perf_harness.GUARD_SECONDS_DERIVATION.strip()) > 0
    assert len(_perf_harness.TARGET_CLEAN_SAMPLES_DERIVATION.strip()) > 0
    assert _perf_harness.MAD_SIGMA_SCALE == 1.4826
    assert _perf_harness.DEFAULT_TARGET_CLEAN_SAMPLES == 5


# -- dual_clock_cpu() (dual-clock CPU accounting) --------------------------------------------


def test_dual_clock_cpu_returns_both_process_and_thread_ns():
    calls = []

    def workload():
        calls.append(1)
        total = 0
        for i in range(1000):
            total += i

    process_ns, thread_ns = _perf_harness.dual_clock_cpu(workload)
    assert calls == [1]
    assert process_ns is not None
    assert thread_ns is not None
    assert process_ns >= 0.0
    assert thread_ns >= 0.0


def test_dual_clock_cpu_returns_neither_on_a_failed_clock_read(monkeypatch):
    def broken_getrusage(_who):
        raise OSError("simulated getrusage failure")

    monkeypatch.setattr(_perf_harness.resource, "getrusage", broken_getrusage)
    process_ns, thread_ns = _perf_harness.dual_clock_cpu(lambda: None)
    assert process_ns is None
    assert thread_ns is None


def test_measure_benchmark_dual_clock_produces_the_four_registered_metrics():
    reader = _sequenced_reader([0, 1, 1, 2, 2, 3, 3, 4, 4, 5])
    metrics = _perf_harness.measure_benchmark(
        "remoteSetRate", lambda: None, {"transaction_lock_acquisitions": reader},
        window_sampler=_quiet_window_sampler, bytes_per_repeat=100, ops_per_repeat=10,
    )
    for name in _perf_harness.DUAL_CLOCK_METRIC_NAMES:
        assert name in metrics
        assert metrics[name]["tier_candidate"] == perf_tier_registry.TIER_2


def test_measure_benchmark_without_dual_clock_args_emits_no_cpu_metrics():
    reader = _sequenced_reader([0, 1, 1, 2, 2, 3, 3, 4, 4, 5])
    metrics = _perf_harness.measure_benchmark(
        "remoteSetRate", lambda: None, {"transaction_lock_acquisitions": reader},
        window_sampler=_quiet_window_sampler,
    )
    for name in _perf_harness.DUAL_CLOCK_METRIC_NAMES:
        assert name not in metrics


# -- derive_microarchitecture() -------------------------------------------------------------


def test_derive_microarchitecture_known_cpu_model(tmp_path):
    cpuinfo = tmp_path / "cpuinfo"
    cpuinfo.write_text(
        "vendor_id\t: AuthenticAMD\n"
        "cpu family\t: 25\n"
        "model\t\t: 1\n"
        "model name\t: AMD EPYC 7763\n"
        "stepping\t: 1\n"
    )
    result = _perf_harness.derive_microarchitecture(cpuinfo)
    assert result["microarchitecture"] == "Zen 3"
    assert result["raw_cpuinfo_fields"]["cpu_family"] == "25"


def test_derive_microarchitecture_unrecognized_cpu_model(tmp_path):
    cpuinfo = tmp_path / "cpuinfo"
    cpuinfo.write_text(
        "vendor_id\t: GenuineIntel\n"
        "cpu family\t: 6\n"
        "model\t\t: 42\n"
        "model name\t: Some Future CPU Nobody Has Seen\n"
        "stepping\t: 2\n"
    )
    result = _perf_harness.derive_microarchitecture(cpuinfo)
    assert result["microarchitecture"] == _perf_harness.env_fingerprint.UNAVAILABLE
    assert result["raw_cpuinfo_fields"]["cpu_family"] == "6"


# -- calibration measurement shape and repeat count ------------------------------------------


def test_build_harness_record_calibration_measurement_shape_states_the_repeat_count():
    record = _perf_harness.build_harness_record(
        "remoteSetRate", {}, {"reduced_size": 1000, "full_size": 100000},
    )
    shape_note = record["environment"]["calibration_measurement_shape"]
    assert str(_perf_harness.DEFAULT_CALIBRATION_REPEATS) in shape_note
    assert "not be compared directly" in shape_note
    for component in perf_tier_registry.CALIBRATION_COMPONENTS:
        repeats = record["environment"]["calibration_vector"]["components"][component]
        if isinstance(repeats, dict):
            assert repeats["repeats"] == _perf_harness.DEFAULT_CALIBRATION_REPEATS


# -- Every backward-compatible metadata field present under a fixed key set -------------------


def test_build_harness_record_metadata_carries_every_fixed_metadata_field():
    record = _perf_harness.build_harness_record(
        "remoteSetRate", {}, {"reduced_size": 1000, "full_size": 100000},
    )
    for field in _perf_harness.FIXED_METADATA_FIELDS:
        assert field in record["environment"]


def test_build_harness_record_steal_jiffies_delta_unavailable_with_no_sampled_windows():
    record = _perf_harness.build_harness_record(
        "remoteSetRate", {}, {"reduced_size": 1000, "full_size": 100000},
    )
    assert record["environment"]["steal_jiffies_delta"] == _perf_harness.env_fingerprint.UNAVAILABLE


def test_build_harness_record_steal_jiffies_delta_sums_sampled_windows():
    reader = _sequenced_reader([0, 1, 1, 2, 2, 3, 3, 4, 4, 5])

    def contaminated_window_sampler(label, fn):
        result = fn()
        return {
            "label": label, "wall_seconds": 0.0,
            "steal_jiffies_delta": 3, "cgroup_nr_throttled_delta": 0,
            "result": result,
        }

    metrics = _perf_harness.measure_benchmark(
        "remoteSetRate", lambda: None, {"transaction_lock_acquisitions": reader},
        window_sampler=contaminated_window_sampler,
    )
    record = _perf_harness.build_harness_record(
        "remoteSetRate", metrics, {"reduced_size": 1000, "full_size": 100000},
    )
    assert record["environment"]["steal_jiffies_delta"] == 3 * _perf_harness.DEFAULT_TARGET_CLEAN_SAMPLES
    assert len(record["benchmarks"]["remoteSetRate"]["measurement_windows"]) == (
        _perf_harness.DEFAULT_TARGET_CLEAN_SAMPLES
    )
    assert _perf_harness.MEASUREMENT_WINDOWS_KEY not in record["benchmarks"]["remoteSetRate"]["metrics"]


def test_build_harness_record_per_unit_work_normalization_for_count_metrics():
    reader = _sequenced_reader([0, 1, 1, 2, 2, 3, 3, 4, 4, 5])
    metrics = _perf_harness.measure_benchmark(
        "remoteSetRate", lambda: None, {"transaction_lock_acquisitions": reader},
        window_sampler=_quiet_window_sampler,
    )
    record = _perf_harness.build_harness_record(
        "remoteSetRate", metrics, {"reduced_size": 1000, "full_size": 100000},
    )
    entry = record["benchmarks"]["remoteSetRate"]["metrics"]["transaction_lock_acquisitions"]
    assert entry["per_unit_work"] == entry["median"] / 1000


def test_build_harness_record_top_level_keys_are_exact():
    record = _perf_harness.build_harness_record(
        "remoteSetRate",
        {
            "transaction_lock_acquisitions": {
                "samples": [1, 1, 1, 1, 1],
                "median": 1.0,
                "mad": 0.0,
                "n_clean": 5,
                "tier_candidate": perf_tier_registry.TIER_1,
                "within_run_repeatability": {"verdict": _perf_harness.VERDICT_BIT_IDENTICAL, "n": 5},
                "status": _perf_harness.STATUS_OK,
                "reason": None,
            },
        },
        {"reduced_size": 1000, "full_size": 100000},
    )
    assert set(record.keys()) == {
        "harness_schema_version", "run", "environment", "build", "benchmarks", "errors",
    }
    assert record["harness_schema_version"] == _perf_harness.HARNESS_SCHEMA_VERSION
    assert "cpu_model" in record["environment"]
    assert "calibration_vector" in record["environment"]
    assert "microarchitecture" in record["environment"]
    assert record["benchmarks"]["remoteSetRate"]["metrics"]["transaction_lock_acquisitions"]["tier_candidate"] == 1
    assert "git_tree_hash" in record["run"]


def test_emit_harness_result_writes_nothing_when_env_var_unset(monkeypatch, tmp_path):
    monkeypatch.delenv(_perf_harness.HARNESS_RESULTS_DIR_ENV, raising=False)
    record = {"harness_schema_version": 1}
    returned = _perf_harness.emit_harness_result(record, "remoteSetRate")
    assert returned == record
    assert list(tmp_path.iterdir()) == []


def test_emit_harness_result_writes_one_sorted_key_json_file_when_env_var_set(monkeypatch, tmp_path):
    monkeypatch.setenv(_perf_harness.HARNESS_RESULTS_DIR_ENV, str(tmp_path))
    record = {"b": 2, "a": 1}
    _perf_harness.emit_harness_result(record, "remoteSetRate")
    written = list(tmp_path.iterdir())
    assert len(written) == 1
    text = written[0].read_text()
    assert text == json.dumps(record, indent=2, sort_keys=True) + "\n"
