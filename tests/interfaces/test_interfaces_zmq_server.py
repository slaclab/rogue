#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

import json
import pickle

import pyrogue.interfaces._ZmqServer as zmq_server_mod


class FakeRoot:
    def __init__(self, node_map):
        self.node_map = node_map
        self.listeners = []

    def addVarListener(self, **kwargs):
        self.listeners.append(kwargs)

    def getNode(self, path):
        return self.node_map.get(path)


class FakeNode:
    def __init__(self):
        self.value = "node-value"

    def multiply(self, lhs, rhs=1):
        return lhs * rhs


def test_zmq_server_registers_listener_and_resolves_address(monkeypatch):
    monkeypatch.setattr(zmq_server_mod.rogue.interfaces.ZmqServer, "__init__", lambda self, addr, port: (setattr(self, "_port", port), None))
    monkeypatch.setattr(zmq_server_mod.ZmqServer, "port", lambda self: self._port)

    root = FakeRoot({})
    server = zmq_server_mod.ZmqServer(root=root, addr="*", port=9100, incGroups="A", excGroups="B")

    # Capture the root listener registration so update batching stays filtered
    # the same way it would in a live server.
    assert root.listeners == [{
        "func": server._varUpdate,
        "done": server._varDone,
        "incGroups": "A",
        "excGroups": "B",
    }]
    assert server.address == "127.0.0.1:9100"

    server._addr = "example.com"
    assert server.address == "example.com:9100"


def test_zmq_server_operation_request_and_string_paths(monkeypatch, capsys):
    monkeypatch.setattr(zmq_server_mod.rogue.interfaces.ZmqServer, "__init__", lambda self, addr, port: setattr(self, "_port", port))
    monkeypatch.setattr(zmq_server_mod.ZmqServer, "port", lambda self: self._port)
    monkeypatch.setattr(zmq_server_mod.rogue.interfaces.ZmqServer, "_start", lambda self: setattr(self, "_started", True))

    node = FakeNode()
    root = FakeRoot({"root.Node": node})
    server = zmq_server_mod.ZmqServer(root=root, addr="127.0.0.1", port=9200)

    assert server._doOperation({"path": "__ROOT__", "attr": None}) is root
    assert server._doOperation({"path": "root.Node", "attr": "value"}) == "node-value"
    assert server._doOperation({"path": "root.Node", "attr": "multiply", "args": (6,), "kwargs": {"rhs": 7}}) == 42
    assert server._doOperation({"path": "missing.Node", "attr": "value"}) is None

    request = pickle.dumps({"path": "root.Node", "attr": "multiply", "args": (3,), "kwargs": {"rhs": 5}})
    assert pickle.loads(server._doRequest(request)) == 15

    bad_request = pickle.dumps({"path": "root.Node", "attr": "multiply", "args": (), "kwargs": {"rhs": 5}})
    assert isinstance(pickle.loads(server._doRequest(bad_request)), Exception)

    # Verify that unpicklable exceptions are converted to a standard Exception
    # instead of crashing the server (ESROGUE-723).
    class _UnpicklableError(Exception):
        """An exception whose module cannot be resolved by pickle."""
        pass
    _UnpicklableError.__module__ = "Boost.Python"
    _UnpicklableError.__qualname__ = "ArgumentError"

    def _raise_unpicklable(*args, **kwargs):
        raise _UnpicklableError("bad argument")
    node.trigger_unpicklable = _raise_unpicklable

    unpicklable_request = pickle.dumps({"path": "root.Node", "attr": "trigger_unpicklable"})
    result = pickle.loads(server._doRequest(unpicklable_request))
    assert type(result) is Exception
    assert "Boost.Python.ArgumentError" in str(result)
    assert "bad argument" in str(result)

    assert server._doString(json.dumps({"path": "root.Node", "attr": "value"})) == "node-value"
    assert server._doString(json.dumps({"path": "root.Node", "attr": "multiply", "args": [2], "kwargs": {"rhs": 4}})) == "8"
    assert server._doString("{bad json") == "EXCEPTION: Expecting property name enclosed in double quotes: line 1 column 2 (char 1)"

    published = []
    server._publish = lambda payload: published.append(pickle.loads(payload))
    server._varUpdate("root.Node.value", 5)
    server._varUpdate("root.Node.other", 7)
    server._varDone()
    assert published == [{"root.Node.value": 5, "root.Node.other": 7}]
    assert server._updateList == {}

    server._start()
    out = capsys.readouterr().out
    assert server._started is True
    assert "Started zmqServer on ports 9200-9202" in out
