#!/usr/bin/env python3
#-----------------------------------------------------------------------------
# Title      : memory::TcpServer ctor bind-failure cleanup
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
# in ``rim::TcpServer::TcpServer`` (and the symmetric one in
# ``rim::TcpClient::TcpClient`` and ``ris::TcpCore::TcpCore``).
#
# Before the fix, a failure in ``zmq_bind`` (e.g. address already in use)
# threw out of the ctor. Because the dtor does NOT run on a ctor-throw, the
# ZMQ context and three sockets allocated above the bind line were leaked.
# zmq_ctx_destroy blocks until every socket is explicitly closed, so the
# leak persisted for the lifetime of the process and, in long-lived test
# processes, accumulated thousands of stale ZMQ sockets visible in
# /proc/self/fd.
#
# We trigger the bind failure deterministically by binding two TcpServers
# to the same address+port. Without the catch block the fd count grows by
# one per failed-second-bind iteration; with it the count stays bounded.

import os
import sys
import time

import pytest

import rogue.interfaces.memory

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not sys.platform.startswith("linux"),
        reason="/proc/self/fd is Linux-only",
    ),
]


def _open_fd_count() -> int:
    return len(os.listdir("/proc/self/fd"))


def test_memory_tcp_server_bind_failure_releases_sockets(free_tcp_port):
    """A second TcpServer on a held port must throw without leaking fds.

    Reverting the new ctor try/catch in src/rogue/interfaces/memory/TcpServer.cpp
    leaves the ZMQ context and three sockets (PUSH, PULL, ZMQ_REP) allocated
    when ``zmq_bind`` fails, so /proc/self/fd grows monotonically across
    iterations.
    """
    port = free_tcp_port

    # First server holds the port for the rest of the test.
    holder = rogue.interfaces.memory.TcpServer("127.0.0.1", port)
    try:
        baseline = _open_fd_count()

        # Each iteration tries to construct a second server on the same
        # port; the bind in the ctor must fail and the catch block must
        # release every fd opened so far. The 32-iteration count gives the
        # pre-fix leak (4+ fds per cycle) ample headroom over the +12 slack.
        for _ in range(32):
            with pytest.raises(Exception):
                rogue.interfaces.memory.TcpServer("127.0.0.1", port)

        # Allow any final ZMQ thread teardown to settle before measuring.
        time.sleep(0.05)
        after = _open_fd_count()
        assert after <= baseline + 12, (
            f"memory::TcpServer ctor leaks fds on bind failure: "
            f"fd count grew from {baseline} to {after} over 32 failed binds"
        )
    finally:
        holder.close()
