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
#
# Pins the contract that ``VirtualNode._loadNodes`` runs exactly once per
# instance even under concurrent first-access and that the matching
# ``_loaded = True`` flag is set AFTER ``self._nodes`` is fully populated.
# Without the double-checked-locking pair added in this branch, two threads
# racing on ``__getattr__`` / ``.nodes`` / ``.node()`` could both observe
# ``_loaded == False``, both enter ``_loadNodes()``, and produce a half-built
# ``_nodes`` dict (a remote ``nodes`` call done twice, with nodes re-parented
# to whichever caller wrote last). The test does not need real ZMQ -- it
# wires a fake ``_client`` whose ``_remoteAttr('nodes')`` is the slow
# operation we want to serialize.

import importlib.util
import threading
from pathlib import Path


def _load_virtual_module():
    """Load _Virtual.py without importing the rogue C++ extension.

    ``pyrogue.interfaces._Virtual`` imports ``rogue.interfaces`` to subclass
    ``ZmqClient`` for VirtualClient. We only want the Python-side
    VirtualNode class for this race test, so load the module directly via
    its file path with the C++ ZmqClient stubbed out.
    """
    module_path = (
        Path(__file__).resolve().parents[2]
        / "python" / "pyrogue" / "interfaces" / "_Virtual.py"
    )
    spec = importlib.util.spec_from_file_location("_virtual_for_load_race", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


vm = _load_virtual_module()


class _SlowClient:
    """Fake VirtualClient whose ``_remoteAttr`` blocks until released.

    Two threads call into ``__getattr__`` / ``.nodes`` simultaneously; only
    one thread should reach ``_remoteAttr('nodes')`` because the second
    thread is held off by the new ``_loadLock``. We assert that exactly one
    nodes-fetch happened.
    """

    def __init__(self):
        self._gate = threading.Event()
        self._calls = 0
        self._calls_lock = threading.Lock()

    def _remoteAttr(self, path, attr, *args, **kwargs):
        # Count concurrent entries before blocking; without the new lock
        # both racing threads land here together.
        with self._calls_lock:
            self._calls += 1
            entered = self._calls
        if entered == 1:
            # First entrant blocks so the second has time to race the
            # outer ``_loaded`` check before the dict is published.
            assert self._gate.wait(timeout=2.0)
        if attr == "nodes":
            return {}
        raise AssertionError(f"unexpected remote attr: {attr}")


def _make_node():
    """Build a VirtualNode wired to a slow client and an empty initial nodes dict."""
    attrs = {
        "name":        "TestNode",
        "description": "load-race test node",
        "expand":      True,
        "groups":      [],
        "guiGroup":    None,
        "path":        "Top.TestNode",
        "class":       "TestNode",
        "nodes":       {},
        "bases":       [],
    }
    node = vm.VirtualNode(attrs)
    node._client = _SlowClient()
    node._root   = None
    return node


def test_virtual_node_load_nodes_runs_once_under_concurrent_access():
    node = _make_node()
    client = node._client

    barrier = threading.Barrier(2)
    errors = []

    def worker():
        try:
            barrier.wait(timeout=2.0)
            # First call to ``nodes`` triggers _loadNodes via the DCL guard.
            _ = node.nodes
        except Exception as exc:  # pragma: no cover - shouldn't fire
            errors.append(exc)

    t1 = threading.Thread(target=worker)
    t2 = threading.Thread(target=worker)
    t1.start()
    t2.start()

    # Give the second thread a chance to land on the inner ``_loaded`` check
    # while the first is blocked inside ``_remoteAttr('nodes')``.
    threading.Event().wait(0.05)
    client._gate.set()

    t1.join(timeout=3.0)
    t2.join(timeout=3.0)

    assert not t1.is_alive() and not t2.is_alive(), "load-race workers deadlocked"
    assert errors == []
    # Exactly one ``_remoteAttr('nodes')`` reached the slow client; the
    # second concurrent caller serialized on the new ``_loadLock`` and saw
    # ``_loaded=True`` on retry.
    assert client._calls == 1
    assert node._loaded is True


def test_virtual_node_loaded_flag_set_after_nodes_dict_populated():
    """Pins the post-population ordering of ``_loaded = True``.

    If ``_loaded`` were set before ``self._nodes`` was filled, a thread that
    skipped the lock on the fast path would observe ``_loaded == True`` and
    walk an empty (or half-built) ``_nodes`` dict. We force this scenario
    deterministically by patching ``_remoteAttr`` to inspect ``_loaded`` at
    the moment the loop runs.
    """
    attrs = {
        "name":        "TestNode",
        "description": "load-flag ordering",
        "expand":      True,
        "groups":      [],
        "guiGroup":    None,
        "path":        "Top.TestNode",
        "class":       "TestNode",
        "nodes":       {},
        "bases":       [],
    }
    node = vm.VirtualNode(attrs)

    observed_during_fetch = []

    class _ObservingClient:
        def _remoteAttr(self, path, attr, *args, **kwargs):
            # The fix moves ``_loaded = True`` AFTER this call returns; if
            # the legacy ordering returns, we'd observe ``_loaded == True``
            # right here and the fast-path readers could see an empty dict.
            observed_during_fetch.append(node._loaded)
            return {}

    node._client = _ObservingClient()
    _ = node.nodes
    assert observed_during_fetch == [False]
    assert node._loaded is True
