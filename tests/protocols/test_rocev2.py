#-----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
#-----------------------------------------------------------------------------
# Description:
#   Unit and hardware-gated tests for pyrogue.protocols._RoCEv2.
#
#   The FPGA-facing metadata-bus codec (PD/MR/QP encoders/decoders and the
#   _roce_setup_connection / _roce_teardown transport helpers) now lives in
#   surf (surf.ethernet.roce._RoCEv2Protocol / _RoCEv2Engine) and is tested
#   there. What remains host-side in rogue — and is covered here — is:
#     1. Hardware-free (run in every CI matrix) — GID helpers, the
#        _ROCEV2_AVAILABLE guard, pmtu validation, and getChannel() wiring.
#     2. Hardware-gated (@pytest.mark.rocev2) — require an ibverbs device.
#        Skipped with a clear reason string when no device is present, never
#        silently passing.
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
import socket
from unittest.mock import MagicMock

import pytest

import rogue
import rogue.interfaces.stream
import pyrogue.protocols._RoCEv2 as _RoCEv2
from pyrogue.protocols._RoCEv2 import (
    _ip_to_gid_bytes,
    _gid_bytes_to_str,
    RoCEv2Server,
    RoCEv2ServerCfg,
    RoCEv2TransportCfg,
)


# xdist_group serializes all tests in this file onto one worker. Combined
# with the CI --dist loadfile flag this is belt-and-braces: one device,
# one worker. Keeps rxe0 from being opened by two workers simultaneously.
pytestmark = pytest.mark.xdist_group("rocev2")


# ---------------------------------------------------------------------------
# Hardware availability probe (imports the C++ extension; no device open yet)
# ---------------------------------------------------------------------------

def _ibverbs_available() -> bool:
    """Return True iff the rogue.protocols.rocev2 C++ extension imports."""
    try:
        import rogue.protocols.rocev2  # noqa: F401
        return True
    except ImportError:
        return False


rocev2_hw = pytest.mark.skipif(
    not _ibverbs_available(),
    reason=(
        "No ibverbs device available - load rdma_rxe "
        "(modprobe rdma_rxe) or attach a hardware RoCE NIC. "
        "Rogue must be built on Linux with libibverbs/rdma-core "
        "available at build and runtime."
    ),
)


# ---------------------------------------------------------------------------
# GID helpers
# ---------------------------------------------------------------------------

def test_ip_to_gid_bytes_layout():
    gid = _ip_to_gid_bytes("192.168.1.100")
    assert len(gid) == 16
    assert gid[0:10] == b'\x00' * 10
    assert gid[10:12] == b'\xff\xff'
    assert gid[12:16] == b'\xc0\xa8\x01\x64'


def test_gid_round_trip():
    s = _gid_bytes_to_str(_ip_to_gid_bytes("10.0.0.1"))
    # 8 groups of 4 hex chars + 7 colons = 39 chars
    assert len(s) == 39
    groups = s.split(':')
    assert len(groups) == 8
    assert all(len(g) == 4 for g in groups)
    # Last two groups encode the IPv4 big-endian
    assert groups[-2] == '0a00'
    assert groups[-1] == '0001'


def test_ip_to_gid_bytes_zero_address():
    """IPv4 0.0.0.0 maps to an IPv4-in-IPv6 GID with zeros in the last
    four bytes; the leading 10 zero bytes and the 0xFFFF marker stay
    put so the GID is well-formed even for an all-zero IPv4."""
    gid = _ip_to_gid_bytes("0.0.0.0")
    assert len(gid) == 16
    assert gid[0:10]  == b'\x00' * 10
    assert gid[10:12] == b'\xff\xff'
    assert gid[12:16] == b'\x00\x00\x00\x00'


def test_ip_to_gid_bytes_max_address():
    """IPv4 255.255.255.255 maps to all-ones in the last four bytes.
    A successful round-trip proves the helper doesn't sign-extend or
    truncate high bytes."""
    gid = _ip_to_gid_bytes("255.255.255.255")
    assert gid[12:16] == b'\xff\xff\xff\xff'


def test_ip_to_gid_bytes_invalid_raises():
    """Passing a non-IPv4 string (domain name, garbage, IPv6) must raise
    — the helper delegates to socket.inet_aton which raises OSError
    (socket.error is an alias)."""
    with pytest.raises((OSError, socket.error)):
        _ip_to_gid_bytes("not-an-ip")


# ---------------------------------------------------------------------------
# _ROCEV2_AVAILABLE guard
# ---------------------------------------------------------------------------

def test_rocev2_available_is_bool():
    assert isinstance(_RoCEv2._ROCEV2_AVAILABLE, bool)


def test_rocev2server_raises_import_error_when_unavailable(monkeypatch):
    monkeypatch.setattr(_RoCEv2, '_ROCEV2_AVAILABLE', False)
    with pytest.raises(ImportError) as excinfo:
        _RoCEv2.RoCEv2Server(
            rocev2Cfg=RoCEv2ServerCfg(ip='192.168.1.1', deviceName='dummy'),
            name='test',
        )
    msg = str(excinfo.value)
    assert "Linux build" in msg
    assert "libibverbs" in msg


@pytest.mark.parametrize("bad_pmtu", [-1, 0, 6, 7, 100])
def test_transport_cfg_rejects_out_of_range_pmtu(bad_pmtu):
    # pmtu validation lives in RoCEv2TransportCfg.__post_init__ (mirroring
    # completeConnection's invariant) so a bad cfg fails loudly at
    # construction — no ibverbs device needed.
    with pytest.raises(rogue.GeneralError) as excinfo:
        RoCEv2TransportCfg(pmtu=bad_pmtu)
    assert "pmtu" in str(excinfo.value)


@pytest.mark.parametrize("valid_pmtu", [1, 2, 3, 4, 5])
def test_transport_cfg_accepts_valid_pmtu(valid_pmtu):
    # Pin the accept side of the boundary so a future off-by-one in the
    # validator is caught.
    cfg = RoCEv2TransportCfg(pmtu=valid_pmtu)
    assert cfg.pmtu == valid_pmtu


# ---------------------------------------------------------------------------
# getChannel wiring
# ---------------------------------------------------------------------------

def test_get_channel_creates_filter_and_wires_server():
    # Build a bare object that has a _server attribute; bypass __init__
    # (which requires ibverbs).  Call getChannel via the unbound descriptor
    # so we do not need to instantiate RoCEv2Server.
    obj = MagicMock()
    obj._server = MagicMock()
    result = RoCEv2Server.getChannel(obj, 3)
    assert isinstance(result, rogue.interfaces.stream.Filter)
    # self._server >> filt must have invoked __rshift__ on _server
    assert obj._server.__rshift__.called


@pytest.mark.parametrize("channel", [0, 255])
def test_get_channel_accepts_edge_ids(channel):
    """The valid channel range is the 8-bit immediate field 0..255; both
    extremes must construct a Filter without raising."""
    obj = MagicMock()
    obj._server = MagicMock()
    result = RoCEv2Server.getChannel(obj, channel)
    assert isinstance(result, rogue.interfaces.stream.Filter)


@pytest.mark.parametrize("channel", [-1, 256, 1000])
def test_get_channel_rejects_out_of_range_ids(channel):
    """Out-of-range channel ids must raise a clear rogue.GeneralError up
    front rather than overflowing inside the Filter ctor."""
    obj = MagicMock()
    obj._server = MagicMock()
    with pytest.raises(rogue.GeneralError):
        RoCEv2Server.getChannel(obj, channel)


# ---------------------------------------------------------------------------
# Hardware-gated tests (skipped when no ibverbs device is present)
# ---------------------------------------------------------------------------

@pytest.mark.rocev2
@rocev2_hw
def test_rocev2_extension_importable():
    import rogue.protocols.rocev2 as _r
    assert _r is not None


@pytest.mark.rocev2
@rocev2_hw
def test_rocev2_default_constants():
    import rogue.protocols.rocev2 as _r
    assert isinstance(_r.DefaultMaxPayload, int)
    assert isinstance(_r.DefaultRxQueueDepth, int)
    assert _r.DefaultMaxPayload > 0
    assert _r.DefaultRxQueueDepth > 0


@pytest.mark.rocev2
@rocev2_hw
def test_rxe_server_fixture_is_live(rxe_server):
    """Sentinel: when rxe0 IS available this test MUST run (not skip).
    Guards against the silent-pass mode where the @rocev2_hw decorator
    wrongly evaluates True on a dev box without rxe0. If this test is
    PASSED, the hardware path is live.
    """
    assert rxe_server is not None
    assert rxe_server.getQpn() != 0


@pytest.mark.rocev2
@rocev2_hw
def test_get_channel_with_live_server(rxe_server):
    """getChannel returns a rogue.interfaces.stream.Filter wired
    downstream of the live rxe_server. Exercises the real `_server >> filt`
    path. Multiple channel indices keep the Filter constructor out of a
    single-index happy path.
    """
    shim = MagicMock()
    shim._server = rxe_server
    for channel_id in (0, 3, 15):
        filt = RoCEv2Server.getChannel(shim, channel_id)
        assert isinstance(filt, rogue.interfaces.stream.Filter)
