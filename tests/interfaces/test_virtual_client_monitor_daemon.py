#!/usr/bin/env python3
#-----------------------------------------------------------------------------
# Title      : VirtualClient monitor-thread lifecycle regression tests
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
# Regression coverage for issue #1238:
# "ZMQ client monitor thread is not exiting in interactive environment".
#
# ``VirtualClient.__init__`` spawned ``self._monThread`` via plain
# ``threading.Thread(target=self._monWorker)`` -- without ``daemon=True``.
# Because ``VirtualClient.ClientCache`` (a class-level dict) holds a strong
# reference to every constructed instance, dropping the user-side reference
# does not let the instance get garbage-collected. The non-daemon monitor
# thread therefore keeps the interpreter alive on ``quit()`` / ``exit()``
# in interactive sessions (the symptom reported by ``pysmurf``).
#
# Two contracts are pinned here:
#
# 1. ``_monThread.daemon is True`` so interpreter shutdown does not hang
#    even when ``ClientCache`` still pins the instance. Reverting the
#    ``daemon=True`` argument in ``_Virtual.py`` makes
#    ``test_virtual_client_monitor_thread_is_daemon`` fail.
#
# 2. ``stopMonitor()`` disables the link-heartbeat polling thread without
#    releasing the underlying ZMQ resources. The pre-issue-#1238 API only
#    offered ``stop()``, which also closes the C++ ``ZmqClient`` sockets;
#    this left ``pysmurf``-style callers (who want to silence the monitor
#    while keeping the connection open) without a clean option. Removing
#    ``stopMonitor()`` -- or making it tear down the ZMQ transport --
#    makes ``test_stop_monitor_keeps_zmq_open`` fail.

import threading

import pytest

import pyrogue
import pyrogue.interfaces


pytestmark = pytest.mark.integration


def _clear_virtual_client_cache() -> None:
    """Drain ``VirtualClient.ClientCache`` between tests.

    The cache is a class-level dict pinned for the life of the process, so
    test isolation depends on emptying it after each lifecycle test.
    """
    for client in list(pyrogue.interfaces.VirtualClient.ClientCache.values()):
        try:
            client.stop()
            client._stop()
        except Exception:
            pass
    pyrogue.interfaces.VirtualClient.ClientCache.clear()


class _MonitorRoot(pyrogue.Root):
    """Minimal Root + ZmqServer used to bring up a VirtualClient in tests."""

    def __init__(self, *, name: str, port: int):
        super().__init__(name=name, pollEn=False)
        self.add(pyrogue.LocalVariable(name='Value', value=0, mode='RW'))
        self.zmqServer = pyrogue.interfaces.ZmqServer(root=self, addr='127.0.0.1', port=port)
        self.addInterface(self.zmqServer)


def test_virtual_client_monitor_thread_is_daemon(free_zmq_port):
    """``VirtualClient._monThread`` must be a daemon thread.

    Pins the daemon flag so interpreter shutdown (``quit()`` in ipython,
    process exit in a host script) does not hang when ``ClientCache`` is
    still holding the only strong reference to the client.

    Reverting the ``daemon=True`` argument in ``_Virtual.py`` makes this
    assertion fail.
    """
    port = free_zmq_port
    _clear_virtual_client_cache()

    with _MonitorRoot(name='DaemonRoot', port=port):
        client = pyrogue.interfaces.VirtualClient(addr='127.0.0.1', port=port)
        try:
            assert client._monThread is not None, (
                "VirtualClient.__init__ must spawn the link-monitor thread."
            )
            assert isinstance(client._monThread, threading.Thread)
            assert client._monThread.daemon is True, (
                "VirtualClient._monThread must be a daemon thread so the "
                "interpreter can exit cleanly when ClientCache pins the "
                "instance (issue #1238)."
            )
        finally:
            client.stop()

    _clear_virtual_client_cache()


def test_stop_monitor_keeps_zmq_open(free_zmq_port):
    """``stopMonitor()`` disables heartbeat polling but leaves ZMQ open.

    The pre-fix API only offered ``stop()``, which also closes the C++
    ``ZmqClient`` sockets. Callers that want to silence the monitor
    thread but keep using the connection -- as ``pysmurf`` does -- need
    a separate, narrower entry point.

    Pins:
      * ``stopMonitor()`` drains the Python monitor thread.
      * ``_vcInitialized`` stays ``True`` so ``_remoteAttr`` keeps working.
      * The instance remains in ``ClientCache`` (no implicit teardown).
      * A real ZMQ round-trip (``Value.set``/``Value.get``) still
        succeeds after ``stopMonitor()``.

    Reverting ``stopMonitor()`` -- or making it call
    ``rogue.interfaces.ZmqClient._stop`` -- makes this test fail.
    """
    port = free_zmq_port
    _clear_virtual_client_cache()
    cache_key = hash(('127.0.0.1', port))

    with _MonitorRoot(name='MonOnlyRoot', port=port) as root:
        client = pyrogue.interfaces.VirtualClient(addr='127.0.0.1', port=port)
        try:
            mon_thread = client._monThread
            assert mon_thread is not None and mon_thread.is_alive(), (
                "VirtualClient must start the link-monitor thread before "
                "stopMonitor() can be exercised."
            )

            client.stopMonitor()

            # Thread reference may be cleared by stopMonitor; either way it
            # must no longer be alive.
            assert (client._monThread is None
                    or not client._monThread.is_alive()), (
                "stopMonitor() must drain the Python monitor thread."
            )
            assert not mon_thread.is_alive(), (
                "Captured monitor-thread handle must report not-alive after "
                "stopMonitor()."
            )

            # The ZMQ transport must still be functional -- this is the
            # whole point of having a separate stopMonitor() entry point.
            assert client._vcInitialized is True, (
                "stopMonitor() must NOT clear _vcInitialized; the client "
                "is still usable for remote attribute calls."
            )
            assert cache_key in pyrogue.interfaces.VirtualClient.ClientCache, (
                "stopMonitor() must NOT remove the client from ClientCache."
            )

            # Real ZMQ round-trip after stopMonitor() to prove the transport
            # is still alive.
            client.root.Value.set(42)
            assert root.Value.get() == 42, (
                "Server-side write via VirtualClient must succeed after "
                "stopMonitor(); the ZMQ transport must remain open."
            )
            assert client.root.Value.get() == 42, (
                "Server-side read via VirtualClient must succeed after "
                "stopMonitor(); the ZMQ transport must remain open."
            )

            # stopMonitor() is idempotent.
            client.stopMonitor()
        finally:
            client.stop()

    _clear_virtual_client_cache()


def test_stop_monitor_then_stop_is_safe(free_zmq_port):
    """``stop()`` after ``stopMonitor()`` still releases ZMQ resources.

    Pins that calling the two methods in sequence does not leave the
    instance pinned in ``ClientCache`` or double-join the (already-joined)
    monitor thread. This protects callers that opportunistically call
    ``stopMonitor()`` early and ``stop()`` later on the same instance.
    """
    port = free_zmq_port
    _clear_virtual_client_cache()
    cache_key = hash(('127.0.0.1', port))

    with _MonitorRoot(name='SeqRoot', port=port):
        client = pyrogue.interfaces.VirtualClient(addr='127.0.0.1', port=port)
        try:
            client.stopMonitor()
        finally:
            client.stop()

        assert client._vcInitialized is False, (
            "stop() must clear _vcInitialized after a prior stopMonitor()."
        )
        assert cache_key not in pyrogue.interfaces.VirtualClient.ClientCache, (
            "stop() must remove the instance from ClientCache even when "
            "stopMonitor() has already drained the monitor thread."
        )

    _clear_virtual_client_cache()
