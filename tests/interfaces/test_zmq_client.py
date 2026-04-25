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
import sys
import threading
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


def test_virtual_client_concurrent_threadsafety(free_zmq_port):
    """Reproduce ESROGUE-740: concurrent threads on a cached VirtualClient
    share a single ZMQ_REQ socket and violate its alternating send/recv
    state machine.

    On unpatched main this test is EXPECTED to fail (crash, timeout, or
    ZMQ protocol error) within ~30 s. Phase 2 adds a std::mutex in C++
    ZmqClient to serialize the REQ cycle; the same test must then pass.
    """
    N_COMMANDS = 500
    WATCHDOG_SECONDS = 25.0
    JOIN_TIMEOUT = 2.0

    # Clear the process-wide cache so we observe a fresh cache miss + hit.
    pyrogue.interfaces.VirtualClient.ClientCache.clear()

    # Root name must NOT collide with the read-only VirtualClient.root @property
    # (python/pyrogue/interfaces/_Virtual.py:698); _Virtual.py:477 does
    # `setattr(self, self._root.name, self._root)`, so naming the Root 'root'
    # raises AttributeError at VirtualClient construction, before the race can run.
    root = pr.Root(name='Root', pollEn=False, timeout=2.0)
    root.add(ZmqTestDevice(name='Dev'))
    zmqSrv = pyrogue.interfaces.ZmqServer(
        root=root, addr="127.0.0.1", port=free_zmq_port)
    root.start()
    try:
        zmqSrv._start()
        time.sleep(0.5)
        port = zmqSrv.port()

        # Two VirtualClients with the same (addr, port) MUST be the same
        # Python object via ClientCache -- that is what forces them to
        # share a single underlying ZMQ_REQ socket, which is the whole
        # point of the reproduction.
        client1 = pyrogue.interfaces.VirtualClient(addr="127.0.0.1", port=port)
        client2 = pyrogue.interfaces.VirtualClient(addr="127.0.0.1", port=port)
        assert client1 is client2, "VirtualClient cache miss: test would not reproduce ESROGUE-740"

        stop_event = threading.Event()
        errors = []
        timeout_flag = {"fired": False}

        def _poll_loop():
            try:
                while not stop_event.is_set():
                    _ = client1.Root.Dev.TestVar.get()
            except BaseException as exc:  # noqa: BLE001 - must capture any race-induced error
                errors.append(exc)

        def _watchdog():
            # Fires iff the test process is still alive after WATCHDOG_SECONDS.
            # On unpatched HEAD the corrupted ZMQ_REQ socket can deadlock
            # teardown (srv._stop/root.stop), so setting stop_event alone
            # is insufficient to satisfy REPRO-03 (< 30s).  Hard-exit is
            # the only mechanism that bypasses a C++/GIL deadlock; a
            # non-zero exit preserves the Phase 1 FAIL-on-unpatched signal.
            timeout_flag["fired"] = True
            stop_event.set()
            sys.stderr.write(
                "ESROGUE-740 watchdog fired at %.1fs: hard-exiting to "
                "escape teardown deadlock\n" % WATCHDOG_SECONDS
            )
            sys.stderr.flush()
            os._exit(77)

        poll_thread = threading.Thread(
            target=_poll_loop,
            name="esrogue740-poller",
            daemon=True,
        )
        watchdog = threading.Timer(WATCHDOG_SECONDS, _watchdog)
        # Daemonize so a stray watchdog cannot keep the test process alive
        # if cleanup is bypassed (e.g. exception between start() and the
        # inner finally), avoiding a spurious os._exit(77) during teardown.
        watchdog.daemon = True

        poll_thread.start()
        watchdog.start()
        try:
            for _ in range(N_COMMANDS):
                client2.Root.Dev.TestCmd()
        finally:
            stop_event.set()
            watchdog.cancel()
            poll_thread.join(timeout=JOIN_TIMEOUT)

        # REPRO-03 invariants: the polling thread MUST have exited, and
        # the watchdog MUST NOT have fired (otherwise we blew the 30 s budget).
        assert not poll_thread.is_alive(), "polling thread did not join within %.1fs" % JOIN_TIMEOUT
        assert not timeout_flag["fired"], "watchdog fired: test exceeded %.1fs budget" % WATCHDOG_SECONDS

        # Re-raise any error captured in the polling thread so a poller-only
        # crash still fails the pytest run (D-12).
        if errors:
            raise AssertionError(
                "concurrent RPC race: polling thread raised %d error(s); first: %r"
                % (len(errors), errors[0])
            ) from errors[0]
    finally:
        # Belt-and-braces: even on an exception path, make sure the
        # polling thread, server, root, and cache are all cleaned up.
        try:
            stop_event.set()
        except NameError:
            pass
        try:
            watchdog.cancel()
        except NameError:
            pass
        try:
            poll_thread.join(timeout=JOIN_TIMEOUT)
        except NameError:
            pass
        # VirtualClient._monWorker is a non-daemon thread (_Virtual.py:485).
        # Without client.stop() it will keep the Python process alive after
        # pytest returns, causing an apparent hang.  stop() sets
        # _monEnable=False so the monitor exits on its next 1-second tick.
        try:
            client1.stop()
            if getattr(client1, "_monThread", None) is not None:
                client1._monThread.join(timeout=JOIN_TIMEOUT)
        except NameError:
            pass
        zmqSrv._stop()
        root.stop()
        pyrogue.interfaces.VirtualClient.ClientCache.clear()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
