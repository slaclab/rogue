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

# NOTE: The C++ ZmqClient blocks on the GIL when used in the same
# process as the Python ZmqServer, causing a deadlock under pytest's
# single-threaded runner. These tests validate the client API when run
# as a standalone script but are skipped in CI. The Python-side ZMQ
# server is already covered by test_interfaces_zmq_server.py.

import os
import time

import pyrogue as pr
import pyrogue.interfaces
import rogue
import rogue.interfaces
import pytest

pytestmark = [pytest.mark.integration, pytest.mark.skipif(
    not os.environ.get("RUN_ZMQ_CLIENT_TESTS"),
    reason="ZmqClient deadlocks with in-process ZmqServer under pytest GIL; "
           "set RUN_ZMQ_CLIENT_TESTS=1 to run")]


class ZmqTestDevice(pr.Device):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.add(pr.LocalVariable(
            name='TestVar',
            value=42,
            mode='RW',
        ))

        self._cmdCalled = False
        self.add(pr.LocalCommand(
            name='TestCmd',
            function=self._runCmd,
        ))

    def _runCmd(self):
        self._cmdCalled = True


def _setup():
    """Create a root with ZmqServer ready for ZmqClient testing."""
    root = pr.Root(name='root', pollEn=False, timeout=2.0)
    root.add(ZmqTestDevice(name='Dev'))
    zmqSrv = pyrogue.interfaces.ZmqServer(
        root=root, addr="127.0.0.1", port=0)
    root.start()
    try:
        zmqSrv._start()
        time.sleep(0.5)
        port = zmqSrv.port()
        client = rogue.interfaces.ZmqClient("127.0.0.1", port, True)
        client.setTimeout(2000, False)
    except Exception:
        zmqSrv._stop()
        root.stop()
        raise
    return root, zmqSrv, client


def test_zmq_client_string_get():
    root, zmqSrv, client = _setup()
    try:
        val = client.getDisp('root.Dev.TestVar')
        assert val == '42'
    finally:
        zmqSrv._stop()
        root.stop()


def test_zmq_client_string_set():
    root, zmqSrv, client = _setup()
    try:
        client.setDisp('root.Dev.TestVar', '99')
        val = client.getDisp('root.Dev.TestVar')
        assert val == '99'
    finally:
        zmqSrv._stop()
        root.stop()


def test_zmq_client_exec():
    root, zmqSrv, client = _setup()
    try:
        client.exec('root.Dev.TestCmd', '')
        time.sleep(0.1)
        assert root.Dev._cmdCalled is True
    finally:
        zmqSrv._stop()
        root.stop()


def test_zmq_client_value_disp():
    root, zmqSrv, client = _setup()
    try:
        val = client.valueDisp('root.Dev.TestVar')
        assert '42' in val
    finally:
        zmqSrv._stop()
        root.stop()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
