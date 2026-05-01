#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
"""Thread-safety tests for BaseVariable listener list concurrent modification.

BaseVariable.__functions and _listeners are modified by addListener/delListener
from user threads while _doUpdate() iterates them from the update worker thread.
This can silently cause missed or duplicated callbacks during iteration.
"""
import threading
import time

import pyrogue as pr


class DummyDev(pr.Device):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.add(pr.LocalVariable(
            name='TestVar',
            value=0,
            mode='RW',
        ))


class DummyRoot(pr.Root):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.add(DummyDev(name='Dev'))


def test_variable_add_listener_during_updates():
    """Adding listeners while updates are in flight should not raise RuntimeError."""
    errors = []

    with DummyRoot() as root:
        var = root.Dev.TestVar
        stop = threading.Event()

        def update_loop():
            """Continuously set variable to trigger _doUpdate."""
            i = 0
            try:
                while not stop.is_set():
                    var.set(i, write=False)
                    i += 1
                    if i % 100 == 0:
                        time.sleep(0.001)
            except Exception as e:
                if not stop.is_set():
                    errors.append(('update', e))

        def listener_churn():
            """Continuously add/remove listeners."""
            try:
                listeners = []
                for i in range(200):
                    if stop.is_set():
                        break
                    def _noop(path, val):
                        pass
                    fn = _noop
                    var.addListener(fn)
                    listeners.append(fn)
                    if len(listeners) > 5:
                        old = listeners.pop(0)
                        var.delListener(old)
                    time.sleep(0.001)
                # Cleanup
                for fn in listeners:
                    try:
                        var.delListener(fn)
                    except Exception:
                        pass
            except Exception as e:
                if not stop.is_set():
                    errors.append(('listener', e))

        t1 = threading.Thread(target=update_loop, daemon=True)
        t2 = threading.Thread(target=listener_churn, daemon=True)
        t1.start()
        t2.start()

        time.sleep(3)
        stop.set()
        t1.join(timeout=5)
        t2.join(timeout=5)
        assert not t1.is_alive(), "update_loop thread hung"
        assert not t2.is_alive(), "listener_churn thread hung"

    assert not errors, f"Errors during test: {errors}"


def test_variable_listener_chain_concurrent_modification():
    """Modifying listener chains while _recurseAddListeners iterates should not crash."""
    errors = []

    class ChainDev(pr.Device):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.add(pr.LocalVariable(name='TestVar', value=0, mode='RW'))
            for i in range(5):
                self.add(pr.LocalVariable(name=f'Chain{i}', value=0, mode='RW'))
            self.add(pr.LocalVariable(name='ExtraChain', value=0, mode='RW'))

    class ChainRoot(pr.Root):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.add(ChainDev(name='Dev'))

    with ChainRoot() as root:
        var = root.Dev.TestVar
        stop = threading.Event()

        chain_vars = [getattr(root.Dev, f'Chain{i}') for i in range(5)]

        # Wire up a chain
        var.addListener(chain_vars[0])
        for i in range(len(chain_vars) - 1):
            chain_vars[i].addListener(chain_vars[i + 1])

        extra = root.Dev.ExtraChain

        def update_loop():
            i = 0
            try:
                while not stop.is_set():
                    var.set(i, write=False)
                    i += 1
                    if i % 100 == 0:
                        time.sleep(0.001)
            except Exception as e:
                if not stop.is_set():
                    errors.append(('update', e))

        def modify_chain():
            """Add/remove chain links while updates propagate."""
            try:
                for i in range(100):
                    if stop.is_set():
                        break
                    # Add to middle of chain
                    chain_vars[2].addListener(extra)
                    time.sleep(0.005)
                    # Remove from chain
                    chain_vars[2].delListener(extra)
                    time.sleep(0.005)
            except Exception as e:
                if not stop.is_set():
                    errors.append(('chain', e))

        t1 = threading.Thread(target=update_loop, daemon=True)
        t2 = threading.Thread(target=modify_chain, daemon=True)
        t1.start()
        t2.start()

        time.sleep(3)
        stop.set()
        t1.join(timeout=5)
        t2.join(timeout=5)
        assert not t1.is_alive(), "update_loop thread hung"
        assert not t2.is_alive(), "modify_chain thread hung"

    assert not errors, f"Errors during test: {errors}"
