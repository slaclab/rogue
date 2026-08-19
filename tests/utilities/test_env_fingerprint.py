# ----------------------------------------------------------------------------
# Title      : Environment Fingerprint Tests
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
import math
import sys
from pathlib import Path

import pytest


SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

env_fingerprint = importlib.import_module("env_fingerprint")
perf_noise_report = importlib.import_module("perf_noise_report")


CALIBRATION_COMPONENT_KEYS = {"alu", "memcpy", "syscall", "tsc"}

EXPECTED_KEYS = {
    "cpu_model",
    "cpu_mhz",
    "nproc",
    "kernel_version",
    "glibc_version",
    "cpython_version",
    "compiler_version",
    "memory_total_bytes",
    "cgroup_v2_cpu_stat",
    "cgroup_v2_cpu_max",
    "systemd_timers",
    "runner_image_version",
    "fingerprint_schema_version",
    "errors",
}


def _write_cpuinfo(root: Path, model: str = "Intel(R) Xeon(R) Fake CPU", mhz: str = "2800.000") -> Path:
    path = root / "cpuinfo"
    path.write_text(
        f"processor\t: 0\nmodel name\t: {model}\ncpu MHz\t\t: {mhz}\nflags\t\t: fpu\n",
        encoding="utf-8",
    )
    return path


def _write_meminfo(root: Path, mem_total_line: str = "MemTotal:       16374420 kB") -> Path:
    path = root / "meminfo"
    path.write_text(f"{mem_total_line}\nMemFree:        100 kB\n", encoding="utf-8")
    return path


def _write_cgroup_stat(root: Path, name: str = "cpu.stat") -> Path:
    path = root / name
    path.write_text("nr_periods 10\nnr_throttled 0\nthrottled_usec 0\n", encoding="utf-8")
    return path


def _write_cgroup_max(root: Path, name: str = "cpu.max") -> Path:
    path = root / name
    path.write_text("max 100000\n", encoding="utf-8")
    return path


def _default_kwargs(root: Path) -> dict:
    return {
        "cpuinfo_path": _write_cpuinfo(root),
        "meminfo_path": _write_meminfo(root),
        "cgroup_cpu_stat_path": _write_cgroup_stat(root),
        "cgroup_cpu_max_path": _write_cgroup_max(root),
        "ldd_cmd": [sys.executable, "-c", "print('ldd (fake) 2.39')"],
        "gcc_cmd": [sys.executable, "-c", "print('gcc (fake) 13.2.0')"],
        "systemctl_cmd": [sys.executable, "-c", "print('mon.timer  fake.service')"],
    }


def test_collect_fingerprint_returns_all_documented_keys(tmp_path, monkeypatch):
    monkeypatch.setenv("ImageVersion", "20260810.271.1")
    result = env_fingerprint.collect_fingerprint(**_default_kwargs(tmp_path))

    assert set(result) == EXPECTED_KEYS
    assert result["fingerprint_schema_version"] == env_fingerprint.FINGERPRINT_SCHEMA_VERSION
    assert result["cpu_model"] == "Intel(R) Xeon(R) Fake CPU"
    assert result["cpu_mhz"] == 2800.0
    assert isinstance(result["nproc"], int) and result["nproc"] > 0
    assert result["kernel_version"] != env_fingerprint.UNAVAILABLE
    assert result["cpython_version"] != env_fingerprint.UNAVAILABLE
    assert result["memory_total_bytes"] == 16374420 * 1024
    assert result["cgroup_v2_cpu_stat"] == {"nr_periods": 10, "nr_throttled": 0, "throttled_usec": 0}
    assert result["cgroup_v2_cpu_max"] == "max 100000"
    assert result["systemd_timers"] == ["mon.timer  fake.service"]
    assert result["runner_image_version"] == "20260810.271.1"
    assert result["errors"] == []


def test_missing_cpuinfo_yields_unavailable_with_reason(tmp_path, monkeypatch):
    monkeypatch.setenv("ImageVersion", "v1")
    kwargs = _default_kwargs(tmp_path)
    kwargs["cpuinfo_path"] = tmp_path / "does-not-exist-cpuinfo"

    result = env_fingerprint.collect_fingerprint(**kwargs)

    assert result["cpu_model"] == env_fingerprint.UNAVAILABLE
    assert result["cpu_mhz"] == env_fingerprint.UNAVAILABLE
    assert any("cpu_model" in reason for reason in result["errors"])
    assert any("cpu_mhz" in reason for reason in result["errors"])


def test_meminfo_non_numeric_memtotal_yields_unavailable_not_valueerror(tmp_path, monkeypatch):
    monkeypatch.setenv("ImageVersion", "v1")
    kwargs = _default_kwargs(tmp_path)
    kwargs["meminfo_path"] = _write_meminfo(tmp_path, mem_total_line="MemTotal:       notanumber kB")

    result = env_fingerprint.collect_fingerprint(**kwargs)

    assert result["memory_total_bytes"] == env_fingerprint.UNAVAILABLE
    assert any("memory_total_bytes" in reason for reason in result["errors"])


def test_cgroup_absent_mount_yields_unavailable(tmp_path, monkeypatch):
    monkeypatch.setenv("ImageVersion", "v1")
    kwargs = _default_kwargs(tmp_path)
    kwargs["cgroup_cpu_stat_path"] = tmp_path / "no-such-cpu-stat"

    result = env_fingerprint.collect_fingerprint(**kwargs)

    assert result["cgroup_v2_cpu_stat"] == env_fingerprint.UNAVAILABLE
    assert any("cgroup_v2_cpu_stat" in reason for reason in result["errors"])


def test_cgroup_present_but_empty_yields_empty_mapping_distinct_from_unavailable(tmp_path, monkeypatch):
    monkeypatch.setenv("ImageVersion", "v1")
    kwargs = _default_kwargs(tmp_path)
    empty_stat = tmp_path / "empty-cpu.stat"
    empty_stat.write_text("", encoding="utf-8")
    kwargs["cgroup_cpu_stat_path"] = empty_stat

    result = env_fingerprint.collect_fingerprint(**kwargs)

    assert result["cgroup_v2_cpu_stat"] == {}
    assert result["cgroup_v2_cpu_stat"] != env_fingerprint.UNAVAILABLE


def test_missing_runner_image_version_env_yields_unavailable(tmp_path, monkeypatch):
    monkeypatch.delenv("ImageVersion", raising=False)
    result = env_fingerprint.collect_fingerprint(**_default_kwargs(tmp_path))

    assert result["runner_image_version"] == env_fingerprint.UNAVAILABLE
    assert any("runner_image_version" in reason for reason in result["errors"])


def test_no_exception_escapes_when_every_source_is_missing(tmp_path, monkeypatch):
    monkeypatch.delenv("ImageVersion", raising=False)
    result = env_fingerprint.collect_fingerprint(
        cpuinfo_path=tmp_path / "missing-cpuinfo",
        meminfo_path=tmp_path / "missing-meminfo",
        cgroup_cpu_stat_path=tmp_path / "missing-cpu.stat",
        cgroup_cpu_max_path=tmp_path / "missing-cpu.max",
        ldd_cmd=["definitely-not-a-real-binary-xyz"],
        gcc_cmd=["definitely-not-a-real-binary-xyz"],
        systemctl_cmd=["definitely-not-a-real-binary-xyz"],
    )

    assert result["cpu_model"] == env_fingerprint.UNAVAILABLE
    assert result["memory_total_bytes"] == env_fingerprint.UNAVAILABLE
    assert result["cgroup_v2_cpu_stat"] == env_fingerprint.UNAVAILABLE
    assert result["cgroup_v2_cpu_max"] == env_fingerprint.UNAVAILABLE
    assert result["compiler_version"] == env_fingerprint.UNAVAILABLE
    assert result["systemd_timers"] == env_fingerprint.UNAVAILABLE
    assert result["runner_image_version"] == env_fingerprint.UNAVAILABLE
    assert len(result["errors"]) >= 6


def test_cli_json_flag_prints_fingerprint_and_calibration_together(capsys):
    exit_code = env_fingerprint.main(["--json"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert set(payload["fingerprint"]) == EXPECTED_KEYS
    assert set(payload["calibration"]["components"]) == CALIBRATION_COMPONENT_KEYS


def test_cli_fingerprint_only_prints_just_the_fingerprint(capsys):
    exit_code = env_fingerprint.main(["--fingerprint-only", "--json"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert set(payload) == EXPECTED_KEYS


def test_cli_calibration_only_prints_the_four_component_keys(capsys):
    exit_code = env_fingerprint.main(["--calibration-only", "--json"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert set(payload["components"]) == CALIBRATION_COMPONENT_KEYS


# ---------------------------------------------------------------------------
# Calibration vector (collect_calibration_vector)
# ---------------------------------------------------------------------------

_FAST_CALIBRATION_KWARGS = {
    "alu_iterations": 1000,
    "memcpy_bytes": 4096,
    "memcpy_block_bytes": 1024,
    "syscall_iterations": 100,
    "tsc_sample_seconds": 0.01,
}


def test_collect_calibration_vector_returns_exactly_four_components():
    result = env_fingerprint.collect_calibration_vector(repeats=2, **_FAST_CALIBRATION_KWARGS)

    assert result["calibration_schema_version"] == env_fingerprint.CALIBRATION_SCHEMA_VERSION
    assert set(result["components"]) == CALIBRATION_COMPONENT_KEYS


def test_collect_calibration_vector_component_entries_are_well_formed():
    result = env_fingerprint.collect_calibration_vector(repeats=3, **_FAST_CALIBRATION_KWARGS)

    expected_units = {
        "alu": "ops_per_second",
        "memcpy": "bytes_per_second",
        "syscall": "nanoseconds_per_call",
        "tsc": "hertz",
    }
    for name, unit in expected_units.items():
        entry = result["components"][name]
        assert entry != env_fingerprint.UNAVAILABLE, f"{name} component was unavailable"
        assert entry["unit"] == unit
        assert entry["repeats"] == 3
        assert len(entry["samples"]) == 3
        for numeric_field in ("value", "median", "mad"):
            assert math.isfinite(entry[numeric_field])
        for sample in entry["samples"]:
            assert math.isfinite(sample)


def test_collect_calibration_vector_single_repeat_yields_zero_mad():
    result = env_fingerprint.collect_calibration_vector(repeats=1, **_FAST_CALIBRATION_KWARGS)

    for name in CALIBRATION_COMPONENT_KEYS:
        entry = result["components"][name]
        assert entry["repeats"] == 1
        assert entry["mad"] == 0.0


def test_collect_calibration_vector_no_fifth_blended_component():
    result = env_fingerprint.collect_calibration_vector(repeats=1, **_FAST_CALIBRATION_KWARGS)

    assert "components" in result
    assert len(result["components"]) == 4
    assert "overall" not in result
    assert "score" not in result


def test_tsc_component_falls_back_to_cpuinfo_when_hwcounter_unavailable(tmp_path, monkeypatch):
    monkeypatch.setattr(env_fingerprint, "HAS_HWCOUNTER", False)
    cpuinfo_path = _write_cpuinfo(tmp_path, mhz="2800.000")

    result = env_fingerprint.collect_calibration_vector(
        repeats=1, cpuinfo_path=cpuinfo_path, **_FAST_CALIBRATION_KWARGS,
    )

    tsc_entry = result["components"]["tsc"]
    assert tsc_entry != env_fingerprint.UNAVAILABLE
    assert tsc_entry["value"] == pytest.approx(2800.0 * 1e6)


def test_tsc_component_unavailable_when_both_sources_fail(tmp_path, monkeypatch):
    monkeypatch.setattr(env_fingerprint, "HAS_HWCOUNTER", False)
    missing_cpuinfo = tmp_path / "does-not-exist-cpuinfo"

    result = env_fingerprint.collect_calibration_vector(
        repeats=1, cpuinfo_path=missing_cpuinfo, **_FAST_CALIBRATION_KWARGS,
    )

    assert result["components"]["tsc"] == env_fingerprint.UNAVAILABLE
    assert any("calibration_tsc" in reason for reason in result["errors"])
    # The other three components are still measured despite the tsc failure.
    for name in ("alu", "memcpy", "syscall"):
        assert result["components"][name] != env_fingerprint.UNAVAILABLE


def test_tsc_rate_derivation_matches_noise_report_host_group_bucketing():
    cycles = 2_800_000_000.0
    elapsed_ns = 1_000_000_000.0

    rate_hz = env_fingerprint._derive_cycles_rate_hz(cycles, elapsed_ns)

    record = {
        "benchmarks": [
            {
                "name": "variable_rate_perf_localGetRate",
                "raw": {
                    "cycles": cycles,
                    "avg_ns": elapsed_ns / perf_noise_report.BENCH_COUNT,
                },
            },
        ],
    }
    expected_rate_hz = perf_noise_report.derived_rate_hz(record)

    assert expected_rate_hz is not None
    assert (
        perf_noise_report.host_group_id(rate_hz)
        == perf_noise_report.host_group_id(expected_rate_hz)
        == "tsc-2.80GHz"
    )


# ---------------------------------------------------------------------------
# Measurement-window steal/cgroup sampler (sample_cpu_window)
# ---------------------------------------------------------------------------

def _write_proc_stat(root: Path, name: str, fields: list[int]) -> Path:
    path = root / name
    path.write_text("cpu  " + " ".join(str(field) for field in fields) + "\n", encoding="utf-8")
    return path


def test_read_proc_stat_cpu_parses_ten_fields(tmp_path):
    fields = [100, 0, 50, 900, 0, 0, 0, 5, 0, 0]
    path = _write_proc_stat(tmp_path, "stat", fields)

    result = env_fingerprint.read_proc_stat_cpu(path)

    assert result == fields
    assert result[7] == 5  # steal


def test_read_proc_stat_cpu_missing_file_yields_unavailable(tmp_path):
    result = env_fingerprint.read_proc_stat_cpu(tmp_path / "no-such-stat")

    assert result == env_fingerprint.UNAVAILABLE


def test_read_proc_stat_cpu_malformed_line_yields_unavailable(tmp_path):
    path = tmp_path / "stat"
    path.write_text("cpu  1 2 3\n", encoding="utf-8")

    result = env_fingerprint.read_proc_stat_cpu(path)

    assert result == env_fingerprint.UNAVAILABLE


def test_read_cgroup_cpu_stat_public_wrapper_distinguishes_absent_and_empty(tmp_path):
    present_empty = tmp_path / "empty-cpu.stat"
    present_empty.write_text("", encoding="utf-8")

    assert env_fingerprint.read_cgroup_cpu_stat(present_empty) == {}
    assert env_fingerprint.read_cgroup_cpu_stat(tmp_path / "absent-cpu.stat") == env_fingerprint.UNAVAILABLE


def test_sample_cpu_window_flags_steal_fraction_exactly_at_threshold(tmp_path):
    # sample_cpu_window reads proc_stat_path once before fn() and once after,
    # so fn() rewrites the file in place to produce a controlled delta:
    # 1 steal jiffy out of 100 total jiffies delta == 0.01, the default threshold.
    stat_path = _write_proc_stat(tmp_path, "stat", [0, 0, 0, 0, 0, 0, 0, 0, 0, 0])

    def fn():
        _write_proc_stat(tmp_path, "stat", [99, 0, 0, 0, 0, 0, 0, 1, 0, 0])
        return "done"

    window = env_fingerprint.sample_cpu_window(
        "probe", fn,
        proc_stat_path=stat_path,
        cgroup_cpu_stat_path=tmp_path / "absent-cpu.stat",
    )

    assert window["steal_jiffies_delta"] == 1
    assert window["cpu_total_jiffies_delta"] == 100
    assert window["steal_fraction"] == pytest.approx(0.01)
    assert window["steal_flagged"] is True
    assert window["steal_comparison"] == ">="
    assert window["steal_threshold"] == env_fingerprint.DEFAULT_STEAL_THRESHOLD


def test_sample_cpu_window_absent_cgroup_leaves_steal_fields_populated(tmp_path):
    stat_path = _write_proc_stat(tmp_path, "stat", [0, 0, 0, 0, 0, 0, 0, 0, 0, 0])

    def fn():
        _write_proc_stat(tmp_path, "stat", [100, 0, 0, 0, 0, 0, 0, 0, 0, 0])
        return "done"

    window = env_fingerprint.sample_cpu_window(
        "probe", fn,
        proc_stat_path=stat_path,
        cgroup_cpu_stat_path=tmp_path / "absent-cpu.stat",
    )

    assert window["steal_jiffies_delta"] == 0
    assert window["cpu_total_jiffies_delta"] == 100
    assert window["cgroup_nr_periods_delta"] == env_fingerprint.UNAVAILABLE
    assert window["cgroup_nr_throttled_delta"] == env_fingerprint.UNAVAILABLE
    assert window["cgroup_throttled_usec_delta"] == env_fingerprint.UNAVAILABLE
    assert window["result"] == "done"


def test_sample_cpu_window_reads_real_proc_stat_and_absent_cgroup(tmp_path):
    window = env_fingerprint.sample_cpu_window(
        "probe",
        lambda: 42,
        cgroup_cpu_stat_path=tmp_path / "absent-cpu.stat",
    )

    assert window["result"] == 42
    assert window["cgroup_nr_periods_delta"] == env_fingerprint.UNAVAILABLE
    assert window["cgroup_nr_throttled_delta"] == env_fingerprint.UNAVAILABLE
    assert window["cgroup_throttled_usec_delta"] == env_fingerprint.UNAVAILABLE
    # /proc/stat is expected to be readable in the test environment; if it
    # is not, both steal fields degrade to UNAVAILABLE together, never one
    # without the other.
    steal_available = window["steal_jiffies_delta"] != env_fingerprint.UNAVAILABLE
    assert steal_available == (window["cpu_total_jiffies_delta"] != env_fingerprint.UNAVAILABLE)


def test_read_cgroup_cpu_stat_present_but_empty_distinct_from_absent(tmp_path):
    present_empty = tmp_path / "empty-cpu.stat"
    present_empty.write_text("", encoding="utf-8")
    stat_path = _write_proc_stat(tmp_path, "stat", [0, 0, 0, 0, 0, 0, 0, 0, 0, 0])

    def fn():
        _write_proc_stat(tmp_path, "stat", [100, 0, 0, 0, 0, 0, 0, 0, 0, 0])
        return "done"

    window = env_fingerprint.sample_cpu_window(
        "probe", fn,
        proc_stat_path=stat_path,
        cgroup_cpu_stat_path=present_empty,
    )

    # Present-but-empty cgroup file: the mapping is {} (not UNAVAILABLE), so
    # per-field deltas come back UNAVAILABLE (no periods/throttled keys to
    # diff), distinct from the absent-file case which never even attempts
    # to read a cgroup mapping.
    assert window["cgroup_nr_periods_delta"] == env_fingerprint.UNAVAILABLE
    assert window["cgroup_nr_throttled_delta"] == env_fingerprint.UNAVAILABLE
    assert window["cgroup_throttled_usec_delta"] == env_fingerprint.UNAVAILABLE


def test_order_windows_stable_tie_break_on_label():
    windows = [
        {"label": "b", "steal_fraction": 0.02},
        {"label": "a", "steal_fraction": 0.02},
    ]

    ordered = env_fingerprint.order_windows(windows)

    assert [window["label"] for window in ordered] == ["a", "b"]


def test_order_windows_unavailable_steal_fraction_sorts_last():
    windows = [
        {"label": "a", "steal_fraction": env_fingerprint.UNAVAILABLE},
        {"label": "b", "steal_fraction": 0.5},
    ]

    ordered = env_fingerprint.order_windows(windows)

    assert [window["label"] for window in ordered] == ["b", "a"]
