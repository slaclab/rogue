#!/usr/bin/env python3
# ----------------------------------------------------------------------------
# Title      : ROGUE Runner Instrument Overhead and Repeatability Probe
# ----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
# ----------------------------------------------------------------------------

"""Measure, against one shared synthetic workload run repeatedly in this job,
whether each candidate instrument installs unprivileged, what it costs, and
whether the count it produces is stable enough to be worth anything.

Covers the three heavyweight external tools named by the phase's
requirements (a syscall tracer, a preloaded allocation interposer, and a
call-graph profiler) plus the zero-dependency in-process counters. Every
overhead multiplier here is measured in this job against the synthetic
workload defined below; a published literature figure is never written into
any field of the record. Literature ranges exist only as a sanity check for
the operator reading this module's output: if a measured multiplier lands
wildly outside the expected order of magnitude, suspect the harness (a
timing bug, a workload too small to be stable) before trusting the number.
"""

from __future__ import annotations

import argparse
import ctypes
import ctypes.util
import json
import re
import statistics
import subprocess
import sys
import tempfile
import tracemalloc
from pathlib import Path
from typing import Any, Callable

try:
    import resource
    HAS_RESOURCE = True
except ImportError:
    HAS_RESOURCE = False

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import env_fingerprint  # noqa: E402  (flat sibling import, path inserted above)
import perf_noise_report  # noqa: E402  (flat sibling import, path inserted above)
import probe_perf_events  # noqa: E402  (flat sibling import, path inserted above)

INSUFFICIENT_SAMPLES = perf_noise_report.INSUFFICIENT_SAMPLES

SUBPROCESS_TIMEOUT_SECONDS = 60
STDERR_EXCERPT_MAX_CHARS = 2000

# Repeat counts for the admission gate: every instrument runs its workload
# this many times inside this one job. A repeatability verdict requires at
# least MIN_REPEATS_FOR_VERDICT counts, so a single-repeat run never falsely
# reports bit-identical.
WORKLOAD_REPEATS = 7
MIN_REPEATS_FOR_VERDICT = 3

# Synthetic workload sizes (no Rogue build required). Keyword-argument
# defaults on the measurement functions below so unit tests can shrink the
# workload without editing this module; these module constants are the
# production sizes used by this module's own CLI.
SYSCALL_WORKLOAD_ITERATIONS = 2000
ALLOC_WORKLOAD_ITERATIONS = 500
ALLOC_WORKLOAD_BLOCK_BYTES = 4096

# Instrument names (the shortlist this module probes): the three heavyweight external tools
# plus the four zero-dependency in-process counters. Always accessed in
# sorted order so a serialized record is reproducible regardless of
# dict/list construction order.
INSTRUMENT_STRACE = "strace"
INSTRUMENT_MALLOC_INTERPOSER = "malloc_interposer"
INSTRUMENT_CALLGRIND = "callgrind"
INSTRUMENT_PYTHON_TRACEMALLOC = "python_tracemalloc"
INSTRUMENT_ALLOCATOR_STATS = "allocator_stats"
INSTRUMENT_RESOURCE_USAGE = "resource_usage"
INSTRUMENT_PERF_SOFTWARE_EVENTS = "perf_software_events"
INSTRUMENT_NAMES: tuple[str, ...] = tuple(sorted((
    INSTRUMENT_STRACE, INSTRUMENT_MALLOC_INTERPOSER, INSTRUMENT_CALLGRIND,
    INSTRUMENT_PYTHON_TRACEMALLOC, INSTRUMENT_ALLOCATOR_STATS, INSTRUMENT_RESOURCE_USAGE,
    INSTRUMENT_PERF_SOFTWARE_EVENTS,
)))

# Graded per-instrument verdict vocabulary, assigned to every entry by
# _apply_verdict(): an instrument that works but costs too much
# (overhead-disqualifies) is a different finding from one that does not run
# at all (unavailable), and a wobbling count (count-unstable) disqualifies an
# otherwise-cheap instrument regardless of its overhead.
VERDICT_USABLE = "usable"
VERDICT_OVERHEAD_DISQUALIFIES = "overhead-disqualifies"
VERDICT_COUNT_UNSTABLE = "count-unstable"
VERDICT_UNAVAILABLE = "unavailable"

OVERHEAD_DISQUALIFY_MULTIPLIER = 5.0

VERDICT_BIT_IDENTICAL = "bit-identical"
VERDICT_UNSTABLE = "unstable"

REASON_TOOL_UNAVAILABLE = "tool did not install; see the install field for the captured error"

_INTERPOSER_COMPARISON_NOTE = (
    "Counts every process-wide malloc/free/calloc/realloc/posix_memalign/aligned_alloc call via a "
    "compiled LD_PRELOAD shim, including allocations made inside a native shared library such as "
    "librogue-core.so, at the cost of an in-job compiled build step."
)
_ALLOCATOR_COMPARISON_NOTE = (
    "Reads glibc's own mallinfo2() heap-usage snapshot with zero build step and zero preload, but "
    "only reports allocator-arena aggregates (bytes and block counts), never a per-call event count, "
    "and only for allocations that actually go through glibc's malloc."
)
_TRACEMALLOC_NOTE = (
    "tracemalloc observes Python-object allocations only; the allocations that matter for Rogue's "
    "frame and buffer path happen in native code inside librogue-core.so, which this tracer is "
    "structurally blind to, not merely quiet about."
)

STRACE_PACKAGE = "strace"
VALGRIND_PACKAGE = "valgrind"
STRACE_VERSION_CMD: tuple[str, ...] = ("strace", "-V")
VALGRIND_VERSION_CMD: tuple[str, ...] = ("valgrind", "--version")
APT_UPDATE_CMD: tuple[str, ...] = ("sudo", "apt-get", "update")
APT_INSTALL_PREFIX: tuple[str, ...] = ("sudo", "apt-get", "install", "-y")

STRACE_CMD_PREFIX: tuple[str, ...] = ("strace", "-f", "-c", "--")
CALLGRIND_CMD_PREFIX_HEAD: tuple[str, ...] = ("valgrind", "--tool=callgrind")

BUILD_SCRIPT_PATH = SCRIPTS_DIR / "build_malloc_interposer.sh"

_SYSCALL_WORKLOAD_TEMPLATE = "import os\nfor _ in range({iterations}):\n    os.getppid()\n"
_ALLOC_WORKLOAD_TEMPLATE = (
    "buffers = [bytearray({block_bytes}) for _ in range({iterations})]\n"
    "buffers.clear()\n"
)

_CALLGRIND_COLLECTED_RE = re.compile(r"Collected\s*:\s*(\d+)")


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


def _bounded_excerpt(text: str, limit: int = STDERR_EXCERPT_MAX_CHARS) -> str:
    return (text or "")[:limit]


def measure_overhead(baseline_seconds: list[float], instrumented_seconds: list[float]) -> Any:
    """Ratio of the instrumented median to the baseline median wall-clock
    seconds. Returns the insufficient-samples sentinel for an empty sample
    list on either side, and the unavailable sentinel for a zero, negative,
    or non-finite baseline (or a non-finite result), never a division error
    and never an infinity.
    """
    if not baseline_seconds or not instrumented_seconds:
        return INSUFFICIENT_SAMPLES

    baseline_median = statistics.median(baseline_seconds)
    instrumented_median = statistics.median(instrumented_seconds)

    if not _is_finite_positive(baseline_median):
        return env_fingerprint.UNAVAILABLE
    if not _is_finite(instrumented_median):
        return env_fingerprint.UNAVAILABLE

    ratio = instrumented_median / baseline_median
    if not _is_finite(ratio):
        return env_fingerprint.UNAVAILABLE
    return ratio


def _is_finite(value: float) -> bool:
    return value == value and value not in (float("inf"), float("-inf"))


def _is_finite_positive(value: float) -> bool:
    return _is_finite(value) and value > 0


def repeatability_verdict(
    counts: list[int], *, min_repeats: int = MIN_REPEATS_FOR_VERDICT,
) -> dict[str, Any]:
    """`bit-identical` when every count is equal, `unstable` with the
    observed minimum, maximum, and spread when they are not, and the
    insufficient-samples sentinel when fewer than `min_repeats` counts are
    present -- a single count can never falsely report bit-identical.
    """
    n = len(counts)
    if n < min_repeats:
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


def _syscall_workload_command(iterations: int) -> list[str]:
    return [sys.executable, "-c", _SYSCALL_WORKLOAD_TEMPLATE.format(iterations=iterations)]


def _alloc_workload_command(iterations: int, block_bytes: int) -> list[str]:
    return [sys.executable, "-c", _ALLOC_WORKLOAD_TEMPLATE.format(iterations=iterations, block_bytes=block_bytes)]


def _interposer_wrap_argv(argv: list[str], so_path: Path, out_path: Path) -> list[str]:
    return ["env", f"LD_PRELOAD={so_path}", f"ROGUE_PROBE_ALLOC_OUT={out_path}", *argv]


def _parse_strace_total_calls(text: str) -> int | None:
    """Extract the `calls` column from strace -c's trailing `total` row.
    That column is always the fourth whitespace-separated field before
    `total` (percent, seconds, usecs/call, calls), whether or not the
    optional `errors` column is present after it, so this indexing holds
    regardless of whether any traced syscall errored.
    """
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.endswith("total"):
            continue
        fields = stripped.split()[:-1]
        if len(fields) < 4:
            return None
        try:
            return int(fields[3])
        except ValueError:
            return None
    return None


def _parse_callgrind_collected(text: str) -> int | None:
    match = _CALLGRIND_COLLECTED_RE.search(text)
    if match is None:
        return None
    return int(match.group(1))


def _read_interposer_dump(path: Path) -> dict[str, int] | None:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    counts: dict[str, int] = {}
    for line in text.splitlines():
        key, _, value = line.partition(" ")
        if not key:
            continue
        try:
            counts[key] = int(value.strip())
        except ValueError:
            continue
    return counts or None


def _interposer_malloc_calls(counts: dict[str, int] | None) -> int | None:
    if counts is None:
        return None
    return counts.get("malloc_calls")


def _install_apt_tool(
    package: str,
    version_cmd: tuple[str, ...],
    runner: Callable[[list[str]], subprocess.CompletedProcess],
) -> dict[str, Any]:
    """Install `package` with apt, then confirm the tool actually responds
    to its own version command -- matching probe_perf_events.py's
    install_perf_tooling pattern: `installed` reflects a real version check,
    not the apt exit code, so a benign apt failure alongside an
    already-working binary is never misreported as unavailable.
    """
    runner(list(APT_UPDATE_CMD))
    install_completed = runner([*APT_INSTALL_PREFIX, package])

    version_completed = runner(list(version_cmd))
    version_text = ((version_completed.stdout or "") + (version_completed.stderr or "")).strip()
    if version_completed.returncode == 0 and version_text:
        installed = True
        version: Any = version_text.splitlines()[0].strip()
    else:
        installed = False
        version = env_fingerprint.UNAVAILABLE

    return {
        "installed": installed,
        "package": package,
        "exit_code": install_completed.returncode,
        "stderr_excerpt": _bounded_excerpt(install_completed.stderr),
        "version": version,
    }


def _time_repeats(
    runner: Callable[[list[str]], subprocess.CompletedProcess],
    argv: list[str],
    repeats: int,
    window_sampler: Callable[[str, Callable[[], Any]], dict[str, Any]],
    label: str,
) -> list[float]:
    seconds: list[float] = []
    for i in range(repeats):
        window = window_sampler(f"{label}_{i}", lambda a=argv: runner(a))
        seconds.append(window["wall_seconds"])
    return seconds


def _unavailable_entry(name: str, install: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": name,
        "available": False,
        "install": install,
        "repeats": 0,
        "baseline_seconds": [],
        "instrumented_seconds": [],
        "counts": [],
        "overhead_multiplier": env_fingerprint.UNAVAILABLE,
        "repeatability": {"verdict": INSUFFICIENT_SAMPLES, "n": 0},
        "verdict": VERDICT_UNAVAILABLE,
        "verdict_reason": install.get("reason", REASON_TOOL_UNAVAILABLE),
    }


def _finalize_entry(
    name: str,
    install: dict[str, Any],
    repeats: int,
    baseline_seconds: list[float],
    instrumented_seconds: list[float],
    counts: list[int],
) -> dict[str, Any]:
    overhead = measure_overhead(baseline_seconds, instrumented_seconds)
    repeatability = repeatability_verdict(counts) if counts else {"verdict": INSUFFICIENT_SAMPLES, "n": len(counts)}
    return {
        "name": name,
        "available": True,
        "install": install,
        "repeats": repeats,
        "baseline_seconds": baseline_seconds,
        "instrumented_seconds": instrumented_seconds,
        "counts": counts,
        "overhead_multiplier": overhead,
        "repeatability": repeatability,
        "verdict": None,
        "verdict_reason": None,
    }


def _apply_verdict(entry: dict[str, Any], *, threshold: float = OVERHEAD_DISQUALIFY_MULTIPLIER) -> dict[str, Any]:
    """Assign the graded verdict, checked in this order: an unavailable
    instrument short-circuits every other check, then an unstable count,
    then an excessive overhead multiplier, then usable. The threshold value
    is always recorded on the entry so a reader sees the rule that was
    applied rather than having to infer it.
    """
    entry["overhead_disqualify_threshold"] = threshold

    if not entry["available"]:
        entry["verdict"] = VERDICT_UNAVAILABLE
        entry["verdict_reason"] = entry.get("verdict_reason") or REASON_TOOL_UNAVAILABLE
        return entry

    repeatability_status = entry["repeatability"]["verdict"]
    if repeatability_status == VERDICT_UNSTABLE:
        entry["verdict"] = VERDICT_COUNT_UNSTABLE
        entry["verdict_reason"] = (
            f"count varied across {entry['repeatability']['n']} repeats on this host "
            f"(spread {entry['repeatability'].get('spread')}); ineligible for deterministic-tier use"
        )
        return entry

    multiplier = entry["overhead_multiplier"]
    if not isinstance(multiplier, (int, float)) or isinstance(multiplier, bool):
        entry["verdict"] = VERDICT_UNAVAILABLE
        entry["verdict_reason"] = f"overhead multiplier could not be measured ({multiplier})"
        return entry

    if multiplier > threshold:
        entry["verdict"] = VERDICT_OVERHEAD_DISQUALIFIES
        entry["verdict_reason"] = f"overhead multiplier {multiplier} exceeds the disqualifying threshold {threshold}"
        return entry

    entry["verdict"] = VERDICT_USABLE
    entry["verdict_reason"] = "available, an acceptable overhead multiplier, and no repeatability finding disqualifies it"
    return entry


def _alloc_workload_inprocess(iterations: int, block_bytes: int) -> None:
    buffers = [bytearray(block_bytes) for _ in range(iterations)]
    buffers.clear()


class MallInfo2Struct(ctypes.Structure):
    """glibc's `struct mallinfo2` field layout (see malloc.h). Every field
    is an unsigned size_t counting bytes or blocks in the allocator arena;
    none of them is a per-call event count.
    """

    _fields_ = [
        ("arena", ctypes.c_size_t),
        ("ordblks", ctypes.c_size_t),
        ("smblks", ctypes.c_size_t),
        ("hblks", ctypes.c_size_t),
        ("hblkhd", ctypes.c_size_t),
        ("usmblks", ctypes.c_size_t),
        ("fsmblks", ctypes.c_size_t),
        ("uordblks", ctypes.c_size_t),
        ("fordblks", ctypes.c_size_t),
        ("keepcost", ctypes.c_size_t),
    ]


def _resolve_mallinfo2() -> Callable[[], MallInfo2Struct] | None:
    """Resolve libc's mallinfo2 symbol through the foreign function
    interface. Returns None (never raises) when the C library or the symbol
    itself cannot be found on this platform.
    """
    libc_path = ctypes.util.find_library("c")
    if libc_path is None:
        return None
    try:
        libc = ctypes.CDLL(libc_path)
        fn = libc.mallinfo2
    except (OSError, AttributeError):
        return None
    fn.restype = MallInfo2Struct
    fn.argtypes = []
    return fn


def _real_getrusage() -> Any:
    return resource.getrusage(resource.RUSAGE_SELF)


def _measure_strace(
    *,
    runner: Callable[[list[str]], subprocess.CompletedProcess],
    repeats: int,
    iterations: int,
    window_sampler: Callable[[str, Callable[[], Any]], dict[str, Any]],
) -> dict[str, Any]:
    """Measure the syscall tracer against the syscall-dense leg of the
    synthetic workload, which actually exercises what strace counts.
    """
    install = _install_apt_tool(STRACE_PACKAGE, STRACE_VERSION_CMD, runner)
    if not install["installed"]:
        return _unavailable_entry(INSTRUMENT_STRACE, install)

    workload_argv = _syscall_workload_command(iterations)
    baseline_seconds = _time_repeats(runner, workload_argv, repeats, window_sampler, "strace_baseline")

    instrumented_seconds: list[float] = []
    counts: list[int] = []
    for i in range(repeats):
        wrapped = [*STRACE_CMD_PREFIX, *workload_argv]
        window = window_sampler(f"strace_instrumented_{i}", lambda a=wrapped: runner(a))
        instrumented_seconds.append(window["wall_seconds"])
        count = _parse_strace_total_calls(window["result"].stderr or "")
        if count is not None:
            counts.append(count)

    return _finalize_entry(INSTRUMENT_STRACE, install, repeats, baseline_seconds, instrumented_seconds, counts)


def _measure_malloc_interposer(
    *,
    runner: Callable[[list[str]], subprocess.CompletedProcess],
    repeats: int,
    iterations: int,
    block_bytes: int,
    window_sampler: Callable[[str, Callable[[], Any]], dict[str, Any]],
    output_path: Path | None = None,
    read_dump_fn: Callable[[Path], dict[str, int] | None] = _read_interposer_dump,
) -> dict[str, Any]:
    """Measure the purpose-written LD_PRELOAD interposer against the
    allocation-dense leg of the synthetic workload. Builds the object inside
    this job via build_malloc_interposer.sh; a build failure is a recorded
    finding, never a job failure.
    """
    output_path = output_path if output_path is not None else Path(tempfile.mkdtemp()) / "probe_malloc_interposer.so"
    build_completed = runner(["bash", str(BUILD_SCRIPT_PATH), str(output_path)])
    if build_completed.returncode != 0:
        return _unavailable_entry(INSTRUMENT_MALLOC_INTERPOSER, {
            "built": False,
            "exit_code": build_completed.returncode,
            "stderr_excerpt": _bounded_excerpt(build_completed.stderr),
        })

    install = {"built": True, "exit_code": build_completed.returncode, "path": str(output_path)}
    workload_argv = _alloc_workload_command(iterations, block_bytes)
    baseline_seconds = _time_repeats(runner, workload_argv, repeats, window_sampler, "malloc_interposer_baseline")

    instrumented_seconds: list[float] = []
    counts: list[int] = []
    for i in range(repeats):
        dump_path = Path(tempfile.mkdtemp()) / f"alloc_counts_{i}.txt"
        wrapped = _interposer_wrap_argv(workload_argv, output_path, dump_path)
        window = window_sampler(f"malloc_interposer_instrumented_{i}", lambda a=wrapped: runner(a))
        instrumented_seconds.append(window["wall_seconds"])
        count = _interposer_malloc_calls(read_dump_fn(dump_path))
        if count is not None:
            counts.append(count)

    return _finalize_entry(
        INSTRUMENT_MALLOC_INTERPOSER, install, repeats, baseline_seconds, instrumented_seconds, counts,
    )


def _measure_callgrind(
    *,
    runner: Callable[[list[str]], subprocess.CompletedProcess],
    repeats: int,
    iterations: int,
    block_bytes: int,
    window_sampler: Callable[[str, Callable[[], Any]], dict[str, Any]],
) -> dict[str, Any]:
    """Measure the call-graph profiler in its call-counting mode, against
    the synthetic workload only -- pointing it at a real tests/perf module
    is structurally incompatible with any sane job timeout.
    """
    install = _install_apt_tool(VALGRIND_PACKAGE, VALGRIND_VERSION_CMD, runner)
    if not install["installed"]:
        return _unavailable_entry(INSTRUMENT_CALLGRIND, install)

    workload_argv = _alloc_workload_command(iterations, block_bytes)
    baseline_seconds = _time_repeats(runner, workload_argv, repeats, window_sampler, "callgrind_baseline")

    instrumented_seconds: list[float] = []
    counts: list[int] = []
    for i in range(repeats):
        out_file = Path(tempfile.mkdtemp()) / f"callgrind_{i}.out"
        wrapped = [*CALLGRIND_CMD_PREFIX_HEAD, f"--callgrind-out-file={out_file}", "--", *workload_argv]
        window = window_sampler(f"callgrind_instrumented_{i}", lambda a=wrapped: runner(a))
        instrumented_seconds.append(window["wall_seconds"])
        count = _parse_callgrind_collected(window["result"].stderr or "")
        if count is not None:
            counts.append(count)

    return _finalize_entry(INSTRUMENT_CALLGRIND, install, repeats, baseline_seconds, instrumented_seconds, counts)


def _measure_python_tracemalloc(
    *,
    repeats: int,
    iterations: int,
    block_bytes: int,
    window_sampler: Callable[[str, Callable[[], Any]], dict[str, Any]],
) -> dict[str, Any]:
    """Measure the standard library's own allocation tracer. Always present
    (tracemalloc ships with CPython), so this entry is never emitted as
    unavailable; its note field always states that it cannot see allocations
    made inside a native shared library -- the obvious first counter a
    reader reaches for, and the reason it cannot work here is not obvious
    until that blindness is named.
    """
    def workload_fn() -> None:
        _alloc_workload_inprocess(iterations, block_bytes)

    baseline_seconds: list[float] = []
    for i in range(repeats):
        window = window_sampler(f"python_tracemalloc_baseline_{i}", workload_fn)
        baseline_seconds.append(window["wall_seconds"])

    instrumented_seconds: list[float] = []
    counts: list[int] = []
    for i in range(repeats):
        tracemalloc.start()
        before = tracemalloc.take_snapshot()
        window = window_sampler(f"python_tracemalloc_instrumented_{i}", workload_fn)
        after = tracemalloc.take_snapshot()
        tracemalloc.stop()
        instrumented_seconds.append(window["wall_seconds"])
        diff = after.compare_to(before, "lineno")
        counts.append(sum(stat.count_diff for stat in diff if stat.count_diff > 0))

    install = {"available": True}
    entry = _finalize_entry(
        INSTRUMENT_PYTHON_TRACEMALLOC, install, repeats, baseline_seconds, instrumented_seconds, counts,
    )
    entry["note"] = _TRACEMALLOC_NOTE
    return entry


def _measure_allocator_stats(
    *,
    repeats: int,
    iterations: int,
    block_bytes: int,
    window_sampler: Callable[[str, Callable[[], Any]], dict[str, Any]],
    resolve_fn: Callable[[], Any] = _resolve_mallinfo2,
) -> dict[str, Any]:
    """Measure glibc's mallinfo2() heap-usage snapshot: a zero-artifact
    comparison point for the LD_PRELOAD interposer. When the symbol cannot
    be resolved on this platform, emits the unavailable sentinel with the
    reason rather than raising.
    """
    mallinfo2_fn = resolve_fn()
    if mallinfo2_fn is None:
        entry = _unavailable_entry(INSTRUMENT_ALLOCATOR_STATS, {
            "available": False,
            "reason": "the libc mallinfo2 symbol could not be resolved on this platform",
        })
        entry["comparison_note"] = _ALLOCATOR_COMPARISON_NOTE
        return entry

    def workload_fn() -> None:
        _alloc_workload_inprocess(iterations, block_bytes)

    baseline_seconds: list[float] = []
    for i in range(repeats):
        window = window_sampler(f"allocator_stats_baseline_{i}", workload_fn)
        baseline_seconds.append(window["wall_seconds"])

    field_names = [name for name, _ in MallInfo2Struct._fields_]
    instrumented_seconds: list[float] = []
    counts: list[int] = []
    field_deltas: list[dict[str, int]] = []
    for i in range(repeats):
        before = mallinfo2_fn()
        window = window_sampler(f"allocator_stats_instrumented_{i}", workload_fn)
        after = mallinfo2_fn()
        instrumented_seconds.append(window["wall_seconds"])
        deltas = {name: getattr(after, name) - getattr(before, name) for name in field_names}
        field_deltas.append(deltas)
        counts.append(deltas["uordblks"])

    install = {"available": True}
    entry = _finalize_entry(
        INSTRUMENT_ALLOCATOR_STATS, install, repeats, baseline_seconds, instrumented_seconds, counts,
    )
    entry["field_deltas"] = field_deltas
    entry["comparison_note"] = _ALLOCATOR_COMPARISON_NOTE
    return entry


def _measure_resource_usage(
    *,
    repeats: int,
    iterations: int,
    block_bytes: int,
    window_sampler: Callable[[str, Callable[[], Any]], dict[str, Any]],
    getrusage_fn: Callable[[], Any] = _real_getrusage,
) -> dict[str, Any]:
    """Measure resource.getrusage() deltas: minor faults, voluntary context
    switches, and involuntary context switches across the workload.
    """
    if not HAS_RESOURCE:
        entry = _unavailable_entry(INSTRUMENT_RESOURCE_USAGE, {
            "available": False,
            "reason": "the resource module is not importable on this platform",
        })
        return entry

    def workload_fn() -> None:
        _alloc_workload_inprocess(iterations, block_bytes)

    baseline_seconds: list[float] = []
    for i in range(repeats):
        window = window_sampler(f"resource_usage_baseline_{i}", workload_fn)
        baseline_seconds.append(window["wall_seconds"])

    instrumented_seconds: list[float] = []
    counts: list[int] = []
    deltas_samples: list[dict[str, int]] = []
    for i in range(repeats):
        before = getrusage_fn()
        window = window_sampler(f"resource_usage_instrumented_{i}", workload_fn)
        after = getrusage_fn()
        instrumented_seconds.append(window["wall_seconds"])
        deltas = {
            "minor_faults": after.ru_minflt - before.ru_minflt,
            "voluntary_context_switches": after.ru_nvcsw - before.ru_nvcsw,
            "involuntary_context_switches": after.ru_nivcsw - before.ru_nivcsw,
        }
        deltas_samples.append(deltas)
        counts.append(deltas["minor_faults"])

    install = {"available": True}
    entry = _finalize_entry(
        INSTRUMENT_RESOURCE_USAGE, install, repeats, baseline_seconds, instrumented_seconds, counts,
    )
    entry["deltas"] = deltas_samples
    return entry


def _measure_perf_software_events(
    *,
    runner: Callable[[list[str]], subprocess.CompletedProcess],
    repeats: int,
    iterations: int,
    window_sampler: Callable[[str, Callable[[], Any]], dict[str, Any]],
) -> dict[str, Any]:
    """Measure the perf software event tuple against the syscall-dense leg,
    reusing probe_perf_events.py's own event tuple and output parser so the
    two modules can never disagree about what a count means.
    """
    install = probe_perf_events.install_perf_tooling(runner=runner)
    if not install["installed"]:
        return _unavailable_entry(INSTRUMENT_PERF_SOFTWARE_EVENTS, install)

    events = list(probe_perf_events.PERF_SOFTWARE_EVENTS)
    workload_argv = _syscall_workload_command(iterations)
    baseline_seconds = _time_repeats(
        runner, workload_argv, repeats, window_sampler, "perf_software_events_baseline",
    )

    instrumented_seconds: list[float] = []
    counts: list[int] = []
    for i in range(repeats):
        wrapped = ["perf", "stat", "-e", ",".join(events), "--", *workload_argv]
        window = window_sampler(f"perf_software_events_instrumented_{i}", lambda a=wrapped: runner(a))
        instrumented_seconds.append(window["wall_seconds"])
        parsed = probe_perf_events.parse_perf_stat_output(window["result"].stderr or "", events)
        counted_values = [item["value"] for item in parsed if item["status"] == probe_perf_events.STATUS_COUNTED]
        if counted_values:
            counts.append(sum(counted_values))

    return _finalize_entry(
        INSTRUMENT_PERF_SOFTWARE_EVENTS, install, repeats, baseline_seconds, instrumented_seconds, counts,
    )


def collect_instrument_sweep(
    *,
    runner: Callable[[list[str]], subprocess.CompletedProcess] = _run_subprocess,
    repeats: int = WORKLOAD_REPEATS,
    syscall_iterations: int = SYSCALL_WORKLOAD_ITERATIONS,
    alloc_iterations: int = ALLOC_WORKLOAD_ITERATIONS,
    alloc_block_bytes: int = ALLOC_WORKLOAD_BLOCK_BYTES,
    window_sampler: Callable[[str, Callable[[], Any]], dict[str, Any]] = env_fingerprint.sample_cpu_window,
) -> list[dict[str, Any]]:
    """Collect the instruments sub-mapping's entry list: the three
    heavyweight external tools plus the four zero-dependency in-process
    counters, in name-sorted order. An absent tool never aborts the sweep;
    its entry simply records `available: False` and the sweep continues to
    the next instrument. Two instruments that happen to measure an identical
    overhead multiplier both keep their own entry -- they are never merged.
    Every entry receives a graded verdict before this function returns.
    """
    malloc_interposer_entry = _measure_malloc_interposer(
        runner=runner, repeats=repeats, iterations=alloc_iterations, block_bytes=alloc_block_bytes,
        window_sampler=window_sampler,
    )
    malloc_interposer_entry["comparison_note"] = _INTERPOSER_COMPARISON_NOTE

    entries = [
        _measure_strace(runner=runner, repeats=repeats, iterations=syscall_iterations, window_sampler=window_sampler),
        malloc_interposer_entry,
        _measure_callgrind(
            runner=runner, repeats=repeats, iterations=alloc_iterations, block_bytes=alloc_block_bytes,
            window_sampler=window_sampler,
        ),
        _measure_python_tracemalloc(
            repeats=repeats, iterations=alloc_iterations, block_bytes=alloc_block_bytes,
            window_sampler=window_sampler,
        ),
        _measure_allocator_stats(
            repeats=repeats, iterations=alloc_iterations, block_bytes=alloc_block_bytes,
            window_sampler=window_sampler,
        ),
        _measure_resource_usage(
            repeats=repeats, iterations=alloc_iterations, block_bytes=alloc_block_bytes,
            window_sampler=window_sampler,
        ),
        _measure_perf_software_events(
            runner=runner, repeats=repeats, iterations=syscall_iterations, window_sampler=window_sampler,
        ),
    ]
    for entry in entries:
        _apply_verdict(entry)
    return sorted(entries, key=lambda entry: entry["name"])


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the collected instrument entries as JSON",
    )
    parser.add_argument(
        "--repeats",
        type=int,
        default=WORKLOAD_REPEATS,
        help=f"Number of times each leg runs inside this job (default: {WORKLOAD_REPEATS})",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    entries = collect_instrument_sweep(repeats=args.repeats)

    if args.json:
        print(json.dumps(entries, indent=2, sort_keys=True))
    else:
        for entry in entries:
            print(
                f"{entry['name']}: available={entry['available']} "
                f"overhead={entry.get('overhead_multiplier')} verdict={entry.get('verdict')}"
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
