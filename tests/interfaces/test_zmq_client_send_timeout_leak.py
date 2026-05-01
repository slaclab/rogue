#!/usr/bin/env python3
#-----------------------------------------------------------------------------
# Title      : ZmqClient send/sendString timeout-path leak regression
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
# Pin the contract that ``ZmqClient::send()`` releases the per-iteration
# ``zmq_msg_t`` on the timeout-then-throw path.
#
# Pre-fix recv loop (src/rogue/interfaces/ZmqClient.cpp):
#
#     while (1) {
#         zmq_msg_init(&rxMsg);
#         if (zmq_recvmsg(zmqReq_, &rxMsg, 0) <= 0) {
#             ...
#             if (waitRetry_) {
#                 ...
#                 zmq_msg_close(&rxMsg);     // <-- closed on retry
#             } else {
#                 throw rogue::GeneralError::create(...);  // <-- NO close
#             }
#         } else { break; }
#     }
#
# When ``waitRetry_`` is false (the default) and the request times out, the
# pre-fix code raised the ``GeneralError`` without ever calling
# ``zmq_msg_close()``. With ZMQ's RCVTIMEO path the msg buffer is usually
# left empty so the per-iteration cost is small, but it is still an explicit
# ``zmq_msg_init`` without a matching ``zmq_msg_close`` — a contract leak
# that future ZMQ versions could turn into a real heap leak. The fix adds
# the missing close before the throw on both ``send()`` and ``sendString()``.
#
# Coverage scope: this test exercises the binary ``_send`` path. The
# string-mode ``getDisp`` path cannot be cleanly tested in CI because the
# pre-existing ``ZmqClient::stop()`` only closes ``zmqSub_`` when
# ``!doString_``, so a string-mode client's ``zmq_ctx_destroy()`` deadlocks
# waiting for the never-closed SUB socket. That is an independent
# pre-existing issue and is not in scope for this PR; the binary-mode test
# below is sufficient to lock in the missing-close fix because both call
# sites use the same recv loop pattern.

import gc
import zmq

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


def _silent_peer(port: int):
    """Bind a PUB on `port` and a silent REP on `port+1`.

    The REP socket binds but never calls ``recv``, so the ZmqClient's
    ``_send`` calls always reach RCVTIMEO and throw — exactly the
    timeout-then-throw recv loop the fix is about. Real binds (rather than
    a closed/unbound port) are required so ``ZmqClient._stop()`` can run
    its socket close + ``zmq_ctx_destroy()`` cleanly during teardown.

    ``port`` is supplied by the ``free_zmq_port`` fixture, which reserves
    a 3-port consecutive block via ``_find_free_port_block`` so port+1 is
    guaranteed free at allocation time and xdist workers cannot collide.
    """
    ctx = zmq.Context()
    pub = ctx.socket(zmq.PUB)
    pub.bind(f"tcp://127.0.0.1:{port}")
    rep = ctx.socket(zmq.REP)
    rep.bind(f"tcp://127.0.0.1:{port + 1}")
    return ctx, pub, rep, port


def _hammer_send_binary_timeouts(port: int, iterations: int) -> None:
    """Issue ``iterations`` binary-mode requests, each timing out and throwing.

    Binary mode (``doString=False``) drives ``ZmqClient::send()``, the call
    site of the missing ``zmq_msg_close()``.
    """
    client = rogue.interfaces.ZmqClient("127.0.0.1", port, False)
    try:
        client.setTimeout(50, False)  # 50 ms timeout, no waitRetry
        payload = b"timeout-leak-probe"
        for _ in range(iterations):
            with pytest.raises(Exception):
                client._send(payload)
    finally:
        client._stop()


def test_zmq_client_send_binary_timeout_does_not_leak(free_zmq_port) -> None:
    """``send()`` timeout-throw path must not grow heap unboundedly.

    Reverting the ``zmq_msg_close(&rxMsg);`` line added before the
    timeout-path ``throw`` in ``ZmqClient::send()`` lets a per-call
    ``zmq_msg_t`` resource stay un-closed; on libzmq versions that allocate
    inside ``zmq_msg_init``, the cycle below would visibly grow
    ``mallinfo2().uordblks``. The 4 MiB ceiling matches the other ZMQ
    lifecycle leak regressions (e.g.
    ``test_zmq_server_construct_without_start_does_not_leak_ctx``).
    """
    if _mallinfo2_uordblks() is None:
        pytest.skip("mallinfo2 not available on this libc")

    ctx, pub, rep, port = _silent_peer(free_zmq_port)
    try:
        # Warm-up so first-cycle internal allocations do not pollute the baseline.
        _hammer_send_binary_timeouts(port, iterations=10)
        gc.collect()

        iterations = 100
        before = _mallinfo2_uordblks()
        _hammer_send_binary_timeouts(port, iterations=iterations)
        gc.collect()
        after = _mallinfo2_uordblks()

        delta = after - before
        assert delta < 4 * 1024 * 1024, (
            f"ZmqClient::send timeout-throw cycle has catastrophic heap "
            f"growth: uordblks grew {delta} B over {iterations} timeouts "
            f"(missing zmq_msg_close before throw?)"
        )
    finally:
        pub.close(linger=0)
        rep.close(linger=0)
        ctx.term()
