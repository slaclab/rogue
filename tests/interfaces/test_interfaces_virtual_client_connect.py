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

import os
import time

import pyrogue
import pyrogue.interfaces


def _test_port(index: int) -> int:
    """Return a stable high port for the current process."""
    return 22000 + ((os.getpid() % 1000) * 16) + (index * 4)


def _clear_virtual_client_cache() -> None:
    """Stop any cached VirtualClient instances left by the test process."""
    for client in list(pyrogue.interfaces.VirtualClient.ClientCache.values()):
        try:
            client.stop()
            client._stop()
        except Exception:
            pass

    pyrogue.interfaces.VirtualClient.ClientCache.clear()


class SlowFirstRootServer(pyrogue.interfaces.ZmqServer):
    def __init__(self, *, root, addr: str, port: int, initial_root_delay: float = 0.0):
        super().__init__(root=root, addr=addr, port=port)
        self._initial_root_delay = initial_root_delay
        self._root_delay_done = False

    def _doOperation(self, d):
        if (not self._root_delay_done) and d.get('path') == '__ROOT__' and self._initial_root_delay > 0.0:
            self._root_delay_done = True
            time.sleep(self._initial_root_delay)

        return super()._doOperation(d)


class VirtualConnectRoot(pyrogue.Root):
    def __init__(self, *, name: str, port: int, initial_root_delay: float = 0.0):
        super().__init__(name=name, pollEn=False)
        self.add(pyrogue.LocalVariable(name='Value', value=5, mode='RO'))
        self.zmqServer = SlowFirstRootServer(
            root=self,
            addr='127.0.0.1',
            port=port,
            initial_root_delay=initial_root_delay,
        )
        self.addInterface(self.zmqServer)


def test_virtual_client_retries_initial_root_handshake(monkeypatch):
    port = _test_port(0)
    _clear_virtual_client_cache()
    monkeypatch.setenv('ROGUE_VIRTUAL_CONNECT_TIMEOUT', '5.0')

    try:
        with VirtualConnectRoot(name='ConnectRoot', port=port, initial_root_delay=1.5):
            client = pyrogue.interfaces.VirtualClient(addr='127.0.0.1', port=port)

            try:
                assert client.root is not None
                assert client.root.name == 'ConnectRoot'
                assert client.root.Value.value() == 5
            finally:
                client.stop()
                client._stop()
    finally:
        _clear_virtual_client_cache()


def test_virtual_client_bootstrap_handshake_completes_in_one_attempt(monkeypatch):
    """Bootstrap must not self-crash during the `notify` log on the first reply.

    The first successful `_requestDone(True)` happens inside `_waitForRoot`
    while `self._root` is still `None`. A stray `self._root.name` access in
    the notify path raises AttributeError, which `_waitForRoot` catches and
    retries — so the handshake silently takes two round trips instead of one.
    """
    port = _test_port(2)
    _clear_virtual_client_cache()
    monkeypatch.setenv('ROGUE_VIRTUAL_CONNECT_TIMEOUT', '5.0')

    VC = pyrogue.interfaces.VirtualClient
    original_remoteAttr = VC._remoteAttr
    root_handshake_attempts = []

    def counting_remoteAttr(self, path, attr, *args, **kwargs):
        if path == '__ROOT__':
            root_handshake_attempts.append(path)
        return original_remoteAttr(self, path, attr, *args, **kwargs)

    monkeypatch.setattr(VC, '_remoteAttr', counting_remoteAttr)

    try:
        with VirtualConnectRoot(name='BootstrapRoot', port=port):
            client = pyrogue.interfaces.VirtualClient(addr='127.0.0.1', port=port)

            try:
                assert client.root is not None
                assert len(root_handshake_attempts) == 1, (
                    f"Expected exactly 1 __ROOT__ handshake attempt, got "
                    f"{len(root_handshake_attempts)} — first _requestDone "
                    "raised AttributeError and was retried."
                )
            finally:
                client.stop()
                client._stop()
    finally:
        _clear_virtual_client_cache()


def test_virtual_client_reqlock_exists_before_zmq_base_init(monkeypatch):
    """Regression: SUB receive thread spawned by ZmqClient.__init__ must not race _reqLock.

    `rogue.interfaces.ZmqClient.__init__` creates the SUB receive thread
    synchronously. Any publish arriving during VirtualClient bootstrap
    fires `_doUpdate(data)` on that thread, which acquires `_reqLock`
    and reads `_root`/`_ltime`/`_varListeners`. If those attributes are
    assigned after the base constructor runs, `_doUpdate` raises
    AttributeError in a daemon thread. Pin the ordering invariant so
    future refactors can't regress it.
    """
    import pickle

    import rogue.interfaces

    port = _test_port(3)
    _clear_virtual_client_cache()
    monkeypatch.setenv('ROGUE_VIRTUAL_CONNECT_TIMEOUT', '5.0')

    original_zmq_init = rogue.interfaces.ZmqClient.__init__
    observed = {}

    def racing_init(self, *args, **kwargs):
        observed['reqLock']      = hasattr(self, '_reqLock')
        observed['root']         = hasattr(self, '_root')
        observed['ltime']        = hasattr(self, '_ltime')
        observed['varListeners'] = hasattr(self, '_varListeners')
        # Prove _doUpdate itself survives a publish at the point the SUB
        # thread would fire — should no-op because _root is still None.
        self._doUpdate(pickle.dumps({}))
        return original_zmq_init(self, *args, **kwargs)

    monkeypatch.setattr(rogue.interfaces.ZmqClient, '__init__', racing_init)

    try:
        with VirtualConnectRoot(name='RaceRoot', port=port):
            client = pyrogue.interfaces.VirtualClient(addr='127.0.0.1', port=port)

            try:
                assert observed == {
                    'reqLock':      True,
                    'root':         True,
                    'ltime':        True,
                    'varListeners': True,
                }, (
                    f"VirtualClient state not fully initialized before "
                    f"ZmqClient.__init__ spawns the SUB thread: {observed}"
                )
                assert client.root is not None
            finally:
                client.stop()
                client._stop()
    finally:
        _clear_virtual_client_cache()


def test_virtual_client_does_not_cache_failed_bootstrap(monkeypatch):
    port = _test_port(1)
    cache_key = hash(('127.0.0.1', port))
    _clear_virtual_client_cache()
    monkeypatch.setenv('ROGUE_VIRTUAL_CONNECT_TIMEOUT', '1.0')

    try:
        failed = pyrogue.interfaces.VirtualClient(addr='127.0.0.1', port=port)

        assert failed.root is None
        assert cache_key not in pyrogue.interfaces.VirtualClient.ClientCache

        with VirtualConnectRoot(name='RecoveredRoot', port=port):
            recovered = pyrogue.interfaces.VirtualClient(addr='127.0.0.1', port=port)

            try:
                assert recovered.root is not None
                assert recovered.root.name == 'RecoveredRoot'
                assert recovered.root.Value.value() == 5
            finally:
                recovered.stop()
                recovered._stop()
    finally:
        _clear_virtual_client_cache()
