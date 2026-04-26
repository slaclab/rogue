#!/usr/bin/env python3
#-----------------------------------------------------------------------------
# Title      : UDP Server / Client constructor throw paths
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
# These tests pin the constructor-throw contracts and catch regressions in
# the file-descriptor / addrinfo cleanup added on those paths:
#   * udp.Server::Server() must throw if bind() fails (e.g. binding to a
#     privileged port without CAP_NET_BIND_SERVICE). The fix close()s the
#     socket fd before raising; we observe via /proc/self/fd that the fd
#     count stays bounded across many failed attempts. Without the
#     close-before-throw, the fd count grows monotonically and the
#     assertion below trips.
#   * udp.Client::Client() must throw on a syntactically valid but
#     unresolvable hostname. The fix close()s the fd and frees the
#     getaddrinfo result before raising; the same fd-count observation
#     applies.

import os
import socket
import sys
import time

import pytest

import rogue.protocols.udp


pytestmark = pytest.mark.skipif(
    not sys.platform.startswith("linux"),
    reason="/proc/self/fd is Linux-only",
)


def _open_fd_count() -> int:
    return len(os.listdir("/proc/self/fd"))


def _can_bind_privileged_port(port: int) -> bool:
    """Return True if this process can bind to ``port`` (i.e. is privileged)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.bind(("127.0.0.1", port))
            return True
        except PermissionError:
            return False
        except OSError:
            # Port may be in use; not a permission issue, so we *can* bind in
            # general. Treat as privileged for the purpose of skip logic.
            return True
        finally:
            s.close()
    except Exception:
        return False


def test_udp_server_bind_failure_releases_fd():
    """A failed bind() must throw and not leak the socket fd.

    Reverting the close-before-throw added in Server::Server() makes the fd
    count grow by one per iteration and trips the assertion below.
    """
    if _can_bind_privileged_port(1):
        pytest.skip("running with privileges to bind to port 1; cannot trigger bind failure")

    baseline = _open_fd_count()
    for _ in range(32):
        with pytest.raises(Exception, match="Failed to bind"):
            rogue.protocols.udp.Server(1, False)
    # An unfixed fd leak grows by 32 over the loop, which is well above the
    # small slack allowed for unrelated fd churn.
    assert _open_fd_count() <= baseline + 4


def test_udp_client_unresolvable_host_releases_fd():
    """Client constructor must throw on an unresolvable host without leaking.

    Reverting the close-before-throw + freeaddrinfo() call added in
    Client::Client() makes the fd count grow by one per iteration.
    """
    # ``.invalid`` is reserved by RFC 6761 to never resolve.
    bad_host = "rogue-test-host-does-not-exist.invalid"
    baseline = _open_fd_count()
    for _ in range(32):
        with pytest.raises(Exception, match="Failed to resolve"):
            rogue.protocols.udp.Client(bad_host, 12345, False)
    assert _open_fd_count() <= baseline + 4


def test_udp_server_so_reuseaddr_coexists_with_python_socket():
    """The new ``setsockopt(SO_REUSEADDR)`` in Server::Server() must let the
    rogue Server bind to a port already held by another SO_REUSEADDR socket.

    Reverting the setsockopt() call makes the rogue bind() fail with
    EADDRINUSE because Linux requires *both* sockets to set SO_REUSEADDR for
    UDP coexistence on the same address+port. Verified against the
    pre-release version of Server.cpp: bind() fails with the
    "Another process may be using it" message.
    """
    helper = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    helper.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    helper.bind(("0.0.0.0", 0))
    port = helper.getsockname()[1]
    try:
        # If the rogue Server lacks SO_REUSEADDR this raises EADDRINUSE.
        serv = rogue.protocols.udp.Server(port, False)
        assert serv.getPort() == port
        # Pre-existing crash workaround: rogue Server destruction races with
        # its rx-thread startup if the object is destroyed too quickly. Give
        # the thread time to settle before dropping the reference.
        time.sleep(0.5)
        serv = None
    finally:
        helper.close()


def test_udp_server_two_rogue_instances_coexist_on_same_port():
    """Document the SO_REUSEADDR semantic shift: two ``udp::Server`` instances
    on the same port now BOTH bind successfully where the pre-release code
    would have rejected the second with EADDRINUSE.

    This is a deliberate behavior change motivated by rapid-rebind
    workflows and coexistence with externally-held SO_REUSEADDR sockets.
    The downside is that an accidental duplicate Server is now silently
    accepted; incoming UDP packets are then split between the two by the
    kernel non-deterministically. This test pins the new contract so a
    future revert (or a guard flag added to opt out) is caught at the test
    layer rather than as a surprise in production.

    If a constructor option is later added to disable SO_REUSEADDR, this
    test should be tightened to assert the duplicate raises under the
    default and only coexists when the option is set.
    """
    # Bind the first Server to an arbitrary free port chosen by the kernel.
    first = rogue.protocols.udp.Server(0, False)
    port = first.getPort()
    try:
        # Pre-fix this would raise "Another process may be using it"; with
        # SO_REUSEADDR set on both sockets the kernel accepts the second
        # bind. We tear it down quickly to avoid the rx-thread startup
        # race noted in the helper-coexistence test above.
        second = rogue.protocols.udp.Server(port, False)
        try:
            assert second.getPort() == port
            time.sleep(0.5)
        finally:
            second = None
    finally:
        # Same settle delay before dropping the first reference.
        time.sleep(0.5)
        first = None
