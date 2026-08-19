#!/usr/bin/env python3
# ----------------------------------------------------------------------------
# Title      : ROGUE Perf Harness In-Job Runner
# ----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
# ----------------------------------------------------------------------------

"""In-job entry point for the perf harness campaign vehicle (.github/workflows/
perf_harness.yml) and the shared perf job (.github/workflows/rogue_ci.yml).
Owns the ccache-accelerated build, the ccache statistics this campaign's
wall-clock budget accounting requires, the resolved build-target evidence
this campaign's build-target accounting requires, the
pytest measurement invocation across the tests/perf/ modules named in
DEFAULT_PERF_MODULES, and the aggregation of every per-benchmark
tests/perf/_perf_harness.py record it finds into one tree-hash-stamped run
record.

Structured directly on scripts/probe_runner.py (Phase 2's equivalent
in-job entry point): the same run_stage()-contained per-stage failure
handling and the same injectable _run_subprocess so every unit test can
supply a fake. Deliberately does not import from probe_runner.py: that
module is Phase 2's committed diagnostic under its own regression tests, and
coupling this module to it would put Phase 2's reproduce contract at risk.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import env_fingerprint  # noqa: E402  (flat sibling import, path inserted above)


HARNESS_RUN_SCHEMA_VERSION = 1

# Matches tests/perf/_perf_harness.py's HARNESS_RESULTS_DIR_ENV value exactly;
# not imported from there since scripts/ and tests/ are separate import roots
# in this repository and tests.perf is affected by a pre-existing shadowing
# defect on this shared machine (a stray top-level `tests` package shadowing
# this repository's own `tests/` namespace package).
HARNESS_RESULTS_DIR_ENV = "PERF_HARNESS_RESULTS_DIR"

STAGE_FAILURE_STATUS = "failed"
STAGE_ERROR_MESSAGE_MAX_CHARS = 2000
STDERR_EXCERPT_MAX_CHARS = 2000

BUILD_SUBPROCESS_TIMEOUT_SECONDS = 1800
MEASUREMENT_SUBPROCESS_TIMEOUT_SECONDS = 1800

# The two flags this phase requires on the configure command: -DROGUE_BUILD_TESTS=OFF pins the
# property the resolved build-target evidence rests on rather than inheriting the CMake default
# (CMakeLists.txt:48), and
# -DCMAKE_CXX_COMPILER_LAUNCHER=ccache wires ccache in as a compiler-invocation wrapper. The
# launcher hook is honoured only by the Makefile and Ninja CMake generators; this configure
# command carries no -G flag, so it takes the platform default, which on the target
# ubuntu-24.04 runner is Unix Makefiles.
CMAKE_CONFIGURE_CMD: tuple[str, ...] = (
    "cmake", "-S", ".", "-B", "build",
    "-DROGUE_INSTALL=local", "-DROGUE_BUILD_TESTS=OFF", "-DCMAKE_CXX_COMPILER_LAUNCHER=ccache",
)
CMAKE_INSTALL_CMD: tuple[str, ...] = ("cmake", "--build", "build", "--target", "install")

# Reads the target list the "all" target expands to and the resolved ROGUE_BUILD_TESTS cache
# value, both from the already-configured build tree, rather than from a reading of
# CMakeLists.txt -- so the resolved-build-target claim rests on captured evidence, not an
# assumption about what the CMake configuration says.
CMAKE_TARGET_HELP_CMD: tuple[str, ...] = ("cmake", "--build", "build", "--target", "help")
CMAKE_CACHE_VARIABLES_CMD: tuple[str, ...] = ("cmake", "-L", "-N", "-B", "build")

# A dry run (-n) of the "all" target against an already-built tree prints exactly one "Built
# target <name>" line per target "all" actually resolves to -- literally what runs, not every
# buildable target the generator knows about (cmake --build build --target help lists every
# target, including thousands of per-source-file convenience targets Unix Makefiles always
# generates, which is NOT what "all" builds; a real hosted-runner run confirmed this the hard
# way). This only works correctly when every prerequisite object file already exists: make's -n
# stops at the first missing prerequisite otherwise, so collect_build_targets must run only
# after collect_build_timing has completed a real build, never against a bare/unconfigured tree.
CMAKE_BUILD_ALL_DRY_RUN_CMD: tuple[str, ...] = ("cmake", "--build", "build", "--target", "all", "--", "-n")
_BUILT_TARGET_RE = re.compile(r'"Built target (\S+)"')

CCACHE_VERSION_CMD: tuple[str, ...] = ("ccache", "--version")
CCACHE_ZERO_STATS_CMD: tuple[str, ...] = ("ccache", "--zero-stats")
# Machine-readable, tab-separated key/value lines -- never parsed from ccache -s's rounded
# human-readable output, whose format also varies across ccache versions.
CCACHE_STATS_CMD: tuple[str, ...] = ("ccache", "--print-stats")
CCACHE_HUMAN_STATS_CMD: tuple[str, ...] = ("ccache", "-s")

CCACHE_DIRECT_HIT_KEY = "direct_cache_hit"
CCACHE_PREPROCESSED_HIT_KEY = "preprocessed_cache_hit"
CCACHE_MISS_KEY = "cache_miss"

CCACHE_STATUS_UNAVAILABLE = "unavailable"

# DEFAULT_PERF_MODULES is the single source of truth for which tests/perf/ modules a dispatch
# measures: extending this tuple is sufficient to carry a new module into every hosted
# dispatch, since .github/workflows/perf_harness.yml invokes this runner with no --modules flag.
DEFAULT_PERF_MODULES: tuple[str, ...] = (
    "tests/perf/test_variable_rate_perf.py",
    "tests/perf/test_fifo_perf.py",
    "tests/perf/test_stream_bridge_perf.py",
    "tests/perf/test_udp_packetizer_perf.py",
    "tests/perf/test_block_gil_contention_perf.py",
    "tests/perf/test_pool_alloc_perf.py",
    "tests/perf/test_batcher_combine_perf.py",
)


def run_stage(name: str, fn: Callable[[], Any]) -> Any:
    """Run fn(), returning its result on success.

    On any exception, returns a mapping recording the failure (status,
    exception class name, bounded message) instead of letting the exception
    escape, exactly matching scripts/probe_runner.py's run_stage() contract:
    a single stage's failure is contained, never allowed to abort the run.
    `name` is accepted for symmetry with the calling convention every stage
    is invoked through.
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


def _run_subprocess(
    argv: list[str], *, timeout: int = BUILD_SUBPROCESS_TIMEOUT_SECONDS,
) -> subprocess.CompletedProcess:
    """Injectable module-level default runner. Never raises: a missing
    binary or a timeout is captured as a nonzero-returncode result, matching
    every other never-raise subprocess helper in this phase.
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
    """Time the configure/compile/install commands, recording each elapsed
    figure separately plus the parallelism used and every exit code. A
    non-zero exit is recorded as a failure mapping, never raised: a run whose
    build failed still has a benchmarks block worth keeping (populated from
    whatever is already on disk).
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


def _parse_ccache_print_stats(text: str) -> dict[str, int]:
    """Parse ccache --print-stats' tab-separated key/value lines into
    integer counters. A line that is not a valid `key\\tvalue` integer pair
    is skipped rather than raising."""
    counters: dict[str, int] = {}
    for line in (text or "").splitlines():
        if "\t" not in line:
            continue
        key, _sep, value = line.partition("\t")
        key = key.strip()
        try:
            counters[key] = int(value.strip())
        except ValueError:
            continue
    return counters


def collect_ccache_stats(
    *, runner: Callable[..., subprocess.CompletedProcess] = _run_subprocess,
) -> dict[str, Any]:
    """Read ccache's own machine-readable counters and derive the hit rate
    from them, never from ccache -s's rounded human-readable text.

    Returns `status` `unavailable` with a reason when the ccache binary is
    absent or `--print-stats` is unsupported -- distinguishable from a
    genuine `hit_rate_percent` of `0.0` (every compilation missed) without
    inspecting the percentage, since the unavailable mapping carries no
    `hit_rate_percent` key at all.
    """
    version_completed = runner(list(CCACHE_VERSION_CMD))
    if version_completed.returncode != 0:
        return {
            "status": CCACHE_STATUS_UNAVAILABLE,
            "reason": "ccache binary not found or --version failed",
            "stderr_excerpt": _bounded_excerpt(version_completed.stderr),
        }
    version_lines = (version_completed.stdout or "").splitlines()
    version = version_lines[0].strip() if version_lines else ""

    stats_completed = runner(list(CCACHE_STATS_CMD))
    if stats_completed.returncode != 0:
        return {
            "status": CCACHE_STATUS_UNAVAILABLE,
            "reason": "ccache --print-stats unsupported or failed",
            "version": version,
            "stderr_excerpt": _bounded_excerpt(stats_completed.stderr),
        }

    counters = _parse_ccache_print_stats(stats_completed.stdout or "")
    hit_count = counters.get(CCACHE_DIRECT_HIT_KEY, 0) + counters.get(CCACHE_PREPROCESSED_HIT_KEY, 0)
    miss_count = counters.get(CCACHE_MISS_KEY, 0)
    total = hit_count + miss_count
    hit_rate_percent = (hit_count / total * 100.0) if total > 0 else 0.0

    # Captured verbatim for a human reader, alongside (never in place of) the derived figures.
    human_completed = runner(list(CCACHE_HUMAN_STATS_CMD))
    human_readable = human_completed.stdout if human_completed.returncode == 0 else ""

    return {
        "status": "ok",
        "version": version,
        "hit_count": hit_count,
        "miss_count": miss_count,
        "hit_rate_percent": hit_rate_percent,
        "counters": counters,
        "human_readable": human_readable,
    }


def collect_build_targets(
    *, runner: Callable[..., subprocess.CompletedProcess] = _run_subprocess,
) -> dict[str, Any]:
    """Capture the target list the `all` target expands to and the resolved
    `ROGUE_BUILD_TESTS` cache value, both read from the configured build tree
    at run time rather than from a reading of CMakeLists.txt. Must be called
    after a real build has completed (see CMAKE_BUILD_ALL_DRY_RUN_CMD's own
    comment): a dry run against a bare/unconfigured tree fails partway with a
    missing-prerequisite error rather than enumerating every target.
    """
    dry_run_completed = runner(list(CMAKE_BUILD_ALL_DRY_RUN_CMD))
    if dry_run_completed.returncode != 0:
        return {
            "status": "failed",
            "reason": "cmake --build build --target all -- -n failed (the tree may not be "
            "fully built yet)",
            "exit_code": dry_run_completed.returncode,
            "stderr_excerpt": _bounded_excerpt(dry_run_completed.stderr),
        }

    resolved_targets = sorted(set(_BUILT_TARGET_RE.findall(dry_run_completed.stdout or "")))

    cache_completed = runner(list(CMAKE_CACHE_VARIABLES_CMD))
    rogue_build_tests = env_fingerprint.UNAVAILABLE
    if cache_completed.returncode == 0:
        for line in (cache_completed.stdout or "").splitlines():
            if line.startswith("ROGUE_BUILD_TESTS:"):
                rogue_build_tests = line.partition("=")[2].strip()
                break

    return {
        "status": "ok",
        "resolved_targets": resolved_targets,
        "rogue_build_tests": rogue_build_tests,
    }


def _run_build_stage(
    *, runner: Callable[..., subprocess.CompletedProcess], parallelism: int | None,
) -> dict[str, Any]:
    """Bundle the build's three collectors into the one "build" stage:
    zero ccache's statistics before the build (best effort; ignored if
    ccache is absent, since collect_ccache_stats' own version check then
    reports the run as unavailable), time the build, then read the ccache
    counters and the resolved build targets from the now-configured tree.
    """
    runner(list(CCACHE_ZERO_STATS_CMD))
    timing = collect_build_timing(runner=runner, parallelism=parallelism)
    ccache = collect_ccache_stats(runner=runner)
    targets = collect_build_targets(runner=runner)
    return {"timing": timing, "ccache": ccache, "targets": targets}


ROGUE_SETUP_SCRIPT = "build/setup_rogue.sh"
_ROGUE_SETUP_ENV_KEYS: tuple[str, ...] = ("PYTHONPATH", "LD_LIBRARY_PATH", "DYLD_LIBRARY_PATH")


def _rogue_setup_env(runner: Callable[..., subprocess.CompletedProcess]) -> dict[str, str]:
    """Source build/setup_rogue.sh in a real shell and read back the handful
    of variables it exports, rather than re-deriving them from ROGUE_DIR by
    hand -- matching scripts/probe_runner.py's own helper (independently
    reimplemented here, not imported, per this module's no-coupling rule).
    The measurement subprocess needs these: this module's own process runs
    before the build stage installs Rogue, so the interpreter that invokes
    perf_harness_runner.py never itself imports rogue/pyrogue, only the
    pytest subprocess it launches does.

    Returns an empty mapping, never raising, when the script is absent or
    sourcing it fails -- the caller's subprocess invocation then simply
    inherits this process's own environment unchanged.
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


def _env_prefixed_argv(argv: list[str], env_vars: dict[str, str]) -> list[str]:
    return ["env", *[f"{key}={value}" for key, value in env_vars.items()], *argv]


def collect_measurement(
    *,
    runner: Callable[..., subprocess.CompletedProcess] = _run_subprocess,
    modules: tuple[str, ...] = DEFAULT_PERF_MODULES,
    extra_env: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Run the given tests/perf/ modules through pytest in one invocation,
    with `extra_env` (the freshly-built Rogue's PYTHONPATH/LD_LIBRARY_PATH,
    from `_rogue_setup_env`) prefixed onto the subprocess's environment so
    the pytest subprocess can import the library the build stage just
    installed. A non-zero exit is recorded as a failure mapping, never
    raised: the benchmarks aggregation step still reads whatever
    per-benchmark records were written to PERF_HARNESS_RESULTS_DIR before
    the failure."""
    argv = [sys.executable, "-m", "pytest", *modules, "-q", "-s"]
    if extra_env:
        argv = _env_prefixed_argv(argv, extra_env)
    completed = runner(argv, timeout=MEASUREMENT_SUBPROCESS_TIMEOUT_SECONDS)
    result: dict[str, Any] = {
        "status": "ok" if completed.returncode == 0 else "failed",
        "exit_code": completed.returncode,
        "modules": list(modules),
    }
    if completed.returncode != 0:
        result["stderr_excerpt"] = _bounded_excerpt(completed.stderr)
    return result


def collect_benchmarks(
    results_dir: Path | None,
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    """Read every JSON file in `results_dir` in sorted filename order,
    aggregating each file's `benchmarks` mapping by benchmark name, and
    lifting one `environment` mapping from the first record that carries
    one (every per-benchmark record from the same run shares the same
    runner fingerprint). A file that fails to parse or lacks a `benchmarks`
    mapping is recorded in the returned errors list with its filename and
    skipped, never aborting aggregation. Returns ({}, {}, []) when
    `results_dir` is None or does not exist.
    """
    benchmarks: dict[str, Any] = {}
    environment: dict[str, Any] = {}
    errors: list[dict[str, Any]] = []

    if results_dir is None or not results_dir.is_dir():
        return benchmarks, environment, errors

    for path in sorted(results_dir.glob("*.json")):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            errors.append({
                "file": path.name,
                "exception_class": type(exc).__name__,
                "message": str(exc)[:STAGE_ERROR_MESSAGE_MAX_CHARS],
            })
            continue

        if not isinstance(record, dict) or not isinstance(record.get("benchmarks"), dict):
            errors.append({
                "file": path.name,
                "exception_class": "ValueError",
                "message": "record missing a 'benchmarks' mapping",
            })
            continue

        for name, entry in record["benchmarks"].items():
            benchmarks[name] = entry

        if not environment and isinstance(record.get("environment"), dict):
            environment = record["environment"]

    return dict(sorted(benchmarks.items())), environment, errors


def _build_stage_fn(ctx: dict[str, Any]) -> Callable[[], Any]:
    args = ctx["args"]
    runner = ctx["runner"]
    return lambda: _run_build_stage(runner=runner, parallelism=args.parallelism)


def _measurement_stage_fn(ctx: dict[str, Any]) -> Callable[[], Any]:
    args = ctx["args"]
    runner = ctx["runner"]
    modules = tuple(m.strip() for m in args.modules.split(",") if m.strip()) or DEFAULT_PERF_MODULES

    def _fn() -> dict[str, Any]:
        extra_env = _rogue_setup_env(runner)
        return collect_measurement(runner=runner, modules=modules, extra_env=extra_env)

    return _fn


# STAGES is an ordered mapping from stage name to (record_key, factory), exactly matching
# scripts/probe_runner.py's own convention. Order matters: build runs before measurement so the
# measurement runs against an installed Rogue.
STAGES: dict[str, tuple[str, Callable[[dict[str, Any]], Callable[[], Any]]]] = {
    "build": ("build", _build_stage_fn),
    "measurement": ("measurement", _measurement_stage_fn),
}


def collect_stage_results(
    stage_names: list[str],
    args: argparse.Namespace,
    *,
    stages: dict[str, tuple[str, Callable[[dict[str, Any]], Callable[[], Any]]]] = STAGES,
    runner: Callable[..., subprocess.CompletedProcess] = _run_subprocess,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Run every stage named in `stage_names`, in `stages`' own order,
    through run_stage(). Returns (results_by_record_key, errors). A stage
    that raises never prevents a later stage from running: run_stage
    contains the exception into a failure mapping, and this function appends
    one entry to `errors` for it, then continues to the next selected stage.
    """
    results: dict[str, Any] = {}
    errors: list[dict[str, Any]] = []
    ctx: dict[str, Any] = {"args": args, "runner": runner, "record": results}

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

    return results, errors


def _git_tree_hash(runner: Callable[..., subprocess.CompletedProcess] = _run_subprocess) -> str:
    completed = runner(["git", "rev-parse", "HEAD^{tree}"])
    if completed.returncode != 0:
        return env_fingerprint.UNAVAILABLE
    value = (completed.stdout or "").strip()
    return value if value else env_fingerprint.UNAVAILABLE


def build_run_record(
    *,
    git_tree_hash: str,
    git_tree_hash_source: str,
    environment: dict[str, Any],
    build: dict[str, Any],
    benchmarks: dict[str, Any],
    stages: dict[str, Any],
    errors: list[dict[str, Any]],
) -> dict[str, Any]:
    """Assemble the fixed seven-key run-record shape: harness_run_schema_version, run,
    environment, build, benchmarks, stages, errors. `run`'s fields are read from the same
    environment variables tests/perf/_perf_harness.py's own per-benchmark records read, so the
    two record shapes describe the same run under the same field names.
    """
    run = {
        "github_run_id": os.environ.get("GITHUB_RUN_ID", env_fingerprint.UNAVAILABLE),
        "github_run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT", env_fingerprint.UNAVAILABLE),
        "git_sha": os.environ.get("GITHUB_SHA", env_fingerprint.UNAVAILABLE),
        "git_tree_hash": git_tree_hash,
        "git_tree_hash_source": git_tree_hash_source,
        "campaign_branch": os.environ.get("HARNESS_CAMPAIGN_BRANCH", env_fingerprint.UNAVAILABLE),
        "dispatch_index": os.environ.get("HARNESS_DISPATCH_INDEX", env_fingerprint.UNAVAILABLE),
        "injected_load": os.environ.get("HARNESS_INJECTED_LOAD", env_fingerprint.UNAVAILABLE),
    }
    return {
        "harness_run_schema_version": HARNESS_RUN_SCHEMA_VERSION,
        "run": run,
        "environment": environment,
        "build": build,
        "benchmarks": benchmarks,
        "stages": stages,
        "errors": errors,
    }


def format_ccache_summary_markdown(ccache_stats: dict[str, Any]) -> str:
    """Render collect_ccache_stats()' output as a small markdown block for
    GITHUB_STEP_SUMMARY, reused by both perf_harness.yml and rogue_ci.yml so
    there is exactly one implementation of the hit-rate presentation."""
    if ccache_stats.get("status") != "ok":
        return f"ccache statistics unavailable: {ccache_stats.get('reason', 'unknown reason')}\n"
    lines = [
        "| Metric | Value |",
        "| --- | --- |",
        f"| ccache version | {ccache_stats.get('version', '')} |",
        f"| Hit rate | {ccache_stats['hit_rate_percent']:.2f}% |",
        f"| Hits | {ccache_stats['hit_count']} |",
        f"| Misses | {ccache_stats['miss_count']} |",
    ]
    return "\n".join(lines) + "\n"


def format_build_targets_summary_markdown(build_targets: dict[str, Any]) -> str:
    """Render collect_build_targets()' output as a small markdown block for
    GITHUB_STEP_SUMMARY, so the resolved-build-target evidence (the resolved
    target set and the resolved ROGUE_BUILD_TESTS cache value) is visible on
    the CI run and not only in a committed campaign record."""
    if build_targets.get("status") != "ok":
        return f"build targets unavailable: {build_targets.get('reason', 'unknown reason')}\n"
    return (
        f"- ROGUE_BUILD_TESTS: `{build_targets['rogue_build_tests']}`\n"
        f"- Resolved targets: `{', '.join(build_targets['resolved_targets'])}`\n"
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=None,
        help="Output path for the aggregated run-record JSON (required unless "
        "--print-ccache-summary is given)",
    )
    parser.add_argument(
        "--stages",
        default=",".join(STAGES),
        help=f"Comma-separated stage list to run (default: all of {', '.join(STAGES)})",
    )
    parser.add_argument(
        "--results-dir",
        default=None,
        help=f"Override for the {HARNESS_RESULTS_DIR_ENV} environment variable, primarily for testing",
    )
    parser.add_argument(
        "--modules",
        default=",".join(DEFAULT_PERF_MODULES),
        help="Comma-separated tests/perf module paths to run through pytest",
    )
    parser.add_argument(
        "--parallelism",
        type=int,
        default=None,
        help="Override for the compile step's -j value (default: os.cpu_count())",
    )
    parser.add_argument(
        "--tree-hash",
        default=None,
        help="Override for git rev-parse HEAD^{tree}, primarily for testing",
    )
    parser.add_argument(
        "--print-ccache-summary",
        action="store_true",
        help="Print a markdown ccache statistics summary to stdout and exit, without running "
        "the build or measurement stages",
    )
    parser.add_argument(
        "--print-build-targets-summary",
        action="store_true",
        help="Print a markdown build-targets summary (the resolved-build-target evidence) to "
        "stdout and exit, without running the build or measurement stages",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if args.print_ccache_summary:
        print(format_ccache_summary_markdown(collect_ccache_stats()))
        return 0

    if args.print_build_targets_summary:
        print(format_build_targets_summary_markdown(collect_build_targets()))
        return 0

    if not args.out:
        print("error: --out is required unless --print-ccache-summary is given", file=sys.stderr)
        return 2

    requested_stages = [stage.strip() for stage in args.stages.split(",") if stage.strip()]
    unknown_stages = [name for name in requested_stages if name not in STAGES]
    if unknown_stages:
        valid = ", ".join(sorted(STAGES))
        print(
            f"error: unknown stage(s): {', '.join(unknown_stages)}; valid stages: {valid}",
            file=sys.stderr,
        )
        return 2

    stage_results, errors = collect_stage_results(requested_stages, args)

    results_dir_value = args.results_dir or os.environ.get(HARNESS_RESULTS_DIR_ENV)
    results_dir = Path(results_dir_value) if results_dir_value else None
    benchmarks, environment, benchmark_errors = collect_benchmarks(results_dir)
    errors = errors + benchmark_errors

    if args.tree_hash:
        tree_hash = args.tree_hash
        tree_hash_source = "explicit"
    else:
        tree_hash = _git_tree_hash()
        tree_hash_source = "git_rev_parse" if tree_hash != env_fingerprint.UNAVAILABLE else "unavailable"

    record = build_run_record(
        git_tree_hash=tree_hash,
        git_tree_hash_source=tree_hash_source,
        environment=environment,
        build=stage_results.get("build", {}),
        benchmarks=benchmarks,
        stages=stage_results,
        errors=errors,
    )

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
