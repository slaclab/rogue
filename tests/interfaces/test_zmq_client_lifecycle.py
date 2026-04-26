#!/usr/bin/env python3
#-----------------------------------------------------------------------------
# Title      : ZmqClient lifecycle / leak regression tests
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
# Pins the contract that ``rogue::interfaces::ZmqClient::stop()`` releases the
# worker ``std::thread`` allocated for the SUB-receive loop. The thread-safety
# pass that added ``reqLock_`` to the ZMQ_REQ send/recv cycle (see
# src/rogue/interfaces/ZmqClient.cpp) left the matching
# ``delete thread_; thread_ = nullptr;`` step unimplemented; reverting that
# follow-up fix leaks the libstdc++ std::thread implementation allocation
# on every client teardown.
#
# Direct attribution still requires a leak detector (ASan / Valgrind) because
# the per-cycle leak is small (~100 B). The mallinfo2 ceiling here is a
# coarse smoke screen for catastrophic regressions; the explicit
# ``stop()`` / repeat-stop assertions pin the new ``thread_ = nullptr`` reset.
#
# Uses ``rogue.interfaces.ZmqClient`` directly (not ``VirtualClient``) to
# isolate the C++ object's lifecycle from pyrogue Root caching.

import gc
import time

import pytest

import rogue.interfaces


def _mallinfo2_uordblks() -> int | None:
    """Return ``mallinfo2().uordblks`` (in-use bytes) or ``None`` if unavailable."""
    import ctypes
    import ctypes.util
    libc_path = ctypes.util.find_library("c")
    if libc_path is None:
        return None
    libc = ctypes.CDLL(libc_path)
    if not hasattr(libc, "mallinfo2"):
        return None

    class _Mallinfo2(ctypes.Structure):
        _fields_ = [
            ("arena", ctypes.c_size_t),
            ("ordblks", ctypes.c_size_t),
            ("smblks", ctypes.c_size_t),
            ("hblks", ctypes.c_size_t),
            ("hblkhd", ctypes.c_size_t),
            ("usmblks", ctypes.c_size_t),
            ("fsmblks", ctypes.c_size_t),
            ("uordblks", ctypes.c_size_t),
            ("fordblks", ctypes.c_size_t),
            ("keepcost", ctypes.c_size_t),
        ]

    libc.mallinfo2.restype = _Mallinfo2
    return libc.mallinfo2().uordblks


def _cycle(port: int) -> None:
    """One create/destroy cycle of a non-doString ZmqClient.

    ``doString=False`` is the path that allocates the SUB-receive worker
    thread (the doString=True path skips thread creation entirely; see
    ZmqClient::ZmqClient at src/rogue/interfaces/ZmqClient.cpp). Pointing
    at a port nobody listens on is fine: zmq_connect() is non-blocking and
    the worker simply spins on RCVTIMEO until ``_stop()`` joins it.
    """
    client = rogue.interfaces.ZmqClient("127.0.0.1", port, False)
    client._stop()
    del client


def test_zmq_client_create_destroy_cycle_smoke(free_zmq_port):
    """``ZmqClient::stop()`` must run the create/destroy cycle without
    catastrophic heap growth.

    The std::thread* leak fixed by ``delete thread_; thread_ = nullptr;`` in
    ZmqClient.cpp is too small (~100 B per cycle) to attribute reliably
    without a leak detector. The 4 MiB ceiling here catches catastrophic
    regressions only; ASan/Valgrind catch the small leak directly.

    Skipped on libcs without ``mallinfo2`` (macOS, musl).
    """
    if _mallinfo2_uordblks() is None:
        pytest.skip("mallinfo2 not available on this libc")

    # ``free_zmq_port`` returns the base of a free 3-port block. ZmqClient's
    # SUB connects to base, REQ connects to base+1.
    port = free_zmq_port

    # Warm-up so first-cycle internal allocations do not pollute the baseline.
    for _ in range(4):
        _cycle(port)
    gc.collect()

    iterations = 200
    before = _mallinfo2_uordblks()
    for _ in range(iterations):
        _cycle(port)
    gc.collect()
    after = _mallinfo2_uordblks()

    delta = after - before

    assert delta < 4 * 1024 * 1024, (
        f"ZmqClient lifecycle has catastrophic heap growth: uordblks grew "
        f"{delta} B over {iterations} create/destroy cycles"
    )


def test_zmq_client_repeated_stop_is_safe(free_zmq_port):
    """``_stop()`` is idempotent across the new ``thread_ = nullptr`` reset.

    After the fix, the second ``_stop()`` enters the C++ stop() with
    ``running_`` already false and short-circuits before touching the
    now-null ``thread_``. Reverting the ``thread_ = nullptr`` line and
    deleting it without nilling would still pass the ``running_`` guard
    (so this test does not directly fail there), but the assertion still
    pins the user-visible contract that calling stop twice is safe.
    """
    port = free_zmq_port

    client = rogue.interfaces.ZmqClient("127.0.0.1", port, False)
    client._stop()  # real teardown
    client._stop()  # must be a safe no-op
    client._stop()  # still safe
    del client

    # Give any background threads a tick to fully unwind before the
    # next test's port-search starts probing.
    time.sleep(0.05)
