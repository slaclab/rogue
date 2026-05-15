#!/usr/bin/env python3
#-----------------------------------------------------------------------------
# Title      : VirtualClient dead-instance regression (issue #1234)
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
#
# Pre-fix behaviour (the bug):
#   ``VirtualClient.__init__`` wrapped the bootstrap ``_waitForRoot``
#   handshake in ``try/except Exception`` and on failure called
#   ``_cleanupFailedInit()`` -- which tears down the ZMQ context via
#   ``ZmqClient._stop(self)`` -- then *printed* a "Failed to connect" banner
#   and *returned normally* from ``__init__``. The caller received a
#   ``VirtualClient`` instance whose underlying ``ZmqClient`` had been
#   destroyed, with no exception to signal the failure.
#
#   The first subsequent ``_remoteAttr`` / ``_send`` on the dead instance
#   reached ``ZmqClient::send`` (src/rogue/interfaces/ZmqClient.cpp:330),
#   where ``zmq_sendmsg`` on the torn-down socket returned -1 and the
#   throw surfaced as the exact crash on the issue:
#       rogue.GeneralError: ZmqClient::send: General Error: zmq_sendmsg failed
#
#   That throw was introduced in v6.12.0 (commit a5bff522c). Before then
#   the same ``zmq_sendmsg`` failure was silently discarded and the recv
#   loop subsequently timed out, surfacing as "Timeout waiting for response"
#   -- so the bug is older than v6.12.0 but only became visible at v6.12.0.
#
# Post-fix behaviour pinned by this file:
#   1. ``VirtualClient.__init__`` raises ``ConnectionError`` (chained from
#      the underlying handshake exception) when ``_waitForRoot`` fails.
#      No dead instance escapes the constructor.
#   2. As defence-in-depth, ``_remoteAttr`` checks ``_vcInitialized`` and
#      raises ``RuntimeError`` early on a dead instance (for example after
#      ``stop()``), so even a path that constructed an instance and then
#      tore it down fails fast with a clear message instead of slipping
#      through to the C++ ``zmq_sendmsg failed`` throw.
#   3. The C++ throw at ``ZmqClient::send`` now embeds ``zmq_errno`` and
#      ``zmq_strerror`` in the message, so any residual path that does
#      reach it produces a self-describing error.

import pytest

import pyrogue
import pyrogue.interfaces


pytestmark = pytest.mark.integration


class _RemoteRoot(pyrogue.Root):
    """Minimal Root with a ZmqServer suitable for VirtualClient bootstrap."""

    def __init__(self, *, name: str, port: int):
        super().__init__(name=name, pollEn=False)
        self.add(pyrogue.LocalVariable(name='Value', value=0, mode='RO'))
        self.zmqServer = pyrogue.interfaces.ZmqServer(
            root=self, addr='127.0.0.1', port=port)
        self.addInterface(self.zmqServer)


def _clear_client_cache() -> None:
    """Drain any cached VirtualClient instances between tests."""
    cache = pyrogue.interfaces.VirtualClient.ClientCache
    for client in list(cache.values()):
        try:
            client.stop()
        except Exception:
            pass
    cache.clear()


@pytest.fixture
def fast_connect_timeout(monkeypatch):
    """Shorten the _waitForRoot deadline so the unreachable cases finish fast."""
    monkeypatch.setenv("ROGUE_VIRTUAL_CONNECT_TIMEOUT", "0.5")
    _clear_client_cache()
    yield
    _clear_client_cache()


def test_virtualclient_init_raises_connectionerror_on_unreachable_server(
    fast_connect_timeout, free_zmq_port
):
    """``__init__`` must raise instead of returning a dead instance.

    No server is bound on ``free_zmq_port``, so ``_waitForRoot`` exhausts
    its bounded retry window and ``_cleanupFailedInit`` tears down the
    underlying ZmqClient. Pre-fix, ``__init__`` printed an error and
    returned -- this test pins the post-fix contract that the failure
    surfaces as ``ConnectionError`` to the caller.
    """
    with pytest.raises(ConnectionError) as exc_info:
        pyrogue.interfaces.VirtualClient(
            addr='127.0.0.1', port=free_zmq_port)

    msg = str(exc_info.value)
    assert "127.0.0.1" in msg and str(free_zmq_port) in msg, (
        f"ConnectionError must identify the unreachable target; got: {msg!r}"
    )

    # No instance must remain pinned in the singleton cache after init fails.
    assert hash(('127.0.0.1', free_zmq_port)) not in (
        pyrogue.interfaces.VirtualClient.ClientCache
    ), "Failed-init instance must be removed from ClientCache by _cleanupFailedInit."


def test_virtualclient_init_chains_underlying_handshake_exception(
    fast_connect_timeout, free_zmq_port
):
    """The raised ConnectionError must chain the original handshake exception.

    Preserving ``__cause__`` is what lets callers and tracebacks recover
    the libzmq-level error (RCVTIMEO etc.) without grepping the message.
    """
    with pytest.raises(ConnectionError) as exc_info:
        pyrogue.interfaces.VirtualClient(
            addr='127.0.0.1', port=free_zmq_port)

    assert exc_info.value.__cause__ is not None, (
        "ConnectionError must chain the underlying _waitForRoot exception "
        "via `raise ... from exc` so callers can inspect the root cause."
    )


def test_remoteattr_after_stop_raises_runtime_error(free_zmq_port):
    """``_remoteAttr`` on a stopped VirtualClient must fail fast and clear.

    Exercises the defence-in-depth liveness guard: construct a real,
    working VirtualClient against a live Root, call ``stop()`` (which sets
    ``_vcInitialized=False``), then call ``_remoteAttr``. Pre-fix this
    slipped through to ``ZmqClient::send`` and crashed with the issue
    #1234 traceback. Post-fix the guard catches it with a RuntimeError
    that names what happened.
    """
    _clear_client_cache()
    with _RemoteRoot(name='RemoteRoot', port=free_zmq_port):
        client = pyrogue.interfaces.VirtualClient(
            addr='127.0.0.1', port=free_zmq_port)
        assert client.root is not None, "bootstrap handshake must succeed"

        client.stop()
        assert client._vcInitialized is False, (
            "stop() must clear _vcInitialized (precondition for the guard)"
        )

        with pytest.raises(RuntimeError) as exc_info:
            client._remoteAttr('__ROOT__', None)

        msg = str(exc_info.value)
        assert "not connected" in msg.lower(), (
            f"RuntimeError must explain why the call is rejected; got: {msg!r}"
        )
        # Critically, the failure must NOT be the issue #1234 string -- if
        # it is, the guard was bypassed and the call leaked to zmq_sendmsg.
        assert "zmq_sendmsg failed" not in msg, (
            "Liveness guard was bypassed: call reached ZmqClient::send "
            "instead of failing in _remoteAttr."
        )
