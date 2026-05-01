#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
"""Thread-safety tests for VirtualClient._monitors and _varListeners lists.

These lists are modified by addLinkMonitor/remLinkMonitor and _addVarListener
from user threads while the monitor thread and ZMQ SUB thread iterate them.
"""
import threading
import time

import pyrogue as pr
import pyrogue.interfaces


class VcTestRoot(pr.Root):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.add(pr.LocalVariable(name='TestVar', value=0, mode='RW'))


def test_virtual_client_monitors_concurrent_modification():
    """addLinkMonitor/remLinkMonitor racing with monitor thread iteration."""
    errors = []
    with VcTestRoot() as root:
        zmq_server = pyrogue.interfaces.ZmqServer(root=root, addr='127.0.0.1', port=0)
        zmq_server._start()

        port = zmq_server.port()
        client = pyrogue.interfaces.VirtualClient('127.0.0.1', port)
        stop = threading.Event()

        def churn_monitors():
            """Add/remove monitors rapidly."""
            try:
                callbacks = []
                for i in range(200):
                    if stop.is_set():
                        break
                    def _noop_mon(state):
                        pass
                    fn = _noop_mon
                    client.addLinkMonitor(fn)
                    callbacks.append(fn)
                    if len(callbacks) > 3:
                        old = callbacks.pop(0)
                        client.remLinkMonitor(old)
                    time.sleep(0.005)
                for fn in callbacks:
                    try:
                        client.remLinkMonitor(fn)
                    except Exception:
                        pass
            except Exception as e:
                if not stop.is_set():
                    errors.append(('churn', e))

        t = threading.Thread(target=churn_monitors, daemon=True)
        t.start()

        time.sleep(3)
        stop.set()
        t.join(timeout=5)
        assert not t.is_alive(), "churn_monitors thread hung"
        client.stop()
        zmq_server._stop()
    assert not errors, f"Errors: {errors}"


def test_virtual_client_var_listeners_concurrent_modification():
    """_addVarListener racing with _doUpdate from SUB thread."""
    errors = []
    with VcTestRoot() as root:
        zmq_server = pyrogue.interfaces.ZmqServer(root=root, addr='127.0.0.1', port=0)
        zmq_server._start()

        port = zmq_server.port()
        client = pyrogue.interfaces.VirtualClient('127.0.0.1', port)
        stop = threading.Event()

        def update_loop():
            """Trigger variable updates on the server side."""
            i = 0
            try:
                while not stop.is_set():
                    root.TestVar.set(i, write=False)
                    i += 1
                    time.sleep(0.01)
            except Exception as e:
                if not stop.is_set():
                    errors.append(('update', e))

        def add_listeners():
            """Add var listeners while updates are flowing."""
            try:
                for i in range(100):
                    if stop.is_set():
                        break
                    def _noop_var(path, val):
                        pass
                    fn = _noop_var
                    client._addVarListener(fn)
                    time.sleep(0.01)
            except Exception as e:
                if not stop.is_set():
                    errors.append(('listener', e))

        t1 = threading.Thread(target=update_loop, daemon=True)
        t2 = threading.Thread(target=add_listeners, daemon=True)
        t1.start()
        t2.start()

        time.sleep(3)
        stop.set()
        t1.join(timeout=5)
        t2.join(timeout=5)
        assert not t1.is_alive(), "update_loop thread hung"
        assert not t2.is_alive(), "add_listeners thread hung"
        client.stop()
        zmq_server._stop()

    assert not errors, f"Errors: {errors}"
