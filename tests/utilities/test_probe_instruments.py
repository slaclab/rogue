# ----------------------------------------------------------------------------
# Title      : Probe Instruments Tests
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
import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

probe_instruments = importlib.import_module("probe_instruments")
env_fingerprint = importlib.import_module("env_fingerprint")
perf_noise_report = importlib.import_module("perf_noise_report")


def _completed(argv, returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(argv, returncode=returncode, stdout=stdout, stderr=stderr)


class _ScriptedRunner:
    """An injectable subprocess runner returning canned CompletedProcess
    objects keyed off a predicate over the argv, in registration order.
    Mirrors tests/utilities/test_probe_perf_events.py's _ScriptedRunner:
    every invocation is recorded so tests can assert on the command sequence,
    with no privileged access and no dependence on real tooling.
    """

    def __init__(self, default=None):
        self._rules: list[tuple] = []
        self._default = default if default is not None else _completed([], returncode=0)
        self.calls: list[list[str]] = []

    def when(self, predicate, completed):
        self._rules.append((predicate, completed))
        return self

    def __call__(self, argv):
        self.calls.append(argv)
        for predicate, completed in self._rules:
            if predicate(argv):
                return completed
        return self._default


def _contains(token):
    return lambda argv: any(token in part for part in argv)


class _FakeWindowSampler:
    """Deterministic stand-in for env_fingerprint.sample_cpu_window: still
    calls fn() for its side effects and to capture the real result (so count
    extraction from a CompletedProcess still works), but returns a scripted
    wall_seconds keyed off a predicate over the window label, so an
    overhead-ratio test never depends on real elapsed wall-clock time.
    """

    def __init__(self, default_seconds=1.0):
        self._rules: list[tuple] = []
        self._default_seconds = default_seconds
        self.labels: list[str] = []

    def when(self, predicate, seconds):
        self._rules.append((predicate, seconds))
        return self

    def __call__(self, label, fn):
        self.labels.append(label)
        result = fn()
        seconds = self._default_seconds
        for predicate, value in self._rules:
            if predicate(label):
                seconds = value
                break
        return {"label": label, "wall_seconds": seconds, "result": result}


def _installed_version_runner(package_ok=True, version_text="1.0"):
    runner = _ScriptedRunner(default=_completed([], returncode=0))
    if not package_ok:
        runner.when(_contains("apt-get"), _completed([], returncode=1, stderr="E: Unable to locate package"))
        runner.when(_contains("--version"), _completed([], returncode=1, stderr="not found"))
        runner.when(_contains("-V"), _completed([], returncode=1, stderr="not found"))
    else:
        runner.when(_contains("--version"), _completed([], returncode=0, stdout=version_text))
        runner.when(_contains("-V"), _completed([], returncode=0, stderr=version_text))
    return runner


# ---------------------------------------------------------------------------
# measure_overhead
# ---------------------------------------------------------------------------

def test_measure_overhead_empty_sample_list_returns_insufficient_samples():
    assert probe_instruments.measure_overhead([], [1.0, 1.0]) == perf_noise_report.INSUFFICIENT_SAMPLES
    assert probe_instruments.measure_overhead([1.0, 1.0], []) == perf_noise_report.INSUFFICIENT_SAMPLES


def test_measure_overhead_zero_baseline_returns_unavailable():
    assert probe_instruments.measure_overhead([0.0, 0.0], [1.0, 1.0]) == env_fingerprint.UNAVAILABLE


def test_measure_overhead_non_finite_baseline_returns_unavailable():
    assert probe_instruments.measure_overhead([float("nan"), float("nan")], [1.0]) == env_fingerprint.UNAVAILABLE
    assert probe_instruments.measure_overhead([float("inf"), float("inf")], [1.0]) == env_fingerprint.UNAVAILABLE


def test_measure_overhead_positive_inputs_returns_ratio():
    ratio = probe_instruments.measure_overhead([1.0, 1.0, 1.0], [4.0, 4.0, 4.0])
    assert ratio == 4.0


def test_measure_overhead_never_raises_or_returns_infinity_on_negative_baseline():
    result = probe_instruments.measure_overhead([-1.0, -1.0], [1.0, 1.0])
    assert result == env_fingerprint.UNAVAILABLE


# ---------------------------------------------------------------------------
# repeatability_verdict
# ---------------------------------------------------------------------------

def test_repeatability_verdict_equal_counts_bit_identical():
    verdict = probe_instruments.repeatability_verdict([100, 100, 100])
    assert verdict["verdict"] == probe_instruments.VERDICT_BIT_IDENTICAL
    assert verdict["n"] == 3


def test_repeatability_verdict_unequal_counts_unstable_with_spread():
    verdict = probe_instruments.repeatability_verdict([100, 105, 98])
    assert verdict["verdict"] == probe_instruments.VERDICT_UNSTABLE
    assert verdict["min"] == 98
    assert verdict["max"] == 105
    assert verdict["spread"] == 7


def test_repeatability_verdict_fewer_than_minimum_returns_insufficient_samples():
    verdict = probe_instruments.repeatability_verdict([100, 100])
    assert verdict["verdict"] == perf_noise_report.INSUFFICIENT_SAMPLES
    assert verdict["n"] == 2


def test_repeatability_verdict_single_count_with_repeats_one_is_insufficient_not_bit_identical():
    verdict = probe_instruments.repeatability_verdict([100])
    assert verdict["verdict"] == perf_noise_report.INSUFFICIENT_SAMPLES
    assert verdict["verdict"] != probe_instruments.VERDICT_BIT_IDENTICAL


# ---------------------------------------------------------------------------
# collect_instrument_sweep
# ---------------------------------------------------------------------------

def test_collect_instrument_sweep_orders_entries_by_name():
    runner = _installed_version_runner(package_ok=True)
    sampler = _FakeWindowSampler(default_seconds=1.0)

    entries = probe_instruments.collect_instrument_sweep(
        runner=runner, repeats=3, syscall_iterations=1, alloc_iterations=1,
        alloc_block_bytes=64, window_sampler=sampler,
    )

    names = [entry["name"] for entry in entries]
    assert names == sorted(names)
    assert set(names) == set(probe_instruments.INSTRUMENT_NAMES)


def test_collect_instrument_sweep_identical_multiplier_both_entries_retained():
    runner = _installed_version_runner(package_ok=True)
    sampler = _FakeWindowSampler(default_seconds=1.0)
    sampler.when(_contains("instrumented"), 3.0)

    entries = probe_instruments.collect_instrument_sweep(
        runner=runner, repeats=3, syscall_iterations=1, alloc_iterations=1,
        alloc_block_bytes=64, window_sampler=sampler,
    )

    multipliers = {entry["name"]: entry["overhead_multiplier"] for entry in entries}
    assert len(multipliers) == len(probe_instruments.INSTRUMENT_NAMES)
    assert len(set(multipliers.values())) == 1
    names = [entry["name"] for entry in entries]
    assert names == sorted(names)


def test_collect_instrument_sweep_absent_tool_yields_unavailable_and_continues():
    runner = _installed_version_runner(package_ok=False)
    sampler = _FakeWindowSampler(default_seconds=1.0)

    entries = probe_instruments.collect_instrument_sweep(
        runner=runner, repeats=3, syscall_iterations=1, alloc_iterations=1,
        alloc_block_bytes=64, window_sampler=sampler,
    )

    by_name = {entry["name"]: entry for entry in entries}
    strace_entry = by_name[probe_instruments.INSTRUMENT_STRACE]
    assert strace_entry["available"] is False
    assert strace_entry["verdict"] == probe_instruments.VERDICT_UNAVAILABLE
    assert strace_entry["overhead_multiplier"] == env_fingerprint.UNAVAILABLE
    assert strace_entry["install"]["installed"] is False
    # The sweep continues past the absent tool: every instrument name is present.
    assert set(by_name) == set(probe_instruments.INSTRUMENT_NAMES)


def test_collect_instrument_sweep_records_configured_repeat_count():
    runner = _installed_version_runner(package_ok=True)
    sampler = _FakeWindowSampler(default_seconds=1.0)

    entries = probe_instruments.collect_instrument_sweep(
        runner=runner, repeats=5, syscall_iterations=1, alloc_iterations=1,
        alloc_block_bytes=64, window_sampler=sampler,
    )

    for entry in entries:
        assert entry["repeats"] == 5
        assert len(entry["baseline_seconds"]) == 5
        assert len(entry["instrumented_seconds"]) == 5


# ---------------------------------------------------------------------------
# Output-text parsing helpers
# ---------------------------------------------------------------------------

def test_parse_strace_total_calls_extracts_calls_column_with_errors_column():
    text = (
        "% time     seconds  usecs/call     calls    errors syscall\n"
        "------ ----------- ----------- --------- --------- ----------------\n"
        " 50.00    0.000050           1        50           getppid\n"
        "------ ----------- ----------- --------- --------- ----------------\n"
        "100.00    0.000100           2        50         0 total\n"
    )
    assert probe_instruments._parse_strace_total_calls(text) == 50


def test_parse_strace_total_calls_extracts_calls_column_without_errors_column():
    text = "100.00    0.000100           2        75 total\n"
    assert probe_instruments._parse_strace_total_calls(text) == 75


def test_parse_strace_total_calls_returns_none_when_absent():
    assert probe_instruments._parse_strace_total_calls("no summary here\n") is None


def test_parse_callgrind_collected_extracts_instruction_count():
    text = "==123== Events    : Ir\n==123== Collected : 56846197\n"
    assert probe_instruments._parse_callgrind_collected(text) == 56846197


def test_parse_callgrind_collected_returns_none_when_absent():
    assert probe_instruments._parse_callgrind_collected("no summary here\n") is None


def test_read_interposer_dump_parses_key_value_lines(tmp_path):
    dump_path = tmp_path / "alloc_counts.txt"
    dump_path.write_text("malloc_calls 42\nfree_calls 40\nbytes_requested 1024\n")
    counts = probe_instruments._read_interposer_dump(dump_path)
    assert counts == {"malloc_calls": 42, "free_calls": 40, "bytes_requested": 1024}


def test_read_interposer_dump_returns_none_when_file_missing(tmp_path):
    assert probe_instruments._read_interposer_dump(tmp_path / "missing.txt") is None


def test_measure_malloc_interposer_build_failure_yields_unavailable():
    runner = _ScriptedRunner(default=_completed([], returncode=0))
    runner.when(_contains("build_malloc_interposer.sh"), _completed([], returncode=1, stderr="cc1: fatal error"))
    sampler = _FakeWindowSampler(default_seconds=1.0)

    entry = probe_instruments._measure_malloc_interposer(
        runner=runner, repeats=3, iterations=1, block_bytes=64, window_sampler=sampler,
    )

    assert entry["available"] is False
    assert entry["verdict"] == probe_instruments.VERDICT_UNAVAILABLE
    assert entry["install"]["built"] is False


# ---------------------------------------------------------------------------
# _apply_verdict: the graded per-instrument verdict
# ---------------------------------------------------------------------------

def _measured_entry(*, available=True, repeatability_verdict, overhead_multiplier):
    return {
        "name": "fake",
        "available": available,
        "install": {"installed": available},
        "repeats": 3,
        "baseline_seconds": [1.0, 1.0, 1.0],
        "instrumented_seconds": [1.0, 1.0, 1.0],
        "counts": [],
        "overhead_multiplier": overhead_multiplier,
        "repeatability": repeatability_verdict,
        "verdict": None,
        "verdict_reason": None,
    }


def test_apply_verdict_bit_identical_low_overhead_is_usable():
    entry = _measured_entry(
        repeatability_verdict={"verdict": probe_instruments.VERDICT_BIT_IDENTICAL, "n": 3},
        overhead_multiplier=1.2,
    )
    probe_instruments._apply_verdict(entry)
    assert entry["verdict"] == probe_instruments.VERDICT_USABLE
    assert entry["overhead_disqualify_threshold"] == probe_instruments.OVERHEAD_DISQUALIFY_MULTIPLIER


def test_apply_verdict_bit_identical_excessive_overhead_is_overhead_disqualifies():
    entry = _measured_entry(
        repeatability_verdict={"verdict": probe_instruments.VERDICT_BIT_IDENTICAL, "n": 3},
        overhead_multiplier=probe_instruments.OVERHEAD_DISQUALIFY_MULTIPLIER + 1.0,
    )
    probe_instruments._apply_verdict(entry)
    assert entry["verdict"] == probe_instruments.VERDICT_OVERHEAD_DISQUALIFIES
    assert entry["overhead_disqualify_threshold"] == probe_instruments.OVERHEAD_DISQUALIFY_MULTIPLIER


def test_apply_verdict_unstable_count_is_count_unstable_even_with_low_overhead():
    entry = _measured_entry(
        repeatability_verdict={"verdict": probe_instruments.VERDICT_UNSTABLE, "n": 3, "min": 1, "max": 2, "spread": 1},
        overhead_multiplier=1.0,
    )
    probe_instruments._apply_verdict(entry)
    assert entry["verdict"] == probe_instruments.VERDICT_COUNT_UNSTABLE


def test_apply_verdict_unavailable_short_circuits_other_checks():
    entry = _measured_entry(
        available=False,
        repeatability_verdict={"verdict": probe_instruments.VERDICT_UNSTABLE, "n": 3, "min": 1, "max": 2, "spread": 1},
        overhead_multiplier=probe_instruments.OVERHEAD_DISQUALIFY_MULTIPLIER + 1.0,
    )
    probe_instruments._apply_verdict(entry)
    assert entry["verdict"] == probe_instruments.VERDICT_UNAVAILABLE


# ---------------------------------------------------------------------------
# Zero-dependency in-process counters
# ---------------------------------------------------------------------------

def test_measure_python_tracemalloc_always_present_with_native_blindness_note():
    sampler = _FakeWindowSampler(default_seconds=1.0)
    entry = probe_instruments._measure_python_tracemalloc(
        repeats=3, iterations=5, block_bytes=64, window_sampler=sampler,
    )
    assert entry["available"] is True
    assert "native" in entry["note"]
    assert entry["repeats"] == 3
    assert len(entry["counts"]) == 3


def test_measure_allocator_stats_unresolvable_symbol_returns_unavailable_never_raises():
    sampler = _FakeWindowSampler(default_seconds=1.0)
    entry = probe_instruments._measure_allocator_stats(
        repeats=3, iterations=5, block_bytes=64, window_sampler=sampler, resolve_fn=lambda: None,
    )
    assert entry["available"] is False
    assert entry["verdict"] == probe_instruments.VERDICT_UNAVAILABLE
    assert "reason" in entry["install"]
    assert entry["comparison_note"]


def test_measure_allocator_stats_reports_field_deltas_when_resolved():
    class _FakeMallInfo:
        def __init__(self, uordblks):
            for name, _ in probe_instruments.MallInfo2Struct._fields_:
                setattr(self, name, 0)
            self.uordblks = uordblks

    state = {"n": 0}

    def fake_resolve():
        def fn():
            state["n"] += 1
            return _FakeMallInfo(uordblks=state["n"] * 100)
        return fn

    sampler = _FakeWindowSampler(default_seconds=1.0)
    entry = probe_instruments._measure_allocator_stats(
        repeats=3, iterations=5, block_bytes=64, window_sampler=sampler, resolve_fn=fake_resolve,
    )
    assert entry["available"] is True
    assert len(entry["field_deltas"]) == 3
    assert all("uordblks" in delta for delta in entry["field_deltas"])
    assert entry["comparison_note"]


def test_measure_resource_usage_reports_deltas():
    from types import SimpleNamespace

    state = {"n": 0}

    def fake_getrusage():
        state["n"] += 1
        return SimpleNamespace(ru_minflt=state["n"] * 10, ru_nvcsw=state["n"], ru_nivcsw=0)

    sampler = _FakeWindowSampler(default_seconds=1.0)
    entry = probe_instruments._measure_resource_usage(
        repeats=3, iterations=5, block_bytes=64, window_sampler=sampler, getrusage_fn=fake_getrusage,
    )
    assert entry["available"] is True
    assert len(entry["deltas"]) == 3
    for delta in entry["deltas"]:
        assert "minor_faults" in delta
        assert "voluntary_context_switches" in delta
        assert "involuntary_context_switches" in delta


def test_measure_perf_software_events_uses_shared_parser():
    runner = _installed_version_runner(package_ok=True)
    sampler = _FakeWindowSampler(default_seconds=1.0)

    entry = probe_instruments._measure_perf_software_events(
        runner=runner, repeats=3, iterations=1, window_sampler=sampler,
    )

    assert entry["available"] is True
    assert entry["repeats"] == 3


# ---------------------------------------------------------------------------
# collect_instrument_sweep: full seven-instrument sweep
# ---------------------------------------------------------------------------

def test_collect_instrument_sweep_includes_all_seven_instrument_names():
    assert len(probe_instruments.INSTRUMENT_NAMES) == 7
    expected = {
        probe_instruments.INSTRUMENT_STRACE,
        probe_instruments.INSTRUMENT_MALLOC_INTERPOSER,
        probe_instruments.INSTRUMENT_CALLGRIND,
        probe_instruments.INSTRUMENT_PYTHON_TRACEMALLOC,
        probe_instruments.INSTRUMENT_ALLOCATOR_STATS,
        probe_instruments.INSTRUMENT_RESOURCE_USAGE,
        probe_instruments.INSTRUMENT_PERF_SOFTWARE_EVENTS,
    }
    assert set(probe_instruments.INSTRUMENT_NAMES) == expected


def test_collect_instrument_sweep_malloc_interposer_and_allocator_stats_have_comparison_notes():
    runner = _installed_version_runner(package_ok=True)
    sampler = _FakeWindowSampler(default_seconds=1.0)

    entries = probe_instruments.collect_instrument_sweep(
        runner=runner, repeats=2, syscall_iterations=1, alloc_iterations=1,
        alloc_block_bytes=64, window_sampler=sampler,
    )

    by_name = {entry["name"]: entry for entry in entries}
    assert by_name[probe_instruments.INSTRUMENT_MALLOC_INTERPOSER]["comparison_note"]
    assert by_name[probe_instruments.INSTRUMENT_ALLOCATOR_STATS]["comparison_note"]


def test_collect_instrument_sweep_every_entry_carries_a_graded_verdict():
    runner = _installed_version_runner(package_ok=True)
    sampler = _FakeWindowSampler(default_seconds=1.0)

    entries = probe_instruments.collect_instrument_sweep(
        runner=runner, repeats=2, syscall_iterations=1, alloc_iterations=1,
        alloc_block_bytes=64, window_sampler=sampler,
    )

    valid_verdicts = {
        probe_instruments.VERDICT_USABLE,
        probe_instruments.VERDICT_OVERHEAD_DISQUALIFIES,
        probe_instruments.VERDICT_COUNT_UNSTABLE,
        probe_instruments.VERDICT_UNAVAILABLE,
    }
    for entry in entries:
        assert entry["verdict"] in valid_verdicts
        assert isinstance(entry["verdict_reason"], str)
        assert entry["overhead_disqualify_threshold"] == probe_instruments.OVERHEAD_DISQUALIFY_MULTIPLIER
