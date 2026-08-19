#!/usr/bin/env python3
# ----------------------------------------------------------------------------
# Title      : ROGUE Perf Gate Hang Diagnostics
# ----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
# ----------------------------------------------------------------------------

"""Standard-library-only per-thread snapshot of a hung process tree.

This module exists because a hosted validation hang previously produced no evidence at
all: the job's own step timeout killed the run before anything could be read from the
stuck process. `arm()` starts a background timer that, on firing, reads a per-thread
snapshot of a process tree from `/proc` while its threads are still parked, writes that
snapshot to a file, renders it to stderr so it also lands in the job log, and then
signals the measurement subprocess so CPython dumps its own Python-level traceback too.

Every read goes through one private helper that refuses any file name outside a small
explicit allowlist, and the per-process environment pseudo-file is deliberately absent
from that allowlist: a public job artifact carries this snapshot, so there is no code
path by which a runner secret could reach it. A secret-shaped command-line assignment is
redacted independently of that allowlist, as a second layer.
"""

from __future__ import annotations

import json
import os
import re
import signal
import sys
import threading
import time
from pathlib import Path
from typing import Any, Callable

SNAPSHOT_SCHEMA_VERSION = 1
PROC_ROOT = "/proc"

# The per-process environment pseudo-file (commonly named "environ") is deliberately
# absent from this tuple. `_read_allowlisted` refuses any name not listed here, so there
# is no code path from this module into that file.
PROC_READ_ALLOWLIST: tuple[str, ...] = ("cmdline", "stat", "status", "task")
TASK_READ_ALLOWLIST: tuple[str, ...] = ("comm", "stat", "wchan")

REDACTED = "<redacted>"

# Case-insensitive: matches a command-line word's key side naming a token, secret,
# password, passwd, credential, or api key style assignment.
_SECRET_KEY_PATTERN = re.compile(r"(token|secret|password|passwd|credential|api[-_]?key)", re.IGNORECASE)


def _read_allowlisted(base_dir: Path, name: str, allowlist: tuple[str, ...]) -> str | None:
    """Read `name` from `base_dir`, refusing any name not a member of `allowlist`.
    Returns `None` on a refused name, a vanished file, or any other read failure --
    never raises. This is the single seam every read in this module goes through, so the
    per-process environment pseudo-file (absent from both module-level allowlists) has no
    path into a snapshot."""
    if name not in allowlist:
        return None
    try:
        return (base_dir / name).read_text(errors="replace")
    except OSError:
        return None


def _parse_stat(text: str) -> tuple[str | None, int | None]:
    """Parse a `/proc/<pid>/stat` or `/proc/<pid>/task/<tid>/stat` line into
    `(state, ppid)`. The comm field (field 2) can itself contain parentheses and spaces,
    so this splits on the *last* `)` rather than assuming fixed field positions from the
    start of the line, matching the documented `proc(5)` shape."""
    stripped = text.strip()
    close = stripped.rfind(")")
    if close == -1:
        return None, None
    rest = stripped[close + 1:].split()
    if not rest:
        return None, None
    state = rest[0]
    ppid: int | None = None
    if len(rest) >= 2:
        try:
            ppid = int(rest[1])
        except ValueError:
            ppid = None
    return state, ppid


def _redact_cmdline(cmdline: str) -> str:
    """Replace the value side of any word shaped like `KEY=VALUE` whose key side matches
    `_SECRET_KEY_PATTERN` with `REDACTED`. Every other word passes through unchanged."""
    words = cmdline.split(" ")
    redacted_words = []
    for word in words:
        if "=" in word:
            key, _, _ = word.partition("=")
            if _SECRET_KEY_PATTERN.search(key):
                redacted_words.append(f"{key}={REDACTED}")
                continue
        redacted_words.append(word)
    return " ".join(redacted_words)


def descendant_pids(root_pid: int, *, proc_root: str = PROC_ROOT) -> list[int]:
    """The transitive descendants of `root_pid`, sorted, never including `root_pid`
    itself. Built from every numeric `/proc` entry's own stat field 4 (ppid), so a pid
    whose `stat` file vanishes mid-walk is simply skipped rather than raised on."""
    proc_root_path = Path(proc_root)
    try:
        entries = list(proc_root_path.iterdir())
    except OSError:
        entries = []

    parent_of: dict[int, int] = {}
    for entry in entries:
        if not entry.name.isdigit():
            continue
        pid = int(entry.name)
        stat_text = _read_allowlisted(entry, "stat", PROC_READ_ALLOWLIST)
        if stat_text is None:
            continue
        _, ppid = _parse_stat(stat_text)
        if ppid is None:
            continue
        parent_of[pid] = ppid

    children_of: dict[int, list[int]] = {}
    for pid, ppid in parent_of.items():
        children_of.setdefault(ppid, []).append(pid)

    descendants: list[int] = []
    seen = {root_pid}
    frontier = [root_pid]
    while frontier:
        next_frontier: list[int] = []
        for pid in frontier:
            for child in children_of.get(pid, []):
                if child not in seen:
                    seen.add(child)
                    descendants.append(child)
                    next_frontier.append(child)
        frontier = next_frontier
    return sorted(descendants)


def thread_snapshot(pid: int, *, proc_root: str = PROC_ROOT) -> dict[str, Any]:
    """One process's own snapshot: `pid`, `ppid`, `cmdline` (redacted, null separators
    turned into spaces), `state`, and `threads` (one entry per `/proc/<pid>/task/<tid>`,
    each carrying `tid`, `comm`, `state`, and `wchan`). An unreadable field is recorded as
    the string `"unavailable"` and its name listed under an `unavailable` key -- at
    process level and, separately, at each thread's own level -- rather than dropped."""
    pid_dir = Path(proc_root) / str(pid)
    unavailable: list[str] = []

    cmdline_raw = _read_allowlisted(pid_dir, "cmdline", PROC_READ_ALLOWLIST)
    if cmdline_raw is None:
        cmdline = "unavailable"
        unavailable.append("cmdline")
    else:
        cmdline = _redact_cmdline(cmdline_raw.replace("\x00", " ").strip())

    stat_text = _read_allowlisted(pid_dir, "stat", PROC_READ_ALLOWLIST)
    if stat_text is None:
        state: Any = "unavailable"
        ppid: Any = "unavailable"
        unavailable.append("stat")
    else:
        parsed_state, parsed_ppid = _parse_stat(stat_text)
        state = parsed_state if parsed_state is not None else "unavailable"
        ppid = parsed_ppid if parsed_ppid is not None else "unavailable"

    threads: list[dict[str, Any]] = []
    task_dir = pid_dir / "task"
    try:
        tid_names = sorted(
            (entry.name for entry in task_dir.iterdir() if entry.name.isdigit()), key=int,
        )
    except OSError:
        tid_names = []
        unavailable.append("task")

    for tid_name in tid_names:
        tid_dir = task_dir / tid_name
        thread_unavailable: list[str] = []

        comm = _read_allowlisted(tid_dir, "comm", TASK_READ_ALLOWLIST)
        if comm is None:
            comm = "unavailable"
            thread_unavailable.append("comm")
        else:
            comm = comm.strip()

        thread_stat = _read_allowlisted(tid_dir, "stat", TASK_READ_ALLOWLIST)
        if thread_stat is None:
            thread_state = "unavailable"
            thread_unavailable.append("stat")
        else:
            parsed_thread_state, _ = _parse_stat(thread_stat)
            thread_state = parsed_thread_state if parsed_thread_state is not None else "unavailable"

        wchan = _read_allowlisted(tid_dir, "wchan", TASK_READ_ALLOWLIST)
        if wchan is None:
            wchan = "unavailable"
            thread_unavailable.append("wchan")
        else:
            wchan = wchan.strip()

        thread_entry: dict[str, Any] = {
            "tid": int(tid_name), "comm": comm, "state": thread_state, "wchan": wchan,
        }
        if thread_unavailable:
            thread_entry["unavailable"] = thread_unavailable
        threads.append(thread_entry)

    result: dict[str, Any] = {"pid": pid, "ppid": ppid, "cmdline": cmdline, "state": state, "threads": threads}
    if unavailable:
        result["unavailable"] = unavailable
    return result


def snapshot(root_pid: int, *, proc_root: str = PROC_ROOT, clock: Callable[[], float] = time.time) -> dict[str, Any]:
    """`thread_snapshot` for `root_pid` followed by one entry per transitive descendant,
    in pid order, wrapped with a schema version, a capture timestamp, and the proc root
    used -- so the snapshot is self-describing on its own inside a public artifact."""
    processes = [thread_snapshot(root_pid, proc_root=proc_root)]
    for pid in descendant_pids(root_pid, proc_root=proc_root):
        processes.append(thread_snapshot(pid, proc_root=proc_root))
    return {
        "snapshot_schema_version": SNAPSHOT_SCHEMA_VERSION,
        "captured_at": clock(),
        "root_pid": root_pid,
        "proc_root": str(proc_root),
        "processes": processes,
    }


def write_snapshot(out_path: str | Path, snapshot_mapping: dict[str, Any]) -> str:
    """Write `snapshot_mapping` as sorted, indented JSON plus one trailing newline --
    byte stable for one mapping, matching how scripts/perf_gate_ab_runner.py writes its
    own record. Returns the path written."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(snapshot_mapping, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return str(out_path)


def render_snapshot_text(snapshot_mapping: dict[str, Any]) -> str:
    """One line per thread naming pid, tid, comm, state, and wait location, so the same
    evidence a public JSON artifact carries is also readable in a job log with no JSON
    reader."""
    lines: list[str] = []
    for process in snapshot_mapping.get("processes", []):
        pid = process.get("pid")
        for thread in process.get("threads", []):
            lines.append(
                f"pid={pid} tid={thread.get('tid')} comm={thread.get('comm')} "
                f"state={thread.get('state')} wchan={thread.get('wchan')}"
            )
    return "\n".join(lines) + ("\n" if lines else "")


def signal_python_descendants(
    root_pid: int,
    sig: int = signal.SIGABRT,
    *,
    proc_root: str = PROC_ROOT,
    kill_fn: Callable[[int, int], None] = os.kill,
    script_marker: str = "perf_harness_runner.py",
) -> list[int]:
    """Signal only transitive descendants of `root_pid` whose command line contains
    `script_marker`, never `root_pid` itself. A SIGABRT delivered to a Python process
    running under `PYTHONFAULTHANDLER=1` dumps every thread's own Python-level traceback
    to that process's stderr, which the caller already captures -- unlike the hard kill a
    subprocess timeout issues, which is uncatchable and dumps nothing. Returns the pids
    signalled, in pid order; a per-pid failure is swallowed as a skip rather than
    raised."""
    signalled: list[int] = []
    for pid in descendant_pids(root_pid, proc_root=proc_root):
        pid_dir = Path(proc_root) / str(pid)
        cmdline_raw = _read_allowlisted(pid_dir, "cmdline", PROC_READ_ALLOWLIST)
        if cmdline_raw is None:
            continue
        cmdline = cmdline_raw.replace("\x00", " ")
        if script_marker not in cmdline:
            continue
        try:
            kill_fn(pid, sig)
        except OSError:
            continue
        signalled.append(pid)
    return sorted(signalled)


def arm(
    lead_seconds: float,
    root_pid: int,
    out_path: str | Path,
    *,
    timer_factory: Callable[..., threading.Timer] = threading.Timer,
    proc_root: str = PROC_ROOT,
    clock: Callable[[], float] = time.time,
    kill_fn: Callable[[int, int], None] = os.kill,
    signal_after_snapshot: bool = True,
) -> threading.Timer:
    """Start a timer that fires after `lead_seconds`: on firing, capture a snapshot,
    write it to `out_path`, render it to stderr so the evidence also lands in the job
    log, then -- when `signal_after_snapshot` -- signal the measurement descendants.
    That order is deliberate and load-bearing: evidence is captured before anything is
    killed. Returns the started timer; `disarm()` cancels it."""

    def _on_fire() -> None:
        captured = snapshot(root_pid, proc_root=proc_root, clock=clock)
        write_snapshot(out_path, captured)
        sys.stderr.write(render_snapshot_text(captured))
        sys.stderr.flush()
        if signal_after_snapshot:
            signal_python_descendants(root_pid, proc_root=proc_root, kill_fn=kill_fn)

    timer = timer_factory(max(lead_seconds, 0), _on_fire)
    timer.daemon = True
    timer.start()
    return timer


def disarm(timer: threading.Timer) -> None:
    """Cancel a timer returned by `arm()`. Safe to call on a timer that already fired."""
    timer.cancel()
# ----------------------------------------------------------------------------
