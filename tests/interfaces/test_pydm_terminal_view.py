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

# Checks how the terminal widget renders: what is actually on screen, where the
# cursor row lands, scroll behaviour, and the dark theme. Bytes are fed straight
# into the emulator rather than through a real shell, so there is no process and
# no timing involved. Needs a QApplication, so it self-skips without Qt.

import time

import pytest

try:
    import pyte  # noqa: F401
    from qtpy.QtCore import Qt
    from qtpy.QtGui import QPalette
    from qtpy.QtWidgets import QApplication
    # The widget package imports pydm, which needs more of the Qt stack than the
    # modules above. Import it here so a partial Qt install skips the module
    # rather than erroring inside every fixture.
    from pyrogue.pydm import widgets  # noqa: F401
except Exception as exc:
    pytest.skip(
        f"PyDM/Qt test dependencies unavailable: {exc}",
        allow_module_level=True,
    )


@pytest.fixture(scope="module")
def qapp():
    yield QApplication.instance() or QApplication([])


@pytest.fixture
def term(qapp):
    """A shown terminal widget with no shell attached."""
    from pyrogue.pydm.widgets import LinuxTerminal

    widget = LinuxTerminal()
    widget.resize(700, 300)
    widget.show()
    qapp.processEvents()

    # Resizes are debounced behind a timer that a test event loop will not
    # necessarily run, so apply the new geometry directly to keep this
    # deterministic.
    widget._applyGeometry()
    qapp.processEvents()

    yield widget
    widget.shutdown()
    widget.deleteLater()
    qapp.processEvents()


def _feed(widget, data):
    """Push bytes through the emulator and repaint synchronously."""
    widget._stream.feed(data)
    widget._repaintTimer.stop()
    widget._repaint()


def _onScreen(widget):
    """Return the rows currently visible, which is what a user sees."""
    lines = widget.toPlainText().split('\n')
    first = widget.firstVisibleBlock().blockNumber()
    return lines[first:first + widget._viewportRows()]


def _text(widget):
    return [line.rstrip() for line in _onScreen(widget) if line.strip()]


# ---------------------------------------------------------------------------
# Geometry
# ---------------------------------------------------------------------------

def test_emulated_grid_matches_the_visible_rows(term):
    # If the emulated screen were taller than the viewport, its top row would be
    # permanently scrolled out of sight.
    assert term._screen.lines == term._viewportRows()


def test_full_grid_fills_the_viewport_with_nothing_hidden(term):
    _feed(term, b'hello')
    assert term.document().blockCount() == term._screen.lines
    assert term.verticalScrollBar().maximum() == 0


def test_blank_rows_below_the_output_are_kept(term):
    # The grid is fixed height, so a single line of output still occupies one
    # row with the rest of the grid blank beneath it.
    _feed(term, b'hello')
    assert len(_onScreen(term)) == term._screen.lines
    assert _text(term) == ['hello']


# ---------------------------------------------------------------------------
# clear
# ---------------------------------------------------------------------------

def test_erase_display_leaves_the_screen_blank(term):
    rows = term._screen.lines
    _feed(term, b''.join(b'LINE%d\r\n' % i for i in range(rows * 2)))
    assert _text(term) != []

    # What `clear` does: home the cursor and erase the display.
    _feed(term, b'\x1b[H\x1b[2J')
    assert _text(term) == []


def test_reset_leaves_the_screen_blank(term):
    # Some clear implementations emit RIS instead of a home plus erase.
    rows = term._screen.lines
    _feed(term, b''.join(b'LINE%d\r\n' % i for i in range(rows * 2)))
    _feed(term, b'\x1bc')
    assert _text(term) == []


def test_clear_keeps_earlier_output_in_scrollback(term):
    # Clearing the screen must not destroy history; it should still be reachable
    # by scrolling up, which is how a terminal with scrollback behaves.
    rows = term._screen.lines
    _feed(term, b''.join(b'LINE%d\r\n' % i for i in range(rows * 2)))
    _feed(term, b'\x1bc')

    assert 'LINE0' not in '\n'.join(_onScreen(term))
    assert 'LINE0' in term.toPlainText()


def test_output_after_clear_starts_at_the_top(term):
    rows = term._screen.lines
    _feed(term, b''.join(b'LINE%d\r\n' % i for i in range(rows * 2)))
    _feed(term, b'\x1bc')
    _feed(term, b'AFTER')
    assert _onScreen(term)[0].rstrip() == 'AFTER'


# ---------------------------------------------------------------------------
# Scrolling
# ---------------------------------------------------------------------------

def test_prompt_reaches_the_bottom_row_once_the_screen_fills(term):
    # Enough output to scroll, then a prompt with no trailing newline, which is
    # what a shell leaves on screen while waiting for input.
    rows = term._screen.lines
    _feed(term, b''.join(b'LINE%d\r\n' % i for i in range(rows * 3)) + b'PROMPT$ ')

    onScreen = _onScreen(term)
    lastText = max(i for i, line in enumerate(onScreen) if line.strip())
    assert onScreen[lastText].startswith('PROMPT$')
    assert lastText == rows - 1


def test_scrollback_accumulates_above_the_screen(term):
    rows = term._screen.lines
    _feed(term, b''.join(b'LINE%d\r\n' % i for i in range(rows * 3)))

    assert term.document().blockCount() > rows
    assert term.verticalScrollBar().maximum() > 0
    assert 'LINE0' in term.toPlainText()


def test_view_stays_put_when_scrolled_up(term):
    rows = term._screen.lines
    _feed(term, b''.join(b'LINE%d\r\n' % i for i in range(rows * 3)))

    bar = term.verticalScrollBar()
    bar.setValue(2)
    _feed(term, b'MORE\r\n')

    assert bar.value() == 2


def test_view_follows_when_already_at_the_bottom(term):
    rows = term._screen.lines
    _feed(term, b''.join(b'LINE%d\r\n' % i for i in range(rows * 3)))

    bar = term.verticalScrollBar()
    bar.setValue(bar.maximum())
    _feed(term, b'MORE\r\n')

    assert bar.value() == bar.maximum()


# ---------------------------------------------------------------------------
# Appearance
# ---------------------------------------------------------------------------

def test_scrollbar_is_always_visible(term):
    # An as-needed bar would appear and disappear as content crosses the
    # viewport height, and because it consumes width that changes the column
    # count, which can oscillate.
    assert term.verticalScrollBarPolicy() == Qt.ScrollBarAlwaysOn


def test_dark_theme_is_applied(term):
    palette = term.palette()
    background = palette.color(QPalette.Base)
    foreground = palette.color(QPalette.Text)

    assert background.lightness() < 60, "background should be dark"
    assert foreground.lightness() > 150, "foreground should be light"


# ---------------------------------------------------------------------------
# Restarting after the shell exits
# ---------------------------------------------------------------------------

def _waitFor(qapp, predicate, timeout=8.0):
    """Pump the event loop until ``predicate`` holds or the timeout expires."""
    end = time.monotonic() + timeout

    while time.monotonic() < end:
        if predicate():
            return True
        qapp.processEvents()
        time.sleep(0.02)

    return predicate()


def _waitReady(qapp, term):
    """Wait until the shell has printed something, so it is reading input.

    Sending Ctrl-D before the shell reaches its prompt proves nothing, because
    the shell has not started reading yet.
    """
    assert _waitFor(qapp, lambda: term.toPlainText().strip() != ''), "shell never produced a prompt"


def test_shell_exit_starts_a_fresh_session(qapp, term):
    _waitReady(qapp, term)
    # Ctrl-D and `exit` are easy to hit by accident. Leaving a dead terminal
    # behind would mean restarting the whole GUI to get a shell back.
    first = term._proc.pid
    term.sendInput(b'echo BEFORE_EXIT\n')
    assert _waitFor(qapp, lambda: 'BEFORE_EXIT' in term.toPlainText())

    term.sendInput(b'\x04')                       # Ctrl-D
    assert _waitFor(qapp, lambda: term._proc is not None and term._proc.pid != first)

    assert term._proc.poll() is None, "the replacement shell must be running"


def test_restarted_session_starts_clean(qapp, term):
    _waitReady(qapp, term)
    term.sendInput(b'echo OLD_OUTPUT\n')
    assert _waitFor(qapp, lambda: 'OLD_OUTPUT' in term.toPlainText())

    first = term._proc.pid
    term.sendInput(b'\x04')
    assert _waitFor(qapp, lambda: term._proc is not None and term._proc.pid != first)

    # Same state as a freshly opened terminal: no leftover output, no scrollback.
    assert _waitFor(qapp, lambda: 'OLD_OUTPUT' not in term.toPlainText())
    assert term.verticalScrollBar().maximum() == 0


def test_restarted_session_is_usable(qapp, term):
    _waitReady(qapp, term)
    first = term._proc.pid
    term.sendInput(b'\x04')
    assert _waitFor(qapp, lambda: term._proc is not None and term._proc.pid != first)

    term.sendInput(b'echo AFTER_RESTART\n')
    assert _waitFor(qapp, lambda: 'AFTER_RESTART' in term.toPlainText())


def test_restart_can_happen_repeatedly(qapp, term):
    _waitReady(qapp, term)
    seen = {term._proc.pid}

    for _ in range(3):
        previous = term._proc.pid
        term.sendInput(b'exit\n')
        assert _waitFor(qapp, lambda: term._proc is not None and term._proc.pid != previous)
        seen.add(term._proc.pid)

    assert len(seen) == 4, "each exit should produce a distinct shell"
    # A shell that lived long enough is not counted as a failure to start.
    assert term._startupFailures == 0


def test_a_shell_that_dies_instantly_is_not_restarted_forever(qapp, monkeypatch):
    # Guards against spawning processes in a loop when the shell cannot start,
    # for example a bogus $SHELL.
    from pyrogue.pydm.widgets import terminal as module
    from pyrogue.pydm.widgets import terminal_core

    attempts = []
    real = terminal_core.spawnShell

    def instantExit(rows, cols, argv=None, useCtty=True):
        attempts.append(1)
        return real(rows, cols, argv=['/bin/true'], useCtty=useCtty)

    monkeypatch.setattr(module, 'spawnShell', instantExit)

    widget = module.LinuxTerminal()
    widget.resize(700, 300)
    widget.show()

    try:
        assert _waitFor(qapp, lambda: widget._startupFailures >= module._MAX_STARTUP_FAILURES)
        # Let any runaway restart loop reveal itself.
        deadline = time.monotonic() + 2.0
        while time.monotonic() < deadline:
            qapp.processEvents()
            time.sleep(0.02)

        assert len(attempts) <= module._MAX_STARTUP_FAILURES
        assert widget._proc is None, "it should stop rather than hold a dead child"
        assert 'not restarting' in ' '.join(widget.toPlainText().split())
    finally:
        widget.shutdown()
        widget.deleteLater()
        qapp.processEvents()


def test_restart_rebinds_the_read_notifier(qapp, term):
    _waitReady(qapp, term)
    # The old notifier watches a descriptor that restart closes, so a stale one
    # would either do nothing or fire on a recycled descriptor.
    before = term._readNotifier
    term.restart()

    assert term._readNotifier is not before
    term.sendInput(b'echo REBOUND\n')
    assert _waitFor(qapp, lambda: 'REBOUND' in term.toPlainText())


# ---------------------------------------------------------------------------
# Keyboard focus
# ---------------------------------------------------------------------------

def test_terminal_takes_focus_when_its_tab_is_selected(qapp):
    # Clicking a tab leaves the keyboard focus on the tab bar, so without the
    # widget claiming it the terminal looks ready but ignores typing until it is
    # clicked a second time.
    from qtpy.QtWidgets import QTabWidget, QWidget
    from pyrogue.pydm.widgets import LinuxTerminal

    tabs = QTabWidget()
    tabs.addTab(QWidget(), 'Other')
    terminal = LinuxTerminal(parent=None)
    tabs.addTab(terminal, 'Terminal')
    tabs.resize(700, 300)
    tabs.show()
    tabs.activateWindow()
    qapp.processEvents()

    try:
        assert not terminal.hasFocus(), "the other tab is selected at this point"

        tabs.setCurrentIndex(1)
        qapp.processEvents()
        assert terminal.hasFocus()

        # Leaving and returning has to focus it again, not just the first time.
        tabs.setCurrentIndex(0)
        qapp.processEvents()
        tabs.setCurrentIndex(1)
        qapp.processEvents()
        assert terminal.hasFocus()
    finally:
        terminal.shutdown()
        tabs.deleteLater()
        qapp.processEvents()


def test_terminal_accepts_keyboard_focus(term):
    assert term.focusPolicy() == Qt.StrongFocus


# ---------------------------------------------------------------------------
# Color
# ---------------------------------------------------------------------------

def _formatAt(widget, needle):
    """Return the character format applied to the first char of ``needle``."""
    from qtpy.QtGui import QTextCursor

    index = widget.toPlainText().index(needle)
    cursor = QTextCursor(widget.document())
    cursor.setPosition(index)
    cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor)
    return cursor.charFormat()


def test_named_color_is_applied(term):
    _feed(term, b'\x1b[31mRED\x1b[0m')
    assert _formatAt(term, 'RED').foreground().color().name() == '#cd0000'


def test_bold_renders_the_bright_shade_and_bold_weight(term):
    # Colorizing tools emit bold plus a color meaning the bright variant, so
    # bold has to brighten as well as embolden or their output looks wrong.
    from qtpy.QtGui import QFont

    _feed(term, b'\x1b[1;31mBOLD\x1b[0m')
    fmt = _formatAt(term, 'BOLD')
    assert fmt.foreground().color().name() == '#ff0000'
    assert fmt.fontWeight() == QFont.Bold


def test_aixterm_bright_color_is_applied(term):
    _feed(term, b'\x1b[91mBRIGHT\x1b[0m')
    assert _formatAt(term, 'BRIGHT').foreground().color().name() == '#ff0000'


def test_256_color_is_applied(term):
    _feed(term, b'\x1b[38;5;208mORANGE\x1b[0m')
    assert _formatAt(term, 'ORANGE').foreground().color().name() == '#ff8700'


def test_true_color_is_applied(term):
    _feed(term, b'\x1b[38;2;10;20;30mTRUE\x1b[0m')
    assert _formatAt(term, 'TRUE').foreground().color().name() == '#0a141e'


def test_background_color_is_applied(term):
    _feed(term, b'\x1b[44mONBLUE\x1b[0m')
    assert _formatAt(term, 'ONBLUE').background().color().name() == '#0000ee'


def test_reverse_swaps_foreground_and_background(term):
    _feed(term, b'\x1b[7mREV\x1b[0m')
    fmt = _formatAt(term, 'REV')
    assert fmt.foreground().color().name() == '#1e1e1e'
    assert fmt.background().color().name() == '#d4d4d4'


def test_underline_and_italic_are_applied(term):
    _feed(term, b'\x1b[4mUL\x1b[0m \x1b[3mIT\x1b[0m')
    assert _formatAt(term, 'UL').fontUnderline()
    assert _formatAt(term, 'IT').fontItalic()


def test_plain_text_uses_the_theme_foreground(term):
    _feed(term, b'PLAIN')
    assert _formatAt(term, 'PLAIN').foreground().color().name() == '#d4d4d4'


def test_unrecognised_color_falls_back_to_the_theme(term):
    # pyte's own aixterm background table contains a misspelled name, so an
    # unknown value must not raise or produce a black-on-black cell.
    from pyrogue.pydm.widgets.terminal import resolveColor
    assert resolveColor('bfightmagenta') is None
    assert resolveColor('default') is None
    assert resolveColor('') is None


def test_color_survives_scrolling_into_scrollback(term):
    # The whole point of keeping attributes in the scrollback: a colored line
    # must not turn grey when it scrolls off the live screen.
    rows = term._screen.lines
    _feed(term, b'\x1b[32mGREENLINE\x1b[0m\r\n')
    _feed(term, b''.join(b'filler%d\r\n' % i for i in range(rows * 2)))

    assert 'GREENLINE' in term.toPlainText()
    assert _formatAt(term, 'GREENLINE').foreground().color().name() == '#00cd00'


def test_format_cache_is_small_for_real_output(term):
    _feed(term, b''.join(b'\x1b[32mok\x1b[0m plain \x1b[31mbad\x1b[0m\r\n' for _ in range(20)))
    # A handful of distinct attribute combinations, not one per cell.
    assert len(term._formatCache) <= 8


def test_escape_sequences_never_reach_the_view(term):
    _feed(term, b'\x1b[31mred\x1b[0m\x1b[1mbold\x1b[0m')
    text = term.toPlainText()
    assert '\x1b' not in text
    assert '31m' not in text
    assert 'red' in text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
