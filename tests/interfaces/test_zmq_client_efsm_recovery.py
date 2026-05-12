#!/usr/bin/env python3
#-----------------------------------------------------------------------------
# Title      : ZmqClient REQ-socket EFSM / sendmsg-failure regression
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
# Regression for slaclab/rogue issue #1234:
#   "ZMQ client crashed with rogue 6.12.0"
#   pysmurf SmurfControl init raises rogue.GeneralError: zmq_sendmsg failed
#   on the first _remoteAttr call after VirtualClient.__init__ prints
#   "Connected to AMCc at localhost:9006".
#
# Root-cause hypothesis under investigation:
#   H1: REQ socket in EFSM after a prior recv timeout (waitRetry_=False path).
#       The _waitForRoot tight retry loop abandons recv and retries send;
#       without ZMQ_REQ_RELAXED that would leave the socket in EFSM.
#       ZMQ_REQ_RELAXED is already set in ZmqClient::ZmqClient — so EFSM
#       should be suppressed. This test confirms the observable behaviour.
#
# Test structure:
#   - A raw ZMQ REP peer is used (not pyrogue ZmqServer) to avoid the
#     in-process GIL deadlock documented in test_zmq_client.py.
#   - The peer binds a PUB on port and a REP on port+1 so the client
#     constructor's zmq_connect calls succeed.
#   - First _send: the REP peer does NOT recv/send, so the client
#     hits RCVTIMEO and throws "Timeout waiting for response".
#   - Second _send: with waitRetry_=False and ZMQ_REQ_RELAXED the client
#     MUST be able to send again without zmq_sendmsg returning -1.
#
# The failing assertion (H1 confirmed) would be:
#   second _send raises rogue.GeneralError matching "zmq_sendmsg failed"
#
# The passing assertion (H1 refuted / bug fixed) is:
#   second _send either succeeds or raises "Timeout" (not "zmq_sendmsg failed")

import pickle

import pytest
import zmq

import rogue
import rogue.interfaces

pytestmark = pytest.mark.integration


def _bind_silent_peer(port: int):
    """Bind PUB on port and a silent REP on port+1.

    The REP socket binds but never calls recv, so every ZmqClient._send()
    reaches RCVTIMEO and throws — exactly the timeout-then-throw recv path
    that leaves a standard (non-RELAXED) REQ socket in EFSM.

    Real binds are required so ZmqClient._stop() can close the context
    cleanly during teardown.  free_zmq_port reserves a 3-port consecutive
    block so port+1 is guaranteed free at allocation time.
    """
    ctx = zmq.Context()
    pub = ctx.socket(zmq.PUB)
    pub.bind(f"tcp://127.0.0.1:{port}")
    rep = ctx.socket(zmq.REP)
    rep.bind(f"tcp://127.0.0.1:{port + 1}")
    return ctx, pub, rep


def test_zmq_client_second_send_after_recv_timeout_does_not_raise_sendmsg_failed(free_zmq_port):
    """Second _send after a recv-timeout must not raise 'zmq_sendmsg failed'.

    This is the core H1 regression for issue #1234.  On a REQ socket with
    ZMQ_REQ_RELAXED=1, abandoning the recv and calling send again is legal.
    The send must succeed (return >= 0 from zmq_sendmsg), so the second
    _send must raise "Timeout" (RCVTIMEO) not "zmq_sendmsg failed".

    If this test fails with "zmq_sendmsg failed", H1 is confirmed and
    ZMQ_REQ_RELAXED is either not being set or not effective.
    """
    port = free_zmq_port
    ctx, pub, rep = _bind_silent_peer(port)
    try:
        client = rogue.interfaces.ZmqClient("127.0.0.1", port, False)
        try:
            client.setTimeout(200, False)  # 200 ms, no waitRetry
            payload = pickle.dumps({"path": "__ROOT__", "attr": None, "args": (), "kwargs": {}})

            # First send: server is silent, expect Timeout (not zmq_sendmsg failed)
            with pytest.raises(Exception) as exc_info:
                client._send(payload)
            first_msg = str(exc_info.value)
            assert "zmq_sendmsg failed" not in first_msg, (
                f"First send raised zmq_sendmsg failed (unexpected): {first_msg}"
            )
            # Positive assertion: the precondition for the EFSM-regression
            # check on the second send is that the first send abandoned recv
            # via RCVTIMEO. If the first send fails on a different error
            # (early disconnect/ETERM/etc.), the second send isn't actually
            # exercising the EFSM-recovery path and the test would pass
            # vacuously.
            assert "Timeout" in first_msg or "timeout" in first_msg.lower(), (
                f"First send raised an unexpected error "
                f"(not Timeout, not zmq_sendmsg): {first_msg}"
            )

            # Second send immediately after the timeout: with ZMQ_REQ_RELAXED,
            # zmq_sendmsg must succeed (queue the message), and RCVTIMEO fires.
            # If zmq_sendmsg fails (e.g. EFSM), we get "zmq_sendmsg failed" here.
            with pytest.raises(Exception) as exc_info2:
                client._send(payload)
            second_msg = str(exc_info2.value)

            assert "zmq_sendmsg failed" not in second_msg, (
                f"H1 CONFIRMED: second send after recv-timeout raised "
                f"'zmq_sendmsg failed' — REQ socket left in EFSM state. "
                f"ZMQ_REQ_RELAXED is not suppressing EFSM for this send. "
                f"Full error: {second_msg}"
            )
            # The second send must raise Timeout (not any other error)
            assert "Timeout" in second_msg or "timeout" in second_msg.lower(), (
                f"Second send raised unexpected error (not Timeout, not zmq_sendmsg): {second_msg}"
            )
        finally:
            client._stop()
    finally:
        pub.close(linger=0)
        rep.close(linger=0)
        ctx.term()


def test_zmq_client_multiple_sends_after_repeated_recv_timeouts(free_zmq_port):
    """N consecutive sends each timing out must all reach the send phase.

    Mirrors the _waitForRoot tight-retry loop: up to 5 calls with
    waitRetry_=False, server silent.  Each must raise Timeout, not
    zmq_sendmsg failed.  This proves the REQ socket does not degrade
    after multiple abandoned-recv cycles.
    """
    port = free_zmq_port
    ctx, pub, rep = _bind_silent_peer(port)
    try:
        client = rogue.interfaces.ZmqClient("127.0.0.1", port, False)
        try:
            client.setTimeout(100, False)  # 100 ms, no waitRetry
            payload = pickle.dumps({"path": "__ROOT__", "attr": None, "args": (), "kwargs": {}})

            for i in range(5):
                with pytest.raises(Exception) as exc_info:
                    client._send(payload)
                msg = str(exc_info.value)
                assert "zmq_sendmsg failed" not in msg, (
                    f"Iteration {i}: send raised 'zmq_sendmsg failed' — "
                    f"REQ socket entered EFSM after {i} abandoned-recv cycles. "
                    f"ZMQ_REQ_RELAXED should prevent this. Full error: {msg}"
                )
                # Positive assertion: each iteration must surface the RCVTIMEO
                # timeout, not some other ZMQ error (ETERM, ENOTSOCK, etc.).
                # Without this check the test could pass on a different
                # failure mode and silently lose coverage.
                assert "Timeout" in msg or "timeout" in msg.lower(), (
                    f"Iteration {i}: send raised an unexpected error "
                    f"(not Timeout, not zmq_sendmsg failed): {msg}"
                )
        finally:
            client._stop()
    finally:
        pub.close(linger=0)
        rep.close(linger=0)
        ctx.term()
