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

# Checks detaching the terminal into its own window and putting it back. The
# property that matters most is that reparenting does not disturb the running
# shell, since the whole feature would be pointless if detaching restarted it.
# Needs a QApplication, so it self-skips without Qt.

import pytest

try:
    import pyte  # noqa: F401
    from qtpy.QtCore import Qt
    from qtpy.QtGui import QCloseEvent
    from qtpy.QtWidgets import QApplication, QPushButton, QTabWidget, QWidget
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
def tabbed(qapp):
    """A panel sitting in a tab widget, with its shell started."""
    from pyrogue.pydm.widgets import TerminalPanel

    tabs = QTabWidget()
    tabs.addTab(QWidget(), 'Other')
    panel = TerminalPanel(parent=None)
    tabs.addTab(panel, 'Terminal')
    tabs.resize(700, 400)
    tabs.show()
    tabs.activateWindow()
    tabs.setCurrentIndex(1)
    qapp.processEvents()

    yield (tabs, panel)

    panel.shutdown()
    tabs.deleteLater()
    qapp.processEvents()


def _labels(tabs):
    return [tabs.tabText(i) for i in range(tabs.count())]


# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------

def test_panel_exposes_the_terminal(tabbed):
    from pyrogue.pydm.widgets import LinuxTerminal
    _tabs, panel = tabbed
    assert isinstance(panel.terminal, LinuxTerminal)


def test_panel_has_a_button(tabbed):
    _tabs, panel = tabbed
    button = panel.findChild(QPushButton)
    assert button is not None
    assert button.text() == 'Detach'


def test_button_does_not_take_keyboard_focus(tabbed):
    # Otherwise clicking it would steal the keyboard from the shell, and Tab
    # completion could land on the button instead of being sent to the pty.
    _tabs, panel = tabbed
    assert panel.findChild(QPushButton).focusPolicy() == Qt.NoFocus


def test_starts_attached(tabbed):
    _tabs, panel = tabbed
    assert not panel.isDetached()
    assert not panel.isWindow()


# ---------------------------------------------------------------------------
# Detach and reattach
# ---------------------------------------------------------------------------

def test_detach_removes_the_tab_and_makes_a_window(tabbed):
    tabs, panel = tabbed
    panel.detach()

    assert panel.isDetached()
    assert panel.isWindow()
    assert _labels(tabs) == ['Other']


def test_detached_window_stays_owned_by_the_gui(tabbed):
    # Parented to the main window rather than to nothing, so closing the GUI
    # takes the detached terminal with it instead of leaving a stray window
    # holding the process open.
    tabs, panel = tabbed
    owner = tabs.window()
    panel.detach()
    assert panel.parent() is owner


def test_detach_keeps_the_same_shell(tabbed):
    _tabs, panel = tabbed
    pid = panel.terminal._proc.pid

    panel.detach()

    assert panel.terminal._proc.pid == pid
    assert panel.terminal._proc.poll() is None


def test_reattach_restores_the_tab_at_its_original_position(tabbed):
    tabs, panel = tabbed
    index = tabs.indexOf(panel)

    panel.detach()
    panel.reattach()

    assert not panel.isDetached()
    assert tabs.indexOf(panel) == index
    assert tabs.currentIndex() == index
    assert _labels(tabs) == ['Other', 'Terminal']


def test_reattach_keeps_the_same_shell(tabbed):
    _tabs, panel = tabbed
    pid = panel.terminal._proc.pid

    panel.detach()
    panel.reattach()

    assert panel.terminal._proc.pid == pid
    assert panel.terminal._proc.poll() is None


def test_button_label_tracks_the_state(tabbed):
    _tabs, panel = tabbed
    button = panel.findChild(QPushButton)

    panel.detach()
    assert button.text() == 'Reattach'

    panel.reattach()
    assert button.text() == 'Detach'


def test_toggle_switches_both_ways(tabbed):
    _tabs, panel = tabbed

    panel.toggleDetached()
    assert panel.isDetached()

    panel.toggleDetached()
    assert not panel.isDetached()


def test_detach_is_idempotent(tabbed):
    tabs, panel = tabbed
    panel.detach()
    panel.detach()
    assert panel.isDetached()
    assert _labels(tabs) == ['Other']


def test_reattach_when_attached_does_nothing(tabbed):
    tabs, panel = tabbed
    panel.reattach()
    assert not panel.isDetached()
    assert _labels(tabs) == ['Other', 'Terminal']


def test_detach_outside_a_tab_widget_is_a_no_op(qapp):
    # A panel used directly in a custom screen has nowhere to detach from, so
    # the button must not strand it in a window it cannot return from.
    from pyrogue.pydm.widgets import TerminalPanel

    panel = TerminalPanel(parent=None)
    try:
        panel.detach()
        assert not panel.isDetached()
    finally:
        panel.shutdown()
        panel.deleteLater()
        qapp.processEvents()


# ---------------------------------------------------------------------------
# Closing the detached window
# ---------------------------------------------------------------------------

def test_closing_the_detached_window_reattaches(tabbed):
    # Closing it must not be a way to lose the terminal, so the close is turned
    # into a reattach and the shell keeps running.
    tabs, panel = tabbed
    pid = panel.terminal._proc.pid
    panel.detach()

    event = QCloseEvent()
    panel.closeEvent(event)

    assert not event.isAccepted()
    assert not panel.isDetached()
    assert _labels(tabs) == ['Other', 'Terminal']
    assert panel.terminal._proc.pid == pid
    assert panel.terminal._proc.poll() is None


def test_shutdown_terminates_the_shell(tabbed):
    _tabs, panel = tabbed
    panel.shutdown()
    assert panel.terminal._proc is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
