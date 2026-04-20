#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
"""End-to-end XVC wire-protocol tests.

Drives a real C++ `rogue.protocols.xilinx.Xvc` server (bound to port 0) via
the pure-stdlib `XvcClient` over a real TCP socket, with a `FakeJtag`
Python emulator wired into the stream graph as the downstream driver.

Covers: getinfo / settck / shift round-trips, chunking over supVecLen_,
port-0 + getPort() discovery, full session, clean teardown, unknown-command
handling, and in-process parallel-worker contention guard.
"""
import concurrent.futures
import socket
import threading
import time

import pytest

import pyrogue as pr
import rogue.protocols.xilinx as xvc_mod

from fake_jtag import FakeJtag
from xvc_client import XvcClient


# ---------------------------------------------------------------------------
# getinfo: round-trip
# ---------------------------------------------------------------------------
def test_getinfo_roundtrip(xvc_session):
    """getinfo: returns xvcServer_v1.0:<N>\\n."""
    _xvc, _fake, port = xvc_session
    with XvcClient(port=port) as cli:
        version, max_vec = cli.getinfo()
    assert version == "xvcServer_v1.0"
    assert isinstance(max_vec, int) and max_vec > 0
    # Deterministic value: XvcConnection::run reports maxVecLen_ which is
    # the maxMsgSize constant passed by Xvc::start() (hardcoded 32768).
    # NOT the (mtu - wordSize) / 2 formula (that is supVecLen_'s cap, used
    # only internally to chunk shifts).
    assert max_vec == 32768, f"expected max_vec=32768, got {max_vec}"


# ---------------------------------------------------------------------------
# settck: round-trip
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("period_ns", [1, 10, 100, 1000])
def test_settck_roundtrip(xvc_session, period_ns):
    """settck: echoes effective period as LE uint32.

    FakeJtag reports periodRaw=0 (UNKNOWN_PERIOD) so
    JtagDriver::setPeriodNs returns the requested period unchanged.
    """
    _xvc, _fake, port = xvc_session
    with XvcClient(port=port) as cli:
        # getinfo first so the initial drv_->query() path is already
        # primed when settck arrives (mirrors real Vivado session order).
        cli.getinfo()
        effective = cli.settck(period_ns)
    assert effective == period_ns, \
        f"settck({period_ns}) -> {effective}, expected echo of requested period"


# ---------------------------------------------------------------------------
# shift: parametrized widths
# ---------------------------------------------------------------------------
SHIFT_BIT_WIDTHS = [1, 7, 8, 9, 15, 16, 17, 32, 64]


def _deterministic_vectors(nbits):
    """Build reproducible TMS/TDI of length ceil(nbits/8)."""
    n = (nbits + 7) // 8
    tms = bytes((i * 37 + 0x11) & 0xFF for i in range(n))
    tdi = bytes((i * 53 + 0xAA) & 0xFF for i in range(n))
    return tms, tdi


@pytest.mark.parametrize("nbits", SHIFT_BIT_WIDTHS)
def test_shift_roundtrip(xvc_session, nbits):
    """shift returns ceil(nbits/8) bytes matching FakeJtag.expected_tdo."""
    _xvc, _fake, port = xvc_session
    tms, tdi = _deterministic_vectors(nbits)
    with XvcClient(port=port) as cli:
        cli.getinfo()
        tdo = cli.shift(nbits, tms, tdi)
    expected = FakeJtag.expected_tdo(nbits, tms, tdi)
    assert len(tdo) == (nbits + 7) // 8, \
        f"nbits={nbits}: got {len(tdo)} bytes, expected {(nbits+7)//8}"
    assert tdo == expected, f"nbits={nbits}: TDO mismatch"


# ---------------------------------------------------------------------------
# shift exceeding supVecLen_ exercises chunking loop
# ---------------------------------------------------------------------------
def test_shift_chunking(xvc_session):
    """nbits=100 exceeds supVecLen_*8 (32 bits default), forcing multiple sendVectors calls."""
    _xvc, fake, port = xvc_session
    nbits = 100  # > 32 bits -> at least 4 CMD_S iterations
    tms, tdi = _deterministic_vectors(nbits)
    with XvcClient(port=port) as cli:
        cli.getinfo()
        tdo = cli.shift(nbits, tms, tdi)
    assert len(tdo) == (nbits + 7) // 8 == 13
    assert tdo == FakeJtag.expected_tdo(nbits, tms, tdi)
    # Sanity: FakeJtag.calls should record >=2 CMD_S entries for this shift.
    shift_calls = [c for c in fake.calls if c[0] == "shift"]
    assert len(shift_calls) >= 2, \
        f"expected chunked CMD_S calls, got {shift_calls}"


# ---------------------------------------------------------------------------
# port-0 + getPort() is dynamic
# ---------------------------------------------------------------------------
def test_port_is_dynamic(xvc_session):
    """port-0 ctor yields a kernel-assigned port, not the Vivado default 2542."""
    _xvc, _fake, port = xvc_session
    assert port > 1024 and port != 2542, \
        f"port {port} should be kernel-assigned (not Vivado default 2542)"


# ---------------------------------------------------------------------------
# full session: getinfo -> settck -> multiple shift -> close
# ---------------------------------------------------------------------------
def test_full_session(xvc_session):
    """getinfo -> settck -> multiple shift -> close completes cleanly."""
    _xvc, _fake, port = xvc_session
    with XvcClient(port=port) as cli:
        version, max_vec = cli.getinfo()
        assert version == "xvcServer_v1.0"
        assert max_vec == 32768
        effective = cli.settck(100)
        assert effective == 100
        for nbits in (8, 32, 9):
            tms, tdi = _deterministic_vectors(nbits)
            tdo = cli.shift(nbits, tms, tdi)
            assert len(tdo) == (nbits + 7) // 8
            assert tdo == FakeJtag.expected_tdo(nbits, tms, tdi), \
                f"TDO mismatch at nbits={nbits}"


# ---------------------------------------------------------------------------
# clean teardown: _stop() < 500ms AND listening socket is unreachable after
# ---------------------------------------------------------------------------
# The event-driven shutdown guarantees the listening socket is closed and
# every XvcServer / XvcConnection worker is joined before _stop() returns.
# The C++ server thread is created via std::thread and is invisible to
# Python's threading.enumerate() (only Python-created or PyGILState_Ensure
# "Dummy-N" threads appear there) -- so a thread-name leak filter would be
# vacuous.  Assert the OBSERVABLE post-condition instead: after _stop(), the
# kernel-assigned port refuses new TCP connections.  Any leaked server thread
# would keep the listener alive and let connect() succeed.
def test_clean_teardown():
    """_stop() returns <500ms; listening port refuses new connections after."""
    xvc  = xvc_mod.Xvc(0)
    fake = FakeJtag()
    pr.streamConnect(xvc, fake)
    pr.streamConnect(fake, xvc)
    xvc._start()
    port = xvc.getPort()
    assert 0 < port < 65536
    try:
        with XvcClient(port=port) as cli:
            version, _ = cli.getinfo()
            assert version == "xvcServer_v1.0"
    finally:
        t0 = time.monotonic()
        xvc._stop()
        elapsed = time.monotonic() - t0

    # Event-driven shutdown contract: _stop() returns within 500ms.
    assert elapsed < 0.5, f"xvc._stop() took {elapsed:.3f}s (>0.5s budget)"

    # Listener must be gone — connect() should now fail (typically
    # ConnectionRefusedError).  Allow a brief settle window for the
    # kernel-side socket teardown.
    deadline   = time.monotonic() + 0.5
    refused    = False
    while time.monotonic() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                pass  # connect succeeded → listener still alive; retry
            time.sleep(0.05)
        except (ConnectionRefusedError, OSError):
            refused = True
            break
    assert refused, f"port {port} still accepting connections after _stop()"


# ---------------------------------------------------------------------------
# unknown 2-byte command prefix closes the connection cleanly
# ---------------------------------------------------------------------------
def test_unknown_command(xvc_session):
    """unknown 2-byte prefix drops the one connection without hanging.

    XvcConnection::run dispatches purely on the first 2 header bytes
    ('ge' / 'se' / 'sh') and throws "Unsupported message received" for
    any other prefix.  The 8 bytes of padding are therefore irrelevant
    to the dispatcher -- they exist only to make the send() a single
    segment.  The throw propagates to the connection worker's catch,
    which closes the socket; the server stays up and continues accepting.
    """
    _xvc, _fake, port = xvc_session

    # Connection #1 -- garbage prefix; expect server to drop us.
    s = socket.create_connection(("127.0.0.1", port), timeout=2.0)
    try:
        s.sendall(b"xx" + b"\x00" * 8)
        s.settimeout(2.0)
        try:
            data = s.recv(16)
        except (ConnectionResetError, ConnectionAbortedError):
            data = b""
        assert data == b"", f"server replied to garbage: {data!r}"
    finally:
        s.close()

    # Connection #2 -- server MUST still be alive and accepting.
    with XvcClient(port=port) as cli:
        version, _ = cli.getinfo()
        assert version == "xvcServer_v1.0"


# ---------------------------------------------------------------------------
# 4 concurrent Xvc instances never collide on ports
# ---------------------------------------------------------------------------
def test_parallel_workers():
    """In-process port-0 + getPort() contention guard.

    pytest-xdist exercises port-0 + getPort() ACROSS processes (the real
    CI mode); this test exercises it WITHIN a single process so a local
    developer can catch a regression without bringing up the full xdist
    harness.  4 worker threads each spin up an Xvc(0), run a getinfo,
    and collect their port.  A barrier keeps all instances alive until
    every port has been recorded, eliminating any TOCTOU window where
    the OS could recycle a released ephemeral port.
    """
    n_workers = 4
    barrier = threading.Barrier(n_workers, timeout=5.0)

    def _one(_i):
        xvc  = xvc_mod.Xvc(0)
        fake = FakeJtag()
        pr.streamConnect(xvc, fake)
        pr.streamConnect(fake, xvc)
        xvc._start()
        try:
            port = xvc.getPort()
            with XvcClient(port=port) as cli:
                version, _ = cli.getinfo()
            try:
                barrier.wait()
            except threading.BrokenBarrierError:
                pass
            return port, version
        finally:
            xvc._stop()

    with concurrent.futures.ThreadPoolExecutor(max_workers=n_workers) as pool:
        results = list(pool.map(_one, range(n_workers)))

    ports = [p for p, _ in results]
    assert len(set(ports)) == n_workers, f"port collision: {ports}"
    assert all(v == "xvcServer_v1.0" for _, v in results), \
        f"unexpected version(s): {[v for _, v in results]}"
