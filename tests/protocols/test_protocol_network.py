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
import pyrogue.protocols._Network as net_mod


class FakeUdp:
    def __init__(self, host=None, port=None, jumbo=False):
        self.host = host
        self.port = port
        self.jumbo = jumbo
        self.rx_buffer_count = None
        self.connections = []

    def __eq__(self, other):
        self.connections.append(other)
        return True

    def maxPayload(self):
        return 1024

    def setRxBufferCount(self, value):
        self.rx_buffer_count = value


class FakeRssi:
    def __init__(self, payload):
        self.payload = payload
        self.transport_endpoint = object()
        self.application_endpoint = object()
        self.open = False
        self.started = 0
        self.stopped = 0
        self.reset_count = 0
        self.setters = {}

    def transport(self):
        return self.transport_endpoint

    def application(self):
        return self.application_endpoint

    def _start(self):
        self.started += 1
        self.open = True

    def _stop(self):
        self.stopped += 1

    def resetCounters(self):
        self.reset_count += 1

    def getOpen(self):
        return self.open

    def getDownCount(self):
        return 1

    def getDropCount(self):
        return 2

    def getRetranCount(self):
        return 3

    def getLocBusy(self):
        return False

    def getLocBusyCnt(self):
        return 4

    def getRemBusy(self):
        return True

    def getRemBusyCnt(self):
        return 5

    def getLocTryPeriod(self):
        return 6

    def getLocMaxBuffers(self):
        return 7

    def getLocMaxSegment(self):
        return 8

    def getLocCumAckTout(self):
        return 9

    def getLocRetranTout(self):
        return 10

    def getLocNullTout(self):
        return 11

    def getLocMaxRetran(self):
        return 12

    def getLocMaxCumAck(self):
        return 13

    def curMaxBuffers(self):
        return 14

    def curMaxSegment(self):
        return 15

    def curCumAckTout(self):
        return 16

    def curRetranTout(self):
        return 17

    def curNullTout(self):
        return 18

    def curMaxRetran(self):
        return 19

    def curMaxCumAck(self):
        return 20

    def setLocMaxBuffers(self, value):
        self.setters["locMaxBuffers"] = value

    def setLocCumAckTout(self, value):
        self.setters["locCumAckTout"] = value

    def setLocRetranTout(self, value):
        self.setters["locRetranTout"] = value

    def setLocNullTout(self, value):
        self.setters["locNullTout"] = value

    def setLocMaxRetran(self, value):
        self.setters["locMaxRetran"] = value

    def setLocMaxCumAck(self, value):
        self.setters["locMaxCumAck"] = value

    def setLocTryPeriod(self, value):
        self.setters["locTryPeriod"] = value

    def setLocMaxSegment(self, value):
        self.setters["locMaxSegment"] = value


class FakePack:
    def __init__(self):
        self.transport_endpoint = object()
        self.destinations = []

    def transport(self):
        return self.transport_endpoint

    def application(self, dest):
        self.destinations.append(dest)
        return f"app:{dest}"


def test_udp_rssi_pack_client_defaults_and_variable_access(monkeypatch):
    fake_rssi = FakeRssi(1016)
    fake_udp = FakeUdp("host", 9000, True)
    fake_pack = FakePack()

    monkeypatch.setattr(net_mod.rogue.protocols.udp, "Client", lambda host, port, jumbo: fake_udp)
    monkeypatch.setattr(net_mod.rogue.protocols.rssi, "Client", lambda payload: fake_rssi)
    monkeypatch.setattr(net_mod.rogue.protocols.packetizer, "CoreV2", lambda *args: fake_pack)

    root = pr.Root(name="root", pollEn=False)
    dev = net_mod.UdpRssiPack(
        name="Net",
        host="host",
        port=9000,
        jumbo=True,
        wait=False,
        packVer=2,
        defaults={"locMaxBuffers": 21, "locNullTout": 22},
    )
    root.add(dev)

    assert fake_udp.connections == [fake_rssi.transport()]
    assert dev.application(3) == "app:3"
    assert fake_pack.destinations == [3]
    assert fake_rssi.setters["locMaxBuffers"] == 21
    assert fake_rssi.setters["locNullTout"] == 22

    with root:
        # The LocalVariables expose RSSI state through the normal variable API.
        assert dev.rssiOpen.get() is True
        assert dev.rssiDownCount.get() == 1
        assert dev.locBusy.get() is False
        assert dev.curMaxCumAck.get() == 20

        dev.locTryPeriod.set(31)
        dev.locMaxSegment.set(32)
        assert fake_rssi.setters["locTryPeriod"] == 31
        assert fake_rssi.setters["locMaxSegment"] == 32

        dev.countReset()
        assert fake_rssi.reset_count == 1


def test_udp_rssi_pack_start_and_stop_paths(monkeypatch):
    fake_rssi = FakeRssi(1016)
    fake_udp = FakeUdp("host", 9001, False)
    fake_pack = FakePack()

    monkeypatch.setattr(net_mod.rogue.protocols.udp, "Client", lambda host, port, jumbo: fake_udp)
    monkeypatch.setattr(net_mod.rogue.protocols.rssi, "Client", lambda payload: fake_rssi)
    monkeypatch.setattr(net_mod.rogue.protocols.packetizer, "Core", lambda en_ssi: fake_pack)
    monkeypatch.setattr(net_mod.time, "sleep", lambda _value: None)

    root = pr.Root(name="root", pollEn=False)
    dev = net_mod.UdpRssiPack(name="Net", host="host", port=9001, wait=True, server=False)
    root.add(dev)

    with root:
        assert fake_rssi.started == 1
        assert fake_udp.rx_buffer_count == 14

        dev._stop()
        assert fake_rssi.stopped == 1
        assert dev.rssiOpen.get() is True


def test_udp_rssi_pack_server_uses_server_backends(monkeypatch):
    fake_rssi = FakeRssi(1016)
    fake_udp = FakeUdp(port=9002, jumbo=True)
    fake_pack = FakePack()

    monkeypatch.setattr(net_mod.rogue.protocols.udp, "Server", lambda port, jumbo: fake_udp)
    monkeypatch.setattr(net_mod.rogue.protocols.rssi, "Server", lambda payload: fake_rssi)
    monkeypatch.setattr(net_mod.rogue.protocols.packetizer, "Core", lambda en_ssi: fake_pack)

    dev = net_mod.UdpRssiPack(name="Net", port=9002, server=True, wait=True, jumbo=True)
    assert dev._server is True
    assert fake_udp.port == 9002
