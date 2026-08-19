#!/usr/bin/env python3
# ----------------------------------------------------------------------------
# Title      : ROGUE Runner Capability Matrix Report
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
import statistics
import sys
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import env_fingerprint  # noqa: E402  (flat sibling import, path inserted above)
import perf_noise_report  # noqa: E402  (flat sibling import, path inserted above)
import probe_instruments  # noqa: E402  (flat sibling import, path inserted above)
import probe_interventions  # noqa: E402  (flat sibling import, path inserted above)
import probe_perf_events  # noqa: E402  (flat sibling import, path inserted above)


SIDECAR_VERSION = 1
DEFAULT_MIN_N = 3
INSUFFICIENT_SAMPLES = "insufficient-samples"
TREE_HASH_MISMATCH = "tree-hash-mismatch"
NOT_APPLICABLE = "not-applicable"
GATING_INELIGIBLE = "gating-ineligible"
CONTAMINATED = "contaminated"
ZERO_WINDOWS = "zero-windows"

STOPPING_CONDITION_TARGET_MET = "target-cpu-model-set-observed"
STOPPING_CONDITION_RUN_CAP_REACHED = "run-cap-reached"
STOPPING_CONDITION_NEITHER = "neither-condition-reached"

CALIBRATION_COMPONENTS: tuple[str, ...] = ("alu", "memcpy", "syscall", "tsc")

EXPECTED_PROBE_SCHEMA_VERSION = 1
MISSING_FIELD = "missing"
NO_TIMERS_OBSERVED = "no-timers-observed"

# The confirmation leg's own "this instrument was never run against real
# code" status, as recorded by probe_runner.py's collect_confirmation_leg().
CONFIRMATION_STATUS_SKIPPED = "skipped"

# Derived deterministic-tier admission vocabulary for the confirmation leg's
# real-module repeatability evidence. These three values are computed by
# this aggregator from the repeatability verdicts each committed record
# already carries; no probe run ever records any of them, and none is a
# spelling probe_instruments.py itself emits (bit-identical, unstable,
# insufficient-samples), so a reader can always tell an aggregator-derived
# cell from a probe-recorded one. The remaining outcome (the confirmation
# leg ran but every attempt failed before a count was ever taken) reuses
# INSUFFICIENT_SAMPLES directly rather than inventing a fourth spelling.
DERIVED_ADMISSION_INELIGIBLE = "derived-ineligible-count-unstable"
DERIVED_ADMISSION_ELIGIBLE = "derived-eligible-count-stable"
DERIVED_ADMISSION_NOT_EXERCISED = "derived-not-exercised"

# The three cgroup v2 cpu.stat throttling counters the compact fingerprint
# cell reports. Kept as a named constant rather than an inline literal set so
# the choice of which counters the compact cell surfaces is visible in one
# place; the dedicated cgroup detail section reports the full observed key
# set instead of this fixed subset.
CGROUP_THROTTLE_COUNTER_KEYS: tuple[str, ...] = ("nr_periods", "nr_throttled", "throttled_usec")

DEFAULT_RUNS_DIR = "docs/plans/perf-ci-hardening/probe-runs"
DEFAULT_OUT_MD = "docs/plans/perf-ci-hardening/CAPABILITY-MATRIX.md"
DEFAULT_OUT_JSON = "docs/plans/perf-ci-hardening/capability-matrix.json"

# The frozen perf-probe/campaign-v2 branch's base tree hash, recorded in
# docs/plans/perf-ci-hardening/CAMPAIGN-SETUP.md. This is the second campaign
# branch: the original perf-probe/campaign was frozen before the probe
# pipeline was finished and can only ever emit fingerprint-only records, so
# the real multi-run campaign runs against this branch instead. Every
# committed probe run's run.git_tree_hash traces to this value, so the
# canonical reproduce command below names it explicitly, letting a reader
# reproduce the population itself rather than merely the arithmetic over
# whatever happens to be on disk. The command also names the coverage target
# and run cap the committed population was built with: the coverage target
# and run cap change the rendered stopping condition, so they are part of
# what has to be reproduced, not incidental bookkeeping alongside the
# population identity above.
DEFAULT_EXPECTED_TREE_HASH = "23ab89659eaccfa80215bba03e6a02f6152c3555"

# The three host models observed by the real perf-probe/campaign-v2
# campaign, matching this module's --target-cpu-models default and the
# committed sidecar's parameters.target_cpu_models. Named as an explicit
# flag in CANONICAL_COMMAND rather than baked into argparse's own default,
# so a later campaign against a different runner fleet overrides this
# visibly instead of silently inheriting this campaign's host set.
DEFAULT_TARGET_CPU_MODELS: tuple[str, ...] = (
    "AMD EPYC 7763 64-Core Processor",
    "AMD EPYC 9V74 80-Core Processor",
    "INTEL(R) XEON(R) PLATINUM 8573C",
)

# The run cap the real campaign was configured with, matching the committed
# sidecar's parameters.run_cap. Named as an explicit flag for the same
# reason as DEFAULT_TARGET_CPU_MODELS above.
DEFAULT_RUN_CAP = 24

CANONICAL_COMMAND = (
    "python3 scripts/probe_capability_report.py "
    f"--runs-dir {DEFAULT_RUNS_DIR} --expected-tree-hash {DEFAULT_EXPECTED_TREE_HASH} "
    f'--target-cpu-models "{",".join(DEFAULT_TARGET_CPU_MODELS)}" --run-cap {DEFAULT_RUN_CAP} '
    f"--out-md {DEFAULT_OUT_MD} --out-json {DEFAULT_OUT_JSON}"
)

FINGERPRINT_COLUMNS = (
    ("cpu_model", "CPU model"),
    ("cpu_mhz", "CPU MHz"),
    ("nproc", "nproc"),
    ("kernel_version", "Kernel"),
    ("glibc_version", "glibc"),
    ("cpython_version", "CPython"),
    ("compiler_version", "Compiler"),
    ("memory_total_bytes", "Memory (bytes)"),
    ("cgroup_v2_cpu_stat", "cgroup v2 cpu.stat"),
    ("systemd_timers", "systemd timers"),
    ("runner_image_version", "Runner image"),
    ("git_tree_hash", "Tree hash"),
)


def fmt_float(value: Any) -> str:
    """Fixed float formatting shared by every numeric cell in this module,
    matching scripts/perf_noise_report.py's own fmt_float convention so byte
    stability survives identical inputs regardless of underlying float repr.
    """
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, (int, float)):
        return f"{value:.6g}"
    return str(value)


def _sidecar_float(value: float) -> float:
    return float(fmt_float(value))


def _fmt_cell(value: Any) -> str:
    if value is None:
        return "none"
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, float):
        return fmt_float(value)
    if isinstance(value, int):
        return str(value)
    return str(value)


def _fmt_tally(tally: dict[str, int]) -> str:
    if not tally:
        return "(none)"
    return ", ".join(f"{key}: {count}" for key, count in tally.items())


def _systemd_unit_names(timers: Any) -> tuple[str, ...]:
    """Sorted distinct unit-name tuple derived from one run's systemd timer
    lines. Each line's second-to-last whitespace-separated field is the timer
    unit name; a line with fewer than two fields contributes nothing rather
    than raising. A non-list input (the absent-field sentinel, or any other
    non-list value) yields an empty tuple, never an exception.
    """
    if not isinstance(timers, list):
        return ()
    names: set[str] = set()
    for line in timers:
        if not isinstance(line, str):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        names.add(parts[-2])
    return tuple(sorted(names))


def _build_unit_set_labels(timer_lists: Any) -> dict[tuple[str, ...], str]:
    """One label per distinct unit-name set observed across `timer_lists` (an
    iterable of raw `systemd_timers` values, one per run), assigned in the
    lexicographic order of the unit-name tuple itself so labels are
    deterministic regardless of iteration order. This is the single
    derivation shared by the fingerprint table's systemd column and the
    cgroup/timer detail section's unit inventory, so a label can never
    disagree between the two: both call this same function over the same
    population.
    """
    distinct: set[tuple[str, ...]] = set()
    for timers in timer_lists:
        names = _systemd_unit_names(timers)
        if names:
            distinct.add(names)
    return {names: f"set-{index + 1}" for index, names in enumerate(sorted(distinct))}


def _fmt_cgroup_cpu_stat_cell(value: Any) -> str:
    """Compact fingerprint-table cell for `cgroup_v2_cpu_stat`: the three
    throttling counters named by CGROUP_THROTTLE_COUNTER_KEYS, when the
    collected value is a populated dict. A non-dict value -- the absent-field
    sentinel, or the collected-but-unreadable sentinel string the fingerprint
    collector emits when the cpu.stat file cannot be read -- renders verbatim
    through `_fmt_cell` instead, keeping the two cases distinguishable rather
    than collapsing both into the same cell text.
    """
    if not isinstance(value, dict):
        return _fmt_cell(value)
    return ", ".join(
        f"{key}: {_fmt_cell(value.get(key, MISSING_FIELD))}" for key in CGROUP_THROTTLE_COUNTER_KEYS
    )


def _fmt_systemd_timers_cell(value: Any, unit_set_labels: dict[tuple[str, ...], str]) -> str:
    """Compact fingerprint-table cell for `systemd_timers`: the run's own
    distinct unit count plus the shared inventory label for that unit set. A
    non-list value (the absent-field sentinel) renders verbatim through
    `_fmt_cell`. A list with no derivable unit names (a genuinely empty
    timer list on this run) renders the zero count with the
    no-timers-observed label rather than looking up a label that does not
    exist for an empty set.
    """
    if not isinstance(value, list):
        return _fmt_cell(value)
    names = _systemd_unit_names(value)
    if not names:
        return f"0 ({NO_TIMERS_OBSERVED})"
    label = unit_set_labels.get(names, MISSING_FIELD)
    return f"{len(names)} ({label})"


# Per-column formatter overrides for the fingerprint markdown table, keyed by
# FINGERPRINT_COLUMNS key. Every column not listed here renders through the
# default `_fmt_cell` path. `systemd_timers` is not registered here since its
# formatter needs the population-wide unit-set label map, which is only
# available once the whole fingerprint section has been built; render_markdown
# adds it to a local copy of this mapping at render time.
FINGERPRINT_COLUMN_FORMATTERS: dict[str, Any] = {
    "cgroup_v2_cpu_stat": _fmt_cgroup_cpu_stat_cell,
}


def _round_floats(stats: dict[str, Any]) -> dict[str, Any]:
    """Round every float value in `stats` through `_sidecar_float`, leaving
    every non-float value (including sentinel strings) untouched.
    """
    return {
        key: (_sidecar_float(value) if isinstance(value, float) else value)
        for key, value in stats.items()
    }


def _median_or_insufficient(values: list[float], min_n: int) -> tuple[Any, int]:
    """Median of `values`, or the insufficient-samples sentinel plus the
    actual sample count when there are fewer than `min_n` usable values --
    including the zero-samples case, never a computed multiplier from an
    empty list.
    """
    n = len(values)
    if n < min_n:
        return INSUFFICIENT_SAMPLES, n
    return statistics.median(values), n


def load_probe_run(path: Path) -> dict[str, Any] | None:
    """Load and validate one committed probe-run JSON file.

    Returns None on any decode failure, a non-mapping payload, or an
    unrecognized `probe_schema_version`, so the caller can skip and count a
    malformed record instead of crashing.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    schema_version = payload.get("probe_schema_version")
    if not isinstance(schema_version, int) or schema_version != EXPECTED_PROBE_SCHEMA_VERSION:
        return None
    return payload


def build_population(paths: list[Path], expected_tree_hash: str | None) -> dict[str, Any]:
    """Classify every committed probe-run file into the accepted population,
    a decode/schema-version skip, or a tree-hash-mismatch rejection.

    Paths are always processed in sorted (filename) order internally,
    regardless of the order the caller enumerated them in, so the accepted
    population is identical no matter how the filesystem listed the runs
    directory. A malformed file and a tree-hash mismatch are counted
    separately, with a reason recorded for each, because they mean different
    things: a malformed file is a tooling problem, while a mismatched tree
    hash means the run measured different code and is not a member of this
    population at all. Neither is ever silently dropped, and neither ever
    raises.
    """
    accepted: list[dict[str, Any]] = []
    skipped_count = 0
    skipped_reasons: list[dict[str, Any]] = []
    rejected_count = 0
    rejected_reasons: list[dict[str, Any]] = []

    for path in sorted(paths, key=lambda p: p.name):
        record = load_probe_run(path)
        if record is None:
            skipped_count += 1
            skipped_reasons.append({
                "path": str(path),
                "reason": "unreadable, malformed JSON, or an unrecognized probe_schema_version",
            })
            continue

        run_info = record.get("run")
        run_info = run_info if isinstance(run_info, dict) else {}
        observed_tree_hash = run_info.get("git_tree_hash")

        if expected_tree_hash is not None and observed_tree_hash != expected_tree_hash:
            rejected_count += 1
            rejected_reasons.append({
                "path": str(path),
                "reason": TREE_HASH_MISMATCH,
                "observed_tree_hash": observed_tree_hash,
                "expected_tree_hash": expected_tree_hash,
            })
            continue

        record = dict(record)
        record["_run_id"] = path.stem
        accepted.append(record)

    return {
        "accepted": accepted,
        "skipped_count": skipped_count,
        "skipped_reasons": skipped_reasons,
        "rejected_count": rejected_count,
        "rejected_reasons": rejected_reasons,
    }


def build_coverage_section(
    records: list[dict[str, Any]],
    target_cpu_models: list[str],
    run_cap: int | None,
) -> dict[str, Any]:
    """Report the accepted run count, the distinct host models observed with
    a per-model run count, the coverage target and run cap the campaign ran
    against, and which stopping condition holds.

    The requirement's floor is a run count, but the purpose is spread: a
    campaign that met a run-count floor on a single host model would satisfy
    the letter while telling a later phase nothing, so this section always
    states which condition actually fired.
    """
    host_counts: dict[str, int] = {}
    for record in records:
        fingerprint = record.get("fingerprint")
        fingerprint = fingerprint if isinstance(fingerprint, dict) else {}
        cpu_model = fingerprint.get("cpu_model")
        if not isinstance(cpu_model, str):
            cpu_model = MISSING_FIELD
        host_counts[cpu_model] = host_counts.get(cpu_model, 0) + 1

    run_count = len(records)
    distinct_models = set(host_counts)
    target_set = {model for model in target_cpu_models if isinstance(model, str)}
    target_met = bool(target_set) and target_set.issubset(distinct_models)

    if target_met:
        stopping_condition = STOPPING_CONDITION_TARGET_MET
    elif run_cap is not None and run_count >= run_cap:
        stopping_condition = STOPPING_CONDITION_RUN_CAP_REACHED
    else:
        stopping_condition = STOPPING_CONDITION_NEITHER

    return {
        "run_count": run_count,
        "distinct_host_model_count": len(distinct_models),
        "host_model_run_counts": dict(sorted(host_counts.items())),
        "coverage_target": sorted(target_set),
        "run_cap": run_cap,
        "stopping_condition": stopping_condition,
    }


def build_fingerprint_section(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One row per run across the whole population, in a fixed column order,
    sorted by run identifier. `sorted()` is stable, and the caller supplies
    `records` in a deterministic (path-sorted) order, so two rows that tie on
    `run_id` still render in a deterministic relative order.
    """
    rows: list[dict[str, Any]] = []
    for record in records:
        fingerprint = record.get("fingerprint")
        if not isinstance(fingerprint, dict):
            fingerprint = {}
        run_info = record.get("run")
        if not isinstance(run_info, dict):
            run_info = {}

        row: dict[str, Any] = {"run_id": record.get("_run_id", MISSING_FIELD)}
        for key, _ in FINGERPRINT_COLUMNS:
            if key == "git_tree_hash":
                row[key] = run_info.get(key, MISSING_FIELD)
            else:
                row[key] = fingerprint.get(key, MISSING_FIELD)
        rows.append(row)

    rows.sort(key=lambda row: row["run_id"])
    return rows


def _host_model_key(record: dict[str, Any]) -> str:
    """Derive the host-model grouping key for calibration dispersion: the
    recorded CPU model string together with the TSC-derived rate bucket,
    matching perf_noise_report.host_group_id's existing derivation exactly
    rather than attributing a rate to a named CPU family from external
    documentation. Either half missing degrades to that half's own sentinel,
    never a raised error.
    """
    fingerprint = record.get("fingerprint")
    fingerprint = fingerprint if isinstance(fingerprint, dict) else {}
    cpu_model = fingerprint.get("cpu_model")
    if not isinstance(cpu_model, str):
        cpu_model = MISSING_FIELD

    calibration = record.get("calibration")
    calibration = calibration if isinstance(calibration, dict) else {}
    components = calibration.get("components")
    components = components if isinstance(components, dict) else {}
    tsc = components.get("tsc")
    tsc_value = tsc.get("value") if isinstance(tsc, dict) else None
    if isinstance(tsc_value, (int, float)) and not isinstance(tsc_value, bool):
        rate_bucket = perf_noise_report.host_group_id(float(tsc_value))
    else:
        rate_bucket = perf_noise_report.UNATTRIBUTED

    return f"{cpu_model} | {rate_bucket}"


def build_perf_event_section(records: list[dict[str, Any]], min_n: int) -> list[dict[str, Any]]:
    """One entry per perf event name observed across the population.

    Each entry carries the event class, a per-privilege-state status tally
    across runs (never a single collapsed verdict for an event whose status
    differs run to run), the gating eligibility verdict and its reason, the
    number of runs backing that verdict, and one retained raw output line as
    quoted evidence. Below `min_n` observed runs, the gating verdict is
    replaced by the insufficient-samples sentinel while the raw per-run
    status tallies -- direct evidence, not a derived statistic -- remain
    listed.
    """
    by_event: dict[str, dict[str, Any]] = {}

    for record in records:
        perf_events = record.get("perf_events")
        if not isinstance(perf_events, dict):
            continue
        entries = perf_events.get("events")
        if not isinstance(entries, list):
            continue
        run_id = record.get("_run_id")

        for entry in entries:
            if not isinstance(entry, dict):
                continue
            event = entry.get("event")
            state = entry.get("paranoid_state")
            if not isinstance(event, str) or not isinstance(state, str):
                continue

            bucket = by_event.setdefault(event, {
                "event_class": entry.get("event_class", MISSING_FIELD),
                "default_status_tally": {},
                "lowered_status_tally": {},
                "gating_eligible_values": [],
                "gating_reasons": set(),
                "raw_line": None,
                "run_ids": set(),
            })

            status = entry.get("status", MISSING_FIELD)
            tally = (
                bucket["default_status_tally"] if state == probe_perf_events.PARANOID_STATE_DEFAULT
                else bucket["lowered_status_tally"]
            )
            tally[status] = tally.get(status, 0) + 1

            gating_eligible = entry.get("gating_eligible")
            if isinstance(gating_eligible, bool):
                bucket["gating_eligible_values"].append(gating_eligible)
            reason = entry.get("reason")
            if isinstance(reason, str):
                bucket["gating_reasons"].add(reason)
            if bucket["raw_line"] is None and isinstance(entry.get("raw_line"), str):
                bucket["raw_line"] = entry["raw_line"]
            if isinstance(run_id, str):
                bucket["run_ids"].add(run_id)

    section: list[dict[str, Any]] = []
    for event, bucket in by_event.items():
        n = len(bucket["run_ids"])
        if n < min_n or not bucket["gating_eligible_values"]:
            gating_eligible: Any = INSUFFICIENT_SAMPLES
            gating_reason: Any = INSUFFICIENT_SAMPLES
        else:
            gating_eligible = all(bucket["gating_eligible_values"])
            gating_reason = sorted(bucket["gating_reasons"]) if bucket["gating_reasons"] else None

        section.append({
            "event": event,
            "event_class": bucket["event_class"],
            "n": n,
            "default_status_tally": dict(sorted(bucket["default_status_tally"].items())),
            "lowered_status_tally": dict(sorted(bucket["lowered_status_tally"].items())),
            "gating_eligible": gating_eligible,
            "gating_reason": gating_reason,
            "evidence_raw_line": bucket["raw_line"],
        })

    section.sort(key=lambda item: item["event"])
    return section


def build_instrument_section(records: list[dict[str, Any]], min_n: int) -> list[dict[str, Any]]:
    """One entry per instrument name, in sorted order.

    Reports the availability tally, the median measured overhead multiplier
    with its own sample count, the repeat-count tally behind those
    measurements, the tally of repeatability verdicts, the tally of graded
    verdicts, and the disqualifying overhead threshold applied. Two
    instruments that happen to share a median multiplier keep separate
    entries -- aggregation is per instrument name, never merged across names.
    An instrument with zero usable overhead samples renders the
    insufficient-samples sentinel rather than a computed multiplier.
    """
    by_name: dict[str, dict[str, Any]] = {}

    for record in records:
        instruments = record.get("instruments")
        if not isinstance(instruments, list):
            continue
        run_id = record.get("_run_id")

        for entry in instruments:
            if not isinstance(entry, dict):
                continue
            name = entry.get("name")
            if not isinstance(name, str):
                continue

            bucket = by_name.setdefault(name, {
                "availability_tally": {},
                "overhead_values": [],
                "repeats_tally": {},
                "repeatability_verdict_tally": {},
                "verdict_tally": {},
                "overhead_disqualify_threshold": None,
                "run_ids": set(),
            })

            available_key = "available" if entry.get("available") is True else "unavailable"
            bucket["availability_tally"][available_key] = bucket["availability_tally"].get(available_key, 0) + 1

            overhead = entry.get("overhead_multiplier")
            if isinstance(overhead, (int, float)) and not isinstance(overhead, bool):
                bucket["overhead_values"].append(float(overhead))

            repeats = entry.get("repeats")
            if isinstance(repeats, int) and not isinstance(repeats, bool):
                key = str(repeats)
                bucket["repeats_tally"][key] = bucket["repeats_tally"].get(key, 0) + 1

            repeatability = entry.get("repeatability")
            if isinstance(repeatability, dict):
                verdict = repeatability.get("verdict", MISSING_FIELD)
                bucket["repeatability_verdict_tally"][verdict] = (
                    bucket["repeatability_verdict_tally"].get(verdict, 0) + 1
                )

            verdict = entry.get("verdict", MISSING_FIELD)
            bucket["verdict_tally"][verdict] = bucket["verdict_tally"].get(verdict, 0) + 1

            threshold = entry.get("overhead_disqualify_threshold")
            if isinstance(threshold, (int, float)) and not isinstance(threshold, bool):
                bucket["overhead_disqualify_threshold"] = threshold

            if isinstance(run_id, str):
                bucket["run_ids"].add(run_id)

    section: list[dict[str, Any]] = []
    for name, bucket in by_name.items():
        median, overhead_n = _median_or_insufficient(bucket["overhead_values"], min_n)
        if isinstance(median, float):
            median = _sidecar_float(median)

        section.append({
            "name": name,
            "n": len(bucket["run_ids"]),
            "availability_tally": dict(sorted(bucket["availability_tally"].items())),
            "overhead_multiplier_median": median,
            "overhead_multiplier_n": overhead_n,
            "repeats_tally": dict(sorted(bucket["repeats_tally"].items())),
            "repeatability_verdict_tally": dict(sorted(bucket["repeatability_verdict_tally"].items())),
            "verdict_tally": dict(sorted(bucket["verdict_tally"].items())),
            "overhead_disqualify_threshold": bucket["overhead_disqualify_threshold"],
        })

    section.sort(key=lambda item: item["name"])
    return section


def _confirmation_admission_marker(verdict_tally: dict[str, int], exercised: bool) -> str:
    """The derived deterministic-tier admission marker for one repeatability
    verdict tally (either a single module-and-instrument pair's own tally, or
    an instrument's tally unioned across every module that exercised it).

    `derived-not-exercised` when the confirmation leg never actually ran this
    pairing against real code at all (every record shows it `skipped`).
    `derived-ineligible-count-unstable` when at least one recorded verdict is
    `unstable`, regardless of how many are `bit-identical` -- one unstable
    module is disqualifying, never averaged away by other modules agreeing.
    `derived-eligible-count-stable` only when at least one recorded verdict
    is `bit-identical` and none is `unstable`. The insufficient-samples
    sentinel otherwise, for example every confirmation attempt failed before
    a count was ever taken. This marker is computed by this aggregator; no
    probe run ever records it.
    """
    if not exercised:
        return DERIVED_ADMISSION_NOT_EXERCISED
    if verdict_tally.get(probe_instruments.VERDICT_UNSTABLE, 0) > 0:
        return DERIVED_ADMISSION_INELIGIBLE
    if verdict_tally.get(probe_instruments.VERDICT_BIT_IDENTICAL, 0) > 0:
        return DERIVED_ADMISSION_ELIGIBLE
    return INSUFFICIENT_SAMPLES


def build_confirmation_section(records: list[dict[str, Any]], min_n: int) -> dict[str, Any]:
    """Aggregate the confirmation leg's real-module repeatability evidence
    from `confirmation.modules[*].instruments[*]` across the committed
    population.

    Follows `build_instrument_section`'s own contract: tolerates every
    absent or wrongly typed key without raising, tallies rather than
    collapses multi-run evidence into a single verdict, and sorts every
    emitted collection. A record whose `confirmation` key is absent, empty,
    or not a dict contributes nothing.

    Returns a dict with three parts: `per_module` (one entry per
    module-and-instrument pair, each carrying its own derived admission
    marker), `by_instrument` (one entry per instrument name, its
    repeatability verdict tally unioned across every module that exercised
    it, and an instrument-level admission marker derived the same way), and
    `excluded_instruments` (the deduplicated reason set for every instrument
    the confirmation leg deliberately never wires into any module at all).

    `min_n` is accepted for signature symmetry with the other section
    builders in this module; the confirmation leg's own per-record repeat
    count (not the number of records) is what governs whether a given
    pairing's repeatability verdict is itself insufficient-samples, so no
    additional suppression is applied here on top of that.
    """
    del min_n  # accepted for contract symmetry; see docstring

    by_pair: dict[tuple[str, str], dict[str, Any]] = {}
    excluded_reasons: dict[str, set[str]] = {}

    for record in records:
        confirmation = record.get("confirmation")
        if not isinstance(confirmation, dict):
            continue
        run_id = record.get("_run_id")

        excluded = confirmation.get("excluded_instruments")
        if isinstance(excluded, dict):
            for name, reason in excluded.items():
                if isinstance(name, str) and isinstance(reason, str):
                    excluded_reasons.setdefault(name, set()).add(reason)

        modules = confirmation.get("modules")
        if not isinstance(modules, dict):
            continue

        for module_path, module_entry in modules.items():
            if not isinstance(module_path, str) or not isinstance(module_entry, dict):
                continue
            instruments = module_entry.get("instruments")
            if not isinstance(instruments, dict):
                continue

            for instrument_name, instrument_entry in instruments.items():
                if not isinstance(instrument_name, str) or not isinstance(instrument_entry, dict):
                    continue

                bucket = by_pair.setdefault((module_path, instrument_name), {
                    "status_tally": {},
                    "repeats_tally": {},
                    "repeatability_verdict_tally": {},
                    "skip_reasons": set(),
                    "run_ids": set(),
                })

                status = instrument_entry.get("status", MISSING_FIELD)
                bucket["status_tally"][status] = bucket["status_tally"].get(status, 0) + 1

                repeats = instrument_entry.get("repeats")
                if isinstance(repeats, int) and not isinstance(repeats, bool):
                    key = str(repeats)
                    bucket["repeats_tally"][key] = bucket["repeats_tally"].get(key, 0) + 1

                repeatability = instrument_entry.get("repeatability")
                if isinstance(repeatability, dict):
                    verdict = repeatability.get("verdict", MISSING_FIELD)
                    bucket["repeatability_verdict_tally"][verdict] = (
                        bucket["repeatability_verdict_tally"].get(verdict, 0) + 1
                    )

                if status == CONFIRMATION_STATUS_SKIPPED:
                    reason = instrument_entry.get("reason")
                    if isinstance(reason, str):
                        bucket["skip_reasons"].add(reason)

                if isinstance(run_id, str):
                    bucket["run_ids"].add(run_id)

    per_module: list[dict[str, Any]] = []
    by_instrument_accum: dict[str, dict[str, Any]] = {}

    for (module_path, instrument_name), bucket in by_pair.items():
        status_tally = dict(sorted(bucket["status_tally"].items()))
        exercised = any(status != CONFIRMATION_STATUS_SKIPPED for status in bucket["status_tally"])
        verdict_tally = dict(sorted(bucket["repeatability_verdict_tally"].items()))
        marker = _confirmation_admission_marker(verdict_tally, exercised)

        per_module.append({
            "module": module_path,
            "instrument": instrument_name,
            "n": len(bucket["run_ids"]),
            "status_tally": status_tally,
            "repeats_tally": dict(sorted(bucket["repeats_tally"].items())),
            "repeatability_verdict_tally": verdict_tally,
            "skip_reasons": sorted(bucket["skip_reasons"]),
            "admission": marker,
        })

        instrument_bucket = by_instrument_accum.setdefault(instrument_name, {
            "repeatability_verdict_tally": {},
            "modules": set(),
            "exercised": False,
        })
        for verdict, count in verdict_tally.items():
            instrument_bucket["repeatability_verdict_tally"][verdict] = (
                instrument_bucket["repeatability_verdict_tally"].get(verdict, 0) + count
            )
        if exercised:
            instrument_bucket["modules"].add(module_path)
            instrument_bucket["exercised"] = True

    per_module.sort(key=lambda item: (item["module"], item["instrument"]))

    by_instrument: dict[str, dict[str, Any]] = {}
    for instrument_name, bucket in by_instrument_accum.items():
        verdict_tally = dict(sorted(bucket["repeatability_verdict_tally"].items()))
        marker = _confirmation_admission_marker(verdict_tally, bucket["exercised"])
        by_instrument[instrument_name] = {
            "repeatability_verdict_tally": verdict_tally,
            "modules": sorted(bucket["modules"]),
            "admission": marker,
        }

    return {
        "per_module": per_module,
        "by_instrument": dict(sorted(by_instrument.items())),
        "excluded_instruments": {
            name: sorted(reasons) for name, reasons in sorted(excluded_reasons.items())
        },
    }


def build_steal_section(records: list[dict[str, Any]], min_n: int) -> dict[str, Any]:
    """Pool every measurement window sampled across the whole population.

    Windows are ordered deterministically (env_fingerprint.order_windows,
    tie-broken by label) before the distribution is computed, so windows
    sharing an identical steal fraction never reorder between invocations.
    Reports the steal-time distribution (count, median, extremes, and the
    flagged-window count against the recorded threshold and comparison
    operator) and the cgroup v2 throttling figures in their own, permanently
    separate block -- the two signals are never combined into one rendered
    cell. A population with zero windows renders the zero-window condition
    and suppresses the distribution rather than reporting zeros, since a
    distribution of zeros would read as a quiet host when nothing was
    measured at all.
    """
    all_windows: list[dict[str, Any]] = []
    for record in records:
        windows = record.get("windows")
        if isinstance(windows, list):
            all_windows.extend(window for window in windows if isinstance(window, dict))

    ordered = env_fingerprint.order_windows(all_windows)

    if not ordered:
        return {
            "window_count": 0,
            "status": ZERO_WINDOWS,
            "steal": None,
            "cgroup_throttling": None,
        }

    def _numeric(values: list[Any]) -> list[float]:
        return [float(value) for value in values if isinstance(value, (int, float)) and not isinstance(value, bool)]

    steal_values = _numeric([window.get("steal_fraction") for window in ordered])
    flagged_count = sum(1 for window in ordered if window.get("steal_flagged") is True)
    threshold = next(
        (window["steal_threshold"] for window in ordered if isinstance(window.get("steal_threshold"), (int, float))),
        None,
    )
    comparison = next(
        (window["steal_comparison"] for window in ordered if isinstance(window.get("steal_comparison"), str)),
        None,
    )

    if steal_values:
        steal_stats = perf_noise_report.suppress_below_min_n(
            _round_floats(perf_noise_report.dispersion(steal_values)), min_n,
        )
    else:
        steal_stats = {"n": 0, "median": INSUFFICIENT_SAMPLES}

    cgroup_periods = _numeric([window.get("cgroup_nr_periods_delta") for window in ordered])
    cgroup_throttled_periods = _numeric([window.get("cgroup_nr_throttled_delta") for window in ordered])
    cgroup_throttled_usec = _numeric([window.get("cgroup_throttled_usec_delta") for window in ordered])

    return {
        "window_count": len(ordered),
        "status": "ok",
        "steal": {
            "samples": steal_values,
            "stats": steal_stats,
            "flagged_count": flagged_count,
            "threshold": threshold,
            "comparison": comparison,
        },
        "cgroup_throttling": {
            "n": len(cgroup_periods),
            "total_periods": sum(cgroup_periods) if cgroup_periods else INSUFFICIENT_SAMPLES,
            "total_throttled_periods": (
                sum(cgroup_throttled_periods) if cgroup_throttled_periods else INSUFFICIENT_SAMPLES
            ),
            "total_throttled_usec": sum(cgroup_throttled_usec) if cgroup_throttled_usec else INSUFFICIENT_SAMPLES,
        },
    }


def build_calibration_section(records: list[dict[str, Any]], min_n: int) -> dict[str, Any]:
    """Per calibration component, report the within-host dispersion (the
    pooled within-group dispersion of the per-run repeat samples, grouped by
    host) and the across-host dispersion (the dispersion of each host
    group's own median, one value per host), each with its own sample count
    and suppressed below `min_n`.

    Reuses perf_noise_report.variance_split and perf_noise_report.dispersion
    directly, matching the within-versus-pooled dispersion contract those
    functions already established for the companion noise-floor report.
    """
    values_by_host_by_component: dict[str, dict[str, list[float]]] = {
        name: {} for name in CALIBRATION_COMPONENTS
    }

    for record in records:
        calibration = record.get("calibration")
        calibration = calibration if isinstance(calibration, dict) else {}
        components = calibration.get("components")
        components = components if isinstance(components, dict) else {}
        host_model = _host_model_key(record)

        for name in CALIBRATION_COMPONENTS:
            component = components.get(name)
            if not isinstance(component, dict):
                continue
            samples = component.get("samples")
            if not isinstance(samples, list):
                continue
            numeric_samples = [
                float(sample) for sample in samples
                if isinstance(sample, (int, float)) and not isinstance(sample, bool)
            ]
            if not numeric_samples:
                continue
            values_by_host_by_component[name].setdefault(host_model, []).extend(numeric_samples)

    section: dict[str, Any] = {}
    for name in CALIBRATION_COMPONENTS:
        values_by_host = values_by_host_by_component[name]

        within_host = perf_noise_report.suppress_below_min_n(
            _round_floats(perf_noise_report.variance_split(values_by_host)), min_n,
        )

        host_medians = [statistics.median(values) for values in values_by_host.values() if values]
        if host_medians:
            across_host = perf_noise_report.suppress_below_min_n(
                _round_floats(perf_noise_report.dispersion(host_medians)), min_n,
            )
        else:
            across_host = {"n": 0, "median": INSUFFICIENT_SAMPLES, "cv": INSUFFICIENT_SAMPLES}

        section[name] = {"within_host": within_host, "across_host": across_host}

    return section


def build_intervention_section(records: list[dict[str, Any]], min_n: int) -> list[dict[str, Any]]:
    """One row per intervention name, in sorted order, aggregated across the
    whole population.

    Reports both baselines and the drift with their own sample counts, the
    drift threshold, and either the pooled effect ratio or the contaminated
    sentinel -- never both, and a contaminated run's own effect ratio is
    never folded into the numeric pool. An intervention recorded as
    not-applicable contributes its reason, never a fabricated zero effect.
    """
    by_name: dict[str, dict[str, Any]] = {}

    for record in records:
        interventions = record.get("interventions")
        if not isinstance(interventions, list):
            continue

        for entry in interventions:
            if not isinstance(entry, dict):
                continue
            name = entry.get("intervention")
            if not isinstance(name, str):
                continue

            bucket = by_name.setdefault(name, {
                "status_tally": {},
                "not_applicable_reasons": set(),
                "baseline_1_values": [],
                "baseline_2_values": [],
                "drift_values": [],
                "drift_threshold": None,
                "contaminated_count": 0,
                "effect_ratio_values": [],
            })

            status = entry.get("status", MISSING_FIELD)
            bucket["status_tally"][status] = bucket["status_tally"].get(status, 0) + 1

            if status == probe_interventions.NOT_APPLICABLE:
                reason = entry.get("reason")
                if isinstance(reason, str):
                    bucket["not_applicable_reasons"].add(reason)
                continue

            for key, values_key in (
                ("baseline_1", "baseline_1_values"),
                ("baseline_2", "baseline_2_values"),
            ):
                value = entry.get(key)
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    bucket[values_key].append(float(value))

            drift = entry.get("drift_ratio")
            if isinstance(drift, (int, float)) and not isinstance(drift, bool):
                bucket["drift_values"].append(float(drift))

            threshold = entry.get("drift_threshold")
            if isinstance(threshold, (int, float)) and not isinstance(threshold, bool):
                bucket["drift_threshold"] = threshold

            if entry.get("contaminated") is True:
                bucket["contaminated_count"] += 1
            else:
                effect_ratio = entry.get("effect_ratio")
                if isinstance(effect_ratio, (int, float)) and not isinstance(effect_ratio, bool):
                    bucket["effect_ratio_values"].append(float(effect_ratio))

    section: list[dict[str, Any]] = []
    for name, bucket in by_name.items():
        baseline_1_median, baseline_1_n = _median_or_insufficient(bucket["baseline_1_values"], min_n)
        baseline_2_median, baseline_2_n = _median_or_insufficient(bucket["baseline_2_values"], min_n)
        drift_median, drift_n = _median_or_insufficient(bucket["drift_values"], min_n)

        if bucket["effect_ratio_values"]:
            effect_ratio, effect_ratio_n = _median_or_insufficient(bucket["effect_ratio_values"], min_n)
        elif bucket["contaminated_count"] > 0:
            effect_ratio, effect_ratio_n = CONTAMINATED, 0
        else:
            effect_ratio, effect_ratio_n = INSUFFICIENT_SAMPLES, 0

        if isinstance(baseline_1_median, float):
            baseline_1_median = _sidecar_float(baseline_1_median)
        if isinstance(baseline_2_median, float):
            baseline_2_median = _sidecar_float(baseline_2_median)
        if isinstance(drift_median, float):
            drift_median = _sidecar_float(drift_median)
        if isinstance(effect_ratio, float):
            effect_ratio = _sidecar_float(effect_ratio)

        section.append({
            "intervention": name,
            "status_tally": dict(sorted(bucket["status_tally"].items())),
            "not_applicable_reasons": sorted(bucket["not_applicable_reasons"]),
            "baseline_1_median": baseline_1_median,
            "baseline_1_n": baseline_1_n,
            "baseline_2_median": baseline_2_median,
            "baseline_2_n": baseline_2_n,
            "drift_median": drift_median,
            "drift_n": drift_n,
            "drift_threshold": bucket["drift_threshold"],
            "contaminated_count": bucket["contaminated_count"],
            "effect_ratio": effect_ratio,
            "effect_ratio_n": effect_ratio_n,
        })

    section.sort(key=lambda item: item["intervention"])
    return section


def _cgroup_stat_row_value(stat: Any, key: str) -> Any:
    """One cgroup_v2_cpu_stat column's value for the detail section: the
    counter itself when `stat` is a populated dict, the sentinel string
    verbatim when `stat` is the collected-but-unreadable sentinel (so a
    reader sees why every counter column is unreadable rather than a
    misleading absent-field sentinel), or MISSING_FIELD when the key is
    absent entirely.
    """
    if isinstance(stat, dict):
        return stat.get(key, MISSING_FIELD)
    if isinstance(stat, str):
        return stat
    return MISSING_FIELD


def build_cgroup_and_timer_section(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Per-run raw cgroup v2 cpu.stat state, the recorded CPU quota, and the
    systemd timer unit-set inventory, aggregated across the whole population.

    The cpu.stat column set is the sorted union of every key observed across
    the population rather than a hardcoded list, so a future kernel exposing
    a different counter set still renders in full. A run missing
    `cgroup_v2_cpu_stat` contributes a row of absent-field sentinels rather
    than being dropped. The systemd timer inventory reuses
    `_build_unit_set_labels`/`_systemd_unit_names`, the exact derivation the
    fingerprint table's systemd column formatter uses, so a run's fingerprint
    cell and its inventory row can never disagree on which label names its
    unit set. Rows and inventory entries are both sorted deterministically
    (by run identifier, and by the unit-name tuple itself) so the section is
    byte-stable across invocations.
    """
    stat_keys: set[str] = set()
    for record in records:
        fingerprint = record.get("fingerprint")
        fingerprint = fingerprint if isinstance(fingerprint, dict) else {}
        stat = fingerprint.get("cgroup_v2_cpu_stat")
        if isinstance(stat, dict):
            stat_keys.update(stat.keys())
    stat_columns = sorted(stat_keys)

    cgroup_rows: list[dict[str, Any]] = []
    timer_lists: list[Any] = []
    set_run_counts: dict[tuple[str, ...], int] = {}

    for record in records:
        fingerprint = record.get("fingerprint")
        fingerprint = fingerprint if isinstance(fingerprint, dict) else {}
        stat = fingerprint.get("cgroup_v2_cpu_stat")

        row: dict[str, Any] = {"run_id": record.get("_run_id", MISSING_FIELD)}
        for key in stat_columns:
            row[key] = _cgroup_stat_row_value(stat, key)
        row["cgroup_v2_cpu_max"] = fingerprint.get("cgroup_v2_cpu_max", MISSING_FIELD)
        cgroup_rows.append(row)

        timers = fingerprint.get("systemd_timers")
        timer_lists.append(timers)
        names = _systemd_unit_names(timers)
        if names:
            set_run_counts[names] = set_run_counts.get(names, 0) + 1

    cgroup_rows.sort(key=lambda row: row["run_id"])

    unit_set_labels = _build_unit_set_labels(timer_lists)
    timer_inventory = [
        {
            "label": unit_set_labels[names],
            "unit_count": len(names),
            "run_count": set_run_counts[names],
            "unit_names": list(names),
        }
        for names in sorted(set_run_counts)
    ]

    return {
        "cgroup_stat_columns": stat_columns,
        "cgroup_rows": cgroup_rows,
        "timer_inventory": timer_inventory,
    }


def build_sidecar(
    population: dict[str, Any],
    min_n: int,
    expected_tree_hash: str | None,
    target_cpu_models: list[str],
    run_cap: int | None,
    runs_dir: str,
) -> dict[str, Any]:
    accepted = population["accepted"]

    return {
        "sidecar_version": SIDECAR_VERSION,
        "source": {
            "runs_dir": runs_dir,
            "record_count": len(accepted),
            "records_skipped": population["skipped_count"],
            "skipped_reasons": population["skipped_reasons"],
            "records_rejected": population["rejected_count"],
            "rejected_reasons": population["rejected_reasons"],
        },
        "parameters": {
            "min_n": min_n,
            "expected_tree_hash": expected_tree_hash,
            "target_cpu_models": sorted(target_cpu_models),
            "run_cap": run_cap,
        },
        "coverage": build_coverage_section(accepted, target_cpu_models, run_cap),
        "fingerprint_runs": build_fingerprint_section(accepted),
        "cgroup_and_timer": build_cgroup_and_timer_section(accepted),
        "perf_events": build_perf_event_section(accepted, min_n),
        "instruments": build_instrument_section(accepted, min_n),
        "confirmation": build_confirmation_section(accepted, min_n),
        "steal": build_steal_section(accepted, min_n),
        "calibration": build_calibration_section(accepted, min_n),
        "interventions": build_intervention_section(accepted, min_n),
    }


def _render_perf_event_section(entries: list[dict[str, Any]]) -> list[str]:
    lines = [
        "## Perf events",
        "",
        "One row per perf event name observed across the committed population. An event "
        f"observed in fewer runs than the configured minimum renders `{INSUFFICIENT_SAMPLES}` "
        "for its gating verdict while its raw per-run status tallies remain listed as direct "
        "evidence.",
        "",
        "| Event | Class | n | Default-state statuses | Lowered-state statuses | "
        "Gating eligible | Reason | Evidence |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for entry in entries:
        reason = entry["gating_reason"]
        reason_cell = ", ".join(reason) if isinstance(reason, list) else _fmt_cell(reason)
        evidence = entry["evidence_raw_line"] if entry["evidence_raw_line"] is not None else "(none)"
        lines.append(
            "| " + " | ".join([
                entry["event"],
                _fmt_cell(entry["event_class"]),
                str(entry["n"]),
                _fmt_tally(entry["default_status_tally"]),
                _fmt_tally(entry["lowered_status_tally"]),
                _fmt_cell(entry["gating_eligible"]),
                reason_cell,
                f"`{evidence}`",
            ]) + " |"
        )
    lines.append("")
    return lines


def _render_instrument_section(
    entries: list[dict[str, Any]], confirmation_by_instrument: dict[str, Any],
) -> list[str]:
    lines = [
        "## Instruments",
        "",
        "One row per instrument name, in sorted order. An instrument with zero usable "
        f"overhead samples renders `{INSUFFICIENT_SAMPLES}` instead of a computed multiplier. "
        "The \"Repeatability verdicts\" and \"Graded verdicts\" columns are transcribed "
        "exactly as each probe run recorded them from the synthetic workload sweep; this "
        "report never rewrites either. \"Confirmation (real modules)\" is a different "
        "signal: this report's own aggregation of the confirmation leg's repeatability "
        "verdicts against shipped code, detailed in the section immediately below, with an "
        "admission marker this report computes and no probe run ever records. Where the "
        "synthetic sweep's graded verdict and the confirmation column disagree, the "
        "confirmation column -- real-module evidence -- is the one that bears on "
        "deterministic-tier admission.",
        "",
        "| Instrument | n | Availability | Median overhead (n) | Repeats | "
        "Repeatability verdicts | Graded verdicts | Disqualify threshold | "
        "Confirmation (real modules) |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for entry in entries:
        median_cell = _fmt_cell(entry["overhead_multiplier_median"])
        confirmation_entry = confirmation_by_instrument.get(entry["name"])
        if confirmation_entry is None:
            confirmation_cell = f"(none) ({DERIVED_ADMISSION_NOT_EXERCISED})"
        else:
            confirmation_cell = (
                f"{_fmt_tally(confirmation_entry['repeatability_verdict_tally'])} "
                f"({confirmation_entry['admission']})"
            )
        lines.append(
            "| " + " | ".join([
                entry["name"],
                str(entry["n"]),
                _fmt_tally(entry["availability_tally"]),
                f"{median_cell} (n={entry['overhead_multiplier_n']})",
                _fmt_tally(entry["repeats_tally"]),
                _fmt_tally(entry["repeatability_verdict_tally"]),
                _fmt_tally(entry["verdict_tally"]),
                _fmt_cell(entry["overhead_disqualify_threshold"]),
                confirmation_cell,
            ]) + " |"
        )
    lines.append("")
    return lines


def _render_confirmation_section(section: dict[str, Any]) -> list[str]:
    per_module = section["per_module"]
    by_instrument = section["by_instrument"]
    excluded_instruments = section["excluded_instruments"]

    modules = sorted({item["module"] for item in per_module})
    repeats_seen = sorted({repeats for item in per_module for repeats in item["repeats_tally"]})
    repeats_label = ", ".join(repeats_seen) if repeats_seen else MISSING_FIELD

    lines = [
        "## Confirmation leg: repeatability against real modules",
        "",
        "The confirmation leg re-runs each surviving cheap instrument against shipped code in "
        f"real `tests/perf` modules ({', '.join(modules) if modules else '(none)'}), one from "
        "each of Phase 1's two measured populations, at "
        f"{repeats_label} in-job repeats per module. The \"Admission (derived)\" column below "
        "is computed by this report from the repeatability verdicts in the rows beneath it; it "
        "is not a value any probe run recorded. Where this real-module evidence disagrees with "
        "the synthetic sweep's own graded verdict in the Instruments section above, this "
        "evidence is the one that bears on deterministic-tier admission.",
        "",
        "### Per module and instrument",
        "",
        "| Module | Instrument | n | Status tally | Repeats | Repeatability verdicts | "
        "Skip reasons | Admission (derived) |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for item in per_module:
        skip_reasons_cell = ", ".join(item["skip_reasons"]) if item["skip_reasons"] else "(none)"
        lines.append(
            "| " + " | ".join([
                item["module"],
                item["instrument"],
                str(item["n"]),
                _fmt_tally(item["status_tally"]),
                _fmt_tally(item["repeats_tally"]),
                _fmt_tally(item["repeatability_verdict_tally"]),
                skip_reasons_cell,
                item["admission"],
            ]) + " |"
        )
    lines.append("")

    lines.append("### By instrument, across every module that exercised it")
    lines.append("")
    lines.append("| Instrument | Repeatability verdicts | Modules exercised | Admission (derived) |")
    lines.append("|---|---|---|---|")
    for name, entry in by_instrument.items():
        modules_cell = ", ".join(entry["modules"]) if entry["modules"] else "(none)"
        lines.append(
            "| " + " | ".join([
                name,
                _fmt_tally(entry["repeatability_verdict_tally"]),
                modules_cell,
                entry["admission"],
            ]) + " |"
        )
    lines.append("")

    lines.append("### Instruments the confirmation leg never wires into any module")
    lines.append("")
    if not excluded_instruments:
        lines.append("- (none)")
    else:
        for name, reasons in excluded_instruments.items():
            lines.append(f"- `{name}`: {', '.join(reasons)}")
    lines.append("")
    return lines


def _render_steal_section(steal_section: dict[str, Any]) -> list[str]:
    lines = [
        "## Steal time and cgroup throttling",
        "",
        "Hypervisor steal time and cgroup v2 CFS throttling are two independently sampled "
        "signals with different root causes and different remedies; no rendered cell here "
        "ever combines them.",
        "",
    ]
    if steal_section["status"] == ZERO_WINDOWS:
        lines.append(
            f"- Window count: 0 (`{ZERO_WINDOWS}`) -- the distribution is suppressed rather "
            "than reported as zero, since a zero-valued distribution would read as a quiet "
            "host when nothing was measured."
        )
        lines.append("")
        return lines

    steal = steal_section["steal"]
    cgroup = steal_section["cgroup_throttling"]
    stats = steal["stats"]

    lines.append(f"- Window count: {steal_section['window_count']}")
    lines.append("")
    lines.append("### Steal-time distribution")
    lines.append("")
    lines.append("| n | median | min | max | flagged | threshold | comparison |")
    lines.append("|---|---|---|---|---|---|---|")
    lines.append(
        "| " + " | ".join([
            str(stats.get("n")),
            _fmt_cell(stats.get("median")),
            _fmt_cell(stats.get("minimum")),
            _fmt_cell(stats.get("maximum")),
            str(steal["flagged_count"]),
            _fmt_cell(steal["threshold"]),
            _fmt_cell(steal["comparison"]),
        ]) + " |"
    )
    lines.append("")
    lines.append("### cgroup v2 throttling")
    lines.append("")
    lines.append("| n | total periods | total throttled periods | total throttled usec |")
    lines.append("|---|---|---|---|")
    lines.append(
        "| " + " | ".join([
            str(cgroup["n"]),
            _fmt_cell(cgroup["total_periods"]),
            _fmt_cell(cgroup["total_throttled_periods"]),
            _fmt_cell(cgroup["total_throttled_usec"]),
        ]) + " |"
    )
    lines.append("")
    return lines


def _render_cgroup_and_timer_section(section: dict[str, Any]) -> list[str]:
    lines = [
        "## cgroup v2 cpu.stat and systemd timer state",
        "",
        "Per-run raw fingerprint state. This is distinct from the Steal section's cgroup v2 "
        "throttling block above, which pools a derived total across sampled measurement "
        "windows; the table below instead reports each run's own recorded cpu.stat counters "
        "and CPU quota exactly as collected. Systemd timer state is reported as the unit "
        "inventory below rather than the raw schedule lines, since those lines carry "
        "per-run next-fire and last-fire wall-clock timestamps and this report's "
        "byte-stability contract admits no wall-clock values into its output.",
        "",
        "### cgroup v2 cpu.stat, per run",
        "",
    ]

    stat_columns = section["cgroup_stat_columns"]
    lines.append("| Run | " + " | ".join(stat_columns) + " | cgroup v2 cpu.max |")
    lines.append("|---" * (len(stat_columns) + 2) + "|")
    for row in section["cgroup_rows"]:
        cells = [_fmt_cell(row[key]) for key in stat_columns]
        lines.append(
            "| " + row["run_id"] + " | " + " | ".join(cells) + " | "
            + _fmt_cell(row["cgroup_v2_cpu_max"]) + " |"
        )
    lines.append("")

    lines.append("### systemd timer unit inventory")
    lines.append("")
    timer_inventory = section["timer_inventory"]
    if not timer_inventory:
        lines.append(f"- No systemd timer lines observed anywhere in this population (`{NO_TIMERS_OBSERVED}`).")
        lines.append("")
        return lines

    lines.append("| Label | Unit count | Run count | Unit names |")
    lines.append("|---|---|---|---|")
    for entry in timer_inventory:
        lines.append(
            "| " + " | ".join([
                entry["label"],
                str(entry["unit_count"]),
                str(entry["run_count"]),
                ", ".join(entry["unit_names"]),
            ]) + " |"
        )
    lines.append("")
    return lines


def _render_calibration_section(calibration_section: dict[str, Any]) -> list[str]:
    lines = [
        "## Calibration vector dispersion",
        "",
        "Per component: within-host dispersion (the pooled dispersion of a host's own repeat "
        "samples) alongside across-host dispersion (the dispersion of each host's own median), "
        "so a calibrator noisier than the metric it would normalize is visible.",
        "",
        "| Component | Within-host n | Within-host CV | Across-host n | Across-host CV |",
        "|---|---|---|---|---|",
    ]
    for name in CALIBRATION_COMPONENTS:
        entry = calibration_section.get(name, {})
        within_host = entry.get("within_host", {})
        across_host = entry.get("across_host", {})
        lines.append(
            "| " + " | ".join([
                name,
                str(within_host.get("n")),
                _fmt_cell(within_host.get("within_cv")),
                str(across_host.get("n")),
                _fmt_cell(across_host.get("cv")),
            ]) + " |"
        )
    lines.append("")
    return lines


def _render_intervention_section(entries: list[dict[str, Any]]) -> list[str]:
    lines = [
        "## Interventions",
        "",
        "One row per intervention name, in sorted order. A contaminated comparison renders "
        f"`{CONTAMINATED}` and no effect ratio; a not-applicable intervention renders its "
        "reason and no numeric effect.",
        "",
        "| Intervention | Status tally | Not-applicable reasons | Baseline 1 (n) | "
        "Baseline 2 (n) | Drift (n) | Drift threshold | Contaminated | Effect ratio (n) |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for entry in entries:
        reasons = ", ".join(entry["not_applicable_reasons"]) if entry["not_applicable_reasons"] else "(none)"
        lines.append(
            "| " + " | ".join([
                entry["intervention"],
                _fmt_tally(entry["status_tally"]),
                reasons,
                f"{_fmt_cell(entry['baseline_1_median'])} (n={entry['baseline_1_n']})",
                f"{_fmt_cell(entry['baseline_2_median'])} (n={entry['baseline_2_n']})",
                f"{_fmt_cell(entry['drift_median'])} (n={entry['drift_n']})",
                _fmt_cell(entry["drift_threshold"]),
                str(entry["contaminated_count"]),
                f"{_fmt_cell(entry['effect_ratio'])} (n={entry['effect_ratio_n']})",
            ]) + " |"
        )
    lines.append("")
    return lines


def _render_coverage_section(coverage: dict[str, Any]) -> list[str]:
    lines = [
        "## Coverage",
        "",
        "The requirement's floor is a run count, but the purpose is spread across distinct "
        "host models; this states which stopping condition actually ended the campaign.",
        "",
        f"- Accepted runs: {coverage['run_count']}",
        f"- Distinct host models observed: {coverage['distinct_host_model_count']}",
        f"- Coverage target (specific host models): {coverage['coverage_target'] or '(none configured)'}",
        f"- Run cap: {_fmt_cell(coverage['run_cap'])}",
        f"- Stopping condition: `{coverage['stopping_condition']}`",
        "",
        "| Host model | Run count |",
        "|---|---|",
    ]
    for model, count in coverage["host_model_run_counts"].items():
        lines.append(f"| {model} | {count} |")
    lines.append("")
    return lines


def render_markdown(sidecar: dict[str, Any]) -> str:
    source = sidecar["source"]
    lines = [
        "<!-- generated by scripts/probe_capability_report.py, do not edit by hand -->",
        "# Runner Capability Matrix",
        "",
        "## Reproducing this report",
        "",
        "```sh",
        CANONICAL_COMMAND,
        "```",
        "",
        "## Source",
        "",
        f"- Runs directory: `{source['runs_dir']}`",
        f"- Records parsed: {source['record_count']}",
        f"- Records skipped: {source['records_skipped']}",
        f"- Records rejected (tree hash mismatch): {source['records_rejected']}",
        "",
    ]
    lines.extend(_render_coverage_section(sidecar["coverage"]))
    lines.extend([
        "## Environment fingerprint",
        "",
        "One row per committed probe run. A cell reading "
        f"`{MISSING_FIELD}` means the field was absent from that run's record entirely, "
        "distinct from the probe's own "
        '"unavailable" sentinel, which means the field was collected but its source could '
        "not be read on that runner.",
        "",
        "| Run | " + " | ".join(label for _, label in FINGERPRINT_COLUMNS) + " |",
        "|---" * (len(FINGERPRINT_COLUMNS) + 1) + "|",
    ])
    unit_set_labels = _build_unit_set_labels(
        row.get("systemd_timers") for row in sidecar["fingerprint_runs"]
    )
    column_formatters: dict[str, Any] = dict(FINGERPRINT_COLUMN_FORMATTERS)
    column_formatters["systemd_timers"] = lambda value: _fmt_systemd_timers_cell(value, unit_set_labels)
    for row in sidecar["fingerprint_runs"]:
        cells = [column_formatters.get(key, _fmt_cell)(row[key]) for key, _ in FINGERPRINT_COLUMNS]
        lines.append("| " + row["run_id"] + " | " + " | ".join(cells) + " |")
    lines.append("")

    lines.extend(_render_cgroup_and_timer_section(sidecar["cgroup_and_timer"]))
    lines.extend(_render_perf_event_section(sidecar["perf_events"]))
    lines.extend(_render_instrument_section(sidecar["instruments"], sidecar["confirmation"]["by_instrument"]))
    lines.extend(_render_confirmation_section(sidecar["confirmation"]))
    lines.extend(_render_steal_section(sidecar["steal"]))
    lines.extend(_render_calibration_section(sidecar["calibration"]))
    lines.extend(_render_intervention_section(sidecar["interventions"]))

    return "\n".join(lines) + "\n"


def write_deterministic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--runs-dir",
        default=DEFAULT_RUNS_DIR,
        help="Directory containing committed per-run probe JSON files",
    )
    parser.add_argument(
        "--expected-tree-hash",
        default=None,
        help="git rev-parse HEAD^{tree} the campaign is pinned to; recorded now, "
        "enforcement lands in a later plan",
    )
    parser.add_argument(
        "--min-n",
        type=int,
        default=DEFAULT_MIN_N,
        help="Minimum sample count before a statistic is reported rather than suppressed",
    )
    parser.add_argument(
        "--target-cpu-models",
        default=None,
        help="Comma-separated target CPU models for coverage tracking; recorded now, "
        "enforcement lands in a later plan",
    )
    parser.add_argument(
        "--run-cap",
        type=int,
        default=None,
        help="Hard cap on campaign runs; recorded now, enforcement lands in a later plan",
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


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    runs_dir = Path(args.runs_dir)
    target_cpu_models = (
        [model.strip() for model in args.target_cpu_models.split(",") if model.strip()]
        if args.target_cpu_models
        else []
    )

    paths = sorted(runs_dir.glob("*.json")) if runs_dir.is_dir() else []
    population = build_population(paths, args.expected_tree_hash)

    if not population["accepted"]:
        print(
            "No probe-run records survived population membership. "
            f"Skipped (malformed/unrecognized schema): {population['skipped_count']}, "
            f"Rejected (tree hash mismatch): {population['rejected_count']}"
        )
        return 1

    sidecar = build_sidecar(
        population=population,
        min_n=args.min_n,
        expected_tree_hash=args.expected_tree_hash,
        target_cpu_models=target_cpu_models,
        run_cap=args.run_cap,
        runs_dir=str(runs_dir),
    )
    markdown = render_markdown(sidecar)

    write_deterministic_json(Path(args.out_json), sidecar)
    out_md = Path(args.out_md)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown, encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
