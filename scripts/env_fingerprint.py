#!/usr/bin/env python3
# ----------------------------------------------------------------------------
# Title      : ROGUE Runner Environment Fingerprint
# ----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
# ----------------------------------------------------------------------------

"""Shared runner environment fingerprint and calibration vector.

The calibration vector's syscall component times `os.getppid()` specifically
because it is a real kernel round trip rather than a vDSO read like
`clock_gettime`, and it is not cached by glibc the way a naive
process-identity lookup might be, so it stays a genuine syscall on every
call.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import platform
import statistics
import subprocess
import time
from pathlib import Path
from typing import Any, Callable

try:
    import hwcounter
    HAS_HWCOUNTER = True
except ImportError:
    HAS_HWCOUNTER = False


FINGERPRINT_SCHEMA_VERSION = 1
UNAVAILABLE = "unavailable"

PROC_CPUINFO_PATH = Path("/proc/cpuinfo")
PROC_MEMINFO_PATH = Path("/proc/meminfo")
PROC_STAT_PATH = Path("/proc/stat")
CGROUP_CPU_STAT_PATH = Path("/sys/fs/cgroup/cpu.stat")
CGROUP_CPU_MAX_PATH = Path("/sys/fs/cgroup/cpu.max")
LDD_VERSION_CMD: tuple[str, ...] = ("ldd", "--version")
GCC_VERSION_CMD: tuple[str, ...] = ("gcc", "--version")
SYSTEMCTL_LIST_TIMERS_CMD: tuple[str, ...] = ("systemctl", "list-timers", "--all", "--no-legend")
RUNNER_IMAGE_VERSION_ENV = "ImageVersion"
SUBPROCESS_TIMEOUT_SECONDS = 15

# Calibration vector: four independently measured components (never blended
# into one score), each a keyword-argument default on collect_calibration_vector
# so tests can shrink the workload without editing this module.
CALIBRATION_SCHEMA_VERSION = 1
CALIBRATION_ALU_ITERATIONS = 5000000
CALIBRATION_MEMCPY_BYTES = 67108864
CALIBRATION_MEMCPY_BLOCK_BYTES = 4194304
CALIBRATION_SYSCALL_ITERATIONS = 200000
CALIBRATION_TSC_SAMPLE_SECONDS = 0.25
CALIBRATION_REPEATS = 5

# Measurement-window steal/throttling sampling. Inclusive
# comparison: a steal fraction exactly at the threshold is flagged.
DEFAULT_STEAL_THRESHOLD = 0.01
STEAL_COMPARISON_OPERATOR = ">="


def _coerce_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        coerced = float(value)
    except (TypeError, ValueError):
        return None
    return coerced if math.isfinite(coerced) else None


def _parse_float_strict(value: Any) -> float:
    coerced = _coerce_float(value)
    if coerced is None:
        raise ValueError(f"non-finite or non-numeric value: {value!r}")
    return coerced


def _try(key: str, errors: list[str], fn: Callable[[], Any]) -> Any:
    """Run fn(), returning UNAVAILABLE and recording a reason on any of the
    documented failure classes: an unreadable source path, a failed or
    missing subprocess, or a value that fails to parse. No exception is
    allowed to escape this helper."""
    try:
        return fn()
    except (OSError, subprocess.SubprocessError, ValueError, LookupError) as exc:
        errors.append(f"{key}: {type(exc).__name__}: {exc}")
        return UNAVAILABLE


def _read_cpuinfo_field(path: Path, prefix: str) -> str:
    text = path.read_text(encoding="utf-8")
    for line in text.splitlines():
        if line.startswith(prefix):
            _, _, value = line.partition(":")
            return value.strip()
    raise ValueError(f"no {prefix!r} line found in {path}")


def _read_nproc() -> int:
    count = os.cpu_count()
    if count is None:
        raise ValueError("os.cpu_count() returned None")
    return count


def _read_kernel_version() -> str:
    value = platform.release()
    if not value:
        raise ValueError("platform.release() returned an empty string")
    return value


def _read_cpython_version() -> str:
    value = platform.python_version()
    if not value:
        raise ValueError("platform.python_version() returned an empty string")
    return value


def _read_glibc_version(ldd_cmd: tuple[str, ...]) -> str:
    lib, version = platform.libc_ver()
    if lib == "glibc" and version:
        return version
    completed = subprocess.run(
        list(ldd_cmd), capture_output=True, text=True, timeout=SUBPROCESS_TIMEOUT_SECONDS,
    )
    if completed.returncode != 0:
        raise subprocess.SubprocessError(
            f"{' '.join(ldd_cmd)} exited {completed.returncode}: {completed.stderr.strip()}"
        )
    first_line = completed.stdout.splitlines()[0] if completed.stdout else ""
    if not first_line:
        raise ValueError(f"{' '.join(ldd_cmd)} produced no output")
    return first_line.strip()


def _read_compiler_version(gcc_cmd: tuple[str, ...]) -> str:
    completed = subprocess.run(
        list(gcc_cmd), capture_output=True, text=True, timeout=SUBPROCESS_TIMEOUT_SECONDS,
    )
    if completed.returncode != 0:
        raise subprocess.SubprocessError(
            f"{' '.join(gcc_cmd)} exited {completed.returncode}: {completed.stderr.strip()}"
        )
    first_line = completed.stdout.splitlines()[0] if completed.stdout else ""
    if not first_line:
        raise ValueError(f"{' '.join(gcc_cmd)} produced no output")
    return first_line.strip()


def _read_memory_total_bytes(path: Path) -> int:
    if not path.is_file():
        raise FileNotFoundError(f"{path} not found")
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("MemTotal"):
            _, _, remainder = line.partition(":")
            fields = remainder.strip().split()
            if not fields:
                raise ValueError(f"malformed MemTotal line: {line!r}")
            kib = _parse_float_strict(fields[0])
            return int(kib * 1024)
    raise ValueError(f"no MemTotal line found in {path}")


def _read_cgroup_cpu_stat(path: Path) -> dict[str, int | str]:
    if not path.is_file():
        raise FileNotFoundError(f"{path} not found")
    stats: dict[str, int | str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        key, _, value = line.partition(" ")
        if not key:
            continue
        value = value.strip()
        stats[key] = int(value) if value.lstrip("-").isdigit() else value
    return stats


def read_cgroup_cpu_stat(path: Path = CGROUP_CPU_STAT_PATH) -> dict[str, int | str] | str:
    """Public, sentinel-returning wrapper around `_read_cgroup_cpu_stat`.

    Reuses the same parse the fingerprint already relies on. Returns
    `UNAVAILABLE` when the path is absent, and an empty mapping (never
    `UNAVAILABLE`) when the file is present but empty, so the two cases stay
    distinguishable to callers such as `sample_cpu_window`.
    """
    try:
        return _read_cgroup_cpu_stat(path)
    except OSError:
        return UNAVAILABLE


def _read_cgroup_cpu_max(path: Path) -> str:
    if not path.is_file():
        raise FileNotFoundError(f"{path} not found")
    return path.read_text(encoding="utf-8").strip()


def _read_systemd_timers(systemctl_cmd: tuple[str, ...]) -> list[str]:
    completed = subprocess.run(
        list(systemctl_cmd), capture_output=True, text=True, timeout=SUBPROCESS_TIMEOUT_SECONDS,
    )
    if completed.returncode != 0:
        raise subprocess.SubprocessError(
            f"{' '.join(systemctl_cmd)} exited {completed.returncode}: {completed.stderr.strip()}"
        )
    return completed.stdout.splitlines()


def _read_runner_image_version(env_var: str) -> str:
    value = os.environ.get(env_var)
    if value is None:
        raise LookupError(f"environment variable {env_var} is not set")
    return value


def _derive_cycles_rate_hz(cycles: float, elapsed_ns: float) -> float:
    """cycles / elapsed_seconds, in hertz.

    Uses the exact same arithmetic as perf_noise_report.derived_rate_hz's
    per-record computation (`cycles / (avg_ns * BENCH_COUNT * 1e-9)`):
    `elapsed_ns` here plays the role of `avg_ns * BENCH_COUNT`, so
    `elapsed_ns * 1e-9` is the same elapsed-seconds quantity. The two
    derivations must stay identical, or a rate measured here would bucket
    into a different perf_noise_report.host_group_id than the historical
    records it needs to retroactively label.
    """
    elapsed_s = elapsed_ns * 1e-9
    return cycles / elapsed_s


def _measure_alu_ops_per_second(iterations: int) -> float:
    start_ns = time.perf_counter_ns()
    total = 0
    for i in range(iterations):
        total += i
    elapsed_ns = time.perf_counter_ns() - start_ns
    if elapsed_ns <= 0:
        raise ValueError("non-positive elapsed time measuring alu component")
    return iterations / (elapsed_ns * 1e-9)


def _measure_memcpy_bytes_per_second(total_bytes: int, block_bytes: int) -> float:
    source = bytearray(block_bytes)
    dest = bytearray(total_bytes)
    start_ns = time.perf_counter_ns()
    offset = 0
    while offset < total_bytes:
        chunk = min(block_bytes, total_bytes - offset)
        dest[offset:offset + chunk] = source[:chunk]
        offset += chunk
    elapsed_ns = time.perf_counter_ns() - start_ns
    if elapsed_ns <= 0:
        raise ValueError("non-positive elapsed time measuring memcpy component")
    return total_bytes / (elapsed_ns * 1e-9)


def _measure_syscall_ns_per_call(iterations: int) -> float:
    start_ns = time.perf_counter_ns()
    for _ in range(iterations):
        os.getppid()
    elapsed_ns = time.perf_counter_ns() - start_ns
    if elapsed_ns <= 0:
        raise ValueError("non-positive elapsed time measuring syscall component")
    return elapsed_ns / iterations


def _measure_tsc_hz(sample_seconds: float, cpuinfo_path: Path) -> float:
    """Measure the TSC rate in hertz.

    Prefers hwcounter's RDTSC read across a monotonic sample window (a real
    cycles-over-elapsed-time measurement, via _derive_cycles_rate_hz). When
    hwcounter is not importable, falls back to the documented alternative of
    reading /proc/cpuinfo's advertised "cpu MHz" field: not an independently
    measured cycle count, but the best available reading without a native
    RDTSC access path.
    """
    if HAS_HWCOUNTER:
        start_cycles = hwcounter.count()
        start_ns = time.perf_counter_ns()
        deadline_ns = start_ns + int(sample_seconds * 1e9)
        while time.perf_counter_ns() < deadline_ns:
            pass
        elapsed_cycles = hwcounter.count_end() - start_cycles
        elapsed_ns = time.perf_counter_ns() - start_ns
        if elapsed_ns <= 0:
            raise ValueError("non-positive elapsed time measuring tsc component")
        return _derive_cycles_rate_hz(elapsed_cycles, elapsed_ns)
    return _parse_float_strict(_read_cpuinfo_field(cpuinfo_path, "cpu MHz")) * 1e6


def _median_and_mad(samples: list[float]) -> tuple[float, float]:
    median = statistics.median(samples)
    mad = statistics.median([abs(sample - median) for sample in samples])
    return median, mad


def _collect_component(
    key: str,
    errors: list[str],
    unit: str,
    repeats: int,
    sample_fn: Callable[[], float],
) -> Any:
    """Run sample_fn() `repeats` times, returning a component entry with
    `value` (the median), `unit`, `repeats`, `median`, `mad`, and the raw
    `samples` list. Degrades to UNAVAILABLE plus a recorded reason on any of
    the documented failure classes, never raising.
    """
    try:
        samples = [_parse_float_strict(sample_fn()) for _ in range(repeats)]
    except (OSError, subprocess.SubprocessError, ValueError, LookupError) as exc:
        errors.append(f"{key}: {type(exc).__name__}: {exc}")
        return UNAVAILABLE

    median, mad = _median_and_mad(samples)
    return {
        "value": median,
        "unit": unit,
        "repeats": repeats,
        "median": median,
        "mad": mad,
        "samples": samples,
    }


def collect_calibration_vector(
    *,
    alu_iterations: int = CALIBRATION_ALU_ITERATIONS,
    memcpy_bytes: int = CALIBRATION_MEMCPY_BYTES,
    memcpy_block_bytes: int = CALIBRATION_MEMCPY_BLOCK_BYTES,
    syscall_iterations: int = CALIBRATION_SYSCALL_ITERATIONS,
    tsc_sample_seconds: float = CALIBRATION_TSC_SAMPLE_SECONDS,
    repeats: int = CALIBRATION_REPEATS,
    cpuinfo_path: Path = PROC_CPUINFO_PATH,
) -> dict[str, Any]:
    """Collect the four-component calibration vector.

    Four components -- alu, memcpy, syscall, tsc -- each measured and
    reported independently, never blended into a fifth overall score: a
    metric normalized against the wrong component is exactly the failure
    mode a single blended calibrator would hide (numpy matmul and sha256
    were rejected as calibrators for the same reason: their own CPU-model-
    dependent dispatch would put a confound inside the thing meant to
    cancel CPU variation).
    """
    errors: list[str] = []

    alu = _collect_component(
        "calibration_alu", errors, "ops_per_second", repeats,
        lambda: _measure_alu_ops_per_second(alu_iterations),
    )
    memcpy = _collect_component(
        "calibration_memcpy", errors, "bytes_per_second", repeats,
        lambda: _measure_memcpy_bytes_per_second(memcpy_bytes, memcpy_block_bytes),
    )
    syscall = _collect_component(
        "calibration_syscall", errors, "nanoseconds_per_call", repeats,
        lambda: _measure_syscall_ns_per_call(syscall_iterations),
    )
    tsc = _collect_component(
        "calibration_tsc", errors, "hertz", repeats,
        lambda: _measure_tsc_hz(tsc_sample_seconds, cpuinfo_path),
    )

    return {
        "calibration_schema_version": CALIBRATION_SCHEMA_VERSION,
        "components": {
            "alu": alu,
            "memcpy": memcpy,
            "syscall": syscall,
            "tsc": tsc,
        },
        "errors": errors,
    }


def read_proc_stat_cpu(path: Path = PROC_STAT_PATH) -> list[int] | str:
    """Parse the aggregate `cpu` line of /proc/stat into its ten integer
    fields, in order: user, nice, system, idle, iowait, irq, softirq,
    steal, guest, guest_nice -- zero-based index 7 is steal. Returns
    UNAVAILABLE rather than raising when the file is missing or the line is
    malformed.
    """
    try:
        if not path.is_file():
            raise FileNotFoundError(f"{path} not found")
        with path.open(encoding="utf-8") as fh:
            first_line = fh.readline()
        fields = first_line.split()
        if not fields or fields[0] != "cpu":
            raise ValueError(f"no aggregate cpu line found in {path}: {first_line!r}")
        values = [int(field) for field in fields[1:11]]
        if len(values) != 10:
            raise ValueError(f"expected 10 cpu fields in {path}, got {len(values)}: {first_line!r}")
        return values
    except (OSError, ValueError):
        return UNAVAILABLE


def _cgroup_int_delta(before: dict[str, Any], after: dict[str, Any], key: str) -> Any:
    before_value = before.get(key)
    after_value = after.get(key)
    if not isinstance(before_value, int) or isinstance(before_value, bool):
        return UNAVAILABLE
    if not isinstance(after_value, int) or isinstance(after_value, bool):
        return UNAVAILABLE
    return after_value - before_value


def order_windows(windows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Order windows deterministically for reporting: primarily by
    steal_fraction (unavailable sorts last), tie-broken by label so windows
    that share an identical steal fraction never reorder between runs.
    """
    def sort_key(window: dict[str, Any]) -> tuple[int, float, str]:
        fraction = window.get("steal_fraction")
        if not isinstance(fraction, (int, float)) or isinstance(fraction, bool):
            return (1, 0.0, str(window.get("label", "")))
        return (0, float(fraction), str(window.get("label", "")))

    return sorted(windows, key=sort_key)


def sample_cpu_window(
    label: str,
    fn: Callable[[], Any],
    *,
    steal_threshold: float = DEFAULT_STEAL_THRESHOLD,
    proc_stat_path: Path = PROC_STAT_PATH,
    cgroup_cpu_stat_path: Path = CGROUP_CPU_STAT_PATH,
) -> dict[str, Any]:
    """Run fn() while sampling steal time and cgroup throttling before and
    after, reporting both as two distinct signals.

    Hypervisor steal time and cgroup v2 CFS throttling are two different,
    independently documented kernel interfaces measuring superficially
    similar symptoms with different root causes and different remedies; this
    function never combines them into one contamination boolean.
    """
    before_stat = read_proc_stat_cpu(proc_stat_path)
    before_cgroup = read_cgroup_cpu_stat(cgroup_cpu_stat_path)
    start_ns = time.perf_counter_ns()

    result = fn()

    wall_seconds = (time.perf_counter_ns() - start_ns) * 1e-9
    after_stat = read_proc_stat_cpu(proc_stat_path)
    after_cgroup = read_cgroup_cpu_stat(cgroup_cpu_stat_path)

    if before_stat == UNAVAILABLE or after_stat == UNAVAILABLE:
        steal_jiffies_delta: Any = UNAVAILABLE
        cpu_total_jiffies_delta: Any = UNAVAILABLE
        steal_fraction: Any = UNAVAILABLE
    else:
        steal_jiffies_delta = after_stat[7] - before_stat[7]
        cpu_total_jiffies_delta = sum(after_stat) - sum(before_stat)
        steal_fraction = (
            UNAVAILABLE if cpu_total_jiffies_delta == 0
            else steal_jiffies_delta / cpu_total_jiffies_delta
        )

    steal_flagged = (
        isinstance(steal_fraction, (int, float))
        and not isinstance(steal_fraction, bool)
        and steal_fraction >= steal_threshold
    )

    if before_cgroup == UNAVAILABLE or after_cgroup == UNAVAILABLE:
        cgroup_nr_periods_delta: Any = UNAVAILABLE
        cgroup_nr_throttled_delta: Any = UNAVAILABLE
        cgroup_throttled_usec_delta: Any = UNAVAILABLE
    else:
        cgroup_nr_periods_delta = _cgroup_int_delta(before_cgroup, after_cgroup, "nr_periods")
        cgroup_nr_throttled_delta = _cgroup_int_delta(before_cgroup, after_cgroup, "nr_throttled")
        cgroup_throttled_usec_delta = _cgroup_int_delta(before_cgroup, after_cgroup, "throttled_usec")

    return {
        "label": label,
        "wall_seconds": wall_seconds,
        "steal_jiffies_delta": steal_jiffies_delta,
        "cpu_total_jiffies_delta": cpu_total_jiffies_delta,
        "steal_fraction": steal_fraction,
        "cgroup_nr_periods_delta": cgroup_nr_periods_delta,
        "cgroup_nr_throttled_delta": cgroup_nr_throttled_delta,
        "cgroup_throttled_usec_delta": cgroup_throttled_usec_delta,
        "steal_threshold": steal_threshold,
        "steal_comparison": STEAL_COMPARISON_OPERATOR,
        "steal_flagged": steal_flagged,
        "result": result,
    }


def collect_fingerprint(
    *,
    cpuinfo_path: Path = PROC_CPUINFO_PATH,
    meminfo_path: Path = PROC_MEMINFO_PATH,
    cgroup_cpu_stat_path: Path = CGROUP_CPU_STAT_PATH,
    cgroup_cpu_max_path: Path = CGROUP_CPU_MAX_PATH,
    ldd_cmd: tuple[str, ...] = LDD_VERSION_CMD,
    gcc_cmd: tuple[str, ...] = GCC_VERSION_CMD,
    systemctl_cmd: tuple[str, ...] = SYSTEMCTL_LIST_TIMERS_CMD,
    image_version_env: str = RUNNER_IMAGE_VERSION_ENV,
) -> dict[str, Any]:
    """Collect the per-run environment fingerprint.

    Every field is read through `_try`, which never lets an exception escape:
    an unreadable source path, a missing or failing subprocess, or a value
    that fails to parse all yield `UNAVAILABLE` plus a reason string appended
    to `errors`, rather than raising. Every documented key is always present
    in the returned mapping.
    """
    errors: list[str] = []

    cpu_model = _try("cpu_model", errors, lambda: _read_cpuinfo_field(cpuinfo_path, "model name"))
    cpu_mhz = _try(
        "cpu_mhz", errors,
        lambda: _parse_float_strict(_read_cpuinfo_field(cpuinfo_path, "cpu MHz")),
    )
    nproc = _try("nproc", errors, _read_nproc)
    kernel_version = _try("kernel_version", errors, _read_kernel_version)
    glibc_version = _try("glibc_version", errors, lambda: _read_glibc_version(ldd_cmd))
    cpython_version = _try("cpython_version", errors, _read_cpython_version)
    compiler_version = _try("compiler_version", errors, lambda: _read_compiler_version(gcc_cmd))
    memory_total_bytes = _try(
        "memory_total_bytes", errors, lambda: _read_memory_total_bytes(meminfo_path),
    )
    cgroup_v2_cpu_stat = _try(
        "cgroup_v2_cpu_stat", errors, lambda: _read_cgroup_cpu_stat(cgroup_cpu_stat_path),
    )
    cgroup_v2_cpu_max = _try(
        "cgroup_v2_cpu_max", errors, lambda: _read_cgroup_cpu_max(cgroup_cpu_max_path),
    )
    systemd_timers = _try("systemd_timers", errors, lambda: _read_systemd_timers(systemctl_cmd))
    runner_image_version = _try(
        "runner_image_version", errors, lambda: _read_runner_image_version(image_version_env),
    )

    return {
        "cpu_model": cpu_model,
        "cpu_mhz": cpu_mhz,
        "nproc": nproc,
        "kernel_version": kernel_version,
        "glibc_version": glibc_version,
        "cpython_version": cpython_version,
        "compiler_version": compiler_version,
        "memory_total_bytes": memory_total_bytes,
        "cgroup_v2_cpu_stat": cgroup_v2_cpu_stat,
        "cgroup_v2_cpu_max": cgroup_v2_cpu_max,
        "systemd_timers": systemd_timers,
        "runner_image_version": runner_image_version,
        "fingerprint_schema_version": FINGERPRINT_SCHEMA_VERSION,
        "errors": errors,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the collected result as JSON instead of one key per line",
    )
    parser.add_argument(
        "--fingerprint-only",
        action="store_true",
        help="Collect and print only the environment fingerprint",
    )
    parser.add_argument(
        "--calibration-only",
        action="store_true",
        help="Collect and print only the calibration vector",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if args.calibration_only:
        payload: dict[str, Any] = collect_calibration_vector()
    elif args.fingerprint_only:
        payload = collect_fingerprint()
    else:
        payload = {
            "fingerprint": collect_fingerprint(),
            "calibration": collect_calibration_vector(),
        }

    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        for key in sorted(payload):
            print(f"{key}: {payload[key]}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
