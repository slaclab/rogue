#!/usr/bin/env python3
#-----------------------------------------------------------------------------
# Title      : stream::TcpCore (server mode) ctor bind-failure cleanup
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
# Pins the new ``try { ... } catch (...) { close+destroy; throw; }`` wrapper
# in ``ris::TcpCore::TcpCore`` for the server-mode branch (where bind() is
# the failure mode we can trigger from CI). Mirrors
# tests/integration/test_memory_tcp_server_bind_failure.py.
#
# Before the fix, a failure in ``zmq_bind`` (e.g. address already in use)
# threw out of the ctor. Because the dtor does NOT run on a ctor-throw,
# the ZMQ context and three sockets allocated above the bind line were
# leaked. zmq_ctx_destroy blocks until every socket is explicitly closed,
# so the leak persisted for the lifetime of the process.
#
# We trigger the bind failure deterministically by binding two stream
# TcpServers (which is the Python-exposed entry point for the TcpCore
# server-mode ctor; ``stream::TcpCore`` itself cannot be instantiated
# from Python) to the same port. Without the catch block /proc/self/fd
# grows by several fds per failed bind iteration; with it the count
# stays bounded.
#
# The TcpClient (non-server) ctor branch is intentionally NOT covered
# here: ``zmq_setsockopt`` does not fail under any input we can supply
# from userspace, and ``zmq_connect`` is asynchronous and never throws
# synchronously even on unreachable addresses, so its catch block has no
# CI-reachable trigger.

import os
import sys
import time

import pytest

import rogue.interfaces.stream

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not sys.platform.startswith("linux"),
        reason="/proc/self/fd is Linux-only",
    ),
]


def _open_fd_count() -> int:
    return len(os.listdir("/proc/self/fd"))


def test_tcp_core_server_bind_failure_releases_sockets(free_tcp_port):
    """A second stream::TcpServer on a held port must throw without leaking fds.

    ``stream::TcpServer`` is a thin subclass that runs the
    ``ris::TcpCore`` ctor with ``server=true``; it is the only Python-
    reachable trigger for the TcpCore catch block. Reverting the new ctor
    try/catch in src/rogue/interfaces/stream/TcpCore.cpp leaves the ZMQ
    context and the PUSH/PULL sockets allocated when ``zmq_bind`` fails,
    so /proc/self/fd grows monotonically across iterations.
    """
    port = free_tcp_port

    # First server holds the port for the rest of the test; the second
    # ctor enters the bind-failure path we want to exercise.
    holder = rogue.interfaces.stream.TcpServer("127.0.0.1", port)
    try:
        baseline = _open_fd_count()

        for _ in range(32):
            with pytest.raises(Exception):
                rogue.interfaces.stream.TcpServer("127.0.0.1", port)

        # Allow any final ZMQ thread teardown to settle before measuring.
        time.sleep(0.05)
        after = _open_fd_count()
        assert after <= baseline + 12, (
            f"stream::TcpCore ctor leaks fds on bind failure: "
            f"fd count grew from {baseline} to {after} over 32 failed binds"
        )
    finally:
        # close() funnels into stop() which delete-and-nulls the worker
        # thread plus zmq_close()/zmq_ctx_destroy() the sockets/ctx.
        holder.close()
