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

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

try:
    from pyrogue.pydm.data_plugins import rogue_plugin
    from pyrogue.pydm.data_plugins.rogue_plugin import RogueConnection, RoguePlugin
    from pydm.widgets.channel import PyDMChannel
    from qtpy.QtCore import QObject, Signal
    from qtpy.QtWidgets import QApplication
except Exception as exc:
    pytest.skip(f"PyDM/Qt test dependencies unavailable: {exc}", allow_module_level=True)


class _SignalRecorder:
    def __init__(self):
        self.values = []

    def __getitem__(self, _key):
        return self

    def emit(self, value):
        self.values.append(value)


def test_rogue_connection_link_state_refreshes_static_name_channels():
    conn = RogueConnection.__new__(RogueConnection)
    conn._node = SimpleNamespace(name="MyVar", path="root.MyVar")
    conn._notDev = True
    conn._mode = "name"
    conn._index = -1
    conn.connection_state_signal = _SignalRecorder()
    conn.new_value_signal = _SignalRecorder()

    RogueConnection.linkState(conn, False)
    assert conn.connection_state_signal.values == [False]
    assert conn.new_value_signal.values == []

    RogueConnection.linkState(conn, True)
    assert conn.connection_state_signal.values == [False, True]
    assert conn.new_value_signal.values == ["MyVar"]


class _Writer(QObject):
    value = Signal((int,), (float,), (str,))


@pytest.fixture
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def shared_client(monkeypatch):
    nodes = {}
    for name in ("First", "Second"):
        listeners = []
        nodes[f"root.{name}"] = SimpleNamespace(
            name=name, path=f"root.{name}",
            isinstance=lambda cls: False,
            disp="{}", enum=None, mode="RW", typeStr="int",
            units=None, minimum=None, maximum=None, precision=0,
            listeners=listeners, addListener=listeners.append,
            delListener=listeners.remove,
            getVariableValue=lambda **kwargs: SimpleNamespace(value=0, severity="Good"),
            setDisp=Mock(),
        )
    monitors = []
    client = SimpleNamespace(
        root=SimpleNamespace(getNode=nodes.get),
        nodes=nodes, monitors=monitors,
        addLinkMonitor=monitors.append, remLinkMonitor=monitors.remove,
        stop=Mock(),
    )
    monkeypatch.setattr(rogue_plugin.pyrogue.interfaces, "VirtualClient", lambda *args: client)
    monkeypatch.setattr(rogue_plugin.utilities, "is_pydm_app", lambda: True)
    return client


@pytest.mark.parametrize("same_address", [False, True])
@pytest.mark.parametrize("destroying", [False, True])
def test_removing_channel_preserves_other_widgets(app, shared_client, same_address, destroying):
    plugin = RoguePlugin()
    values = [[], []]
    states = [[], []]
    writers = [_Writer(), _Writer()]
    paths = ["root.First", "root.First" if same_address else "root.Second"]
    channels = [
        PyDMChannel(
            address=f"rogue://localhost:9099/{path}",
            value_slot=values[i].append, connection_slot=states[i].append,
            value_signal=writers[i].value,
        )
        for i, path in enumerate(paths)
    ]
    try:
        for channel in channels:
            plugin.add_connection(channel)
        app.processEvents()
        for recorded in values + states:
            recorded.clear()

        plugin.remove_connection(channels[0], destroying=destroying)
        shared_client.stop.assert_not_called()
        assert len(plugin.connections) == 1
        remaining = next(iter(plugin.connections.values()))
        assert remaining.listener_count == 1
        assert shared_client.monitors == [remaining.linkState]
        assert shared_client.nodes[paths[0]].listeners == (
            [remaining._updateVariable] if same_address else []
        )

        node = shared_client.nodes[paths[1]]
        for callback in node.listeners:
            callback(node.path, SimpleNamespace(value=42, severity="Good"))
        for callback in shared_client.monitors:
            callback(False)
        writers[1].value[int].emit(7)
        app.processEvents()
        assert values[1] == [42]
        assert states[1] == [False]
        node.setDisp.assert_called_once_with(7, index=-1)

        if not destroying:
            assert values[0] == []
            assert states[0] == []
            for fake_node in shared_client.nodes.values():
                fake_node.setDisp.reset_mock()
            writers[0].value[int].emit(99)
            app.processEvents()
            for fake_node in shared_client.nodes.values():
                fake_node.setDisp.assert_not_called()

        plugin.remove_connection(channels[1], destroying=destroying)
        assert plugin.connections == {}
        assert shared_client.monitors == []
        assert all(not node.listeners for node in shared_client.nodes.values())
        shared_client.stop.assert_not_called()
        remaining.close()  # Repeated cleanup must be harmless.

        # Reopening a plot can reuse the still-running client.
        plugin.add_connection(channels[0])
        assert next(iter(plugin.connections.values())).listener_count == 1
        shared_client.stop.assert_not_called()
    finally:
        for channel in channels:
            plugin.remove_connection(channel)


def test_connection_without_client_can_close(app, monkeypatch):
    monkeypatch.setattr(rogue_plugin.utilities, "is_pydm_app", lambda: False)
    channel = PyDMChannel(address="rogue://localhost:9099/root.First")
    conn = RogueConnection(channel, "localhost:9099/root.First")
    conn.close()
    conn.close()
