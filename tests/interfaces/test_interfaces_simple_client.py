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
