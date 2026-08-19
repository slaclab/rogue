#!/usr/bin/env python3
# ----------------------------------------------------------------------------
# Title      : ROGUE Runner Capability Probe Entry Point
# ----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
# ----------------------------------------------------------------------------

"""Assemble every measurement module built in this phase into one probe job.

The value of this phase comes from comparisons, and a comparison is only
meaningful when the host is held constant. Every stage below runs inside this
one process on one host, so every instrument multiplier and every
intervention effect is measured with the host held constant. A stage that
raises is contained by run_stage(): it costs that stage's data and nothing
else, because runs are the scarce resource in this phase.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Callable

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import env_fingerprint  # noqa: E402  (flat sibling import, path inserted above)
import probe_instruments  # noqa: E402  (flat sibling import, path inserted above)
import probe_interventions  # noqa: E402  (flat sibling import, path inserted above)
import probe_perf_events  # noqa: E402  (flat sibling import, path inserted above)


PROBE_SCHEMA_VERSION = 1

STAGE_FAILURE_STATUS = "failed"
STAGE_ERROR_MESSAGE_MAX_CHARS = 2000
STDERR_EXCERPT_MAX_CHARS = 2000

_TIMER_UNIT_RE = re.compile(r"(\S+\.timer)\b")

# Cold build timing (an incidental byproduct of needing a real build here). The same configure/compile
# commands the shared perf job already runs (rogue_ci.yml's perf_test job),
# so the measured figure is comparable to that job's real cost. Building is
# required anyway: the confirmation leg below needs an importable library.
BUILD_SUBPROCESS_TIMEOUT_SECONDS = 1800
CMAKE_CONFIGURE_CMD: tuple[str, ...] = ("cmake", "-S", ".", "-B", "build", "-DROGUE_INSTALL=local")
CMAKE_INSTALL_CMD: tuple[str, ...] = ("cmake", "--build", "build", "--target", "install")

# Confirmation leg: the two tests/perf modules chosen as one from each
# of Phase 1's two populations. Neither is modified by this module.
CONFIRMATION_TRANSACTION_MODULE = "tests/perf/test_variable_rate_perf.py"
CONFIRMATION_STREAM_MODULE = "tests/perf/test_stream_bridge_perf.py"
CONFIRMATION_MODULES: tuple[str, ...] = (CONFIRMATION_TRANSACTION_MODULE, CONFIRMATION_STREAM_MODULE)
CONFIRMATION_REPEATS = 3
CONFIRMATION_SUBPROCESS_TIMEOUT_SECONDS = 600

# The confirmation leg needs an importable pyrogue, which the freshly-built
# tree only provides once build/setup_rogue.sh is sourced (the shared perf
# job does the same before running tests/perf). Sourced once per collection
# and its PYTHONPATH/LD_LIBRARY_PATH read back, rather than re-derived from
# ROGUE_DIR by hand, so this stays correct if the template ever changes.
ROGUE_SETUP_SCRIPT = "build/setup_rogue.sh"
_ROGUE_SETUP_ENV_KEYS: tuple[str, ...] = ("PYTHONPATH", "LD_LIBRARY_PATH", "DYLD_LIBRARY_PATH")

CALLGRIND_EXCLUSION_REASON = (
    "the call-graph profiler's overhead multiplier makes pointing it at a real performance "
    "module structurally incompatible with any sane job timeout; it is measured only against "
    "the synthetic workload in the instrument sweep, never against shipped code"
)

# Instruments the confirmation leg can wrap around a separate pytest
# subprocess (an external process boundary, matching each instrument's own
# mechanism from the synthetic sweep: strace traces a process, LD_PRELOAD is
# inherited at exec, perf stat wraps a launched command).
_SUBPROCESS_WRAPPABLE_INSTRUMENTS = (
    probe_instruments.INSTRUMENT_STRACE,
    probe_instruments.INSTRUMENT_MALLOC_INTERPOSER,
    probe_instruments.INSTRUMENT_PERF_SOFTWARE_EVENTS,
)
# Instruments that can only observe allocations/resources inside the current
# interpreter (Python tracemalloc, glibc mallinfo2 via ctypes, getrusage of
# the current process): confirming them against a real module would require
# either modifying the target module (out of scope) or running pytest
# in-process, which this module does not do. Recorded as skipped with a
# stated structural reason rather than fabricating a cross-process reading.
_STRUCTURALLY_UNCONFIRMABLE_INSTRUMENTS = (
    probe_instruments.INSTRUMENT_PYTHON_TRACEMALLOC,
    probe_instruments.INSTRUMENT_ALLOCATOR_STATS,
    probe_instruments.INSTRUMENT_RESOURCE_USAGE,
)
STRUCTURAL_SKIP_REASON = (
    "cannot observe allocations or resource usage inside a separate pytest subprocess "
    "without modifying the target performance module; measured only against the synthetic "
    "workload in the instrument sweep"
)
SKIP_REASON_INSTRUMENTS_STAGE_NOT_RUN = (
    "the instruments stage did not run in this job; no synthetic-sweep verdict is available"
)


def run_stage(name: str, fn: Callable[[], Any]) -> Any:
    """Run fn(), returning its result on success.

    On any exception, returns a mapping recording the failure (status,
    exception class name, bounded message) instead of letting the exception
    escape. `name` is accepted for symmetry with the calling convention every
    stage is invoked through, even though this function itself does not
    append to any errors list -- collect_stage_results does that, since it is
    the one holding the record's errors list.
    """
    try:
        return fn()
    except Exception as exc:  # a stage must never abort the run
        return {
            "status": STAGE_FAILURE_STATUS,
            "exception_class": type(exc).__name__,
            "message": str(exc)[:STAGE_ERROR_MESSAGE_MAX_CHARS],
        }


def _is_stage_exception_failure(result: Any) -> bool:
    return (
        isinstance(result, dict)
        and result.get("status") == STAGE_FAILURE_STATUS
        and "exception_class" in result
    )


def _json_safe_window(window: dict[str, Any]) -> dict[str, Any]:
    """Drop the `result` field before a window is added to the record's
    shared window list: a stage's workload_fn may return a raw, non-JSON
    -serializable object (subprocess.CompletedProcess for the instrument and
    confirmation stages), which the stage itself still needs to inspect
    (wall-clock, return code, output) but the aggregate window list, whose
    purpose is only the steal/cgroup-throttling deltas, never does.
    """
    return {key: value for key, value in window.items() if key != "result"}


def _make_window_collector(
    windows: list[dict[str, Any]],
) -> Callable[[str, Callable[[], Any]], dict[str, Any]]:
    """Return a window_sampler that both samples (via
    env_fingerprint.sample_cpu_window) and appends a JSON-safe copy of the
    resulting window to the shared `windows` list, so every stage that
    accepts an injectable window_sampler contributes to the record's single
    window list. The full window (including `result`) is still returned to
    the caller, which may need it.
    """
    def _collect(label: str, fn: Callable[[], Any]) -> dict[str, Any]:
        window = env_fingerprint.sample_cpu_window(label, fn)
        windows.append(_json_safe_window(window))
        return window

    return _collect


def _observed_units_from_fingerprint(fingerprint: dict[str, Any]) -> list[str]:
    """Extract systemd timer unit names from the fingerprint's captured
    `systemctl list-timers` output, so the service-stop intervention targets
    what this run actually observed rather than a hard-coded guess. Every
    matched token is a single whitespace-free `*.timer` name, so this holds
    regardless of how the surrounding date columns are padded.
    """
    timers = fingerprint.get("systemd_timers") if isinstance(fingerprint, dict) else None
    if not isinstance(timers, list):
        return []
    units: list[str] = []
    for line in timers:
        if not isinstance(line, str):
            continue
        match = _TIMER_UNIT_RE.search(line)
        if match:
            units.append(match.group(1))
    return units


def _default_probe_workload(iterations: int = 1000000) -> float:
    start_ns = time.perf_counter_ns()
    total = 0
    for i in range(iterations):
        total += i
    elapsed_ns = time.perf_counter_ns() - start_ns
    if elapsed_ns <= 0:
        raise ValueError("non-positive elapsed time measuring the intervention workload")
    return iterations / (elapsed_ns * 1e-9)


def _run_subprocess(
    argv: list[str], *, timeout: int = CONFIRMATION_SUBPROCESS_TIMEOUT_SECONDS,
) -> subprocess.CompletedProcess:
    """Injectable module-level default runner. Never raises: a missing
    binary or a timeout is captured as a nonzero-returncode result, matching
    the same never-raise contract every other probe helper in this phase
    relies on for hermetic unit testing.
    """
    try:
        return subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError) as exc:
        return subprocess.CompletedProcess(argv, returncode=1, stdout="", stderr=str(exc))


def _bounded_excerpt(text: str | None, limit: int = STDERR_EXCERPT_MAX_CHARS) -> str:
    return (text or "")[:limit]


def collect_build_timing(
    *,
    runner: Callable[..., subprocess.CompletedProcess] = _run_subprocess,
    parallelism: int | None = None,
) -> dict[str, Any]:
    """Time the same cold configure/compile/install commands the shared perf
    job already runs, recording each elapsed figure separately plus the
    parallelism used and every exit code. A non-zero exit is recorded as a
    failure mapping, never raised: a run whose build failed still has a
    complete instrument sweep worth keeping.
    """
    parallelism = parallelism if parallelism is not None else (os.cpu_count() or 1)

    configure_start = time.monotonic()
    configure_completed = runner(list(CMAKE_CONFIGURE_CMD), timeout=BUILD_SUBPROCESS_TIMEOUT_SECONDS)
    configure_seconds = time.monotonic() - configure_start

    if configure_completed.returncode != 0:
        return {
            "status": "failed",
            "step": "configure",
            "parallelism": parallelism,
            "configure_seconds": configure_seconds,
            "configure_exit_code": configure_completed.returncode,
            "stderr_excerpt": _bounded_excerpt(configure_completed.stderr),
        }

    compile_cmd = ["cmake", "--build", "build", "-j", str(parallelism)]
    compile_start = time.monotonic()
    compile_completed = runner(compile_cmd, timeout=BUILD_SUBPROCESS_TIMEOUT_SECONDS)
    install_completed = runner(list(CMAKE_INSTALL_CMD), timeout=BUILD_SUBPROCESS_TIMEOUT_SECONDS)
    compile_seconds = time.monotonic() - compile_start

    if compile_completed.returncode != 0 or install_completed.returncode != 0:
        failed_step = "compile" if compile_completed.returncode != 0 else "install"
        failing_completed = compile_completed if failed_step == "compile" else install_completed
        return {
            "status": "failed",
            "step": failed_step,
            "parallelism": parallelism,
            "configure_seconds": configure_seconds,
            "configure_exit_code": configure_completed.returncode,
            "compile_seconds": compile_seconds,
            "compile_exit_code": compile_completed.returncode,
            "install_exit_code": install_completed.returncode,
            "stderr_excerpt": _bounded_excerpt(failing_completed.stderr),
        }

    return {
        "status": "ok",
        "parallelism": parallelism,
        "configure_seconds": configure_seconds,
        "configure_exit_code": configure_completed.returncode,
        "compile_seconds": compile_seconds,
        "compile_exit_code": compile_completed.returncode,
        "install_exit_code": install_completed.returncode,
    }


def _rogue_setup_env(runner: Callable[..., subprocess.CompletedProcess]) -> dict[str, str]:
    """Source build/setup_rogue.sh in a real shell and read back the handful
    of variables it exports (PYTHONPATH, LD_LIBRARY_PATH), rather than
    re-deriving them from ROGUE_DIR by hand. Returns an empty mapping,
    never raising, when the script is absent or sourcing it fails -- the
    caller's subprocess invocation then simply inherits this process's own
    environment unchanged.
    """
    completed = runner(["bash", "-c", f"source {ROGUE_SETUP_SCRIPT} && env"])
    if completed.returncode != 0:
        return {}
    env_vars: dict[str, str] = {}
    for line in (completed.stdout or "").splitlines():
        key, sep, value = line.partition("=")
        if sep and key in _ROGUE_SETUP_ENV_KEYS:
            env_vars[key] = value
    return env_vars


def _module_pytest_argv(module_path: str) -> list[str]:
    return [sys.executable, "-m", "pytest", module_path, "-q", "-s"]


def _env_prefixed_argv(argv: list[str], env_vars: dict[str, str]) -> list[str]:
    return ["env", *[f"{key}={value}" for key, value in env_vars.items()], *argv]


def _find_instrument_entry(instrument_entries: list[dict[str, Any]], name: str) -> dict[str, Any] | None:
    for entry in instrument_entries:
        if entry.get("name") == name:
            return entry
    return None


def _parse_strace_total_calls(text: str) -> int | None:
    """Extract the `calls` column from strace -c's trailing `total` row.
    Mirrors probe_instruments.py's own private parser: duplicated here
    rather than imported, matching this phase's established convention of
    small independent per-module helpers over reaching into another
    module's private (underscore-prefixed) functions.
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


def _read_interposer_malloc_calls(path: Path) -> int | None:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    for line in text.splitlines():
        key, _, value = line.partition(" ")
        if key == "malloc_calls":
            try:
                return int(value.strip())
            except ValueError:
                return None
    return None


def _wrap_confirmation_argv(
    name: str, module_path: str, module_env: dict[str, str], entry: dict[str, Any], repeat_index: int,
) -> tuple[list[str], dict[str, Any]]:
    """Build the wrapped argv for one confirmation repeat of one instrument.
    Returns (argv, extra_state), where extra_state carries whatever
    _confirmation_count needs afterward (e.g. the interposer dump path).
    """
    base_argv = _module_pytest_argv(module_path)
    if name == probe_instruments.INSTRUMENT_STRACE:
        wrapped = [*probe_instruments.STRACE_CMD_PREFIX, *_env_prefixed_argv(base_argv, module_env)]
        return wrapped, {}
    if name == probe_instruments.INSTRUMENT_PERF_SOFTWARE_EVENTS:
        events = ",".join(probe_perf_events.PERF_SOFTWARE_EVENTS)
        wrapped = ["perf", "stat", "-e", events, "--", *_env_prefixed_argv(base_argv, module_env)]
        return wrapped, {}
    if name == probe_instruments.INSTRUMENT_MALLOC_INTERPOSER:
        so_path = (entry.get("install") or {}).get("path")
        dump_path = Path(tempfile.mkdtemp()) / f"confirmation_alloc_{Path(module_path).stem}_{repeat_index}.txt"
        env_vars = dict(module_env)
        if so_path:
            env_vars["LD_PRELOAD"] = str(so_path)
        env_vars["ROGUE_PROBE_ALLOC_OUT"] = str(dump_path)
        return _env_prefixed_argv(base_argv, env_vars), {"dump_path": dump_path}
    return _env_prefixed_argv(base_argv, module_env), {}


def _confirmation_count(
    name: str, completed: subprocess.CompletedProcess, extra_state: dict[str, Any],
) -> int | None:
    if name == probe_instruments.INSTRUMENT_STRACE:
        return _parse_strace_total_calls(completed.stderr or "")
    if name == probe_instruments.INSTRUMENT_PERF_SOFTWARE_EVENTS:
        events = list(probe_perf_events.PERF_SOFTWARE_EVENTS)
        parsed = probe_perf_events.parse_perf_stat_output(completed.stderr or "", events)
        values = [item["value"] for item in parsed if item["status"] == probe_perf_events.STATUS_COUNTED]
        return sum(values) if values else None
    if name == probe_instruments.INSTRUMENT_MALLOC_INTERPOSER:
        dump_path = extra_state.get("dump_path")
        return _read_interposer_malloc_calls(dump_path) if dump_path else None
    return None


def collect_confirmation_leg(
    instrument_entries: list[dict[str, Any]],
    *,
    modules: tuple[str, ...] = CONFIRMATION_MODULES,
    repeats: int = CONFIRMATION_REPEATS,
    results_dir: Path | None = None,
    runner: Callable[..., subprocess.CompletedProcess] = _run_subprocess,
    window_sampler: Callable[[str, Callable[[], Any]], dict[str, Any]] = env_fingerprint.sample_cpu_window,
) -> dict[str, Any]:
    """Run the two named performance modules, once per selected cheap
    instrument, confirming that the synthetic sweep's conclusions hold on
    shipped code.

    Only an instrument whose synthetic-sweep verdict is `usable` is run
    against real modules; every other one is recorded as skipped with the
    reason naming its verdict. The call-graph profiler is never invoked here
    under any verdict: its exclusion is unconditional and stated explicitly.
    A module whose invocation fails is recorded with the failure and the
    other module still runs; both module paths are always present in the
    returned mapping, even when neither could be run.
    """
    results_dir = results_dir if results_dir is not None else Path(tempfile.mkdtemp()) / "confirmation-perf-results"
    entry_by_name = {
        entry.get("name"): entry for entry in instrument_entries if isinstance(entry, dict)
    }
    rogue_setup_env = _rogue_setup_env(runner)

    modules_out: dict[str, Any] = {}
    for module_path in modules:
        module_env = {"PERF_RESULTS_DIR": str(results_dir), **rogue_setup_env}
        module_stem = Path(module_path).stem
        baseline_argv = _env_prefixed_argv(_module_pytest_argv(module_path), module_env)

        baseline_seconds: list[float] = []
        baseline_failures: list[subprocess.CompletedProcess] = []
        for i in range(repeats):
            window = window_sampler(f"confirmation_baseline_{module_stem}_{i}", lambda a=baseline_argv: runner(a))
            baseline_seconds.append(window["wall_seconds"])
            if window["result"].returncode != 0:
                baseline_failures.append(window["result"])

        instruments_out: dict[str, Any] = {}
        for name in probe_instruments.INSTRUMENT_NAMES:
            if name == probe_instruments.INSTRUMENT_CALLGRIND:
                continue

            entry = entry_by_name.get(name)
            if entry is None:
                instruments_out[name] = {"status": "skipped", "reason": SKIP_REASON_INSTRUMENTS_STAGE_NOT_RUN}
                continue

            verdict = entry.get("verdict")
            if verdict != probe_instruments.VERDICT_USABLE:
                instruments_out[name] = {"status": "skipped", "reason": verdict}
                continue

            if name in _STRUCTURALLY_UNCONFIRMABLE_INSTRUMENTS:
                instruments_out[name] = {"status": "skipped", "reason": STRUCTURAL_SKIP_REASON}
                continue

            instrumented_seconds: list[float] = []
            counts: list[int] = []
            failure_detail: dict[str, Any] | None = None
            for i in range(repeats):
                wrapped_argv, extra_state = _wrap_confirmation_argv(name, module_path, module_env, entry, i)
                window = window_sampler(
                    f"confirmation_{name}_{module_stem}_{i}", lambda a=wrapped_argv: runner(a),
                )
                completed = window["result"]
                instrumented_seconds.append(window["wall_seconds"])
                if completed.returncode != 0 and failure_detail is None:
                    failure_detail = {
                        "exit_code": completed.returncode,
                        "stderr_excerpt": _bounded_excerpt(completed.stderr),
                    }
                count = _confirmation_count(name, completed, extra_state)
                if count is not None:
                    counts.append(count)

            overhead = probe_instruments.measure_overhead(baseline_seconds, instrumented_seconds)
            repeatability = (
                probe_instruments.repeatability_verdict(counts) if counts
                else {"verdict": probe_instruments.INSUFFICIENT_SAMPLES, "n": len(counts)}
            )
            instrument_result: dict[str, Any] = {
                "status": "failed" if failure_detail else "ok",
                "repeats": repeats,
                "overhead_multiplier": overhead,
                "counts": counts,
                "repeatability": repeatability,
            }
            if failure_detail:
                instrument_result["failure"] = failure_detail
            instruments_out[name] = instrument_result

        modules_out[module_path] = {
            "baseline_seconds": baseline_seconds,
            "baseline_status": "failed" if baseline_failures else "ok",
            "instruments": instruments_out,
        }
        if baseline_failures:
            modules_out[module_path]["baseline_failure"] = {
                "exit_code": baseline_failures[0].returncode,
                "stderr_excerpt": _bounded_excerpt(baseline_failures[0].stderr),
            }

    return {
        "modules": modules_out,
        "excluded_instruments": {
            probe_instruments.INSTRUMENT_CALLGRIND: CALLGRIND_EXCLUSION_REASON,
        },
        "results_dir": str(results_dir),
    }


def _fingerprint_stage_fn(ctx: dict[str, Any]) -> Callable[[], Any]:
    return env_fingerprint.collect_fingerprint


def _calibration_stage_fn(ctx: dict[str, Any]) -> Callable[[], Any]:
    args = ctx["args"]
    return lambda: env_fingerprint.collect_calibration_vector(repeats=args.repeats)


def _perf_events_stage_fn(ctx: dict[str, Any]) -> Callable[[], Any]:
    return probe_perf_events.collect_perf_capability


def _instruments_stage_fn(ctx: dict[str, Any]) -> Callable[[], Any]:
    args = ctx["args"]
    window_sampler = _make_window_collector(ctx["windows"])
    return lambda: probe_instruments.collect_instrument_sweep(
        repeats=args.repeats, window_sampler=window_sampler,
    )


def _interventions_stage_fn(ctx: dict[str, Any]) -> Callable[[], Any]:
    fingerprint = ctx["record"].get("fingerprint", {})
    observed_units = _observed_units_from_fingerprint(
        fingerprint if isinstance(fingerprint, dict) else {},
    )
    window_sampler = _make_window_collector(ctx["windows"])
    return lambda: probe_interventions.collect_interventions(
        _default_probe_workload, observed_units, window_sampler=window_sampler,
    )


def _confirmation_stage_fn(ctx: dict[str, Any]) -> Callable[[], Any]:
    instrument_entries = ctx["record"].get("instruments", [])
    if not isinstance(instrument_entries, list):
        instrument_entries = []
    window_sampler = _make_window_collector(ctx["windows"])
    return lambda: collect_confirmation_leg(instrument_entries, window_sampler=window_sampler)


def _build_stage_fn(ctx: dict[str, Any]) -> Callable[[], Any]:
    return collect_build_timing


# STAGES is an ordered mapping from stage name to (record_key, factory).
# `factory(ctx)` returns the zero-argument collector callable run_stage()
# invokes for that stage; `ctx` bundles the partial record built so far
# (`ctx["record"]`), the parsed CLI args (`ctx["args"]`), and the shared
# windows accumulator (`ctx["windows"]`) so a stage such as interventions can
# read an earlier stage's output in the same run. Order matters:
# fingerprint runs first because the service-stop intervention needs the
# timer listing it captures, and build runs before confirmation because the
# confirmation leg needs the library build produces to be importable --
# confirmed the hard way on a real hosted run, where confirmation running
# before build meant every confirmation invocation failed at pytest
# collection with ModuleNotFoundError: No module named 'pyrogue'.
STAGES: dict[str, tuple[str, Callable[[dict[str, Any]], Callable[[], Any]]]] = {
    "fingerprint": ("fingerprint", _fingerprint_stage_fn),
    "calibration": ("calibration", _calibration_stage_fn),
    "perf_events": ("perf_events", _perf_events_stage_fn),
    "instruments": ("instruments", _instruments_stage_fn),
    "interventions": ("interventions", _interventions_stage_fn),
    "build": ("build", _build_stage_fn),
    "confirmation": ("confirmation", _confirmation_stage_fn),
}


def collect_stage_results(
    stage_names: list[str],
    args: argparse.Namespace,
    *,
    stages: dict[str, tuple[str, Callable[[dict[str, Any]], Callable[[], Any]]]] = STAGES,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    """Run every stage named in `stage_names`, in `stages`' own order, through
    run_stage(). Returns (results_by_record_key, errors, windows).

    A stage that raises never prevents a later stage from running: run_stage
    contains the exception into a failure mapping, and this function appends
    one entry to `errors` for it, then continues to the next selected stage.
    A stage not named in `stage_names` is simply not run; the caller is
    responsible for filling its record key with an empty mapping.
    """
    results: dict[str, Any] = {}
    errors: list[dict[str, Any]] = []
    windows: list[dict[str, Any]] = []
    ctx: dict[str, Any] = {"record": results, "args": args, "windows": windows}

    for name in stages:
        if name not in stage_names:
            continue
        key, factory = stages[name]
        fn = factory(ctx)
        result = run_stage(name, fn)
        if _is_stage_exception_failure(result):
            errors.append({
                "stage": name,
                "exception_class": result["exception_class"],
                "message": result["message"],
            })
        results[key] = result

    return results, errors, windows


def build_probe_record(
    *,
    job_index: str,
    github_run_id: str,
    github_run_attempt: str,
    github_sha: str,
    git_tree_hash: str,
    git_tree_hash_source: str,
    campaign_branch: str,
    runner_os: str,
    stage_results: dict[str, Any] | None = None,
    windows: list[dict[str, Any]] | None = None,
    errors: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Assemble the fixed top-level probe-record key set.

    Every key is always present, even for a stage this run did not select: an
    unselected stage's key is an empty mapping rather than being omitted.
    This is the interface contract every stage fills in and
    `probe_capability_report.py` reads.
    """
    stage_results = stage_results or {}
    windows = windows if windows is not None else []
    errors = errors if errors is not None else []

    return {
        "probe_schema_version": PROBE_SCHEMA_VERSION,
        "run": {
            "job_index": job_index,
            "github_run_id": github_run_id,
            "github_run_attempt": github_run_attempt,
            "github_sha": github_sha,
            "git_tree_hash": git_tree_hash,
            "git_tree_hash_source": git_tree_hash_source,
            "campaign_branch": campaign_branch,
            "runner_os": runner_os,
        },
        "fingerprint": stage_results.get("fingerprint", {}),
        "calibration": stage_results.get("calibration", {}),
        "windows": windows,
        "perf_events": stage_results.get("perf_events", {}),
        "instruments": stage_results.get("instruments", {}),
        "interventions": stage_results.get("interventions", {}),
        "confirmation": stage_results.get("confirmation", {}),
        "build": stage_results.get("build", {}),
        "errors": errors,
    }


def _git_tree_hash() -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD^{tree}"], capture_output=True, text=True, check=False,
    )
    if completed.returncode != 0:
        return env_fingerprint.UNAVAILABLE
    return completed.stdout.strip()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        required=True,
        help="Output path for the probe-result JSON",
    )
    parser.add_argument(
        "--stages",
        default=",".join(STAGES),
        help=f"Comma-separated stage list to run (default: all of {', '.join(STAGES)})",
    )
    parser.add_argument(
        "--repeats",
        type=int,
        default=1,
        help="In-job repeat count threaded through to the calibration vector and the "
        "instrument sweep",
    )
    parser.add_argument(
        "--tree-hash",
        default=None,
        help="Override for git rev-parse HEAD^{tree}, primarily for testing",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    requested_stages = [stage.strip() for stage in args.stages.split(",") if stage.strip()]

    unknown_stages = [name for name in requested_stages if name not in STAGES]
    if unknown_stages:
        valid = ", ".join(sorted(STAGES))
        print(
            f"error: unknown stage(s): {', '.join(unknown_stages)}; valid stages: {valid}",
            file=sys.stderr,
        )
        return 2

    stage_results, errors, windows = collect_stage_results(requested_stages, args)

    if args.tree_hash:
        tree_hash = args.tree_hash
        tree_hash_source = "explicit"
    else:
        tree_hash = _git_tree_hash()
        tree_hash_source = "git_rev_parse" if tree_hash != env_fingerprint.UNAVAILABLE else "unavailable"

    record = build_probe_record(
        job_index=os.environ.get("PROBE_JOB_INDEX", "1"),
        github_run_id=os.environ.get("GITHUB_RUN_ID", env_fingerprint.UNAVAILABLE),
        github_run_attempt=os.environ.get("GITHUB_RUN_ATTEMPT", env_fingerprint.UNAVAILABLE),
        github_sha=os.environ.get("GITHUB_SHA", env_fingerprint.UNAVAILABLE),
        git_tree_hash=tree_hash,
        git_tree_hash_source=tree_hash_source,
        campaign_branch=os.environ.get("GITHUB_REF_NAME", env_fingerprint.UNAVAILABLE),
        runner_os=os.environ.get("RUNNER_OS", env_fingerprint.UNAVAILABLE),
        stage_results=stage_results,
        windows=env_fingerprint.order_windows(windows),
        errors=errors,
    )

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
