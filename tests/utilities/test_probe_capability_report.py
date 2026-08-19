# ----------------------------------------------------------------------------
# Title      : Probe Capability Report Tests
# ----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
# ----------------------------------------------------------------------------

from __future__ import annotations

import importlib
import json
import re
import shlex
import statistics
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

probe_capability_report = importlib.import_module("probe_capability_report")


def _write_probe_run(
    root: Path,
    filename: str,
    probe_schema_version: int = 1,
    run: dict | None = None,
    fingerprint: dict | None = None,
    calibration: dict | None = None,
    windows: list | None = None,
    perf_events: dict | None = None,
    instruments: list | None = None,
    interventions: list | None = None,
    confirmation: dict | None = None,
) -> Path:
    payload = {
        "probe_schema_version": probe_schema_version,
        "run": run
        or {
            "job_index": 1,
            "github_run_id": "123",
            "github_run_attempt": "1",
            "github_sha": "abc123",
            "git_tree_hash": "deadbeef",
            "campaign_branch": "perf-probe/campaign",
            "runner_os": "Linux",
        },
        "fingerprint": fingerprint
        or {
            "cpu_model": "AMD EPYC 7763 64-Core Processor",
            "cpu_mhz": 2445.406,
            "nproc": 4,
            "kernel_version": "6.17.0-1022-azure",
            "glibc_version": "2.39",
            "cpython_version": "3.12.3",
            "compiler_version": "gcc (fake) 13.2.0",
            "memory_total_bytes": 16777216000,
            "cgroup_v2_cpu_stat": {"nr_periods": 0, "nr_throttled": 0, "throttled_usec": 0},
            "cgroup_v2_cpu_max": "max 100000",
            "systemd_timers": [],
            "runner_image_version": "20260810.271.1",
            "fingerprint_schema_version": 1,
            "errors": [],
        },
        "calibration": calibration if calibration is not None else {},
        "windows": windows if windows is not None else [],
        "perf_events": perf_events if perf_events is not None else {},
        "instruments": instruments if instruments is not None else [],
        "interventions": interventions if interventions is not None else [],
        "confirmation": confirmation if confirmation is not None else {},
        "build": {},
        "errors": [],
    }
    path = root / filename
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _perf_event_entry(
    event: str = "cycles",
    event_class: str = "hardware",
    paranoid_state: str = "default",
    status: str = "counted",
    value: int = 58235,
    raw_line: str = "58,235      cycles",
    gating_eligible: bool = True,
    reason: str | None = None,
) -> dict:
    return {
        "event": event,
        "event_class": event_class,
        "paranoid_state": paranoid_state,
        "paranoid_value": 4,
        "status": status,
        "value": value,
        "raw_line": raw_line,
        "gating_eligible": gating_eligible,
        "reason": reason,
    }


def _instrument_entry(
    name: str = "strace",
    available: bool = True,
    overhead_multiplier: float = 3.65,
    repeats: int = 7,
    repeatability_verdict: str = "bit-identical",
    verdict: str = "usable",
    overhead_disqualify_threshold: float = 5.0,
) -> dict:
    return {
        "name": name,
        "available": available,
        "repeats": repeats,
        "overhead_multiplier": overhead_multiplier,
        "repeatability": {"verdict": repeatability_verdict, "n": repeats},
        "verdict": verdict,
        "overhead_disqualify_threshold": overhead_disqualify_threshold,
    }


def _confirmation_instrument_entry(
    status: str = "ok",
    repeats: int = 3,
    repeatability_verdict: str = "bit-identical",
    repeatability_n: int | None = None,
    reason: str | None = None,
) -> dict:
    """Build one `confirmation.modules[*].instruments[*]` entry the way
    `_instrument_entry()` builds a sweep entry, so confirmation-leg tests
    read like the existing instrument-sweep tests.
    """
    if status == "skipped":
        return {
            "status": "skipped",
            "reason": reason if reason is not None else "overhead-disqualifies",
        }
    entry: dict = {"status": status, "repeats": repeats}
    entry["repeatability"] = {
        "verdict": repeatability_verdict,
        "n": repeatability_n if repeatability_n is not None else repeats,
    }
    return entry


def _confirmation_payload(modules: dict, excluded_instruments: dict | None = None) -> dict:
    return {
        "results_dir": "/tmp/confirmation-perf-results",
        "excluded_instruments": excluded_instruments if excluded_instruments is not None else {},
        "modules": modules,
    }


def test_load_probe_run_accepts_valid_record(tmp_path):
    path = _write_probe_run(tmp_path, "run-1.json")
    record = probe_capability_report.load_probe_run(path)

    assert record is not None
    assert record["probe_schema_version"] == 1


def test_load_probe_run_rejects_malformed_json(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{not valid json", encoding="utf-8")

    assert probe_capability_report.load_probe_run(path) is None


def test_load_probe_run_rejects_unrecognized_schema_version(tmp_path):
    path = _write_probe_run(tmp_path, "run.json", probe_schema_version=99)

    assert probe_capability_report.load_probe_run(path) is None


def test_load_probe_run_rejects_non_dict_payload(tmp_path):
    path = tmp_path / "list.json"
    path.write_text("[1, 2, 3]", encoding="utf-8")

    assert probe_capability_report.load_probe_run(path) is None


def test_main_skips_and_counts_malformed_record(tmp_path):
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    _write_probe_run(runs_dir, "good-1.json")
    (runs_dir / "bad.json").write_text("not json", encoding="utf-8")
    out_md = tmp_path / "out.md"
    out_json = tmp_path / "out.json"

    exit_code = probe_capability_report.main(
        [
            "--runs-dir", str(runs_dir),
            "--out-md", str(out_md),
            "--out-json", str(out_json),
        ]
    )

    assert exit_code == 0
    sidecar = json.loads(out_json.read_text(encoding="utf-8"))
    assert sidecar["source"]["record_count"] == 1
    assert sidecar["source"]["records_skipped"] == 1


def test_main_returns_failure_when_no_records_parsed(tmp_path):
    runs_dir = tmp_path / "empty-runs"
    runs_dir.mkdir()

    exit_code = probe_capability_report.main(
        [
            "--runs-dir", str(runs_dir),
            "--out-md", str(tmp_path / "m.md"),
            "--out-json", str(tmp_path / "s.json"),
        ]
    )

    assert exit_code == 1


def test_aggregator_is_byte_stable_across_two_runs(tmp_path):
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    _write_probe_run(runs_dir, "good-1.json")
    _write_probe_run(
        runs_dir,
        "good-2.json",
        run={
            "job_index": 2,
            "github_run_id": "124",
            "github_run_attempt": "1",
            "github_sha": "def456",
            "git_tree_hash": "deadbeef",
            "campaign_branch": "perf-probe/campaign",
            "runner_os": "Linux",
        },
        fingerprint={
            "cpu_model": "Intel(R) Xeon(R) Platinum 8272CL",
            "cpu_mhz": 2596.994,
            "nproc": 4,
            "kernel_version": "6.17.0-1022-azure",
            "glibc_version": "2.39",
            "cpython_version": "3.12.3",
            "compiler_version": "gcc (fake) 13.2.0",
            "memory_total_bytes": 16777216000,
            "cgroup_v2_cpu_stat": {},
            "cgroup_v2_cpu_max": "max 100000",
            "systemd_timers": [],
            "runner_image_version": "20260810.271.1",
            "fingerprint_schema_version": 1,
            "errors": [],
        },
    )

    out_md1, out_json1 = tmp_path / "m1.md", tmp_path / "s1.json"
    out_md2, out_json2 = tmp_path / "m2.md", tmp_path / "s2.json"

    probe_capability_report.main(
        ["--runs-dir", str(runs_dir), "--out-md", str(out_md1), "--out-json", str(out_json1)]
    )
    probe_capability_report.main(
        ["--runs-dir", str(runs_dir), "--out-md", str(out_md2), "--out-json", str(out_json2)]
    )

    assert out_md1.read_bytes() == out_md2.read_bytes()
    assert out_json1.read_bytes() == out_json2.read_bytes()


def test_markdown_starts_with_do_not_edit_banner_naming_the_script(tmp_path):
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    _write_probe_run(runs_dir, "good-1.json")
    out_md = tmp_path / "out.md"
    out_json = tmp_path / "out.json"

    probe_capability_report.main(
        ["--runs-dir", str(runs_dir), "--out-md", str(out_md), "--out-json", str(out_json)]
    )

    first_line = out_md.read_text(encoding="utf-8").splitlines()[0]
    assert "probe_capability_report.py" in first_line
    assert "do not edit" in first_line.lower()


def test_write_deterministic_json_sorts_keys_and_ends_with_newline(tmp_path):
    path = tmp_path / "out.json"
    probe_capability_report.write_deterministic_json(path, {"b": 1, "a": 2})

    text = path.read_text(encoding="utf-8")
    assert text.endswith("\n")
    assert text.index('"a"') < text.index('"b"')


# --- build_perf_event_section ---------------------------------------------


def test_build_perf_event_section_inconsistent_status_reports_per_status_counts():
    records = [
        {
            "_run_id": "run-1",
            "perf_events": {"events": [
                _perf_event_entry(paranoid_state="default", status="counted"),
                _perf_event_entry(paranoid_state="lowered", status="counted"),
            ]},
        },
        {
            "_run_id": "run-2",
            "perf_events": {"events": [
                _perf_event_entry(
                    paranoid_state="default", status="not-supported", value=None,
                    gating_eligible=False, reason="not counted in either paranoid state",
                ),
                _perf_event_entry(
                    paranoid_state="lowered", status="not-supported", value=None,
                    gating_eligible=False, reason="not counted in either paranoid state",
                ),
            ]},
        },
        {
            "_run_id": "run-3",
            "perf_events": {"events": [
                _perf_event_entry(paranoid_state="default", status="counted"),
                _perf_event_entry(paranoid_state="lowered", status="counted"),
            ]},
        },
    ]

    section = probe_capability_report.build_perf_event_section(records, min_n=3)

    assert len(section) == 1
    entry = section[0]
    assert entry["default_status_tally"] == {"counted": 2, "not-supported": 1}
    assert "status" not in entry


def test_build_perf_event_section_below_min_n_suppresses_gating_verdict():
    records = [
        {
            "_run_id": "run-1",
            "perf_events": {"events": [_perf_event_entry(paranoid_state="default", status="counted")]},
        },
    ]

    section = probe_capability_report.build_perf_event_section(records, min_n=3)

    assert len(section) == 1
    entry = section[0]
    assert entry["gating_eligible"] == probe_capability_report.INSUFFICIENT_SAMPLES
    assert entry["default_status_tally"] == {"counted": 1}


def test_build_perf_event_section_retains_one_raw_line_as_evidence():
    records = [
        {
            "_run_id": "run-1",
            "perf_events": {"events": [
                _perf_event_entry(paranoid_state="default", raw_line="58,235      cycles"),
            ]},
        },
    ]

    section = probe_capability_report.build_perf_event_section(records, min_n=1)

    assert section[0]["evidence_raw_line"] == "58,235      cycles"


# --- build_instrument_section ----------------------------------------------


def test_build_instrument_section_identical_multiplier_both_entries_retained_by_name():
    records = [
        {
            "_run_id": "run-1",
            "instruments": [
                _instrument_entry(name="malloc_interposer", overhead_multiplier=1.03),
                _instrument_entry(name="getrusage", overhead_multiplier=1.03),
            ],
        },
    ]

    section = probe_capability_report.build_instrument_section(records, min_n=1)

    names = [entry["name"] for entry in section]
    assert names == sorted(names)
    assert {"malloc_interposer", "getrusage"}.issubset(set(names))


def test_build_instrument_section_zero_usable_samples_renders_sentinel():
    records = [
        {
            "_run_id": "run-1",
            "instruments": [_instrument_entry(name="perf_software_events", available=False)],
        },
    ]
    records[0]["instruments"][0]["overhead_multiplier"] = "unavailable"

    section = probe_capability_report.build_instrument_section(records, min_n=1)

    entry = section[0]
    assert entry["overhead_multiplier_median"] == probe_capability_report.INSUFFICIENT_SAMPLES
    assert entry["overhead_multiplier_n"] == 0


def test_build_instrument_section_records_disqualifying_threshold():
    records = [
        {"_run_id": "run-1", "instruments": [_instrument_entry(name="callgrind", overhead_disqualify_threshold=5.0)]},
    ]

    section = probe_capability_report.build_instrument_section(records, min_n=1)

    assert section[0]["overhead_disqualify_threshold"] == 5.0


# --- build_confirmation_section ---------------------------------------------


def test_build_confirmation_section_per_module_repeatability_tallies():
    records = [
        {
            "_run_id": "run-1",
            "confirmation": _confirmation_payload({
                "tests/perf/test_stream_bridge_perf.py": {
                    "instruments": {
                        "malloc_interposer": _confirmation_instrument_entry(repeatability_verdict="unstable"),
                    },
                },
                "tests/perf/test_variable_rate_perf.py": {
                    "instruments": {
                        "malloc_interposer": _confirmation_instrument_entry(repeatability_verdict="bit-identical"),
                    },
                },
            }),
        },
        {
            "_run_id": "run-2",
            "confirmation": _confirmation_payload({
                "tests/perf/test_stream_bridge_perf.py": {
                    "instruments": {
                        "malloc_interposer": _confirmation_instrument_entry(repeatability_verdict="unstable"),
                    },
                },
                "tests/perf/test_variable_rate_perf.py": {
                    "instruments": {
                        "malloc_interposer": _confirmation_instrument_entry(repeatability_verdict="unstable"),
                    },
                },
            }),
        },
    ]

    section = probe_capability_report.build_confirmation_section(records, min_n=3)

    stream_entry = next(
        item for item in section["per_module"]
        if item["module"] == "tests/perf/test_stream_bridge_perf.py" and item["instrument"] == "malloc_interposer"
    )
    variable_entry = next(
        item for item in section["per_module"]
        if item["module"] == "tests/perf/test_variable_rate_perf.py" and item["instrument"] == "malloc_interposer"
    )

    assert stream_entry["repeatability_verdict_tally"] == {"unstable": 2}
    assert variable_entry["repeatability_verdict_tally"] == {"bit-identical": 1, "unstable": 1}


def test_build_confirmation_section_skipped_instrument_reports_status_and_reason_not_exercised():
    records = [
        {
            "_run_id": "run-1",
            "confirmation": _confirmation_payload({
                "tests/perf/test_stream_bridge_perf.py": {
                    "instruments": {
                        "resource_usage": _confirmation_instrument_entry(
                            status="skipped",
                            reason="cannot observe allocations or resource usage inside a separate pytest subprocess",
                        ),
                    },
                },
            }),
        },
    ]

    section = probe_capability_report.build_confirmation_section(records, min_n=3)

    entry = section["per_module"][0]
    assert entry["status_tally"] == {"skipped": 1}
    assert entry["skip_reasons"] == [
        "cannot observe allocations or resource usage inside a separate pytest subprocess",
    ]
    assert entry["admission"] == probe_capability_report.DERIVED_ADMISSION_NOT_EXERCISED
    assert section["by_instrument"]["resource_usage"]["admission"] == (
        probe_capability_report.DERIVED_ADMISSION_NOT_EXERCISED
    )
    assert section["by_instrument"]["resource_usage"]["modules"] == []


def test_build_confirmation_section_all_failed_reports_failed_status_and_insufficient_samples():
    records = [
        {
            "_run_id": "run-1",
            "confirmation": _confirmation_payload({
                "tests/perf/test_stream_bridge_perf.py": {
                    "instruments": {
                        "perf_software_events": {
                            "status": "failed",
                            "repeats": 3,
                            "repeatability": {"verdict": "insufficient-samples", "n": 0},
                        },
                    },
                },
            }),
        },
    ]

    section = probe_capability_report.build_confirmation_section(records, min_n=3)

    entry = section["per_module"][0]
    assert entry["status_tally"] == {"failed": 1}
    assert entry["repeatability_verdict_tally"] == {"insufficient-samples": 1}
    assert entry["admission"] == probe_capability_report.INSUFFICIENT_SAMPLES
    assert entry["admission"] != probe_capability_report.DERIVED_ADMISSION_NOT_EXERCISED
    assert entry["admission"] != probe_capability_report.DERIVED_ADMISSION_INELIGIBLE


def test_build_confirmation_section_admission_marker_ineligible_when_any_module_unstable():
    records = [
        {
            "_run_id": "run-1",
            "confirmation": _confirmation_payload({
                "tests/perf/test_stream_bridge_perf.py": {
                    "instruments": {
                        "malloc_interposer": _confirmation_instrument_entry(repeatability_verdict="unstable"),
                    },
                },
                "tests/perf/test_variable_rate_perf.py": {
                    "instruments": {
                        "malloc_interposer": _confirmation_instrument_entry(repeatability_verdict="bit-identical"),
                    },
                },
            }),
        },
    ]

    section = probe_capability_report.build_confirmation_section(records, min_n=3)

    assert section["by_instrument"]["malloc_interposer"]["admission"] == (
        probe_capability_report.DERIVED_ADMISSION_INELIGIBLE
    )


def test_build_confirmation_section_admission_marker_eligible_only_when_no_module_unstable():
    records = [
        {
            "_run_id": "run-1",
            "confirmation": _confirmation_payload({
                "tests/perf/test_variable_rate_perf.py": {
                    "instruments": {
                        "resource_usage": _confirmation_instrument_entry(repeatability_verdict="bit-identical"),
                    },
                },
            }),
        },
    ]

    section = probe_capability_report.build_confirmation_section(records, min_n=3)

    assert section["by_instrument"]["resource_usage"]["admission"] == (
        probe_capability_report.DERIVED_ADMISSION_ELIGIBLE
    )


def test_build_confirmation_section_excluded_instruments_deduplicated_across_population():
    records = [
        {
            "_run_id": "run-1",
            "confirmation": _confirmation_payload(
                {},
                excluded_instruments={"callgrind": "too expensive to point at real code"},
            ),
        },
        {
            "_run_id": "run-2",
            "confirmation": _confirmation_payload(
                {},
                excluded_instruments={"callgrind": "too expensive to point at real code"},
            ),
        },
    ]

    section = probe_capability_report.build_confirmation_section(records, min_n=3)

    assert section["excluded_instruments"] == {"callgrind": ["too expensive to point at real code"]}


def test_build_confirmation_section_malformed_confirmation_values_do_not_raise():
    records = [
        {"_run_id": "run-1"},
        {"_run_id": "run-2", "confirmation": {}},
        {"_run_id": "run-3", "confirmation": ["not", "a", "dict"]},
        {"_run_id": "run-4", "confirmation": None},
    ]

    section = probe_capability_report.build_confirmation_section(records, min_n=3)

    assert section["per_module"] == []
    assert section["by_instrument"] == {}
    assert section["excluded_instruments"] == {}


def test_build_confirmation_section_rows_ordered_by_module_then_instrument():
    records = [
        {
            "_run_id": "run-1",
            "confirmation": _confirmation_payload({
                "tests/perf/test_variable_rate_perf.py": {
                    "instruments": {
                        "resource_usage": _confirmation_instrument_entry(),
                        "malloc_interposer": _confirmation_instrument_entry(),
                    },
                },
                "tests/perf/test_stream_bridge_perf.py": {
                    "instruments": {
                        "malloc_interposer": _confirmation_instrument_entry(),
                    },
                },
            }),
        },
    ]

    section = probe_capability_report.build_confirmation_section(records, min_n=3)

    pairs = [(item["module"], item["instrument"]) for item in section["per_module"]]
    assert pairs == sorted(pairs)
    assert list(section["by_instrument"].keys()) == sorted(section["by_instrument"].keys())


def test_build_confirmation_section_matches_real_committed_population_counts():
    runs_dir = REPO_ROOT / "docs" / "plans" / "perf-ci-hardening" / "probe-runs"
    population = probe_capability_report.build_population(
        sorted(runs_dir.glob("*.json")),
        "23ab89659eaccfa80215bba03e6a02f6152c3555",
    )
    records = population["accepted"]
    assert len(records) == 20

    section = probe_capability_report.build_confirmation_section(records, min_n=3)

    stream_entry = next(
        item for item in section["per_module"]
        if item["module"] == "tests/perf/test_stream_bridge_perf.py" and item["instrument"] == "malloc_interposer"
    )
    variable_entry = next(
        item for item in section["per_module"]
        if item["module"] == "tests/perf/test_variable_rate_perf.py" and item["instrument"] == "malloc_interposer"
    )

    assert stream_entry["repeatability_verdict_tally"] == {"unstable": 20}
    assert variable_entry["repeatability_verdict_tally"] == {"bit-identical": 14, "unstable": 6}
    assert section["by_instrument"]["malloc_interposer"]["admission"] == (
        probe_capability_report.DERIVED_ADMISSION_INELIGIBLE
    )
    assert section["by_instrument"]["strace"]["admission"] == (
        probe_capability_report.DERIVED_ADMISSION_NOT_EXERCISED
    )
    assert "callgrind" in section["excluded_instruments"]


def _window(
    label: str = "w1",
    steal_fraction: float = 0.02,
    steal_flagged: bool = True,
    steal_threshold: float = 0.01,
    steal_comparison: str = ">=",
    cgroup_nr_periods_delta: int = 10,
    cgroup_nr_throttled_delta: int = 1,
    cgroup_throttled_usec_delta: int = 500,
) -> dict:
    return {
        "label": label,
        "steal_fraction": steal_fraction,
        "steal_flagged": steal_flagged,
        "steal_threshold": steal_threshold,
        "steal_comparison": steal_comparison,
        "cgroup_nr_periods_delta": cgroup_nr_periods_delta,
        "cgroup_nr_throttled_delta": cgroup_nr_throttled_delta,
        "cgroup_throttled_usec_delta": cgroup_throttled_usec_delta,
    }


# --- rendering: confirmation section and Instruments cross-reference -------


def test_render_confirmation_section_header_appears_exactly_once(tmp_path):
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    _write_probe_run(runs_dir, "good.json")
    out_md, out_json = tmp_path / "out.md", tmp_path / "out.json"

    probe_capability_report.main(
        ["--runs-dir", str(runs_dir), "--out-md", str(out_md), "--out-json", str(out_json)]
    )

    text = out_md.read_text(encoding="utf-8")
    assert text.count("## Confirmation leg: repeatability against real modules") == 1


def test_render_confirmation_section_names_both_confirmation_modules(tmp_path):
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    _write_probe_run(
        runs_dir, "good.json",
        confirmation=_confirmation_payload({
            "tests/perf/test_stream_bridge_perf.py": {
                "instruments": {
                    "malloc_interposer": _confirmation_instrument_entry(repeatability_verdict="unstable"),
                },
            },
            "tests/perf/test_variable_rate_perf.py": {
                "instruments": {
                    "malloc_interposer": _confirmation_instrument_entry(repeatability_verdict="bit-identical"),
                },
            },
        }),
    )
    out_md, out_json = tmp_path / "out.md", tmp_path / "out.json"

    probe_capability_report.main(
        ["--runs-dir", str(runs_dir), "--out-md", str(out_md), "--out-json", str(out_json)]
    )

    section_start = out_md.read_text(encoding="utf-8").index("## Confirmation leg")
    section_text = out_md.read_text(encoding="utf-8")[section_start:]
    assert "tests/perf/test_stream_bridge_perf.py" in section_text
    assert "tests/perf/test_variable_rate_perf.py" in section_text


def test_instruments_table_malloc_interposer_row_shows_recorded_and_confirmation_evidence(tmp_path):
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    _write_probe_run(
        runs_dir, "good.json",
        instruments=[_instrument_entry(name="malloc_interposer", verdict="usable")],
        confirmation=_confirmation_payload({
            "tests/perf/test_stream_bridge_perf.py": {
                "instruments": {
                    "malloc_interposer": _confirmation_instrument_entry(repeatability_verdict="unstable"),
                },
            },
        }),
    )
    out_md, out_json = tmp_path / "out.md", tmp_path / "out.json"

    probe_capability_report.main(
        ["--runs-dir", str(runs_dir), "--out-md", str(out_md), "--out-json", str(out_json)]
    )

    lines = out_md.read_text(encoding="utf-8").splitlines()
    header_index = next(i for i, line in enumerate(lines) if line.startswith("| Instrument |"))
    header_line = lines[header_index]
    row_line = next(line for line in lines if line.startswith("| malloc_interposer"))

    assert "usable" in row_line
    assert "unstable" in row_line
    assert header_line.count("|") == row_line.count("|")


def test_instruments_table_every_row_matches_header_cell_count(tmp_path):
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    _write_probe_run(
        runs_dir, "good.json",
        instruments=[
            _instrument_entry(name="strace"),
            _instrument_entry(name="callgrind"),
        ],
        confirmation=_confirmation_payload({
            "tests/perf/test_stream_bridge_perf.py": {
                "instruments": {"strace": _confirmation_instrument_entry(status="skipped")},
            },
        }, excluded_instruments={"callgrind": "too expensive to point at real code"}),
    )
    out_md, out_json = tmp_path / "out.md", tmp_path / "out.json"

    probe_capability_report.main(
        ["--runs-dir", str(runs_dir), "--out-md", str(out_md), "--out-json", str(out_json)]
    )

    lines = out_md.read_text(encoding="utf-8").splitlines()
    header_index = next(i for i, line in enumerate(lines) if line.startswith("| Instrument |"))
    header_line = lines[header_index]
    data_lines = []
    for line in lines[header_index + 2:]:
        if not line.startswith("|"):
            break
        data_lines.append(line)

    for row_line in data_lines:
        assert row_line.count("|") == header_line.count("|")


def test_instruments_table_skipped_confirmation_instrument_shows_not_exercised(tmp_path):
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    _write_probe_run(
        runs_dir, "good.json",
        instruments=[_instrument_entry(name="callgrind")],
        confirmation=_confirmation_payload(
            {}, excluded_instruments={"callgrind": "too expensive to point at real code"},
        ),
    )
    out_md, out_json = tmp_path / "out.md", tmp_path / "out.json"

    probe_capability_report.main(
        ["--runs-dir", str(runs_dir), "--out-md", str(out_md), "--out-json", str(out_json)]
    )

    row_line = next(
        line for line in out_md.read_text(encoding="utf-8").splitlines()
        if line.startswith("| callgrind")
    )
    assert probe_capability_report.DERIVED_ADMISSION_NOT_EXERCISED in row_line


def test_build_instrument_section_verdict_tally_unchanged_by_confirmation_wiring():
    """Guards T-02-11-01: build_instrument_section() must keep tallying only the
    recorded verdict field, exactly as it did before this plan, regardless of
    whatever confirmation evidence a record also carries.
    """
    records = [
        {
            "_run_id": "run-1",
            "instruments": [_instrument_entry(name="malloc_interposer", verdict="usable")],
            "confirmation": _confirmation_payload({
                "tests/perf/test_stream_bridge_perf.py": {
                    "instruments": {
                        "malloc_interposer": _confirmation_instrument_entry(repeatability_verdict="unstable"),
                    },
                },
            }),
        },
    ]

    section = probe_capability_report.build_instrument_section(records, min_n=1)

    assert section[0]["verdict_tally"] == {"usable": 1}


def test_build_instrument_section_verdict_tally_over_real_population_unchanged_by_this_plan():
    """The plan's own acceptance bar: build_instrument_section()'s recorded verdict
    tally over the twenty committed records must be byte-for-byte what it was before
    confirmation-leg wiring existed, since this plan must never rewrite a verdict any
    probe run actually recorded.
    """
    runs_dir = REPO_ROOT / "docs" / "plans" / "perf-ci-hardening" / "probe-runs"
    population = probe_capability_report.build_population(
        sorted(runs_dir.glob("*.json")),
        "23ab89659eaccfa80215bba03e6a02f6152c3555",
    )
    records = population["accepted"]
    assert len(records) == 20

    section = probe_capability_report.build_instrument_section(records, min_n=3)

    malloc_entry = next(item for item in section if item["name"] == "malloc_interposer")
    assert malloc_entry["verdict_tally"] == {"usable": 20}
    assert malloc_entry["repeatability_verdict_tally"] == {"insufficient-samples": 20}


def test_confirmation_and_instrument_sections_byte_stable_across_two_invocations(tmp_path):
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    _write_probe_run(
        runs_dir, "good.json",
        instruments=[_instrument_entry(name="malloc_interposer")],
        confirmation=_confirmation_payload({
            "tests/perf/test_stream_bridge_perf.py": {
                "instruments": {
                    "malloc_interposer": _confirmation_instrument_entry(repeatability_verdict="unstable"),
                },
            },
        }),
    )
    out_md1, out_json1 = tmp_path / "m1.md", tmp_path / "s1.json"
    out_md2, out_json2 = tmp_path / "m2.md", tmp_path / "s2.json"

    probe_capability_report.main(
        ["--runs-dir", str(runs_dir), "--out-md", str(out_md1), "--out-json", str(out_json1)]
    )
    probe_capability_report.main(
        ["--runs-dir", str(runs_dir), "--out-md", str(out_md2), "--out-json", str(out_json2)]
    )

    assert out_md1.read_bytes() == out_md2.read_bytes()
    assert out_json1.read_bytes() == out_json2.read_bytes()


# --- build_steal_section ----------------------------------------------------


def test_build_steal_section_zero_windows_renders_sentinel_and_no_distribution():
    records = [{"_run_id": "run-1", "windows": []}]

    section = probe_capability_report.build_steal_section(records, min_n=1)

    assert section["status"] == probe_capability_report.ZERO_WINDOWS
    assert section["window_count"] == 0
    assert section["steal"] is None
    assert section["cgroup_throttling"] is None


def test_build_steal_section_tied_steal_values_ordered_deterministically():
    records = [
        {"_run_id": "run-1", "windows": [
            _window(label="zeta", steal_fraction=0.05),
            _window(label="alpha", steal_fraction=0.05),
        ]},
    ]

    section = probe_capability_report.build_steal_section(records, min_n=1)

    # order_windows tie-breaks on label; alpha sorts before zeta.
    assert section["steal"]["samples"] == [0.05, 0.05]


def test_build_steal_section_never_combines_steal_and_cgroup_figures():
    records = [{"_run_id": "run-1", "windows": [_window()]}]

    section = probe_capability_report.build_steal_section(records, min_n=1)

    steal_keys = set(section["steal"].keys())
    cgroup_keys = set(section["cgroup_throttling"].keys())
    assert steal_keys.isdisjoint(cgroup_keys)
    assert "cgroup_nr_periods_delta" not in section["steal"]
    assert "steal_fraction" not in section["cgroup_throttling"]


# --- build_calibration_section ----------------------------------------------


def _calibration_record(run_id: str, cpu_model: str, tsc_hz: float, samples: dict) -> dict:
    components = {
        name: {"value": statistics.median(vals), "samples": vals}
        for name, vals in samples.items()
    }
    components.setdefault("tsc", {"value": tsc_hz, "samples": [tsc_hz]})
    return {
        "_run_id": run_id,
        "fingerprint": {"cpu_model": cpu_model},
        "calibration": {"components": components},
    }


def test_build_calibration_section_reports_within_and_across_host_with_separate_counts():
    records = [
        _calibration_record("run-1", "AMD EPYC 7763", 2.445e9, {"alu": [1.0, 1.1, 0.9]}),
        _calibration_record("run-2", "AMD EPYC 7763", 2.445e9, {"alu": [1.2, 1.0, 1.1]}),
        _calibration_record("run-3", "Intel Xeon 8272CL", 2.597e9, {"alu": [2.0, 2.1, 1.9]}),
    ]

    section = probe_capability_report.build_calibration_section(records, min_n=3)

    alu = section["alu"]
    assert alu["within_host"]["n"] == 9
    assert alu["across_host"]["n"] == 2


def test_build_calibration_section_single_host_model_suppresses_across_host():
    records = [
        _calibration_record("run-1", "AMD EPYC 7763", 2.445e9, {"memcpy": [10.0, 11.0, 9.0]}),
    ]

    section = probe_capability_report.build_calibration_section(records, min_n=3)

    across = section["memcpy"]["across_host"]
    assert across["cv"] == probe_capability_report.INSUFFICIENT_SAMPLES


# --- build_intervention_section ---------------------------------------------


def _intervention_entry(
    name: str = "taskset",
    status: str = "measured",
    baseline_1: float = 100.0,
    baseline_2: float = 101.0,
    drift_ratio: float = 0.01,
    drift_threshold: float = 0.10,
    contaminated: bool = False,
    effect_ratio=1.05,
    reason: str | None = None,
) -> dict:
    if status == "not_applicable":
        return {
            "intervention": name,
            "status": "not_applicable",
            "reason": reason,
            "effect_ratio": "not_applicable",
        }
    return {
        "intervention": name,
        "status": "measured",
        "baseline_1": baseline_1,
        "baseline_2": baseline_2,
        "drift_ratio": drift_ratio,
        "drift_threshold": drift_threshold,
        "contaminated": contaminated,
        "effect_ratio": "contaminated" if contaminated else effect_ratio,
    }


def test_build_intervention_section_contaminated_renders_sentinel_no_effect_ratio():
    records = [{"_run_id": "run-1", "interventions": [_intervention_entry(contaminated=True)]}]

    section = probe_capability_report.build_intervention_section(records, min_n=1)

    entry = section[0]
    assert entry["effect_ratio"] == probe_capability_report.CONTAMINATED
    assert entry["contaminated_count"] == 1


def test_build_intervention_section_not_applicable_renders_reason_no_numeric_effect():
    records = [{"_run_id": "run-1", "interventions": [
        _intervention_entry(name="service_stop", status="not_applicable", reason="no observed units supplied"),
    ]}]

    section = probe_capability_report.build_intervention_section(records, min_n=1)

    entry = section[0]
    assert entry["not_applicable_reasons"] == ["no observed units supplied"]
    assert not isinstance(entry["effect_ratio"], (int, float))


def test_build_intervention_section_name_sorted_order():
    records = [{"_run_id": "run-1", "interventions": [
        _intervention_entry(name="taskset"),
        _intervention_entry(name="service_stop"),
    ]}]

    section = probe_capability_report.build_intervention_section(records, min_n=1)

    names = [entry["intervention"] for entry in section]
    assert names == sorted(names)


# --- fingerprint columns: cgroup v2 cpu.stat and systemd timer state -------


def _fingerprint(**overrides) -> dict:
    base = {
        "cpu_model": "AMD EPYC 7763 64-Core Processor",
        "cpu_mhz": 2445.406,
        "nproc": 4,
        "kernel_version": "6.17.0-1022-azure",
        "glibc_version": "2.39",
        "cpython_version": "3.12.3",
        "compiler_version": "gcc (fake) 13.2.0",
        "memory_total_bytes": 16777216000,
        "cgroup_v2_cpu_stat": {"nr_periods": 0, "nr_throttled": 0, "throttled_usec": 0},
        "cgroup_v2_cpu_max": "max 100000",
        "systemd_timers": [],
        "runner_image_version": "20260810.271.1",
        "fingerprint_schema_version": 1,
        "errors": [],
    }
    base.update(overrides)
    return base


def _timer_line(unit: str, service: str | None = None) -> str:
    service = service if service is not None else unit.replace(".timer", ".service")
    return f"Sun 2026-08-16 02:47:53 UTC 3min 22s - - {unit} {service}"


def _row_cells(line: str) -> list[str]:
    """Split one rendered fingerprint-table row into its individual cells,
    stripped of surrounding whitespace, so a test can index a specific
    column by FINGERPRINT_COLUMNS position rather than substring-search the
    whole line.
    """
    return [part.strip() for part in line.split("|")[1:-1]]


def _fingerprint_column_cell(row_line: str, key: str) -> str:
    keys = [k for k, _ in probe_capability_report.FINGERPRINT_COLUMNS]
    # cells[0] is the run id; column N's value is at cells[1 + N].
    return _row_cells(row_line)[1 + keys.index(key)]


def test_fingerprint_columns_include_cgroup_and_systemd_state_between_memory_and_runner_image():
    keys = [key for key, _ in probe_capability_report.FINGERPRINT_COLUMNS]

    assert "cgroup_v2_cpu_stat" in keys
    assert "systemd_timers" in keys
    memory_index = keys.index("memory_total_bytes")
    runner_image_index = keys.index("runner_image_version")
    assert memory_index < keys.index("cgroup_v2_cpu_stat") < runner_image_index
    assert memory_index < keys.index("systemd_timers") < runner_image_index


def test_render_markdown_cgroup_column_compacts_throttling_counters(tmp_path):
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    _write_probe_run(
        runs_dir, "good.json",
        fingerprint=_fingerprint(cgroup_v2_cpu_stat={
            "nr_periods": 42, "nr_throttled": 3, "throttled_usec": 987, "usage_usec": 111,
        }),
    )
    out_md, out_json = tmp_path / "out.md", tmp_path / "out.json"

    probe_capability_report.main(
        ["--runs-dir", str(runs_dir), "--out-md", str(out_md), "--out-json", str(out_json)]
    )

    text = out_md.read_text(encoding="utf-8")
    assert "nr_periods: 42" in text
    assert "nr_throttled: 3" in text
    assert "throttled_usec: 987" in text
    assert "usage_usec: 111" not in text  # compact cell reports only the three throttling counters


def test_render_markdown_cgroup_column_renders_missing_sentinel_for_absent_field(tmp_path):
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    fingerprint = _fingerprint()
    del fingerprint["cgroup_v2_cpu_stat"]
    _write_probe_run(runs_dir, "good.json", fingerprint=fingerprint)
    out_md, out_json = tmp_path / "out.md", tmp_path / "out.json"

    probe_capability_report.main(
        ["--runs-dir", str(runs_dir), "--out-md", str(out_md), "--out-json", str(out_json)]
    )

    row_line = next(
        line for line in out_md.read_text(encoding="utf-8").splitlines() if line.startswith("| good")
    )
    assert _fingerprint_column_cell(row_line, "cgroup_v2_cpu_stat") == probe_capability_report.MISSING_FIELD


def test_render_markdown_cgroup_column_renders_unreadable_sentinel_verbatim(tmp_path):
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    _write_probe_run(runs_dir, "good.json", fingerprint=_fingerprint(cgroup_v2_cpu_stat="unavailable"))
    out_md, out_json = tmp_path / "out.md", tmp_path / "out.json"

    probe_capability_report.main(
        ["--runs-dir", str(runs_dir), "--out-md", str(out_md), "--out-json", str(out_json)]
    )

    row_line = next(
        line for line in out_md.read_text(encoding="utf-8").splitlines() if line.startswith("| good")
    )
    assert _fingerprint_column_cell(row_line, "cgroup_v2_cpu_stat") == "unavailable"


def test_render_markdown_systemd_column_renders_count_and_shared_label_for_identical_sets(tmp_path):
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    timers = [_timer_line("a.timer"), _timer_line("b.timer")]
    _write_probe_run(runs_dir, "run-1.json", fingerprint=_fingerprint(systemd_timers=timers))
    _write_probe_run(
        runs_dir, "run-2.json",
        run={
            "job_index": 2, "github_run_id": "2", "github_run_attempt": "1", "github_sha": "x",
            "git_tree_hash": "deadbeef", "campaign_branch": "perf-probe/campaign", "runner_os": "Linux",
        },
        fingerprint=_fingerprint(systemd_timers=list(reversed(timers))),
    )
    out_md, out_json = tmp_path / "out.md", tmp_path / "out.json"

    probe_capability_report.main(
        ["--runs-dir", str(runs_dir), "--out-md", str(out_md), "--out-json", str(out_json)]
    )

    lines = out_md.read_text(encoding="utf-8").splitlines()
    row_1 = next(line for line in lines if line.startswith("| run-1"))
    row_2 = next(line for line in lines if line.startswith("| run-2"))
    assert _fingerprint_column_cell(row_1, "systemd_timers") == "2 (set-1)"
    # same distinct unit set regardless of line order -> same label
    assert _fingerprint_column_cell(row_2, "systemd_timers") == "2 (set-1)"


def test_render_markdown_systemd_column_distinct_sets_get_distinct_labels(tmp_path):
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    _write_probe_run(
        runs_dir, "run-1.json",
        fingerprint=_fingerprint(systemd_timers=[_timer_line("zeta.timer")]),
    )
    _write_probe_run(
        runs_dir, "run-2.json",
        run={
            "job_index": 2, "github_run_id": "2", "github_run_attempt": "1", "github_sha": "x",
            "git_tree_hash": "deadbeef", "campaign_branch": "perf-probe/campaign", "runner_os": "Linux",
        },
        fingerprint=_fingerprint(systemd_timers=[_timer_line("alpha.timer")]),
    )
    out_md, out_json = tmp_path / "out.md", tmp_path / "out.json"

    probe_capability_report.main(
        ["--runs-dir", str(runs_dir), "--out-md", str(out_md), "--out-json", str(out_json)]
    )

    lines = out_md.read_text(encoding="utf-8").splitlines()
    row_1 = next(line for line in lines if line.startswith("| run-1"))
    row_2 = next(line for line in lines if line.startswith("| run-2"))
    # ("alpha.timer",) sorts before ("zeta.timer",) lexicographically, so run-2 (alpha) gets set-1
    assert _fingerprint_column_cell(row_2, "systemd_timers") == "1 (set-1)"
    assert _fingerprint_column_cell(row_1, "systemd_timers") == "1 (set-2)"


def test_render_markdown_systemd_column_renders_missing_sentinel_for_absent_field(tmp_path):
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    fingerprint = _fingerprint()
    del fingerprint["systemd_timers"]
    _write_probe_run(runs_dir, "good.json", fingerprint=fingerprint)
    out_md, out_json = tmp_path / "out.md", tmp_path / "out.json"

    probe_capability_report.main(
        ["--runs-dir", str(runs_dir), "--out-md", str(out_md), "--out-json", str(out_json)]
    )

    row_line = next(
        line for line in out_md.read_text(encoding="utf-8").splitlines() if line.startswith("| good")
    )
    assert _fingerprint_column_cell(row_line, "systemd_timers") == probe_capability_report.MISSING_FIELD


def test_render_markdown_systemd_column_zero_timers_renders_no_timers_label(tmp_path):
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    _write_probe_run(runs_dir, "good.json", fingerprint=_fingerprint(systemd_timers=[]))
    out_md, out_json = tmp_path / "out.md", tmp_path / "out.json"

    probe_capability_report.main(
        ["--runs-dir", str(runs_dir), "--out-md", str(out_md), "--out-json", str(out_json)]
    )

    row_line = next(
        line for line in out_md.read_text(encoding="utf-8").splitlines() if line.startswith("| good")
    )
    expected = f"0 ({probe_capability_report.NO_TIMERS_OBSERVED})"
    assert _fingerprint_column_cell(row_line, "systemd_timers") == expected


def test_fingerprint_table_has_twelve_data_columns_and_every_row_matches_header_cell_count(tmp_path):
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    _write_probe_run(runs_dir, "good.json")
    out_md, out_json = tmp_path / "out.md", tmp_path / "out.json"

    probe_capability_report.main(
        ["--runs-dir", str(runs_dir), "--out-md", str(out_md), "--out-json", str(out_json)]
    )

    text = out_md.read_text(encoding="utf-8")
    lines = text.splitlines()
    header_index = next(i for i, line in enumerate(lines) if line.startswith("| Run |"))
    header_line = lines[header_index]
    separator_line = lines[header_index + 1]
    row_line = next(line for line in lines if line.startswith("| good"))

    assert len(probe_capability_report.FINGERPRINT_COLUMNS) == 12
    assert header_line.count("|") == separator_line.count("|")
    assert header_line.count("|") == row_line.count("|")


# --- build_cgroup_and_timer_section -----------------------------------------


def _cgroup_timer_record(
    run_id: str,
    cgroup_v2_cpu_stat=None,
    cgroup_v2_cpu_max="unavailable",
    systemd_timers=None,
    include_cgroup_key: bool = True,
) -> dict:
    fingerprint: dict = {"cgroup_v2_cpu_max": cgroup_v2_cpu_max}
    if include_cgroup_key:
        fingerprint["cgroup_v2_cpu_stat"] = (
            cgroup_v2_cpu_stat if cgroup_v2_cpu_stat is not None else {"nr_periods": 0}
        )
    if systemd_timers is not None:
        fingerprint["systemd_timers"] = systemd_timers
    return {"_run_id": run_id, "fingerprint": fingerprint}


def test_build_cgroup_and_timer_section_reports_full_observed_key_union_per_run():
    records = [
        _cgroup_timer_record("run-1", cgroup_v2_cpu_stat={"nr_periods": 1, "nr_throttled": 0}),
        _cgroup_timer_record("run-2", cgroup_v2_cpu_stat={"nr_periods": 2, "usage_usec": 500}),
    ]

    section = probe_capability_report.build_cgroup_and_timer_section(records)

    assert section["cgroup_stat_columns"] == ["nr_periods", "nr_throttled", "usage_usec"]
    rows_by_id = {row["run_id"]: row for row in section["cgroup_rows"]}
    assert rows_by_id["run-1"]["nr_periods"] == 1
    assert rows_by_id["run-1"]["nr_throttled"] == 0
    assert rows_by_id["run-1"]["usage_usec"] == probe_capability_report.MISSING_FIELD
    assert rows_by_id["run-2"]["nr_throttled"] == probe_capability_report.MISSING_FIELD
    assert rows_by_id["run-2"]["usage_usec"] == 500


def test_build_cgroup_and_timer_section_missing_key_contributes_absent_row_not_dropped():
    records = [
        _cgroup_timer_record("run-1", cgroup_v2_cpu_stat={"nr_periods": 1}),
        _cgroup_timer_record("run-2", include_cgroup_key=False),
    ]

    section = probe_capability_report.build_cgroup_and_timer_section(records)

    assert len(section["cgroup_rows"]) == 2
    rows_by_id = {row["run_id"]: row for row in section["cgroup_rows"]}
    assert rows_by_id["run-2"]["nr_periods"] == probe_capability_report.MISSING_FIELD


def test_build_cgroup_and_timer_section_unreadable_sentinel_renders_verbatim_across_row():
    records = [
        _cgroup_timer_record("run-1", cgroup_v2_cpu_stat={"nr_periods": 1}),
        _cgroup_timer_record("run-2", cgroup_v2_cpu_stat="unavailable"),
    ]

    section = probe_capability_report.build_cgroup_and_timer_section(records)

    rows_by_id = {row["run_id"]: row for row in section["cgroup_rows"]}
    assert rows_by_id["run-2"]["nr_periods"] == "unavailable"


def test_build_cgroup_and_timer_section_records_cpu_quota_per_run():
    records = [_cgroup_timer_record("run-1", cgroup_v2_cpu_max="max 100000")]

    section = probe_capability_report.build_cgroup_and_timer_section(records)

    assert section["cgroup_rows"][0]["cgroup_v2_cpu_max"] == "max 100000"


def test_build_cgroup_and_timer_section_rows_ordered_by_run_id():
    records = [
        _cgroup_timer_record("run-b"),
        _cgroup_timer_record("run-a"),
    ]

    section = probe_capability_report.build_cgroup_and_timer_section(records)

    assert [row["run_id"] for row in section["cgroup_rows"]] == ["run-a", "run-b"]


def test_build_cgroup_and_timer_section_single_distinct_unit_set_inventory():
    timers = [_timer_line("a.timer"), _timer_line("b.timer")]
    records = [
        _cgroup_timer_record("run-1", systemd_timers=timers),
        _cgroup_timer_record("run-2", systemd_timers=list(reversed(timers))),
    ]

    section = probe_capability_report.build_cgroup_and_timer_section(records)

    assert len(section["timer_inventory"]) == 1
    entry = section["timer_inventory"][0]
    assert entry["label"] == "set-1"
    assert entry["unit_count"] == 2
    assert entry["run_count"] == 2
    assert entry["unit_names"] == ["a.timer", "b.timer"]


def test_build_cgroup_and_timer_section_two_distinct_unit_sets_get_distinct_labels():
    records = [
        _cgroup_timer_record("run-1", systemd_timers=[_timer_line("zeta.timer")]),
        _cgroup_timer_record("run-2", systemd_timers=[_timer_line("alpha.timer")]),
        _cgroup_timer_record("run-3", systemd_timers=[_timer_line("alpha.timer")]),
    ]

    section = probe_capability_report.build_cgroup_and_timer_section(records)

    labels_by_units = {tuple(entry["unit_names"]): entry for entry in section["timer_inventory"]}
    assert labels_by_units[("alpha.timer",)]["label"] == "set-1"
    assert labels_by_units[("alpha.timer",)]["run_count"] == 2
    assert labels_by_units[("zeta.timer",)]["label"] == "set-2"
    assert labels_by_units[("zeta.timer",)]["run_count"] == 1


def test_build_cgroup_and_timer_section_zero_timers_anywhere_yields_empty_inventory():
    records = [_cgroup_timer_record("run-1", systemd_timers=[])]

    section = probe_capability_report.build_cgroup_and_timer_section(records)

    assert section["timer_inventory"] == []


def test_render_cgroup_and_timer_section_header_appears_exactly_once(tmp_path):
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    _write_probe_run(runs_dir, "good.json")
    out_md, out_json = tmp_path / "out.md", tmp_path / "out.json"

    probe_capability_report.main(
        ["--runs-dir", str(runs_dir), "--out-md", str(out_md), "--out-json", str(out_json)]
    )

    text = out_md.read_text(encoding="utf-8")
    assert text.count("cgroup v2 cpu.stat and systemd timer state") == 1


def test_render_cgroup_and_timer_section_zero_timers_renders_explicit_statement(tmp_path):
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    _write_probe_run(runs_dir, "good.json", fingerprint=_fingerprint(systemd_timers=[]))
    out_md, out_json = tmp_path / "out.md", tmp_path / "out.json"

    probe_capability_report.main(
        ["--runs-dir", str(runs_dir), "--out-md", str(out_md), "--out-json", str(out_json)]
    )

    text = out_md.read_text(encoding="utf-8")
    assert probe_capability_report.NO_TIMERS_OBSERVED in text


def test_render_cgroup_and_timer_section_names_throttling_counter_columns(tmp_path):
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    _write_probe_run(
        runs_dir, "good.json",
        fingerprint=_fingerprint(cgroup_v2_cpu_stat={
            "nr_periods": 1, "nr_throttled": 2, "throttled_usec": 3,
        }),
    )
    out_md, out_json = tmp_path / "out.md", tmp_path / "out.json"

    probe_capability_report.main(
        ["--runs-dir", str(runs_dir), "--out-md", str(out_md), "--out-json", str(out_json)]
    )

    section_index = out_md.read_text(encoding="utf-8").index("cgroup v2 cpu.stat and systemd timer state")
    section_text = out_md.read_text(encoding="utf-8")[section_index:]
    header_line = next(line for line in section_text.splitlines() if line.startswith("| Run |"))
    assert "nr_periods" in header_line
    assert "nr_throttled" in header_line
    assert "throttled_usec" in header_line


def test_fingerprint_column_label_matches_detail_section_inventory_label(tmp_path):
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    timers = [_timer_line("a.timer")]
    _write_probe_run(runs_dir, "good.json", fingerprint=_fingerprint(systemd_timers=timers))
    out_md, out_json = tmp_path / "out.md", tmp_path / "out.json"

    probe_capability_report.main(
        ["--runs-dir", str(runs_dir), "--out-md", str(out_md), "--out-json", str(out_json)]
    )

    sidecar = json.loads(out_json.read_text(encoding="utf-8"))
    inventory_label = sidecar["cgroup_and_timer"]["timer_inventory"][0]["label"]

    row_line = next(
        line for line in out_md.read_text(encoding="utf-8").splitlines() if line.startswith("| good")
    )
    assert f"({inventory_label})" in _fingerprint_column_cell(row_line, "systemd_timers")


def test_cgroup_and_timer_section_byte_stable_across_two_invocations(tmp_path):
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    _write_probe_run(
        runs_dir, "run-1.json",
        fingerprint=_fingerprint(
            cgroup_v2_cpu_stat={"nr_periods": 1, "nr_throttled": 0, "throttled_usec": 0},
            systemd_timers=[_timer_line("a.timer")],
        ),
    )
    _write_probe_run(
        runs_dir, "run-2.json",
        run={
            "job_index": 2, "github_run_id": "2", "github_run_attempt": "1", "github_sha": "x",
            "git_tree_hash": "deadbeef", "campaign_branch": "perf-probe/campaign", "runner_os": "Linux",
        },
        fingerprint=_fingerprint(
            cgroup_v2_cpu_stat="unavailable",
            systemd_timers=[_timer_line("b.timer")],
        ),
    )
    out_md1, out_json1 = tmp_path / "m1.md", tmp_path / "s1.json"
    out_md2, out_json2 = tmp_path / "m2.md", tmp_path / "s2.json"

    probe_capability_report.main(
        ["--runs-dir", str(runs_dir), "--out-md", str(out_md1), "--out-json", str(out_json1)]
    )
    probe_capability_report.main(
        ["--runs-dir", str(runs_dir), "--out-md", str(out_md2), "--out-json", str(out_json2)]
    )

    assert out_md1.read_bytes() == out_md2.read_bytes()
    assert out_json1.read_bytes() == out_json2.read_bytes()


# --- build_population --------------------------------------------------------


def test_build_population_unrecognized_schema_version_is_skipped_and_counted(tmp_path):
    _write_probe_run(tmp_path, "good.json")
    _write_probe_run(tmp_path, "future.json", probe_schema_version=99)

    population = probe_capability_report.build_population(list(tmp_path.glob("*.json")), None)

    assert population["skipped_count"] == 1
    assert len(population["accepted"]) == 1
    accepted_ids = [record["_run_id"] for record in population["accepted"]]
    assert "future" not in accepted_ids


def test_build_population_tree_hash_mismatch_counted_separately_from_skip(tmp_path):
    _write_probe_run(tmp_path, "matches.json", run={"git_tree_hash": "expected-hash"})
    _write_probe_run(tmp_path, "mismatch.json", run={"git_tree_hash": "other-hash"})
    (tmp_path / "malformed.json").write_text("not json", encoding="utf-8")

    population = probe_capability_report.build_population(
        list(tmp_path.glob("*.json")), "expected-hash",
    )

    assert population["skipped_count"] == 1
    assert population["rejected_count"] == 1
    assert len(population["accepted"]) == 1
    assert population["rejected_reasons"][0]["reason"] == probe_capability_report.TREE_HASH_MISMATCH


def test_build_population_sorted_input_order_invariance(tmp_path):
    _write_probe_run(tmp_path, "run-a.json", run={"git_tree_hash": "h", "github_run_id": "a"})
    _write_probe_run(tmp_path, "run-b.json", run={"git_tree_hash": "h", "github_run_id": "b"})

    forward_paths = sorted(tmp_path.glob("*.json"))
    reversed_paths = list(reversed(forward_paths))

    population_forward = probe_capability_report.build_population(forward_paths, None)
    population_reversed = probe_capability_report.build_population(reversed_paths, None)

    forward_ids = [record["_run_id"] for record in population_forward["accepted"]]
    reversed_ids = [record["_run_id"] for record in population_reversed["accepted"]]
    assert forward_ids == reversed_ids


# --- build_coverage_section --------------------------------------------------


def test_build_coverage_section_reports_distinct_host_models_and_stopping_condition():
    records = [
        {"fingerprint": {"cpu_model": "AMD EPYC 7763"}},
        {"fingerprint": {"cpu_model": "AMD EPYC 7763"}},
        {"fingerprint": {"cpu_model": "Intel Xeon 8272CL"}},
    ]

    coverage = probe_capability_report.build_coverage_section(
        records, target_cpu_models=["AMD EPYC 7763", "Intel Xeon 8272CL"], run_cap=10,
    )

    assert coverage["host_model_run_counts"] == {"AMD EPYC 7763": 2, "Intel Xeon 8272CL": 1}
    assert coverage["distinct_host_model_count"] == 2
    assert coverage["stopping_condition"] == probe_capability_report.STOPPING_CONDITION_TARGET_MET


def test_build_coverage_section_run_cap_stopping_condition_when_target_not_met():
    records = [{"fingerprint": {"cpu_model": "AMD EPYC 7763"}} for _ in range(5)]

    coverage = probe_capability_report.build_coverage_section(
        records, target_cpu_models=["Intel Xeon 8272CL"], run_cap=5,
    )

    assert coverage["stopping_condition"] == probe_capability_report.STOPPING_CONDITION_RUN_CAP_REACHED


# --- main(): population hygiene and byte-stable reproduce contract ----------


def test_main_all_excluded_population_returns_nonzero_and_writes_no_matrix(tmp_path):
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    (runs_dir / "bad.json").write_text("not json", encoding="utf-8")
    out_md = tmp_path / "out.md"
    out_json = tmp_path / "out.json"

    exit_code = probe_capability_report.main(
        ["--runs-dir", str(runs_dir), "--out-md", str(out_md), "--out-json", str(out_json)]
    )

    assert exit_code == 1
    assert not out_md.exists()
    assert not out_json.exists()


def test_main_records_rejected_separately_from_skipped(tmp_path):
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    _write_probe_run(runs_dir, "good.json", run={"git_tree_hash": "expected"})
    _write_probe_run(runs_dir, "mismatch.json", run={"git_tree_hash": "other"})
    out_md = tmp_path / "out.md"
    out_json = tmp_path / "out.json"

    exit_code = probe_capability_report.main(
        [
            "--runs-dir", str(runs_dir),
            "--expected-tree-hash", "expected",
            "--out-md", str(out_md),
            "--out-json", str(out_json),
        ]
    )

    assert exit_code == 0
    sidecar = json.loads(out_json.read_text(encoding="utf-8"))
    assert sidecar["source"]["record_count"] == 1
    assert sidecar["source"]["records_rejected"] == 1


def test_main_neither_output_contains_a_wall_clock_timestamp(tmp_path):
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    _write_probe_run(runs_dir, "good.json")
    out_md = tmp_path / "out.md"
    out_json = tmp_path / "out.json"

    probe_capability_report.main(
        ["--runs-dir", str(runs_dir), "--out-md", str(out_md), "--out-json", str(out_json)]
    )

    timestamp_re = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")
    assert timestamp_re.search(out_md.read_text(encoding="utf-8")) is None
    assert timestamp_re.search(out_json.read_text(encoding="utf-8")) is None


def test_reproduce_command_includes_expected_tree_hash_argument():
    assert "--expected-tree-hash" in probe_capability_report.CANONICAL_COMMAND


def test_markdown_reproduce_section_contains_canonical_command(tmp_path):
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    _write_probe_run(runs_dir, "good.json")
    out_md = tmp_path / "out.md"
    out_json = tmp_path / "out.json"

    probe_capability_report.main(
        ["--runs-dir", str(runs_dir), "--out-md", str(out_md), "--out-json", str(out_json)]
    )

    text = out_md.read_text(encoding="utf-8")
    assert probe_capability_report.CANONICAL_COMMAND in text
    assert "--expected-tree-hash" in text


# --- canonical reproduce command: executed for real, not paraphrased -------


def test_canonical_command_names_the_coverage_parameters():
    argv = shlex.split(probe_capability_report.CANONICAL_COMMAND)

    assert argv[argv.index("--target-cpu-models") + 1] == ",".join(
        probe_capability_report.DEFAULT_TARGET_CPU_MODELS
    )
    assert argv[argv.index("--run-cap") + 1] == str(probe_capability_report.DEFAULT_RUN_CAP)


def test_canonical_command_reproduces_committed_matrix_byte_identically(tmp_path):
    argv = shlex.split(probe_capability_report.CANONICAL_COMMAND)

    # The interpreter token is asserted before substitution so a future edit
    # that changes CANONICAL_COMMAND to invoke something other than a python
    # interpreter is caught here rather than silently substituted away.
    assert argv[0].startswith("python")
    assert argv[1] == "scripts/probe_capability_report.py"

    out_md_index = argv.index("--out-md") + 1
    out_json_index = argv.index("--out-json") + 1
    # Assert the published output paths target the committed artifacts
    # before anything is redirected, so the redirection below cannot mask a
    # command that points at the wrong files.
    assert argv[out_md_index] == probe_capability_report.DEFAULT_OUT_MD
    assert argv[out_json_index] == probe_capability_report.DEFAULT_OUT_JSON

    scratch_md = tmp_path / "regen.md"
    scratch_json = tmp_path / "regen.json"
    argv[0] = sys.executable
    argv[out_md_index] = str(scratch_md)
    argv[out_json_index] = str(scratch_json)

    result = subprocess.run(argv, cwd=REPO_ROOT, capture_output=True, text=True)

    assert result.returncode == 0, result.stderr

    committed_md = (REPO_ROOT / probe_capability_report.DEFAULT_OUT_MD).read_bytes()
    committed_json = (REPO_ROOT / probe_capability_report.DEFAULT_OUT_JSON).read_bytes()
    assert scratch_md.read_bytes() == committed_md
    assert scratch_json.read_bytes() == committed_json


def test_aggregator_is_byte_stable_with_non_empty_coverage_state(tmp_path):
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    model_a = "AMD EPYC 7763 64-Core Processor"
    model_b = "Intel(R) Xeon(R) Platinum 8272CL"

    _write_probe_run(runs_dir, "run-1.json")
    _write_probe_run(
        runs_dir,
        "run-2.json",
        run={
            "job_index": 2,
            "github_run_id": "124",
            "github_run_attempt": "1",
            "github_sha": "def456",
            "git_tree_hash": "deadbeef",
            "campaign_branch": "perf-probe/campaign",
            "runner_os": "Linux",
        },
        fingerprint={
            "cpu_model": model_b,
            "cpu_mhz": 2596.994,
            "nproc": 4,
            "kernel_version": "6.17.0-1022-azure",
            "glibc_version": "2.39",
            "cpython_version": "3.12.3",
            "compiler_version": "gcc (fake) 13.2.0",
            "memory_total_bytes": 16777216000,
            "cgroup_v2_cpu_stat": {},
            "cgroup_v2_cpu_max": "max 100000",
            "systemd_timers": [],
            "runner_image_version": "20260810.271.1",
            "fingerprint_schema_version": 1,
            "errors": [],
        },
    )

    out_md1, out_json1 = tmp_path / "m1.md", tmp_path / "s1.json"
    out_md2, out_json2 = tmp_path / "m2.md", tmp_path / "s2.json"
    target_models = f"{model_a},{model_b}"

    probe_capability_report.main([
        "--runs-dir", str(runs_dir),
        "--target-cpu-models", target_models,
        "--run-cap", "10",
        "--out-md", str(out_md1),
        "--out-json", str(out_json1),
    ])
    probe_capability_report.main([
        "--runs-dir", str(runs_dir),
        "--target-cpu-models", target_models,
        "--run-cap", "10",
        "--out-md", str(out_md2),
        "--out-json", str(out_json2),
    ])

    assert out_md1.read_bytes() == out_md2.read_bytes()
    assert out_json1.read_bytes() == out_json2.read_bytes()

    sidecar = json.loads(out_json1.read_text(encoding="utf-8"))
    coverage = sidecar["coverage"]
    assert coverage["coverage_target"]
    assert coverage["run_cap"] == 10
    assert coverage["stopping_condition"] == probe_capability_report.STOPPING_CONDITION_TARGET_MET
