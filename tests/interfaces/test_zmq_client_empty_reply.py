#!/usr/bin/env python3
#-----------------------------------------------------------------------------
# Title      : ZmqClient zero-length reply regression
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
# Regression for slaclab/rogue issue #1360:
#   zmq_recvmsg returns 0 for a successful zero-length reply. ZmqServer sends
#   empty replies after exceptions, and an empty string is a legitimate
#   getDisp answer. The client must return that reply instead of treating it
#   as an RCVTIMEO failure (which then spins on EFSM until failTime_).
#
# A raw ZMQ REP peer is used (not pyrogue ZmqServer) to avoid the in-process
# GIL deadlock documented in test_zmq_client.py.

import pickle
import threading
import time

import pytest
import zmq

import rogue
import rogue.interfaces

pytestmark = pytest.mark.integration

# Generous RCVTIMEO; a correct client returns the empty reply far sooner.
TIMEOUT_MS = 2000


def _start_peer(port: int, repOffset: int, replies):
    """Bind PUB on port and a REP on port+repOffset that answers each request
    with the next entry of replies, then exits."""
    ctx = zmq.Context()
    pub = ctx.socket(zmq.PUB)
    pub.bind(f"tcp://127.0.0.1:{port}")
    rep = ctx.socket(zmq.REP)
    rep.bind(f"tcp://127.0.0.1:{port + repOffset}")

    def serve():
        for reply in replies:
            if rep.poll(10 * TIMEOUT_MS) == 0:
                return
            rep.recv()
            rep.send(reply)

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    return ctx, pub, rep, thread


def _stop_peer(ctx, pub, rep, thread):
    thread.join(timeout=10 * TIMEOUT_MS / 1000.0)
    pub.close(linger=0)
    rep.close(linger=0)
    ctx.term()


def test_zmq_client_send_returns_empty_reply(free_zmq_port):
    port = free_zmq_port
    peer = _start_peer(port, 1, [b"", b"ok"])
    try:
        client = rogue.interfaces.ZmqClient("127.0.0.1", port, False)
        try:
            client.setTimeout(TIMEOUT_MS, TIMEOUT_MS)
            payload = pickle.dumps({"path": "__ROOT__", "attr": None, "args": (), "kwargs": {}})

            start = time.monotonic()
            assert client._send(payload) == b""
            assert time.monotonic() - start < TIMEOUT_MS / 2000.0

            # The socket must still be usable for the next request.
            assert client._send(payload) == b"ok"
        finally:
            client._stop()
    finally:
        _stop_peer(*peer)


def test_zmq_client_get_disp_returns_empty_string(free_zmq_port):
    port = free_zmq_port
    peer = _start_peer(port, 2, [b"", b"ok"])
    try:
        client = rogue.interfaces.ZmqClient("127.0.0.1", port, True)
        try:
            client.setTimeout(TIMEOUT_MS, TIMEOUT_MS)

            start = time.monotonic()
            assert client.getDisp("root.var") == ""
            assert time.monotonic() - start < TIMEOUT_MS / 2000.0

            assert client.getDisp("root.var") == "ok"
        finally:
            client._stop()
    finally:
        _stop_peer(*peer)
