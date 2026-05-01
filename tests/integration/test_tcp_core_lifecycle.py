#!/usr/bin/env python3
#-----------------------------------------------------------------------------
# Title      : TcpCore lifecycle / leak regression tests
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
# Pins the contract that ``TcpCore::stop()`` releases the worker ``std::thread``
# allocated by ``new std::thread(...)`` in the constructor.  The thread-safety/
# memory-lifetime hardening pass added ``std::atomic<bool>`` to ``TcpCore``'s
# ``threadEn_`` to fix a load race in teardown, but the matching
# ``delete thread_; thread_ = nullptr;`` after ``thread_->join()`` was missed
# in the same pass and added in a follow-up commit.  Reverting the
# ``delete thread_`` line leaks the libstdc++ std::thread implementation
# allocation (and its libpthread bookkeeping) on every server/client
# create+destroy cycle.
#
# Direct attribution requires a leak detector (ASan / Valgrind): the per-cycle
# std::thread wrapper is only ~100 B, so a behavioral test cannot reliably
# distinguish it from zmq context teardown noise. The ``mallinfo2()`` check
# below acts as a coarse smoke test (catastrophic regressions only) while
# the create/destroy/repeat-close paths pin the lifecycle contract that
# ``thread_ = nullptr`` makes safe.

import gc
import time

import pytest

import rogue.interfaces.stream

pytestmark = pytest.mark.integration


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
    """One create/destroy cycle: build a server+client pair, then drop them.

    Each cycle exercises the TcpCore ctor's ``new std::thread`` and the
    matching stop() path. ``close()`` is the deprecated alias that funnels
    into stop(), where the leak being pinned was located.
    """
    server = rogue.interfaces.stream.TcpServer("127.0.0.1", port)
    client = rogue.interfaces.stream.TcpClient("127.0.0.1", port)
    server.close()
    client.close()
    del server
    del client


def test_tcp_core_create_destroy_cycle_smoke(free_tcp_port):
    """``TcpCore::stop()`` must run the create/destroy cycle without
    catastrophic heap growth.

    The std::thread* leak fixed by ``delete thread_; thread_ = nullptr;`` in
    src/rogue/interfaces/stream/TcpCore.cpp is too small (~100 B per cycle)
    to attribute reliably without a leak detector. The 4 MiB ceiling here
    is a coarse smoke screen that catches catastrophic regressions (e.g.
    a zmq context never released, a thread stack never reaped) while
    leaving ASan/Valgrind to chase the small leak directly.

    Skipped on libcs without ``mallinfo2`` (macOS, musl). The C++-side
    audit lives in tests/cpp/core/test_atomic_thread_flags.cpp; the
    fd-leak corollary is covered by tests/protocols/test_udp_constructor_throws.py.
    """
    if _mallinfo2_uordblks() is None:
        pytest.skip("mallinfo2 not available on this libc")

    port = free_tcp_port

    # Warm-up so first-cycle internal allocations do not pollute the
    # baseline (zmq context arenas, libstdc++ thread-pool one-shots, etc.).
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

    # Catastrophic-only ceiling. The actual std::thread leak per cycle
    # (~100 B) is invisible against zmq teardown noise; this assertion
    # exists to catch zmq-context- or buffer-pool-scale regressions.
    assert delta < 4 * 1024 * 1024, (
        f"TcpCore lifecycle has catastrophic heap growth: uordblks grew "
        f"{delta} B over {iterations} create/destroy cycles"
    )


def test_tcp_core_repeated_close_is_safe(free_tcp_port):
    """``stop()`` is idempotent across the new ``thread_ = nullptr`` reset.

    After the fix, the second ``close()`` enters stop() with ``threadEn_``
    already false and short-circuits before touching the now-null
    ``thread_``. This is the user-observable contract that protects
    against a follow-on UAF if someone refactors ``running_`` checks.
    """
    server = rogue.interfaces.stream.TcpServer("127.0.0.1", free_tcp_port)
    client = rogue.interfaces.stream.TcpClient("127.0.0.1", free_tcp_port)

    # First close() runs the real teardown.
    server.close()
    client.close()

    # Second close() must be a no-op, not a use-after-free of thread_.
    server.close()
    client.close()

    # Give any background threads a tick to fully unwind before drop.
    time.sleep(0.05)
