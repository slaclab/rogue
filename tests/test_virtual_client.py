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

import pyrogue
import pyrogue.interfaces


def _test_port(index: int) -> int:
    """Return a stable high port for the current process."""
    return 20000 + ((os.getpid() % 1000) * 16) + (index * 4)


class VirtualTestRoot(pyrogue.Root):
    def __init__(self, *, name: str, port: int):
        super().__init__(name=name, pollEn=False)
        self.add(pyrogue.LocalVariable(name='Value', value=5, mode='RO'))
        self.zmqServer = pyrogue.interfaces.ZmqServer(root=self, addr='127.0.0.1', port=port)
        self.addInterface(self.zmqServer)


def test_virtual_client_reconnects_after_initial_failure():
    port = _test_port(0)
    cache_key = hash(('127.0.0.1', port))
    pyrogue.interfaces.VirtualClient.ClientCache.clear()

    first = pyrogue.interfaces.VirtualClient(addr='127.0.0.1', port=port)

    try:
        assert first.root is None
        assert cache_key not in pyrogue.interfaces.VirtualClient.ClientCache

        with VirtualTestRoot(name='ReconnectRoot', port=port):
            second = pyrogue.interfaces.VirtualClient(addr='127.0.0.1', port=port)

            try:
                assert second.root is not None
                assert second.root.name == 'ReconnectRoot'
                assert second.root.Value.value() == 5
            finally:
                second.stop()
    finally:
        first.stop()
        pyrogue.interfaces.VirtualClient.ClientCache.clear()


def test_virtual_client_supports_root_named_root():
    port = _test_port(1)
    pyrogue.interfaces.VirtualClient.ClientCache.clear()

    with VirtualTestRoot(name='root', port=port):
        client = pyrogue.interfaces.VirtualClient(addr='127.0.0.1', port=port)

        try:
            assert client.root is not None
            assert client.root.name == 'root'
            assert client.root.Value.value() == 5
        finally:
            client.stop()
            pyrogue.interfaces.VirtualClient.ClientCache.clear()


def test_virtual_client_stop_evicts_cache():
    port = _test_port(2)
    cache_key = hash(('127.0.0.1', port))
    pyrogue.interfaces.VirtualClient.ClientCache.clear()

    with VirtualTestRoot(name='StopRoot', port=port):
        first = pyrogue.interfaces.VirtualClient(addr='127.0.0.1', port=port)

        try:
            assert pyrogue.interfaces.VirtualClient.ClientCache[cache_key] is first
            first.stop()
            assert cache_key not in pyrogue.interfaces.VirtualClient.ClientCache

            second = pyrogue.interfaces.VirtualClient(addr='127.0.0.1', port=port)

            try:
                assert second is not first
                assert second.root is not None
                assert second.root.name == 'StopRoot'
                assert second.root.Value.value() == 5
            finally:
                second.stop()
        finally:
            first.stop()
            pyrogue.interfaces.VirtualClient.ClientCache.clear()
