# ----------------------------------------------------------------------------
# Title      : Seeded Regression Patch Integrity Tests
# ----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
# ----------------------------------------------------------------------------

"""Behavioural coverage for the five committed seeded-regression patch files
under docs/plans/perf-ci-hardening/seeded-regressions/. Proves that every
patch applies and reverses cleanly against the current tree, that the patch
count is pinned at five, that applying two patches in sequence and reversing
them in reverse order leaves the tree clean except for one documented
conflicting pair, and that every patch name satisfies the same
no-path-separator / no-parent-directory-component contract
scripts/perf_gate_ab_runner.py's own apply_patch name resolution enforces.

Every check that mutates a tracked file runs inside a scratch git worktree
created with `git worktree add --detach`, torn down in fixture teardown even
when a test fails, so nothing here ever touches the developer's own working
tree. No test in this module asserts on the text of any library source file;
the only content assertion is the presence of the magnitude environment
variable name in a patch, which is the contract between a patch and the
runner, not an implementation detail.

scripts/perf_gate_ab_runner.py is a sibling wave-2 plan's deliverable and may
not exist in every checkout that runs this module concurrently with that
plan. Where this module needs to call into it, the check is skipped rather
than failing on an import it cannot control; the self-contained name
resolution contract test below (test_patch_names_satisfy_the_safe_name_contract)
still runs unconditionally, since it verifies the contract against the real
discovered patch files rather than against that module's implementation.
"""

from __future__ import annotations

import itertools
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

PATCH_DIR = REPO_ROOT / "docs" / "plans" / "perf-ci-hardening" / "seeded-regressions"

# Magnitude environment variable every patch is gated on. Reserved by
# scripts/perf_gate_ab_runner.py's PATCH_MAGNITUDE_ENV.
MAGNITUDE_ENV_VAR = "ROGUE_SEEDED_REGRESSION_STRIDE"

EXPECTED_PATCH_NAMES = frozenset(
    {
        "extra-memcpy-per-frame",
        "extra-hotpath-allocation",
        "disable-frame-batching",
        "extra-transaction-lock",
        "per-transaction-delay",
    }
)

# The one pair known to genuinely conflict when applied in sequence (rather
# than combined into a single git apply invocation): both patches insert at
# the same anchor inside Master::intTransaction, immediately around the
# tran->log_->debug() call preceding slave->doTransaction(tran). Documented
# in README.md's Reproducing section. Any *other* pair conflicting would be a
# regression this test must catch, not a second expected pair to add here.
EXPECTED_CONFLICTING_PAIR = frozenset({"extra-transaction-lock", "per-transaction-delay"})


def _discovered_patches() -> list[Path]:
    if not PATCH_DIR.is_dir():
        return []
    return sorted(PATCH_DIR.glob("*.patch"))


def _run_git(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git"] + args,
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


@pytest.fixture
def scratch_worktree(tmp_path):
    """A throwaway git worktree checked out detached at HEAD. Patches are
    applied and reversed inside it so the developer's own working tree is
    never touched. Removed in teardown even if the test raised.
    """
    worktree_dir = tmp_path / "seeded-regression-scratch"
    completed = _run_git(["worktree", "add", "--detach", str(worktree_dir), "HEAD"], cwd=REPO_ROOT)
    assert completed.returncode == 0, completed.stderr
    try:
        yield worktree_dir
    finally:
        _run_git(["worktree", "remove", "--force", str(worktree_dir)], cwd=REPO_ROOT)


def test_directory_holds_exactly_five_patch_files():
    patches = _discovered_patches()
    assert len(patches) == 5, [p.name for p in patches]


def test_discovered_patch_names_match_expected_set():
    discovered = {p.stem for p in _discovered_patches()}
    assert discovered == EXPECTED_PATCH_NAMES


@pytest.mark.parametrize("patch_path", _discovered_patches(), ids=lambda p: p.stem)
def test_patch_applies_and_reverses_cleanly(patch_path, scratch_worktree):
    check = _run_git(["apply", "--check", str(patch_path)], cwd=scratch_worktree)
    assert check.returncode == 0, check.stderr

    applied = _run_git(["apply", str(patch_path)], cwd=scratch_worktree)
    assert applied.returncode == 0, applied.stderr

    dirty = _run_git(["status", "--porcelain"], cwd=scratch_worktree)
    assert dirty.stdout.strip() != "", "patch application produced no working-tree change"

    reversed_apply = _run_git(["apply", "-R", str(patch_path)], cwd=scratch_worktree)
    assert reversed_apply.returncode == 0, reversed_apply.stderr

    clean = _run_git(["status", "--porcelain"], cwd=scratch_worktree)
    assert clean.stdout.strip() == "", clean.stdout


@pytest.mark.parametrize("patch_path", _discovered_patches(), ids=lambda p: p.stem)
def test_patch_contains_magnitude_environment_variable_name(patch_path):
    text = patch_path.read_text(encoding="utf-8")
    assert MAGNITUDE_ENV_VAR in text


@pytest.mark.parametrize(
    "pair",
    list(itertools.combinations(sorted(_discovered_patches()), 2)),
    ids=lambda pair: f"{pair[0].stem}+{pair[1].stem}",
)
def test_patch_pair_sequence_and_reverse_leaves_tree_clean_except_documented_conflict(pair, scratch_worktree):
    first_path, second_path = pair
    pair_names = frozenset({first_path.stem, second_path.stem})

    first_apply = _run_git(["apply", str(first_path)], cwd=scratch_worktree)
    assert first_apply.returncode == 0, first_apply.stderr

    second_check = _run_git(["apply", "--check", str(second_path)], cwd=scratch_worktree)

    if pair_names == EXPECTED_CONFLICTING_PAIR:
        # Recorded as an expected outcome, not a failure: the second patch's
        # context no longer matches after the first is applied, because both
        # anchor at the same location in Master::intTransaction.
        assert second_check.returncode != 0, (
            "expected conflicting pair now applies together; update "
            "EXPECTED_CONFLICTING_PAIR and README.md if this pair no longer conflicts"
        )
        reverted = _run_git(["apply", "-R", str(first_path)], cwd=scratch_worktree)
        assert reverted.returncode == 0, reverted.stderr
    else:
        assert second_check.returncode == 0, (
            f"unexpected conflict between {first_path.stem} and {second_path.stem}: {second_check.stderr}"
        )
        second_apply = _run_git(["apply", str(second_path)], cwd=scratch_worktree)
        assert second_apply.returncode == 0, second_apply.stderr

        # Reverse in the opposite order of application.
        reverse_second = _run_git(["apply", "-R", str(second_path)], cwd=scratch_worktree)
        assert reverse_second.returncode == 0, reverse_second.stderr
        reverse_first = _run_git(["apply", "-R", str(first_path)], cwd=scratch_worktree)
        assert reverse_first.returncode == 0, reverse_first.stderr

    clean = _run_git(["status", "--porcelain"], cwd=scratch_worktree)
    assert clean.stdout.strip() == "", clean.stdout


def _violates_safe_name_contract(name: str) -> bool:
    """Mirrors the no-path-separator / no-parent-directory-component contract
    scripts/perf_gate_ab_runner.py's apply_patch enforces on a runtime-supplied
    patch name (T-04-15). A name is rejected if it contains a path separator
    of either flavor or a literal parent-directory component.
    """
    if "/" in name or "\\" in name:
        return True
    if ".." in Path(name).parts:
        return True
    return False


def test_patch_names_satisfy_the_safe_name_contract():
    for patch_path in _discovered_patches():
        assert not _violates_safe_name_contract(patch_path.stem), patch_path.stem


@pytest.mark.parametrize(
    "bad_name",
    ["../escape", "sub/dir", "sub\\dir", "..", "a/../b"],
)
def test_unsafe_names_are_rejected_by_the_safe_name_contract(bad_name):
    assert _violates_safe_name_contract(bad_name)


def test_ab_runner_module_structural_sanity_when_present():
    """Soft structural cross-check against scripts/perf_gate_ab_runner.py,
    skipped when that sibling wave-2 plan's module is not yet present in this
    checkout. Only checks module-level constants this plan's magnitude
    mechanism and patch directory are contractually bound to; never guesses
    at apply_patch's call signature.
    """
    ab_runner = pytest.importorskip(
        "perf_gate_ab_runner",
        reason="scripts/perf_gate_ab_runner.py is a sibling wave-2 plan's deliverable",
    )
    assert hasattr(ab_runner, "apply_patch")
    if hasattr(ab_runner, "PATCH_MAGNITUDE_ENV"):
        assert ab_runner.PATCH_MAGNITUDE_ENV == MAGNITUDE_ENV_VAR
    if hasattr(ab_runner, "DEFAULT_PATCH_DIR"):
        assert Path(ab_runner.DEFAULT_PATCH_DIR).resolve() == PATCH_DIR.resolve()


def test_no_scratch_worktree_leaks_after_the_module_runs():
    """Runs last by definition order; the real guarantee that no worktree
    leaks comes from every other test's fixture teardown. This test
    independently confirms the invariant by listing worktrees registered
    against this repository and asserting none of them is one of this
    module's own scratch worktrees. A bare `git worktree list` line count is
    not a valid assertion in a multi-agent checkout: sibling agents and the
    primary checkout each register their own persistent worktree entries
    that this module never created and must not be mistaken for a leak.
    """
    listed = _run_git(["worktree", "list"], cwd=REPO_ROOT)
    assert listed.returncode == 0, listed.stderr
    lines = [line for line in listed.stdout.splitlines() if line.strip()]
    leaked = [line for line in lines if "seeded-regression-scratch" in line]
    assert leaked == [], leaked


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
