#!/usr/bin/env python3
#-----------------------------------------------------------------------------
# Title      : ZmqServer REP-EFSM recovery regression
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
# ZMQ_REP requires strict recv -> send alternation. Before the fix, the
# runThread()/strThread() catch blocks dropped the request without sending
# a reply, which puts the REP socket in EFSM state and every subsequent
# zmq_recvmsg() returns -1 (errno=EFSM). The worker spins on failed recvs
# until shutdown and the server stops serving.
#
# The fix sends an empty reply on the REP socket from each catch block.
# This pins the contract that one bad request does not wedge the server.

import pickle
import time

import rogue.interfaces


class _BadResponseServer(rogue.interfaces.ZmqServer):
    """ZmqServer override whose ``_doRequest`` returns a non-buffer object."""

    def __init__(self, addr: str, port: int) -> None:
        rogue.interfaces.ZmqServer.__init__(self, addr, port)
        self.requestCount = 0

    def _doRequest(self, data):  # noqa: D401 - boost.python override
        self.requestCount += 1
        return None


def test_zmq_server_runthread_recovers_after_bad_response(free_zmq_port):
    """Two bad requests in a row must both invoke ``_doRequest``.

    Without the catch-block ``zmq_send(..., "", 0, 0)`` fix, the second
    request never reaches the server because the REP socket is wedged
    in EFSM after the first dropped reply.
    """
    port = free_zmq_port

    server = _BadResponseServer("127.0.0.1", port)
    try:
        server._start()

        client = rogue.interfaces.ZmqClient("127.0.0.1", port, False)
        try:
            client.setTimeout(500, False)
            payload = pickle.dumps({"attr": "noop", "path": ""})

            # Send several requests; track how many reach _doRequest.
            deadline = time.monotonic() + 8.0
            target = 3
            while server.requestCount < target and time.monotonic() < deadline:
                try:
                    client._send(payload)
                except Exception:
                    pass
                # Tiny pause so the worker can complete the cycle.
                time.sleep(0.05)

            assert server.requestCount >= target, (
                f"REP socket likely wedged in EFSM: only "
                f"{server.requestCount} of {target} requests reached "
                f"_doRequest. The catch block must send an empty reply "
                f"to keep the REQ/REP state machine healthy."
            )
        finally:
            client._stop()
    finally:
        server._stop()
