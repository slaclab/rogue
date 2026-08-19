# ----------------------------------------------------------------------------
# Title      : Perf Data Schema Tests
# ----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
# ----------------------------------------------------------------------------

"""Unit tests for scripts/perf_data.py's schema version 2 bump and its
version 1 upgrade path. Every test asserts on returned values or rendered
output, never on scripts/perf_data.py's own source text.
"""

from __future__ import annotations

import importlib
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

perf_data = importlib.import_module("perf_data")
ci_perf_summary = importlib.import_module("ci_perf_summary")

# Copied byte for byte from origin/gh-pages, path recorded in the plan summary:
# perf/branches/main/history/263daced49c65c602513911cb0a5ea91b0292ad7.json
FIXTURE_PATH = REPO_ROOT / "tests" / "utilities" / "fixtures" / "perf_published_record_schema_v1.json"


def _upgraded_fixture() -> dict:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return perf_data.upgrade_summary(payload)


def _run_git(args: list[str], cwd: Path) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


def _v1_record(**overrides) -> dict:
    record = {
        "schema_version": 1,
        "ref_name": "main",
        "ref_slug": "main",
        "sha": "abc123",
        "short_sha": "abc123",
        "run_id": "1",
        "run_url": "",
        "published_at": "2026-01-01T00:00:00Z",
        "benchmarks": [{"name": "bench1"}],
    }
    record.update(overrides)
    return record


# --- SCHEMA_VERSION and build_run_summary's published shape ------------------


def test_schema_version_is_2():
    assert perf_data.SCHEMA_VERSION == 2


def test_build_run_summary_key_order_excluding_provenance_key(tmp_path):
    summary = perf_data.build_run_summary(tmp_path, ref_name="main", sha="abc123")

    keys = [key for key in summary if key != perf_data.SAMPLE_PROVENANCE_KEY]

    assert keys == [
        "schema_version",
        "ref_name",
        "ref_slug",
        "sha",
        "short_sha",
        "run_id",
        "run_url",
        "published_at",
        "benchmarks",
    ]


def test_build_run_summary_provenance_field_is_single_sample(tmp_path):
    summary = perf_data.build_run_summary(tmp_path, ref_name="main", sha="abc123")

    assert summary[perf_data.SAMPLE_PROVENANCE_KEY] == perf_data.SAMPLE_PROVENANCE_SINGLE_SAMPLE


def test_build_run_summary_carries_no_gate_eligibility_key(tmp_path):
    summary = perf_data.build_run_summary(tmp_path, ref_name="main", sha="abc123")

    assert not any("gate" in key and "eligib" in key for key in summary)


# --- upgrade_summary(): version 1 -> upgraded, not gate-eligible -------------


def test_upgrade_summary_on_version_1_returns_distinct_object_with_upgraded_shape():
    original = _v1_record()

    upgraded = perf_data.upgrade_summary(original)

    assert upgraded is not original
    assert upgraded["schema_version"] == perf_data.SCHEMA_VERSION
    assert upgraded[perf_data.GATE_ELIGIBLE_KEY] is False
    assert upgraded[perf_data.GATE_ELIGIBLE_REASON_KEY]


def test_upgrade_summary_on_version_1_does_not_mutate_input():
    original = _v1_record()
    before = dict(original)

    perf_data.upgrade_summary(original)

    assert original == before
    assert original["schema_version"] == 1


# --- upgrade_summary(): version 2, both provenance states --------------------


def test_upgrade_summary_on_version_2_multi_sample_clean_is_gate_eligible():
    record = _v1_record(schema_version=2)
    record[perf_data.SAMPLE_PROVENANCE_KEY] = perf_data.SAMPLE_PROVENANCE_MULTI_SAMPLE_CLEAN

    upgraded = perf_data.upgrade_summary(record)

    assert upgraded[perf_data.GATE_ELIGIBLE_KEY] is True


def test_upgrade_summary_on_version_2_single_sample_is_not_gate_eligible():
    record = _v1_record(schema_version=2)
    record[perf_data.SAMPLE_PROVENANCE_KEY] = perf_data.SAMPLE_PROVENANCE_SINGLE_SAMPLE

    upgraded = perf_data.upgrade_summary(record)

    assert upgraded[perf_data.GATE_ELIGIBLE_KEY] is False
    assert upgraded[perf_data.GATE_ELIGIBLE_REASON_KEY] == perf_data.GATE_REASON_SINGLE_SAMPLE_PUBLISHED


def test_upgrade_summary_on_version_2_with_unrecognized_sample_provenance_names_the_provenance():
    record = _v1_record(schema_version=2)
    record[perf_data.SAMPLE_PROVENANCE_KEY] = "not-a-real-provenance"

    upgraded = perf_data.upgrade_summary(record)

    assert upgraded[perf_data.GATE_ELIGIBLE_KEY] is False
    assert upgraded[perf_data.GATE_ELIGIBLE_REASON_KEY] == perf_data.GATE_REASON_UNRECOGNIZED_SAMPLE_PROVENANCE
    assert upgraded[perf_data.GATE_ELIGIBLE_REASON_KEY] != perf_data.GATE_REASON_UNRECOGNIZED_SCHEMA_VERSION


def test_upgrade_summary_on_version_2_with_absent_sample_provenance_names_the_provenance():
    record = _v1_record(schema_version=2)
    assert perf_data.SAMPLE_PROVENANCE_KEY not in record
    before = dict(record)

    upgraded = perf_data.upgrade_summary(record)

    assert upgraded[perf_data.GATE_ELIGIBLE_KEY] is False
    assert upgraded[perf_data.GATE_ELIGIBLE_REASON_KEY] == perf_data.GATE_REASON_UNRECOGNIZED_SAMPLE_PROVENANCE

    # a null provenance value takes the same reason as an absent key.
    null_record = _v1_record(schema_version=2)
    null_record[perf_data.SAMPLE_PROVENANCE_KEY] = None
    null_upgraded = perf_data.upgrade_summary(null_record)
    assert null_upgraded[perf_data.GATE_ELIGIBLE_REASON_KEY] == perf_data.GATE_REASON_UNRECOGNIZED_SAMPLE_PROVENANCE

    # calling upgrade_summary twice over the same record yields equal results and never
    # mutates the record it was given.
    repeat_upgraded = perf_data.upgrade_summary(record)
    assert repeat_upgraded == upgraded
    assert record == before
    assert perf_data.SAMPLE_PROVENANCE_KEY not in record


# --- upgrade_summary(): unrecognized schema_version, never raises -----------


def test_upgrade_summary_on_absent_schema_version_key_is_not_gate_eligible():
    record = _v1_record()
    del record["schema_version"]

    upgraded = perf_data.upgrade_summary(record)

    assert upgraded[perf_data.GATE_ELIGIBLE_KEY] is False
    assert upgraded[perf_data.GATE_ELIGIBLE_REASON_KEY] == perf_data.GATE_REASON_UNRECOGNIZED_SCHEMA_VERSION


def test_upgrade_summary_on_null_schema_version_is_not_gate_eligible():
    record = _v1_record(schema_version=None)

    upgraded = perf_data.upgrade_summary(record)

    assert upgraded[perf_data.GATE_ELIGIBLE_KEY] is False
    assert upgraded[perf_data.GATE_ELIGIBLE_REASON_KEY] == perf_data.GATE_REASON_UNRECOGNIZED_SCHEMA_VERSION


def test_upgrade_summary_on_schema_version_three_is_not_gate_eligible():
    record = _v1_record(schema_version=3)

    upgraded = perf_data.upgrade_summary(record)

    assert upgraded[perf_data.GATE_ELIGIBLE_KEY] is False
    assert upgraded[perf_data.GATE_ELIGIBLE_REASON_KEY] == perf_data.GATE_REASON_UNRECOGNIZED_SCHEMA_VERSION


# --- upgrade_summary(): empty benchmarks list, never raises ------------------


def test_upgrade_summary_on_empty_benchmarks_list_does_not_raise():
    record = _v1_record(benchmarks=[])

    upgraded = perf_data.upgrade_summary(record)

    assert upgraded["benchmarks"] == []


# --- the committed real version 1 fixture ------------------------------------


def test_committed_v1_fixture_has_schema_version_1_and_multiple_benchmarks():
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    assert payload["schema_version"] == 1
    assert len(payload["benchmarks"]) > 1


# --- load_published_summary(): every published read goes through the upgrade path


def test_load_published_summary_from_published_root_upgrades_the_real_v1_fixture(tmp_path):
    relative_path = Path("perf/branches/main/latest.json")
    target = tmp_path / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(FIXTURE_PATH.read_bytes())

    summary = ci_perf_summary.load_published_summary(relative_path, published_root=tmp_path)

    assert summary["schema_version"] == perf_data.SCHEMA_VERSION
    assert summary[perf_data.GATE_ELIGIBLE_KEY] is False


def test_load_published_summary_from_git_ref_upgrades_the_real_v1_fixture(tmp_path, monkeypatch):
    relative_path = Path("perf/branches/main/latest.json")
    target = tmp_path / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(FIXTURE_PATH.read_bytes())

    _run_git(["init", "-q"], cwd=tmp_path)
    _run_git(["config", "user.email", "test@example.com"], cwd=tmp_path)
    _run_git(["config", "user.name", "Test"], cwd=tmp_path)
    _run_git(["add", str(relative_path)], cwd=tmp_path)
    _run_git(["commit", "-q", "-m", "add fixture"], cwd=tmp_path)
    monkeypatch.chdir(tmp_path)

    summary = ci_perf_summary.load_published_summary(relative_path, gh_pages_ref="HEAD")

    assert summary["schema_version"] == perf_data.SCHEMA_VERSION
    assert summary[perf_data.GATE_ELIGIBLE_KEY] is False


# --- render_summary_markdown(): the upgraded real fixture in both positions --


def test_render_summary_markdown_with_upgraded_fixture_as_current_renders_one_row_per_benchmark():
    upgraded = _upgraded_fixture()
    names = [entry["name"] for entry in upgraded["benchmarks"]]

    markdown = ci_perf_summary.render_summary_markdown(
        current_summary=upgraded,
        previous_branch_summary=None,
        main_summary=None,
        pre_release_summary=None,
    )

    for name in names:
        assert markdown.count(f"<code>{name}</code>") == 1
    assert markdown.count("<code>") == len(names)


def test_render_summary_markdown_with_upgraded_fixture_as_baseline_renders_both_sides():
    baseline_upgraded = _upgraded_fixture()
    current_summary = dict(baseline_upgraded)
    current_summary["ref_name"] = "feature-branch"

    markdown = ci_perf_summary.render_summary_markdown(
        current_summary=current_summary,
        previous_branch_summary=baseline_upgraded,
        main_summary=None,
        pre_release_summary=None,
    )

    names = [entry["name"] for entry in baseline_upgraded["benchmarks"]]
    for name in names:
        assert markdown.count(f"<code>{name}</code>") == 1
    assert markdown.count("<code>") == len(names)


def test_benchmark_names_differing_only_in_case_produce_separate_rows_not_merged():
    upgraded = _upgraded_fixture()
    base_entry = upgraded["benchmarks"][0]
    lower_name = base_entry["name"]
    upper_name = lower_name.upper()
    assert lower_name != upper_name

    current_summary = dict(upgraded)
    current_summary["benchmarks"] = [
        dict(base_entry, name=lower_name),
        dict(base_entry, name=upper_name),
    ]
    baseline_summary = dict(upgraded)
    baseline_summary["benchmarks"] = [dict(base_entry, name=lower_name)]

    markdown = ci_perf_summary.render_summary_markdown(
        current_summary=current_summary,
        previous_branch_summary=baseline_summary,
        main_summary=None,
        pre_release_summary=None,
    )

    assert markdown.count(f"<code>{lower_name}</code>") == 1
    assert markdown.count(f"<code>{upper_name}</code>") == 1


def test_render_summary_markdown_with_empty_benchmarks_list_renders_without_raising():
    current_summary = dict(_upgraded_fixture())
    current_summary["benchmarks"] = []

    markdown = ci_perf_summary.render_summary_markdown(
        current_summary=current_summary,
        previous_branch_summary=None,
        main_summary=None,
        pre_release_summary=None,
    )

    assert "<code>" not in markdown
