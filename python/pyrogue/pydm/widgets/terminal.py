from __future__ import annotations

#-----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
#-----------------------------------------------------------------------------
#  Description:
#       PyRogue PyDM Embedded Linux Terminal Widget
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

import errno
import os
import re

import pyte
import pyte.graphics
from qtpy.QtCore import QSocketNotifier, QTimer, Qt
from qtpy.QtGui import (
    QColor,
    QFont,
    QFontDatabase,
    QFontMetricsF,
    QPalette,
    QTextCharFormat,
    QTextCursor,
)
from qtpy.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QPlainTextEdit,
    QPushButton,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from pyrogue.pydm.widgets.terminal_core import (
    SCROLLBACK_LINES,
    TerminalScreen,
    closeShell,
    computeGrid,
    screenRuns,
    setWinSize,
    spawnShell,
)

# Repaint coalescing interval in milliseconds. A shell dumping output arrives as
# many small reads; without coalescing each one would trigger a full repaint.
_REPAINT_MS = 30

# Resize debounce. Every TIOCSWINSZ raises SIGWINCH and an interactive shell
# redraws its prompt, so dragging a window edge would otherwise storm the pty.
_RESIZE_MS = 50

_READ_CHUNK = 8192

# Ceiling on bytes absorbed per readable notification. pyte's feed() is pure
# Python, so an unbounded drain of `cat bigfile` would stall the event loop for
# seconds. QSocketNotifier is level triggered, so the remainder simply re-fires
# on the next event loop turn and the GUI stays responsive.
_MAX_BYTES_PER_POLL = 64 * 1024

# pyte stores DEC private modes shifted left by 5. 2004 is bracketed paste,
# which bash enables by default from 5.1 onward.
_BRACKETED_PASTE = 2004 << 5

# Size of the detached terminal window, used only when it has no better hint.
_DETACHED_SIZE = (900, 600)

# A shell that exits without the user having typed anything was not exited on
# purpose, it failed to start. After this many such exits in a row the terminal
# stops restarting, so a shell that cannot run does not spawn in a loop.
#
# Elapsed time is deliberately not used to make this distinction. Exiting twice
# in quick succession is something a user can easily do, and treating that as a
# failure would dead-end the terminal exactly as it did before it restarted.
_MAX_STARTUP_FAILURES = 3

# Dark theme. A terminal is read as a terminal, so it keeps its own colors
# rather than following the surrounding PyDM palette.
_COLOR_BG = '#1e1e1e'
_COLOR_FG = '#d4d4d4'
_COLOR_SELECTION = '#264f78'

# pyte names the eight base colors after the SGR 30-37 order, so a name maps
# straight onto an index into its own 256 color table. Entries 0-7 are the
# normal shades and 8-15 the bright ones, which keeps the palette in one place
# instead of a hand-maintained copy.
_COLOR_INDEX = {name: index for index, name in enumerate(
    ('black', 'red', 'green', 'brown', 'blue', 'magenta', 'cyan', 'white'))}

# 256 color and 24 bit values arrive from pyte already as six hex digits.
_HEX_COLOR = re.compile(r'[0-9a-fA-F]{6}')


def resolveColor(value: str, bright: bool = False) -> QColor | None:
    """Map a ``pyte`` color to a ``QColor``.

    Parameters
    ----------
    value : str
        Colour as pyte reports it: ``'default'``, one of the eight base names,
        a ``bright``-prefixed name, or six hex digits for 256 colour and 24 bit.
    bright : bool, optional
        Select the bright shade of a base name. Bold text is rendered in the
        bright shade, which is the convention every colorizing tool assumes.

    Returns
    -------
    QColor | None
        ``None`` when the value is the default or is not recognised, so the
        caller can fall back to the theme colour. pyte's own tables contain at
        least one misspelled name, so unrecognised input has to be tolerated.
    """
    if not value or value == 'default':
        return None

    name = value[6:] if value.startswith('bright') else value
    index = _COLOR_INDEX.get(name)

    if index is not None:
        if bright or value.startswith('bright'):
            index += 8
        return QColor('#' + pyte.graphics.FG_BG_256[index])

    if _HEX_COLOR.fullmatch(value):
        return QColor('#' + value)

    return None


def keyToBytes(key: int, modifiers: int, text: str) -> bytes:
    """Translate a Qt key press into the byte sequence a terminal expects.

    Kept free of ``QKeyEvent`` so it can be unit tested without constructing a
    ``QApplication``. The sequences follow the ``xterm`` conventions, matching
    the ``TERM`` value exported to the child shell. Changing one requires
    changing the other.

    Parameters
    ----------
    key : int
        Qt key code, for example ``Qt.Key_Up``.
    modifiers : int
        Qt keyboard modifier flags.
    text : str
        Text the key event produced, used for ordinary printable input.

    Returns
    -------
    bytes
        Bytes to write to the pty, or ``b''`` when the key produces no input.

    Notes
    -----
    Ctrl-C has to reach the shell as ``ETX`` so it can interrupt the foreground
    job, so copy and paste are bound to Ctrl+Shift+C and Ctrl+Shift+V. Those
    two chords return ``b''`` here and are handled as clipboard actions by the
    widget.
    """
    ctrl = bool(modifiers & Qt.ControlModifier)
    shift = bool(modifiers & Qt.ShiftModifier)
    alt = bool(modifiers & Qt.AltModifier)

    if ctrl and shift and key in (Qt.Key_C, Qt.Key_V):
        return b''

    if key in (Qt.Key_Shift, Qt.Key_Control, Qt.Key_Alt, Qt.Key_Meta,
               Qt.Key_CapsLock, Qt.Key_NumLock, Qt.Key_ScrollLock):
        return b''

    # Control characters are computed rather than taken from text(), which Qt
    # populates for Ctrl+A..Z on some platforms but not for Ctrl+Space or the
    # bracket group.
    if ctrl and not alt:
        if key == Qt.Key_Space:
            return b'\x00'
        if Qt.Key_A <= key <= Qt.Key_Underscore:
            return bytes([key & 0x1f])

    simple = {
        Qt.Key_Return:    b'\r',
        Qt.Key_Enter:     b'\r',
        Qt.Key_Backspace: b'\x7f',
        Qt.Key_Tab:       b'\t',
        Qt.Key_Backtab:   b'\x1b[Z',
        Qt.Key_Escape:    b'\x1b',
        Qt.Key_Up:        b'\x1b[A',
        Qt.Key_Down:      b'\x1b[B',
        Qt.Key_Right:     b'\x1b[C',
        Qt.Key_Left:      b'\x1b[D',
        Qt.Key_Home:      b'\x1b[H',
        Qt.Key_End:       b'\x1b[F',
        Qt.Key_Insert:    b'\x1b[2~',
        Qt.Key_Delete:    b'\x1b[3~',
        Qt.Key_PageUp:    b'\x1b[5~',
        Qt.Key_PageDown:  b'\x1b[6~',
        Qt.Key_F1:        b'\x1bOP',
        Qt.Key_F2:        b'\x1bOQ',
        Qt.Key_F3:        b'\x1bOR',
        Qt.Key_F4:        b'\x1bOS',
        Qt.Key_F5:        b'\x1b[15~',
        Qt.Key_F6:        b'\x1b[17~',
        Qt.Key_F7:        b'\x1b[18~',
        Qt.Key_F8:        b'\x1b[19~',
        Qt.Key_F9:        b'\x1b[20~',
        Qt.Key_F10:       b'\x1b[21~',
        Qt.Key_F11:       b'\x1b[23~',
        Qt.Key_F12:       b'\x1b[24~',
    }

    # Named keys are matched before text() because Qt reports text() as '\x08'
    # for Backspace and '\r' for Return, and readline wants DEL for Backspace.
    seq = simple.get(key)
    if seq is not None:
        return (b'\x1b' + seq) if alt else seq

    if text:
        data = text.encode('utf-8', errors='replace')
        return (b'\x1b' + data) if alt else data

    return b''


class LinuxTerminal(QPlainTextEdit):
    """Interactive local shell rendered into a read-only text view.

    A shell is spawned on a pseudo-terminal, its output is fed to a ``pyte``
    screen emulator, and that screen is painted into this widget.

    The shell is a child of the GUI process, so it runs on the machine
    displaying the GUI as the user who launched it, **not** on the Rogue server.
    Anyone who can reach the GUI window gets an interactive shell with that
    user's privileges, which is why the feature is opt-in.

    The shell starts on first display rather than on construction, so enabling
    the feature costs nothing until the tab is actually opened.

    The view is dark themed and keeps a bounded scrollback above the live
    screen, so output can be scrolled back through. Scrolling up pins the view
    in place; new output only follows the bottom when the view is already there.

    Rendering is monochrome. ``pyte`` does not implement the alternate screen
    buffer, so full screen programs such as ``vim`` and ``htop`` work but leave
    their last frame behind on exit instead of restoring the previous screen.

    Parameters
    ----------
    parent : QWidget | None, optional
        Parent Qt widget.
    argv : list[str] | None, optional
        Program to run on the pseudo-terminal. Defaults to the user's login
        shell. Restarting reuses this, so a program that exits is replaced by
        the same program rather than by a shell.
    """

    def __init__(self, parent: QWidget | None = None, *,
                 argv: list[str] | None = None) -> None:
        QPlainTextEdit.__init__(self, parent)

        self._argv = argv
        self._masterFd = -1
        self._proc = None
        self._readNotifier = None
        self._writeNotifier = None
        self._writeBuf = bytearray()
        self._spawned = False
        self._finished = False
        self._sawInput = False
        self._startupFailures = 0

        # Number of blocks at the end of the document holding the live screen.
        # Everything before them is committed scrollback and never rewritten.
        self._liveRows = 0

        font = QFontDatabase.systemFont(QFontDatabase.FixedFont)
        font.setStyleHint(QFont.Monospace)
        font.setFixedPitch(True)
        self.setFont(font)
        self.document().setDefaultFont(font)
        self.document().setDocumentMargin(0.0)

        self.setReadOnly(True)
        self.setUndoRedoEnabled(False)
        self.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.setFocusPolicy(Qt.StrongFocus)

        # Always on rather than as-needed: an as-needed bar appears and
        # disappears as content crosses the viewport height, and because the bar
        # takes horizontal space that changes the column count, which can
        # oscillate.
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self._applyDarkTheme()

        self._cellWidth, self._cellHeight = self._measureCell()

        self._themeFg = QColor(_COLOR_FG)
        self._themeBg = QColor(_COLOR_BG)

        # Keyed on the pyte attribute tuple. Real output uses only a handful of
        # distinct combinations, so this stays tiny.
        self._formatCache = {}

        cols, rows = computeGrid(self.viewport().width(), self.viewport().height(),
                                 self._cellWidth, self._cellHeight)
        self._screen = TerminalScreen(cols, rows, self.writeBytes)
        self._stream = pyte.ByteStream(self._screen)
        self._setBlockLimit(rows)

        self._repaintTimer = QTimer(self)
        self._repaintTimer.setSingleShot(True)
        self._repaintTimer.timeout.connect(self._repaint)

        self._resizeTimer = QTimer(self)
        self._resizeTimer.setSingleShot(True)
        self._resizeTimer.timeout.connect(self._applyGeometry)

        # Qt does not deliver a close event to a non-window child widget when
        # its parent is destroyed, so the shell is reaped from application
        # shutdown instead.
        app = QApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self.shutdown)

    def _applyDarkTheme(self) -> None:
        """Give the view its own dark palette.

        Both a palette and a style sheet are set. The palette keeps derived
        colors such as the selection consistent, and the style sheet makes the
        result survive an application-wide PyDM style sheet, which would
        otherwise win over the palette.
        """
        palette = self.palette()
        palette.setColor(QPalette.Base, QColor(_COLOR_BG))
        palette.setColor(QPalette.Text, QColor(_COLOR_FG))
        palette.setColor(QPalette.Highlight, QColor(_COLOR_SELECTION))
        palette.setColor(QPalette.HighlightedText, QColor(_COLOR_FG))
        self.setPalette(palette)

        self.setStyleSheet(
            'QPlainTextEdit {'
            f' background-color: {_COLOR_BG};'
            f' color: {_COLOR_FG};'
            f' selection-background-color: {_COLOR_SELECTION};'
            f' selection-color: {_COLOR_FG};'
            ' border: none; }'
        )

    def _colors(self, fg: str, bg: str, bold: bool, reverse: bool) -> tuple[QColor, QColor]:
        """Resolve a cell's foreground and background to concrete colors."""
        foreground = resolveColor(fg, bright=bold) or self._themeFg
        # Bold brightens the text, never the background.
        background = resolveColor(bg) or self._themeBg

        if reverse:
            foreground, background = background, foreground

        return (foreground, background)

    def _formatFor(self, attrs: tuple) -> QTextCharFormat:
        """Return the character format for a ``pyte`` attribute tuple.

        ``attrs`` is a ``Char`` with the data removed, so
        ``(fg, bg, bold, italics, underscore, strikethrough, reverse, blink)``.
        Blink is deliberately ignored.
        """
        cached = self._formatCache.get(attrs)
        if cached is not None:
            return cached

        fg, bg, bold, italics, underscore, strikethrough, reverse, _blink = attrs
        foreground, background = self._colors(fg, bg, bold, reverse)

        fmt = QTextCharFormat()
        fmt.setForeground(foreground)

        # Only paint a background when it differs from the view, so ordinary
        # text is not covered in same-colored rectangles.
        if background != self._themeBg:
            fmt.setBackground(background)

        if bold:
            fmt.setFontWeight(QFont.Bold)
        if italics:
            fmt.setFontItalic(True)
        if underscore:
            fmt.setFontUnderline(True)
        if strikethrough:
            fmt.setFontStrikeOut(True)

        self._formatCache[attrs] = fmt
        return fmt

    def _setBlockLimit(self, rows: int) -> None:
        """Bound the document to the scrollback plus the live screen.

        Qt drops the oldest blocks once the limit is reached, which is what
        keeps a long-lived terminal from growing without bound.
        """
        self.document().setMaximumBlockCount(SCROLLBACK_LINES + rows)

    def _measureCell(self) -> tuple[float, float]:
        """Measure one character cell, avoiding integer rounding drift.

        The row height comes from the document layout rather than the font
        metrics. ``QFontMetricsF.lineSpacing()`` can be smaller than the height
        Qt actually gives a text block, and dividing the viewport by the smaller
        value yields one row more than really fits, which leaves the top row
        permanently scrolled out of view.
        """
        fm = QFontMetricsF(self.font())
        width = max(1.0, fm.horizontalAdvance('M'))

        height = 0.0
        layout = self.document().documentLayout()
        if layout is not None:
            height = layout.blockBoundingRect(self.document().firstBlock()).height()

        if height <= 0.0:
            height = fm.height()

        return (width, max(1.0, height))

    def _viewportRows(self) -> int:
        """Return how many text rows the viewport can display."""
        return max(1, int(self.viewport().height() // self._cellHeight))

    def showEvent(self, event) -> None:
        """Spawn the shell on first display and take the keyboard.

        Clicking a tab in a ``QTabWidget`` leaves the keyboard focus on the tab
        bar, so without this the terminal would appear ready but swallow nothing
        until it was clicked a second time.
        """
        QPlainTextEdit.showEvent(self, event)

        if not self._spawned:
            self._spawned = True
            self._spawn()

        self.setFocus(Qt.OtherFocusReason)

    def _spawn(self) -> None:
        """Start a shell on a new pseudo-terminal."""
        self._sawInput = False

        try:
            self._proc, self._masterFd = spawnShell(self._screen.lines, self._screen.columns,
                                                    argv=self._argv)
        except (OSError, ValueError) as exc:
            self._notice(f'[cannot start a shell: {exc}]')
            return

        self._readNotifier = QSocketNotifier(self._masterFd, QSocketNotifier.Read, self)
        self._readNotifier.activated.connect(self._onReadable)

    def restart(self) -> None:
        """Discard the current session and start a fresh shell.

        Returns the terminal to the state it had when the GUI was opened: an
        empty screen, no scrollback, and a new prompt.
        """
        self._closeProcess()
        self._releaseNotifiers()
        self._writeBuf.clear()
        self._finished = False

        # A new screen rather than a reset one, so no emulator state can carry
        # over from the old session.
        self._screen = TerminalScreen(self._screen.columns, self._screen.lines, self.writeBytes)
        self._stream = pyte.ByteStream(self._screen)

        self._repaintTimer.stop()
        self._liveRows = 0
        self.clear()
        self.setExtraSelections([])

        self._spawned = True
        self._spawn()

    def _releaseNotifiers(self) -> None:
        """Drop the socket notifiers so new ones can be bound to a new pty."""
        for name in ('_readNotifier', '_writeNotifier'):
            notifier = getattr(self, name)
            if notifier is not None:
                notifier.setEnabled(False)
                notifier.deleteLater()
                setattr(self, name, None)

    def _onReadable(self, *_args) -> None:
        """Drain the pty master into the screen emulator.

        Accepts extra arguments because the ``activated`` signal carries an int
        on Qt 5 and a ``QSocketDescriptor`` plus a type on Qt 6.
        """
        if self._finished or self._masterFd < 0:
            return

        # The notifier is level triggered, so it is disabled for the duration of
        # the handler to prevent re-entrancy.
        self._readNotifier.setEnabled(False)
        total = 0

        try:
            while total < _MAX_BYTES_PER_POLL:
                try:
                    chunk = os.read(self._masterFd, _READ_CHUNK)
                except BlockingIOError:
                    break
                except InterruptedError:
                    continue
                except OSError as exc:
                    # Linux raises EIO on the master once the child is gone
                    # rather than returning an empty read. macOS returns b''.
                    if exc.errno in (errno.EIO, errno.EBADF):
                        self._onChildGone()
                        return
                    raise

                if not chunk:
                    self._onChildGone()
                    return

                total += len(chunk)
                # ByteStream keeps an incremental UTF-8 decoder, so a multi-byte
                # character split across reads is reassembled for us.
                self._stream.feed(chunk)

            self._armRepaint()
        finally:
            if not self._finished and self._readNotifier is not None:
                self._readNotifier.setEnabled(True)

    def writeBytes(self, data: bytes) -> None:
        """Queue bytes for the child process.

        Parameters
        ----------
        data : bytes
            Bytes to send to the shell.
        """
        if self._masterFd < 0 or not data:
            return

        self._writeBuf += data
        self._flushWrite()

    def _flushWrite(self) -> None:
        """Push as much of the write queue as the pty will take."""
        while self._writeBuf:
            try:
                written = os.write(self._masterFd, bytes(self._writeBuf[:_READ_CHUNK]))
            except BlockingIOError:
                # The pty buffer is full, which a large paste will do. Finish
                # from a write notifier instead of blocking the GUI thread.
                self._enableWriteNotifier()
                return
            except InterruptedError:
                continue
            except OSError:
                self._onChildGone()
                return

            del self._writeBuf[:written]

        self._disableWriteNotifier()

    def _enableWriteNotifier(self) -> None:
        """Arm the write notifier so a stalled write can finish later."""
        if self._writeNotifier is None:
            self._writeNotifier = QSocketNotifier(self._masterFd, QSocketNotifier.Write, self)
            self._writeNotifier.activated.connect(self._onWritable)

        self._writeNotifier.setEnabled(True)

    def _disableWriteNotifier(self) -> None:
        """Disarm the write notifier.

        A write notifier left enabled on a writable descriptor fires on every
        event loop iteration, which is a busy spin at 100% CPU.
        """
        if self._writeNotifier is not None:
            self._writeNotifier.setEnabled(False)

    def _onWritable(self, *_args) -> None:
        """Continue a write that previously filled the pty buffer."""
        if self._finished or self._masterFd < 0:
            self._disableWriteNotifier()
            return

        self._flushWrite()

    def _armRepaint(self) -> None:
        """Schedule a coalesced repaint. An idle terminal costs nothing."""
        if not self._repaintTimer.isActive():
            self._repaintTimer.start(_REPAINT_MS)

    def _repaint(self) -> None:
        """Commit scrolled-off lines, repaint the live screen, place the cursor.

        Only the tail of the document is rewritten. Replacing the whole document
        would be both wasteful and wrong: it resets the scroll position, so any
        output would yank a user who had scrolled up back to the bottom.
        """
        screen = self._screen

        pending = []
        while screen.scrolledOff:
            pending.append(screen.scrolledOff.popleft())

        if not screen.dirty and not pending:
            return

        # pyte never clears this; the consumer is required to.
        screen.dirty.clear()

        # The whole emulated grid, blank rows included. A terminal is a fixed
        # grid of rows, and the shell decides where in it the cursor sits, so
        # trimming blank rows would break anything that positions within the
        # screen. It is also what makes `clear` work: the cleared grid has to
        # cover the viewport, otherwise the scrollback underneath shows through.
        live = screenRuns(screen)
        doc = self.document()
        scrollBar = self.verticalScrollBar()

        # Follow new output only when the view is already at the bottom, so
        # scrolling back to read is not undone by the next line of output.
        follow = scrollBar.value() >= scrollBar.maximum() - 1

        cursor = QTextCursor(doc)
        cursor.beginEditBlock()

        if self._liveRows == 0:
            cursor.select(QTextCursor.Document)
            cursor.removeSelectedText()
        else:
            # Removing to the end leaves the first live block in place but
            # empty, so the following insert lands in it with no extra newline.
            first = max(0, doc.blockCount() - self._liveRows)
            cursor.setPosition(doc.findBlockByNumber(first).position())
            cursor.movePosition(QTextCursor.End, QTextCursor.KeepAnchor)
            cursor.removeSelectedText()

        for index, runs in enumerate(pending + live):
            if index:
                cursor.insertText('\n')
            for text, attrs in runs:
                if text:
                    cursor.insertText(text, self._formatFor(attrs))

        cursor.endEditBlock()

        self._liveRows = len(live)

        if follow:
            scrollBar.setValue(scrollBar.maximum())

        self._applyCursor()

    def _applyCursor(self) -> None:
        """Draw the terminal cursor as an inverted cell."""
        cursor = self._screen.cursor

        if cursor.hidden:
            self.setExtraSelections([])
            return

        doc = self.document()

        # The live screen occupies the last _liveRows blocks, so the cursor row
        # is an offset into that region rather than an absolute block number.
        liveStart = max(0, doc.blockCount() - self._liveRows)
        block = doc.findBlockByNumber(min(liveStart + cursor.y, doc.blockCount() - 1))

        if not block.isValid():
            return

        # A row can be shorter than the screen width when it holds double width
        # characters, so clamp rather than trusting the column.
        column = min(cursor.x, max(0, block.length() - 1))

        selection = QTextEdit.ExtraSelection()
        selection.cursor = QTextCursor(block)
        selection.cursor.setPosition(block.position() + column)
        selection.cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor)
        selection.format = self._cursorFormatAt(cursor.y, cursor.x)
        self.setExtraSelections([selection])

    def _cursorFormatAt(self, row: int, column: int) -> QTextCharFormat:
        """Build the cursor block by inverting the colors of the cell under it.

        Inverting fixed theme colors instead would make the cursor disappear
        wherever it happens to land on text that is already close to those
        colors.
        """
        cell = self._screen.buffer[row][column]
        foreground, background = self._colors(cell.fg, cell.bg, cell.bold, cell.reverse)

        fmt = QTextCharFormat()
        fmt.setForeground(background)
        fmt.setBackground(foreground)
        return fmt

    def keyPressEvent(self, event) -> None:
        """Forward key presses to the shell instead of editing the view."""
        modifiers = event.modifiers()
        key = event.key()

        # Copy stays available after the shell exits so output can be salvaged.
        if (modifiers & Qt.ControlModifier) and (modifiers & Qt.ShiftModifier):
            if key == Qt.Key_C:
                self.copy()
                event.accept()
                return
            if key == Qt.Key_V:
                self._paste()
                event.accept()
                return

        self.sendInput(keyToBytes(key, modifiers, event.text()))
        event.accept()

    def sendInput(self, data: bytes) -> None:
        """Send user input to the shell.

        Separate from :meth:`writeBytes` because the emulator also writes to the
        pty on its own to answer terminal queries. Only real input shows that the
        session reached a usable state, which is what distinguishes a user
        exiting a shell from a shell that never started.

        Parameters
        ----------
        data : bytes
            Bytes produced by a key press or a paste.
        """
        if not data:
            return

        self._sawInput = True
        self.writeBytes(data)

    def _paste(self) -> None:
        """Send the clipboard to the shell."""
        clipboard = QApplication.clipboard()
        if clipboard is None:
            return

        text = clipboard.text()
        if not text:
            return

        data = text.replace('\r\n', '\r').replace('\n', '\r').encode('utf-8', errors='replace')

        # Without the bracketed paste markers a multi-line paste executes every
        # line as it arrives, which is a real hazard in a hardware control GUI.
        if _BRACKETED_PASTE in self._screen.mode:
            data = b'\x1b[200~' + data + b'\x1b[201~'

        self.sendInput(data)

    def focusNextPrevChild(self, forward: bool) -> bool:
        """Keep Tab for the shell rather than moving focus."""
        return False

    def inputMethodEvent(self, event) -> None:
        """Swallow input method events; composition is not supported."""
        event.accept()

    def resizeEvent(self, event) -> None:
        """Debounce a geometry change before reflowing the shell."""
        QPlainTextEdit.resizeEvent(self, event)
        self._resizeTimer.start(_RESIZE_MS)

    def _applyGeometry(self) -> None:
        """Reflow the emulated screen and the pty to the current widget size."""
        cols, rows = computeGrid(self.viewport().width(), self.viewport().height(),
                                 self._cellWidth, self._cellHeight)

        if cols == self._screen.columns and rows == self._screen.lines:
            return

        # pyte.Screen() takes columns first but Screen.resize() takes lines
        # first, and struct winsize takes rows first. Pass by keyword where the
        # API allows it so the ordering cannot silently transpose.
        self._screen.resize(lines=rows, columns=cols)
        self._setBlockLimit(rows)

        if self._masterFd >= 0:
            try:
                setWinSize(self._masterFd, rows, cols)
            except OSError:
                pass

        self._screen.dirty.update(range(rows))
        self._armRepaint()

    def _notice(self, message: str) -> None:
        """Show an out-of-band status line in the view.

        Written through the emulator rather than appended directly so it becomes
        part of the screen, and so it cannot desynchronise the live region
        accounting in :meth:`_repaint`.
        """
        self._stream.feed(f'\r\n{message}\r\n'.encode())
        self._repaintTimer.stop()
        self._repaint()

    def _onChildGone(self) -> None:
        """Handle the shell exiting, normally by starting a fresh one.

        Exiting the shell with ``exit`` or Ctrl-D is easy to do by accident, and
        leaving a dead terminal behind would mean restarting the whole GUI to get
        it back, so a new session is started instead.
        """
        if self._finished:
            return

        self._finished = True

        if self._readNotifier is not None:
            self._readNotifier.setEnabled(False)
        self._disableWriteNotifier()

        # Exiting is something the user does, so it always follows a keystroke.
        # A session that ends without one never got started, and restarting it
        # would spawn processes in a loop.
        if self._sawInput:
            self._startupFailures = 0
        else:
            self._startupFailures += 1

        if self._startupFailures >= _MAX_STARTUP_FAILURES:
            status = self._proc.poll() if self._proc is not None else None
            # Two short lines rather than one long one, so the notice does not
            # wrap mid word in a narrow terminal.
            self._stream.feed(
                f'\r\n[shell exited with status {status}]'
                f'\r\n[exits immediately, not restarting]\r\n'.encode())
            self._screen.cursor.hidden = True
            self._repaintTimer.stop()
            self._repaint()

            # Defer closing the descriptor out of the notifier callback.
            QTimer.singleShot(0, self._closeProcess)
            return

        # Deferred for the same reason: this runs inside the read notifier's own
        # callback, and it closes the descriptor that notifier is watching.
        QTimer.singleShot(0, self.restart)

    def _closeProcess(self) -> None:
        """Close the pty and reap the child. Safe to call more than once."""
        proc, self._proc = self._proc, None
        self._masterFd = closeShell(proc, self._masterFd)

    def shutdown(self) -> None:
        """Stop all I/O and terminate the shell. Safe to call more than once."""
        self._finished = True

        for notifier in (self._readNotifier, self._writeNotifier):
            if notifier is not None:
                notifier.setEnabled(False)

        self._repaintTimer.stop()
        self._resizeTimer.stop()
        self._closeProcess()

    def closeEvent(self, event) -> None:
        """Tear down the shell when this widget is closed as a window."""
        self.shutdown()
        QPlainTextEdit.closeEvent(self, event)


class TerminalPanel(QWidget):
    """A :class:`LinuxTerminal` with a button to detach it into its own window.

    Detaching is useful because a tab is only as tall as the window it lives in.
    A separate window can be sized and placed independently, or moved to another
    monitor, which makes a long build log or a full screen program readable.

    Reparenting does not disturb the shell. The child process is held by a file
    descriptor and a socket notifier, neither of which is tied to a window, so
    detaching and reattaching keep the same shell, its working directory, and
    its scrollback.

    Parameters
    ----------
    parent : QWidget | None, optional
        Parent Qt widget.
    argv : list[str] | None, optional
        Program to run, passed through to :class:`LinuxTerminal`. Defaults to
        the user's login shell.
    label : str, optional
        Tab label to restore when reattaching.
    windowTitle : str, optional
        Title of the detached window.
    noun : str, optional
        What the detach button tooltips call the contents.
    """

    def __init__(self, parent: QWidget | None = None, *,
                 argv: list[str] | None = None,
                 label: str = 'Terminal',
                 windowTitle: str = 'Rogue Terminal',
                 noun: str = 'terminal') -> None:
        QWidget.__init__(self, parent)

        self._tab = None
        self._tabIndex = 0
        self._tabLabel = label
        self._windowTitle = windowTitle
        self._attachTip = f'Move the {noun} into its own window'
        self._detachTip = f'Put the {noun} back in the main window'

        self.terminal = LinuxTerminal(parent=None, argv=argv)

        self._button = QPushButton('Detach')
        self._button.setToolTip(self._attachTip)
        # No focus, so clicking it does not take the keyboard away from the
        # shell and Tab completion is never captured by the button.
        self._button.setFocusPolicy(Qt.NoFocus)
        self._button.clicked.connect(self.toggleDetached)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.addWidget(self._button)
        header.addStretch(1)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(header)
        layout.addWidget(self.terminal, 1)
        self.setLayout(layout)

    def isDetached(self) -> bool:
        """Return whether the terminal is currently its own window."""
        return self._tab is not None

    def _findTabWidget(self) -> QTabWidget | None:
        """Return the tab widget this panel is a page of, if any.

        Pages of a ``QTabWidget`` are children of an internal stack widget, so
        this walks up rather than checking the immediate parent.
        """
        widget = self.parentWidget()

        while widget is not None:
            if isinstance(widget, QTabWidget):
                return widget
            widget = widget.parentWidget()

        return None

    def toggleDetached(self) -> None:
        """Detach into a window, or put it back in its tab."""
        if self.isDetached():
            self.reattach()
        else:
            self.detach()

    def detach(self) -> None:
        """Move the terminal out of its tab and into its own window."""
        if self.isDetached():
            return

        tab = self._findTabWidget()
        if tab is None:
            return

        self._tab = tab
        self._tabIndex = tab.indexOf(self)
        self._tabLabel = tab.tabText(self._tabIndex)

        owner = tab.window()
        tab.removeTab(self._tabIndex)

        # Reparented to the main window rather than to nothing, with the window
        # flag set. It still behaves as a separate window, but it stays owned by
        # the GUI, so closing the GUI takes it down too instead of leaving a
        # stray window keeping the process alive.
        self.setParent(owner, Qt.Window)
        self.setWindowTitle(self._windowTitle)
        self.resize(*_DETACHED_SIZE)

        self._button.setText('Reattach')
        self._button.setToolTip(self._detachTip)

        self.show()
        self.raise_()
        self.activateWindow()
        self.terminal.setFocus(Qt.OtherFocusReason)

    def reattach(self) -> None:
        """Put the terminal back where it came from."""
        if not self.isDetached():
            return

        tab = self._tab
        self._tab = None

        # The tab count can have changed while detached, so clamp rather than
        # trusting the remembered index.
        index = min(self._tabIndex, tab.count())

        self.setWindowFlags(Qt.Widget)
        tab.insertTab(index, self, self._tabLabel)
        tab.setCurrentIndex(index)

        self._button.setText('Detach')
        self._button.setToolTip(self._attachTip)

        self.terminal.setFocus(Qt.OtherFocusReason)

    def shutdown(self) -> None:
        """Terminate the shell. Safe to call more than once."""
        self.terminal.shutdown()

    def closeEvent(self, event) -> None:
        """Reattach instead of closing when detached.

        Closing the detached window would otherwise leave the terminal with no
        way back into the GUI, so the close is treated as a request to reattach.
        """
        if self.isDetached():
            event.ignore()
            self.reattach()
            return

        QWidget.closeEvent(self, event)
