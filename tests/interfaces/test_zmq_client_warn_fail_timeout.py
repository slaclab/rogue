#!/usr/bin/env python3
#-----------------------------------------------------------------------------
# Title      : ZmqClient warn/fail timeout contract (issue #1236)
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
# Pin the contract for ``ZmqClient::setTimeout(warnTime, failTime=0)``. The
# recv loop in ``ZmqClient::send()`` (binary mode) and ``ZmqClient::sendString()``
# (string mode) wakes every ``warnTime`` ms; it keeps waiting until the
# accumulated wait reaches ``failTime``, then throws ``rogue.GeneralError``.
#
#     while (1) {
#         if (zmq_recvmsg(zmqReq_, &rxMsg, 0) <= 0) {
#             seconds += timeout_ / 1000.0;
#             deadlineReached = (failTime_ != 0 && seconds*1000 >= failTime_);
#             if (!deadlineReached && !stopping_) { logWaitRetry(...); }
#             else { throw rogue::GeneralError::create(...); }
#         } else { break; }
#     }
#
# Contracts pinned here:
#   1. ``failTime > 0`` bounds the send-recv cycle (throws ~failTime).
#   2. ``failTime == 0`` retries forever (the historic #1236 contract that
#      ``_Virtual.py``'s operational ``setTimeout(1000, 0)`` and downstream
#      callers such as pysmurf rely on).
#   3. A Python ``bool`` argument raises ``TypeError`` -- the removed
#      ``(msecs, waitRetry)`` form would otherwise silently coerce ``True`` to
#      ``failTime=1``.

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


def test_setTimeout_finite_failTime_bounds_wait(free_zmq_port) -> None:
    """``setTimeout(warnTime, failTime)`` must throw once the wait reaches failTime.

    50 ms warn poll, 150 ms deadline => the recv loop in ``ZmqClient::send()``
    throws ``rogue.GeneralError`` ("Timeout") after ~150 ms.
    """
    port = free_zmq_port
    ctx, pub, rep = _silent_peer(port)
    try:
        client = rogue.interfaces.ZmqClient("127.0.0.1", port, False)
        try:
            client.setTimeout(50, 150)

            t0 = time.monotonic()
            with pytest.raises(rogue.GeneralError, match="Timeout"):
                client._send(b"probe")
            elapsed = time.monotonic() - t0

            # Lower bound: must have actually waited the full deadline, not
            # short-circuited. Upper bound generous for CI jitter.
            assert 0.10 < elapsed < 2.0, (
                f"Finite failTime: expected ~0.15 s, got {elapsed:.3f} s"
            )
        finally:
            client._stop()
    finally:
        pub.close(linger=0)
        rep.close(linger=0)
        ctx.term()


def test_setTimeout_failTime_zero_retries_forever(free_zmq_port) -> None:
    """``setTimeout(warnTime, 0)`` retries forever (historic #1236 contract).

    ``_Virtual.py``'s post-bootstrap ``setTimeout(1000, 0)`` and pysmurf rely on
    this. Run ``_send`` in a daemon thread for 1 s of wall time: the call must
    still be blocked when the wait expires.
    """
    port = free_zmq_port
    ctx, pub, rep = _silent_peer(port)
    client = None
    try:
        client = rogue.interfaces.ZmqClient("127.0.0.1", port, False)

        # 50 ms warn poll; failTime=0 (forever).
        client.setTimeout(50, 0)

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

        # Wait well past several warn polls; the forever loop must still be
        # retrying, not have thrown or returned.
        worker.join(timeout=1.0)
        assert worker.is_alive(), (
            f"failTime=0 setTimeout unexpectedly exited send(): "
            f"raised={state['raised']!r}, returned={state['returned']!r}"
        )
        assert state["raised"] is None
        assert state["returned"] is False
    finally:
        # Closing the ZMQ context via _stop() sets the stopping_ sentinel and
        # unblocks the recv loop so the daemon thread exits before teardown.
        if client is not None:
            client._stop()
        pub.close(linger=0)
        rep.close(linger=0)
        ctx.term()


def test_setTimeout_rejects_bool_arguments(free_zmq_port) -> None:
    """A Python ``bool`` arg must raise ``TypeError``, not silently coerce.

    The removed ``(msecs, waitRetry)`` form passed ``True``/``False`` as the
    second arg. Under ``setTimeout(warnTime, failTime=0)`` a bool would coerce
    to ``failTime=1``/``0``; the binding rejects bools so stale 2-arg callers
    (e.g. pysmurf's ``setTimeout(10000, True)``) fail loudly.
    """
    port = free_zmq_port
    ctx, pub, rep = _silent_peer(port)
    try:
        client = rogue.interfaces.ZmqClient("127.0.0.1", port, False)
        try:
            with pytest.raises(TypeError):
                client.setTimeout(10000, True)
            with pytest.raises(TypeError):
                client.setTimeout(True, 0)
        finally:
            client._stop()
    finally:
        pub.close(linger=0)
        rep.close(linger=0)
        ctx.term()


def test_setTimeout_rejects_zero_warnTime(free_zmq_port) -> None:
    """``warnTime == 0`` must raise, not install a non-blocking busy-spin.

    A 0 ms warn period sets ZMQ_RCVTIMEO to 0 (non-blocking), so the recv loop
    would spin without ever advancing toward failTime. The setter rejects it.
    """
    port = free_zmq_port
    ctx, pub, rep = _silent_peer(port)
    try:
        client = rogue.interfaces.ZmqClient("127.0.0.1", port, False)
        try:
            with pytest.raises(rogue.GeneralError, match="warnTime"):
                client.setTimeout(0, 0)
            with pytest.raises(rogue.GeneralError, match="warnTime"):
                client.setTimeout(0, 100)
        finally:
            client._stop()
    finally:
        pub.close(linger=0)
        rep.close(linger=0)
        ctx.term()
