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
#
# Pins the contract that ``VirtualClient.stop()`` releases the underlying
# C++ ``ZmqClient`` subscriber thread, REQ/SUB sockets, and ZMQ context.
#
# Before this fix, ``stop()`` only joined the Python ``_monThread`` and
# left the C++ side running until Python garbage collection ran
# ``~ZmqClient``. ``VirtualClient.ClientCache`` (a class-level dict)
# pins each instance with a strong reference, so GC may never run --
# long-lived processes accumulated one stranded native SUB thread per
# cached client.
#
# The matching ``_cleanupFailedInit`` already calls
# ``rogue.interfaces.ZmqClient._stop(self)`` for the failed-bootstrap
# path; this test pins that the success path now does the same. Reverting
# the new ``_stop`` call from ``stop()`` makes the post-stop native-thread
# count assertion fail.

import gc
import os
import time

import pytest

import pyrogue
import pyrogue.interfaces

pytestmark = pytest.mark.integration


def _native_thread_count() -> int | None:
    """Return ``Threads:`` from /proc/self/status, or None on non-Linux.

    Counts native (kernel) threads, including std::thread workers spawned
    by the C++ side that are invisible to ``threading.enumerate()``.
    """
    try:
        with open('/proc/self/status') as f:
            for line in f:
                if line.startswith('Threads:'):
                    return int(line.split()[1])
    except FileNotFoundError:
        return None
    return None


def _test_port(index: int) -> int:
    return 23000 + ((os.getpid() % 1000) * 16) + (index * 4)


def _clear_virtual_client_cache() -> None:
    for client in list(pyrogue.interfaces.VirtualClient.ClientCache.values()):
        try:
            client.stop()
            client._stop()
        except Exception:
            pass
    pyrogue.interfaces.VirtualClient.ClientCache.clear()


class _StopRoot(pyrogue.Root):
    def __init__(self, *, name: str, port: int):
        super().__init__(name=name, pollEn=False)
        self.add(pyrogue.LocalVariable(name='Value', value=0, mode='RO'))
        self.zmqServer = pyrogue.interfaces.ZmqServer(root=self, addr='127.0.0.1', port=port)
        self.addInterface(self.zmqServer)


def test_virtual_client_stop_releases_native_threads():
    """``VirtualClient.stop()`` must release the C++ subscriber thread.

    Drops the native-thread count back to (or below) the post-bootstrap
    baseline after stop(). The pre-fix behavior left the C++ SUB worker
    thread running for the lifetime of the process, which this assertion
    catches without an external leak detector.

    Skipped on non-Linux: ``/proc/self/status`` is the only portable way
    to count native threads from Python without pulling in psutil.
    """
    if _native_thread_count() is None:
        pytest.skip("/proc/self/status not available on this platform")

    port = _test_port(0)
    _clear_virtual_client_cache()

    with _StopRoot(name='StopRoot', port=port):
        # Baseline reading after the server is up but before the client
        # starts: the server has its own SUB/REQ/STR threads that are
        # not affected by client.stop(), so we capture them once here
        # and only count the deltas attributable to client lifecycle.
        time.sleep(0.1)
        baseline = _native_thread_count()

        client = pyrogue.interfaces.VirtualClient(addr='127.0.0.1', port=port)
        try:
            assert client.root is not None
            time.sleep(0.1)

            with_client = _native_thread_count()

            # The client adds at least the C++ SUB worker (ZmqClient::runThread)
            # and the Python _monThread. with_client must be strictly greater
            # than baseline; if it is not, this test is not measuring what
            # it claims to.
            assert with_client > baseline, (
                f"client construction did not raise native thread count: "
                f"baseline={baseline}, with_client={with_client}"
            )
        finally:
            client.stop()

        # Give the kernel a tick to reap the joined threads; ``join()``
        # in the C++ side blocks until the worker has exited, but the
        # /proc/self/status counter updates asynchronously on the next
        # task-list refresh.
        time.sleep(0.2)
        gc.collect()

        after_stop = _native_thread_count()

        # After stop(), the C++ SUB thread must have been joined+released.
        # Allow some slack (other transient threads may exist) but require
        # we have not accumulated relative to the pre-client baseline.
        assert after_stop <= baseline + 1, (
            f"VirtualClient.stop() leaked native threads: "
            f"baseline={baseline}, with_client={with_client}, "
            f"after_stop={after_stop}. The C++ ZmqClient subscriber "
            f"thread should have been released by stop() calling "
            f"rogue.interfaces.ZmqClient._stop(self)."
        )

    _clear_virtual_client_cache()


def test_virtual_client_stop_then_explicit_stop_is_idempotent():
    """Backward compat: callers that already call ``client._stop()`` after
    ``client.stop()`` continue to work.

    The C++ ``ZmqClient::stop()`` is guarded by ``running_``; once
    ``stop()`` has driven it false, the explicit ``_stop()`` follow-up
    short-circuits cleanly. This pins the contract that adding the
    ``_stop()`` call inside ``stop()`` does not break callers using the
    pre-fix two-call pattern.
    """
    port = _test_port(1)
    _clear_virtual_client_cache()

    with _StopRoot(name='IdempotentRoot', port=port):
        client = pyrogue.interfaces.VirtualClient(addr='127.0.0.1', port=port)
        try:
            assert client.root is not None
        finally:
            client.stop()    # now also calls _stop() internally
            client._stop()   # explicit call must remain a safe no-op
            client._stop()   # third call still safe

    _clear_virtual_client_cache()
