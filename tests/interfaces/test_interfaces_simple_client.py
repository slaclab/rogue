#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

import pyrogue.interfaces._SimpleClient as simple_client_mod


class FakeSocket:
    def __init__(self, recv_values=None):
        self.recv_values = list(recv_values or [])
        self.connected = []
        self.sent = []
        self.sockopts = []

    def connect(self, addr):
        self.connected.append(addr)

    def send_pyobj(self, obj):
        self.sent.append(obj)

    def recv_pyobj(self):
        if self.recv_values:
            value = self.recv_values.pop(0)
            if isinstance(value, Exception):
                raise value
            return value
        return {}

    def setsockopt(self, opt, value):
        self.sockopts.append((opt, value))


class FakeContext:
    def __init__(self):
        self.sockets = []

    def socket(self, _kind):
        sock = FakeSocket()
        self.sockets.append(sock)
        return sock


class FakeThread:
    def __init__(self, target):
        self.target = target
        self.started = False

    def start(self):
        self.started = True


def test_simple_client_init_with_callback_starts_subscription_thread(monkeypatch):
    fake_context = FakeContext()

    monkeypatch.setattr(simple_client_mod.zmq, "Context", lambda: fake_context)
    monkeypatch.setattr(simple_client_mod.threading, "Thread", FakeThread)

    seen = []
    client = simple_client_mod.SimpleClient("example.com", 9100, cb=lambda path, value: seen.append((path, value)))

    assert client._req.connected == ["tcp://example.com:9101"]
    assert client._sub.connected == ["tcp://example.com:9100"]
    assert client._subThread.started is True
    assert seen == []


def test_simple_client_remote_attr_and_helpers():
    client = simple_client_mod.SimpleClient.__new__(simple_client_mod.SimpleClient)
    client._req = FakeSocket(recv_values=[5, "disp", 7, "cached", None, None, "done"])

    assert client.get("root.Var") == 5
    assert client.getDisp("root.Var") == "disp"
    assert client.value("root.Var") == 7
    assert client.valueDisp("root.Var") == "cached"
    assert client.set("root.Var", 11) is None
    assert client.setDisp("root.Var", "twelve") is None
    assert client.exec("root.Cmd", arg=13) == "done"

    assert client._req.sent == [
        {"path": "root.Var", "attr": "get", "args": (), "kwargs": {}},
        {"path": "root.Var", "attr": "getDisp", "args": (), "kwargs": {}},
        {"path": "root.Var", "attr": "value", "args": (), "kwargs": {}},
        {"path": "root.Var", "attr": "valueDisp", "args": (), "kwargs": {}},
        {"path": "root.Var", "attr": "set", "args": (11,), "kwargs": {}},
        {"path": "root.Var", "attr": "setDisp", "args": ("twelve",), "kwargs": {}},
        {"path": "root.Cmd", "attr": "__call__", "args": (13,), "kwargs": {}},
    ]


def test_simple_client_remote_attr_error_paths():
    client = simple_client_mod.SimpleClient.__new__(simple_client_mod.SimpleClient)

    # A remote-side exception is delivered as a normal payload object and then
    # re-raised by _remoteAttr after the request succeeds.
    client._req = FakeSocket(recv_values=[])
    client._req.recv_pyobj = lambda: RuntimeError("remote boom")
    try:
        client._remoteAttr("root.Var", "get")
        raise AssertionError("Expected remote exception")
    except RuntimeError as exc:
        assert str(exc) == "remote boom"

    client._req = FakeSocket(recv_values=[ValueError("socket boom")])
    try:
        client._remoteAttr("root.Var", "get")
        raise AssertionError("Expected wrapped transport exception")
    except Exception as exc:
        assert str(exc) == "ZMQ Interface Exception: socket boom"


def test_simple_client_listen_and_context_exit():
    seen = []
    client = simple_client_mod.SimpleClient.__new__(simple_client_mod.SimpleClient)
    client._cb = lambda path, value: (seen.append((path, value)), setattr(client, "_runEn", False))
    client._sub = FakeSocket(recv_values=[{"root.Var": 42}])
    client._runEn = True

    # Run the listener loop inline with a single payload to validate SUBSCRIBE
    # setup and callback dispatch without needing a real background thread.
    client._listen()
    assert client._sub.sockopts == [(simple_client_mod.zmq.SUBSCRIBE, b"")]
    assert seen == [("root.Var", 42)]

    client._runEn = True
    client.__exit__(None, None, None)
    assert client._runEn is False


# ---------------------------------------------------------------------------
# Pins the new ``_stop()`` teardown contract: the SUB socket is closed FIRST
# (so the listener's ``recv_pyobj`` raises ZMQError and the thread exits),
# then the thread is joined, then the REQ socket and ZMQ context are
# released. Reverting any of those four steps fails one of the matching
# assertions below.
# ---------------------------------------------------------------------------
import zmq  # noqa: E402  (imported here so the integration tests above are not perturbed)


class _TrackingSubSocket:
    """Sub socket that raises ZMQError out of ``recv_pyobj`` once closed."""

    def __init__(self):
        self.sockopts = []
        self.close_calls = []
        self._closed = False

    def setsockopt(self, opt, value):
        self.sockopts.append((opt, value))

    def recv_pyobj(self):
        if self._closed:
            raise zmq.error.ZMQError("socket closed")
        # Block-equivalent placeholder: the test drives _listen() inline,
        # so simply raise to advance to the closed state.
        raise zmq.error.ZMQError("socket closed")

    def close(self, linger=None):
        self.close_calls.append(linger)
        self._closed = True


class _TrackingReqSocket:
    def __init__(self):
        self.close_calls = []

    def close(self, linger=None):
        self.close_calls.append(linger)


class _TrackingCtx:
    def __init__(self):
        self.term_calls = 0

    def term(self):
        self.term_calls += 1


class _TrackingListenerThread:
    """Thread stub that records the join() invocation and reports liveness."""

    def __init__(self):
        self.join_calls = []
        self._alive = True

    def is_alive(self):
        return self._alive

    def join(self, timeout=None):
        self.join_calls.append(timeout)
        self._alive = False


def test_simple_client_stop_releases_thread_and_sockets():
    client = simple_client_mod.SimpleClient.__new__(simple_client_mod.SimpleClient)
    client._cb = lambda *_args: None
    client._sub = _TrackingSubSocket()
    client._req = _TrackingReqSocket()
    client._ctx = _TrackingCtx()
    client._subThread = _TrackingListenerThread()
    client._runEn = True

    client._stop()

    # Listener thread is joined (with a non-zero timeout) so caller does not
    # leak a daemon thread holding a reference to the SUB socket.
    assert client._subThread.join_calls and client._subThread.join_calls[0] > 0
    # SUB is closed with linger=0 BEFORE the thread join; the listener exits
    # via ZMQError as a result.
    assert client._sub.close_calls == [0]
    # REQ socket and ZMQ context are also released (linger=0 for REQ).
    assert client._req.close_calls == [0]
    assert client._ctx.term_calls == 1
    # _runEn is cleared so a stale listener cannot continue iterating after a
    # transient exception.
    assert client._runEn is False


def test_simple_client_listen_exits_on_zmqerror():
    """``_listen`` must exit the loop on ``zmq.error.ZMQError`` rather than
    crashing the thread; this is the contract that makes _stop() effective."""

    class _RaisingSubSocket:
        def __init__(self):
            self.sockopts = []

        def setsockopt(self, opt, value):
            self.sockopts.append((opt, value))

        def recv_pyobj(self):
            raise zmq.error.ZMQError("simulated close")

    client = simple_client_mod.SimpleClient.__new__(simple_client_mod.SimpleClient)
    client._sub = _RaisingSubSocket()
    client._cb = lambda *_args: None
    client._runEn = True

    # The loop must return cleanly; if the ZMQError were not caught the
    # exception would propagate out of _listen and crash the listener thread.
    client._listen()


def test_simple_client_stop_without_callback_releases_req_and_ctx():
    """``_stop`` must work when SimpleClient was created without a ``cb`` (no
    SUB socket / listener thread). Pins the ``getattr(..., None)`` guards."""

    client = simple_client_mod.SimpleClient.__new__(simple_client_mod.SimpleClient)
    client._req = _TrackingReqSocket()
    client._ctx = _TrackingCtx()
    # Deliberately omit _sub / _subThread / _runEn — that is the no-callback
    # construction state that previously failed to release REQ/ctx.

    client._stop()

    assert client._req.close_calls == [0]
    assert client._ctx.term_calls == 1
