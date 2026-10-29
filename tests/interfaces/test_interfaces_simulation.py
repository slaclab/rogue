#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

import pytest

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


# Pins the contract that ``SideBandSim._stop()`` joins the rx worker AND
# closes both ZMQ sockets AND tears down the context. The previous
# implementation only flipped ``_run`` and relied on Python GC for the rest,
# which kept the ZMQ context alive for arbitrary time after the simulator
# went out of scope. Reverting any of the three releases makes the matching
# assertion below trip.
#
# The PUSH socket closes with a bounded, non-zero linger so frames queued by
# ``send()`` immediately before ``_stop()`` drain once the simulator's PULL
# side connects (see the real-socket test further below). The PULL socket has
# nothing outbound and closes with linger=0.
class _TrackingZmqSocket:
    def __init__(self):
        self.connected = []
        self.sent = []
        self.to_recv = []
        self.close_calls = []

    def connect(self, addr):
        self.connected.append(addr)

    def send(self, payload):
        self.sent.append(bytes(payload))

    def recv(self):
        return self.to_recv.pop(0)

    def close(self, linger=None):
        self.close_calls.append(linger)


class _TrackingZmqContext:
    def __init__(self):
        self.sockets = []
        self.term_calls = 0

    def socket(self, _kind):
        sock = _TrackingZmqSocket()
        self.sockets.append(sock)
        return sock

    def term(self):
        self.term_calls += 1


class _TrackingThread:
    def __init__(self, target):
        self.target = target
        self.started = False
        self.alive = False
        self.join_calls = []

    def start(self):
        self.started = True
        self.alive = True

    def is_alive(self):
        return self.alive

    def join(self, timeout=None):
        self.join_calls.append(timeout)
        self.alive = False


def test_sideband_sim_stop_releases_sockets_thread_and_context(monkeypatch):
    fake_ctx = _TrackingZmqContext()
    monkeypatch.setattr(sim_mod.zmq, "Context", lambda: fake_ctx)
    monkeypatch.setattr(sim_mod.threading, "Thread", _TrackingThread)

    sideband = sim_mod.SideBandSim("127.0.0.1", 9200)
    assert sideband._recvThread.started is True

    push_sock = sideband._sbPush
    pull_sock = sideband._sbPull

    sideband._stop()

    # Thread is joined exactly once with a non-zero timeout.
    assert sideband._recvThread.join_calls and sideband._recvThread.join_calls[0] > 0
    # PUSH closes with a bounded linger so queued sideband frames are flushed
    # rather than dropped; PULL has nothing outbound and closes immediately.
    assert push_sock.close_calls == [sim_mod.SideBandSim._PUSH_LINGER_MS]
    assert 0 < sim_mod.SideBandSim._PUSH_LINGER_MS <= 2000
    assert pull_sock.close_calls == [0]
    # Context is terminated exactly once.
    assert fake_ctx.term_calls == 1
    # _stop must remain idempotent: a second call must not raise even though
    # the sockets/context are now in a torn-down state. The implementation
    # does not gate term()/close() with an "already-stopped" flag; instead
    # it tolerates the second teardown via the try/except in _stop(), so a
    # repeated term() call is allowed but exception-safe.
    sideband._stop()
    assert fake_ctx.term_calls in (1, 2)


# Regression test for the frame-drop race: ``send()`` queues on a PUSH socket
# whose TCP connection may not be up yet (client started before the simulator
# bound its ports). If a sideband event arrives from the simulator between
# ``send()`` and ``_stop()``, the rx worker exits at once instead of waiting
# out its 1 s select timeout, so ``_stop()`` reaches ``close()`` microseconds
# after ``send()``. With ``linger=0`` the queued frames were discarded with
# no error on either side. Stock code loses frames in roughly half of the
# iterations below; with a bounded PUSH linger it loses none.
def _free_port_pair():
    import socket
    while True:
        with socket.socket() as s0, socket.socket() as s1:
            s0.bind(("127.0.0.1", 0))
            base = s0.getsockname()[1]
            try:
                s1.bind(("127.0.0.1", base + 1))
            except OSError:
                continue
            return base


@pytest.mark.integration
def test_sideband_sim_stop_flushes_frames_sent_before_simulator_binds():
    import threading
    import time
    import zmq

    ctx = zmq.Context()
    iterations = 10
    dropped = 0
    try:
        for _ in range(iterations):
            port = _free_port_pair()
            got_event = threading.Event()

            def client():
                with sim_mod.SideBandSim("127.0.0.1", port) as sb:
                    sb.setRecvCb(lambda op_code, rem_data: got_event.set())
                    got_event.wait(5.0)
                    sb.send(opCode=0x5c)
                    sb.send(remData=0x6d)
                # __exit__ -> _stop() runs right after the second send()

            thr = threading.Thread(target=client)
            thr.start()
            time.sleep(0.03)  # client connects first; simulator binds later

            # Simulator side: PUSH to the client's PULL, PULL from the client's PUSH.
            sim_push = ctx.socket(zmq.PUSH)
            sim_push.bind(f"tcp://127.0.0.1:{port}")
            sim_pull = ctx.socket(zmq.PULL)
            sim_pull.bind(f"tcp://127.0.0.1:{port + 1}")
            try:
                # Two closely spaced events, as the HDL side emits opCode and
                # remData separately. The second one wakes the rx worker right
                # after _run is cleared, which collapses the join wait.
                sim_push.send(bytes([1, 0x2a, 0, 0]))
                time.sleep(0.0005)
                sim_push.send(bytes([0, 0, 1, 0x3b]))
                thr.join(10.0)
                assert not thr.is_alive()

                frames = []
                while len(frames) < 2 and sim_pull.poll(1000):
                    frames.append(sim_pull.recv())
                if frames != [b"\x01\x5c\x00\x00", b"\x00\x00\x01\x6d"]:
                    dropped += 1
            finally:
                sim_push.close(linger=0)
                sim_pull.close(linger=0)
    finally:
        ctx.term()

    assert dropped == 0, f"client frames dropped in {dropped}/{iterations} iterations"


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
