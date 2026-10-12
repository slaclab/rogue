from __future__ import annotations

#-----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
#-----------------------------------------------------------------------------
#  Description:
#       PyRogue PyDM Terminal Pseudo-Terminal And Screen Support
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

# This module deliberately imports no Qt. It holds the pseudo-terminal and
# screen-emulation half of the embedded terminal so that the parts with the
# least obvious failure modes, controlling-terminal setup, child reaping and
# descriptor cleanup, stay testable in a CI environment with no Qt binding.

import collections
import fcntl
import os
import shutil
import signal
import struct
import subprocess
import termios
import time

import pyte
from pyte.screens import Margins

# Fallback grid used before a widget has been laid out.
DEFAULT_COLS = 80
DEFAULT_ROWS = 24

# Smallest grid worth emulating, so a collapsed splitter cannot produce a 0x0
# screen and make cursor arithmetic meaningless.
MIN_COLS = 20
MIN_ROWS = 4

# How long to wait for a shell to honor SIGHUP before sending SIGKILL.
HUP_WAIT_S = 0.3

# Lines of scrollback retained above the live screen.
SCROLLBACK_LINES = 2000

# Run through /bin/sh, which reopens the pty slave from inside the new session
# so that it becomes the controlling terminal, then execs the real program over
# itself. $1 is the slave path and the rest is the command. See spawnShell.
_CTTY_SCRIPT = 'exec 0<>"$1" 1>&0 2>&0; shift; exec "$@"'


def computeGrid(width: float, height: float, cellWidth: float, cellHeight: float) -> tuple[int, int]:
    """Return the ``(columns, lines)`` grid that fits a viewport.

    Parameters
    ----------
    width : float
        Viewport width in pixels.
    height : float
        Viewport height in pixels.
    cellWidth : float
        Width of one character cell in pixels.
    cellHeight : float
        Height of one character cell in pixels.

    Returns
    -------
    tuple[int, int]
        Columns and lines, each clamped to a usable minimum.
    """
    if cellWidth <= 0.0 or cellHeight <= 0.0:
        return (DEFAULT_COLS, DEFAULT_ROWS)

    return (max(MIN_COLS, int(width // cellWidth)),
            max(MIN_ROWS, int(height // cellHeight)))


def resolveShell() -> str:
    """Return an absolute path to the shell to run.

    Resolved in the parent process so that no ``PATH`` lookup ever happens in a
    child process.

    Returns
    -------
    str
        Absolute path to an executable shell.

    Raises
    ------
    FileNotFoundError
        If neither ``$SHELL`` nor any known fallback is executable.
    """
    candidate = os.environ.get('SHELL') or 'bash'
    path = candidate if os.path.isabs(candidate) else shutil.which(candidate)

    if path is not None and os.access(path, os.X_OK):
        return path

    for fallback in ('/bin/bash', '/bin/sh'):
        if os.access(fallback, os.X_OK):
            return fallback

    raise FileNotFoundError(f"no usable shell found (tried {candidate!r})")


def buildEnv() -> dict[str, str]:
    """Build the child environment for the shell.

    ``COLUMNS`` and ``LINES`` are removed so that ``TIOCSWINSZ`` stays the
    single source of truth for geometry.

    Returns
    -------
    dict[str, str]
        Environment for the child process.
    """
    env = dict(os.environ)
    env.pop('COLUMNS', None)
    env.pop('LINES', None)
    env['TERM'] = 'xterm'
    env['TERM_PROGRAM'] = 'pyrogue-pydm-terminal'
    return env


def setWinSize(fd: int, rows: int, cols: int) -> None:
    """Push a window size onto a pty master.

    ``struct winsize`` is ``{ws_row, ws_col, ws_xpixel, ws_ypixel}``, so rows
    come first here. That is the opposite order from ``pyte.Screen(columns,
    lines)``, which is why callers should not pass these positionally without
    checking.

    Parameters
    ----------
    fd : int
        Pty master descriptor.
    rows : int
        Terminal height in characters.
    cols : int
        Terminal width in characters.
    """
    fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack('HHHH', rows, cols, 0, 0))


def spawnShell(rows: int, cols: int, argv: list[str] | None = None, useCtty: bool = True):
    """Start an interactive shell on a new pseudo-terminal.

    ``subprocess`` is used rather than :func:`pty.fork` because
    :func:`os.forkpty` raises a ``DeprecationWarning`` in a multi-threaded
    process from Python 3.12 onward, and the Rogue GUI always has Rogue,
    ZeroMQ and Qt threads running. ``subprocess`` execs through the
    async-signal-safe path in ``_posixsubprocess`` instead.

    ``start_new_session`` makes the child a session leader but cannot give it a
    controlling terminal, because a controlling terminal is only acquired when a
    session leader *opens* a tty itself and here the parent opened the slave.
    Without one there is no foreground process group, so terminal-generated
    signals go nowhere and Ctrl-C, Ctrl-Z and shell job control silently stop
    working. The ``/bin/sh`` step exists to fix exactly that: it reopens this
    same slave from inside the new session, which acquires it as the controlling
    terminal, then execs the real shell over itself.

    Parameters
    ----------
    rows : int
        Initial terminal height in characters.
    cols : int
        Initial terminal width in characters.
    argv : list[str] | None, optional
        Command to run. Defaults to an interactive :func:`resolveShell`.
    useCtty : bool, optional
        Acquire a controlling terminal. Defaults to ``True``. Setting this to
        ``False`` produces a child with no controlling terminal, and exists so
        that tests can pin the difference.

    Returns
    -------
    tuple[subprocess.Popen, int]
        The child process and the pty master descriptor, already set
        non-blocking.

    Notes
    -----
    Whether a child ends up with a controlling terminal otherwise depends on
    what is being run: an interactive ``bash`` acquires one itself, while most
    programs do not. Routing through ``/bin/sh`` makes it guaranteed instead of
    dependent on undocumented shell behavior.
    """
    if argv is None:
        argv = [resolveShell(), '-i']

    masterFd, slaveFd = os.openpty()

    try:
        # Set the size before exec so the first prompt is drawn at the right
        # width instead of needing a redraw.
        setWinSize(masterFd, rows, cols)
        os.set_blocking(masterFd, False)

        if useCtty:
            command = ['/bin/sh', '-c', _CTTY_SCRIPT, 'sh', os.ttyname(slaveFd)] + argv
        else:
            command = list(argv)

        proc = subprocess.Popen(
            command,
            stdin=slaveFd,
            stdout=slaveFd,
            stderr=slaveFd,
            start_new_session=True,
            env=buildEnv(),
        )
    except BaseException:
        os.close(masterFd)
        raise
    finally:
        # Mandatory: while the parent holds a slave descriptor open, the master
        # never reports end of file when the child exits.
        try:
            os.close(slaveFd)
        except OSError:
            pass

    return (proc, masterFd)


def signalGroup(pid: int, sig: int) -> None:
    """Signal a child's process group, falling back to the child alone.

    Parameters
    ----------
    pid : int
        Child process id.
    sig : int
        Signal number to send.
    """
    try:
        os.killpg(os.getpgid(pid), sig)
        return
    except OSError:
        pass

    try:
        os.kill(pid, sig)
    except OSError:
        pass


def closeShell(proc, masterFd: int, hupWait: float = HUP_WAIT_S) -> int:
    """Close a pty and terminate the shell, leaving no zombie behind.

    Safe to call more than once.

    ``SIGHUP`` is sent before ``SIGKILL`` rather than ``SIGTERM`` because an
    interactive ``bash`` ignores ``SIGTERM`` but does exit on a hangup.

    Parameters
    ----------
    proc : subprocess.Popen | None
        Child process, or ``None`` if there is nothing to reap.
    masterFd : int
        Pty master descriptor, or a negative value if already closed.
    hupWait : float, optional
        Seconds to wait for the hangup to take effect before forcing.

    Returns
    -------
    int
        The pty master descriptor to store back, always ``-1``.
    """
    if masterFd >= 0:
        try:
            os.close(masterFd)
        except OSError:
            pass

    if proc is None:
        return -1

    if proc.poll() is None:
        signalGroup(proc.pid, signal.SIGHUP)

        deadline = time.monotonic() + hupWait
        while proc.poll() is None and time.monotonic() < deadline:
            time.sleep(0.01)

    if proc.poll() is None:
        signalGroup(proc.pid, signal.SIGKILL)
        try:
            proc.wait(timeout=1.0)
        except subprocess.TimeoutExpired:
            pass

    return -1


def rowRuns(screen: pyte.Screen, y: int, trim: bool = False) -> list[tuple[str, tuple]]:
    """Run-length encode one screen row into ``(text, attributes)`` pairs.

    Terminal output is overwhelmingly long stretches of one attribute, so a row
    of 120 cells typically collapses to a handful of runs. ``attributes`` is the
    ``pyte.screens.Char`` tuple with the character data removed, that is
    ``(fg, bg, bold, italics, underscore, strikethrough, reverse, blink)``. It is
    hashable, which makes it usable directly as a render cache key.

    Parameters
    ----------
    screen : pyte.Screen
        Screen to read.
    y : int
        Row index.
    trim : bool, optional
        Drop trailing blank cells. Used for scrollback, where nothing depends on
        column positions. The live screen must not be trimmed, because the
        renderer maps a string column onto a screen column when placing the
        cursor.

    Returns
    -------
    list[tuple[str, tuple]]
        Runs in left to right order. Empty for a row that trims away entirely.
    """
    row = screen.buffer[y]
    columns = screen.columns

    if trim:
        # A blank cell with a non-default background is kept, because a colored
        # background is visible even with no character in it.
        while columns > 0:
            cell = row[columns - 1]
            if cell.data != ' ' or cell.bg != 'default' or cell.reverse:
                break
            columns -= 1

    runs = []
    start = 0

    while start < columns:
        attrs = row[start][1:]
        end = start + 1

        while end < columns and row[end][1:] == attrs:
            end += 1

        runs.append((''.join(row[x].data for x in range(start, end)), attrs))
        start = end

    return runs


def screenRuns(screen: pyte.Screen) -> list[list[tuple[str, tuple]]]:
    """Run-length encode the whole live screen, one entry per row.

    Parameters
    ----------
    screen : pyte.Screen
        Screen to read.

    Returns
    -------
    list[list[tuple[str, tuple]]]
        One list of runs per screen row.
    """
    return [rowRuns(screen, y) for y in range(screen.lines)]


class TerminalScreen(pyte.Screen):
    """A ``pyte`` screen with query replies and scrollback capture.

    Two behaviours are added to the base screen.

    ``pyte.Screen.write_process_input`` is a no-op by default, which silently
    breaks anything that probes the terminal. Cursor position reports
    (``ESC[6n``) and device attribute requests (``ESC[c``) are used by readline,
    ``less`` and many shell prompts, and a program that sends one will wait for
    a reply that never arrives.

    ``index`` is overloaded to keep lines that scroll off the top, which the
    base screen simply discards. ``pyte.HistoryScreen`` also offers scrollback
    but is not used here: it hooks ``__getattribute__`` and builds a fresh
    wrapper closure on every access to a wrapped event, including ``draw``,
    which the stream calls once per character. It also repurposes ``display``
    to show the paged view, so cursor arithmetic would have to become
    history-position aware.

    Parameters
    ----------
    columns : int
        Screen width in characters.
    lines : int
        Screen height in characters.
    writer : callable
        Called with the reply bytes to send to the child process.
    scrollback : int, optional
        Maximum number of scrolled-off lines to retain.

    Attributes
    ----------
    scrolledOff : collections.deque
        Rows that have scrolled off the top and not yet been consumed by a
        renderer, each as a list of ``(text, attributes)`` runs. Callers are
        expected to drain this. Attributes are kept rather than flattened to
        plain text so that colored output keeps its colors after scrolling out
        of the live screen.
    """

    def __init__(self, columns: int, lines: int, writer,
                 scrollback: int = SCROLLBACK_LINES) -> None:
        # Assigned before the base constructor because Screen.__init__ calls
        # reset(), which can already route through these.
        self._writer = writer
        self.scrolledOff = collections.deque(maxlen=scrollback)
        pyte.Screen.__init__(self, columns, lines)

    def write_process_input(self, data: str) -> None:
        """Send a terminal reply back to the child process."""
        self._writer(data.encode('utf-8', errors='replace'))

    def index(self) -> None:
        """Scroll down, keeping the line that leaves the top."""
        top, bottom = self.margins or Margins(0, self.lines - 1)

        if self.cursor.y == bottom:
            # Trailing padding is dropped here. Only the live region needs
            # column-exact text, because that is where the cursor is drawn.
            self.scrolledOff.append(rowRuns(self, top, trim=True))

        pyte.Screen.index(self)

    def resize(self, lines: int | None = None, columns: int | None = None) -> None:
        """Resize the screen, keeping rows that a shrink would discard.

        The base implementation drops the excess rows off the top by deleting
        them outright rather than scrolling them, so they never pass through
        :meth:`index` and would otherwise be lost. Making the window shorter
        should move that content into the scrollback, not destroy it.
        """
        newLines = self.lines if lines is None else lines

        for y in range(max(0, self.lines - newLines)):
            runs = rowRuns(self, y, trim=True)
            # Blank rows carry no history. Skipping them keeps a first layout,
            # which usually shrinks the screen from its unshown default size,
            # from filling the scrollback with empty lines.
            if runs:
                self.scrolledOff.append(runs)

        pyte.Screen.resize(self, lines=lines, columns=columns)


def screenLines(screen: pyte.Screen) -> list[str]:
    """Return the current screen rows as text.

    Rows keep their trailing padding so a character column in the string
    matches the same column on the emulated screen, which is what makes cursor
    placement exact.

    Parameters
    ----------
    screen : pyte.Screen
        Screen whose current viewport should be rendered.

    Returns
    -------
    list[str]
        One string per screen row.
    """
    try:
        return list(screen.display)
    except AssertionError:
        # pyte asserts on some combining character sequences. A bad frame must
        # not take the GUI down with it.
        return [''] * screen.lines


def screenToText(screen: pyte.Screen) -> str:
    """Flatten a ``pyte`` screen viewport into displayable text.

    Parameters
    ----------
    screen : pyte.Screen
        Screen whose current viewport should be rendered.

    Returns
    -------
    str
        Newline-joined screen rows.
    """
    return '\n'.join(screenLines(screen))
