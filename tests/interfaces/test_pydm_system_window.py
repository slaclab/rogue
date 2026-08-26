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

# Guards the System tab layout. The terminal is a top level tab, so the system
# log must stay exactly as it was: added straight to the vertical layout, with no
# tab bar wrapped around it and no terminal nested inside. Needs a real
# QApplication because SystemWindow is a PyDMFrame, so it self-skips without Qt.
# The Rogue node is stubbed, so no server and no hardware are involved.

import pytest

try:
    from qtpy.QtWidgets import QApplication, QTabWidget
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
def systemWindow(qapp, monkeypatch):
    """A SystemWindow that has completed its lazy build."""
    from pyrogue.pydm.widgets import system_window as sw

    class FakeNode:
        def getNodes(self, typ=None):
            return {}

    monkeypatch.setattr(sw, 'nodeFromAddress', lambda channel: FakeNode())
    monkeypatch.setattr(sw, 'RootControl', lambda parent=None, init_channel=None: sw.QWidget())
    monkeypatch.setattr(sw, 'SystemLog', lambda parent=None, init_channel=None: sw.QWidget())

    window = sw.SystemWindow(parent=None, init_channel='rogue://0/root')
    window._connected = False
    window.connection_changed(True)

    yield window

    window.deleteLater()
    qapp.processEvents()


def test_system_tab_has_no_tab_bar(systemWindow):
    # A nested tab set here was the earlier design. The terminal moved to the top
    # level precisely so this view keeps its original full height layout.
    assert systemWindow.findChild(QTabWidget) is None


def test_system_window_takes_no_terminal_option(systemWindow):
    from pyrogue.pydm.widgets import SystemWindow
    import inspect

    assert 'enableTerminal' not in inspect.signature(SystemWindow.__init__).parameters


def test_system_window_does_not_own_a_terminal(systemWindow):
    from pyrogue.pydm.widgets import LinuxTerminal
    assert systemWindow.findChild(LinuxTerminal) is None


def test_build_runs_only_once(systemWindow):
    # connection_changed is gated on _node, so a reconnect must not rebuild the
    # layout and duplicate the log.
    before = len(systemWindow.children())

    systemWindow.connection_changed(False)
    systemWindow.connection_changed(True)

    assert len(systemWindow.children()) == before


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
