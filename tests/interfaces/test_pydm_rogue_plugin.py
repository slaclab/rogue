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

import pytest

try:
    from pyrogue.pydm.data_plugins.rogue_plugin import RogueConnection
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
    conn = object.__new__(RogueConnection)
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


class _SharedClient:
    def __init__(self):
        self.monitors = []
        self.stopCalls = 0

    def addLinkMonitor(self, function):
        self.monitors.append(function)

    def remLinkMonitor(self, function):
        self.monitors.remove(function)

    def stop(self):
        self.stopCalls += 1


def test_rogue_connection_remove_listener_keeps_shared_client_running():
    client = _SharedClient()
    connA = SimpleNamespace(_client=client, linkState=object())
    connB = SimpleNamespace(_client=client, linkState=object())

    for conn in (connA, connB):
        client.addLinkMonitor(conn.linkState)

    RogueConnection.remove_listener(connA, channel=None, destroying=True)

    assert client.stopCalls == 0
    assert client.monitors == [connB.linkState]
