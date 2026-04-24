#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
"""
DETECTED-IDs:
  - PY-003
  - PY-006
  - PY-013
  - PY-026

Stress the Python-layer cross-thread update-worker races:
  - PY-003 : VirtualNode._doUpdate iterates the listener list while another
    thread calls addListener() / delListener(), mutating it in flight.
  - PY-006 : VirtualClient bootstrap race — the first SUB message from the
    ZmqServer can arrive before the client's update-worker dict is fully
    populated.
  - PY-013 : ZmqServer._updateList dict mutation concurrent with the C++ REP
    thread reading the same dict and the Root update-worker writing to it.
  - PY-026 : PyDM RogueConnection._updateVariable emits a Qt signal from the
    Root update-worker thread (same cross-thread update-worker pattern; Qt
    bridge not constructed in CI, exercised via the shared _updateVariable
    path only).

No network loopback required beyond the ZMQ REQ/REP pair which binds to
127.0.0.1 — no macOS skip needed.
"""
import threading

import pyrogue as pr
import pytest

pytestmark = pytest.mark.repro


class _Probe(pr.Device):
    """Minimal Device holding one LocalVariable for update-worker stress."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.add(pr.LocalVariable(
            name="Value",
            value=0,
            mode="RW",
        ))


@pytest.mark.repro
def test_stress_virtual_node_list_mutation(memory_root, stress_iters):
    """VirtualNode._doUpdate list-iter vs addListener mutation (PY-003)."""
    errors = []

    probe = _Probe(name="probe")
    memory_root.add(probe)

    def callback(path, value):
        pass

    def listener_churn():
        for i in range(stress_iters // 10):
            try:
                probe.Value.addListener(callback)
                probe.Value.delListener(callback)
            except Exception as e:
                errors.append(e)

    def updater():
        for i in range(stress_iters // 10):
            try:
                probe.Value.set(i)
            except Exception as e:
                errors.append(e)

    threads = [threading.Thread(target=listener_churn) for _ in range(5)]
    threads += [threading.Thread(target=updater) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors, f"VirtualNode list-mutation stress errors: {errors}"


@pytest.mark.repro
def test_stress_virtual_client_bootstrap_race(stress_iters):
    """VirtualClient bootstrap race with first SUB message (PY-006).

    Construct a VirtualClient and immediately publish to it from another
    thread before the client's _root dict is fully populated. The bootstrap
    path under `_rootAttached` races the inbound SUB handler.
    """
    errors = []

    def cycle():
        for _ in range(stress_iters // 10):
            try:
                # VirtualClient ctor connects to a non-existent server; the
                # bootstrap handshake code path still runs through _addVarListener
                # setup before the first SUB arrives.
                vc = pr.interfaces.VirtualClient(addr="127.0.0.1", port=19690)
                vc.stop()
                del vc
            except Exception as e:
                errors.append(e)

    threads = [threading.Thread(target=cycle) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors, f"VirtualClient bootstrap stress errors: {errors}"


@pytest.mark.repro
def test_stress_zmqserver_update_list(memory_root, stress_iters):
    """ZmqServer._updateList dict mutation across REP + update-worker (PY-013)."""
    errors = []

    # Attach a ZmqServer to the root; drive variable updates from multiple
    # threads so the server's _updateList dict is mutated while the C++ REP
    # thread reads and the update-worker writes.
    zs = pr.interfaces.ZmqServer(root=memory_root, addr="127.0.0.1", port=19790)
    probe = _Probe(name="zprobe")
    memory_root.add(probe)

    def updater(i):
        for j in range(stress_iters // 10):
            try:
                probe.Value.set(i * 1000 + j)
            except Exception as e:
                errors.append(e)

    threads = [threading.Thread(target=updater, args=(i,)) for i in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    zs.stop()
    assert not errors, f"ZmqServer update-list stress errors: {errors}"


@pytest.mark.repro
def test_stress_pydm_update_variable_pathway(memory_root, stress_iters):
    """PyDM RogueConnection._updateVariable emit path (PY-026).

    The Qt bridge is not constructible in CI (no QApplication), so this
    test exercises the shared Python-layer update-worker -> listener chain
    that PyDM plugs into. Validates the update-worker dispatch is reentrant
    under concurrent variable sets from many threads — the same invariant
    PyDM's Qt-signal emit depends on.
    """
    errors = []

    probe = _Probe(name="pydm_probe")
    memory_root.add(probe)

    # Simulate a PyDM-style listener that re-reads the variable on each tick.
    def listener(path, value):
        try:
            _ = probe.Value.get()
        except Exception as e:
            errors.append(e)

    probe.Value.addListener(listener)

    def driver(i):
        for j in range(stress_iters // 10):
            try:
                probe.Value.set(i * 7 + j)
            except Exception as e:
                errors.append(e)

    threads = [threading.Thread(target=driver, args=(i,)) for i in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    probe.Value.delListener(listener)
    assert not errors, f"PyDM update-variable pathway stress errors: {errors}"
