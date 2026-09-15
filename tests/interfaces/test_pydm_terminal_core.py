#!/usr/bin/env python3
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

# Exercises the pseudo-terminal and screen-emulation half of the embedded
# terminal. This half imports no Qt on purpose, so these tests run in CI
# environments that have no Qt binding and no display, which is where the
# behaviour with the least obvious failure modes lives: controlling-terminal
# setup, child reaping and descriptor cleanup.

import errno
import importlib.util
import os
import select
import sys
import time
from pathlib import Path

import pytest

try:
    import pyte
except Exception as exc:
    pytest.skip(f"pyte unavailable: {exc}", allow_module_level=True)


def _loadTerminalCore():
    """Load ``terminal_core`` without importing the widget package.

    ``pyrogue.pydm.widgets.__init__`` imports every widget, so the ordinary
    import path drags in pydm and a Qt binding even for a module that needs
    neither. Loading the file directly is what keeps these tests running in a
    CI environment that has no Qt binding.
    """
    path = Path(__file__).resolve().parents[2] / "python/pyrogue/pydm/widgets/terminal_core.py"
    spec = importlib.util.spec_from_file_location("rogue_test_terminal_core", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


tc = _loadTerminalCore()

posixOnly = pytest.mark.skipif(os.name != 'posix', reason="pseudo-terminals are POSIX only")


def _drain(fd, seconds=1.0):
    """Read from a non-blocking descriptor for a bounded time."""
    out = b''
    end = time.monotonic() + seconds

    while time.monotonic() < end:
        ready, _, _ = select.select([fd], [], [], 0.05)
        if not ready:
            continue
        try:
            chunk = os.read(fd, 4096)
        except BlockingIOError:
            continue
        except OSError:
            break
        if not chunk:
            break
        out += chunk

    return out


def _feed(data, columns=20, lines=4):
    """Return a screen with ``data`` fed through a byte stream."""
    screen = pyte.Screen(columns, lines)
    stream = pyte.ByteStream(screen)
    stream.feed(data)
    return screen


# ---------------------------------------------------------------------------
# Grid arithmetic
# ---------------------------------------------------------------------------

def test_compute_grid_exact_fit():
    assert tc.computeGrid(800.0, 400.0, 8.0, 16.0) == (100, 25)


def test_compute_grid_rounds_down_partial_cells():
    assert tc.computeGrid(805.0, 407.0, 8.0, 16.0) == (100, 25)


def test_compute_grid_clamps_to_minimum():
    assert tc.computeGrid(10.0, 10.0, 8.0, 16.0) == (tc.MIN_COLS, tc.MIN_ROWS)


def test_compute_grid_falls_back_on_zero_cell():
    assert tc.computeGrid(800.0, 400.0, 0.0, 16.0) == (tc.DEFAULT_COLS, tc.DEFAULT_ROWS)


# ---------------------------------------------------------------------------
# Shell and environment resolution
# ---------------------------------------------------------------------------

def test_resolve_shell_returns_executable():
    path = tc.resolveShell()
    assert os.path.isabs(path)
    assert os.access(path, os.X_OK)


def test_resolve_shell_falls_back_when_shell_is_bogus(monkeypatch):
    monkeypatch.setenv('SHELL', '/nonexistent/definitely/not/a/shell')
    assert os.access(tc.resolveShell(), os.X_OK)


def test_build_env_strips_columns_and_lines(monkeypatch):
    monkeypatch.setenv('COLUMNS', '999')
    monkeypatch.setenv('LINES', '999')
    env = tc.buildEnv()
    # TIOCSWINSZ must be the only source of geometry, otherwise a stale
    # COLUMNS wins and the shell wraps at the wrong column.
    assert 'COLUMNS' not in env
    assert 'LINES' not in env
    assert env['TERM'] == 'xterm'


# ---------------------------------------------------------------------------
# Screen emulation
# ---------------------------------------------------------------------------

def test_plain_text_renders():
    assert tc.screenToText(_feed(b'hello')).split('\n')[0].startswith('hello')


def test_newline_advances_a_line():
    lines = tc.screenToText(_feed(b'one\r\ntwo')).split('\n')
    assert lines[0].startswith('one')
    assert lines[1].startswith('two')


def test_color_escape_is_consumed_not_rendered():
    # v1 renders monochrome, but pyte must still swallow the SGR sequence so
    # escape bytes never leak into the displayed text.
    text = tc.screenToText(_feed(b'\x1b[31mred\x1b[0m'))
    assert 'red' in text
    assert '\x1b' not in text
    assert '31m' not in text


def test_color_attribute_is_still_parsed():
    # Pins the contract a future colour-capable renderer would consume.
    assert _feed(b'\x1b[31mR').buffer[0][0].fg == 'red'


def test_cursor_addressing_positions_text():
    # CSI 2;3 H moves to row 2, column 3, both 1-based.
    screen = _feed(b'\x1b[2;3Hx')
    assert screen.cursor.y == 1
    assert tc.screenToText(screen).split('\n')[1][2] == 'x'


def test_carriage_return_overwrites_in_place():
    assert tc.screenToText(_feed(b'abc\rZ')).split('\n')[0].startswith('Zbc')


def test_erase_display_clears_text():
    assert 'junk' not in tc.screenToText(_feed(b'junk\x1b[2J'))


def test_rendered_geometry_matches_screen():
    lines = tc.screenToText(_feed(b'x', columns=20, lines=4)).split('\n')
    assert len(lines) == 4
    # Padding is retained so a string column matches a screen column, which is
    # what makes the widget's cursor placement exact.
    assert all(len(line) == 20 for line in lines)


def test_partial_utf8_across_feeds():
    # The single most important decoding regression: a multi-byte character
    # split across two reads must not become two replacement characters.
    screen = pyte.Screen(20, 4)
    stream = pyte.ByteStream(screen)
    stream.feed(b'\xc3')
    stream.feed(b'\xa9')
    assert tc.screenToText(screen).split('\n')[0][0] == 'é'


def test_invalid_utf8_is_replaced_not_raised():
    assert tc.screenToText(_feed(b'\xff'))[0] == '�'


def test_dirty_tracks_changed_lines():
    screen = pyte.Screen(20, 4)
    stream = pyte.ByteStream(screen)
    screen.dirty.clear()
    stream.feed(b'hi')
    assert screen.dirty == {0}


def test_resize_keyword_ordering():
    # pyte.Screen() takes columns first but resize() takes lines first. Getting
    # this backwards transposes the screen.
    screen = pyte.Screen(20, 4)
    screen.resize(lines=10, columns=40)
    assert (screen.lines, screen.columns) == (10, 40)


# ---------------------------------------------------------------------------
# Terminal query replies
# ---------------------------------------------------------------------------

def _reply(data):
    """Return the bytes a TerminalScreen writes back in answer to ``data``."""
    sent = []
    screen = tc.TerminalScreen(20, 4, sent.append)
    pyte.ByteStream(screen).feed(data)
    return b''.join(sent)


def test_screen_answers_cursor_position_report():
    # Without this, readline, less and many shell prompts hang waiting for a
    # reply that pyte's default no-op write_process_input never sends. The
    # introducer is left unasserted because whether pyte emits the 7-bit
    # "\x1b[" or the 8-bit "\x9b" form is its internal choice; both are valid
    # and terminals accept either.
    reply = _reply(b'\x1b[6n')
    assert reply.endswith(b'1;1R')


def test_screen_reports_moved_cursor_position():
    assert _reply(b'\x1b[2;3H\x1b[6n').endswith(b'2;3R')


def test_screen_answers_device_attributes():
    assert _reply(b'\x1b[c') != b''


# ---------------------------------------------------------------------------
# Scrollback capture
# ---------------------------------------------------------------------------

def _scrolled(data, columns=20, lines=3, scrollback=100):
    screen = tc.TerminalScreen(columns, lines, lambda b: None, scrollback=scrollback)
    pyte.ByteStream(screen).feed(data)
    return screen


def _text(runs):
    """Flatten a row of runs back to plain text."""
    return ''.join(text for text, _attrs in runs)


def _scrollbackText(screen):
    return [_text(runs) for runs in screen.scrolledOff]


def test_nothing_scrolls_off_until_the_screen_fills():
    screen = _scrolled(b'a\r\nb\r\nc')
    assert list(screen.scrolledOff) == []


def test_lines_scrolling_off_the_top_are_kept():
    # A 3 line screen: writing 5 lines pushes the first two into scrollback.
    screen = _scrolled(b'one\r\ntwo\r\nthree\r\nfour\r\nfive')
    assert _scrollbackText(screen) == ['one', 'two']
    # The live screen keeps only what still fits.
    assert [line.rstrip() for line in tc.screenLines(screen)] == ['three', 'four', 'five']


def test_scrollback_lines_are_stripped_of_padding():
    screen = _scrolled(b'x\r\n\r\n\r\n\r\n')
    assert all(line == line.rstrip() for line in _scrollbackText(screen))


def test_scrollback_is_bounded():
    # The deque bound is what stops a long-lived terminal growing without end.
    screen = _scrolled(b''.join(b'line%d\r\n' % i for i in range(50)), scrollback=10)
    # Feeding 50 terminated lines onto a 3 line screen scrolls off line0..line47,
    # leaving line48 and line49 plus the trailing empty line live. Only the most
    # recent 10 scrolled-off lines are kept.
    assert _scrollbackText(screen) == [f'line{i}' for i in range(38, 48)]


def test_scrollback_survives_a_resize():
    screen = _scrolled(b'one\r\ntwo\r\nthree\r\nfour\r\nfive')
    before = list(screen.scrolledOff)
    screen.resize(lines=6, columns=30)
    assert list(screen.scrolledOff) == before


def test_shrinking_the_screen_keeps_the_lost_rows():
    # pyte's own resize deletes the excess rows off the top outright rather than
    # scrolling them, so they never reach index(). Making a window shorter has to
    # move that content into the scrollback, not destroy it.
    screen = _scrolled(b'one\r\ntwo\r\nthree', lines=4)
    assert list(screen.scrolledOff) == []

    screen.resize(lines=2, columns=20)

    assert _scrollbackText(screen)[:2] == ['one', 'two']


def test_growing_the_screen_keeps_scrollback_untouched():
    screen = _scrolled(b'one\r\ntwo\r\nthree\r\nfour\r\nfive')
    before = list(screen.scrolledOff)
    screen.resize(lines=10, columns=40)
    assert list(screen.scrolledOff) == before


def test_scrollback_keeps_color_attributes():
    # Without this a colored line would turn grey the moment it scrolled out of
    # the live screen, which is a very visible artifact.
    screen = _scrolled(b'\x1b[31mRED\x1b[0m\r\nb\r\nc\r\nd\r\ne')
    first = screen.scrolledOff[0]
    assert _text(first) == 'RED'
    assert first[0][1][0] == 'red'


# ---------------------------------------------------------------------------
# Run-length encoding
# ---------------------------------------------------------------------------

def test_row_runs_collapses_uniform_text_to_one_run():
    runs = tc.rowRuns(_feed(b'hello', columns=20, lines=2), 0, trim=True)
    assert runs == [('hello', _feed(b'x', 20, 2).buffer[0][0][1:])]


def test_row_runs_splits_on_attribute_change():
    screen = _feed(b'ab\x1b[31mcd\x1b[0mef', columns=20, lines=2)
    runs = tc.rowRuns(screen, 0, trim=True)
    assert [text for text, _ in runs] == ['ab', 'cd', 'ef']
    assert [attrs[0] for _, attrs in runs] == ['default', 'red', 'default']


def test_row_runs_untrimmed_covers_every_column():
    # The live screen must stay column exact, because the renderer maps a string
    # column onto a screen column when it places the cursor.
    screen = _feed(b'hi', columns=20, lines=2)
    assert sum(len(text) for text, _ in tc.rowRuns(screen, 0)) == 20


def test_row_runs_trimmed_drops_trailing_blanks():
    screen = _feed(b'hi', columns=20, lines=2)
    assert sum(len(text) for text, _ in tc.rowRuns(screen, 0, trim=True)) == 2


def test_row_runs_trim_keeps_a_colored_background():
    # A blank cell with a background color is visible, so it must survive the
    # trim even though it holds no character.
    screen = _feed(b'\x1b[44m   ', columns=10, lines=2)
    runs = tc.rowRuns(screen, 0, trim=True)
    assert runs and runs[0][1][1] == 'blue'


def test_real_output_collapses_to_few_runs():
    # Colorized output is long stretches of one attribute, which is what keeps
    # per-run rendering cheap. This pins that assumption.
    body = b''.join(b'\x1b[32mok\x1b[0m plain text here\r\n' for _ in range(10))
    screen = _feed(body, columns=80, lines=12)
    assert max(len(tc.rowRuns(screen, y)) for y in range(screen.lines)) <= 6


def test_screen_runs_returns_one_entry_per_row():
    screen = _feed(b'a\r\nb', columns=10, lines=4)
    runs = tc.screenRuns(screen)
    assert len(runs) == 4
    assert _text(runs[0]).startswith('a')


def test_history_screen_is_not_used():
    # pyte.HistoryScreen hooks __getattribute__ and rebuilds a wrapper closure
    # on every access to a wrapped event, including draw, which the stream calls
    # once per character. Scrollback is captured in index() instead.
    assert not issubclass(tc.TerminalScreen, pyte.HistoryScreen)


# ---------------------------------------------------------------------------
# Window size
# ---------------------------------------------------------------------------

@posixOnly
def test_winsize_roundtrips_through_the_pty():
    proc, master = tc.spawnShell(24, 80, argv=['/bin/sh', '-i'])
    try:
        _drain(master, 0.5)
        tc.setWinSize(master, 30, 100)
        os.write(master, b'stty size\n')
        out = _drain(master, 1.5)
        assert b'30 100' in out
    finally:
        tc.closeShell(proc, master)


# ---------------------------------------------------------------------------
# Controlling terminal and job control
# ---------------------------------------------------------------------------

# Reports the child's real controlling-terminal state. Deliberately a Python
# child rather than a shell: an interactive bash acquires a controlling terminal
# by itself, which would mask whether spawnShell provided one.
_CTTY_PROBE = (
    'import os,sys\n'
    'try:\n'
    '    fd=os.open("/dev/tty", os.O_RDWR); os.close(fd); c="YES"\n'
    'except OSError: c="NO"\n'
    'try: f=str(os.tcgetpgrp(0)==os.getpgrp())\n'
    'except OSError: f="ENOTTY"\n'
    'sys.stdout.write("PROBE CTTY=%s FG=%s\\n"%(c,f)); sys.stdout.flush()\n'
)


def _probeCtty(useCtty):
    """Return the probe output line for a child spawned with or without a ctty."""
    proc, master = tc.spawnShell(24, 80, argv=[sys.executable, '-c', _CTTY_PROBE],
                                 useCtty=useCtty)
    try:
        out = _drain(master, 5.0).decode(errors='replace')
    finally:
        tc.closeShell(proc, master)

    for line in out.splitlines():
        if 'PROBE' in line:
            return line.strip()

    pytest.fail(f"probe produced no output: {out!r}")


@posixOnly
def test_child_gets_a_controlling_terminal():
    # A controlling terminal is what gives the pty a foreground process group.
    # Without one the line discipline has nothing to signal, so Ctrl-C, Ctrl-Z
    # and shell job control all silently stop working.
    assert _probeCtty(True) == 'PROBE CTTY=YES FG=True'


@posixOnly
def test_without_the_reopen_step_there_is_no_controlling_terminal():
    # Negative control. subprocess(start_new_session=True) on its own cannot
    # give the child a controlling terminal: the parent opened the slave, and a
    # ctty is only acquired when a session leader opens a tty itself. This test
    # exists so that nobody "simplifies away" the /bin/sh reopen step in
    # spawnShell without noticing what it buys.
    assert _probeCtty(False) == 'PROBE CTTY=NO FG=ENOTTY'


@posixOnly
def test_sigint_interrupts_the_foreground_job():
    # End-to-end proof that the controlling terminal works: writing ETX must
    # make the line discipline signal the foreground process group, so the shell
    # returns to a prompt instead of waiting out the sleep.
    #
    # The prompt is set to a unique token first. The pty echoes back everything
    # written to it, so matching on anything that is also typed would match the
    # echo rather than the shell's own output.
    proc, master = tc.spawnShell(24, 80)
    try:
        _drain(master, 1.0)
        os.write(master, b"PS1='<<RDY>>'\n")
        _drain(master, 1.0)

        os.write(master, b'sleep 30\n')
        _drain(master, 0.5)

        os.write(master, b'\x03')
        # The sleep is far longer than this window, so a prompt appearing here
        # can only mean the foreground job was actually interrupted.
        out = _drain(master, 5.0)

        assert b'<<RDY>>' in out, "the shell never returned to a prompt"
        assert proc.poll() is None, "the shell itself must survive the interrupt"
    finally:
        tc.closeShell(proc, master)


# ---------------------------------------------------------------------------
# Teardown
# ---------------------------------------------------------------------------

@posixOnly
def test_master_reports_eof_or_eio_when_child_exits():
    # Documents the platform split the read loop has to handle: Linux raises
    # EIO on the master once the child is gone, macOS returns an empty read.
    proc, master = tc.spawnShell(24, 80, argv=['/bin/sh', '-i'])
    os.write(master, b'exit\n')

    sawEnd = False
    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline:
        select.select([master], [], [], 0.1)
        try:
            if os.read(master, 4096) == b'':
                sawEnd = True
                break
        except BlockingIOError:
            continue
        except OSError as exc:
            assert exc.errno in (errno.EIO, errno.EBADF)
            sawEnd = True
            break

    tc.closeShell(proc, master)
    assert sawEnd


@posixOnly
def test_close_reaps_child_leaving_no_zombie():
    proc, master = tc.spawnShell(24, 80)
    pid = proc.pid
    tc.closeShell(proc, master)

    with pytest.raises(ChildProcessError):
        os.waitpid(pid, os.WNOHANG)


@posixOnly
def test_close_kills_a_shell_that_ignores_hangup():
    proc, master = tc.spawnShell(24, 80, argv=['/bin/sh', '-i'])
    _drain(master, 0.5)
    os.write(master, b'trap "" HUP TERM; sleep 60\n')
    _drain(master, 0.5)

    started = time.monotonic()
    tc.closeShell(proc, master)
    elapsed = time.monotonic() - started

    assert proc.poll() is not None, "SIGKILL escalation must terminate it"
    assert elapsed < 3.0


@posixOnly
def test_close_is_idempotent():
    proc, master = tc.spawnShell(24, 80, argv=['/bin/sh', '-i'])
    assert tc.closeShell(proc, master) == -1
    assert tc.closeShell(proc, -1) == -1


@posixOnly
@pytest.mark.skipif(not sys.platform.startswith('linux'), reason="reads /proc/self/fd")
def test_repeated_spawn_and_close_does_not_leak_descriptors():
    before = len(os.listdir('/proc/self/fd'))

    for _ in range(10):
        proc, master = tc.spawnShell(24, 80, argv=['/bin/sh', '-i'])
        tc.closeShell(proc, master)

    assert len(os.listdir('/proc/self/fd')) == before


@posixOnly
def test_spawn_does_not_warn_about_forking(recwarn):
    # os.forkpty() raises a DeprecationWarning in a multi-threaded process from
    # Python 3.12, and the Rogue GUI always has Rogue, ZeroMQ and Qt threads.
    # That is why this spawns through subprocess instead of pty.fork().
    proc, master = tc.spawnShell(24, 80, argv=['/bin/sh', '-i'])
    tc.closeShell(proc, master)

    assert [w for w in recwarn if issubclass(w.category, DeprecationWarning)] == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
