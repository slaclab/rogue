#!/usr/bin/env python3
# ----------------------------------------------------------------------------
# Title      : ROGUE Runner Capability Probe Interventions
# ----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
# ----------------------------------------------------------------------------

"""Paired within-job A/B/A intervention harness with contamination detection.

Every intervention (taskset pinning, background-service stopping) is
measured as baseline, intervention, treatment, revert, baseline again. The
second baseline is the point of the design: if the two baselines disagree
beyond a documented drift threshold, the job drifted mid-measurement and the
comparison is reported as contaminated rather than publishing a bogus
effect size.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import env_fingerprint  # noqa: E402  (flat sibling import, path inserted above)


NOT_APPLICABLE = "not_applicable"
CONTAMINATED = "contaminated"

ABA_DRIFT_THRESHOLD = 0.10
DRIFT_COMPARISON_OPERATOR = ">="

SUBPROCESS_TIMEOUT_SECONDS = 15


def measure_aba(
    workload_fn: Callable[[], float],
    intervene_fn: Callable[[], None],
    revert_fn: Callable[[], None],
    *,
    drift_threshold: float = ABA_DRIFT_THRESHOLD,
    window_sampler: Callable[[str, Callable[[], Any]], dict[str, Any]] = env_fingerprint.sample_cpu_window,
) -> dict[str, Any]:
    """Paired within-job A/B/A measurement: baseline, intervention, treatment,
    revert, second baseline -- never averaged, always compared.

    Each leg is wrapped in `window_sampler` (real callers pass
    `env_fingerprint.sample_cpu_window`) so every leg carries its own steal
    and cgroup throttling deltas. When the two baselines disagree by at
    least `drift_threshold`, the comparison is contaminated and `effect_ratio`
    holds the `CONTAMINATED` sentinel instead of a number, because publishing
    an effect size from a drifting host is exactly the false confidence this
    design exists to prevent.
    """
    notes: list[str] = []

    baseline_1_window = window_sampler("baseline_1", workload_fn)
    baseline_1 = baseline_1_window["result"]
    if baseline_1_window.get("steal_flagged"):
        notes.append("baseline_1 window was steal-flagged")

    intervene_fn()

    treatment_window = window_sampler("treatment", workload_fn)
    treatment = treatment_window["result"]
    if treatment_window.get("steal_flagged"):
        notes.append("treatment window was steal-flagged")

    revert_fn()

    baseline_2_window = window_sampler("baseline_2", workload_fn)
    baseline_2 = baseline_2_window["result"]
    if baseline_2_window.get("steal_flagged"):
        notes.append("baseline_2 window was steal-flagged")

    if not baseline_1:
        drift_ratio: Any = env_fingerprint.UNAVAILABLE
        contaminated = True
    else:
        drift_ratio = abs(baseline_2 - baseline_1) / baseline_1
        contaminated = drift_ratio >= drift_threshold

    effect_ratio: Any = CONTAMINATED if contaminated else treatment / baseline_1

    return {
        "baseline_1": baseline_1,
        "treatment": treatment,
        "baseline_2": baseline_2,
        "drift_ratio": drift_ratio,
        "drift_threshold": drift_threshold,
        "drift_comparison": DRIFT_COMPARISON_OPERATOR,
        "contaminated": contaminated,
        "effect_ratio": effect_ratio,
        "notes": notes,
        "windows": [baseline_1_window, treatment_window, baseline_2_window],
    }


def taskset_intervention(
    workload_fn: Callable[[], float],
    *,
    cpu_set: tuple[int, ...] = (0,),
    which_fn: Callable[[str], str | None] = shutil.which,
    window_sampler: Callable[[str, Callable[[], Any]], dict[str, Any]] = env_fingerprint.sample_cpu_window,
) -> dict[str, Any]:
    """Measure the taskset CPU-pinning intervention as a paired A/B/A.

    Gates on the `taskset` binary's presence (a `command -v`-style lookup)
    even though the actual pin/restore uses the standard-library affinity
    calls (`os.sched_setaffinity`/`os.sched_getaffinity`) rather than
    shelling out. When the binary is absent, returns a not-applicable entry
    with a reason and never a fabricated zero effect.
    """
    if which_fn("taskset") is None:
        return {
            "intervention": "taskset",
            "status": NOT_APPLICABLE,
            "reason": "taskset binary not found on PATH",
            "effect_ratio": NOT_APPLICABLE,
        }

    original_affinity = os.sched_getaffinity(0)

    def intervene() -> None:
        os.sched_setaffinity(0, set(cpu_set))

    def revert() -> None:
        os.sched_setaffinity(0, original_affinity)

    result = measure_aba(workload_fn, intervene, revert, window_sampler=window_sampler)
    result["intervention"] = "taskset"
    result["status"] = "measured"
    result["cpu_set"] = sorted(cpu_set)
    return result


def _run_systemctl_command(argv: list[str]) -> subprocess.CompletedProcess:
    """Run a privileged systemctl command, recording a failed invocation as
    a nonzero-returncode result rather than letting it raise -- an
    unavailable binary or a timeout is itself informative, not a crash.
    """
    try:
        return subprocess.run(
            argv, capture_output=True, text=True, timeout=SUBPROCESS_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return subprocess.CompletedProcess(argv, returncode=1, stdout="", stderr=str(exc))


def service_stop_intervention(
    observed_units: list[str],
    workload_fn: Callable[[], float],
    *,
    run_cmd: Callable[[list[str]], subprocess.CompletedProcess] = _run_systemctl_command,
    window_sampler: Callable[[str, Callable[[], Any]], dict[str, Any]] = env_fingerprint.sample_cpu_window,
) -> dict[str, Any]:
    """Measure the background-service-stop intervention as a paired A/B/A.

    `observed_units` is always a parameter supplied from what the run's own
    fingerprint actually observed running (never a pre-guessed list). Given
    an empty list, returns a not-applicable entry naming that reason. Given
    units, stops each one, measures, and restarts every unit it stopped in a
    `finally` block, so a raising treatment can never leave the runner with
    services down for the rest of the job.
    """
    if not observed_units:
        return {
            "intervention": "service_stop",
            "status": NOT_APPLICABLE,
            "reason": "no observed units supplied (empty observation)",
            "effect_ratio": NOT_APPLICABLE,
        }

    stop_records: list[dict[str, Any]] = []
    restart_records: list[dict[str, Any]] = []
    stopped_units: list[str] = []

    def intervene() -> None:
        for unit in observed_units:
            completed = run_cmd(["sudo", "systemctl", "stop", unit])
            stop_records.append({
                "unit": unit,
                "returncode": completed.returncode,
                "stderr": completed.stderr,
            })
            if completed.returncode == 0:
                stopped_units.append(unit)

    def revert() -> None:
        for unit in stopped_units:
            completed = run_cmd(["sudo", "systemctl", "start", unit])
            restart_records.append({
                "unit": unit,
                "returncode": completed.returncode,
                "stderr": completed.stderr,
            })

    try:
        result = measure_aba(workload_fn, intervene, revert, window_sampler=window_sampler)
    finally:
        if not restart_records and stopped_units:
            # revert() above was never reached inside measure_aba (the
            # treatment leg raised before the second baseline); restart
            # every stopped unit here so a raising treatment never leaves
            # the runner degraded for the rest of the job.
            revert()

    result["intervention"] = "service_stop"
    result["status"] = "measured"
    result["stop_records"] = stop_records
    result["restart_records"] = restart_records
    return result


def collect_interventions(
    workload_fn: Callable[[], float],
    observed_units: list[str],
    *,
    cpu_set: tuple[int, ...] = (0,),
    which_fn: Callable[[str], str | None] = shutil.which,
    run_cmd: Callable[[list[str]], subprocess.CompletedProcess] = _run_systemctl_command,
    window_sampler: Callable[[str, Callable[[], Any]], dict[str, Any]] = env_fingerprint.sample_cpu_window,
) -> list[dict[str, Any]]:
    """Collect both interventions, returned in name-sorted order."""
    entries = [
        taskset_intervention(
            workload_fn, cpu_set=cpu_set, which_fn=which_fn, window_sampler=window_sampler,
        ),
        service_stop_intervention(
            observed_units, workload_fn, run_cmd=run_cmd, window_sampler=window_sampler,
        ),
    ]
    return sorted(entries, key=lambda entry: entry["intervention"])


def _default_workload(iterations: int = 1000000) -> float:
    start_ns = time.perf_counter_ns()
    total = 0
    for i in range(iterations):
        total += i
    elapsed_ns = time.perf_counter_ns() - start_ns
    return iterations / (elapsed_ns * 1e-9)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the collected intervention entries as JSON",
    )
    parser.add_argument(
        "--observed-unit",
        action="append",
        default=[],
        dest="observed_units",
        help="A systemd unit name to include in the service-stop intervention "
        "(repeatable); defaults to none, which reports that intervention as "
        "not-applicable",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    entries = collect_interventions(_default_workload, args.observed_units)

    if args.json:
        print(json.dumps(entries, indent=2, sort_keys=True))
    else:
        for entry in entries:
            print(f"{entry['intervention']}: {entry.get('status')}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
