#!/usr/bin/env python3
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""Shared repeat, warmup, counter-snapshot, and versioned record emission
plumbing for the tests/perf/ measurement harness. Written once here so
tests/utilities/ can unit-test it without a Rogue build, exactly as the
scripts/probe_*.py modules are tested today. Each of the five tests/perf/
modules calls this beside its own unchanged emit_perf_result call, additive
rather than a replacement, so the pre-existing published record shape keeps
working exactly as before; this module never imports or modifies
tests/perf/_perf_metrics.py or scripts/perf_data.py.
"""

from __future__ import annotations

import json
import os
import re
import resource
import statistics
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable

SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import env_fingerprint  # noqa: E402  (flat sibling import, path inserted above)
import perf_tier_registry  # noqa: E402  (flat sibling import, path inserted above)


HARNESS_SCHEMA_VERSION = 1
HARNESS_RESULTS_DIR_ENV = "PERF_HARNESS_RESULTS_DIR"

DEFAULT_TARGET_CLEAN_SAMPLES = 5
DEFAULT_WARMUP_REPEATS = 1
DEFAULT_CALIBRATION_REPEATS = 5

# k=5 clean samples for Tier 1 and Tier 2. Paired derivation, so every derived constant here
# carries its own module-level string rather than standing as a bare number.
TARGET_CLEAN_SAMPLES_DERIVATION = (
    "DEFAULT_TARGET_CLEAN_SAMPLES = 5: five repeats give a usable median absolute deviation "
    "(the median of five absolute deviations from the median, rather than one or two, which "
    "cannot describe a distribution's spread at all) and reduce the minimum detectable effect "
    "by a factor of sqrt(5) =~ 2.24x relative to a single-sample design. Chosen as the "
    "smallest k that clears both bars without inflating the per-benchmark wall-clock cost the "
    "guard below has to fit."
)

STATUS_OK = "ok"
STATUS_INCONCLUSIVE = "inconclusive"

REASON_INSUFFICIENT_CLEAN_SAMPLES = "insufficient-clean-samples"
REASON_GUARD_EXCEEDED = "guard-exceeded"

COUNTER_REGRESSED = "counter-regressed"

VERDICT_BIT_IDENTICAL = "bit-identical"
VERDICT_UNSTABLE = "unstable"
INSUFFICIENT_SAMPLES = "insufficient-samples"

# A Tier 1 count that is not bit-identical across repeats is a tier verdict, not a
# sample verdict -- demoted to Tier 2 with its observed spread recorded, never INCONCLUSIVE.
DEMOTED_TO_TIER_2 = "demoted-to-tier-2"

# The primary contamination detector is a sample's disagreement with its own siblings in
# the same run (a MAD-derived band), applied only to continuous Tier 2/Tier 3 metrics; a Tier
# 1 integer count routes to within_run_repeatability/DEMOTED_TO_TIER_2 instead, since rejecting
# a differing count would smooth away exactly the nondeterminism that disqualifies it.
REJECTION_MAD_BAND = "mad-band"

# Steal time and cgroup v2 throttling stay secondary flags recorded on every sampled window,
# never the primary contamination test.
REJECTION_STEAL_NONZERO = "steal-nonzero"
REJECTION_CGROUP_THROTTLED = "cgroup-throttled"

# MAD_SIGMA_SCALE is the normal-consistency constant (1.4826) that makes the median absolute
# deviation an estimator of the standard deviation under a normal distribution; without it, a
# raw MAD understates dispersion by a fixed, known factor. DEFAULT_MAD_SIGMA_MULTIPLIER = 3.0
# is the conventional three-sigma robust-outlier bar, whose expected false-rejection rate under
# normality stays low enough at DEFAULT_TARGET_CLEAN_SAMPLES that a clean run keeps every
# sample and never trips the clean-sample guard through the detector itself. A MAD of exactly
# zero collapses the band to exact equality, which is the correct behaviour: with every sibling
# identical, a differing sibling is genuinely anomalous rather than a false positive.
MAD_SIGMA_SCALE = 1.4826
DEFAULT_MAD_SIGMA_MULTIPLIER = 3.0
MAD_BAND_DERIVATION = (
    "band = median +/- DEFAULT_MAD_SIGMA_MULTIPLIER (3.0, the conventional three-sigma robust "
    "outlier bar) * MAD_SIGMA_SCALE (1.4826, the normal-consistency constant that converts a "
    "median absolute deviation into a standard-deviation estimate) * mad. A MAD of exactly zero "
    "collapses the band to exact equality: with every sibling identical, a differing sibling is "
    "genuinely anomalous, not a false positive."
)

# Any nonzero steal delta is anomalous on this fleet, stricter than
# env_fingerprint.DEFAULT_STEAL_THRESHOLD's >= 0.01 fraction, because Phase 2 observed zero
# nonzero steal windows to calibrate a fractional threshold against.
STEAL_DELTA_THRESHOLD_DERIVATION = (
    "659 measurement windows sampled in Phase 2's real campaign (docs/plans/perf-ci-hardening/"
    "CAPABILITY-MATRIX.md, Steal time section), and every one recorded steal_jiffies_delta "
    "exactly zero (median 0, min 0, max 0, zero flagged against env_fingerprint's own >= 0.01 "
    "fractional threshold). Any nonzero delta observed by this harness therefore lies outside "
    "everything this runner fleet has ever shown, so the threshold here is 'nonzero', not a "
    "fraction calibrated against a distribution of nonzero values -- none exist yet to "
    "calibrate against. This campaign can therefore only report that no contention was "
    "observed; it cannot speak to gate behaviour under real steal, which stays untested."
)

# The per-benchmark wall-clock guard, checked between repeats only (never mid-repeat) so
# an overrun converts into a recorded INCONCLUSIVE rather than a partial sample or a hung job.
#
# MEASURED (a real 25-run campaign against perf-harness/campaign-v2, tree hash
# 6b74f79118161d744d1969808ef3020a3844a570; see GUARD_SECONDS_DERIVATION below for the full
# reconciliation). The provisional value below (15.0 s) is VALIDATED with a wide measured
# margin: across all 25 real dispatches (24 clean plus the 1 injected-load demonstration under
# a deliberate all-core competing load), the guard never fired even once (zero
# REASON_GUARD_EXCEEDED occurrences anywhere in the committed population). The measured
# per-benchmark Tier 1/Tier 2/Tier 3 collection time (the "Run Perf Harness" step's wall time
# minus ccache-warm configure-plus-compile, divided by 14 benchmarks) is roughly 5.7 s per
# benchmark, about a third of the 17 s the provisional arithmetic budgeted for it. The numeric
# constant is left unchanged since the provisional value is already comfortably validated, not
# because a tighter value couldn't be justified.
DEFAULT_BENCHMARK_GUARD_SECONDS = 15.0
GUARD_SECONDS_DERIVATION = (
    "MEASURED against the committed campaign population (docs/plans/perf-ci-hardening/"
    "harness-runs/, 25 real workflow_dispatch runs against perf-harness/campaign-v2, tree hash "
    "6b74f79118161d744d1969808ef3020a3844a570): the guard was never observed to fire. Every "
    "run's INCONCLUSIVE metrics (601 across the 24 clean runs, 20 in the 1 injected-load "
    "demonstration run) carry REASON_INSUFFICIENT_CLEAN_SAMPLES, never REASON_GUARD_EXCEEDED -- "
    "including the injected-load run, dispatched under a deliberate all-core competing load, "
    "which still completed every benchmark's repeat budget inside the guard and instead showed "
    "contamination through mad-band sample rejection. Measured per-run figures, real GitHub "
    "Actions job step timestamps (gh api repos/ruck314/rogue/actions/jobs/<id>): median "
    "configure-plus-compile with ccache warm (98.92% hit rate on every clean run) 8.46 s "
    "(configure median 2.57 s, compile median 5.89 s, n=24), versus Phase 2's original 96.4 s "
    "COLD-cache estimate the provisional arithmetic below was built from -- ccache alone "
    "recovered most of the provisional budget's own safety margin. Measured setup time "
    "(checkout through ccache install, before the harness runner starts) ranged 55-80 s across "
    "5 sampled runs (versus the provisional arithmetic's stated 60 s allowance). Measured "
    "'Run Perf Harness' step wall time (build plus all-five-module measurement) ranged 87-94 s "
    "across the same 5 runs; subtracting the ~8-10 s ccache-warm build leaves roughly 79-84 s "
    "for measurement across 14 benchmarks, or about 5.7 s per benchmark for Tier 1/Tier 2 "
    "collection combined with the unchanged full-size Tier 3 region -- well under the 15.0 s "
    "guard and under even the provisional arithmetic's 17 s per-benchmark Tier 1/Tier 2 budget "
    "alone. The guard is VALIDATED: the provisional value was never inadequate, and this "
    "campaign's population was collected entirely under it with zero guard-driven data loss. "
    "The numeric value is left at 15.0 s rather than tightened, since the requirement is that "
    "k=5 clean samples be obtainable inside the guard, not that the guard be minimal, and "
    "changing it would require a fresh campaign under a new tree hash per this derivation's own "
    "discipline. "
    "PROVISIONAL ARITHMETIC THIS RECONCILES (superseded, kept for the historical derivation): "
    "600 s total gating-job budget minus 96.4 s measured median configure-plus-"
    "compile (Phase 2's 20 real probe runs, cold cache) minus a stated 60 s allowance for "
    "checkout, actions/setup-python, apt-get install, and pip install (all four then "
    "unmeasured) left 443.6 s; divided across the 13 benchmarks the five modules were then "
    "counted as emitting (14 is the corrected count, per scripts/perf_tier_registry.py's "
    "ALL_BENCHMARKS) is =~34.1 s per benchmark for Tier 1/Tier 2 collection combined with the "
    "unchanged full-size Tier 3 region; reserving half of that per-benchmark remainder for the "
    "unchanged Tier 3 region left =~17 s, rounded down to a round, conservative 15.0 s."
)

# CPU model strings observed by Phase 2's real campaign, mapped to their
# microarchitecture name. An unrecognised model records
# env_fingerprint.UNAVAILABLE rather than a guessed microarchitecture name.
MICROARCH_BY_CPU_MODEL = {
    "AMD EPYC 7763": "Zen 3",
    "AMD EPYC 9V74": "Zen 4",
    "Intel(R) Xeon(R) Platinum 8573C": "Emerald Rapids",
}

# The ten backward-compatible metadata fields this harness commits to publishing, under one
# fixed key tuple so two records from the same runner can never differ in which keys are
# present. Seven of these (cpu_model, nproc,
# memory_total_bytes, kernel_version, cpu_mhz, cgroup_v2_cpu_max, runner_image_version) are
# already unconditionally present on every collect_fingerprint() return via its own _try
# sentinel wrapper; the remaining three (microarchitecture, steal_jiffies_delta,
# calibration_kernel_scores) are computed here and merged in the same way, defaulting to
# env_fingerprint.UNAVAILABLE rather than being omitted when their source is unreadable or
# unsampled.
FIXED_METADATA_FIELDS: tuple[str, ...] = (
    "cpu_model",
    "microarchitecture",
    "nproc",
    "memory_total_bytes",
    "kernel_version",
    "cpu_mhz",
    "steal_jiffies_delta",
    "cgroup_v2_cpu_max",
    "runner_image_version",
    "calibration_kernel_scores",
)


def median_and_mad(samples: list[float]) -> tuple[float, float]:
    """Median and median absolute deviation, never a bare mean. Same
    subtract-map-median construction as env_fingerprint._median_and_mad."""
    median = statistics.median(samples)
    mad = statistics.median([abs(sample - median) for sample in samples])
    return median, mad


def mad_band_rejections(samples: list[float]) -> list[int]:
    """Return the indices of `samples` whose value falls outside
    `median +/- DEFAULT_MAD_SIGMA_MULTIPLIER * MAD_SIGMA_SCALE * mad`
    (MAD_BAND_DERIVATION). The primary contamination detector: a sample's
    disagreement with its own siblings in the same run, applied only to
    continuous metrics -- a Tier 1 integer count routes to
    within_run_repeatability instead, never through this function. Fewer
    than two samples cannot describe a band, so none are flagged."""
    if len(samples) < 2:
        return []
    median, mad = median_and_mad(samples)
    band = DEFAULT_MAD_SIGMA_MULTIPLIER * MAD_SIGMA_SCALE * mad
    return [index for index, sample in enumerate(samples) if abs(sample - median) > band]


def snapshot_counters(readers: dict[str, Callable[[], int]]) -> dict[str, int]:
    """Read every counter in `readers` immediately, in sorted key order, and
    return a plain mapping of metric name to its current value."""
    return {name: int(readers[name]()) for name in sorted(readers)}


def counter_deltas(after: dict[str, int], before: dict[str, int]) -> dict[str, Any]:
    """Per-key `after - before`, or the COUNTER_REGRESSED sentinel when a
    counter reads lower after the measured region than before it -- a
    monotonic counter must never decrease, so this is reported as an
    anomaly, never as a negative delta."""
    deltas: dict[str, Any] = {}
    for key, after_value in after.items():
        before_value = before.get(key, 0)
        if after_value < before_value:
            deltas[key] = COUNTER_REGRESSED
        else:
            deltas[key] = after_value - before_value
    return deltas


def within_run_repeatability(counts: list[int]) -> dict[str, Any]:
    """`bit-identical` when every count is equal, `unstable` with the
    observed min/max/spread when they are not, and the insufficient-samples
    sentinel below two counts -- exactly the no-tolerance admission gate
    shape used by scripts/probe_instruments.py's repeatability_verdict."""
    n = len(counts)
    if n < 2:
        return {"verdict": INSUFFICIENT_SAMPLES, "n": n}
    if min(counts) == max(counts):
        return {"verdict": VERDICT_BIT_IDENTICAL, "n": n}
    return {
        "verdict": VERDICT_UNSTABLE,
        "n": n,
        "min": min(counts),
        "max": max(counts),
        "spread": max(counts) - min(counts),
    }


def derive_microarchitecture(cpuinfo_path: Path) -> dict[str, Any]:
    """Derive a microarchitecture name from /proc/cpuinfo's model name
    string via MICROARCH_BY_CPU_MODEL, kept out of
    env_fingerprint.collect_fingerprint() because that module's own output
    shape is costly to change once published. Records the raw
    vendor_id/cpu-family/model/stepping quadruple alongside the derived (or
    UNAVAILABLE) name so an unrecognised model is diagnosable rather than
    silently guessed at.
    """
    try:
        cpu_model_name = env_fingerprint._read_cpuinfo_field(cpuinfo_path, "model name")
    except (OSError, ValueError):
        cpu_model_name = env_fingerprint.UNAVAILABLE

    raw_fields = {}
    for key, prefix in (
        ("vendor_id", "vendor_id"), ("cpu_family", "cpu family"),
        ("model", "model"), ("stepping", "stepping"),
    ):
        try:
            raw_fields[key] = env_fingerprint._read_cpuinfo_field(cpuinfo_path, prefix)
        except (OSError, ValueError):
            raw_fields[key] = env_fingerprint.UNAVAILABLE

    microarchitecture = MICROARCH_BY_CPU_MODEL.get(cpu_model_name, env_fingerprint.UNAVAILABLE)

    return {
        "microarchitecture": microarchitecture,
        "cpu_model_name": cpu_model_name,
        "raw_cpuinfo_fields": raw_fields,
    }


def _window_secondary_flags(window: dict[str, Any]) -> list[str]:
    """Any nonzero steal_jiffies_delta or cgroup_nr_throttled_delta is
    anomalous on this fleet, recorded as a secondary flag on the window
    itself regardless of whether the primary MAD-band test fired."""
    flags: list[str] = []
    steal_delta = window.get("steal_jiffies_delta")
    if isinstance(steal_delta, int) and not isinstance(steal_delta, bool) and steal_delta != 0:
        flags.append(REJECTION_STEAL_NONZERO)
    cgroup_delta = window.get("cgroup_nr_throttled_delta")
    if isinstance(cgroup_delta, int) and not isinstance(cgroup_delta, bool) and cgroup_delta != 0:
        flags.append(REJECTION_CGROUP_THROTTLED)
    return flags


# The measure_benchmark return dict is keyed by metric name for every real registered metric,
# plus this one reserved non-metric key carrying the per-repeat measurement windows and their
# steal/cgroup secondary flags. build_harness_record pops it into its own record field rather
# than leaving it readable as a bogus "metric".
MEASUREMENT_WINDOWS_KEY = "_measurement_windows"


def dual_clock_cpu(fn: Callable[[], Any]) -> tuple[float, float] | tuple[None, None]:
    """Measure both process and thread CPU time in nanoseconds across one
    call to `fn()`, returning `(process_ns, thread_ns)`, or `(None, None)`
    if either clock read fails -- never one clock without the other.

    Process CPU comes from `resource.getrusage(RUSAGE_SELF)`'s
    `ru_utime + ru_stime`; thread CPU comes from
    `time.clock_gettime(CLOCK_THREAD_CPUTIME_ID)` -- a `time` module
    function, not a `resource` one. Both clocks are required: the stream
    path is threaded, so a thread-only figure misses the work happening in
    Rogue's transport threads, while a process-only figure folds in pytest
    and interpreter overhead alongside it.
    """
    try:
        process_before = resource.getrusage(resource.RUSAGE_SELF)
        thread_before_s = time.clock_gettime(time.CLOCK_THREAD_CPUTIME_ID)
        fn()
        process_after = resource.getrusage(resource.RUSAGE_SELF)
        thread_after_s = time.clock_gettime(time.CLOCK_THREAD_CPUTIME_ID)
    except (OSError, AttributeError):
        return None, None

    process_before_s = process_before.ru_utime + process_before.ru_stime
    process_after_s = process_after.ru_utime + process_after.ru_stime
    process_ns = (process_after_s - process_before_s) * 1e9
    thread_ns = (thread_after_s - thread_before_s) * 1e9
    return process_ns, thread_ns


# The four Tier 2 metric names dual-clock accounting produces, matching perf_tier_registry's
# registered entries exactly.
DUAL_CLOCK_METRIC_NAMES: tuple[str, ...] = (
    "cpu_process_ns_per_byte",
    "cpu_process_ns_per_op",
    "cpu_thread_ns_per_byte",
    "cpu_thread_ns_per_op",
)


def _aggregate_steal_jiffies_delta(windows: list[dict[str, Any]]) -> Any:
    """Sum of `steal_jiffies_delta` across every sampled measurement window
    for this benchmark. `env_fingerprint.UNAVAILABLE` when no window was
    sampled at all -- an absent measurement must never be readable as a
    clean zero -- or when every sampled window's own delta was itself
    unavailable."""
    if not windows:
        return env_fingerprint.UNAVAILABLE
    total = 0
    any_numeric = False
    for window in windows:
        delta = window.get("steal_jiffies_delta")
        if isinstance(delta, int) and not isinstance(delta, bool):
            total += delta
            any_numeric = True
    return total if any_numeric else env_fingerprint.UNAVAILABLE


def _calibration_kernel_scores(calibration: dict[str, Any]) -> dict[str, Any]:
    """One kernel score (the component's own median) per calibration
    component, never blended into a single figure -- mirrors
    env_fingerprint.collect_calibration_vector's own no-blending
    discipline. A component whose collection failed reports
    env_fingerprint.UNAVAILABLE rather than being omitted."""
    components = calibration.get("components", {})
    scores: dict[str, Any] = {}
    for component in perf_tier_registry.CALIBRATION_COMPONENTS:
        entry = components.get(component)
        if isinstance(entry, dict) and "median" in entry:
            scores[component] = entry["median"]
        else:
            scores[component] = env_fingerprint.UNAVAILABLE
    return scores


def measure_benchmark(
    benchmark: str,
    workload: Callable[[], Any],
    counter_readers: dict[str, Callable[[], int]],
    repeats: int = DEFAULT_TARGET_CLEAN_SAMPLES,
    warmup_repeats: int = DEFAULT_WARMUP_REPEATS,
    guard_seconds: float = DEFAULT_BENCHMARK_GUARD_SECONDS,
    clock: Callable[[], float] = time.perf_counter,
    window_sampler: Callable[[str, Callable[[], Any]], dict[str, Any]] = env_fingerprint.sample_cpu_window,
    bytes_per_repeat: int | None = None,
    ops_per_repeat: int | None = None,
) -> dict[str, Any]:
    """Run `warmup_repeats` unmeasured warmup iterations of `workload`, then
    up to `repeats` measured iterations, snapshotting `counter_readers`
    immediately before and immediately after each measured iteration and
    nowhere else. The accumulated wall-clock time is checked between repeats
    only: once it reaches `guard_seconds`, no further repeat starts,
    so a repeat is never cut mid-flight and no partial sample is ever
    emitted. Each repeat is wrapped in `window_sampler` (which records the
    steal and cgroup v2 throttling secondary flags), collected under
    MEASUREMENT_WINDOWS_KEY.

    When both `bytes_per_repeat` and `ops_per_repeat` are given, each repeat
    also measures `dual_clock_cpu` across the same
    instrumented call, dividing both clocks by both units of work to
    populate DUAL_CLOCK_METRIC_NAMES' four registered Tier 2 entries exactly
    like any other continuous metric; a repeat whose dual-clock read fails
    (`dual_clock_cpu` returning `(None, None)`) contributes no sample for
    those four names rather than a fabricated one. Neither parameter is
    required: omit both to measure counters only.

    Routes by metric kind: a Tier 1 integer count goes through
    `within_run_repeatability`, demoting to Tier 2 with its observed
    min/max/spread on an unstable verdict rather than rejecting a sample; a
    continuous Tier 2 or Tier 3 metric goes through `mad_band_rejections`,
    excluding a flagged repeat from `samples`, the median, the MAD, and
    `n_clean`. A metric with fewer than DEFAULT_TARGET_CLEAN_SAMPLES clean
    samples emits STATUS_INCONCLUSIVE with REASON_GUARD_EXCEEDED (the guard
    fired first) or REASON_INSUFFICIENT_CLEAN_SAMPLES (rejection dropped it
    below target with repeats to spare), and emits no `median`/`mad` key at
    all -- never a null one -- so a consumer that forgets to check `status`
    fails loudly instead of reading a null as a number.
    """
    for _ in range(warmup_repeats):
        workload()

    dual_clock_requested = bytes_per_repeat is not None and ops_per_repeat is not None

    raw_samples: dict[str, list[Any]] = {name: [] for name in counter_readers}
    if dual_clock_requested:
        for name in DUAL_CLOCK_METRIC_NAMES:
            raw_samples.setdefault(name, [])

    windows: list[dict[str, Any]] = []
    guard_exceeded = False
    elapsed_total = 0.0
    completed_repeats = 0

    while completed_repeats < repeats:
        if elapsed_total >= guard_seconds:
            guard_exceeded = True
            break

        before_holder: dict[str, dict[str, int]] = {}
        window_holder: list[dict[str, Any]] = []

        def _instrumented() -> dict[str, int]:
            before_holder["before"] = snapshot_counters(counter_readers)
            workload()
            return snapshot_counters(counter_readers)

        def _sampled_repeat() -> None:
            window_holder.append(
                window_sampler(f"{benchmark}-repeat-{completed_repeats}", _instrumented)
            )

        start = clock()
        if dual_clock_requested:
            process_ns, thread_ns = dual_clock_cpu(_sampled_repeat)
        else:
            process_ns = thread_ns = None
            _sampled_repeat()
        elapsed_total += clock() - start

        window = window_holder[0]
        after = window["result"]
        before = before_holder["before"]
        window = dict(window)
        window["secondary_flags"] = _window_secondary_flags(window)
        windows.append(window)

        deltas = counter_deltas(after, before)
        for name, delta in deltas.items():
            raw_samples[name].append(delta)

        if dual_clock_requested and process_ns is not None and thread_ns is not None:
            raw_samples["cpu_process_ns_per_byte"].append(process_ns / bytes_per_repeat)
            raw_samples["cpu_process_ns_per_op"].append(process_ns / ops_per_repeat)
            raw_samples["cpu_thread_ns_per_byte"].append(thread_ns / bytes_per_repeat)
            raw_samples["cpu_thread_ns_per_op"].append(thread_ns / ops_per_repeat)

        completed_repeats += 1

    metrics: dict[str, Any] = {}
    for name in sorted(raw_samples):
        samples = raw_samples[name]
        tier = perf_tier_registry.tier_for(name)
        entry: dict[str, Any] = {"tier_candidate": tier}

        if tier == perf_tier_registry.TIER_1:
            clean_samples = [sample for sample in samples if isinstance(sample, int)]
            n_clean = len(clean_samples)
            if clean_samples:
                repeatability = within_run_repeatability(clean_samples)
            else:
                repeatability = {"verdict": INSUFFICIENT_SAMPLES, "n": 0}
            entry["within_run_repeatability"] = repeatability
            entry["rejected_samples"] = []
            if repeatability.get("verdict") == VERDICT_UNSTABLE:
                entry["tier_demoted_to"] = perf_tier_registry.TIER_2
                entry["demotion_reason"] = DEMOTED_TO_TIER_2
                entry["min"] = repeatability["min"]
                entry["max"] = repeatability["max"]
                entry["spread"] = repeatability["spread"]
            accepted: list[float] = list(clean_samples)
        else:
            continuous_samples = [
                float(sample) for sample in samples
                if isinstance(sample, (int, float)) and not isinstance(sample, bool)
            ]
            rejected_indices = set(mad_band_rejections(continuous_samples))
            entry["rejected_samples"] = [
                {"index": index, "value": continuous_samples[index], "reason": REJECTION_MAD_BAND}
                for index in sorted(rejected_indices)
            ]
            accepted = [
                value for index, value in enumerate(continuous_samples)
                if index not in rejected_indices
            ]
            n_clean = len(accepted)

        entry["n_clean"] = n_clean

        if n_clean < DEFAULT_TARGET_CLEAN_SAMPLES:
            entry["status"] = STATUS_INCONCLUSIVE
            entry["reason"] = REASON_GUARD_EXCEEDED if guard_exceeded else REASON_INSUFFICIENT_CLEAN_SAMPLES
            entry["samples"] = accepted
        else:
            entry["status"] = STATUS_OK
            entry["reason"] = None
            entry["samples"] = accepted
            entry["median"], entry["mad"] = median_and_mad([float(value) for value in accepted])

        metrics[name] = entry

    metrics[MEASUREMENT_WINDOWS_KEY] = windows
    return metrics


def _git_tree_hash() -> str:
    """`git rev-parse HEAD^{tree}` for the checkout this process runs in,
    never raising: an unreadable repository or a missing git binary records
    env_fingerprint.UNAVAILABLE rather than aborting record construction."""
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD^{tree}"],
            capture_output=True, text=True, timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return env_fingerprint.UNAVAILABLE
    if completed.returncode != 0:
        return env_fingerprint.UNAVAILABLE
    value = completed.stdout.strip()
    return value if value else env_fingerprint.UNAVAILABLE


CALIBRATION_MEASUREMENT_SHAPE_NOTE = (
    "This record's calibration vector was measured {repeats} times per run and the median "
    "used, which cuts the calibrator's own contributed noise roughly as sqrt({repeats}). "
    "Phase 2 recorded its own calibration with a single sample per run "
    "(docs/plans/perf-ci-hardening/capability-matrix.json), so the two sets of figures "
    "describe different measurement shapes and must not be compared directly."
).format(repeats=DEFAULT_CALIBRATION_REPEATS)


def build_harness_record(
    benchmark: str,
    metrics: dict[str, Any],
    workload: dict[str, Any],
) -> dict[str, Any]:
    """Build the versioned harness record for one benchmark's measured
    metrics. Top level is exactly harness_schema_version, run, environment,
    build, benchmarks, errors. `environment` carries the whole
    env_fingerprint.collect_fingerprint() field set, the derived
    microarchitecture, the calibration vector (measured
    DEFAULT_CALIBRATION_REPEATS times and the median used), and
    every one of FIXED_METADATA_FIELDS under its fixed key set.

    `metrics` may carry MEASUREMENT_WINDOWS_KEY (measure_benchmark's
    per-repeat steal/cgroup window list); it is popped out into its own
    `measurement_windows` benchmark field and used to compute
    `environment["steal_jiffies_delta"]`, rather than being left readable as
    a bogus metric entry. `metrics` is copied, never mutated in place.
    """
    metrics = dict(metrics)
    windows = metrics.pop(MEASUREMENT_WINDOWS_KEY, [])

    errors: list[str] = []

    fingerprint = env_fingerprint.collect_fingerprint()
    errors.extend(fingerprint.get("errors", []))

    microarch = derive_microarchitecture(env_fingerprint.PROC_CPUINFO_PATH)

    calibration = env_fingerprint.collect_calibration_vector(repeats=DEFAULT_CALIBRATION_REPEATS)
    errors.extend(calibration.get("errors", []))

    environment = dict(fingerprint)
    environment["microarchitecture"] = microarch["microarchitecture"]
    environment["cpu_model_name"] = microarch["cpu_model_name"]
    environment["raw_cpuinfo_fields"] = microarch["raw_cpuinfo_fields"]
    environment["calibration_vector"] = calibration
    environment["calibration_measurement_shape"] = CALIBRATION_MEASUREMENT_SHAPE_NOTE
    environment["steal_jiffies_delta"] = _aggregate_steal_jiffies_delta(windows)
    environment["calibration_kernel_scores"] = _calibration_kernel_scores(calibration)

    # Defensive fill: the field set is fixed by FIXED_METADATA_FIELDS, so an
    # unreadable field is always UNAVAILABLE rather than silently absent from the mapping.
    for field in FIXED_METADATA_FIELDS:
        environment.setdefault(field, env_fingerprint.UNAVAILABLE)

    # Every raw count-type metric also carries a per-unit-work normalized value, so the
    # reduced-size counts are comparable across benchmarks; the raw count stays untouched.
    reduced_size = workload.get("reduced_size") if isinstance(workload, dict) else None
    if reduced_size:
        for name, entry in metrics.items():
            descriptor = perf_tier_registry.METRICS.get(name)
            if descriptor is None or descriptor["unit"] not in ("count", "bytes"):
                continue
            if "median" in entry:
                entry["per_unit_work"] = entry["median"] / reduced_size

    run = {
        "github_run_id": os.environ.get("GITHUB_RUN_ID", env_fingerprint.UNAVAILABLE),
        "github_run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT", env_fingerprint.UNAVAILABLE),
        "git_sha": os.environ.get("GITHUB_SHA", env_fingerprint.UNAVAILABLE),
        "git_tree_hash": _git_tree_hash(),
        "campaign_branch": os.environ.get("HARNESS_CAMPAIGN_BRANCH", env_fingerprint.UNAVAILABLE),
        "dispatch_index": os.environ.get("HARNESS_DISPATCH_INDEX", env_fingerprint.UNAVAILABLE),
        "injected_load": os.environ.get("HARNESS_INJECTED_LOAD", env_fingerprint.UNAVAILABLE),
    }

    return {
        "harness_schema_version": HARNESS_SCHEMA_VERSION,
        "run": run,
        "environment": environment,
        # Build timing/ccache metadata is scripts/perf_harness_runner.py's
        # concern, added in a later plan; left empty here rather than
        # guessed at.
        "build": {},
        "benchmarks": {
            benchmark: {
                "metrics": metrics,
                "workload": workload,
                "measurement_windows": windows,
            },
        },
        "errors": errors,
    }


def emit_harness_result(record: dict[str, Any], benchmark: str) -> dict[str, Any]:
    """Write `record` to PERF_HARNESS_RESULTS_DIR/<slug>.json, mirroring
    tests/perf/_perf_metrics.py:emit_perf_result's slug regex and
    sort_keys=True JSON shape. Writes nothing and returns `record` unchanged
    when PERF_HARNESS_RESULTS_DIR is unset."""
    outdir = os.getenv(HARNESS_RESULTS_DIR_ENV)
    if outdir:
        target_dir = Path(outdir)
        target_dir.mkdir(parents=True, exist_ok=True)
        slug = re.sub(r"[^A-Za-z0-9_.-]+", "_", benchmark)
        (target_dir / f"{slug}.json").write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")

    return record
