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

# Checks the IPython console tab: that it targets the server the rest of the GUI
# is pointed at, that it is labelled and titled as a console rather than a
# terminal, and that detaching does not restart the session. The generic
# detach/reattach behaviour it inherits is covered by
# test_pydm_terminal_panel.py. Needs a QApplication, so it self-skips without Qt.
#
# Most of it involves no Rogue server: the console reports that it cannot connect
# and hands over a prompt anyway, which is all those tests need. The integration
# tests at the end do run one, because reading the tree, completing on it, and
# exiting a session that holds a connected client only mean something against a
# server that is really there.

import importlib.util
import time

import pytest

try:
    import pyte  # noqa: F401
    from qtpy.QtWidgets import QApplication, QTabWidget, QWidget
    # The widget package imports pydm, which needs more of the Qt stack than the
    # modules above. Import it here so a partial Qt install skips the module
    # rather than erroring inside every fixture.
    from pyrogue.pydm import widgets  # noqa: F401
except Exception as exc:
    pytest.skip(
        f"PyDM/Qt test dependencies unavailable: {exc}",
        allow_module_level=True,
    )

needsIPython = pytest.mark.skipif(importlib.util.find_spec('IPython') is None,
                                  reason="IPython is not installed")


@pytest.fixture(scope="module")
def qapp():
    yield QApplication.instance() or QApplication([])


@pytest.fixture
def server(monkeypatch):
    """Point the GUI at a server address, as runPyDM does."""
    monkeypatch.setenv('ROGUE_SERVERS', 'rogue-host.example:9123')
    return ('rogue-host.example', 9123)


@pytest.fixture
def panel(qapp, server):
    """An unshown panel, so no console has been started yet."""
    from pyrogue.pydm.widgets import IPythonPanel

    widget = IPythonPanel(parent=None)
    yield widget
    widget.shutdown()
    widget.deleteLater()
    qapp.processEvents()


@pytest.fixture
def tabbed(qapp, server):
    """A panel sitting in a tab widget, with its console started."""
    from pyrogue.pydm.widgets import IPythonPanel

    tabs = QTabWidget()
    tabs.addTab(QWidget(), 'Other')
    widget = IPythonPanel(parent=None)
    tabs.addTab(widget, 'IPython')
    tabs.resize(700, 400)
    tabs.show()
    tabs.setCurrentIndex(1)
    qapp.processEvents()

    yield (tabs, widget)

    widget.shutdown()
    tabs.deleteLater()
    qapp.processEvents()


# ---------------------------------------------------------------------------
# Server targeting
# ---------------------------------------------------------------------------

def test_console_targets_the_gui_server(panel, server):
    # The console must reach the same server the System and Debug Tree tabs are
    # bound to. A hardcoded localhost:9099 would silently connect somewhere else
    # whenever the GUI was launched against a remote server.
    addr, port = server
    startup = panel.terminal._argv[-1]
    assert f"addr='{addr}'" in startup
    assert f'port={port}' in startup


def test_explicit_channel_overrides_the_default(qapp, server):
    from pyrogue.pydm.widgets import IPythonPanel

    widget = IPythonPanel(parent=None, init_channel='rogue://other-host:9500/root')
    try:
        startup = widget.terminal._argv[-1]
        assert "addr='other-host'" in startup
        assert 'port=9500' in startup
    finally:
        widget.shutdown()
        widget.deleteLater()
        qapp.processEvents()


# ---------------------------------------------------------------------------
# Presentation
# ---------------------------------------------------------------------------

def test_tab_is_labelled_ipython(panel):
    assert panel._tabLabel == 'IPython'


def test_detached_window_names_the_server(panel, server):
    # Two consoles against two servers are otherwise indistinguishable once
    # detached, which is exactly when it matters that the window says which one
    # it is.
    addr, port = server
    assert f'{addr}:{port}' in panel._windowTitle


def test_button_tooltips_say_console(panel):
    assert 'console' in panel._attachTip
    assert 'console' in panel._detachTip
    assert 'terminal' not in panel._attachTip


def test_console_is_not_started_until_shown(panel):
    # Enabling the tab costs nothing until it is opened, and the connection
    # attempt never delays the GUI coming up.
    assert panel.terminal._proc is None


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------

@needsIPython
def test_showing_the_tab_starts_the_console(tabbed):
    _tabs, widget = tabbed
    assert widget.terminal._proc is not None
    assert widget.terminal._proc.poll() is None


@needsIPython
def test_detach_and_reattach_keep_the_same_session(tabbed):
    # The whole point of detaching is reading a long session comfortably, which
    # would be pointless if it restarted the interpreter and lost the namespace.
    _tabs, widget = tabbed
    pid = widget.terminal._proc.pid

    widget.detach()
    assert widget.terminal._proc.pid == pid

    widget.reattach()
    assert widget.terminal._proc.pid == pid
    assert widget.terminal._proc.poll() is None


@needsIPython
def test_shutdown_terminates_the_console(tabbed):
    _tabs, widget = tabbed
    proc = widget.terminal._proc

    widget.shutdown()

    assert proc.poll() is not None


# ---------------------------------------------------------------------------
# Real session
# ---------------------------------------------------------------------------

def _pump(qapp, terminal, needle, seconds):
    """Drive the event loop until ``needle`` appears in the view."""
    deadline = time.monotonic() + seconds

    while time.monotonic() < deadline:
        qapp.processEvents()
        if needle in terminal.toPlainText():
            return True
        time.sleep(0.05)

    return False


@pytest.mark.integration
@needsIPython
def test_console_reaches_a_prompt_in_the_widget(tabbed, qapp):
    # End to end through the widget rather than the pty alone: IPython starts,
    # the startup code runs, and prompt_toolkit's output renders into the view.
    _tabs, widget = tabbed

    assert _pump(qapp, widget.terminal, 'In [', 60.0), \
        f"no prompt rendered: {widget.terminal.toPlainText()[-400:]!r}"
    assert 'Rogue console' in widget.terminal.toPlainText()


@pytest.mark.integration
@needsIPython
def test_cursor_position_requests_are_answered(tabbed, qapp):
    # prompt_toolkit asks the terminal where the cursor is and warns when nothing
    # answers. TerminalScreen.write_process_input is what replies, so this is the
    # check that the emulator is complete enough to host a real readline UI.
    _tabs, widget = tabbed

    assert _pump(qapp, widget.terminal, 'In [', 60.0), \
        f"no prompt rendered: {widget.terminal.toPlainText()[-400:]!r}"
    assert 'cursor position' not in widget.terminal.toPlainText()


@pytest.fixture
def liveTree(monkeypatch, free_zmq_port):
    """A running Rogue server, with the GUI pointed at it."""
    import pyrogue as pr
    import pyrogue.interfaces as pri

    class Dev(pr.Device):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.add(pr.LocalVariable(name='Value', value=1234, mode='RW'))

    class Top(pr.Root):
        def __init__(self):
            super().__init__(name='Top', pollEn=False)
            self.add(Dev(name='Dev'))
            self.zmqServer = pri.ZmqServer(root=self, addr='*', port=free_zmq_port)
            self.addInterface(self.zmqServer)

    monkeypatch.setenv('ROGUE_SERVERS', f'localhost:{free_zmq_port}')

    with Top() as root:
        yield root


@pytest.fixture
def connected(qapp, liveTree, monkeypatch, tmp_path):
    """A shown console that has reached its prompt with the client connected."""
    from pyrogue.pydm.widgets import IPythonPanel

    # An empty history for the child. IPython otherwise uses the history of
    # whoever runs the suite, and prompt_toolkit renders a suggestion drawn from
    # it as ghost text in the view, which reads exactly like a completion.
    monkeypatch.setenv('IPYTHONDIR', str(tmp_path / 'ipython'))

    panel = IPythonPanel(parent=None)
    # Wide enough that a typed command is not wrapped by the emulator.
    panel.resize(1100, 500)
    panel.show()
    qapp.processEvents()

    assert _pump(qapp, panel.terminal, 'are ready', 90.0), \
        f"client never connected: {panel.terminal.toPlainText()[-600:]!r}"

    yield panel

    panel.shutdown()
    panel.deleteLater()
    qapp.processEvents()


@pytest.mark.integration
@needsIPython
def test_console_reads_and_writes_a_real_tree(qapp, liveTree, connected):
    # The whole point of the tab, end to end: a real server, a real client in a
    # real IPython process, a value read back through the tree and one written
    # that the server side then sees. Nothing else covers the actual purpose.
    connected.terminal.writeBytes(b'print("READBACK", root.Dev.Value.get())\r')
    assert _pump(qapp, connected.terminal, 'READBACK 1234', 60.0), \
        f"read did not come back: {connected.terminal.toPlainText()[-600:]!r}"

    connected.terminal.writeBytes(b'root.Dev.Value.set(777)\r')
    assert _pump(qapp, connected.terminal, 'In [3]', 60.0), \
        f"write did not complete: {connected.terminal.toPlainText()[-600:]!r}"
    assert liveTree.Dev.Value.get() == 777


@pytest.mark.integration
@needsIPython
def test_tab_completes_on_the_tree(qapp, connected):
    # Completing on the tree is why the console exists, and it is the one thing
    # the default completer cannot do: jedi crashes on the dynamic __getattr__
    # nodes and IPython then has nothing to offer, so Tab does nothing. A live
    # server is required because there is no tree to complete against without one.
    connected.terminal.sendInput(b'root.De')
    assert _pump(qapp, connected.terminal, 'root.De', 30.0), \
        f"input never echoed: {connected.terminal.toPlainText()[-600:]!r}"

    connected.terminal.sendInput(b'\t')
    assert _pump(qapp, connected.terminal, 'root.Dev', 30.0), \
        f"Tab did not complete: {connected.terminal.toPlainText()[-600:]!r}"


@pytest.mark.integration
@needsIPython
def test_exiting_a_connected_session_starts_a_fresh_one(qapp, connected):
    # Restarting on exit only works if the interpreter can exit, and a connected
    # client used to keep it alive: the widget learns the session ended from the
    # pty reporting end of file, which never comes while the child is still there.
    first = connected.terminal._proc.pid

    connected.terminal.sendInput(b'exit\r')

    deadline = time.monotonic() + 90.0
    while time.monotonic() < deadline:
        qapp.processEvents()
        proc = connected.terminal._proc
        if proc is not None and proc.pid != first:
            break
        time.sleep(0.05)
    else:
        pytest.fail(f"console never restarted: {connected.terminal.toPlainText()[-600:]!r}")

    # A restarted session is only useful if it reconnected, and it starts from a
    # cleared view, so this needle can only come from the new one.
    assert _pump(qapp, connected.terminal, 'are ready', 90.0), \
        f"fresh session did not connect: {connected.terminal.toPlainText()[-600:]!r}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
