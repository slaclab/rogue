#!/usr/bin/env python3
# ----------------------------------------------------------------------------
# Title      : ROGUE Perf Gate A/B Runner
# ----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
# ----------------------------------------------------------------------------

"""Paired same-job A/B measurement mechanism: one job, two source trees.

Materializes the candidate and the merge-base ref as two `git worktree`
checkouts sharing the job checkout's own object store, builds and measures
both through one measurement implementation (`scripts/perf_harness_runner.py`,
invoked with `cwd` set to whichever leg is being measured), alternates
measurement rounds between the two legs, and emits one record carrying both
legs plus the run's own per-stage measured wall clock.

Both legs are worktrees, never the job's own checkout, so the two legs are
symmetric by construction: a difference between them can never come from one
side being the checkout and the other not. One measurement implementation is
reused for both legs (rather than each leg carrying its own copy) so an
unrelated-commit run cannot silently measure two different harness
implementations. scripts/perf_gate_evaluator.py reads the two-leg record this
module produces.
"""

from __future__ import annotations

import argparse
import hashlib
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
import perf_gate_evaluator  # noqa: E402  (flat sibling import, path inserted above)
import perf_gate_hang_diagnostics  # noqa: E402  (flat sibling import, path inserted above)
import perf_harness_runner  # noqa: E402  (flat sibling import, path inserted above)
import perf_tier_registry  # noqa: E402  (flat sibling import, path inserted above)

TESTS_PERF_DIR = SCRIPTS_DIR.parent / "tests" / "perf"
if str(TESTS_PERF_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_PERF_DIR))

# Imported by bare module name (never `tests.perf._perf_harness`), matching
# scripts/perf_gate_evaluator.py's own import so this module stays runnable on a machine
# where a stray top-level `tests` package shadows this repository's own `tests/` namespace
# package.
import _perf_harness  # noqa: E402  (flat sibling import, path inserted above)


GATE_AB_SCHEMA_VERSION = 1

LEG_CANDIDATE = "candidate"
LEG_MERGE_BASE = "merge_base"

MODE_NULL = "null"
MODE_UNRELATED = "unrelated"
MODE_SEEDED = "seeded-regression"
MODE_FORCED_INCONCLUSIVE = "forced-inconclusive"
VALID_MODES: tuple[str, ...] = (MODE_NULL, MODE_UNRELATED, MODE_SEEDED, MODE_FORCED_INCONCLUSIVE)

DEFAULT_PATCH_DIR = "docs/plans/perf-ci-hardening/seeded-regressions"

# Read once by a patched src/rogue call site through a function-local static, so a
# magnitude sweep needs one committed patch per regression rather than one per magnitude:
# the patch's own code reads this variable at measurement time. This module only forwards
# the CLI value into the candidate leg's measurement subprocess environment and records it
# on the run for provenance; it never interprets the value itself.
PATCH_MAGNITUDE_ENV = "ROGUE_SEEDED_REGRESSION_STRIDE"

# DEFAULT_ROUNDS = 2: measured at about 80 seconds for one full pass over every module on
# one leg, so two rounds per leg is roughly 320 seconds of measurement -- affordable inside
# the 600 second budget alongside two builds, and two is the smallest round count for which
# the word "interleaved" means anything at all (one round per leg cannot alternate). The
# runner measures and reports the real per-run figure rather than relying on this
# projection.
DEFAULT_ROUNDS = 2

# Declared once, in this fixed order, so a stage's position in the record never depends on
# which stages happened to run or how long they took: two stages with an equal measured
# duration keep this declared order rather than an incidental one.
TIMING_STAGE_ORDER: tuple[str, ...] = (
    "worktree_candidate",
    "worktree_merge_base",
    "patch_candidate",
    "build_candidate",
    "build_merge_base",
    "measure_candidate",
    "measure_merge_base",
    "total",
)

WORKTREE_SUBPROCESS_TIMEOUT_SECONDS = 120

# GATE_RUNNER_DEADLINE_SECONDS = 1260: the paired-run step's own 1500 second bound
# (.github/workflows/perf_gate_validation.yml "Run paired A/B measurement" timeout-minutes: 25)
# minus 240 seconds of slack for the record write and both worktree removals. The
# population's worst observed whole-step figure is 682.07 seconds, so this bound sits well
# clear of a real cold-cache run.
GATE_RUNNER_DEADLINE_SECONDS = 1260

# Seconds before a bounded call's own expiry at which the hang-diagnostics snapshot
# fires, chosen so parked threads are captured while the subprocess is still alive
# rather than after it has already been killed.
HANG_DIAGNOSTICS_LEAD_SECONDS = 60

# GATE_ROUND_SHARE_FLOOR_SECONDS = 180: twice the measured per-round-per-leg median of
# 85.08 seconds, rounded up to the next whole minute. Worst case check against a real run:
# 1260 seconds minus the 311.12 second cold-cache combined build leaves 948.88 seconds,
# which is 237.22 seconds for each of four units at two rounds per leg, clearing this floor
# with 57 seconds of margin.
GATE_ROUND_SHARE_FLOOR_SECONDS = 180

# HANG_DIAGNOSTICS_MIN_LEAD_FRACTION = 0.5: exists so a snapshot is never armed at zero
# seconds, which fires it the instant the subprocess starts and captures nothing useful.
HANG_DIAGNOSTICS_MIN_LEAD_FRACTION = 0.5

# Named reasons a measurement round or a build subprocess call can be recorded against
# when this runner's own deadline -- not the stage's own timeout -- is what bounded or
# skipped it. Both must read as measurement failures, never as clean results.
REASON_DEADLINE_BOUNDED_SUBPROCESS = "measurement subprocess bounded by the gate runner deadline"
REASON_DEADLINE_ALREADY_PASSED = "gate runner deadline already passed before this stage could start"

# A third named reason, distinct from both of the above, recorded when a round's own
# partitioned share of the remaining deadline falls below the usable floor: the round is
# skipped outright rather than started with a share it cannot use.
REASON_DEADLINE_SHARE_BELOW_FLOOR = (
    "measurement round's partitioned deadline share fell below the usable floor"
)

# A full 40-character lowercase hex git sha, rejected before it can reach any subprocess
# argument list: a workflow_dispatch string input is tampering surface, and a
# malformed ref must never be threaded into a `git` argv.
SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")

# A --modules element, anchored at both ends so no path separator, parent-directory
# component, leading dash, absolute path, or shell metacharacter can reach the pytest argv
# collect_measurement builds: only a literal tests/perf/ prefix, a test_ filename of
# lowercase letters, digits, and underscores, and the .py suffix is accepted.
PERF_MODULE_PATTERN = re.compile(r"^tests/perf/test_[a-z0-9_]+\.py$")

# The three evaluator-enumerated INCONCLUSIVE conditions this runner can induce without
# touching library source. Each string is kept equal to
# scripts/perf_gate_evaluator.py's own REASON_* value by convention, not by import. This
# module now does import perf_gate_evaluator (above): the single in-job retry decision below
# calls evaluate_run on the first attempt's own record to find a retry-eligible gating cell,
# reusing the shipped roll-up rather than reimplementing per-cell comparison a second time --
# a second implementation of the gating comparison is exactly how a validated contract
# silently diverges. These three forced-condition strings stay plain literals rather than
# switching to the evaluator's own REASON_* constants: that substitution is a separate change
# with its own blast radius and is not part of this plan.
FORCED_MERGE_BASE_BUILD_FAILED = "merge-base-build-failed"
FORCED_METRIC_ABSENT_FROM_LEG = "metric-absent-from-leg"
FORCED_TREE_HASH_PAIR_MISMATCH = "tree-hash-pair-mismatch"
FORCED_CONDITIONS: tuple[str, ...] = (
    FORCED_MERGE_BASE_BUILD_FAILED,
    FORCED_METRIC_ABSENT_FROM_LEG,
    FORCED_TREE_HASH_PAIR_MISMATCH,
)

# A tree hash that is syntactically valid but can never equal a real merge-base leg's
# measured tree hash, used only to induce FORCED_TREE_HASH_PAIR_MISMATCH deliberately.
_BOGUS_TREE_HASH = "0" * 40


class ModuleBenchmarkMapError(Exception):
    """Raised at import time when MODULE_BENCHMARKS's key set is not a subset of
    perf_harness_runner.DEFAULT_PERF_MODULES, or when the union of its values is not exactly
    perf_tier_registry.ALL_BENCHMARKS: a future benchmark added to the registry without a
    module entry here must fail loudly rather than silently become un-retryable."""


# Maps each default tests/perf/ module path to the benchmark identities that module emits,
# so the in-job retry can narrow its own re-measurement to only the modules that produced an
# affected benchmark. The variable-rate and gil modules draw their tuples directly from
# perf_tier_registry rather than retyping them; the stream and coverage modules are
# enumerated explicitly because their six and two identities do not map one-to-one onto
# module stems: test_udp_packetizer_perf.py alone emits all four udp identities, and no
# derivable naming rule connects test_block_gil_contention_perf.py's stem to its single drain
# identity.
MODULE_BENCHMARKS: dict[str, tuple[str, ...]] = {
    "tests/perf/test_variable_rate_perf.py": perf_tier_registry.TRANSACTION_BENCHMARKS,
    "tests/perf/test_fifo_perf.py": ("fifo_perf",),
    "tests/perf/test_stream_bridge_perf.py": ("stream_bridge_perf",),
    "tests/perf/test_udp_packetizer_perf.py": (
        "udp_packetizer_perf_v1_jumbo",
        "udp_packetizer_perf_v1_std",
        "udp_packetizer_perf_v2_jumbo",
        "udp_packetizer_perf_v2_std",
    ),
    "tests/perf/test_block_gil_contention_perf.py": perf_tier_registry.GIL_BENCHMARKS,
    "tests/perf/test_pool_alloc_perf.py": ("pool_alloc_perf",),
    "tests/perf/test_batcher_combine_perf.py": ("batcher_combine_perf",),
}


def _validate_module_benchmarks(mapping: dict[str, tuple[str, ...]]) -> None:
    """The two invariants MODULE_BENCHMARKS must hold, factored into a standalone function
    (rather than checked inline at import time only) so a test can exercise a deliberately
    incomplete map by monkeypatching MODULE_BENCHMARKS and re-calling this function, without
    re-importing the module."""
    keys = set(mapping)
    unknown_keys = keys - set(perf_harness_runner.DEFAULT_PERF_MODULES)
    if unknown_keys:
        raise ModuleBenchmarkMapError(
            f"MODULE_BENCHMARKS has keys outside DEFAULT_PERF_MODULES: {sorted(unknown_keys)}"
        )
    union: set[str] = set()
    for benchmarks in mapping.values():
        union.update(benchmarks)
    all_benchmarks = set(perf_tier_registry.ALL_BENCHMARKS)
    if union != all_benchmarks:
        raise ModuleBenchmarkMapError(
            "MODULE_BENCHMARKS' benchmark union does not equal perf_tier_registry.ALL_BENCHMARKS: "
            f"missing={sorted(all_benchmarks - union)}, extra={sorted(union - all_benchmarks)}"
        )


_validate_module_benchmarks(MODULE_BENCHMARKS)


def modules_for_benchmarks(names: tuple[str, ...] | list[str] | set[str]) -> tuple[str, ...]:
    """The module paths, in perf_harness_runner.DEFAULT_PERF_MODULES order and
    de-duplicated, that emit any benchmark identity in `names`. Returns an empty tuple for an
    empty input. A benchmark identity MODULE_BENCHMARKS does not know is skipped rather than
    raising: an unknown identity must not abort a run that already has a record to write."""
    wanted = set(names)
    if not wanted:
        return ()
    return tuple(
        module for module in perf_harness_runner.DEFAULT_PERF_MODULES
        if wanted & set(MODULE_BENCHMARKS.get(module, ()))
    )

# Set per leg to that leg's own worktree root (build_leg below) so ccache rewrites any
# absolute path under it -- the compiler's own working directory and every source/-I path
# CMake resolves against the worktree root -- to the same relative form on both legs before
# hashing. Without this, two otherwise-identical compiles (a null run's two legs) hash to
# different keys purely because they live at different absolute worktree paths, which is
# exactly what a real hosted null run measured: 0% ccache hit rate on both legs despite
# sharing one cache directory and one key.
CCACHE_BASEDIR_ENV = "CCACHE_BASEDIR"


def _run_subprocess(
    argv: list[str],
    *,
    timeout: int = WORKTREE_SUBPROCESS_TIMEOUT_SECONDS,
    cwd: str | None = None,
) -> subprocess.CompletedProcess:
    """Injectable module-level default runner. Never raises: a missing binary or a
    timeout comes back as a non-zero-returncode CompletedProcess, matching
    perf_harness_runner._run_subprocess exactly, with an added `cwd` parameter since every
    subprocess call in this module must run inside a leg's own worktree (or the job
    checkout, for the `git worktree` commands themselves)."""
    try:
        return subprocess.run(argv, capture_output=True, text=True, timeout=timeout, cwd=cwd)
    except (OSError, subprocess.SubprocessError) as exc:
        return subprocess.CompletedProcess(argv, returncode=1, stdout="", stderr=str(exc))


def _sha256_of(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _is_failed(result: Any) -> bool:
    return isinstance(result, dict) and result.get("status") == "failed"


def _stage_error(name: str, result: dict[str, Any]) -> dict[str, Any]:
    message = result.get("message") or result.get("stderr_excerpt") or result.get("reason") or "stage failed"
    return {
        "stage": name,
        "exception_class": result.get("exception_class", "StageFailure"),
        "message": message,
    }


def _unavailable_timing(reason: str) -> dict[str, Any]:
    return {"value": env_fingerprint.UNAVAILABLE, "reason": reason}


def add_worktree(
    repo_root: str,
    path: str,
    sha: str,
    runner: Callable[..., subprocess.CompletedProcess] = _run_subprocess,
) -> dict[str, Any]:
    """`git worktree add --detach <path> <sha>`, run with `cwd` set to `repo_root` (the
    job's own checkout). Never raises: a failure is recorded as a failure mapping with a
    bounded stderr excerpt, matching perf_harness_runner's own never-raise convention."""
    completed = runner(
        ["git", "worktree", "add", "--detach", str(path), sha],
        cwd=repo_root, timeout=WORKTREE_SUBPROCESS_TIMEOUT_SECONDS,
    )
    if completed.returncode != 0:
        return {
            "status": "failed",
            "path": str(path),
            "sha": sha,
            "stderr_excerpt": perf_harness_runner._bounded_excerpt(completed.stderr),
        }
    return {"status": "ok", "path": str(path), "sha": sha}


def remove_worktree(
    repo_root: str,
    path: str,
    runner: Callable[..., subprocess.CompletedProcess] = _run_subprocess,
) -> dict[str, Any]:
    """`git worktree remove --force <path>`, safe to call for a path that was never
    added (git reports a failure, which this function records rather than raising)."""
    completed = runner(
        ["git", "worktree", "remove", "--force", str(path)],
        cwd=repo_root, timeout=WORKTREE_SUBPROCESS_TIMEOUT_SECONDS,
    )
    if completed.returncode != 0:
        return {
            "status": "failed",
            "path": str(path),
            "stderr_excerpt": perf_harness_runner._bounded_excerpt(completed.stderr),
        }
    return {"status": "ok", "path": str(path)}


def apply_patch(
    worktree: str,
    patch_path: str,
    patch_magnitude: str | None = None,
    runner: Callable[..., subprocess.CompletedProcess] = _run_subprocess,
) -> dict[str, Any]:
    """`git apply --check` then `git apply`, run inside `worktree` only (the candidate
    leg, never the merge-base leg or the job checkout). `patch_magnitude` is recorded here
    for provenance only -- it plays no part in applying the patch itself, since the patch's
    own code reads PATCH_MAGNITUDE_ENV at measurement time. Never raises: a patch that
    fails `--check` is recorded as a failed patch stage, and `git apply` is never invoked
    against a tree `--check` already rejected."""
    patch_path = str(patch_path)
    patch_sha256 = _sha256_of(patch_path)

    check_completed = runner(
        ["git", "apply", "--check", patch_path],
        cwd=worktree, timeout=WORKTREE_SUBPROCESS_TIMEOUT_SECONDS,
    )
    if check_completed.returncode != 0:
        return {
            "status": "failed",
            "patch_path": patch_path,
            "patch_sha256": patch_sha256,
            "patch_magnitude": patch_magnitude,
            "stderr_excerpt": perf_harness_runner._bounded_excerpt(check_completed.stderr),
        }

    apply_completed = runner(
        ["git", "apply", patch_path],
        cwd=worktree, timeout=WORKTREE_SUBPROCESS_TIMEOUT_SECONDS,
    )
    if apply_completed.returncode != 0:
        return {
            "status": "failed",
            "patch_path": patch_path,
            "patch_sha256": patch_sha256,
            "patch_magnitude": patch_magnitude,
            "stderr_excerpt": perf_harness_runner._bounded_excerpt(apply_completed.stderr),
        }

    return {
        "status": "ok",
        "patch_path": patch_path,
        "patch_sha256": patch_sha256,
        "patch_magnitude": patch_magnitude,
    }


def tree_hash_of(
    worktree: str, runner: Callable[..., subprocess.CompletedProcess] = _run_subprocess,
) -> str:
    """`git rev-parse HEAD^{tree}` with `cwd` set to `worktree`. Returns the unavailable
    sentinel rather than raising."""
    completed = runner(
        ["git", "rev-parse", "HEAD^{tree}"], cwd=worktree, timeout=WORKTREE_SUBPROCESS_TIMEOUT_SECONDS,
    )
    if completed.returncode != 0:
        return env_fingerprint.UNAVAILABLE
    value = (completed.stdout or "").strip()
    return value if value else env_fingerprint.UNAVAILABLE


def head_sha_of(
    worktree: str, runner: Callable[..., subprocess.CompletedProcess] = _run_subprocess,
) -> str:
    """`git rev-parse HEAD` with `cwd` set to `worktree`. Returns the unavailable
    sentinel rather than raising."""
    completed = runner(
        ["git", "rev-parse", "HEAD"], cwd=worktree, timeout=WORKTREE_SUBPROCESS_TIMEOUT_SECONDS,
    )
    if completed.returncode != 0:
        return env_fingerprint.UNAVAILABLE
    value = (completed.stdout or "").strip()
    return value if value else env_fingerprint.UNAVAILABLE


def _clamped_timeout(
    stage_timeout: int, deadline_monotonic: float | None, clock: Callable[[], float] = time.monotonic,
) -> int | None:
    """The smaller of `stage_timeout` and the seconds remaining until
    `deadline_monotonic`, as an int. `deadline_monotonic is None` disables clamping
    entirely (today's behaviour): `stage_timeout` is returned unchanged. Returns `None`
    once the deadline has already passed, so the caller knows to skip the call rather
    than start it with a nonsensical or negative timeout."""
    if deadline_monotonic is None:
        return stage_timeout
    remaining = deadline_monotonic - clock()
    if remaining <= 0:
        return None
    return min(stage_timeout, int(remaining))


def _partitioned_timeout(
    stage_timeout: int,
    deadline_monotonic: float | None,
    remaining_units: int,
    *,
    floor_seconds: int = GATE_ROUND_SHARE_FLOOR_SECONDS,
    clock: Callable[[], float] = time.monotonic,
) -> tuple[int | None, str | None]:
    """One measurement round's own partitioned share of the remaining gate-runner
    deadline: a two-tuple of an optional int timeout and an optional named reason.

    `deadline_monotonic is None` disables partitioning entirely (today's unclamped path):
    `stage_timeout` is returned unchanged with no reason. A remaining time at or below zero
    returns no timeout with `REASON_DEADLINE_ALREADY_PASSED`, checked ahead of the floor so
    an already-expired deadline is never misreported as a floor skip. `remaining_units` is
    coerced with a lower bound of one so a zero or negative count can never divide. The
    share is the remaining seconds divided by the (coerced) unit count; a positive
    `floor_seconds` that strictly exceeds the share returns no timeout with
    `REASON_DEADLINE_SHARE_BELOW_FLOOR`, so a share exactly equal to the floor is runnable
    and a `floor_seconds` of 0 never skips. Otherwise the returned timeout is the smaller of
    `stage_timeout` and the share truncated toward zero with `int()`: rounding up would let
    the shares handed to the remaining units sum above the remaining budget."""
    if deadline_monotonic is None:
        return stage_timeout, None
    remaining = deadline_monotonic - clock()
    if remaining <= 0:
        return None, REASON_DEADLINE_ALREADY_PASSED
    units = max(remaining_units, 1)
    share = remaining / units
    if floor_seconds > 0 and floor_seconds > share:
        return None, REASON_DEADLINE_SHARE_BELOW_FLOOR
    return min(stage_timeout, int(share)), None


def _diagnostics_arm_lead(timeout: float, lead_seconds: float) -> float:
    """The hang-diagnostics timer's own lead time for a bounded measurement call of
    `timeout` seconds: `timeout - lead_seconds` when that difference is positive -- the
    previous unconditional expression, which collapsed to zero (or below) under a
    near-zero partitioned share, arming the snapshot the instant the measurement
    subprocess started and capturing nothing but the harness process itself, exactly what
    made three starved hosted records' snapshots unusable. Otherwise
    `HANG_DIAGNOSTICS_MIN_LEAD_FRACTION` of `timeout`, with a lower bound of 1.0 second, so
    the lead is strictly positive for any positive timeout. A `timeout` of zero or less
    returns 0.0, and the caller then arms nothing."""
    if timeout <= 0:
        return 0.0
    candidate = timeout - lead_seconds
    if candidate > 0:
        return candidate
    return max(timeout * HANG_DIAGNOSTICS_MIN_LEAD_FRACTION, 1.0)


def _cwd_bound_runner(
    worktree: str,
    runner: Callable[..., subprocess.CompletedProcess],
    env_vars: dict[str, str] | None = None,
    *,
    deadline_monotonic: float | None = None,
    clock: Callable[[], float] = time.monotonic,
) -> Callable[..., subprocess.CompletedProcess]:
    """Wrap this module's own (argv, timeout, cwd) runner signature into
    perf_harness_runner's own (argv, timeout) calling convention, bound to `worktree`, so
    perf_harness_runner's existing build/ccache/target collectors can be reused unmodified
    for one leg with zero change to that module. When `env_vars` is given, every argv this
    bound runner is asked to run is prefixed with `env KEY=VALUE ...` first, reusing
    perf_harness_runner._env_prefixed_argv's own idiom (already used by measure_leg_round
    below) rather than adding a second way to thread environment into a subprocess call.

    Every call this wrapper makes is clamped against `deadline_monotonic` through
    `_clamped_timeout` before it reaches `runner`. When nothing remains, no subprocess is
    started at all: a synthetic nonzero-returncode `CompletedProcess` carrying
    `REASON_DEADLINE_ALREADY_PASSED` is returned instead, which
    perf_harness_runner's own build-stage collectors already treat as a failed step."""
    def _bound(argv: list[str], timeout: int = perf_harness_runner.BUILD_SUBPROCESS_TIMEOUT_SECONDS):
        bound_argv = perf_harness_runner._env_prefixed_argv(list(argv), env_vars) if env_vars else argv
        clamped = _clamped_timeout(timeout, deadline_monotonic, clock)
        if clamped is None:
            return subprocess.CompletedProcess(
                bound_argv, returncode=1, stdout="", stderr=REASON_DEADLINE_ALREADY_PASSED,
            )
        return runner(bound_argv, timeout=clamped, cwd=worktree)
    return _bound


def build_leg(
    leg: str,
    worktree: str,
    runner: Callable[..., subprocess.CompletedProcess] = _run_subprocess,
    *,
    deadline_monotonic: float | None = None,
    clock: Callable[[], float] = time.monotonic,
    diagnostics_dir: str | None = None,
    diagnostics_lead_seconds: int = HANG_DIAGNOSTICS_LEAD_SECONDS,
) -> dict[str, Any]:
    """Configure, compile, install, ccache statistics, and resolved build targets for one
    leg, delegating entirely to perf_harness_runner's own collectors with `cwd` bound to
    `worktree` -- no build logic is reimplemented here, matching
    perf_harness_runner._run_build_stage's own zero-stats/timing/ccache/targets order.

    CCACHE_BASEDIR is set to this leg's own `worktree` for every subprocess run here. A real
    hosted null run's compile command line (captured with `VERBOSE=1` against this
    repository's own CMakeLists.txt) showed both the `-c` source argument and every `-I`
    include path as absolute paths anchored at the worktree root, and the compiler's own
    working directory (`<worktree>/build`) is itself under that root -- so two legs compiling
    byte-identical source from two different worktree roots hash to two different keys with
    no CCACHE_BASEDIR set. Setting it here makes ccache rewrite all of those paths, including
    the working directory, to the same relative form on both legs before hashing.
    CCACHE_NOHASHDIR is deliberately not set: ccache's own documented base_dir behavior
    already relativizes the working directory once it is under base_dir (true here, since the
    build directory is always a direct `build` subdirectory of the worktree root on both
    legs), and this build's CMakeLists.txt defaults to a Release configuration with no `-g`,
    so there is no separate debug-info path left for hash_dir to affect.

    `deadline_monotonic` and `clock` are threaded through to `_cwd_bound_runner`, which
    clamps every subprocess call this function makes; `deadline_monotonic=None` (the
    default) reproduces today's unclamped behaviour exactly. `diagnostics_dir` and
    `diagnostics_lead_seconds` are accepted for signature symmetry with
    `measure_leg_round` but are not used here: the build stage's several short configure/
    compile/install calls have no single blocking point worth arming a snapshot against,
    unlike the one long-running measurement subprocess call below."""
    del diagnostics_dir, diagnostics_lead_seconds  # signature symmetry only, see docstring
    bound_runner = _cwd_bound_runner(
        worktree, runner, env_vars={CCACHE_BASEDIR_ENV: str(worktree)},
        deadline_monotonic=deadline_monotonic, clock=clock,
    )
    bound_runner(list(perf_harness_runner.CCACHE_ZERO_STATS_CMD))
    timing = perf_harness_runner.collect_build_timing(runner=bound_runner)
    ccache = perf_harness_runner.collect_ccache_stats(runner=bound_runner)
    targets = perf_harness_runner.collect_build_targets(runner=bound_runner)
    return {
        "leg": leg,
        "success": timing.get("status") == "ok",
        "timing": timing,
        "ccache": ccache,
        "targets": targets,
    }


def measure_leg_round(
    leg_worktree: str,
    results_dir: str,
    runner: Callable[..., subprocess.CompletedProcess] = _run_subprocess,
    *,
    checkout_root: str = ".",
    modules: tuple[str, ...] = perf_harness_runner.DEFAULT_PERF_MODULES,
    extra_env: dict[str, str] | None = None,
    deadline_monotonic: float | None = None,
    clock: Callable[[], float] = time.monotonic,
    diagnostics_dir: str | None = None,
    diagnostics_lead_seconds: int = HANG_DIAGNOSTICS_LEAD_SECONDS,
    remaining_units: int = 1,
    share_floor_seconds: int = GATE_ROUND_SHARE_FLOOR_SECONDS,
) -> dict[str, Any]:
    """Invoke the job checkout's own scripts/perf_harness_runner.py once, running only its
    "measurement" stage (the build already happened separately via build_leg), with `cwd`
    set to `leg_worktree` -- so the harness runner's own cwd-relative
    PYTHONPATH/setup_rogue.sh sourcing retargets at this leg with zero change to that
    module -- and PERF_HARNESS_RESULTS_DIR / PERF_RESULTS_DIR (plus any `extra_env`, such as
    PATCH_MAGNITUDE_ENV for a patched candidate round) threaded in through an env-prefixed
    argv, matching perf_harness_runner._env_prefixed_argv's own idiom. Returns the parsed
    run record on success, or a failure mapping -- never raising -- when the subprocess
    exits non-zero or writes no record.

    PYTHONFAULTHANDLER=1 is exported into the subprocess environment unconditionally.
    Installing CPython's own fault handler cannot change a measured value: it only
    installs signal handlers and reads no counter. It is what makes
    perf_gate_hang_diagnostics.signal_python_descendants' SIGABRT dump every thread's own
    Python-level traceback to this subprocess's stderr, which this function already
    captures, instead of the uncatchable, silent kill a bare subprocess timeout issues.

    `deadline_monotonic` and `clock` bound this call's own timeout through
    `_partitioned_timeout`, to `remaining_units`' own share of what remains rather than the
    whole remaining budget; `remaining_units` of 1 (the default) reproduces the
    whole-remaining-budget behaviour the previous plan shipped, and `deadline_monotonic` of
    `None` still reproduces today's unclamped behaviour exactly. When the deadline has
    already passed, or when this round's own partitioned share falls below
    `share_floor_seconds`, this function records a named failure -- carrying only `status`
    and `reason` -- and never starts the subprocess at all. When `diagnostics_dir` is
    given, a per-thread snapshot is armed against this process's own pid before the call
    (skipped when the computed arm lead is not positive) and disarmed in a `finally` once
    it returns; on a nonzero return the snapshot path and the full (untruncated) captured
    stderr -- written to a sibling path -- are both recorded on the failure mapping,
    alongside the existing `stderr_excerpt` field, which is left exactly as it was."""
    out_path = Path(results_dir) / "run-record.json"
    runner_script = str(Path(checkout_root).resolve() / "scripts" / "perf_harness_runner.py")
    argv = [
        sys.executable, runner_script,
        "--out", str(out_path),
        "--stages", "measurement",
        "--modules", ",".join(modules),
    ]
    env_vars = {
        perf_harness_runner.HARNESS_RESULTS_DIR_ENV: str(results_dir),
        "PERF_RESULTS_DIR": str(results_dir),
        "PYTHONFAULTHANDLER": "1",
    }
    if extra_env:
        env_vars.update(extra_env)
    argv = perf_harness_runner._env_prefixed_argv(argv, env_vars)

    full_timeout = perf_harness_runner.MEASUREMENT_SUBPROCESS_TIMEOUT_SECONDS
    timeout, skip_reason = _partitioned_timeout(
        full_timeout, deadline_monotonic, remaining_units,
        floor_seconds=share_floor_seconds, clock=clock,
    )
    if timeout is None:
        return {"status": "failed", "reason": skip_reason}
    was_deadline_bounded = deadline_monotonic is not None and timeout < full_timeout

    hang_diagnostics_path: str | None = None
    timer = None
    if diagnostics_dir is not None:
        leg_name = Path(results_dir).parent.name or "leg"
        round_index = Path(results_dir).name or "0"
        hang_diagnostics_path = str(Path(diagnostics_dir) / f"hang-{leg_name}-round{round_index}.json")
        arm_lead = _diagnostics_arm_lead(timeout, diagnostics_lead_seconds)
        if arm_lead > 0:
            timer = perf_gate_hang_diagnostics.arm(arm_lead, os.getpid(), hang_diagnostics_path)

    try:
        completed = runner(argv, cwd=leg_worktree, timeout=timeout)
    finally:
        if timer is not None:
            perf_gate_hang_diagnostics.disarm(timer)

    if completed.returncode != 0:
        failure: dict[str, Any] = {
            "status": "failed",
            "reason": (
                REASON_DEADLINE_BOUNDED_SUBPROCESS if was_deadline_bounded
                else "measurement subprocess exited non-zero"
            ),
            "exit_code": completed.returncode,
            "stderr_excerpt": perf_harness_runner._bounded_excerpt(completed.stderr),
        }
        if hang_diagnostics_path is not None:
            stderr_path = str(Path(hang_diagnostics_path).with_suffix("")) + ".stderr.txt"
            Path(stderr_path).parent.mkdir(parents=True, exist_ok=True)
            Path(stderr_path).write_text(completed.stderr or "", encoding="utf-8")
            failure["hang_diagnostics_path"] = hang_diagnostics_path
            failure["hang_diagnostics_stderr_path"] = stderr_path
        return failure
    if not out_path.exists():
        return {
            "status": "failed",
            "reason": "measurement subprocess wrote no record",
            "exit_code": completed.returncode,
        }
    try:
        return json.loads(out_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return {
            "status": "failed",
            "reason": "measurement record could not be parsed",
            "exception_class": type(exc).__name__,
            "message": str(exc)[:perf_harness_runner.STAGE_ERROR_MESSAGE_MAX_CHARS],
        }


def _stage_was_deadline_truncated(result: Any) -> bool:
    """True when `result` (a build_leg or measure_leg_round return value) carries either
    of this module's own named deadline reasons anywhere inside it -- including nested
    inside a build stage's own `timing` sub-mapping, where `_cwd_bound_runner`'s synthetic
    skip surfaces as a `stderr_excerpt`. A single substring scan over the serialized
    mapping is used deliberately rather than teaching this function every collector's own
    nested shape."""
    if not isinstance(result, dict):
        return False
    text = json.dumps(result)
    return (
        REASON_DEADLINE_BOUNDED_SUBPROCESS in text
        or REASON_DEADLINE_ALREADY_PASSED in text
        or REASON_DEADLINE_SHARE_BELOW_FLOOR in text
    )


def _is_successful_round(record: Any) -> bool:
    """A round is "completed" when the invoked scripts/perf_harness_runner.py wrote a
    well-formed record *and* that record's own measurement stage itself succeeded --
    never merely because a parseable record exists. A planning machine that cannot build
    Rogue at all still gets a well-formed record back (the harness runner's own main()
    returns 0 and writes --out regardless of an internal stage failure), so checking only
    for a parseable record would silently call a run "completed" when nothing was
    actually measured."""
    if not isinstance(record, dict) or "harness_run_schema_version" not in record:
        return False
    measurement = record.get("stages", {}).get("measurement")
    return isinstance(measurement, dict) and measurement.get("status") == "ok"


def _merge_metric_rounds(round_entries: list[dict[str, Any]]) -> dict[str, Any]:
    """One merged metric cell from `round_entries` (one leg's own per-round metric
    entries for one (benchmark, metric) pair, in round order): `samples` is the
    concatenation of every round's clean samples in round order, `n_clean` is their
    count, `status` is clean only when every contributing round was itself clean,
    `reason` is the first non-null reason otherwise, `median`/`mad` are recomputed from
    the merged samples through _perf_harness.median_and_mad and are absent entirely when
    the merged status is not clean, `tier_candidate` is carried through unchanged, and
    `tier_demoted_to` is present when any round carried it."""
    samples: list[Any] = []
    rejected_samples: list[Any] = []
    all_clean = True
    first_reason: str | None = None
    tier_candidate = None
    tier_demoted_to = None

    for entry in round_entries:
        if tier_candidate is None:
            tier_candidate = entry.get("tier_candidate")
        entry_samples = entry.get("samples")
        if isinstance(entry_samples, list):
            samples.extend(entry_samples)
        entry_rejected = entry.get("rejected_samples")
        if isinstance(entry_rejected, list):
            rejected_samples.extend(entry_rejected)
        if entry.get("status") != _perf_harness.STATUS_OK:
            all_clean = False
            if first_reason is None and entry.get("reason"):
                first_reason = entry.get("reason")
        if entry.get("tier_demoted_to") is not None:
            tier_demoted_to = entry.get("tier_demoted_to")

    merged: dict[str, Any] = {
        "tier_candidate": tier_candidate,
        "n_clean": len(samples),
        "samples": samples,
        "rejected_samples": rejected_samples,
        "status": _perf_harness.STATUS_OK if all_clean else _perf_harness.STATUS_INCONCLUSIVE,
        "reason": None if all_clean else first_reason,
    }
    if tier_demoted_to is not None:
        merged["tier_demoted_to"] = tier_demoted_to
    if all_clean and samples:
        merged["median"], merged["mad"] = _perf_harness.median_and_mad([float(v) for v in samples])
    return merged


def merge_leg_rounds(round_records: list[dict[str, Any]]) -> dict[str, Any]:
    """Merge one leg's own round_count harness-run records into one merged `benchmarks`
    mapping, keyed by benchmark name. A benchmark present in some rounds and absent from
    others is present in the merge with the rounds that carried it and a recorded
    `rounds_missing` count, rather than being silently dropped. `round_records` may
    include failure mappings (a round whose measurement subprocess failed): those
    contribute no benchmarks and count toward every benchmark's `rounds_missing`."""
    benchmark_names: set[str] = set()
    for record in round_records:
        benchmarks = record.get("benchmarks") if isinstance(record, dict) else None
        if isinstance(benchmarks, dict):
            benchmark_names.update(benchmarks.keys())

    merged: dict[str, Any] = {}
    for benchmark in sorted(benchmark_names):
        contributing_rounds: list[dict[str, Any]] = []
        rounds_missing = 0
        for record in round_records:
            benchmarks = record.get("benchmarks") if isinstance(record, dict) else None
            entry = benchmarks.get(benchmark) if isinstance(benchmarks, dict) else None
            if isinstance(entry, dict):
                contributing_rounds.append(entry)
            else:
                rounds_missing += 1

        metric_names: set[str] = set()
        windows: list[Any] = []
        for entry in contributing_rounds:
            metrics = entry.get("metrics")
            if isinstance(metrics, dict):
                metric_names.update(metrics.keys())
            entry_windows = entry.get("measurement_windows")
            if isinstance(entry_windows, list):
                windows.extend(entry_windows)

        merged_metrics: dict[str, Any] = {}
        for metric in sorted(metric_names):
            round_entries = [
                entry["metrics"][metric] for entry in contributing_rounds
                if isinstance(entry.get("metrics"), dict) and metric in entry["metrics"]
            ]
            merged_metrics[metric] = _merge_metric_rounds(round_entries)

        merged_entry: dict[str, Any] = {"metrics": merged_metrics, "measurement_windows": windows}
        if rounds_missing:
            merged_entry["rounds_missing"] = rounds_missing
        merged[benchmark] = merged_entry

    return merged


def interleave_order(rounds: int) -> list[str]:
    """The leg sequence for `rounds` rounds, candidate first, alternating, of length
    `2 * rounds` -- a plain value a test can assert rather than control flow."""
    order: list[str] = []
    for _ in range(rounds):
        order.append(LEG_CANDIDATE)
        order.append(LEG_MERGE_BASE)
    return order


def _first_environment(round_records: list[dict[str, Any]]) -> dict[str, Any]:
    for record in round_records:
        environment = record.get("environment") if isinstance(record, dict) else None
        if isinstance(environment, dict) and environment:
            return environment
    return {}


def build_ab_record(
    *,
    github_run_id: str,
    github_run_attempt: str,
    campaign_branch: str,
    dispatch_index: str,
    mode: str,
    label: str | None,
    rounds: int,
    patch_name: str | None,
    patch_sha256: str | None,
    patch_magnitude: str | None,
    patch_applied: bool,
    forced_condition: str | None,
    declared_candidate_ref: str,
    declared_merge_base_ref: str,
    declared_candidate_tree_hash: str,
    declared_merge_base_tree_hash: str,
    candidate_sha: str,
    merge_base_sha: str,
    candidate_tree_hash: str,
    merge_base_tree_hash: str,
    candidate_leg: dict[str, Any],
    merge_base_leg: dict[str, Any],
    environment: dict[str, Any],
    timings: dict[str, Any],
    stages: dict[str, Any],
    errors: list[dict[str, Any]],
    measured_modules: list[str] | None = None,
    measured_modules_is_default: bool = True,
    attempts: list[dict[str, Any]] | None = None,
    final_verdict: str | None = None,
    merge_base_source: str | None = None,
    cold_cache: bool | None = None,
    cold_cache_reason: str | None = None,
) -> dict[str, Any]:
    """Assemble the fixed top-level gate-ab record shape: gate_ab_schema_version, run,
    environment, legs, timings, stages, errors.

    `tree_hash_pair_match` is the merge-base leg's measured tree hash equalling its
    declared tree hash, and, when no patch was applied, the candidate leg's measured tree
    hash equalling its declared tree hash too. When a patch was applied the candidate half
    of the comparison never enters the boolean at all -- the merge-base half alone decides
    the match -- and the candidate's provenance is instead carried by `patch_applied`,
    `patch_sha256`, and `candidate_sha` (the pre-patch commit), so a reader can still tell
    exactly what was built without a tolerance-shaped comparison standing in for it.

    `measured_modules` is the module path list actually handed to the measurement
    subprocess, in invocation order, and `measured_modules_is_default` states whether that
    list equals the runner's own default set. A record whose module set is not the default
    is not a like-for-like replica of a default-set record: a reader comparing two records
    must check this field rather than assuming.

    `attempts` is the run's own attempts array (one entry, or two when the single in-job
    retry ran), each carrying that attempt's own verdict, reasons, and condition counts;
    `final_verdict` is derived by the caller from the last attempts entry rather than
    recomputed here, so the two can never disagree. `merge_base_source` names which source
    resolved `--merge-base-ref` (provenance only). `cold_cache` and `cold_cache_reason`
    record whether either leg's build measured a cold ccache, so a cold run is recorded as
    cold rather than blamed on the developer or resolved to INCONCLUSIVE. All five are
    optional and default to values that reproduce today's shape when omitted, so an older
    caller (or a preliminary, pre-retry-decision assembly) still gets a well-formed record."""
    merge_base_match = merge_base_tree_hash == declared_merge_base_tree_hash
    if patch_applied:
        tree_hash_pair_match = merge_base_match
    else:
        candidate_match = candidate_tree_hash == declared_candidate_tree_hash
        tree_hash_pair_match = bool(candidate_match and merge_base_match)

    run_info = {
        "github_run_id": github_run_id,
        "github_run_attempt": github_run_attempt,
        "campaign_branch": campaign_branch,
        "dispatch_index": dispatch_index,
        "mode": mode,
        "label": label,
        "rounds": rounds,
        "measured_modules": list(measured_modules) if measured_modules is not None else None,
        "measured_modules_is_default": measured_modules_is_default,
        "patch_name": patch_name,
        "patch_sha256": patch_sha256,
        "patch_magnitude": patch_magnitude,
        "patch_applied": patch_applied,
        "forced_condition": forced_condition,
        "declared_candidate_ref": declared_candidate_ref,
        "declared_merge_base_ref": declared_merge_base_ref,
        "declared_candidate_tree_hash": declared_candidate_tree_hash,
        "declared_merge_base_tree_hash": declared_merge_base_tree_hash,
        "candidate_sha": candidate_sha,
        "merge_base_sha": merge_base_sha,
        "candidate_tree_hash": candidate_tree_hash,
        "merge_base_tree_hash": merge_base_tree_hash,
        "tree_hash_pair_match": tree_hash_pair_match,
        "attempts": list(attempts) if attempts is not None else [],
        "final_verdict": final_verdict,
        "merge_base_source": merge_base_source,
        "cold_cache": cold_cache,
        "cold_cache_reason": cold_cache_reason,
    }

    ordered_timings: dict[str, Any] = {}
    for stage in TIMING_STAGE_ORDER:
        ordered_timings[stage] = timings.get(stage, _unavailable_timing("stage not run"))

    return {
        "gate_ab_schema_version": GATE_AB_SCHEMA_VERSION,
        "run": run_info,
        "environment": environment,
        "legs": {LEG_CANDIDATE: candidate_leg, LEG_MERGE_BASE: merge_base_leg},
        "timings": ordered_timings,
        "stages": stages,
        "errors": errors,
    }


def render_summary_markdown(record: dict[str, Any]) -> str:
    """A byte-stable markdown block naming the run's mode, tree-hash-pair match, attempt
    count, final verdict, merge-base source, cold-cache flag, every declared timing stage in
    TIMING_STAGE_ORDER, and each leg's build success and ccache summary. Deterministic over
    the same `record` input: no wall-clock timestamp."""
    run = record.get("run", {})
    lines = [
        "<!-- generated by scripts/perf_gate_ab_runner.py, do not edit by hand -->",
        "# Perf Gate A/B Run",
        "",
        f"Mode: {run.get('mode')}",
        f"Label: {run.get('label')}",
        f"Rounds: {run.get('rounds')}",
        f"Measured modules: {', '.join(run.get('measured_modules') or [])}",
        f"Measured modules is default: {run.get('measured_modules_is_default')}",
        f"Forced condition: {run.get('forced_condition')}",
        f"Tree-hash pair match: {run.get('tree_hash_pair_match')}",
        f"Attempts: {len(run.get('attempts') or [])}",
        f"Final verdict: {run.get('final_verdict')}",
        f"Merge-base source: {run.get('merge_base_source')}",
        f"Cold cache: {run.get('cold_cache')}",
        "",
        "## Timings",
        "",
        "| Stage | Seconds |",
        "| --- | --- |",
    ]
    timings = record.get("timings", {})
    for stage in TIMING_STAGE_ORDER:
        value = timings.get(stage)
        if isinstance(value, bool):
            lines.append(f"| {stage} | unavailable |")
        elif isinstance(value, (int, float)):
            lines.append(f"| {stage} | {value:.3f} |")
        elif isinstance(value, dict):
            lines.append(f"| {stage} | unavailable ({value.get('reason', 'unknown reason')}) |")
        else:
            lines.append(f"| {stage} | unavailable |")
    lines.append("")

    for leg_name in (LEG_CANDIDATE, LEG_MERGE_BASE):
        leg = record.get("legs", {}).get(leg_name, {})
        build = leg.get("build", {})
        lines.append(f"## Leg: {leg_name}")
        lines.append("")
        lines.append(f"- Build success: {build.get('success')}")
        lines.append(f"- Round count: {leg.get('round_count')}")
        lines.append("")
        lines.append(perf_harness_runner.format_ccache_summary_markdown(build.get("ccache", {})))

    return "\n".join(lines) + "\n"


def _sha_arg(value: str) -> str:
    if not SHA_PATTERN.match(value):
        raise argparse.ArgumentTypeError(f"{value!r} is not a 40-character lowercase hex git sha")
    return value


def _modules_arg(value: str) -> str:
    """argparse type for --modules: splits `value` on commas, strips each element, rejects
    an empty result and any element `PERF_MODULE_PATTERN` does not match, and returns
    `value` unchanged otherwise -- mirroring `_sha_arg`'s raise-on-reject convention.
    Element order and duplicates are preserved exactly: benchmark order inside one
    measurement invocation is the factor under investigation, so this function never sorts
    or de-duplicates, and a duplicate element is passed through so the record shows what
    actually ran."""
    elements = [element.strip() for element in value.split(",")]
    if not elements or any(not element for element in elements):
        raise argparse.ArgumentTypeError(f"{value!r} contains no usable module path")
    for element in elements:
        if not PERF_MODULE_PATTERN.match(element):
            raise argparse.ArgumentTypeError(f"{element!r} is not an accepted tests/perf module path")
    return value


def _resolve_patch_path(patch_dir: str, patch_name: str) -> Path | None:
    """Resolve `patch_name` against `patch_dir`, rejecting any value containing a path
    separator or a parent-directory component so a name can never escape the
    patch directory, and requiring the resolved file to already exist. Returns `None` on
    any rejection rather than raising."""
    if "/" in patch_name or "\\" in patch_name or ".." in Path(patch_name).parts:
        return None
    candidate = Path(patch_dir) / patch_name
    if not candidate.is_file():
        return None
    return candidate


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, help="Output path for the two-leg gate-ab record JSON")
    parser.add_argument(
        "--candidate-ref", required=True, type=_sha_arg,
        help="Full 40-character hex git sha for the candidate leg",
    )
    parser.add_argument(
        "--merge-base-ref", required=True, type=_sha_arg,
        help="Full 40-character hex git sha for the merge-base leg",
    )
    parser.add_argument(
        "--mode", default=MODE_NULL, choices=VALID_MODES,
        help="The run's declared population membership",
    )
    parser.add_argument(
        "--patch-name", default=None,
        help="Seeded-regression patch filename inside --patch-dir, applied to the candidate leg only",
    )
    parser.add_argument(
        "--patch-magnitude", default=None,
        help=f"Value recorded for provenance and exported as {PATCH_MAGNITUDE_ENV} to the "
        "candidate leg's measurement subprocess",
    )
    parser.add_argument(
        "--forced-condition", default=None,
        help="Deliberately induce one named evaluator INCONCLUSIVE condition; any other "
        "value is accepted, recorded, and induces nothing",
    )
    parser.add_argument("--label", default=None, help="Free-text label recorded on the run")
    parser.add_argument("--rounds", type=int, default=DEFAULT_ROUNDS, help="Measurement rounds per leg")
    parser.add_argument(
        "--modules", default=",".join(perf_harness_runner.DEFAULT_PERF_MODULES), type=_modules_arg,
        help="Comma-separated tests/perf module paths to measure",
    )
    parser.add_argument(
        "--patch-dir", default=DEFAULT_PATCH_DIR,
        help="Directory a --patch-name is resolved against",
    )
    parser.add_argument(
        "--worktree-root", default=None,
        help="Parent directory for both legs' git worktrees (default: a fresh tempdir)",
    )
    parser.add_argument(
        "--repo-root", default=".",
        help="The job checkout's own root, supplying tooling only -- never measured itself",
    )
    parser.add_argument(
        "--print-summary", action="store_true",
        help="Print the rendered markdown summary to stdout after writing --out",
    )
    parser.add_argument(
        "--deadline-seconds", type=int, default=GATE_RUNNER_DEADLINE_SECONDS,
        help="Seconds from process start within which every build and measurement "
        "subprocess this runner starts must be bounded. 0 disables clamping entirely, "
        "for a local run.",
    )
    parser.add_argument(
        "--round-share-floor-seconds", type=int, default=GATE_ROUND_SHARE_FLOOR_SECONDS,
        help="Seconds below which a measurement round's own partitioned deadline share is "
        "skipped rather than started. 0 disables the floor entirely, for a local run.",
    )
    parser.add_argument(
        "--hang-diagnostics-dir", default=None,
        help="Directory a per-thread hang snapshot is written into on a bounded "
        "measurement call's failure. Defaults to a hang-diagnostics subdirectory of "
        "--worktree-root.",
    )
    parser.add_argument(
        "--hang-diagnostics-lead-seconds", type=int, default=HANG_DIAGNOSTICS_LEAD_SECONDS,
        help="Seconds before a bounded measurement call's own expiry at which its "
        "hang snapshot fires.",
    )
    parser.add_argument(
        "--baseline", default=perf_gate_evaluator.DEFAULT_BASELINE_PATH,
        help="Path to the committed gate-baseline.json sidecar the single in-job retry "
        "decision is taken against.",
    )
    parser.add_argument(
        "--no-retry", action="store_true", default=False,
        help="Suppress the single automatic re-measurement this runner otherwise performs "
        "in job on a retry-eligible INCONCLUSIVE verdict, for a local run.",
    )
    parser.add_argument(
        "--merge-base-source", default="direct-invocation",
        choices=("pull_request_base_sha", "git_merge_base_fallback", "direct-invocation"),
        help="Which source resolved --merge-base-ref, recorded on the run for provenance only.",
    )
    return parser.parse_args(argv)


def _load_baseline_for_retry(path: str) -> dict[str, Any]:
    """Read the baseline sidecar for the single in-job retry decision only. This read is
    deliberately more forgiving than perf_gate_evaluator.main()'s own baseline read: an
    unreadable or unparsable baseline here substitutes a zero-cell baseline through
    perf_gate_evaluator._substituted_empty_baseline(), which evaluate_run resolves to
    INCONCLUSIVE with the structural no-gating-cell-evaluated reason -- never retried --
    rather than aborting a measurement run whose build cost has already been paid. The
    verdict-deciding read in perf_gate_evaluator.main() is not symmetric with this one: it
    fails loudly on the same unreadable-or-unparsable condition, because that read decides the
    published verdict rather than a cheap retry that can safely degrade to taking none."""
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        baseline, _ = perf_gate_evaluator._substituted_empty_baseline()
        return baseline


def _retry_affected_benchmarks(evaluation: dict[str, Any]) -> tuple[str, ...]:
    """The benchmark names carried by every gating cell whose verdict is INCONCLUSIVE with
    a reason in perf_gate_evaluator.RETRY_ELIGIBLE_CONDITIONS, de-duplicated and sorted."""
    return tuple(sorted({
        cell["benchmark"] for cell in evaluation.get("cells", [])
        if cell.get("gating")
        and cell.get("verdict") == perf_gate_evaluator.VERDICT_INCONCLUSIVE
        and cell.get("reason") in perf_gate_evaluator.RETRY_ELIGIBLE_CONDITIONS
    }))


def _is_retry_eligible(evaluation: dict[str, Any]) -> bool:
    """True only when the run verdict itself is INCONCLUSIVE and at least one gating cell
    carries a retry-eligible reason. A structural-only INCONCLUSIVE, a PASS, or a FAIL are
    all ineligible: exactly one retry is permitted, for the INCONCLUSIVE state only, on a
    condition a re-measurement can plausibly change."""
    return (
        evaluation.get("verdict") == perf_gate_evaluator.VERDICT_INCONCLUSIVE
        and bool(_retry_affected_benchmarks(evaluation))
    )


def _non_retry_reason(evaluation: dict[str, Any]) -> str:
    """Why the retry did not run for a non-retry-eligible first attempt: the verdict itself
    when it is PASS or FAIL, the structural condition(s) observed on its gating cells when
    it is INCONCLUSIVE for a structural reason, or the run-level verdict reason (e.g.
    no-gating-cell-evaluated) when no gating cell fired at all."""
    verdict = evaluation.get("verdict")
    if verdict != perf_gate_evaluator.VERDICT_INCONCLUSIVE:
        return f"verdict is {verdict}"
    gating_cells = [cell for cell in evaluation.get("cells", []) if cell.get("gating")]
    observed = {
        cell["reason"] for cell in gating_cells
        if cell.get("verdict") == perf_gate_evaluator.VERDICT_INCONCLUSIVE
        and cell.get("reason") in perf_gate_evaluator.STRUCTURAL_CONDITIONS
    }
    structural = [condition for condition in perf_gate_evaluator.STRUCTURAL_CONDITIONS if condition in observed]
    if structural:
        return "structural condition(s) observed: " + ", ".join(structural)
    return evaluation.get("verdict_reason") or "no retry-eligible condition observed on any gating cell"


def _attempt_entry(index: int, evaluation: dict[str, Any], *, retried: bool) -> dict[str, Any]:
    """One `run.attempts` entry derived from an evaluator evaluation: the attempt index
    (starting at one), the verdict and its reason, the gating cell count, the condition
    counts in the evaluator's own declared order, the failing gating cells reduced to
    benchmark/metric pairs, the retry-eligible conditions observed on gating cells (kept in
    perf_gate_evaluator.RETRY_ELIGIBLE_CONDITIONS' own declared order so two conditions
    that tie never depend on fire order), and whether a retry followed this attempt."""
    gating_cells = [cell for cell in evaluation.get("cells", []) if cell.get("gating")]
    observed = {
        cell["reason"] for cell in gating_cells
        if cell.get("verdict") == perf_gate_evaluator.VERDICT_INCONCLUSIVE
        and cell.get("reason") in perf_gate_evaluator.RETRY_ELIGIBLE_CONDITIONS
    }
    return {
        "attempt": index,
        "verdict": evaluation.get("verdict"),
        "verdict_reason": evaluation.get("verdict_reason"),
        "gating_cell_count": evaluation.get("gating_cell_count"),
        "condition_counts": evaluation.get("condition_counts"),
        "failing_cells": [
            {"benchmark": cell["benchmark"], "metric": cell["metric"]}
            for cell in evaluation.get("failing_cells", [])
        ],
        "retry_eligible_conditions_observed": [
            condition for condition in perf_gate_evaluator.RETRY_ELIGIBLE_CONDITIONS if condition in observed
        ],
        "retried": retried,
    }


def _cold_cache_status(
    candidate_build: dict[str, Any], merge_base_build: dict[str, Any],
) -> tuple[bool, str | None]:
    """True, with a naming reason, when either leg's own build recorded ccache mapping
    carries a zero `hit_rate_percent` (a genuine all-miss build) or omits the key entirely
    (ccache was unavailable). A cold run still completes and is recorded as cold rather than
    blamed on the developer or resolved to INCONCLUSIVE; nothing here maps a cold
    cache to a verdict."""
    for leg_name, build in ((LEG_CANDIDATE, candidate_build), (LEG_MERGE_BASE, merge_base_build)):
        ccache = build.get("ccache") if isinstance(build, dict) else None
        ccache = ccache if isinstance(ccache, dict) else {}
        if "hit_rate_percent" not in ccache:
            return True, f"{leg_name} leg's ccache was unavailable"
        if ccache.get("hit_rate_percent") == 0.0:
            return True, f"{leg_name} leg's ccache hit rate was zero"
    return False, None


def _run_gate_retry(
    *,
    affected_benchmarks: tuple[str, ...],
    candidate_worktree: Path,
    merge_base_worktree: Path,
    results_root: Path,
    runner: Callable[..., subprocess.CompletedProcess],
    repo_root: str,
    patch_magnitude: str | None,
    deadline_monotonic: float | None,
    diagnostics_dir: str,
    diagnostics_lead_seconds: int,
    share_floor_seconds: int,
) -> dict[str, Any]:
    """Run the single narrow retry pass: one interleaved round per leg, over only the
    modules that emit `affected_benchmarks`, reusing the already-built worktrees this
    process created -- no `git worktree add` and no build subprocess is started here. Never
    raises. Returns an empty modules tuple (running nothing) when no module maps
    `affected_benchmarks` at all.

    One round per leg rather than the run's own round count is a budget decision, not a
    shortcut: the worst case, every module affected, is then one measurement pass per leg,
    which the recorded per-round-per-leg medians place inside the recorded headroom to the
    ten minute budget, whereas repeating the run's own round count over every module would
    cost a second full paired measurement and break it."""
    retry_modules = modules_for_benchmarks(affected_benchmarks)
    rounds: dict[str, Any] = {}
    elapsed_seconds: dict[str, float] = {}
    if not retry_modules:
        return {"modules": retry_modules, "rounds": rounds, "elapsed_seconds": elapsed_seconds}

    retry_total_units = 2
    for index, leg in enumerate(interleave_order(1)):
        leg_worktree = candidate_worktree if leg == LEG_CANDIDATE else merge_base_worktree
        results_dir = results_root / leg / "retry"
        extra_env = {PATCH_MAGNITUDE_ENV: patch_magnitude} if leg == LEG_CANDIDATE and patch_magnitude else None
        start = time.monotonic()
        round_record = perf_harness_runner.run_stage(
            f"gate_retry_measure_{leg}",
            lambda leg_worktree=leg_worktree, results_dir=results_dir, extra_env=extra_env, index=index: (
                measure_leg_round(
                    str(leg_worktree), str(results_dir), runner,
                    checkout_root=repo_root, modules=retry_modules, extra_env=extra_env,
                    deadline_monotonic=deadline_monotonic, clock=time.monotonic,
                    diagnostics_dir=diagnostics_dir, diagnostics_lead_seconds=diagnostics_lead_seconds,
                    remaining_units=retry_total_units - index, share_floor_seconds=share_floor_seconds,
                )
            ),
        )
        elapsed_seconds[leg] = time.monotonic() - start
        rounds[leg] = round_record
    return {"modules": retry_modules, "rounds": rounds, "elapsed_seconds": elapsed_seconds}


def main(
    argv: list[str] | None = None,
    *,
    runner: Callable[..., subprocess.CompletedProcess] = _run_subprocess,
) -> int:
    args = parse_args(argv)

    total_start = time.monotonic()
    errors: list[dict[str, Any]] = []
    stages: dict[str, Any] = {}
    timings: dict[str, Any] = {}

    repo_root = str(Path(args.repo_root).resolve())
    worktree_root = Path(args.worktree_root) if args.worktree_root else Path(tempfile.mkdtemp(prefix="perf-gate-ab-"))
    worktree_root.mkdir(parents=True, exist_ok=True)
    candidate_worktree = worktree_root / "candidate"
    merge_base_worktree = worktree_root / "merge_base"

    modules = tuple(m.strip() for m in args.modules.split(",") if m.strip()) or perf_harness_runner.DEFAULT_PERF_MODULES
    # Order-sensitive on purpose: a reordered set is not the default set, because module
    # order inside one measurement invocation is exactly what is under investigation.
    measured_modules_is_default = modules == perf_harness_runner.DEFAULT_PERF_MODULES
    forced_condition = args.forced_condition
    induced_condition = forced_condition if forced_condition in FORCED_CONDITIONS else None

    deadline_seconds = args.deadline_seconds
    deadline_monotonic = time.monotonic() + deadline_seconds if deadline_seconds and deadline_seconds > 0 else None
    diagnostics_dir = args.hang_diagnostics_dir or str(worktree_root / "hang-diagnostics")
    diagnostics_lead_seconds = args.hang_diagnostics_lead_seconds
    truncated_stages: list[str] = []

    # Twice args.rounds: one measurement unit per leg per round. Each round is handed
    # remaining_units as this total minus its own loop index, so a round is partitioned
    # against what is left after every round that already ran, never against the whole
    # remaining budget.
    total_units = args.rounds * 2

    def _note_truncation(stage_name: str, result: Any) -> None:
        if _stage_was_deadline_truncated(result):
            truncated_stages.append(stage_name)

    candidate_rounds: list[Any] = []
    merge_base_rounds: list[Any] = []
    all_rounds_in_order: list[Any] = []
    candidate_build: dict[str, Any] = {"leg": LEG_CANDIDATE, "success": False}
    merge_base_build: dict[str, Any] = {"leg": LEG_MERGE_BASE, "success": False}
    declared_candidate_tree_hash = env_fingerprint.UNAVAILABLE
    declared_merge_base_tree_hash = env_fingerprint.UNAVAILABLE
    candidate_tree_hash = env_fingerprint.UNAVAILABLE
    merge_base_tree_hash = env_fingerprint.UNAVAILABLE
    candidate_sha = env_fingerprint.UNAVAILABLE
    merge_base_sha = env_fingerprint.UNAVAILABLE
    patch_result: dict[str, Any] | None = None
    patch_applied = False

    try:
        start = time.monotonic()
        candidate_worktree_result = perf_harness_runner.run_stage(
            "worktree_candidate",
            lambda: add_worktree(repo_root, str(candidate_worktree), args.candidate_ref, runner),
        )
        timings["worktree_candidate"] = time.monotonic() - start
        stages["worktree_candidate"] = candidate_worktree_result
        if _is_failed(candidate_worktree_result):
            errors.append(_stage_error("worktree_candidate", candidate_worktree_result))

        start = time.monotonic()
        merge_base_worktree_result = perf_harness_runner.run_stage(
            "worktree_merge_base",
            lambda: add_worktree(repo_root, str(merge_base_worktree), args.merge_base_ref, runner),
        )
        timings["worktree_merge_base"] = time.monotonic() - start
        stages["worktree_merge_base"] = merge_base_worktree_result
        if _is_failed(merge_base_worktree_result):
            errors.append(_stage_error("worktree_merge_base", merge_base_worktree_result))

        declared_candidate_tree_hash = tree_hash_of(str(candidate_worktree), runner)
        declared_merge_base_tree_hash = tree_hash_of(str(merge_base_worktree), runner)
        candidate_sha = head_sha_of(str(candidate_worktree), runner)
        merge_base_sha = head_sha_of(str(merge_base_worktree), runner)
        candidate_tree_hash = declared_candidate_tree_hash
        merge_base_tree_hash = declared_merge_base_tree_hash

        if induced_condition == FORCED_TREE_HASH_PAIR_MISMATCH:
            declared_merge_base_tree_hash = _BOGUS_TREE_HASH

        if args.patch_name:
            patch_path = _resolve_patch_path(args.patch_dir, args.patch_name)
            start = time.monotonic()
            if patch_path is None:
                patch_result = {
                    "status": "failed",
                    "patch_path": args.patch_name,
                    "reason": "patch name rejected or not found inside --patch-dir",
                }
            else:
                patch_result = perf_harness_runner.run_stage(
                    "patch_candidate",
                    lambda: apply_patch(str(candidate_worktree), str(patch_path), args.patch_magnitude, runner),
                )
            timings["patch_candidate"] = time.monotonic() - start
            stages["patch_candidate"] = patch_result
            patch_applied = patch_result.get("status") == "ok"
            if _is_failed(patch_result):
                errors.append(_stage_error("patch_candidate", patch_result))
            if patch_applied:
                candidate_tree_hash = tree_hash_of(str(candidate_worktree), runner)
        else:
            timings["patch_candidate"] = _unavailable_timing("no patch requested")

        start = time.monotonic()
        candidate_build_result = perf_harness_runner.run_stage(
            "build_candidate", lambda: build_leg(
                LEG_CANDIDATE, str(candidate_worktree), runner,
                deadline_monotonic=deadline_monotonic, clock=time.monotonic,
            ),
        )
        timings["build_candidate"] = time.monotonic() - start
        stages["build_candidate"] = candidate_build_result
        _note_truncation("build_candidate", candidate_build_result)
        if perf_harness_runner._is_stage_exception_failure(candidate_build_result):
            errors.append(_stage_error("build_candidate", candidate_build_result))
            candidate_build = {"leg": LEG_CANDIDATE, "success": False, "timing": candidate_build_result}
        else:
            candidate_build = candidate_build_result

        if induced_condition == FORCED_MERGE_BASE_BUILD_FAILED:
            merge_base_build = {
                "leg": LEG_MERGE_BASE,
                "success": False,
                "timing": {"status": "failed", "reason": f"forced_condition: {FORCED_MERGE_BASE_BUILD_FAILED}"},
                "ccache": {
                    "status": env_fingerprint.UNAVAILABLE,
                    "reason": "build skipped by forced_condition",
                },
                "targets": {"status": "skipped", "reason": "build skipped by forced_condition"},
            }
            stages["build_merge_base"] = merge_base_build
            timings["build_merge_base"] = _unavailable_timing(f"forced_condition: {FORCED_MERGE_BASE_BUILD_FAILED}")
        else:
            start = time.monotonic()
            merge_base_build_result = perf_harness_runner.run_stage(
                "build_merge_base", lambda: build_leg(
                    LEG_MERGE_BASE, str(merge_base_worktree), runner,
                    deadline_monotonic=deadline_monotonic, clock=time.monotonic,
                ),
            )
            timings["build_merge_base"] = time.monotonic() - start
            stages["build_merge_base"] = merge_base_build_result
            _note_truncation("build_merge_base", merge_base_build_result)
            if perf_harness_runner._is_stage_exception_failure(merge_base_build_result):
                errors.append(_stage_error("build_merge_base", merge_base_build_result))
                merge_base_build = {"leg": LEG_MERGE_BASE, "success": False, "timing": merge_base_build_result}
            else:
                merge_base_build = merge_base_build_result

        results_root = worktree_root / "results"
        candidate_round_elapsed: list[float] = []
        merge_base_round_elapsed: list[float] = []

        for index, leg in enumerate(interleave_order(args.rounds)):
            leg_worktree = candidate_worktree if leg == LEG_CANDIDATE else merge_base_worktree
            results_dir = results_root / leg / str(index)
            stage_name = f"measure_{leg}_round_{index}"

            extra_env = None
            if leg == LEG_CANDIDATE and args.patch_magnitude:
                extra_env = {PATCH_MAGNITUDE_ENV: args.patch_magnitude}

            start = time.monotonic()
            round_record = perf_harness_runner.run_stage(
                stage_name,
                lambda leg_worktree=leg_worktree, results_dir=results_dir, extra_env=extra_env, index=index: (
                    measure_leg_round(
                        str(leg_worktree), str(results_dir), runner,
                        checkout_root=repo_root, modules=modules, extra_env=extra_env,
                        deadline_monotonic=deadline_monotonic, clock=time.monotonic,
                        diagnostics_dir=diagnostics_dir, diagnostics_lead_seconds=diagnostics_lead_seconds,
                        remaining_units=total_units - index, share_floor_seconds=args.round_share_floor_seconds,
                    )
                ),
            )
            elapsed = time.monotonic() - start
            _note_truncation(stage_name, round_record)
            if _is_failed(round_record) or perf_harness_runner._is_stage_exception_failure(round_record):
                errors.append(_stage_error(stage_name, round_record))

            all_rounds_in_order.append(round_record)
            if leg == LEG_CANDIDATE:
                candidate_rounds.append(round_record)
                candidate_round_elapsed.append(elapsed)
            else:
                merge_base_rounds.append(round_record)
                merge_base_round_elapsed.append(elapsed)

        stages["measure_candidate"] = candidate_rounds
        stages["measure_merge_base"] = merge_base_rounds

        candidate_completed = sum(1 for record in candidate_rounds if _is_successful_round(record))
        merge_base_completed = sum(1 for record in merge_base_rounds if _is_successful_round(record))

        timings["measure_candidate"] = (
            _unavailable_timing("zero completed candidate measurement rounds")
            if candidate_completed == 0 else sum(candidate_round_elapsed)
        )
        timings["measure_merge_base"] = (
            _unavailable_timing("zero completed merge-base measurement rounds")
            if merge_base_completed == 0 else sum(merge_base_round_elapsed)
        )

        candidate_benchmarks = merge_leg_rounds([r for r in candidate_rounds if isinstance(r, dict)])
        merge_base_benchmarks = merge_leg_rounds([r for r in merge_base_rounds if isinstance(r, dict)])

        if induced_condition == FORCED_METRIC_ABSENT_FROM_LEG and merge_base_benchmarks:
            dropped_benchmark = sorted(merge_base_benchmarks)[0]
            merge_base_benchmarks = {
                name: entry for name, entry in merge_base_benchmarks.items() if name != dropped_benchmark
            }
            stages["forced_metric_absent_dropped_benchmark"] = dropped_benchmark

        environment = _first_environment(all_rounds_in_order)

        # --- the single in-process retry -------------------------------------------------
        # Decided, run, and merged here, still inside this try block and before the finally
        # below removes both worktrees, so the retry reuses them and pays no rebuild.
        def _record_kwargs() -> dict[str, Any]:
            return dict(
                github_run_id=os.environ.get("GITHUB_RUN_ID", env_fingerprint.UNAVAILABLE),
                github_run_attempt=os.environ.get("GITHUB_RUN_ATTEMPT", env_fingerprint.UNAVAILABLE),
                campaign_branch=os.environ.get("HARNESS_CAMPAIGN_BRANCH", env_fingerprint.UNAVAILABLE),
                dispatch_index=os.environ.get("HARNESS_DISPATCH_INDEX", env_fingerprint.UNAVAILABLE),
                mode=args.mode, label=args.label, rounds=args.rounds,
                measured_modules=list(modules), measured_modules_is_default=measured_modules_is_default,
                patch_name=args.patch_name, patch_sha256=(patch_result or {}).get("patch_sha256"),
                patch_magnitude=args.patch_magnitude, patch_applied=patch_applied,
                forced_condition=forced_condition,
                declared_candidate_ref=args.candidate_ref, declared_merge_base_ref=args.merge_base_ref,
                declared_candidate_tree_hash=declared_candidate_tree_hash,
                declared_merge_base_tree_hash=declared_merge_base_tree_hash,
                candidate_sha=candidate_sha, merge_base_sha=merge_base_sha,
                candidate_tree_hash=candidate_tree_hash, merge_base_tree_hash=merge_base_tree_hash,
            )

        baseline_for_retry = _load_baseline_for_retry(args.baseline)
        attempt1_record = build_ab_record(
            **_record_kwargs(),
            candidate_leg={
                "build": candidate_build, "benchmarks": candidate_benchmarks,
                "rounds": candidate_rounds, "round_count": candidate_completed,
            },
            merge_base_leg={
                "build": merge_base_build, "benchmarks": merge_base_benchmarks,
                "rounds": merge_base_rounds, "round_count": merge_base_completed,
            },
            environment=environment, timings=timings, stages=stages, errors=errors,
        )
        evaluation1 = perf_gate_evaluator.evaluate_run(attempt1_record, baseline_for_retry)
        affected_benchmarks = _retry_affected_benchmarks(evaluation1)
        retry_eligible = _is_retry_eligible(evaluation1)

        retry_ran = False
        retry_outcome: dict[str, Any] | None = None
        retry_reason: str | None = None
        not_remeasured: list[dict[str, str]] = []

        if not retry_eligible:
            retry_reason = _non_retry_reason(evaluation1)
        elif args.no_retry:
            retry_reason = "suppressed by --no-retry"
        else:
            retry_outcome = _run_gate_retry(
                affected_benchmarks=affected_benchmarks,
                candidate_worktree=candidate_worktree, merge_base_worktree=merge_base_worktree,
                results_root=results_root, runner=runner, repo_root=repo_root,
                patch_magnitude=args.patch_magnitude, deadline_monotonic=deadline_monotonic,
                diagnostics_dir=diagnostics_dir, diagnostics_lead_seconds=diagnostics_lead_seconds,
                share_floor_seconds=args.round_share_floor_seconds,
            )
            if not retry_outcome["modules"]:
                retry_reason = "no module maps the affected benchmark set"
            else:
                retry_ran = True

        if retry_ran:
            candidate_retry_round = retry_outcome["rounds"].get(LEG_CANDIDATE)
            merge_base_retry_round = retry_outcome["rounds"].get(LEG_MERGE_BASE)

            for stage_name, round_record in (
                (f"gate_retry_measure_{LEG_CANDIDATE}", candidate_retry_round),
                (f"gate_retry_measure_{LEG_MERGE_BASE}", merge_base_retry_round),
            ):
                _note_truncation(stage_name, round_record)
                if _is_failed(round_record) or perf_harness_runner._is_stage_exception_failure(round_record):
                    errors.append(_stage_error(stage_name, round_record))

            candidate_rounds.append(candidate_retry_round)
            merge_base_rounds.append(merge_base_retry_round)
            all_rounds_in_order.append(candidate_retry_round)
            all_rounds_in_order.append(merge_base_retry_round)

            retry_candidate_benchmarks = merge_leg_rounds(
                [r for r in (candidate_retry_round,) if isinstance(r, dict)],
            )
            retry_merge_base_benchmarks = merge_leg_rounds(
                [r for r in (merge_base_retry_round,) if isinstance(r, dict)],
            )
            for benchmark in affected_benchmarks:
                if benchmark in retry_candidate_benchmarks:
                    candidate_benchmarks[benchmark] = retry_candidate_benchmarks[benchmark]
                else:
                    not_remeasured.append({"leg": LEG_CANDIDATE, "benchmark": benchmark})
                if benchmark in retry_merge_base_benchmarks:
                    merge_base_benchmarks[benchmark] = retry_merge_base_benchmarks[benchmark]
                else:
                    not_remeasured.append({"leg": LEG_MERGE_BASE, "benchmark": benchmark})

        if retry_ran:
            # The retry appended one round per leg to the same two lists the tally above
            # was taken over, so that tally now describes a rounds list that no longer
            # exists. Recompute it once, over the same success predicate, so every record
            # assembled from here on reads a round_count that matches its own rounds list.
            candidate_completed = sum(1 for record in candidate_rounds if _is_successful_round(record))
            merge_base_completed = sum(1 for record in merge_base_rounds if _is_successful_round(record))

        attempts = [_attempt_entry(1, evaluation1, retried=retry_ran)]
        final_verdict = evaluation1.get("verdict")
        if retry_ran:
            attempt2_record = build_ab_record(
                **_record_kwargs(),
                candidate_leg={
                    "build": candidate_build, "benchmarks": candidate_benchmarks,
                    "rounds": candidate_rounds, "round_count": candidate_completed,
                },
                merge_base_leg={
                    "build": merge_base_build, "benchmarks": merge_base_benchmarks,
                    "rounds": merge_base_rounds, "round_count": merge_base_completed,
                },
                environment=environment, timings=timings, stages=stages, errors=errors,
            )
            evaluation2 = perf_gate_evaluator.evaluate_run(attempt2_record, baseline_for_retry)
            attempts.append(_attempt_entry(2, evaluation2, retried=False))
            final_verdict = evaluation2.get("verdict")

        stages["gate_retry"] = {
            "ran": retry_ran,
            "reason": retry_reason,
            "affected_benchmarks": list(affected_benchmarks),
            "modules": list(retry_outcome["modules"]) if retry_outcome else [],
            "elapsed_seconds": retry_outcome["elapsed_seconds"] if retry_outcome else {},
            "not_remeasured_benchmarks": not_remeasured,
            "no_retry_flag": args.no_retry,
        }

        cold_cache, cold_cache_reason = _cold_cache_status(candidate_build, merge_base_build)
    finally:
        remove_candidate_result = remove_worktree(repo_root, str(candidate_worktree), runner)
        remove_merge_base_result = remove_worktree(repo_root, str(merge_base_worktree), runner)
        stages["remove_worktree_candidate"] = remove_candidate_result
        stages["remove_worktree_merge_base"] = remove_merge_base_result

    timings["total"] = time.monotonic() - total_start

    # Additive only: no other emitted field changes shape, so the report generator's
    # byte-identical regeneration over the already-published population is unaffected.
    stages["runner_deadline"] = {
        "deadline_seconds": deadline_seconds,
        "exceeded": bool(truncated_stages),
        "truncated_stages": truncated_stages,
        "round_share_floor_seconds": args.round_share_floor_seconds,
        "partitioned_units": total_units,
    }

    candidate_leg = {
        "build": candidate_build,
        "benchmarks": candidate_benchmarks,
        "rounds": candidate_rounds,
        "round_count": candidate_completed,
    }
    merge_base_leg = {
        "build": merge_base_build,
        "benchmarks": merge_base_benchmarks,
        "rounds": merge_base_rounds,
        "round_count": merge_base_completed,
    }

    record = build_ab_record(
        **_record_kwargs(),
        candidate_leg=candidate_leg,
        merge_base_leg=merge_base_leg,
        environment=environment,
        timings=timings,
        stages=stages,
        errors=errors,
        attempts=attempts,
        final_verdict=final_verdict,
        merge_base_source=args.merge_base_source,
        cold_cache=cold_cache,
        cold_cache_reason=cold_cache_reason,
    )

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if args.print_summary:
        print(render_summary_markdown(record))

    return 0


if __name__ == "__main__":
    sys.exit(main())
# ----------------------------------------------------------------------------
