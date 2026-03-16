import pyrogue as pr
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

        self.add(pr.LocalCommand(
            name="Multiply",
            value=0,
            retValue=0,
            function=lambda arg: arg * 3,
        ))


class ZmqIntegrationRoot(pr.Root):
    def __init__(self):
        super().__init__(name="Top", pollEn=False)
        self.add(ZmqIntegrationDevice(name="Dev"))

        # Bind to an ephemeral port so the test can run alongside other local
        # Rogue services without depending on a fixed editor/CI port layout.
        self.zmqServer = pr.interfaces.ZmqServer(root=self, addr="127.0.0.1", port=0)
        self.addInterface(self.zmqServer)


def test_virtual_client_over_zmq(wait_until):
    pr.interfaces.VirtualClient.ClientCache.clear()

    with ZmqIntegrationRoot() as root:
        client = pr.interfaces.VirtualClient(addr="127.0.0.1", port=root.zmqServer.port())

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
            pr.interfaces.VirtualClient.ClientCache.clear()
