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


class ZmqIntegrationDevice(pr.Device):
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

        self.add(pr.LocalVariable(
            name="HiddenValue",
            value=5,
            mode="RW",
            groups=["NoServe"],
        ))

        self.add(pr.LocalCommand(
            name="Multiply",
            value=0,
            retValue=0,
            function=lambda arg: arg * 3,
        ))


class ZmqIntegrationRoot(pr.Root):
    def __init__(self, *, port):
        super().__init__(name="Top", pollEn=False)
        self.add(ZmqIntegrationDevice(name="Dev"))

        # Use a caller-provided free port block because this Rogue build does
        # not support auto-binding ZMQ servers with port=0.
        self.zmqServer = pr_interfaces.ZmqServer(root=self, addr="*", port=port)
        self.addInterface(self.zmqServer)


def test_virtual_client_over_zmq(wait_until, free_zmq_port):
    pr_interfaces.VirtualClient.ClientCache.clear()

    with ZmqIntegrationRoot(port=free_zmq_port) as root:
        client = pr_interfaces.VirtualClient(addr="127.0.0.1", port=root.zmqServer.port())

        try:
            remote_root = client.root
            assert remote_root.name == "Top"
            assert client.Top is remote_root

            remote_dev = remote_root.Dev
            remote_value = remote_root.getNode("Top.Dev.Value")
            assert remote_value is remote_dev.Value
            assert remote_root.getNode("root.Dev.EnumValue") is remote_dev.EnumValue

            # Verify that direct method/property access on the virtual tree
            # performs real ZMQ round-trips against the live root.
            assert remote_dev.Value.get() == 1
            remote_dev.Value.set(7)
            assert root.Dev.Value.get() == 7

            remote_dev.EnumValue.setDisp("One")
            assert root.Dev.EnumValue.get() == 1
            assert remote_dev.Multiply(4) == 12

            updates = []

            # Virtual leaf listeners are driven by the VirtualClient update
            # subscription path rather than local method calls.
            remote_value.addListener(lambda path, value: updates.append((path, value.value)))
            root.Dev.Value.set(9)
            assert wait_until(lambda: ("Top.Dev.Value", 9) in updates, timeout=5.0)
        finally:
            client.stop()
            pr_interfaces.VirtualClient.ClientCache.clear()


def test_virtual_client_respects_noserve_update_filter(wait_until, free_zmq_port):
    pr_interfaces.VirtualClient.ClientCache.clear()

    with ZmqIntegrationRoot(port=free_zmq_port) as root:
        client = pr_interfaces.VirtualClient(addr="127.0.0.1", port=root.zmqServer.port())

        try:
            remote_dev = client.root.Dev
            visible_updates = []

            # The NoServe group suppresses publication entirely, so the hidden
            # node is not exposed through the remote tree at all.
            remote_dev.Value.addListener(lambda path, value: visible_updates.append((path, value.value)))
            assert client.root.getNode("Top.Dev.HiddenValue") is None
            assert not hasattr(remote_dev, "HiddenValue")

            root.Dev.Value.set(11)
            root.Dev.HiddenValue.set(17)

            assert wait_until(lambda: ("Top.Dev.Value", 11) in visible_updates, timeout=5.0)
        finally:
            client.stop()
            pr_interfaces.VirtualClient.ClientCache.clear()
