import pyrogue.interfaces.simulation as sim_mod
import rogue.interfaces.memory


class FakeZmqSocket:
    def __init__(self):
        self.connected = []
        self.sent = []
        self.to_recv = []

    def connect(self, addr):
        self.connected.append(addr)

    def send(self, payload):
        self.sent.append(bytes(payload))

    def recv(self):
        return self.to_recv.pop(0)


class FakeZmqContext:
    def __init__(self):
        self.sockets = []

    def socket(self, _kind):
        sock = FakeZmqSocket()
        self.sockets.append(sock)
        return sock


class FakeThread:
    def __init__(self, target):
        self.target = target
        self.started = False

    def start(self):
        self.started = True


class FakeTransaction:
    def __init__(self, *, address, size, tx_type, payload=None):
        self._address = address
        self._size = size
        self._type = tx_type
        self._payload = bytearray(payload or bytes(size))
        self.error_msg = None
        self.done_called = False
        self.readback = None

    def address(self):
        return self._address

    def size(self):
        return self._size

    def type(self):
        return self._type

    def getData(self, buffer, offset):
        buffer[:] = self._payload[offset:offset + len(buffer)]

    def setData(self, buffer, offset):
        self.readback = bytes(buffer[offset:offset + len(buffer)])

    def error(self, msg):
        self.error_msg = msg

    def done(self):
        self.done_called = True


def test_sideband_sim_send_receive_and_stop(monkeypatch):
    fake_ctx = FakeZmqContext()
    monkeypatch.setattr(sim_mod.zmq, "Context", lambda: fake_ctx)
    monkeypatch.setattr(sim_mod.threading, "Thread", FakeThread)

    select_calls = {"count": 0}

    def fake_select(read_list, _write, _error, _timeout):
        select_calls["count"] += 1
        if select_calls["count"] == 1:
            return ([read_list[0]], [], [])
        sideband._run = False
        return ([], [], [])

    monkeypatch.setattr(sim_mod.zmq, "select", fake_select)

    sideband = sim_mod.SideBandSim("127.0.0.1", 9000)
    assert sideband._sbPush.connected == ["tcp://127.0.0.1:9001"]
    assert sideband._sbPull.connected == ["tcp://127.0.0.1:9000"]
    assert sideband._recvThread.started is True

    sideband.send(opCode=0x12, remData=0x34)
    assert sideband._sbPush.sent == [b"\x01\x12\x01\x34"]

    seen = []
    sideband.setRecvCb(lambda op_code, rem_data: seen.append((op_code, rem_data)))
    sideband._sbPull.to_recv.append(b"\x01\x56\x01\x78")
    sideband._recvWorker()
    assert seen == [(0x56, 0x78)]

    sideband._stop()
    assert sideband._run is False


def test_sideband_sim_context_manager_stops_worker(monkeypatch):
    fake_ctx = FakeZmqContext()
    monkeypatch.setattr(sim_mod.zmq, "Context", lambda: fake_ctx)
    monkeypatch.setattr(sim_mod.threading, "Thread", FakeThread)
    monkeypatch.setattr(sim_mod.zmq, "select", lambda *_args: ([], [], []))

    with sim_mod.SideBandSim("127.0.0.1", 9100) as sideband:
        assert sideband._run is True

    assert sideband._run is False


def test_pgp2b_sim_connects_virtual_channels(monkeypatch):
    stream_links = []

    monkeypatch.setattr(sim_mod.rogue.interfaces.stream, "TcpClient", lambda host, port: (host, port))
    monkeypatch.setattr(sim_mod.pyrogue, "streamConnectBiDir", lambda left, right: stream_links.append((left, right)))

    class FakeSideBand:
        def __init__(self, host, port):
            self.host = host
            self.port = port
            self.recv_cb = None
            self.stopped = False

        def setRecvCb(self, cb):
            self.recv_cb = cb

        def send(self, opCode=None, remData=None):
            self.last_send = (opCode, remData)

        def _stop(self):
            self.stopped = True

    monkeypatch.setattr(sim_mod, "SideBandSim", FakeSideBand)

    pgp_a = sim_mod.Pgp2bSim(2, "hostA", 1000)
    pgp_b = sim_mod.Pgp2bSim(2, "hostB", 2000)

    sim_mod.connectPgp2bSim(pgp_a, pgp_b)
    assert stream_links == [
        (("hostA", 1000), ("hostB", 2000)),
        (("hostA", 1002), ("hostB", 2002)),
    ]
    assert pgp_a.sb.recv_cb == pgp_b.sb.send
    assert pgp_b.sb.recv_cb == pgp_a.sb.send

    pgp_a._stop()
    assert pgp_a.sb.stopped is True


def test_mem_emulate_handles_write_read_and_errors():
    drop_mem = sim_mod.MemEmulate(minWidth=4, maxSize=8, dropCount=1)

    # The first transaction is intentionally dropped to exercise the retry/drop
    # path used by older retry-oriented tests.
    dropped = FakeTransaction(address=0x0, size=4, tx_type=rogue.interfaces.memory.Write, payload=b"\x01\x02\x03\x04")
    drop_mem._doTransaction(dropped)
    assert dropped.done_called is False

    mem = sim_mod.MemEmulate(minWidth=4, maxSize=8)
    write_tx = FakeTransaction(address=0x0, size=4, tx_type=rogue.interfaces.memory.Write, payload=b"\x01\x02\x03\x04")
    mem._doTransaction(write_tx)
    assert write_tx.done_called is True

    read_tx = FakeTransaction(address=0x0, size=4, tx_type=rogue.interfaces.memory.Read)
    mem._doTransaction(read_tx)
    assert read_tx.readback == b"\x01\x02\x03\x04"
    assert read_tx.done_called is True

    misaligned = FakeTransaction(address=0x2, size=4, tx_type=rogue.interfaces.memory.Read)
    mem._doTransaction(misaligned)
    assert "not aligned" in misaligned.error_msg

    oversized = FakeTransaction(address=0x0, size=16, tx_type=rogue.interfaces.memory.Read)
    mem._doTransaction(oversized)
    assert "exceeds max" in oversized.error_msg


def test_mem_emulate_reports_access_widths_and_post_transactions():
    mem = sim_mod.MemEmulate(minWidth=8, maxSize=16)

    assert mem._doMinAccess() == 8
    assert mem._doMaxAccess() == 16
    assert mem._checkRange(0x100, 4) == 0

    # Post transactions follow the same write path but are used by callers
    # that do not wait for a readback response.
    post_tx = FakeTransaction(address=0x20, size=4, tx_type=rogue.interfaces.memory.Post, payload=b"\xaa\xbb\xcc\xdd")
    mem._doTransaction(post_tx)
    assert post_tx.done_called is True

    read_tx = FakeTransaction(address=0x20, size=4, tx_type=rogue.interfaces.memory.Read)
    mem._doTransaction(read_tx)
    assert read_tx.readback == b"\xaa\xbb\xcc\xdd"
