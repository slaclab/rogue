import pickle

import pyrogue as pr
import pyrogue.interfaces._Virtual as virtual_mod


class FakeThread:
    def __init__(self, target):
        self.target = target
        self.started = False

    def start(self):
        self.started = True


class FakeVirtualRemote:
    def __init__(self):
        self.calls = []
        self.var_listeners = []

    def _remoteAttr(self, path, attr, *args, **kwargs):
        self.calls.append((path, attr, args, kwargs))

        # Return serialized child nodes the same way a real ZMQ-backed root
        # would, so VirtualNode lazy-loading can be exercised end-to-end.
        if (path, attr) == ("root", "nodes"):
            return {
                "Child": virtual_mod.VirtualFactory({
                    "name": "Child",
                    "class": "ChildDevice",
                    "bases": [str(pr.Node)],
                    "description": "child",
                    "groups": [],
                    "path": "root.Child",
                    "expand": True,
                    "guiGroup": None,
                    "nodes": {"LeafVar": None},
                    "props": [],
                    "funcs": {"ping": {"args": [], "kwargs": []}},
                }),
            }

        if (path, attr) == ("root.Child", "nodes"):
            return {
                "LeafVar": virtual_mod.VirtualFactory({
                    "name": "LeafVar",
                    "class": "LeafVar",
                    "bases": [str(pr.BaseVariable)],
                    "description": "leaf",
                    "groups": [],
                    "path": "root.Child.LeafVar",
                    "expand": True,
                    "guiGroup": None,
                    "nodes": {},
                    "props": ["mode"],
                    "funcs": {},
                }),
            }

        if (path, attr) == ("root", "status"):
            return "OK"

        if (path, attr) == ("root", "ping"):
            return "pong"

        if (path, attr) == ("root.Cmd", "__call__"):
            return args[0]

        if (path, attr) == ("root.Child", "ping"):
            return "child-pong"

        if (path, attr) == ("root.Child.LeafVar", "mode"):
            return "RW"

        raise AssertionError(f"Unexpected remoteAttr call: {(path, attr, args, kwargs)}")

    def _addVarListener(self, func):
        self.var_listeners.append(func)


def _make_virtual_root():
    root = virtual_mod.VirtualFactory({
        "name": "root",
        "class": "RootNode",
        "bases": [str(pr.Root)],
        "description": "root desc",
        "groups": [],
        "path": "root",
        "expand": True,
        "guiGroup": None,
        "nodes": {"Child": None},
        "props": ["status"],
        "funcs": {"ping": {"args": [], "kwargs": []}},
    })
    client = FakeVirtualRemote()
    root._parent = root
    root._root = root
    root._client = client
    return root, client


def test_virtual_factory_dynamic_methods_properties_and_listeners():
    root, client = _make_virtual_root()

    assert root.status == "OK"
    assert root.ping() == "pong"

    child = root.Child
    assert child._parent is root
    assert child._root is root
    assert child._client is client
    assert root.getNode("root.Child") is child
    assert root.getNode("root.Child.LeafVar") is child.LeafVar
    assert child.ping() == "child-pong"

    leaf = child.LeafVar
    assert leaf.mode == "RW"

    seen = []
    # Listener callbacks are stored on the virtual leaf itself and invoked by
    # _doUpdate() when VirtualClient dispatches a remote update.
    leaf.addListener(lambda path, value: seen.append((path, value)))
    leaf._doUpdate(123)
    assert seen == [("root.Child.LeafVar", 123)]
    leaf.delListener(leaf._functions[0])
    assert leaf._functions == []

    root.addVarListener(lambda *_args: None)
    assert len(client.var_listeners) == 1


def test_virtual_factory_command_call_and_node_errors():
    cmd = virtual_mod.VirtualFactory({
        "name": "Cmd",
        "class": "CmdNode",
        "bases": [str(pr.BaseCommand)],
        "description": "cmd",
        "groups": [],
        "path": "root.Cmd",
        "expand": True,
        "guiGroup": None,
        "nodes": {},
        "props": [],
        "funcs": {},
    })
    client = FakeVirtualRemote()
    cmd._client = client

    assert cmd("value") == "value"
    assert cmd.isinstance(pr.BaseCommand) is True

    for func in (cmd.addToGroup, cmd.removeFromGroup, cmd.add, cmd.callRecursive, cmd._getDict, cmd._setDict):
        try:
            if func is cmd.addToGroup or func is cmd.removeFromGroup:
                func("x")
            elif func is cmd.add:
                func(cmd)
            elif func is cmd.callRecursive:
                func(lambda: None)
            else:
                func([])
            raise AssertionError("Expected NodeError")
        except pr.NodeError:
            pass


def test_virtual_client_cache_update_dispatch_and_monitor(monkeypatch):
    virtual_mod.VirtualClient.ClientCache.clear()

    monkeypatch.setattr(virtual_mod.rogue.interfaces.ZmqClient, "__init__", lambda self, addr, port, flag: (setattr(self, "_host", addr), setattr(self, "_port", port)))
    monkeypatch.setattr(virtual_mod.VirtualClient, "setTimeout", lambda self, timeout, enabled: setattr(self, "_timeouts", getattr(self, "_timeouts", []) + [(timeout, enabled)]))
    monkeypatch.setattr(virtual_mod.threading, "Thread", FakeThread)

    root = virtual_mod.VirtualFactory({
        "name": "Top",
        "class": "RootNode",
        "bases": [str(pr.Root)],
        "description": "root desc",
        "groups": [],
        "path": "Top",
        "expand": True,
        "guiGroup": None,
        "nodes": {"Leaf": None},
        "props": [],
        "funcs": {},
    })
    root.Time = type("FakeTimeNode", (), {"value": lambda self: 100.0})()

    def fake_remote_attr(self, path, attr, *args, **kwargs):
        if path == "__ROOT__":
            return root
        raise AssertionError(f"Unexpected remote attr: {(path, attr, args, kwargs)}")

    monkeypatch.setattr(virtual_mod.VirtualClient, "_remoteAttr", fake_remote_attr)

    client = virtual_mod.VirtualClient("localhost", 9200)
    same_client = virtual_mod.VirtualClient("localhost", 9200)
    assert client is same_client
    assert client.root is root
    assert client.linked is True
    assert client._monThread.started is True
    assert client._timeouts == [(1000, False), (1000, True)]

    root._nodes["Leaf"] = virtual_mod.VirtualFactory({
        "name": "Leaf",
        "class": "LeafVar",
        "bases": [str(pr.BaseVariable)],
        "description": "leaf",
        "groups": [],
        "path": "Top.Leaf",
        "expand": True,
        "guiGroup": None,
        "nodes": {},
        "props": [],
        "funcs": {},
    })
    root._nodes["Leaf"]._client = client
    root._nodes["Leaf"]._root = root
    root._nodes["Leaf"]._parent = root
    root._loaded = True

    leaf_updates = []
    root._nodes["Leaf"].addListener(lambda path, value: leaf_updates.append((path, value)))
    global_updates = []
    client._addVarListener(lambda path, value: global_updates.append((path, value)))

    client._doUpdate(pickle.dumps({"Top.Leaf": 55, "Top.Missing": 99}))
    assert leaf_updates == [("Top.Leaf", 55)]
    assert global_updates == [("Top.Leaf", 55), ("Top.Missing", 99)]

    monitors = []
    client.addLinkMonitor(monitors.append)
    client._link = True
    client._ltime = 0.0

    times = iter([20.0, 5.0, 5.0, 5.0])
    sleeps = {"count": 0}

    def fake_time():
        return next(times)

    def fake_sleep(_seconds):
        sleeps["count"] += 1
        if sleeps["count"] == 2:
            # After the link-loss callback fires, make the heartbeat appear
            # recent again so the next loop trips the restore path.
            client._ltime = 4.0
        elif sleeps["count"] == 3:
            client._monEnable = False

    monkeypatch.setattr(virtual_mod.time, "time", fake_time)
    monkeypatch.setattr(virtual_mod.time, "sleep", fake_sleep)

    client._monEnable = True
    client._monWorker()
    assert monitors == [False, True]

    client.stop()
    assert client._monEnable is False
