#-----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
#-----------------------------------------------------------------------------
# Description:
#   Corner-case tests for pyrogue.protocols._RoCEv2.
#
#   Every test in this file is hardware-FREE (MagicMock-only). There is NO
#   hardware-gated pytest marker, NO hardware-skip decorator, NO session
#   rxe-device fixture consumption, and NO xdist-group pytestmark
#   declaration — that last omission is deliberate: the sibling
#   test_rocev2.py file serializes onto one xdist worker because it shares
#   the single rxe0 device; this file has no such constraint and gets full
#   -n auto parallelism.
#
#   ImportError coverage (when _ROCEV2_AVAILABLE=False) is already provided
#   by test_rocev2.py::test_rocev2server_raises_import_error_when_unavailable
#   and is not duplicated here.
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
from unittest.mock import MagicMock, call

import pytest

import rogue
import rogue.interfaces.stream
import pyrogue.protocols._RoCEv2 as _rce
from pyrogue.protocols._RoCEv2 import (
    _decode_resp_type,
    _decode_pd_resp,
    _decode_mr_resp,
    _decode_qp_resp,
    _wait_resp,
    _roce_setup_connection,
    _roce_teardown,
    _encode_alloc_pd,
    _encode_alloc_mr,
    _encode_create_qp,
    _encode_modify_qp,
    _encode_err_qp,
    _encode_destroy_qp,
    _encode_dealloc_pd,
    _send_meta,
    _mk_bus,
    _ip_to_gid_bytes,
    RoCEv2Server,
    _META_DATA_TX_BITS,
    _METADATA_PD_T,
    _METADATA_MR_T,
    _METADATA_QP_T,
    _PD_KEY_B,
    _PD_HANDLER_B,
    _MR_KEY_B,
    _IBV_QP_STATE,
    _IBV_QPS_RESET,
    _IBV_QPS_INIT,
    _IBV_QPS_RTR,
    _IBV_QPS_RTS,
    _IBV_QPS_ERR,
    _REQ_QP_CREATE,
    _REQ_QP_DESTROY,
    _REQ_QP_MODIFY,
    _QP_REQTYPE_B,
)
from conftest import (
    _pack_pd_ok,
    _pack_mr_ok,
    _pack_qp_ok,
    _pack_pd_fail,
    _pack_mr_fail,
    _pack_qp_fail,
    _pack_unknown_type,
)


# ---------------------------------------------------------------------------
# Shared helpers for the rollback-matrix tests below.
#
# _accelerate_time monkeypatches pyrogue.protocols._RoCEv2._time so _wait_resp
# never waits on wall-clock.  Required when a test scripts a _wait_resp that
# must time out (timeout_s > 0 would otherwise block), AND when a test wants
# the happy-path _wait_resp's 20 ms zero-probe loop to return immediately
# rather than sleeping for the probe duration on every call.
#
# _script_rx returns a callable side_effect for engine.MetaDataRx.get that
# pops responses in order and raises a clear AssertionError (NOT
# StopIteration, which MagicMock would otherwise emit) when the script is
# exhausted — the raise makes script-length mismatches show up as failures
# pinned to the unexpected call, not as a downstream decoder error.
# ---------------------------------------------------------------------------

def _accelerate_time(monkeypatch):
    """Replace _rce._time.monotonic / sleep so _wait_resp deadlines fire
    immediately without real wall-clock sleep.  Must be called inside a test
    that also uses pytest's `monkeypatch` fixture."""
    fake_clock = {"t": 0.0}

    def _fake_monotonic():
        fake_clock["t"] += 100.0
        return fake_clock["t"]

    def _fake_sleep(_s):
        return None

    monkeypatch.setattr(_rce._time, "monotonic", _fake_monotonic)
    monkeypatch.setattr(_rce._time, "sleep", _fake_sleep)


def _script_rx(*responses, name="rx"):
    """Return a callable side_effect that pops from `responses` in order and
    raises AssertionError on exhaustion — never StopIteration.  Keeps a
    visible failure pinned to the unexpected call rather than masking as a
    decoder error downstream.  `name` is echoed into the error message to
    disambiguate when multiple scripts are in play."""
    remaining = list(responses)
    calls = {"n": 0}

    def _rx(*args, **kwargs):
        calls["n"] += 1
        if not remaining:
            raise AssertionError(
                f"unexpected {name} call #{calls['n']} — script exhausted "
                f"(test expected exactly {len(responses)} MetaDataRx reads)")
        return remaining.pop(0)

    return _rx

# ---------------------------------------------------------------------------
# Decode-failure matrix — each decoder returns success=False when the success
# bit is cleared, remaining fields still decoded from the packed word.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "decoder,packer",
    [
        (_decode_pd_resp, _pack_pd_fail),
        (_decode_mr_resp, _pack_mr_fail),
        (_decode_qp_resp, _pack_qp_fail),
    ],
    ids=["pd", "mr", "qp"],
)
def test_decode_resp_success_false(decoder, packer):
    """Each decoder returns success=False when the success bit is cleared.
    The first element of every decoder tuple is the success bool;
    remaining elements are still decoded from the packed payload."""
    rx = packer()
    result = decoder(rx)
    # Every decoder returns (success, ...) — first element is the bool.
    assert result[0] is False
    # Remaining fields are decoded (not masked to zero) — prove at least one
    # non-zero downstream field to distinguish "success=False with payload"
    # from "all-zero word".
    assert len(result) >= 2  # PD has 2 fields; MR/QP have 3
    # At least one payload field is non-zero (the default packer values are
    # explicitly non-zero: pd_handler=0xDEADBEEF, lkey/rkey/qpn/state all
    # non-zero), confirming the packer preserved payload alongside the
    # cleared success bit.
    assert any(x != 0 for x in result[1:])


# ---------------------------------------------------------------------------
# Unknown resp_type value (tag=3 is reserved / unused).
# _decode_resp_type does NOT raise — it returns the raw 2-bit tag. The
# "unexpected type" raise lives one layer up in _roce_setup_connection at
# lines 525-528. Two tests cover both layers.
# ---------------------------------------------------------------------------

def test_decode_resp_type_unknown_returns_three():
    """Unit: _decode_resp_type on a resp_type=3 word returns 3 — no raise.
    The unknown-type branch lives one layer up in _roce_setup_connection,
    not in the decoder itself."""
    rx = _pack_unknown_type()
    assert _decode_resp_type(rx) == 3


def test_setup_connection_raises_on_unexpected_resp_type():
    """Integration: when the first RX word has resp_type=3 instead of the
    expected PD type, _roce_setup_connection raises rogue.GeneralError
    with 'Expected PD response' in the message (verified against the
    _decode_resp_type check inside _roce_setup_connection)."""
    engine = MagicMock()
    engine.RecvMetaData.get.return_value = 1
    engine.MetaDataRx.get.return_value = _pack_unknown_type()
    with pytest.raises(rogue.GeneralError) as excinfo:
        _roce_setup_connection(
            engine,
            host_qpn=1, host_rq_psn=0, host_sq_psn=0,
            mr_laddr=0x1000, mr_len=4096, pmtu=5,
        )
    assert "Expected PD response" in str(excinfo.value)


# ---------------------------------------------------------------------------
# _wait_resp timeout — extends the sibling test_wait_resp_timeout_raises
# which only checked 'Timeout'. This test matches all three substrings from
# the actual message emitted by _wait_resp on deadline expiry.
# ---------------------------------------------------------------------------

def test_wait_resp_timeout_exact_message():
    """_wait_resp(engine, timeout_s=0.05) raises rogue.GeneralError whose
    message contains '_wait_resp' (call tag), 'Timeout', and
    'RecvMetaData never went to 1' (the full detail line emitted by
    _wait_resp on deadline expiry). timeout_s=0.05 keeps the test fast (no
    production-code seam needed — _wait_resp already takes timeout_s as a
    kwarg)."""
    engine = MagicMock()
    engine.RecvMetaData.get.return_value = 0  # firmware never completes
    with pytest.raises(rogue.GeneralError) as excinfo:
        _wait_resp(engine, timeout_s=0.05)
    msg = str(excinfo.value)
    assert "_wait_resp" in msg
    assert "Timeout" in msg
    assert "RecvMetaData never went to 1" in msg


# ---------------------------------------------------------------------------
# _roce_teardown continues through subsequent steps when an intermediate
# step times out. Uses a MagicMock-based log object (not the pytest
# log-capture fixture) to match the sibling-test style. The timeout is
# produced by a callable side_effect on RecvMetaData.get that returns 0 for
# the MR-dealloc poll only, and 1 elsewhere — this forces _wait_resp to raise
# on step 3, which the teardown's try/except around the MR-dealloc _wait_resp
# catches and logs a warning, then proceeds to step 4 (PD dealloc).
#
# Time acceleration: _roce_teardown passes timeout_s=3.0 to _wait_resp for
# the MR-dealloc step, which would produce a real 3-second wall-clock wait.
# We monkeypatch _time.monotonic + _time.sleep on the _RoCEv2 module so the
# deadline triggers immediately.
# ---------------------------------------------------------------------------

def test_teardown_continues_on_intermediate_timeout(monkeypatch):
    """_roce_teardown continues to subsequent steps when one _wait_resp
    times out. Proves that all 4 TX writes land (ERR, DESTROY, MR-dealloc,
    PD-dealloc) and log.warning was called on the timed-out step.

    Test uses the same decoded-success word as the sibling
    test_roce_teardown_calls_all_four_steps (ok=True on every step), so the
    non-timeout steps decode cleanly; only the MR-dealloc step times out via
    a scripted RecvMetaData.get returning 0 for that phase."""
    import pyrogue.protocols._RoCEv2 as _rce

    # Time acceleration: replace _time.sleep with no-op and _time.monotonic
    # with a fast counter so the 3.0-second deadline inside _wait_resp
    # triggers on the first check rather than after 3 real seconds.
    fake_clock = {"t": 0.0}

    def _fake_monotonic():
        # Advance the clock by a large amount every call, so any deadline
        # of the form `_time.monotonic() + timeout_s` is exceeded on the
        # very next iteration of the timed loop.
        fake_clock["t"] += 100.0
        return fake_clock["t"]

    def _fake_sleep(_s):
        # No-op: tests must not block on real wall-clock sleeps.
        return None

    monkeypatch.setattr(_rce._time, "monotonic", _fake_monotonic)
    monkeypatch.setattr(_rce._time, "sleep", _fake_sleep)

    engine = MagicMock()
    # Same all-steps-success RX word as the sibling teardown test — bit 273
    # (QP success), bit 262 (MR success), bit 64 (PD success) all set. Every
    # non-timeout step decodes ok=True.
    engine.MetaDataRx.get.return_value = (
        (1 << 273) | (1 << 262) | (1 << 64)
    )

    # Script RecvMetaData.get to time out on the 3rd step (MR dealloc).
    # _roce_teardown has 4 _wait_resp calls (steps 1-4). Each call polls
    # RecvMetaData.get multiple times; to time out step 3 we must return 0
    # for every poll on that step. We track the current step via a counter
    # incremented on each SendMetaData.set(1) rising edge (exactly one per
    # _send_meta call, hence one per teardown step).
    phase = {"send_count": 0}

    def _bump_on_write_to_one(value):
        # _send_meta writes 0, then after MetaDataTx.set, writes 1 then 0.
        # Count the rising-edge (the write-1) to know which phase we're in.
        # NOTE: MagicMock records call_args_list / call_count regardless of
        # side_effect; we do NOT call the underlying mock method here —
        # doing so would re-invoke this same side_effect and recurse
        # infinitely.
        if value == 1:
            phase["send_count"] += 1

    engine.SendMetaData.set.side_effect = _bump_on_write_to_one

    def _recv_get(*args, **kwargs):
        # During step 3 (MR dealloc), return 0 forever → _wait_resp times out.
        if phase["send_count"] == 3:
            return 0
        return 1

    engine.RecvMetaData.get.side_effect = _recv_get

    log = MagicMock()
    _roce_teardown(
        engine,
        fpga_qpn=0x001234,
        pd_handler=0x55,
        lkey=0x66,
        rkey=0x77,
        log=log,
    )
    # All four teardown TX writes landed despite the step-3 timeout.
    assert engine.MetaDataTx.set.call_count == 4
    # At least one warning was logged (the MR-dealloc timeout path in
    # _roce_teardown).
    assert log.warning.called, (
        "log.warning must be called on the timed-out step"
    )


# ---------------------------------------------------------------------------
# Partial-setup rollback.  When PD alloc succeeds and a later stage fails,
# _roce_setup_connection must deallocate every resource it allocated before
# re-raising so the FPGA is not left with a stranded PD / MR / QP.  The
# rollback lives in the try/except wrapper around stages 2-6 in
# _RoCEv2.py::_roce_setup_connection.
# ---------------------------------------------------------------------------


def test_partial_setup_rollback_on_mr_failure():
    """When PD alloc succeeds and MR alloc fails, _roce_setup_connection:
        - raises rogue.GeneralError with 'MR allocation failed' in the
          message
        - emits exactly 3 TX writes: PD-alloc, MR-alloc, PD-dealloc (the
          rollback write)
        - does NOT emit a QP-create or MR-dealloc TX write (no QP exists;
          no MR was successfully allocated)."""
    engine = MagicMock()
    engine.RecvMetaData.get.return_value = 1
    engine.MetaDataRx.get.side_effect = [
        _pack_pd_ok(pd_handler=0xDEAD),
        _pack_mr_fail(),
        # The rollback's PD-dealloc _wait_resp also reads MetaDataRx; give
        # it an ok response so the rollback path doesn't hit StopIteration
        # from an exhausted side_effect list (the rollback would still
        # proceed via the best-effort try/except, but feeding a real
        # response keeps the test's intent about the rollback path clear).
        _pack_pd_ok(pd_handler=0xDEAD),
    ]
    with pytest.raises(rogue.GeneralError) as excinfo:
        _roce_setup_connection(
            engine,
            host_qpn=1, host_rq_psn=0, host_sq_psn=0,
            mr_laddr=0x1000, mr_len=4096, pmtu=5,
        )
    assert "MR allocation failed" in str(excinfo.value)
    # 3 TX writes: PD alloc + MR alloc (failing) + PD dealloc (rollback).
    # No QP-create TX: the MR failure aborts before stage 3.
    assert engine.MetaDataTx.set.call_count == 3


# ---------------------------------------------------------------------------
# Illegal QP state-machine transitions. Python layer is stateless; the FPGA
# enforces the state machine and replies with success=False. The test drives
# encoder + _send_meta + _wait_resp + _decode_qp_resp directly (not via
# _roce_setup_connection) because the illegal-transition scenario exists
# OUTSIDE the strict 6-step setup flow.
# ---------------------------------------------------------------------------

def test_illegal_qp_transition_reports_failure():
    """Calling _encode_err_qp on a qpn that the FPGA considers illegal
    (e.g. never created) returns a metadata-bus word that, when
    round-tripped, decodes to success=False. Python does not enforce the
    state machine — the test verifies the caller correctly observes FPGA
    rejection via the decoded success bit."""
    engine = MagicMock()
    engine.RecvMetaData.get.return_value = 1
    engine.MetaDataRx.get.return_value = _pack_qp_fail(
        qpn=0xDEADBE, state=_IBV_QPS_INIT,
    )

    bus = _encode_err_qp(qpn=0xDEADBE)
    _send_meta(engine, bus)
    rx = _wait_resp(engine, timeout_s=0.5)
    ok, qpn, state = _decode_qp_resp(rx)
    assert ok is False
    assert qpn == 0xDEADBE
    # FPGA reports its ACTUAL current state (INIT), not the requested state
    # (ERR).
    assert state == _IBV_QPS_INIT


# ---------------------------------------------------------------------------
# Double modify_qp (INIT → RTR, then RTR → RTR). The second call is an
# illegal no-op from the FPGA's state-machine perspective. FPGA replies
# with success=False and returns its current state.
# ---------------------------------------------------------------------------

def test_double_modify_qp_reports_failure():
    """Two successive modify_qp calls targeting the same state (RTR → RTR).
    First succeeds (ok=True, state=RTR); second fails (ok=False) and the
    returned state stays at RTR (not a silent corruption to a different
    state)."""
    engine = MagicMock()
    engine.RecvMetaData.get.return_value = 1

    responses = [
        _pack_qp_ok(qpn=0x111111, state=_IBV_QPS_RTR),    # 1st: RTR ok
        _pack_qp_fail(qpn=0x111111, state=_IBV_QPS_RTR),  # 2nd: fail, RTR
    ]
    calls = {"n": 0}

    def _rx(*args, **kwargs):
        calls["n"] += 1
        if not responses:
            raise AssertionError(
                f"unexpected RX call #{calls['n']} — script exhausted "
                f"(test expected only 2 modify_qp round-trips)")
        return responses.pop(0)

    engine.MetaDataRx.get.side_effect = _rx

    qpn = 0x111111
    # First modify_qp: INIT → RTR. Per _encode_modify_qp the kwargs for
    # RTR include dqpn/rq_psn; placeholder values are fine since we only
    # need the encoder to produce a well-formed bus word.
    bus1 = _encode_modify_qp(
        qpn=qpn, attr_mask=0x1, qp_state=_IBV_QPS_RTR, pmtu=5,
    )
    _send_meta(engine, bus1)
    ok1, _, state1 = _decode_qp_resp(_wait_resp(engine, timeout_s=0.5))
    assert ok1 is True
    assert state1 == _IBV_QPS_RTR

    # Second modify_qp: RTR → RTR (illegal no-op).
    bus2 = _encode_modify_qp(
        qpn=qpn, attr_mask=0x1, qp_state=_IBV_QPS_RTR, pmtu=5,
    )
    _send_meta(engine, bus2)
    ok2, _, state2 = _decode_qp_resp(_wait_resp(engine, timeout_s=0.5))
    assert ok2 is False
    assert state2 == _IBV_QPS_RTR  # unchanged — not silently corrupted


# ---------------------------------------------------------------------------
# Resource bounds.
#   Part A: _encode_alloc_mr with zero-length, unit, common, max 32-bit
#           length — all fit in _META_DATA_TX_BITS.
#   Part B: _encode_alloc_mr with length > 32-bit silently masks to 0
#           (_mk_bus masks each field with (1 << width) - 1 where
#           _MR_LEN_B = 32).
#   Part C: RoCEv2Server.getChannel with edge channel_ids — in-range
#           (0..255) ids return rogue.interfaces.stream.Filter; out-of-
#           range ids raise rogue.GeneralError (bounds enforced by the
#           Python wrapper, matching the 8-bit channel field in the RDMA
#           immediate value).
#
# Note: _mk_bus overflow ("Bus type cannot fit") is already covered by the
# sibling test_mk_bus_overflow_raises at test_rocev2.py:136-140. Not
# duplicated here.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "length",
    [0, 1, 4096, (1 << 32) - 1],
    ids=["zero", "unit", "common", "max32"],
)
def test_encode_alloc_mr_length_bounds_fit(length):
    """Zero, unit, common-page, and max-32-bit lengths all encode to a bus
    word that fits in _META_DATA_TX_BITS bits."""
    bus = _encode_alloc_mr(
        pd_handler=0x1, laddr=0, length=length, lkey_part=0, rkey_part=0,
    )
    assert 0 <= bus < (1 << _META_DATA_TX_BITS)


def test_encode_alloc_mr_length_overflow_silently_truncated():
    """Length >= 2**32 is silently masked by _mk_bus to 0. This documents
    existing encoder behavior (not a bug — FPGA-side protocol is 32-bit).
    Assertion: bus(length=2**32) equals bus(length=0)."""
    bus_overflow = _encode_alloc_mr(
        pd_handler=0x1, laddr=0, length=(1 << 32),
        lkey_part=0, rkey_part=0,
    )
    bus_zero = _encode_alloc_mr(
        pd_handler=0x1, laddr=0, length=0, lkey_part=0, rkey_part=0,
    )
    assert bus_overflow == bus_zero


@pytest.mark.parametrize(
    "channel_id",
    [0, 1, 255],
    ids=["min", "one", "uint8-max"],
)
def test_get_channel_accepts_edge_indices(channel_id):
    """RoCEv2Server.getChannel returns a rogue.interfaces.stream.Filter
    for every in-range channel_id (0..255, the bit-width of the RDMA
    immediate-value channel field). Uses unbound-descriptor invocation on
    a MagicMock shim to bypass __init__ (which requires ibverbs),
    mirroring the sibling test_get_channel_creates_filter_and_wires_server
    pattern at test_rocev2.py:343-352."""
    shim = MagicMock()
    shim._server = MagicMock()
    filt = RoCEv2Server.getChannel(shim, channel_id)
    assert isinstance(filt, rogue.interfaces.stream.Filter)


@pytest.mark.parametrize(
    "bad_channel",
    [-1, 256, 1 << 16],
    ids=["negative", "above-uint8", "oversize"],
)
def test_get_channel_rejects_out_of_range(bad_channel):
    """getChannel raises rogue.GeneralError for channel ids outside 0..255
    — the RDMA immediate value only has 8 bits for the channel field
    (Server.cpp runThread decodes `wc.imm_data & 0xFF`), so an out-of-
    range caller id can never be observed on the wire."""
    shim = MagicMock()
    shim._server = MagicMock()
    with pytest.raises(rogue.GeneralError) as excinfo:
        RoCEv2Server.getChannel(shim, bad_channel)
    assert "channel" in str(excinfo.value).lower()


def test_get_channel_multiple_subscribers_return_distinct_filters():
    """Two getChannel calls with the same channel_id must return two
    distinct Filter objects so downstream code can subscribe multiple
    independent consumers to the same RDMA-immediate channel id. If the
    wrapper cached and reused a Filter, a late subscriber would miss
    frames that had already been forwarded to the earlier one."""
    shim = MagicMock()
    shim._server = MagicMock()
    f1 = RoCEv2Server.getChannel(shim, 3)
    f2 = RoCEv2Server.getChannel(shim, 3)
    assert f1 is not f2
    # Both must be wired downstream of the same _server via __rshift__;
    # assert the call count so a silent no-op on the second call would fail.
    assert shim._server.__rshift__.call_count == 2


# ---------------------------------------------------------------------------
# Decoder completeness — every resp_type tag (0..3) and every qp_state
# nibble (0..15) round-trips through _decode_resp_type / _decode_qp_resp.
# The parametric sweeps close the gap between the existing single-tag and
# single-state tests in test_rocev2.py and the resp_type=3 / state-specific
# cases already covered above.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "tag,expected",
    [(_METADATA_PD_T, 0), (_METADATA_MR_T, 1), (_METADATA_QP_T, 2), (3, 3)],
    ids=["pd", "mr", "qp", "reserved"],
)
def test_decode_resp_type_all_four_tags(tag, expected):
    """_decode_resp_type returns the raw 2-bit tag at bits [275:274] for
    every one of the four encodings (PD=0, MR=1, QP=2, reserved=3). The
    reserved tag is not a raise in the decoder itself — the unknown-type
    raise lives one layer up in _roce_setup_connection."""
    rx = (tag & 0x3) << 274
    assert _decode_resp_type(rx) == expected


def test_decode_pd_resp_all_zero_word():
    """_decode_pd_resp(rx=0) returns (False, 0). Documents the
    empty-response boundary: both the success bit (64) and the pd_handler
    field ([63:32]) are zero. Protects against a future refactor that
    computes the success bit from a different offset and silently reports
    success=True on a zero word."""
    success, pd_handler = _decode_pd_resp(0)
    assert success is False
    assert pd_handler == 0


@pytest.mark.parametrize("state", list(range(16)), ids=[f"s{n}" for n in range(16)])
def test_decode_qp_resp_state_nibble_full_range(state):
    """_decode_qp_resp cleanly extracts every value 0..15 from the 4-bit
    qpaQpState field at [216:213]. The sibling test in test_rocev2.py only
    checks state=_IBV_QPS_RTS; this sweep ensures the mask doesn't bleed
    into neighboring bits for any value in the nibble — including the
    handful of values (5, 7, 9..15) that have no named ibverbs constant
    but could appear if the FPGA emits an unexpected state."""
    rx = (1 << 273) | (0x123456 << 249) | (state << 213)
    ok, qpn, got_state = _decode_qp_resp(rx)
    assert ok is True
    assert qpn == 0x123456
    assert got_state == state


def test_decode_mr_resp_keys_at_max_uint32():
    """_decode_mr_resp cleanly extracts 32-bit max lkey and rkey values —
    the sibling test uses values that happen to have high bits clear, so
    this test pins the top-of-range round-trip against mask errors."""
    lkey = 0xFFFFFFFF
    rkey = 0xFFFFFFFF
    success_bit = 32 + 32 + 31 + 31 + 32 + 8 + 32 + 64
    rx = (1 << success_bit) | (lkey << _MR_KEY_B) | rkey
    success, got_lkey, got_rkey = _decode_mr_resp(rx)
    assert success is True
    assert got_lkey == lkey
    assert got_rkey == rkey


# ---------------------------------------------------------------------------
# Encoder completeness — _mk_bus boundary, field masking, and round-trip
# identity between the modify-QP-to-ERR helper and the generic modify_qp
# encoder.
# ---------------------------------------------------------------------------

def test_mk_bus_at_max_payload_bits_fits():
    """_mk_bus with exactly 301 bits of payload fields (the maximum that
    leaves 2 reserved bits for the bus-type tag at [302:301]) succeeds
    without raising. The sibling test_mk_bus_overflow_raises at
    test_rocev2.py:141-145 proves 302 bits DOES raise — this test pins the
    accept side of the boundary so a future off-by-one in the capacity
    check is caught by at least one of the pair."""
    bus = _mk_bus(_METADATA_PD_T, (0, 301))
    assert bus < (1 << _META_DATA_TX_BITS)
    # Bus type tag still lands in [302:301] — payload did not displace it.
    assert (bus >> 301) & 0x3 == _METADATA_PD_T


def test_mk_bus_value_exceeds_field_width_is_masked():
    """_mk_bus masks each field value with ((1<<width)-1) so a caller that
    passes a too-wide value produces the same bus as passing the masked
    value. This is the firmware convention (BusStructs.py slice_vec is a
    fixed-width shift-and-mask); tests pin it so a later 'raise on
    oversized' refactor isn't applied silently."""
    # 33-bit value in a 32-bit field: top bit is discarded.
    too_big = (1 << 33) | 0xDEAD
    masked  = 0xDEAD
    bus_a = _mk_bus(_METADATA_PD_T, (too_big, 32))
    bus_b = _mk_bus(_METADATA_PD_T, (masked,  32))
    assert bus_a == bus_b


def test_mk_bus_field_order_puts_last_field_at_bit_zero():
    """_mk_bus concatenates fields MSB-first within the used region: the
    FIRST-listed field occupies the top of the payload window, the
    LAST-listed field lands at bit 0. A reversed field order would
    silently swap field meanings on the wire — pin the invariant."""
    # Two 4-bit fields: first=0xA, second=0x5. Concatenation yields
    # (0xA << 4) | 0x5 = 0xA5; the last field's LSB must be at bit 0.
    bus = _mk_bus(_METADATA_PD_T, (0xA, 4), (0x5, 4))
    assert bus & 0x0F == 0x5       # second field at [3:0]
    assert (bus >> 4) & 0x0F == 0xA  # first field at [7:4]


def test_encode_alloc_pd_sets_allocornot_bit_at_expected_position():
    """_encode_alloc_pd places allocOrNot=1 at bit
    (_PD_KEY_B + _PD_HANDLER_B) = 64 of the TX bus. The TX bit layout is
    the SAME as the RX decoder convention at bits [64:0] (low bits are
    LSB-aligned in both 303-bit and 276-bit buses — only the bus-type
    tag moves). A regression that relocates the alloc/success bit would
    break both the request side and the RX decoder alignment."""
    bus = _encode_alloc_pd(pd_key=0xDEADBEEF)
    assert (bus >> (_PD_KEY_B + _PD_HANDLER_B)) & 1 == 1
    # pd_key lands at [63:32] of the TX payload (same offset as the RX
    # decoder's pdHandler readback — the field ordering mirrors the
    # RX layout deliberately).
    assert (bus >> _PD_KEY_B) & ((1 << _PD_HANDLER_B) - 1) == 0xDEADBEEF


def test_encode_dealloc_pd_clears_allocornot_bit():
    """Complementary to the alloc test: _encode_dealloc_pd writes
    allocOrNot=0 at bit (_PD_KEY_B + _PD_HANDLER_B) and carries the
    pd_handler payload at [63:32] (pdKey don't-care, set to 0). A
    regression that left the allocOrNot bit high on the dealloc path
    would cause the firmware to treat a teardown as an alloc request."""
    bus = _encode_dealloc_pd(pd_handler=0xDEADBEEF)
    assert (bus >> (_PD_KEY_B + _PD_HANDLER_B)) & 1 == 0
    # pd_handler at [63:32] — _encode_dealloc_pd passes (pd_handler, 32)
    # as the last field, which lands at bit 0 in the payload. But per
    # the LSB-aligned MSB-first layout the third field (pd_handler) is at
    # [31:0], and the second (pdKey=0) is at [63:32]. Verify handler at
    # the LOW bits via a direct mask.
    assert bus & ((1 << _PD_HANDLER_B) - 1) == 0xDEADBEEF


def test_encode_err_qp_is_modify_qp_with_err_state_and_state_mask():
    """_encode_err_qp is a convenience wrapper over _encode_modify_qp with
    attr_mask=_IBV_QP_STATE, qp_state=_IBV_QPS_ERR, pmtu=1. Pin the
    identity so a future change to one helper that isn't mirrored in the
    other is caught. Equivalent encodings guarantee the rollback and
    teardown paths agree on the wire format of a QP→ERR request."""
    qpn = 0x0ABCDE
    assert _encode_err_qp(qpn) == _encode_modify_qp(
        qpn, _IBV_QP_STATE, _IBV_QPS_ERR, 1)


def test_encode_destroy_qp_sets_req_type_to_destroy():
    """_encode_destroy_qp places _REQ_QP_DESTROY in the req_type field at
    the top of the QP payload window — distinguishable from CREATE and
    MODIFY. Extract the top 2 bits of the payload (just below the bus
    type tag) and confirm the correct req_type reaches the wire."""
    bus = _encode_destroy_qp(qpn=0x123456)
    # Bus layout: bits [302:301] = bus type, the first field of the QP
    # payload (REQTYPE, _QP_REQTYPE_B = 2 bits) is at [300:299]. That
    # corresponds to (bus >> 299) & 0x3 after masking off the top 2 bus
    # type bits.
    assert (bus >> 301) & 0x3 == _METADATA_QP_T
    assert (bus >> 299) & ((1 << _QP_REQTYPE_B) - 1) == _REQ_QP_DESTROY


def test_encode_create_qp_vs_modify_qp_req_type_differ():
    """Complementary to the destroy-QP test: CREATE=0 and MODIFY=2
    produce different req_type fields on the wire. A regression that
    reversed the two constants would silently send modify-as-create (or
    vice versa) — pin the encoding."""
    create_bus = _encode_create_qp(pd_handler=0x55)
    modify_bus = _encode_modify_qp(qpn=0x0, attr_mask=0x0,
                                   qp_state=_IBV_QPS_INIT, pmtu=5)
    assert (create_bus >> 299) & 0x3 == _REQ_QP_CREATE
    assert (modify_bus >> 299) & 0x3 == _REQ_QP_MODIFY


# ---------------------------------------------------------------------------
# _wait_resp — edge cases.
#
#   A: RecvMetaData already at 1 on entry returns immediately without
#      spending 20 ms in the zero-probe loop.  The fake-clock fixture
#      bumps monotonic by 100 s per call, so the zero_deadline (+0.02 s)
#      is exceeded on the very next monotonic check, exiting the probe
#      loop on its first iteration.  Verifies the function is safe to
#      call back-to-back without accumulating zero-probe overhead per
#      call — matters because _roce_setup_connection chains six such
#      calls on the happy path.
#   B: timeout_s=0 raises rogue.GeneralError on the first deadline
#      comparison (no RecvMetaData==1 was observed).
# ---------------------------------------------------------------------------

def test_wait_resp_returns_immediately_when_already_ready(monkeypatch):
    """When RecvMetaData.get() already returns 1 on the first poll,
    _wait_resp must return the MetaDataRx value without waiting. The
    monkeypatched clock ensures the 20 ms zero-probe loop exits on the
    first iteration rather than spinning for 20 real ms per call."""
    _accelerate_time(monkeypatch)
    engine = MagicMock()
    engine.RecvMetaData.get.return_value = 1
    engine.MetaDataRx.get.return_value = 0xFEEDC0DE
    assert _wait_resp(engine, timeout_s=5.0) == 0xFEEDC0DE


def test_wait_resp_timeout_s_zero_raises_fast(monkeypatch):
    """timeout_s=0 makes the second loop raise on its first deadline check,
    even if the zero-probe loop observed the transient 0 first. The fake
    clock ensures no wall-clock sleep is incurred."""
    _accelerate_time(monkeypatch)
    engine = MagicMock()
    engine.RecvMetaData.get.return_value = 0
    with pytest.raises(rogue.GeneralError) as excinfo:
        _wait_resp(engine, timeout_s=0)
    assert "Timeout" in str(excinfo.value)


# ---------------------------------------------------------------------------
# _send_meta — auxiliary invariants beyond the sibling
# test_send_meta_rising_edge_sequence.  Pin MetaDataTx.set call count and
# the invariant that bus_value=0 still triggers a rising edge (the firmware
# trigger is on the SendMetaData 0→1 edge, not on the MetaDataTx value).
# ---------------------------------------------------------------------------

def test_send_meta_metadata_tx_set_exactly_once_per_call():
    """_send_meta writes MetaDataTx exactly once (and SendMetaData three
    times: 0, 1, 0). An erroneous duplicate MetaDataTx write could clobber
    the bus between the rising edge and the firmware latching it."""
    engine = MagicMock()
    _send_meta(engine, 0x12345)
    assert engine.MetaDataTx.set.call_count == 1
    assert engine.SendMetaData.set.call_count == 3


def test_send_meta_bus_value_zero_still_fires_rising_edge():
    """Edge: a zero bus_value still emits the 0→1→0 rising-edge sequence
    on SendMetaData. A teardown or diagnostic path that encodes to 0
    would otherwise be silently dropped if an optimization tried to skip
    the write."""
    engine = MagicMock()
    _send_meta(engine, 0)
    assert engine.SendMetaData.set.call_args_list == [
        call(0), call(1), call(0),
    ]


# ---------------------------------------------------------------------------
# _roce_setup_connection — rollback matrix.
#
# One test per failure stage — the sibling test_partial_setup_rollback_on_
# mr_failure only covers stage 2.  Each test asserts:
#   1. rogue.GeneralError with the right message substring raises
#   2. the expected number of MetaDataTx.set calls lands (N forward +
#      K rollback)
#   3. the exception surfaces AFTER the rollback runs, so a caller
#      observing the raise can rely on FPGA state being clean
#
# The rollback count reasoning:
#   - Stage 1 (PD) failure: no try/except wraps stage 1, no rollback → 1 TX.
#   - Stage 2 (MR) failure: qp_created=False, mr_allocated=False → only PD
#     dealloc → 2 forward + 1 rollback = 3 TX. (Covered by the existing
#     test_partial_setup_rollback_on_mr_failure; not duplicated here —
#     instead we add the type-mismatch analogue below.)
#   - Stage 3 (QP create) failure: qp_created=False, mr_allocated=True →
#     MR + PD dealloc → 3 forward + 2 rollback = 5 TX.
#   - Stage 4 (QP→INIT) / 5 (QP→RTR) / 6 (QP→RTS) failure: qp_created=True,
#     mr_allocated=True → QP ERR + QP DESTROY + MR + PD dealloc = 4 rollback
#     writes on top of the forward count (4, 5, or 6 respectively) = 8, 9,
#     or 10 TX.
# ---------------------------------------------------------------------------

def test_setup_raises_on_pd_failure_with_no_rollback(monkeypatch):
    """Stage 1 (PD alloc) failure: _roce_setup_connection raises without
    any rollback TX (the try/except wrapper only protects stages 2-6).
    Exactly one MetaDataTx.set call lands (the failed PD alloc itself);
    no dealloc follows."""
    _accelerate_time(monkeypatch)
    engine = MagicMock()
    engine.RecvMetaData.get.return_value = 1
    engine.MetaDataRx.get.return_value = _pack_pd_fail(pd_handler=0x0)
    with pytest.raises(rogue.GeneralError) as excinfo:
        _roce_setup_connection(
            engine,
            host_qpn=1, host_rq_psn=0, host_sq_psn=0,
            mr_laddr=0x1000, mr_len=4096, pmtu=5,
        )
    assert "FPGA PD allocation failed" in str(excinfo.value)
    assert engine.MetaDataTx.set.call_count == 1


def test_setup_raises_on_mr_resp_type_mismatch_with_pd_rollback(monkeypatch):
    """Stage 2: PD succeeds, but the MR response carries an unexpected
    resp_type (the firmware emitted a QP tag on the MR slot). The resp_type
    check raises BEFORE mr_allocated flips to True, so rollback only
    deallocs the PD. Total TX: 2 forward + 1 rollback = 3."""
    _accelerate_time(monkeypatch)
    engine = MagicMock()
    engine.RecvMetaData.get.return_value = 1
    engine.MetaDataRx.get.side_effect = _script_rx(
        _pack_pd_ok(pd_handler=0xDEAD),
        _pack_unknown_type(),     # MR slot: resp_type=3 (not MR)
        _pack_pd_ok(),            # rollback PD dealloc RX
        name="mr-type-mismatch",
    )
    with pytest.raises(rogue.GeneralError) as excinfo:
        _roce_setup_connection(
            engine,
            host_qpn=1, host_rq_psn=0, host_sq_psn=0,
            mr_laddr=0x1000, mr_len=4096, pmtu=5,
        )
    assert "Expected MR response" in str(excinfo.value)
    assert engine.MetaDataTx.set.call_count == 3


def test_setup_rollback_on_qp_create_failure(monkeypatch):
    """Stage 3 (QP CREATE ok=False): PD + MR already allocated. Rollback
    deallocs MR then PD. Total TX: 3 forward + 2 rollback = 5."""
    _accelerate_time(monkeypatch)
    engine = MagicMock()
    engine.RecvMetaData.get.return_value = 1
    engine.MetaDataRx.get.side_effect = _script_rx(
        _pack_pd_ok(pd_handler=0xDEAD),
        _pack_mr_ok(),
        _pack_qp_fail(),          # QP CREATE fail
        _pack_mr_ok(),            # rollback: MR dealloc resp (ignored by _rollback_step)
        _pack_pd_ok(),            # rollback: PD dealloc resp
        name="qp-create-fail",
    )
    with pytest.raises(rogue.GeneralError) as excinfo:
        _roce_setup_connection(
            engine,
            host_qpn=1, host_rq_psn=0, host_sq_psn=0,
            mr_laddr=0x1000, mr_len=4096, pmtu=5,
        )
    assert "FPGA QP creation failed" in str(excinfo.value)
    assert engine.MetaDataTx.set.call_count == 5


@pytest.mark.parametrize(
    "init_response,expected_msg",
    [
        (_pack_qp_fail(state=_IBV_QPS_INIT), "FPGA QP→INIT failed"),
        (_pack_qp_ok  (state=_IBV_QPS_RESET), "FPGA QP→INIT failed"),
    ],
    ids=["ok-false", "wrong-state"],
)
def test_setup_rollback_on_qp_init_failure(monkeypatch,
                                           init_response, expected_msg):
    """Stage 4 (QP→INIT): both ok=False and ok=True-with-wrong-state must
    trigger full rollback (QP ERR + QP DESTROY + MR dealloc + PD dealloc).
    qp_created=True at this point so all four rollback steps emit.
    Total TX: 4 forward + 4 rollback = 8."""
    _accelerate_time(monkeypatch)
    engine = MagicMock()
    engine.RecvMetaData.get.return_value = 1
    engine.MetaDataRx.get.side_effect = _script_rx(
        _pack_pd_ok(pd_handler=0xDEAD),
        _pack_mr_ok(),
        _pack_qp_ok(state=_IBV_QPS_INIT),  # QP CREATE ok
        init_response,                      # QP→INIT outcome under test
        # 4 rollback RX words (values don't matter — _rollback_step's
        # _wait_resp output is discarded):
        _pack_qp_ok(state=_IBV_QPS_ERR),
        _pack_qp_ok(state=_IBV_QPS_RESET),
        _pack_mr_ok(),
        _pack_pd_ok(),
        name="qp-init-fail",
    )
    with pytest.raises(rogue.GeneralError) as excinfo:
        _roce_setup_connection(
            engine,
            host_qpn=1, host_rq_psn=0, host_sq_psn=0,
            mr_laddr=0x1000, mr_len=4096, pmtu=5,
        )
    assert expected_msg in str(excinfo.value)
    assert engine.MetaDataTx.set.call_count == 8


def test_setup_rollback_on_qp_rtr_failure(monkeypatch):
    """Stage 5 (QP→RTR): forward 5 TX (PD, MR, QP CREATE, QP→INIT ok,
    QP→RTR attempt), rollback 4 (QP ERR + DESTROY + MR + PD). Total: 9."""
    _accelerate_time(monkeypatch)
    engine = MagicMock()
    engine.RecvMetaData.get.return_value = 1
    engine.MetaDataRx.get.side_effect = _script_rx(
        _pack_pd_ok(pd_handler=0xDEAD),
        _pack_mr_ok(),
        _pack_qp_ok(state=_IBV_QPS_INIT),
        _pack_qp_ok(state=_IBV_QPS_INIT),
        _pack_qp_fail(state=_IBV_QPS_RTR),  # RTR attempt fails
        _pack_qp_ok(state=_IBV_QPS_ERR),
        _pack_qp_ok(state=_IBV_QPS_RESET),
        _pack_mr_ok(),
        _pack_pd_ok(),
        name="qp-rtr-fail",
    )
    with pytest.raises(rogue.GeneralError) as excinfo:
        _roce_setup_connection(
            engine,
            host_qpn=1, host_rq_psn=0, host_sq_psn=0,
            mr_laddr=0x1000, mr_len=4096, pmtu=5,
        )
    assert "FPGA QP→RTR failed" in str(excinfo.value)
    assert engine.MetaDataTx.set.call_count == 9


def test_setup_rollback_on_qp_rts_failure(monkeypatch):
    """Stage 6 (QP→RTS): forward 6 TX, rollback 4. Total: 10. The last
    forward stage — proves the rollback fires even after the MR + QP are
    fully established on the firmware side."""
    _accelerate_time(monkeypatch)
    engine = MagicMock()
    engine.RecvMetaData.get.return_value = 1
    engine.MetaDataRx.get.side_effect = _script_rx(
        _pack_pd_ok(pd_handler=0xDEAD),
        _pack_mr_ok(),
        _pack_qp_ok(state=_IBV_QPS_INIT),
        _pack_qp_ok(state=_IBV_QPS_INIT),
        _pack_qp_ok(state=_IBV_QPS_RTR),
        _pack_qp_fail(state=_IBV_QPS_RTS),  # RTS attempt fails
        _pack_qp_ok(state=_IBV_QPS_ERR),
        _pack_qp_ok(state=_IBV_QPS_RESET),
        _pack_mr_ok(),
        _pack_pd_ok(),
        name="qp-rts-fail",
    )
    with pytest.raises(rogue.GeneralError) as excinfo:
        _roce_setup_connection(
            engine,
            host_qpn=1, host_rq_psn=0, host_sq_psn=0,
            mr_laddr=0x1000, mr_len=4096, pmtu=5,
        )
    assert "FPGA QP→RTS failed" in str(excinfo.value)
    assert engine.MetaDataTx.set.call_count == 10


def test_setup_happy_path_emits_six_tx_writes(monkeypatch):
    """Hardware-free analogue of the hardware-gated
    test_roce_setup_connection_full_flow_against_live_server. Drives the
    6-step setup flow with a scripted MagicMock engine (no rxe0
    dependency) and asserts the documented return tuple and TX write
    count. Covers the success path on every CI run, not just ones that
    manage to bring up Soft-RoCE."""
    _accelerate_time(monkeypatch)
    engine = MagicMock()
    engine.RecvMetaData.get.return_value = 1
    engine.MetaDataRx.get.side_effect = _script_rx(
        _pack_pd_ok(pd_handler=0xDEADBEEF),
        _pack_mr_ok(lkey=0xABCD1234, rkey=0x5678DEAD),
        _pack_qp_ok(qpn=0x123456, state=_IBV_QPS_INIT),
        _pack_qp_ok(qpn=0x123456, state=_IBV_QPS_INIT),
        _pack_qp_ok(qpn=0x123456, state=_IBV_QPS_RTR),
        _pack_qp_ok(qpn=0x123456, state=_IBV_QPS_RTS),
        name="setup-happy",
    )
    fpga_qpn, lkey, pd_handler, rkey = _roce_setup_connection(
        engine,
        host_qpn=1, host_rq_psn=0, host_sq_psn=0,
        mr_laddr=0x1000, mr_len=4096, pmtu=5,
    )
    assert engine.MetaDataTx.set.call_count == 6
    assert fpga_qpn   == 0x123456
    assert pd_handler == 0xDEADBEEF
    assert lkey       == 0xABCD1234
    assert rkey       == 0x5678DEAD


# ---------------------------------------------------------------------------
# _roce_teardown — step-by-step timeout coverage.
#
# The existing test_teardown_continues_on_intermediate_timeout covers
# step-3 (MR dealloc) only. Add the missing steps so every try/except
# inside _roce_teardown is exercised at least once.
#
# Strategy: a scripted RecvMetaData.get side_effect tracks which phase
# we're in by counting _send_meta rising edges and returns 0 (never-goes-
# to-1) for the phase under test, 1 otherwise. This forces _wait_resp to
# hit its deadline on that phase and raise, which the teardown catches
# and continues past.
# ---------------------------------------------------------------------------

def _run_teardown_with_timeout_at_step(monkeypatch, timeout_step_index):
    """Drive _roce_teardown with RecvMetaData.get scripted to time out on
    the Nth _send_meta rising edge (1-indexed: 1=QP-ERR, 2=QP-DESTROY,
    3=MR-dealloc, 4=PD-dealloc). Returns (engine, log) for assertions."""
    _accelerate_time(monkeypatch)
    engine = MagicMock()
    # All-success RX word (same as the sibling test): QP ok + MR ok + PD ok.
    engine.MetaDataRx.get.return_value = (1 << 273) | (1 << 262) | (1 << 64)

    phase = {"send_count": 0}

    def _bump_on_rising_edge(value):
        if value == 1:
            phase["send_count"] += 1

    engine.SendMetaData.set.side_effect = _bump_on_rising_edge

    def _recv_get(*args, **kwargs):
        return 0 if phase["send_count"] == timeout_step_index else 1

    engine.RecvMetaData.get.side_effect = _recv_get

    log = MagicMock()
    _roce_teardown(
        engine,
        fpga_qpn=0x001234,
        pd_handler=0x55, lkey=0x66, rkey=0x77,
        log=log,
    )
    return engine, log


@pytest.mark.parametrize(
    "timeout_step",
    [1, 2, 3, 4],
    ids=["qp-err", "qp-destroy", "mr-dealloc", "pd-dealloc"],
)
def test_teardown_continues_after_any_single_step_timeout(
        monkeypatch, timeout_step):
    """Every one of the four teardown steps (QP ERR, QP DESTROY, MR
    dealloc, PD dealloc) must be tolerant of an intermediate _wait_resp
    timeout. After the timed-out step, subsequent steps still emit their
    MetaDataTx write. Invariant: MetaDataTx.set is called exactly 4
    times even when one of the four steps times out. The step-3 case
    duplicates the sibling
    test_teardown_continues_on_intermediate_timeout on purpose — keeping
    all four in one parametric set documents the invariant as a single
    matrix rather than four scattered asserts."""
    engine, log = _run_teardown_with_timeout_at_step(monkeypatch,
                                                    timeout_step)
    assert engine.MetaDataTx.set.call_count == 4
    assert log.warning.called, (
        f"log.warning must be called on the timed-out step {timeout_step}")


def test_teardown_all_four_steps_timeout_still_emits_four_writes(monkeypatch):
    """Pathological: every _wait_resp times out. All four TX writes must
    still land (the try/except around each _wait_resp catches the
    GeneralError) and log.warning is called at least four times (once per
    step). Guards against a future refactor that threads a shared 'abort
    on first timeout' through the teardown sequence."""
    _accelerate_time(monkeypatch)
    engine = MagicMock()
    engine.RecvMetaData.get.return_value = 0  # every poll never completes
    engine.MetaDataRx.get.return_value = 0
    log = MagicMock()
    _roce_teardown(
        engine,
        fpga_qpn=0x001234,
        pd_handler=0x55, lkey=0x66, rkey=0x77,
        log=log,
    )
    assert engine.MetaDataTx.set.call_count == 4
    assert log.warning.call_count >= 4


def test_teardown_skips_mr_pd_when_pd_handler_zero_with_log(monkeypatch):
    """Parallel to the sibling test_roce_teardown_skips_mr_pd_when_pd_
    handler_zero (in test_rocev2.py), but also asserts log.info was
    called on the QP steps. Verifies that when pd_handler=0 (e.g.
    teardown called before the MR+PD were allocated), only the QP ERR
    and QP DESTROY writes land — MR and PD dealloc are skipped entirely,
    not just no-op'd. Total TX: 2, not 4."""
    _accelerate_time(monkeypatch)
    engine = MagicMock()
    engine.RecvMetaData.get.return_value = 1
    engine.MetaDataRx.get.return_value = (1 << 273)  # QP ok only
    log = MagicMock()
    _roce_teardown(engine, fpga_qpn=0x001234, pd_handler=0, log=log)
    assert engine.MetaDataTx.set.call_count == 2
    # log.info fires on QP ERR + QP DESTROY success branches (twice each
    # step: entering + response-ok) so at least 2. Assertion is loose
    # on call_count to avoid brittleness against future log verbosity
    # tweaks.
    assert log.info.called


# ---------------------------------------------------------------------------
# RoCEv2Server — lifecycle with mocked ibverbs Server.create.
#
# These tests patch rogue.protocols.rocev2.Server.create so no rxe0 is
# required. They exercise the pyrogue.Device layer paths that the
# hardware-gated tests also touch, but in a form every CI run can execute.
# ---------------------------------------------------------------------------

@pytest.fixture
def mocked_rocev2_cpp(monkeypatch):
    """Patch the C++ rogue.protocols.rocev2.Server.create to return a
    MagicMock, so RoCEv2Server.__init__ can construct without rxe0. The
    fixture yields the mock so individual tests can program return values
    for the Server accessors (getQpn, getMrAddr, etc.).

    RoCEv2 is Linux-only (ROGUE_LINUX_BUILD); the C++ submodule doesn't
    exist on macOS, so the fixture skips consumers there rather than
    erroring at setup."""
    _cpp = pytest.importorskip(
        "rogue.protocols.rocev2",
        reason="RoCEv2 is Linux-only (libibverbs not available)",
    )
    mock_server = MagicMock()
    mock_server.getQpn.return_value    = 0x000abc
    mock_server.getGid.return_value    = 'fe80:0000:0000:0000:dead:beef:feed:face'
    mock_server.getRqPsn.return_value  = 0x111111
    mock_server.getSqPsn.return_value  = 0x222222
    mock_server.getMrAddr.return_value = 0x7fff00000000
    mock_server.getMrRkey.return_value = 0x33334444
    mock_server.getFrameCount.return_value = 0
    mock_server.getByteCount.return_value  = 0
    monkeypatch.setattr(_cpp.Server, "create",
                        MagicMock(return_value=mock_server))
    monkeypatch.setattr(_rce, "_ROCEV2_AVAILABLE", True)
    yield mock_server


@pytest.mark.parametrize("valid_pmtu", [1, 5])
def test_rocev2server_accepts_valid_pmtu_boundaries(
        mocked_rocev2_cpp, valid_pmtu):
    """The sibling test_rocev2server_rejects_out_of_range_pmtu covers
    only the reject side of the boundary. Pin the accept side so a
    future off-by-one in the pmtu validator is caught: pmtu=1 and pmtu=5
    must both construct without raising."""
    srv = RoCEv2Server(
        ip='10.0.0.1', deviceName='rxe0',
        pmtu=valid_pmtu, roceEngine=MagicMock(),
        name=f'srv_pmtu_{valid_pmtu}',
    )
    assert srv._pmtu == valid_pmtu


def test_teardown_fpga_qp_is_noop_when_qpn_zero(mocked_rocev2_cpp):
    """teardownFpgaQp early-returns when _fpga_qpn == 0 (setup never
    completed, or already torn down). No metadata-bus activity must
    occur on the RoceEngine — the engine's set methods are never
    called. Guards against a regression that forgets the early-return
    and sends stale qpn=0 to the firmware."""
    engine = MagicMock()
    srv = RoCEv2Server(
        ip='10.0.0.1', deviceName='rxe0',
        roceEngine=engine, name='srv_noop_teardown',
    )
    # _fpga_qpn starts at 0 from __init__.
    srv.teardownFpgaQp()
    # Neither TX nor the rising-edge SendMetaData was touched.
    engine.MetaDataTx.set.assert_not_called()
    engine.SendMetaData.set.assert_not_called()


def test_teardown_fpga_qp_swallows_exception_and_logs(
        monkeypatch, mocked_rocev2_cpp):
    """teardownFpgaQp wraps _roce_teardown in try/except: if teardown
    itself raises (e.g. a bug mid-call, not a per-step timeout), the
    exception is logged as a warning and swallowed. Guards _stop()
    from ever propagating a teardown bug up into Root.stop()."""
    engine = MagicMock()
    srv = RoCEv2Server(
        ip='10.0.0.1', deviceName='rxe0',
        roceEngine=engine, name='srv_swallow',
    )
    # Force teardownFpgaQp past the qpn==0 gate so _roce_teardown runs.
    srv._fpga_qpn        = 0x001234
    srv._fpga_pd_handler = 0x55

    def _boom(*args, **kwargs):
        raise rogue.GeneralError("injected", "teardown exploded")

    monkeypatch.setattr(_rce, "_roce_teardown", _boom)

    # Must not raise.
    srv.teardownFpgaQp()
    # Log is a pyrogue-managed Logger; we can't spy on it directly
    # without reaching into pyrogue internals, but the silent-return is
    # itself the observable contract under test.


def test_stop_calls_teardown_before_server_stop(
        monkeypatch, mocked_rocev2_cpp):
    """_stop() must call teardownFpgaQp() BEFORE self._server.stop() —
    the RoceEngine (host-side SRP transport) is still alive during
    teardown so the metadata-bus writes can reach the firmware. If the
    order flipped, teardown would run after the transport is dead and
    the FPGA would leak its PD / MR / QP. Verified via a call-order
    spy that records which mock was invoked first."""
    engine = MagicMock()
    srv = RoCEv2Server(
        ip='10.0.0.1', deviceName='rxe0',
        roceEngine=engine, name='srv_stop_order',
    )
    # Put the object in a state where teardownFpgaQp WOULD do work
    # (skip the qpn==0 early-return).
    srv._fpga_qpn        = 0x001234
    srv._fpga_pd_handler = 0x55

    order = []

    def _record_teardown(_self):
        order.append("teardownFpgaQp")
        # Reset state so a second stop() wouldn't re-teardown.
        _self._fpga_qpn = 0

    def _record_server_stop(*args, **kwargs):
        order.append("server.stop")

    # Patch the class method so it retains access to self; monkeypatching
    # the bound method would bypass the spy.
    monkeypatch.setattr(RoCEv2Server, "teardownFpgaQp",
                        lambda s: _record_teardown(s))
    srv._server.stop.side_effect = _record_server_stop

    # ConnectionState.set requires a running Root (_queueUpdate reaches
    # up through the Device tree). Substitute a MagicMock for the
    # LocalVariable so _stop's `self.ConnectionState.set('Disconnected')`
    # becomes a no-op observable only if we care to assert it.
    srv.ConnectionState = MagicMock()

    # super()._stop() would otherwise touch pyrogue plumbing that isn't
    # set up in this unit context (Device._stop walks children, etc.).
    # Replace the parent's _stop with a no-op so we stay focused on the
    # teardown-vs-server.stop ordering under test.
    monkeypatch.setattr(RoCEv2Server.__bases__[0], "_stop",
                        lambda self: None)
    srv._stop()
    assert order == ["teardownFpgaQp", "server.stop"]
    srv.ConnectionState.set.assert_called_with('Disconnected')


def test_stream_property_returns_underlying_cpp_server(mocked_rocev2_cpp):
    """RoCEv2Server.stream returns self._server (the C++ RC receive
    master) so the documented `srv.stream >> slave` pattern wires to the
    same object that the per-channel getChannel() filter is downstream
    of. A property that silently returned a copy or a filtered view
    would break the 'catch every channel' use case."""
    srv = RoCEv2Server(
        ip='10.0.0.1', deviceName='rxe0',
        roceEngine=MagicMock(), name='srv_stream',
    )
    assert srv.stream is srv._server


# ---------------------------------------------------------------------------
# GID helpers — edge IPv4 inputs.
# ---------------------------------------------------------------------------

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
    (socket.error is an alias). Pin the raise so a future switch to a
    best-effort parser that silently substitutes 0.0.0.0 would fail."""
    with pytest.raises((OSError, socket.error)):
        _ip_to_gid_bytes("not-an-ip")
