#!/usr/bin/env python3
# ----------------------------------------------------------------------------
# Title      : Perf Gate Hang Diagnostics Tests
# ----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
# ----------------------------------------------------------------------------

"""Behavioural coverage for scripts/perf_gate_hang_diagnostics.py, driven entirely
against a real temporary directory standing in for /proc: no test signals a real
process, reads the real process filesystem, or sleeps."""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

D = importlib.import_module("perf_gate_hang_diagnostics")


def _write_proc_entry(
    root: Path, pid: int, *, ppid: int = 1, comm: str = "python3", state: str = "S",
    cmdline: str | None = None, threads: dict[str, dict[str, str]] | None = None,
) -> Path:
    """Build one `<root>/<pid>` fixture directory shaped like `/proc/<pid>`: a `stat`
    line whose field 4 is `ppid`, an optional `cmdline`, and one `task/<tid>` directory
    per entry of `threads` (each carrying `comm`, `stat`, and `wchan`)."""
    pid_dir = root / str(pid)
    pid_dir.mkdir(parents=True, exist_ok=True)
    stat_line = f"{pid} ({comm}) {state} {ppid} {pid} 0 0 -1 0 0 0 0 0 0 0 0 0\n"
    (pid_dir / "stat").write_text(stat_line)
    (pid_dir / "status").write_text(f"Name:\t{comm}\nState:\t{state}\n")
    if cmdline is not None:
        (pid_dir / "cmdline").write_text(cmdline)

    task_dir = pid_dir / "task"
    task_dir.mkdir(exist_ok=True)
    threads = threads or {str(pid): {"comm": comm, "wchan": "0"}}
    for tid, fields in threads.items():
        tid_dir = task_dir / tid
        tid_dir.mkdir(exist_ok=True)
        (tid_dir / "comm").write_text(fields.get("comm", comm) + "\n")
        (tid_dir / "stat").write_text(
            f"{tid} ({fields.get('comm', comm)}) {fields.get('state', state)} {ppid} {pid} 0 0 -1 0 0 0 0 0 0 0 0 0\n"
        )
        (tid_dir / "wchan").write_text(fields.get("wchan", "0"))
    return pid_dir


# --- descendant_pids -------------------------------------------------------------------


def test_descendant_pids_walks_the_parent_chain_from_a_fixture_tree(tmp_path):
    _write_proc_entry(tmp_path, 100, ppid=1)
    _write_proc_entry(tmp_path, 200, ppid=100)
    _write_proc_entry(tmp_path, 201, ppid=100)
    _write_proc_entry(tmp_path, 300, ppid=200)
    _write_proc_entry(tmp_path, 999, ppid=1)  # unrelated pid, must not appear

    descendants = D.descendant_pids(100, proc_root=str(tmp_path))

    assert descendants == [200, 201, 300]
    assert 100 not in descendants


def test_descendant_pids_skips_a_pid_that_disappears_mid_walk(tmp_path):
    _write_proc_entry(tmp_path, 100, ppid=1)
    _write_proc_entry(tmp_path, 200, ppid=100)
    # Simulate a pid whose stat file vanished mid-walk: the directory exists (so it is
    # enumerated) but its stat file does not.
    vanished_dir = tmp_path / "201"
    vanished_dir.mkdir()

    descendants = D.descendant_pids(100, proc_root=str(tmp_path))

    assert descendants == [200]
    assert 201 not in descendants


# --- thread_snapshot ---------------------------------------------------------------------


def test_thread_snapshot_records_every_task_directory_with_its_wait_location(tmp_path):
    _write_proc_entry(
        tmp_path, 100, cmdline="python3\0scripts/perf_harness_runner.py\0",
        threads={
            "100": {"wchan": "__skb_wait_for_more_packets"},
            "101": {"wchan": "futex_wait_queue_me"},
        },
    )

    entry = D.thread_snapshot(100, proc_root=str(tmp_path))

    assert entry["pid"] == 100
    assert entry["ppid"] == 1
    wchans = {thread["tid"]: thread["wchan"] for thread in entry["threads"]}
    assert wchans == {100: "__skb_wait_for_more_packets", 101: "futex_wait_queue_me"}
    assert "unavailable" not in entry


def test_thread_snapshot_marks_an_unreadable_field_unavailable_rather_than_dropping_it(tmp_path):
    # No cmdline file written at all -- simulates a field that cannot be read.
    _write_proc_entry(tmp_path, 100, cmdline=None)

    entry = D.thread_snapshot(100, proc_root=str(tmp_path))

    assert entry["cmdline"] == "unavailable"
    assert "cmdline" in entry["unavailable"]
    # The thread itself is still present with its other fields intact.
    assert len(entry["threads"]) == 1


# --- allowlist enforcement ---------------------------------------------------------------


def test_snapshot_reads_only_the_allowlisted_files(tmp_path):
    pid_dir = _write_proc_entry(tmp_path, 100, cmdline="python3\0scripts/perf_harness_runner.py\0")
    # A per-process environment pseudo-file stand-in, deliberately not in the allowlist.
    (pid_dir / "environ").write_text("GITHUB_TOKEN=leak-if-read\0")

    captured = D.snapshot(100, proc_root=str(tmp_path), clock=lambda: 1.0)

    assert "leak-if-read" not in json.dumps(captured)
    # The private read helper refuses the name directly, regardless of caller.
    assert D._read_allowlisted(pid_dir, "environ", D.PROC_READ_ALLOWLIST) is None
    assert "environ" not in D.PROC_READ_ALLOWLIST
    assert "environ" not in D.TASK_READ_ALLOWLIST


def test_snapshot_redacts_a_secret_shaped_cmdline_assignment(tmp_path):
    _write_proc_entry(
        tmp_path, 100,
        cmdline="env\0GITHUB_TOKEN=supersecretvalue\0python3\0scripts/perf_harness_runner.py\0",
    )

    captured = D.snapshot(100, proc_root=str(tmp_path), clock=lambda: 1.0)
    text = json.dumps(captured)

    assert "supersecretvalue" not in text
    assert D.REDACTED in text
    assert "GITHUB_TOKEN" in text


# --- write_snapshot ----------------------------------------------------------------------


def test_write_snapshot_is_byte_stable_for_one_mapping(tmp_path):
    mapping = {"snapshot_schema_version": 1, "captured_at": 1.0, "root_pid": 100, "processes": []}
    out_path = tmp_path / "hang.json"

    D.write_snapshot(out_path, mapping)
    first = out_path.read_bytes()
    D.write_snapshot(out_path, mapping)
    second = out_path.read_bytes()

    assert first == second
    assert first.endswith(b"\n")


# --- signal_python_descendants -----------------------------------------------------------


def test_signal_python_descendants_never_signals_the_root_pid(tmp_path):
    _write_proc_entry(tmp_path, 100, cmdline="python3\0scripts/perf_harness_runner.py\0")

    killed: list[int] = []
    signalled = D.signal_python_descendants(
        100, proc_root=str(tmp_path), kill_fn=lambda pid, sig: killed.append(pid),
    )

    assert killed == []
    assert signalled == []


def test_signal_python_descendants_only_signals_a_measurement_subprocess(tmp_path):
    _write_proc_entry(tmp_path, 100, cmdline="bash\0-c\0true\0")
    _write_proc_entry(
        tmp_path, 200, ppid=100, cmdline="python3\0scripts/perf_harness_runner.py\0",
    )
    _write_proc_entry(tmp_path, 201, ppid=100, cmdline="sleep\0100\0")

    killed: list[int] = []
    signalled = D.signal_python_descendants(
        100, proc_root=str(tmp_path), kill_fn=lambda pid, sig: killed.append(pid),
    )

    assert signalled == [200]
    assert killed == [200]


# --- arm/disarm ----------------------------------------------------------------------------


class _SyncTimer:
    """A `threading.Timer`-shaped stand-in that fires synchronously on `start()` --
    sleeps for nothing, matching this phase's own testing convention."""

    def __init__(self, interval, function):
        self.interval = interval
        self.function = function
        self.cancelled = False

    def start(self):
        if not self.cancelled:
            self.function()

    def cancel(self):
        self.cancelled = True


def test_arm_captures_the_snapshot_before_it_signals_anything(tmp_path):
    _write_proc_entry(tmp_path, 100, cmdline="bash\0-c\0true\0")
    _write_proc_entry(
        tmp_path, 200, ppid=100, cmdline="python3\0scripts/perf_harness_runner.py\0",
    )
    out_path = tmp_path / "hang.json"
    events: list[str] = []

    def _recording_kill(pid, sig):
        events.append(f"kill:{pid}")

    real_write_snapshot = D.write_snapshot

    def _recording_write_snapshot(path, mapping):
        events.append("write_snapshot")
        return real_write_snapshot(path, mapping)

    import unittest.mock as mock

    with mock.patch.object(D, "write_snapshot", _recording_write_snapshot):
        D.arm(
            5, 100, out_path,
            timer_factory=_SyncTimer, proc_root=str(tmp_path),
            clock=lambda: 1.0, kill_fn=_recording_kill,
        )

    assert events == ["write_snapshot", "kill:200"]
    assert out_path.exists()


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
# ----------------------------------------------------------------------------
