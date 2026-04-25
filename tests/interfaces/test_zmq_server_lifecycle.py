#!/usr/bin/env python3
#-----------------------------------------------------------------------------
# Title      : ZmqServer lifecycle / leak regression tests
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
# Pins the contract that ``rogue::interfaces::ZmqServer::stop()`` releases
# both worker ``std::thread`` allocations (the binary-request rThread_ and
# the string-request sThread_). Reverting the
# ``delete rThread_; rThread_ = nullptr; delete sThread_; sThread_ = nullptr;``
# follow-up in src/rogue/interfaces/ZmqServer.cpp leaks two libstdc++
# std::thread implementation allocations on every server teardown.
#
# Mirrors test_zmq_client_lifecycle.py — the same caveats apply: each leaked
# std::thread internal struct is small (~80 B), so a glibc mallinfo2 ceiling
# only catches catastrophic regressions, not the small per-cycle leak. The
# repeated-stop assertion pins the public contract that ``_stop()`` is
# idempotent across the new ``rThread_/sThread_ = nullptr`` resets.
#
# Uses ``rogue.interfaces.ZmqServer`` directly (not ``pyrogue.interfaces``)
# to keep the C++ object's lifecycle isolated from pyrogue Root caching.

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
    """One create/start/stop/destroy cycle of a ZmqServer.

    ``_start()`` is what allocates rThread_ and sThread_ (see
    ZmqServer::start at src/rogue/interfaces/ZmqServer.cpp); without
    ``_start()`` the dtor short-circuits via ``threadEn_=false`` and the
    PR-added thread-pointer cleanup never runs, defeating the test.
    """
    server = rogue.interfaces.ZmqServer("127.0.0.1", port)
    server._start()
    server._stop()
    del server


def test_zmq_server_create_destroy_cycle_smoke(free_zmq_port):
    """``ZmqServer::stop()`` must run start/stop cycles without
    catastrophic heap growth.

    The std::thread* leaks fixed by
    ``delete rThread_; delete sThread_; rThread_/sThread_ = nullptr;`` are
    each ~80 B per cycle (so ~160 B per server cycle). The 4 MiB ceiling
    here catches catastrophic regressions only; ASan/Valgrind catch the
    small leak directly.

    Skipped on libcs without ``mallinfo2`` (macOS, musl).
    """
    if _mallinfo2_uordblks() is None:
        pytest.skip("mallinfo2 not available on this libc")

    # ``free_zmq_port`` returns the base of a free 3-port block. ZmqServer
    # binds base (PUB), base+1 (binary REP), base+2 (string REP).
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
        f"ZmqServer lifecycle has catastrophic heap growth: uordblks grew "
        f"{delta} B over {iterations} create/start/stop/destroy cycles"
    )


def test_zmq_server_repeated_stop_is_safe(free_zmq_port):
    """``_stop()`` is idempotent across the new ``rThread_/sThread_ = nullptr`` resets.

    After the fix, the second ``_stop()`` enters the C++ stop() with
    ``threadEn_`` already false and short-circuits before touching the
    now-null thread pointers. Without the ``= nullptr`` resets, a second
    ``_stop()`` would still short-circuit (so this test does not directly
    fail there), but the assertion pins the user-visible contract that
    calling stop twice is safe.
    """
    port = free_zmq_port

    server = rogue.interfaces.ZmqServer("127.0.0.1", port)
    server._start()
    server._stop()  # real teardown
    server._stop()  # must be a safe no-op
    server._stop()  # still safe
    del server

    # Give any background threads a tick to fully unwind before the
    # next test's port-search starts probing.
    time.sleep(0.05)


def test_zmq_server_construct_without_start_is_safe(free_zmq_port):
    """Constructing without ``_start()`` then destroying must not crash.

    The dtor's ``stop()`` short-circuits via ``threadEn_=false``, so no
    thread cleanup runs and the never-allocated ``rThread_/sThread_``
    pointers are never dereferenced. This pins the contract that the
    pre-start state is destroy-safe — important because the new
    ``delete rThread_; delete sThread_;`` lines added by the audit
    follow-up only execute inside the threadEn_ guard.
    """
    port = free_zmq_port
    server = rogue.interfaces.ZmqServer("127.0.0.1", port)
    del server


def test_zmq_server_start_failure_releases_resources(free_zmq_port):
    """A failed ``_start()`` (port collision) must not leak ZMQ resources."""
    if _mallinfo2_uordblks() is None:
        pytest.skip("mallinfo2 not available on this libc")

    port = free_zmq_port

    # Hold the publish port so every tryConnect() in the auto-port loop fails.
    import socket
    blocker = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    blocker.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        blocker.bind(("127.0.0.1", port))
        blocker.listen(1)

        for _ in range(2):
            s = rogue.interfaces.ZmqServer("127.0.0.1", port)
            with pytest.raises(Exception):
                s._start()
            del s
        gc.collect()

        iterations = 50
        before = _mallinfo2_uordblks()
        for _ in range(iterations):
            s = rogue.interfaces.ZmqServer("127.0.0.1", port)
            with pytest.raises(Exception):
                s._start()
            del s
        gc.collect()
        after = _mallinfo2_uordblks()

        delta = after - before
        assert delta < 4 * 1024 * 1024, (
            f"ZmqServer failed-start cycle has catastrophic heap growth: "
            f"uordblks grew {delta} B over {iterations} iterations"
        )
    finally:
        blocker.close()


def test_zmq_server_construct_without_start_does_not_leak_ctx(free_zmq_port):
    """Construct-without-start must not leak the ZMQ context allocated in the ctor."""
    if _mallinfo2_uordblks() is None:
        pytest.skip("mallinfo2 not available on this libc")

    port = free_zmq_port

    # Warm-up so first-cycle internal allocations do not pollute the baseline.
    for _ in range(4):
        s = rogue.interfaces.ZmqServer("127.0.0.1", port)
        del s
    gc.collect()

    iterations = 200
    before = _mallinfo2_uordblks()
    for _ in range(iterations):
        s = rogue.interfaces.ZmqServer("127.0.0.1", port)
        del s
    gc.collect()
    after = _mallinfo2_uordblks()

    delta = after - before

    # Each leaked zmq_ctx is several KiB, so a regression here is highly
    # visible against the 4 MiB ceiling that other lifecycle tests use.
    assert delta < 4 * 1024 * 1024, (
        f"ZmqServer construct-without-start has catastrophic heap growth: "
        f"uordblks grew {delta} B over {iterations} construct/destroy cycles "
        f"(ZMQ context likely leaked when start() was never called)"
    )
