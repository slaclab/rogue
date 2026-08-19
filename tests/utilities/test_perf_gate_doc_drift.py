# ----------------------------------------------------------------------------
# Title      : Perf Gate Documentation Drift Tests
# ----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
# ----------------------------------------------------------------------------

"""Binds tests/perf/README.md's quoted vocabulary to the live constants declared in
scripts/perf_gate_evaluator.py. This module is not the source-audit shape
tests/METHODOLOGY.md warns against: it never reads a .py file as text. It imports the
evaluator's constants as live objects through importlib.import_module, and it reads
tests/perf/README.md as a plain data file, the same way a test may read any other fixture.
"""

from __future__ import annotations

import argparse
import importlib
import json
import re
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

perf_gate_evaluator = importlib.import_module("perf_gate_evaluator")
perf_gate_ab_runner = importlib.import_module("perf_gate_ab_runner")

README_PATH = REPO_ROOT / "tests" / "perf" / "README.md"
GATE_RUNS_DIR = REPO_ROOT / "docs" / "plans" / "perf-ci-hardening" / "gate-runs"
EVIDENCE_TAG_PATH = GATE_RUNS_DIR / "evidence-tag.json"
GATE_BASELINE_PATH = REPO_ROOT / "docs" / "plans" / "perf-ci-hardening" / "gate-baseline.json"
PERF_GATE_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "perf_gate.yml"

# Excludes the private planning system's own vocabulary: a requirement or decision
# identifier (an uppercase tag followed by a dash and two or more digits, such as
# DOC-01, GATE-19, or D-13), and a literal reference to the local, gitignored
# `.planning/` directory. Neither belongs in a document a contributor reads, because
# neither means anything outside the planning tooling that produced it. Committed
# narrative documents under docs/plans/perf-ci-hardening/ are a different thing
# entirely (durable, shipped artifacts this README is required to cite) and this
# pattern does not match paths under docs/plans/, only the local planning directory
# and its identifier vocabulary.
PLANNING_ARTIFACT_CITATION_PATTERN = re.compile(r"\b[A-Z]{2,10}-\d{2,}\b|\.planning/")


def _read_readme() -> str:
    # tests/perf/README.md is a committed deliverable of this repository, not an optional
    # generated sidecar such as the campaign report tests/utilities/test_perf_tier_registry.py
    # skips over when absent. A deleted or empty README must fail this suite outright rather
    # than skip, so the drift check itself cannot be silenced by removing the file it checks.
    return README_PATH.read_text(encoding="utf-8")


def test_readme_exists_and_is_non_empty():
    assert README_PATH.exists(), f"{README_PATH} is missing"
    assert _read_readme().strip(), f"{README_PATH} is empty"


def test_readme_quotes_every_live_verdict_literal():
    text = _read_readme()
    for verdict in (
        perf_gate_evaluator.VERDICT_PASS,
        perf_gate_evaluator.VERDICT_FAIL,
        perf_gate_evaluator.VERDICT_INCONCLUSIVE,
    ):
        assert verdict in text, verdict


def test_readme_quotes_every_live_inconclusive_condition():
    text = _read_readme()
    for condition in perf_gate_evaluator.INCONCLUSIVE_CONDITIONS:
        assert condition in text, condition


def test_readme_quotes_the_live_retry_partition():
    text = _read_readme()
    for condition in perf_gate_evaluator.RETRY_ELIGIBLE_CONDITIONS:
        assert condition in text, condition
    for condition in perf_gate_evaluator.STRUCTURAL_CONDITIONS:
        assert condition in text, condition


def _evaluator_declared_long_flags() -> set[str]:
    """The real `--long-form` option strings scripts/perf_gate_evaluator.py's own
    parse_args() declares, captured by intercepting the ArgumentParser instance that
    function builds internally rather than hand-copying its option list. parse_args()
    never exposes its parser as a module-level object, so the only way to read the
    parser's own declared actions without re-typing them is to run parse_args() itself
    with the one required argument it needs, and capture the parser it constructs along
    the way."""
    captured: list[argparse.ArgumentParser] = []
    original_init = argparse.ArgumentParser.__init__

    def _capturing_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        captured.append(self)

    argparse.ArgumentParser.__init__ = _capturing_init
    try:
        perf_gate_evaluator.parse_args(["--record", "/dev/null"])
    finally:
        argparse.ArgumentParser.__init__ = original_init

    flags: set[str] = set()
    for action in captured[0]._actions:
        flags.update(option for option in action.option_strings if option.startswith("--"))
    return flags


def _evaluator_invocation_block(text: str) -> str:
    """The one fenced code block in `text` that invokes scripts/perf_gate_evaluator.py,
    isolated from the README's other fenced blocks (in particular the
    scripts/perf_gate_ab_runner.py invocation, which declares its own, different flag
    set) so a flag-shaped token belonging to that other script is never checked against
    this script's own parser."""
    for block in re.findall(r"```(?:sh)?\n(.*?)```", text, re.DOTALL):
        if "perf_gate_evaluator.py" in block:
            return block
    raise AssertionError(
        "no fenced code block in tests/perf/README.md invokes scripts/perf_gate_evaluator.py"
    )


def test_readme_quotes_the_live_evaluator_cli_flags():
    text = _read_readme()
    block = _evaluator_invocation_block(text)
    documented_flags = set(re.findall(r"--[a-z][a-z-]*", block))
    real_flags = _evaluator_declared_long_flags()

    assert documented_flags, "no flag-shaped token found in the evaluator invocation block"
    # No option string in the documented command is absent from the parser's own
    # declared set: this is what catches a plausible-but-absent flag name such as
    # --summary-out or --verdict-out before it reaches a contributor's shell.
    assert documented_flags <= real_flags, documented_flags - real_flags
    # The documented command actually exercises the evaluator's real required and
    # output-path flags, not merely avoids fake ones.
    assert {"--record", "--baseline", "--out-json", "--out-md"} <= documented_flags


def test_readme_worked_example_record_is_committed():
    text = _read_readme()
    match = re.search(r"gate-runs/(\d+-ab-record\.json)", text)
    assert match, "README does not name a gate-runs/<id>-ab-record.json worked example"
    record_path = GATE_RUNS_DIR / match.group(1)
    assert record_path.exists(), f"{record_path} is missing"


def test_readme_quotes_the_recorded_evidence_tag():
    tag_data = json.loads(EVIDENCE_TAG_PATH.read_text(encoding="utf-8"))
    text = _read_readme()
    assert tag_data["tag"] in text


def test_readme_quotes_the_live_override_trailer_constants():
    text = _read_readme()
    assert perf_gate_evaluator.OVERRIDE_TRAILER_KEY in text
    assert str(perf_gate_evaluator.OVERRIDE_MIN_JUSTIFICATION_CHARS) in text
    for reason in (
        perf_gate_evaluator.OVERRIDE_REJECTED_NO_SEMICOLON,
        perf_gate_evaluator.OVERRIDE_REJECTED_EMPTY_JUSTIFICATION,
        perf_gate_evaluator.OVERRIDE_REJECTED_JUSTIFICATION_TOO_SHORT,
        perf_gate_evaluator.OVERRIDE_REJECTED_EMPTY_CELL_LIST,
        perf_gate_evaluator.OVERRIDE_REJECTED_MALFORMED_CELL_TOKEN,
    ):
        assert reason in text, reason
    for reason in (
        perf_gate_evaluator.OVERRIDE_UNMATCHED_NOT_FAILING,
        perf_gate_evaluator.OVERRIDE_UNMATCHED_NOT_GATING,
        perf_gate_evaluator.OVERRIDE_UNMATCHED_ABSENT_FROM_BASELINE,
    ):
        assert reason in text, reason


def test_readme_quotes_the_committed_gating_cell_census():
    census = json.loads(GATE_BASELINE_PATH.read_text(encoding="utf-8"))["census"]
    text = _read_readme()

    quoted = {
        "gating_cells": census["gating_cells"],
        "gating_metrics": census["gating_metrics"],
        "total_cells": census["total_cells"],
    }
    for key, value in quoted.items():
        assert str(value) in text, f"{key}={value} not quoted in {README_PATH}"

    # The three counts must be distinct values, so this test cannot pass on a document
    # that quotes one number three times and calls it the census.
    values = list(quoted.values())
    assert len(set(values)) == len(values), quoted


def _live_report_only_variable_name() -> str:
    """The real repository-variable name `.github/workflows/perf_gate.yml`'s gate job
    reads to decide whether the gate blocks, extracted from the parsed workflow rather
    than hand-copied. The workflow is parsed with a YAML loader (PyYAML is already a
    dependency this repository's own test suite uses, see
    tests/interfaces/test_stream_variable.py and tests/fileio/test_core_fileio.py) and
    the variable name is pulled out of the `GATE_BLOCKING` environment expression of
    the evaluator step, the one place this workflow actually reads that variable to
    decide gate polarity. A text-level regex anchored to the same key would work
    equally well here, since this workflow file is configuration rather than
    production source and the thing being extracted is only the name the document
    must match; the YAML loader is used because the file parses cleanly."""
    workflow = yaml.safe_load(PERF_GATE_WORKFLOW_PATH.read_text(encoding="utf-8"))
    for job in workflow["jobs"].values():
        for step in job.get("steps", []):
            expr = step.get("env", {}).get("GATE_BLOCKING")
            if expr:
                match = re.search(r"vars\.([A-Za-z0-9_]+)", expr)
                if match:
                    return match.group(1)
    raise AssertionError(
        f"no GATE_BLOCKING environment expression found in {PERF_GATE_WORKFLOW_PATH}"
    )


def test_readme_quotes_the_live_report_only_variable_name():
    variable_name = _live_report_only_variable_name()
    assert variable_name in _read_readme()


def test_readme_lists_every_module_and_benchmark_from_the_live_mapping():
    text = _read_readme()
    mapping = perf_gate_ab_runner.MODULE_BENCHMARKS

    for module_path in mapping:
        assert module_path in text, module_path

    all_benchmarks = {
        benchmark for benchmarks in mapping.values() for benchmark in benchmarks
    }
    for benchmark in all_benchmarks:
        assert benchmark in text, benchmark

    # For each module, the benchmark identities must appear in the document in the
    # mapping's own declared order: the sequence of their first index positions in the
    # document text must already be sorted ascending.
    for module_path, benchmarks in mapping.items():
        positions = [text.index(benchmark) for benchmark in benchmarks]
        assert positions == sorted(positions), (module_path, benchmarks, positions)


def test_readme_carries_no_planning_artifact_citation():
    text = _read_readme()
    matches = PLANNING_ARTIFACT_CITATION_PATTERN.findall(text)
    assert not matches, matches
# ----------------------------------------------------------------------------
