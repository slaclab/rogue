#!/usr/bin/env python3
# ----------------------------------------------------------------------------
# Title      : ROGUE Runner Perf Event Capability Probe
# ----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
# ----------------------------------------------------------------------------

"""Determine, from real perf output text, which hardware and software events
actually count on this runner.

The kernel.perf_event_paranoid sysctl writing successfully is not evidence
that the underlying performance monitoring unit is exposed to the guest: a
hypervisor can withhold PMU pass-through independent of the paranoid level.
Every status in this module's output is therefore derived from parsing the
actual `perf stat` output text for each requested event, never from whether
the sysctl write itself succeeded.

Installing the kernel-matched linux-tools package can legitimately fail on a
GitHub-hosted runner: Actions runners boot an Azure-flavored kernel, and
Ubuntu's linux-tools-$(uname -r) package has repeatedly gone missing for that
kernel flavor (the same class of problem scripts/ci_bring_up_soft_roce.sh
already documents for Soft-RoCE). A failed install is recorded as the finding
for that run, not raised as an error.
"""

from __future__ import annotations

import argparse
import json
import math
import platform
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Sequence

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import env_fingerprint  # noqa: E402  (flat sibling import, path inserted above)


SUBPROCESS_TIMEOUT_SECONDS = 15
STDERR_EXCERPT_MAX_CHARS = 2000

# perf event families this module probes. Disjoint by construction: event_class is
# derived from membership in exactly one of these two tuples, never from a
# hand-maintained third mapping.
PERF_HARDWARE_EVENTS: tuple[str, ...] = (
    "cycles", "instructions", "cache-references", "cache-misses", "branches", "branch-misses",
)
PERF_SOFTWARE_EVENTS: tuple[str, ...] = (
    "task-clock", "context-switches", "cpu-migrations", "page-faults", "minor-faults",
    "major-faults", "alignment-faults", "emulation-faults",
)

# Per-event classification vocabulary. Derived only from the actual output
# text of a real perf invocation, never from the paranoid sysctl value.
STATUS_COUNTED = "counted"
STATUS_NOT_SUPPORTED = "not-supported"
STATUS_NOT_PERMITTED = "not-permitted"
STATUS_UNPARSED = "unparsed"
STATUS_UNAVAILABLE = "unavailable"

NOT_SUPPORTED_MARKER = "<not supported>"
NOT_PERMITTED_MARKER = "permission denied"

PARANOID_STATE_DEFAULT = "default"
PARANOID_STATE_LOWERED = "lowered"
DEFAULT_LOWERED_PARANOID_VALUE = 0

REASON_TOOLING_UNAVAILABLE = "perf tooling did not install; see the install field for the captured error"
REASON_REQUIRES_LOWERED_PARANOID = (
    "counted only after lowering kernel.perf_event_paranoid; ineligible for the gating job "
    "because the gate must behave identically on every contributor pull request and on forks"
)
REASON_NOT_COUNTED_EITHER_STATE = "not counted in either paranoid state"

# The three packages attempted, in order, to install a kernel-matched perf
# binary: a missing kernel-matched package on the azure-flavored runner
# kernel is a known, currently recurring condition (see module docstring),
# and it is the finding for that run rather than an error.
PERF_COMMON_PACKAGE = "linux-tools-common"
PERF_GENERIC_PACKAGE = "linux-tools-generic"
APT_UPDATE_CMD: tuple[str, ...] = ("sudo", "apt-get", "update")
APT_INSTALL_PREFIX: tuple[str, ...] = ("sudo", "apt-get", "install", "-y")
PERF_VERSION_CMD: tuple[str, ...] = ("perf", "--version")
PARANOID_SYSCTL_KEY = "kernel.perf_event_paranoid"
DEFAULT_WORKLOAD_CMD: tuple[str, ...] = ("sleep", "0.2")


def _run_subprocess(argv: list[str]) -> subprocess.CompletedProcess:
    """Injectable module-level default runner. Never raises: a missing
    binary or a timeout is captured as a nonzero-returncode result, matching
    the same never-raise contract every other probe helper in this phase
    relies on for hermetic unit testing.
    """
    try:
        return subprocess.run(
            argv, capture_output=True, text=True, timeout=SUBPROCESS_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return subprocess.CompletedProcess(argv, returncode=1, stdout="", stderr=str(exc))


def _coerce_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        coerced = float(value)
    except (TypeError, ValueError):
        return None
    return coerced if math.isfinite(coerced) else None


def _bounded_excerpt(text: str, limit: int = STDERR_EXCERPT_MAX_CHARS) -> str:
    return (text or "")[:limit]


def _kernel_matched_package(kernel_release: str) -> str:
    return f"linux-tools-{kernel_release}"


def _coerce_counted_value(token: str) -> int | None:
    cleaned = token.replace(",", "")
    coerced = _coerce_float(cleaned)
    if coerced is None or not float(coerced).is_integer():
        return None
    return int(coerced)


def _classify_event_line(event: str, raw_line: str | None) -> dict[str, Any]:
    if raw_line is None:
        return {"event": event, "status": STATUS_UNPARSED, "value": None, "raw_line": None}

    lowered = raw_line.lower()
    if NOT_SUPPORTED_MARKER in lowered:
        return {"event": event, "status": STATUS_NOT_SUPPORTED, "value": None, "raw_line": raw_line}
    if NOT_PERMITTED_MARKER in lowered:
        return {"event": event, "status": STATUS_NOT_PERMITTED, "value": None, "raw_line": raw_line}

    stripped = raw_line.strip()
    token = stripped.split()[0] if stripped else ""
    value = _coerce_counted_value(token)
    if value is None:
        return {"event": event, "status": STATUS_UNPARSED, "value": None, "raw_line": raw_line}
    return {"event": event, "status": STATUS_COUNTED, "value": value, "raw_line": raw_line}


def parse_perf_stat_output(text: str, events: Sequence[str]) -> list[dict[str, Any]]:
    """Classify each requested event from real `perf stat` output text.

    This is the function that decides truth: a sysctl write succeeding tells
    you nothing about whether the underlying performance monitoring unit is
    exposed to the guest, so classification comes only from the output text.
    Returns one entry per requested event, in the order given, even for an
    event that appears nowhere in the output (status "unparsed", never
    silently dropped).
    """
    lines = text.splitlines()
    entries: list[dict[str, Any]] = []
    for event in events:
        pattern = re.compile(rf"(?<![\w-]){re.escape(event)}(?![\w-])")
        raw_line = next((line for line in lines if pattern.search(line)), None)
        entries.append(_classify_event_line(event, raw_line))
    return entries


def read_paranoid_setting(
    runner: Callable[[list[str]], subprocess.CompletedProcess] = _run_subprocess,
    errors: list[str] | None = None,
) -> int | str:
    """Read kernel.perf_event_paranoid, returning the integer value on
    success or the UNAVAILABLE sentinel plus a recorded reason on failure.
    Never raises.
    """
    if errors is None:
        errors = []
    completed = runner(["sysctl", "-n", PARANOID_SYSCTL_KEY])
    if completed.returncode != 0:
        errors.append(
            f"paranoid_read: sysctl exited {completed.returncode}: {(completed.stderr or '').strip()}"
        )
        return env_fingerprint.UNAVAILABLE
    try:
        return int((completed.stdout or "").strip())
    except ValueError:
        errors.append(f"paranoid_read: unparsable sysctl output: {completed.stdout!r}")
        return env_fingerprint.UNAVAILABLE


def set_paranoid_setting(
    value: int,
    runner: Callable[[list[str]], subprocess.CompletedProcess] = _run_subprocess,
) -> dict[str, Any]:
    """Attempt to write kernel.perf_event_paranoid. Never raises: the
    attempted value, exit code, and a bounded stderr excerpt are always
    returned, whether or not the write succeeded.
    """
    completed = runner(["sudo", "sysctl", "-w", f"{PARANOID_SYSCTL_KEY}={value}"])
    return {
        "attempted_value": value,
        "exit_code": completed.returncode,
        "stderr_excerpt": _bounded_excerpt(completed.stderr),
        "succeeded": completed.returncode == 0,
    }


def restore_paranoid_setting(
    original: int | str,
    runner: Callable[[list[str]], subprocess.CompletedProcess] = _run_subprocess,
) -> dict[str, Any]:
    """Restore kernel.perf_event_paranoid to its originally observed value.
    The caller is responsible for invoking this from a finally block so the
    probe never leaves a hosted runner with a lowered setting. When the
    original value itself was UNAVAILABLE, there is nothing to restore to,
    so no write is attempted.
    """
    if original == env_fingerprint.UNAVAILABLE:
        return {
            "attempted": False,
            "reason": "original paranoid value was unavailable; nothing to restore",
        }
    result = set_paranoid_setting(original, runner=runner)
    result["attempted"] = True
    return result


def install_perf_tooling(
    runner: Callable[[list[str]], subprocess.CompletedProcess] = _run_subprocess,
    kernel_release: str | None = None,
) -> dict[str, Any]:
    """Attempt to install perf tooling: the common package, the
    kernel-matched package named for the running kernel release, and the
    generic fallback, in one combined apt install call (matching the
    research-verified install command sequence). apt-get install with
    multiple package arguments is transactional, so a missing kernel-matched
    package on the azure-flavored runner kernel fails the whole call -- that
    failure, with its exit code and a bounded stderr excerpt, is the finding
    for that run, not a raised error. `installed` reflects whether
    `perf --version` actually responds afterward, not merely whether the
    apt exit code was zero, so a benign apt failure alongside an
    already-working perf binary is not misreported as unavailable.
    """
    kernel_release = kernel_release or platform.release()
    attempted_packages = [
        PERF_COMMON_PACKAGE,
        _kernel_matched_package(kernel_release),
        PERF_GENERIC_PACKAGE,
    ]

    runner(list(APT_UPDATE_CMD))
    install_completed = runner([*APT_INSTALL_PREFIX, *attempted_packages])

    version_completed = runner(list(PERF_VERSION_CMD))
    if version_completed.returncode == 0 and (version_completed.stdout or "").strip():
        perf_version: Any = version_completed.stdout.strip()
        installed = True
    else:
        perf_version = env_fingerprint.UNAVAILABLE
        installed = False

    return {
        "installed": installed,
        "attempted_packages": attempted_packages,
        "exit_code": install_completed.returncode,
        "stderr_excerpt": _bounded_excerpt(install_completed.stderr),
        "perf_version": perf_version,
    }


def _event_class(event: str) -> str:
    if event in PERF_HARDWARE_EVENTS:
        return "hardware"
    if event in PERF_SOFTWARE_EVENTS:
        return "software"
    raise ValueError(f"unknown perf event: {event}")


def _gating_verdict(
    default_entry: dict[str, Any], lowered_entry: dict[str, Any],
) -> tuple[bool, str | None]:
    """An event counts as gate-usable only when it counted in the default
    paranoid state: a gate that depends on a mutable privilege turns a
    permissions difference on a fork into what looks like a performance
    failure.
    """
    if default_entry["status"] == STATUS_COUNTED:
        return True, None
    if lowered_entry["status"] == STATUS_COUNTED:
        return False, REASON_REQUIRES_LOWERED_PARANOID
    return False, REASON_NOT_COUNTED_EITHER_STATE


def _perf_stat_cmd(events: Sequence[str], workload_cmd: Sequence[str]) -> list[str]:
    return ["perf", "stat", "-e", ",".join(events), "--", *workload_cmd]


def _build_event_entry(
    event: str,
    event_class: str,
    paranoid_state: str,
    paranoid_value: Any,
    parsed_entry: dict[str, Any],
    gating_eligible: bool,
    reason: str | None,
) -> dict[str, Any]:
    return {
        "event": event,
        "event_class": event_class,
        "paranoid_state": paranoid_state,
        "paranoid_value": paranoid_value,
        "status": parsed_entry["status"],
        "value": parsed_entry["value"],
        "raw_line": parsed_entry["raw_line"],
        "gating_eligible": gating_eligible,
        "reason": reason,
    }


def collect_perf_capability(
    *,
    runner: Callable[[list[str]], subprocess.CompletedProcess] = _run_subprocess,
    workload_cmd: Sequence[str] = DEFAULT_WORKLOAD_CMD,
    lowered_paranoid_value: int = DEFAULT_LOWERED_PARANOID_VALUE,
) -> dict[str, Any]:
    """Probe every hardware and software event in both paranoid states and
    return the perf_events sub-mapping of the probe record.

    Reads and records the paranoid default first, attempts the tooling
    install, sweeps every event in the default state, attempts to lower the
    paranoid setting, sweeps again in the lowered state, then restores the
    original setting from a finally block -- so restoration happens even
    when the sweep raises partway through. Every event's gating eligibility
    is derived only from the two sweeps' parsed status, never from whether
    the paranoid write itself succeeded.
    """
    errors: list[str] = []
    all_events = list(PERF_HARDWARE_EVENTS) + list(PERF_SOFTWARE_EVENTS)

    paranoid_default = read_paranoid_setting(runner=runner, errors=errors)
    install = install_perf_tooling(runner=runner)
    perf_installed = install["installed"]

    default_results: dict[str, dict[str, Any]] = {}
    if perf_installed:
        default_output = runner(_perf_stat_cmd(all_events, workload_cmd)).stderr
        default_results = {
            entry["event"]: entry for entry in parse_perf_stat_output(default_output, all_events)
        }

    paranoid_lowered = set_paranoid_setting(lowered_paranoid_value, runner=runner)

    lowered_results: dict[str, dict[str, Any]] = {}
    try:
        if perf_installed:
            lowered_output = runner(_perf_stat_cmd(all_events, workload_cmd)).stderr
            lowered_results = {
                entry["event"]: entry for entry in parse_perf_stat_output(lowered_output, all_events)
            }
    finally:
        restore_paranoid_setting(paranoid_default, runner=runner)
        paranoid_restored = read_paranoid_setting(runner=runner, errors=errors)

    events: list[dict[str, Any]] = []
    for event in all_events:
        event_class = _event_class(event)
        if perf_installed:
            default_entry = default_results[event]
            lowered_entry = lowered_results[event]
            gating_eligible, reason = _gating_verdict(default_entry, lowered_entry)
            lowered_paranoid_state_value = (
                lowered_paranoid_value if paranoid_lowered["succeeded"] else env_fingerprint.UNAVAILABLE
            )
            events.append(_build_event_entry(
                event, event_class, PARANOID_STATE_DEFAULT, paranoid_default,
                default_entry, gating_eligible, reason,
            ))
            events.append(_build_event_entry(
                event, event_class, PARANOID_STATE_LOWERED, lowered_paranoid_state_value,
                lowered_entry, gating_eligible, reason,
            ))
        else:
            unavailable_entry = {"status": STATUS_UNAVAILABLE, "value": None, "raw_line": None}
            events.append(_build_event_entry(
                event, event_class, PARANOID_STATE_DEFAULT, paranoid_default,
                unavailable_entry, False, REASON_TOOLING_UNAVAILABLE,
            ))
            events.append(_build_event_entry(
                event, event_class, PARANOID_STATE_LOWERED, env_fingerprint.UNAVAILABLE,
                unavailable_entry, False, REASON_TOOLING_UNAVAILABLE,
            ))

    return {
        "perf_installed": perf_installed,
        "perf_version": install["perf_version"],
        "install": install,
        "paranoid_default": paranoid_default,
        "paranoid_lowered": paranoid_lowered,
        "paranoid_restored": paranoid_restored,
        "events": events,
        "errors": errors,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the collected perf capability sub-mapping as JSON",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    record = collect_perf_capability()

    if args.json:
        print(json.dumps(record, indent=2, sort_keys=True))
    else:
        print(f"perf_installed: {record['perf_installed']}")
        print(f"paranoid_default: {record['paranoid_default']}")
        print(f"paranoid_restored: {record['paranoid_restored']}")
        for entry in record["events"]:
            print(
                f"{entry['event']} ({entry['event_class']}, {entry['paranoid_state']}): "
                f"{entry['status']} gating_eligible={entry['gating_eligible']}"
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
