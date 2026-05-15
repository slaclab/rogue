#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
"""Thread-safety tests for ZmqServer._updateList dictionary.

_varUpdate() and _varDone() access _updateList without synchronization
prior to the ESROGUE-711 fix. If user code or multiple Root instances
invoke these callbacks from different threads, concurrent access can
corrupt the dictionary or raise "dictionary changed size during
iteration" during pickle.dumps.
"""
import threading
import time

import pyrogue as pr
import pyrogue.interfaces


class _SlowPickleValue:
    """Value whose pickle blocks in __reduce__, releasing the GIL.

    Reproduces the matplotlib-transforms scenario from the original JIRA
    report (ESROGUE-711): a value whose serialization is slow enough that
    a concurrent _varUpdate() can mutate _updateList mid-pickle and raise
    "RuntimeError: dictionary changed size during iteration".
    """
    delay_s = 0.2

    def __reduce__(self):
        time.sleep(self.delay_s)
        return (self.__class__, ())


class ZmqTestRoot(pr.Root):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        dev = pr.Device(name='Dev')
        for i in range(10):
            dev.add(pr.LocalVariable(name=f'Var{i}', value=0, mode='RW'))
        self.add(dev)


def test_zmq_server_update_list_concurrent_access():
    """Rapid variable updates should not corrupt _updateList."""
    errors = []

    with ZmqTestRoot() as root:
        zmq_server = pyrogue.interfaces.ZmqServer(root=root, addr='127.0.0.1', port=0)  # noqa: F841

        stop = threading.Event()

        def rapid_updates():
            """Set variables rapidly from multiple threads."""
            try:
                j = 0
                while not stop.is_set():
                    for i in range(10):
                        getattr(root.Dev, f'Var{i}').set(j, write=False)
                    j += 1
                    if j % 50 == 0:
                        time.sleep(0.001)
            except Exception as e:
                if not stop.is_set():
                    errors.append(e)

        threads = []
        for _ in range(3):
            t = threading.Thread(target=rapid_updates, daemon=True)
            threads.append(t)
            t.start()

        time.sleep(3)
        stop.set()
        for t in threads:
            t.join(timeout=5)
        for t in threads:
            assert not t.is_alive(), "rapid_updates thread hung"

    assert not errors, f"Errors: {errors}"


def test_zmq_server_update_list_direct_race():
    """Directly call _varUpdate/_varDone from multiple threads to race _updateList."""
    errors = []

    with ZmqTestRoot() as root:
        zmq_server = pyrogue.interfaces.ZmqServer(root=root, addr='127.0.0.1', port=0)

        stop = threading.Event()

        def update_caller(thread_id):
            """Directly invoke _varUpdate and _varDone in tight loop."""
            try:
                for i in range(2000):
                    if stop.is_set():
                        break
                    zmq_server._varUpdate(f'Root.Dev.Var{thread_id}', i)
                    if i % 5 == 0:
                        zmq_server._varDone()
            except Exception as e:
                if not stop.is_set():
                    errors.append(e)

        threads = []
        for tid in range(4):
            t = threading.Thread(target=update_caller, args=(tid % 10,), daemon=True)
            threads.append(t)
            t.start()

        for t in threads:
            t.join(timeout=30)
        stop.set()
        for t in threads:
            assert not t.is_alive(), "update_caller thread hung"

    assert not errors, f"Errors: {errors}"


def test_zmq_server_varDone_race_with_slow_pickle():
    """Deterministic ESROGUE-711 reproducer.

    Seed _updateList with a slow-pickling value and have a second thread
    call _varUpdate() while _varDone() is mid-pickle. Without the
    snapshot-and-swap fix this raises:
        RuntimeError: dictionary changed size during iteration
    """
    errors = []

    with ZmqTestRoot() as root:
        zmq_server = pyrogue.interfaces.ZmqServer(root=root, addr='127.0.0.1', port=0)

        # Seed extra entries so pickle iteration has time to start before
        # hitting the slow value.
        for i in range(10):
            zmq_server._updateList[f'Root.Pre{i}'] = i
        zmq_server._updateList['Root.Slow'] = _SlowPickleValue()

        mutator_started = threading.Event()

        def mutator():
            mutator_started.wait(timeout=2)
            try:
                # Insert during _varDone's pickle iteration. The slow value
                # holds pickle for ~0.2 s with the GIL released, giving this
                # thread ample time to mutate _updateList.
                for i in range(50):
                    zmq_server._varUpdate(f'Root.Late{i}', i)
                    time.sleep(0.001)
            except Exception as e:
                errors.append(('mutator', e))

        t = threading.Thread(target=mutator, daemon=True)
        t.start()

        mutator_started.set()
        try:
            zmq_server._varDone()
        except Exception as e:
            errors.append(('main', e))

        t.join(timeout=10)
        assert not t.is_alive(), "mutator thread hung"

    runtime_errors = [e for tag, e in errors if isinstance(e, RuntimeError)]
    assert not runtime_errors, (
        f"ESROGUE-711 race triggered: {runtime_errors}. "
        f"_varDone must snapshot _updateList under a lock before serializing."
    )
    assert not errors, f"Unexpected errors: {errors}"
