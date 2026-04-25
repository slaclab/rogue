#!/usr/bin/env python3
#-----------------------------------------------------------------------------
# Title      : memory::TcpClient / memory::TcpServer lifecycle regression tests
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
# Pins the contract that ``rim::TcpClient::stop()`` and ``rim::TcpServer::stop()``
# release the worker ``std::thread`` allocated by ``new std::thread(...)`` in
# their constructors. The thread-safety / memory-lifetime hardening pass added
# the matching ``delete thread_; thread_ = nullptr;`` step in both stop()
# implementations; reverting either leaks the libstdc++ std::thread
# implementation allocation per create+destroy cycle.
#
# Direct attribution of the ~100 B per-cycle leak still requires a leak detector
# (ASan / Valgrind). The mallinfo2 ceiling here is a coarse smoke screen for
# catastrophic regressions; the explicit ``close()`` / repeat-close assertions
# pin the new ``thread_ = nullptr`` reset that makes a second close() safe.
#
# Mirrors tests/integration/test_tcp_core_lifecycle.py (which targets the
# stream::TcpCore counterpart) so a future refactor to either class is caught
# at the same layer.

import gc
import time

import pytest

import rogue.interfaces.memory

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
    """One create/destroy cycle for the memory::TcpServer/TcpClient pair.

    Each cycle exercises both ctors' ``new std::thread(...)`` and the matching
    stop() path. ``close()`` is the deprecated alias that funnels into stop(),
    where the leak being pinned was located. ``waitReady=False`` skips the
    handshake probe so the test does not depend on transport timing.
    """
    server = rogue.interfaces.memory.TcpServer("127.0.0.1", port)
    client = rogue.interfaces.memory.TcpClient("127.0.0.1", port, False)
    client.close()
    server.close()
    del client
    del server


def test_memory_tcp_create_destroy_cycle_smoke(free_tcp_port):
    """memory::TcpClient/Server stop() must run the create/destroy cycle without
    catastrophic heap growth.

    The std::thread* leak fixed by ``delete thread_; thread_ = nullptr;`` in
    src/rogue/interfaces/memory/TcpClient.cpp and TcpServer.cpp is too small
    (~100 B per cycle) to attribute reliably without a leak detector. The
    4 MiB ceiling here is a coarse smoke screen that catches catastrophic
    regressions (e.g. a zmq context never released) while leaving ASan /
    Valgrind to chase the small leak directly.

    Skipped on libcs without ``mallinfo2`` (macOS, musl). The matching
    stream-side test lives in tests/integration/test_tcp_core_lifecycle.py.
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

    assert delta < 4 * 1024 * 1024, (
        f"memory::Tcp{{Client,Server}} lifecycle has catastrophic heap growth: "
        f"uordblks grew {delta} B over {iterations} create/destroy cycles"
    )


def test_memory_tcp_repeated_close_is_safe(free_tcp_port):
    """``close()`` is idempotent across the new ``thread_ = nullptr`` reset.

    After the fix, the second close() enters stop() with ``threadEn_``
    already false and short-circuits before touching the now-null
    ``thread_``. Pins the user-observable contract that double-close
    is safe and not a use-after-free of thread_.
    """
    server = rogue.interfaces.memory.TcpServer("127.0.0.1", free_tcp_port)
    client = rogue.interfaces.memory.TcpClient("127.0.0.1", free_tcp_port, False)

    # First close() runs the real teardown.
    client.close()
    server.close()

    # Second close() must be a no-op, not a use-after-free of thread_.
    client.close()
    server.close()

    # Third close() still safe.
    client.close()
    server.close()

    # Give any background threads a tick to fully unwind before drop.
    time.sleep(0.05)
