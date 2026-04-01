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

import pyrogue as pr
import pyrogue.interfaces as pr_interfaces
import pytest


pytestmark = pytest.mark.integration


class SimpleClientIntegrationDevice(pr.Device):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.add(pr.LocalVariable(
            name="Value",
            value=1,
            mode="RW",
        ))

        self.add(pr.LocalVariable(
            name="EnumValue",
            value=0,
            mode="RW",
            enum={0: "Zero", 1: "One"},
        ))

        self.add(pr.LocalCommand(
            name="Multiply",
            value=0,
            retValue=0,
            function=lambda arg: arg * 3,
        ))


class SimpleClientIntegrationRoot(pr.Root):
    def __init__(self, *, port):
        super().__init__(name="Top", pollEn=False)
        self.add(SimpleClientIntegrationDevice(name="Dev"))

        # Use a caller-provided free port block because this Rogue build does
        # not support auto-binding ZMQ servers with port=0.
        self.zmqServer = pr_interfaces.ZmqServer(root=self, addr="*", port=port)
        self.addInterface(self.zmqServer)


def test_simple_client_over_zmq_round_trip(free_zmq_port):
    with SimpleClientIntegrationRoot(port=free_zmq_port) as root:
        with pr_interfaces.SimpleClient(addr="127.0.0.1", port=root.zmqServer.port()) as client:
            # Exercise the SimpleClient request/response API against a live
            # ZMQ-backed root rather than a mocked request socket.
            assert client.get("Top.Dev.Value") == 1
            assert client.value("Top.Dev.Value") == 1
            assert client.getDisp("Top.Dev.EnumValue") == "Zero"
            assert client.valueDisp("Top.Dev.EnumValue") == "Zero"

            client.set("Top.Dev.Value", 7)
            assert root.Dev.Value.get() == 7
            assert client.get("Top.Dev.Value") == 7

            client.setDisp("Top.Dev.EnumValue", "One")
            assert root.Dev.EnumValue.get() == 1
            assert client.valueDisp("Top.Dev.EnumValue") == "One"

            assert client.exec("Top.Dev.Multiply", arg=4) == 12
            assert client.get("Top.Dev.Missing") is None
