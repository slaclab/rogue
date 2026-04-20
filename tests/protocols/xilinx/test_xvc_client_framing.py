#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
"""Byte-level framing tests for xvc_client.XvcClient.

The wire bytes emitted by XvcClient must match XvcConnection::run dispatch
exactly (getinfo/settck/shift command handling; fill() sizes 8/11/10;
little-endian bit reassembly in the settck and shift response paths).

These tests do NOT spin up the C++ server.  Each test uses socket.socketpair()
as a fake server endpoint:
  - the client's _sock is replaced with one end of the pair
  - a helper thread drives the other end (reads request bytes, scripts reply)
  - assertions compare the request bytes byte-for-byte against the spec

Zero dependency on the Rogue C++ build (no `import rogue` / `import pyrogue`).
"""
import socket
import struct
import threading

import pytest

from xvc_client import XvcClient


# ---------------------------------------------------------------------------
# Test harness: inject a socketpair endpoint as the client's socket.
# ---------------------------------------------------------------------------


class _MockXvcClient(XvcClient):
    """XvcClient that skips connect() and binds to a pre-made socket."""

    def __init__(self, sock, timeout=5.0):
        super().__init__(host="mock", port=0, timeout=timeout)
        self._sock = sock

    def connect(self):
        # already wired
        return


def _run_with_socketpair(client_fn, server_fn):
    """Drive client_fn(client) in a background thread, server_fn(srv) in main.

    Returns (server_return, client_return, client_exc).
    """
    sp_srv, sp_cli = socket.socketpair()
    sp_srv.settimeout(5.0)
    sp_cli.settimeout(5.0)

    client = _MockXvcClient(sp_cli)
    result = {}

    def _client_thread():
        try:
            result["ret"] = client_fn(client)
        except Exception as e:
            result["exc"] = e

    t = threading.Thread(target=_client_thread, name="xvc-client")
    t.start()
    try:
        srv_ret = server_fn(sp_srv)
    finally:
        t.join(timeout=5.0)
        try:
            sp_srv.close()
        except OSError:
            pass
        client.close()

    assert not t.is_alive(), "client thread did not exit"
    return srv_ret, result.get("ret"), result.get("exc")


def _recv_exact(s, n):
    buf = bytearray()
    while len(buf) < n:
        chunk = s.recv(n - len(buf))
        if not chunk:
            raise RuntimeError("server-side EOF (got {})".format(len(buf)))
        buf.extend(chunk)
    return bytes(buf)


# ---------------------------------------------------------------------------
# Frame-out tests: what bytes does the client put on the wire?
# ---------------------------------------------------------------------------


def test_getinfo_frame_bytes():
    """Request is literally b'getinfo:' (8 bytes)."""
    def server(srv):
        req = _recv_exact(srv, 8)
        srv.sendall(b"xvcServer_v1.0:1024\n")
        return req

    req, ret, exc = _run_with_socketpair(
        lambda c: c.getinfo(),
        server,
    )
    assert exc is None, exc
    assert req == b"getinfo:"
    assert ret == ("xvcServer_v1.0", 1024)


def test_settck_frame_bytes():
    """Request is b'settck:' + struct.pack('<I', period) (7 + 4 = 11 bytes)."""
    expected = b"settck:" + struct.pack("<I", 42)
    assert len(expected) == 11

    def server(srv):
        req = _recv_exact(srv, 11)
        srv.sendall(struct.pack("<I", 25))
        return req

    req, ret, exc = _run_with_socketpair(
        lambda c: c.settck(42),
        server,
    )
    assert exc is None, exc
    assert req == expected
    assert ret == 25


def test_shift_frame_bytes():
    """Request: b'shift:' + <u32 LE nbits> + tms + tdi (10 bytes header)."""
    nbits = 9
    tms   = b"\xAB\x01"
    tdi   = b"\xCD\x00"
    expected_header = b"shift:" + struct.pack("<I", nbits)
    assert len(expected_header) == 10

    def server(srv):
        header = _recv_exact(srv, 10)
        tms_rx = _recv_exact(srv, 2)
        tdi_rx = _recv_exact(srv, 2)
        srv.sendall(b"\x55\x00")
        return header, tms_rx, tdi_rx

    (header, tms_rx, tdi_rx), tdo, exc = _run_with_socketpair(
        lambda c: c.shift(nbits, tms, tdi),
        server,
    )
    assert exc is None, exc
    assert header == expected_header
    assert tms_rx == tms
    assert tdi_rx == tdi
    assert tdo == b"\x55\x00"


# ---------------------------------------------------------------------------
# Response-parse tests: what does the client return to the caller?
# ---------------------------------------------------------------------------


def test_getinfo_response_parse():
    def server(srv):
        _recv_exact(srv, 8)
        srv.sendall(b"xvcServer_v1.0:1024\n")

    _, ret, exc = _run_with_socketpair(
        lambda c: c.getinfo(),
        server,
    )
    assert exc is None, exc
    assert ret == ("xvcServer_v1.0", 1024)


def test_settck_response_parse():
    def server(srv):
        _recv_exact(srv, 11)
        srv.sendall(struct.pack("<I", 25))

    _, ret, exc = _run_with_socketpair(
        lambda c: c.settck(100),
        server,
    )
    assert exc is None, exc
    assert ret == 25


@pytest.mark.parametrize("nbits", [1, 7, 8, 9, 15, 16, 17, 32, 64])
def test_shift_response_length(nbits):
    """Client reads exactly ceil(nbits/8) TDO bytes for each required width.

    These are the same widths exercised at the E2E layer — we lock the
    framing contract first so a failure here cannot be confused with a
    server-side bug later.
    """
    nbytes = (nbits + 7) // 8
    tms    = b"\x00" * nbytes
    tdi    = b"\x00" * nbytes
    tdo_payload = bytes(((i + 1) & 0xFF) for i in range(nbytes))

    def server(srv):
        header = _recv_exact(srv, 10)
        assert header == b"shift:" + struct.pack("<I", nbits)
        _recv_exact(srv, 2 * nbytes)  # consume tms + tdi
        srv.sendall(tdo_payload)

    _, tdo, exc = _run_with_socketpair(
        lambda c: c.shift(nbits, tms, tdi),
        server,
    )
    assert exc is None, exc
    assert len(tdo) == nbytes
    assert tdo == tdo_payload


# ---------------------------------------------------------------------------
# Error-path tests: client must reject malformed input and server deviations.
# ---------------------------------------------------------------------------


def test_malformed_getinfo_raises():
    def server(srv):
        _recv_exact(srv, 8)
        srv.sendall(b"garbage\n")

    _, ret, exc = _run_with_socketpair(
        lambda c: c.getinfo(),
        server,
    )
    assert ret is None
    assert isinstance(exc, ValueError), "expected ValueError, got {!r}".format(exc)


def test_shift_tms_tdi_length_mismatch():
    """Client raises ValueError when tms length != ceil(nbits/8)."""
    sp_srv, sp_cli = socket.socketpair()
    client = None
    try:
        client = _MockXvcClient(sp_cli)
        with pytest.raises(ValueError):
            # nbits=9 -> needs 2 bytes, pass only 1
            client.shift(9, b"\xAA", b"\x00\x00")
        with pytest.raises(ValueError):
            client.shift(9, b"\xAA\x00", b"\x00")
    finally:
        sp_srv.close()
        if client is not None:
            client.close()
        else:
            sp_cli.close()
