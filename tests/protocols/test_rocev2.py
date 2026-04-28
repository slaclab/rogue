#-----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
#-----------------------------------------------------------------------------
# Description:
#   Unit and hardware-gated tests for pyrogue.protocols._RoCEv2.
#
#   Two tiers of tests live here:
#     1. Hardware-free (run in every CI matrix) — pure Python arithmetic on
#        the metadata bus encoders/decoders, GID helpers, _ROCEV2_AVAILABLE
#        guard, _send_meta / _wait_resp / _roce_teardown (MagicMock engine),
#        and getChannel() wiring.
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
from unittest.mock import MagicMock, call

import pytest

import rogue
import rogue.interfaces.stream
import pyrogue.protocols._RoCEv2 as _RoCEv2
from pyrogue.protocols._RoCEv2 import (
    _ip_to_gid_bytes,
    _gid_bytes_to_str,
    _mk_bus,
    _encode_alloc_pd,
    _encode_alloc_mr,
    _encode_create_qp,
    _encode_modify_qp,
    _encode_err_qp,
    _encode_destroy_qp,
    _encode_dealloc_pd,
    _encode_dealloc_mr,
    _decode_resp_type,
    _decode_pd_resp,
    _decode_mr_resp,
    _decode_qp_resp,
    _send_meta,
    _wait_resp,
    _roce_setup_connection,
    _roce_teardown,
    RoCEv2Server,
    _METADATA_PD_T,
    _METADATA_MR_T,
    _METADATA_QP_T,
    _META_DATA_TX_BITS,
    _PD_KEY_B,
    _PD_HANDLER_B,
    _MR_KEY_B,
    _IBV_QPS_INIT,
    _IBV_QPS_RTR,
    _IBV_QPS_RTS,
)
# Response-word builders shared with tests/protocols/test_rocev2_corner_cases.py
# (hoisted to conftest.py to eliminate drift). pytest adds the conftest's
# directory to sys.path during collection, so the bare `conftest` import
# works without a package __init__.py.
from conftest import _pack_pd_ok, _pack_mr_ok, _pack_qp_ok


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


# ---------------------------------------------------------------------------
# _mk_bus low-level
# ---------------------------------------------------------------------------

def test_mk_bus_type_tag_position():
    # QP type = 2 (binary 10); bit 302 = 1, bit 301 = 0
    bus_qp = _mk_bus(_METADATA_QP_T, (0, 10))
    assert (bus_qp >> 302) & 1 == 1
    assert (bus_qp >> 301) & 1 == 0
    # PD type = 0; bits 302:301 = 00
    bus_pd = _mk_bus(_METADATA_PD_T, (0, 10))
    assert (bus_pd >> 301) & 0x3 == _METADATA_PD_T
    # MR type = 1; bits 302:301 = 01
    bus_mr = _mk_bus(_METADATA_MR_T, (0, 10))
    assert (bus_mr >> 301) & 0x3 == _METADATA_MR_T


def test_mk_bus_overflow_raises():
    # 302 bits of payload leaves only 1 bit for the 2-bit bus type tag
    with pytest.raises(rogue.GeneralError) as excinfo:
        _mk_bus(_METADATA_PD_T, (0, 302))
    assert "Bus type cannot fit" in str(excinfo.value)


# ---------------------------------------------------------------------------
# TX encoders
# ---------------------------------------------------------------------------

def test_encode_alloc_pd_fits_in_303_bits():
    bus = _encode_alloc_pd(0xDEADBEEF)
    assert bus < (1 << _META_DATA_TX_BITS)


def test_encode_alloc_pd_bus_type():
    bus = _encode_alloc_pd(0xABCDEF01)
    assert (bus >> 301) & 0x3 == _METADATA_PD_T


def test_encode_alloc_mr_bus_type_and_fits():
    bus = _encode_alloc_mr(
        pd_handler=0x11, laddr=0x2000, length=4096,
        lkey_part=0x3, rkey_part=0x4,
    )
    assert (bus >> 301) & 0x3 == _METADATA_MR_T
    assert bus < (1 << _META_DATA_TX_BITS)


def test_encode_create_qp_bus_type_and_fits():
    bus = _encode_create_qp(pd_handler=0x55)
    assert (bus >> 301) & 0x3 == _METADATA_QP_T
    assert bus < (1 << _META_DATA_TX_BITS)


def test_encode_modify_qp_bus_type_and_fits():
    bus = _encode_modify_qp(
        qpn=0x1234, attr_mask=0x1, qp_state=1, pmtu=5,
    )
    assert (bus >> 301) & 0x3 == _METADATA_QP_T
    assert bus < (1 << _META_DATA_TX_BITS)


def test_encode_err_qp_bus_type_and_fits():
    bus = _encode_err_qp(qpn=0x5678)
    assert (bus >> 301) & 0x3 == _METADATA_QP_T
    assert bus < (1 << _META_DATA_TX_BITS)


def test_encode_destroy_qp_bus_type_and_fits():
    bus = _encode_destroy_qp(qpn=0x9ABC)
    assert (bus >> 301) & 0x3 == _METADATA_QP_T
    assert bus < (1 << _META_DATA_TX_BITS)


def test_encode_dealloc_pd_and_mr_fit():
    assert _encode_dealloc_pd(0x1234) < (1 << _META_DATA_TX_BITS)
    assert _encode_dealloc_mr(0x1234, 0xAABB, 0xCCDD) < (1 << _META_DATA_TX_BITS)


# ---------------------------------------------------------------------------
# RX decoders
# ---------------------------------------------------------------------------

def test_decode_resp_type_matches_encoder():
    # The TX bus writes bus-type at [302:301]; the RX bus (276 bits) keeps
    # the same two-bit field at [275:274]. Shifting TX>>27 aligns TX with RX.
    shift = _META_DATA_TX_BITS - 276  # == 27
    assert _decode_resp_type(_encode_alloc_pd(0xABCDEF01) >> shift) \
        == _METADATA_PD_T
    assert _decode_resp_type(_encode_alloc_mr(0, 0, 0, 0, 0) >> shift) \
        == _METADATA_MR_T
    assert _decode_resp_type(_encode_create_qp(0) >> shift) \
        == _METADATA_QP_T


def test_decode_pd_resp_success_and_handler():
    # Layout (LSB convention, matches _RoCEv2.py comments):
    #   bits [31:0]   = pdKey
    #   bits [63:32]  = pdHandler
    #   bit  [64]     = successOrNot
    pd_handler = 0xDEADBEEF
    rx = (1 << (_PD_KEY_B + _PD_HANDLER_B)) | (pd_handler << _PD_KEY_B)
    success, handler = _decode_pd_resp(rx)
    assert success is True
    assert handler == pd_handler


def test_decode_pd_resp_failure():
    # Same rx but success bit cleared
    rx = 0
    success, _ = _decode_pd_resp(rx)
    assert success is False


def test_decode_mr_resp_success_and_keys():
    # Layout: rKey [31:0], lKey [63:32], successOrNot at the high end
    lkey = 0xABCD1234
    rkey = 0x5678DEAD
    # success_bit offset is computed in _RoCEv2._decode_mr_resp; reproduce:
    #   _MR_KEY_B + _MR_KEY_B + _MR_RKEYPART_B + _MR_LKEYPART_B
    #   + _MR_PDHANDLER_B + _MR_ACCFLAGS_B + _MR_LEN_B + _MR_LADDR_B
    success_bit = 32 + 32 + 31 + 31 + 32 + 8 + 32 + 64
    rx = (1 << success_bit) | (lkey << _MR_KEY_B) | rkey
    success, got_lkey, got_rkey = _decode_mr_resp(rx)
    assert success is True
    assert got_lkey == lkey
    assert got_rkey == rkey


def test_decode_qp_resp_success_and_qpn_and_state():
    # Layout: successOrNot bit 273, qpn [272:249] (24b), qpaQpState [216:213] (4b)
    qpn = 0x0ABCDE
    qp_state = _IBV_QPS_RTS  # 3
    rx = (1 << 273) | (qpn << 249) | (qp_state << 213)
    success, got_qpn, got_state = _decode_qp_resp(rx)
    assert success is True
    assert got_qpn == qpn
    assert got_state == qp_state


# ---------------------------------------------------------------------------
# _ROCEV2_AVAILABLE guard
# ---------------------------------------------------------------------------

def test_rocev2_available_is_bool():
    assert isinstance(_RoCEv2._ROCEV2_AVAILABLE, bool)


def test_rocev2server_raises_import_error_when_unavailable(monkeypatch):
    monkeypatch.setattr(_RoCEv2, '_ROCEV2_AVAILABLE', False)
    with pytest.raises(ImportError) as excinfo:
        _RoCEv2.RoCEv2Server(
            ip='192.168.1.1',
            deviceName='dummy',
            name='test',
        )
    msg = str(excinfo.value)
    assert "Linux build" in msg
    assert "libibverbs" in msg


@pytest.mark.parametrize("bad_pmtu", [-1, 0, 6, 7, 100])
def test_rocev2server_rejects_out_of_range_pmtu(monkeypatch, bad_pmtu):
    # Force the early-exit path so we exercise pmtu validation before any
    # ibverbs call.  pmtu validation runs after the _ROCEV2_AVAILABLE check
    # — pinning _ROCEV2_AVAILABLE to True keeps the validation reachable on
    # hosts without ibverbs.
    monkeypatch.setattr(_RoCEv2, '_ROCEV2_AVAILABLE', True)
    with pytest.raises(rogue.GeneralError) as excinfo:
        _RoCEv2.RoCEv2Server(
            ip='192.168.1.1',
            deviceName='dummy',
            pmtu=bad_pmtu,
            name='test',
        )
    assert "pmtu" in str(excinfo.value)


# ---------------------------------------------------------------------------
# Transport helpers (MagicMock RoceEngine)
# ---------------------------------------------------------------------------

def test_send_meta_rising_edge_sequence():
    engine = MagicMock()
    _send_meta(engine, 0xABCD)
    assert engine.SendMetaData.set.call_args_list == [
        call(0), call(1), call(0),
    ]
    assert engine.MetaDataTx.set.call_args == call(0xABCD)


def test_wait_resp_returns_rx_value():
    engine = MagicMock()
    engine.RecvMetaData.get.return_value = 1
    engine.MetaDataRx.get.return_value = 0xDEADBEEF
    assert _wait_resp(engine, timeout_s=0.5) == 0xDEADBEEF


def test_wait_resp_timeout_raises():
    engine = MagicMock()
    engine.RecvMetaData.get.return_value = 0
    with pytest.raises(rogue.GeneralError) as excinfo:
        _wait_resp(engine, timeout_s=0.1)
    assert "Timeout" in str(excinfo.value)


# ---------------------------------------------------------------------------
# Teardown
# ---------------------------------------------------------------------------

def test_roce_teardown_calls_all_four_steps():
    engine = MagicMock()
    engine.RecvMetaData.get.return_value = 1
    # QP success decode: bit 273 set; MR success decode: bit at
    # 32+32+31+31+32+8+32+64 = 262 set; PD success decode: bit 64 set.
    # We want all teardown steps to report ok=True so none warn.
    engine.MetaDataRx.get.return_value = (
        (1 << 273) | (1 << 262) | (1 << 64)
    )
    _roce_teardown(
        engine,
        fpga_qpn=0x001234,
        pd_handler=0x55,
        lkey=0x66,
        rkey=0x77,
    )
    # 4 metadata TX writes: ERR, DESTROY, MR-dealloc, PD-dealloc
    assert engine.MetaDataTx.set.call_count == 4
    assert engine.SendMetaData.set.called


def test_roce_teardown_skips_mr_pd_when_pd_handler_zero():
    engine = MagicMock()
    engine.RecvMetaData.get.return_value = 1
    engine.MetaDataRx.get.return_value = (1 << 273)
    _roce_teardown(engine, fpga_qpn=0x001234, pd_handler=0)
    # Only QP ERR + QP DESTROY when pd_handler == 0
    assert engine.MetaDataTx.set.call_count == 2


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


@pytest.mark.skip(
    reason="deferred — hardware skip-marker did not fire on GHA runner without "
           "rdma_rxe; revisit once a self-hosted runner with rdma_rxe is available."
)
@pytest.mark.rocev2
@rocev2_hw
def test_rocev2_server_init_with_mock_engine_and_live_device():
    """Construct RoCEv2Server against the real rxe0 device, with
    roceEngine=MagicMock() to bypass the surf.ethernet.roce._RoceEngine
    import inside RoCEv2Server.__init__.  Verifies the ibverbs setup path
    (Server.create via Boost.Python) runs end-to-end.
    """
    srv = RoCEv2Server(
        ip          ='10.0.0.1',        # arbitrary; not exercised without a peer bring-up
        deviceName  ='rxe0',
        ibPort      =1,
        gidIndex    =0,
        maxPayload  =9000,
        rxQueueDepth=256,
        roceEngine  =MagicMock(),
        name        ='test_rocev2_server_init',
    )
    try:
        # Smoke-level asserts: the server is built and exposes the expected
        # ibverbs-derived accessors. Do NOT assert specific GID / QPN values
        # — GID is MAC-derived and flaky across runner images.
        assert srv._server is not None
        assert srv._server.getQpn() != 0
        assert srv._server.getMrAddr() != 0
        assert srv._server.getMrRkey() != 0
    finally:
        # Best-effort teardown of the real ibverbs resources
        try:
            srv._server.stop()
        except Exception:
            pass


@pytest.mark.rocev2
@rocev2_hw
def test_roce_setup_connection_full_flow_against_live_server(rxe_server):
    """Drive the full 6-step PD/MR/QP metadata-bus setup against a
    MagicMock RoceEngine, using the live rxe_server fixture's real
    host_qpn/host_rq_psn/host_sq_psn/mr_laddr/mr_len values.
    """
    engine = MagicMock()
    engine.RecvMetaData.get.return_value = 1

    # Prefer a callable side_effect over a list — avoids StopIteration
    # masking the real decoder error.
    responses = [
        _pack_pd_ok(),
        _pack_mr_ok(),
        _pack_qp_ok(state=_IBV_QPS_INIT),
        _pack_qp_ok(state=_IBV_QPS_INIT),
        _pack_qp_ok(state=_IBV_QPS_RTR),
        _pack_qp_ok(state=_IBV_QPS_RTS),
    ]
    calls = {"n": 0}

    def _rx(*args, **kwargs):
        calls["n"] += 1
        if not responses:
            raise AssertionError(
                f"unexpected RX call #{calls['n']} — script exhausted "
                f"(setup_connection asked for more responses than PD/MR/QP*4)")
        return responses.pop(0)

    engine.MetaDataRx.get.side_effect = _rx

    fpga_qpn, lkey, pd_handler, rkey = _roce_setup_connection(
        engine,
        host_qpn   =rxe_server.getQpn(),
        host_rq_psn=rxe_server.getRqPsn(),
        host_sq_psn=rxe_server.getSqPsn(),
        mr_laddr   =rxe_server.getMrAddr(),
        mr_len     =9000 * 256,
        pmtu       =5,
    )
    # 6 TX writes, one per round-trip
    assert engine.MetaDataTx.set.call_count == 6
    # Values unpacked from our scripted responses
    assert fpga_qpn == 0x123456
    assert lkey     == 0xABCD1234
    assert rkey     == 0x5678DEAD
    assert pd_handler == 0xDEADBEEF


@pytest.mark.rocev2
@rocev2_hw
def test_get_channel_with_live_server(rxe_server):
    """getChannel returns a rogue.interfaces.stream.Filter wired
    downstream of the live rxe_server. Exercises the real `_server >> filt`
    path. Multiple channel indices keep the Filter constructor out of a
    single-index happy path.
    """
    # Use RoCEv2Server.getChannel as an unbound descriptor on a shim that
    # holds the live server in _server (matches the hardware-free test
    # at lines 333-342 but with rxe_server in place of MagicMock).
    shim = MagicMock()
    shim._server = rxe_server
    for channel_id in (0, 3, 15):
        filt = RoCEv2Server.getChannel(shim, channel_id)
        assert isinstance(filt, rogue.interfaces.stream.Filter)
    # Real server path: channel count is not directly observable on the Filter;
    # existence + type already proves the getChannel path executed.


@pytest.mark.rocev2
@rocev2_hw
def test_roce_teardown_with_live_server_resources(rxe_server):
    """Drive the 4-step teardown using real qpn/mr_addr/mr_rkey values
    from the live rxe_server, scripted MagicMock engine for the FPGA
    side. Mirrors the existing hardware-free
    test_roce_teardown_calls_all_four_steps at line 299 but with live
    resource values in place of the 0x001234/0x55/0x66/0x77 constants.
    """
    engine = MagicMock()
    engine.RecvMetaData.get.return_value = 1
    # All four teardown decode steps pass: QP ok (bit 273), MR ok (bit 262),
    # PD ok (bit 64) — same bit layout as existing hardware-free test
    # lines 305-307.
    engine.MetaDataRx.get.return_value = (
        (1 << 273) | (1 << 262) | (1 << 64)
    )
    _roce_teardown(
        engine,
        fpga_qpn   =rxe_server.getQpn(),
        pd_handler =0x55,          # host-side PD handler bookkeeping — opaque to teardown
        lkey       =0x66,          # host-side MR lkey bookkeeping
        rkey       =rxe_server.getMrRkey(),
    )
    # All four meta-bus rounds performed: QP-ERR, QP-DESTROY, MR-dealloc, PD-dealloc
    assert engine.MetaDataTx.set.call_count == 4
    assert engine.SendMetaData.set.called
