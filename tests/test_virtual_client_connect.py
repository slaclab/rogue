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
import pytest


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
