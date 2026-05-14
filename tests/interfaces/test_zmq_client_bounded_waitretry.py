#!/usr/bin/env python3
#-----------------------------------------------------------------------------
# Title      : ZmqClient bounded waitRetry regression (issue #1236)
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
# Pin the contract for issue #1236: ``ZmqClient::setTimeout(msecs, waitRetry,
# maxRetries)`` must bound the recv-then-retry loop in ``ZmqClient::send()``
# (binary mode) and ``ZmqClient::sendString()`` (string mode).
#
# Pre-fix recv loop (src/rogue/interfaces/ZmqClient.cpp, both call sites):
#
#     while (1) {
#         zmq_msg_init(&rxMsg);
#         if (zmq_recvmsg(zmqReq_, &rxMsg, 0) <= 0) {
#             seconds += timeout_ / 1000.0;
#             if (waitRetry_) {          // <-- unbounded; SO deployment hung 20+ min
#                 logWaitRetry(...);
#                 zmq_msg_close(&rxMsg);
#             } else {
#                 zmq_msg_close(&rxMsg);
#                 throw rogue::GeneralError::create(...);
#             }
#         } else { break; }
#     }
#
# Caller in the wild that triggered #1236 (pysmurf base_class.py:90):
#
#     self._client.setTimeout(10000, True)   # comment: "Retries forever anyway"
#
# The fix adds an optional ``maxRetries`` parameter (default ``0`` = unbounded
# = pre-fix behaviour). When ``maxRetries > 0`` and ``waitRetry`` is true, the
# recv loop throws the same ``rogue.GeneralError`` after that many timeouts as
# the ``waitRetry=False`` path throws today.
#
# Test contracts pinned here:
#   1. New 3-arg ``setTimeout(msecs, waitRetry=True, maxRetries=N)`` exists in
#      the binding AND actually bounds the send-recv cycle.
#   2. Existing 2-arg form is unchanged (still unbounded retry).

import threading
import time

import pytest
import rogue
import rogue.interfaces
import zmq


def _silent_peer(port: int):
    """Bind PUB on ``port`` and a never-recv'ing REP on ``port+1``.

    Same pattern as ``test_zmq_client_send_timeout_leak``: real binds so
    ``ZmqClient._stop()`` cleanly tears down sockets and the context.
    ``free_zmq_port`` reserves a 3-port consecutive block.
    """
    ctx = zmq.Context()
    pub = ctx.socket(zmq.PUB)
    pub.bind(f"tcp://127.0.0.1:{port}")
    rep = ctx.socket(zmq.REP)
    rep.bind(f"tcp://127.0.0.1:{port + 1}")
    return ctx, pub, rep


def test_setTimeout_three_arg_form_bounds_retries(free_zmq_port) -> None:
    """``setTimeout(msecs, waitRetry=True, maxRetries=N)`` must throw after N timeouts.

    Pre-fix this test fails because the binding only accepts 2 positional
    args — boost::python raises ``ArgumentError``. With the fix, the recv
    loop in ``ZmqClient::send()`` exits after ``maxRetries`` RCVTIMEO trips
    and the call raises ``rogue.GeneralError`` with "Timeout" in the message.
    """
    port = free_zmq_port
    ctx, pub, rep = _silent_peer(port)
    try:
        client = rogue.interfaces.ZmqClient("127.0.0.1", port, False)
        try:
            # 50 ms RCVTIMEO × 3 retries = ~150 ms total wait before throw.
            client.setTimeout(50, True, 3)

            t0 = time.monotonic()
            with pytest.raises(rogue.GeneralError, match="Timeout"):
                client._send(b"probe")
            elapsed = time.monotonic() - t0

            # Lower bound: must have actually waited the full retry budget,
            # not short-circuited. Upper bound generous for CI jitter.
            assert 0.10 < elapsed < 2.0, (
                f"Bounded waitRetry: expected ~0.15 s, got {elapsed:.3f} s"
            )
        finally:
            client._stop()
    finally:
        pub.close(linger=0)
        rep.close(linger=0)
        ctx.term()


def test_setTimeout_two_arg_form_keeps_unbounded_retry(free_zmq_port) -> None:
    """Backwards compat: 2-arg ``setTimeout(msecs, waitRetry=True)`` stays unbounded.

    Issue #1236's pysmurf caller and ``_Virtual.py``'s post-bootstrap
    ``self.setTimeout(1000, True)`` both rely on this. The fix adds the
    ``maxRetries`` parameter as an opt-in default of ``0`` (unbounded). This
    test runs ``_send`` in a daemon thread for 1 s of wall time: the call
    must still be blocked when the wait expires.
    """
    port = free_zmq_port
    ctx, pub, rep = _silent_peer(port)
    client = None
    try:
        client = rogue.interfaces.ZmqClient("127.0.0.1", port, False)

        # 50 ms RCVTIMEO; no maxRetries (default unbounded).
        client.setTimeout(50, True)

        state = {"raised": None, "returned": False, "done": False}

        def _worker() -> None:
            try:
                client._send(b"probe")
                state["returned"] = True
            except BaseException as exc:
                state["raised"] = exc
            finally:
                state["done"] = True

        worker = threading.Thread(target=_worker, daemon=True)
        worker.start()

        # Wait well past several recv timeouts; the unbounded loop must still
        # be retrying, not have thrown or returned.
        worker.join(timeout=1.0)
        assert worker.is_alive(), (
            f"2-arg setTimeout unexpectedly exited send(): "
            f"raised={state['raised']!r}, returned={state['returned']!r}"
        )
        assert state["raised"] is None
        assert state["returned"] is False
    finally:
        # Closing the ZMQ context via _stop() unblocks the recv loop with
        # ETERM (or the close zeroes the socket pointer) so the daemon thread
        # exits before the process tears down.
        if client is not None:
            client._stop()
        pub.close(linger=0)
        rep.close(linger=0)
        ctx.term()
