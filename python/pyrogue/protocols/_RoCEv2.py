#-----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
#-----------------------------------------------------------------------------
# Description:
#   PyRogue Device wrapper for the RoCEv2 RC receive server.  Drives the
#   FPGA-side RoceEngine through a metadata bus, manages host-side
#   ibverbs resource allocation, and orchestrates the QP handshake.
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
from __future__ import annotations

import socket
import struct
import random as _random
import time as _time

import pyrogue as pr
import rogue
import rogue.interfaces.stream

try:
    import rogue.protocols.rocev2 as _cpp_rocev2  # noqa: F401
    _ROCEV2_AVAILABLE = True
except ImportError:
    _ROCEV2_AVAILABLE = False


# ---------------------------------------------------------------------------
# GID helpers
# ---------------------------------------------------------------------------

def _ip_to_gid_bytes(ip: str) -> bytes:
    """Convert IPv4 string to 16-byte IPv4-mapped IPv6 GID."""
    return b'\x00' * 10 + b'\xff\xff' + socket.inet_aton(ip)


def _gid_bytes_to_str(gid: bytes) -> str:
    """Format 16 GID bytes as colon-separated hex (ibv_devinfo format)."""
    words = struct.unpack('>8H', gid)
    return ':'.join(f'{w:04x}' for w in words)


# ---------------------------------------------------------------------------
# Constants — must match BSVSettings.py / BusStructs.py in the firmware repo
# ---------------------------------------------------------------------------

_META_DATA_TX_BITS   = 303
_META_DATA_RX_BITS   = 276   # informational only; actual bus may be shorter

# Bus type tags
_METADATA_PD_T = 0
_METADATA_MR_T = 1
_METADATA_QP_T = 2

# QP request types
_REQ_QP_CREATE  = 0
_REQ_QP_DESTROY = 1
_REQ_QP_MODIFY  = 2
_REQ_QP_QUERY   = 3   # kept for completeness, not currently used

# QP types / states
_IBV_QPT_RC    = 2
_IBV_QPS_RESET  = 0
_IBV_QPS_INIT   = 1
_IBV_QPS_RTR    = 2
_IBV_QPS_RTS    = 3
_IBV_QPS_SQD    = 4
_IBV_QPS_ERR    = 6
_IBV_QPS_CREATE = 8

# QP attribute mask bits
_IBV_QP_STATE             = 1
_IBV_QP_ACCESS_FLAGS      = 8
_IBV_QP_PKEY_INDEX        = 16
_IBV_QP_PATH_MTU          = 256
_IBV_QP_TIMEOUT           = 512
_IBV_QP_RETRY_CNT         = 1024
_IBV_QP_RNR_RETRY         = 2048
_IBV_QP_RQ_PSN            = 4096
_IBV_QP_MAX_QP_RD_ATOMIC  = 8192
_IBV_QP_MIN_RNR_TIMER     = 32768
_IBV_QP_SQ_PSN            = 65536
_IBV_QP_MAX_DEST_RD_ATOMIC = 131072
_IBV_QP_DEST_QPN          = 1048576

# Field widths — derived from BSVSettings.py with MAX_PD=1, MAX_MR=2
_PD_ALLOC_OR_NOT_B = 1
_PD_INDEX_B        = 0    # int(log2(MAX_PD=1)) = 0
_PD_HANDLER_B      = 32
_PD_KEY_B          = 32   # PD_HANDLER_B - PD_INDEX_B = 32

_MR_ALLOC_OR_NOT_B = 1
_MR_INDEX_B        = 1    # int(log2(MAX_MR/MAX_PD = 2)) = 1
_MR_LADDR_B        = 64
_MR_LEN_B          = 32
_MR_ACCFLAGS_B     = 8
_MR_PDHANDLER_B    = 32
_MR_KEY_B          = 32
_MR_LKEYPART_B     = 31   # MR_KEY_B - MR_INDEX_B = 31
_MR_RKEYPART_B     = 31   # MR_KEY_B - MR_INDEX_B = 31
_MR_LKEYORNOT_B    = 1

_QPI_TYPE_B        = 4
_QPI_SQSIGALL_B    = 1

_QPA_QPSTATE_B     = 4
_QPA_CURRQPSTATE_B = 4
_QPA_PMTU_B        = 3
_QPA_QKEY_B        = 32
_QPA_RQPSN_B       = 24
_QPA_SQPSN_B       = 24
_QPA_DQPN_B        = 24
_QPA_QPACCFLAGS_B  = 8
_QPA_CAP_B         = 40
_QPA_PKEY_B        = 16
_QPA_SQDRAINING_B  = 1
_QPA_MAXREADATOMIC_B  = 8
_QPA_MAXDESTRD_B      = 8
_QPA_RNRTIMER_B    = 5
_QPA_TIMEOUT_B     = 5
_QPA_RETRYCNT_B    = 3
_QPA_RNRRETRY_B    = 3

_QP_REQTYPE_B      = 2
_QP_PDHANDLER_B    = 32
_QP_QPN_B          = 24
_QP_ATTRMASK_B     = 26

# Default QP tuning values
_ACC_PERM          = 0x0F   # local_write | remote_write | remote_read | remote_atomic
_DEFAULT_RETRY_NUM = 3
_DEFAULT_RNR_TIMER = 1
_DEFAULT_TIMEOUT   = 14
_MAX_QP_RD_ATOM    = 16
_CAP_VALUE         = 0x2020010100   # from Utils4Test.bsv


# ---------------------------------------------------------------------------
# TX bus encoders — pure-int arithmetic, no external dependencies
#
# Pattern (mirrors BusStructs.py getBus() semantics):
#   Fields are concatenated LSB-aligned at bit 0 of the returned integer:
#   the last field's LSB lands at bit 0, the first field's MSB lands at
#   bit (used_bits-1).  Within this used region the first-listed field
#   is at the top and the last-listed field is at the bottom — i.e.
#   relative order is MSB-first within the used window, but the window
#   itself is NOT left-aligned in the 301-bit payload region; bits
#   [300:used_bits] are zero-padded.  The 2-bit bus type is written at
#   the TOP 2 bits (bits 302:301) of the 303-bit bus.  This matches the
#   FPGA BusStructs.py layout and the RX decoder offsets below (e.g.
#   _decode_resp_type extracts (rx >> 274) & 0x3 from a 276-bit RX bus,
#   _decode_pd_resp reads successOrNot at bit 64, pd_handler at 63:32,
#   pd_key at 31:0 — same LSB-aligned-in-used-region convention).
# ---------------------------------------------------------------------------

def _mk_bus(bus_type: int, *fields: tuple[int, int]) -> int:
    """Build a 303-bit TX metadata bus integer from (value, width) fields.

    Fields are concatenated LSB-aligned at bit 0 of the returned integer:
    the last field's LSB is at bit 0 and the first field's MSB is at bit
    ``used_bits-1``.  Within the used window the first-listed field sits
    at the top and the last-listed at the bottom (MSB-first ordering),
    but the window itself is right-aligned at bit 0 — bits
    ``[300:used_bits]`` are zero-padded, not occupied by a shifted
    payload.  The 2-bit bus type is written at the TOP 2 bits
    (bits 302:301) of the 303-bit bus, matching the FPGA BusStructs.py
    layout and the RX-side ``_decode_*`` helpers, which all read fields
    at fixed offsets counted from bit 0 (e.g. ``_decode_resp_type``
    extracts ``(rx >> 274) & 0x3`` from a 276-bit RX bus).
    """
    acc = 0
    used_bits = 0
    for value, width in fields:
        mask = (1 << width) - 1
        acc = (acc << width) | (int(value) & mask)
        used_bits += width

    if _META_DATA_TX_BITS - used_bits < 2:
        raise rogue.GeneralError(
            "_mk_bus",
            f"Bus type cannot fit: fields consume {used_bits} of "
            f"{_META_DATA_TX_BITS} bits, need 2 reserved for bus type")

    # Low `used_bits` bits hold the meta payload; bus type at [302:301].
    full = acc | ((bus_type & 0x3) << (_META_DATA_TX_BITS - 2))
    return full


def _encode_alloc_pd(pd_key):
    """reqPd.getBus(): allocOrNot(1) + pdKey(32) + pdHandler(32)"""
    return _mk_bus(_METADATA_PD_T,
        (1,      _PD_ALLOC_OR_NOT_B),
        (pd_key, _PD_KEY_B),
        (0,      _PD_HANDLER_B),       # pdHandler don't-care in request
    )


def _encode_alloc_mr(pd_handler, laddr, length, lkey_part, rkey_part):
    """reqMr.getBus(): allocOrNot + mrLAddr + mrLen + mrAccFlags + mrPdHandler
                       + mrLKeyPart + mrRKeyPart + lKeyOrNot + lKey + rKey"""
    return _mk_bus(_METADATA_MR_T,
        (1,           _MR_ALLOC_OR_NOT_B),
        (laddr,       _MR_LADDR_B),
        (length,      _MR_LEN_B),
        (_ACC_PERM,   _MR_ACCFLAGS_B),
        (pd_handler,  _MR_PDHANDLER_B),
        (lkey_part,   _MR_LKEYPART_B),
        (rkey_part,   _MR_RKEYPART_B),
        (0,           _MR_LKEYORNOT_B),
        (0,           _MR_KEY_B),       # lKey don't-care
        (0,           _MR_KEY_B),       # rKey don't-care
    )


def _encode_create_qp(pd_handler):
    """reqQp.getBus() for CREATE: all QPA fields + qpiType + qpiSqSigAll"""
    fields = [
        (_REQ_QP_CREATE, _QP_REQTYPE_B),
        (pd_handler,     _QP_PDHANDLER_B),
        (0,              _QP_QPN_B),
        (0,              _QP_ATTRMASK_B),
    ]
    # All QPA fields don't-care for CREATE
    for w in [_QPA_QPSTATE_B, _QPA_CURRQPSTATE_B, _QPA_PMTU_B,
              _QPA_QKEY_B, _QPA_RQPSN_B, _QPA_SQPSN_B, _QPA_DQPN_B,
              _QPA_QPACCFLAGS_B, _QPA_CAP_B, _QPA_PKEY_B,
              _QPA_SQDRAINING_B, _QPA_MAXREADATOMIC_B, _QPA_MAXDESTRD_B,
              _QPA_RNRTIMER_B, _QPA_TIMEOUT_B, _QPA_RETRYCNT_B, _QPA_RNRRETRY_B]:
        fields.append((0, w))
    fields.append((_IBV_QPT_RC, _QPI_TYPE_B))
    fields.append((0,           _QPI_SQSIGALL_B))
    return _mk_bus(_METADATA_QP_T, *fields)


def _encode_modify_qp(qpn, attr_mask, qp_state, pmtu,
                      dqpn=0, rq_psn=0, sq_psn=0,
                      min_rnr_timer=_DEFAULT_RNR_TIMER,
                      rnr_retry=_DEFAULT_RETRY_NUM,
                      retry_count=_DEFAULT_RETRY_NUM):
    """reqQp.getBus() for MODIFY — same field order as CREATE."""
    fields = [
        (_REQ_QP_MODIFY, _QP_REQTYPE_B),
        (0,              _QP_PDHANDLER_B),
        (qpn,            _QP_QPN_B),
        (attr_mask,      _QP_ATTRMASK_B),
    ]
    # QPA fields in reqQp.getBus() order
    for value, width in [
        (qp_state,           _QPA_QPSTATE_B),
        (0,                  _QPA_CURRQPSTATE_B),
        (pmtu,               _QPA_PMTU_B),
        (0,                  _QPA_QKEY_B),
        (rq_psn,             _QPA_RQPSN_B),
        (sq_psn,             _QPA_SQPSN_B),
        (dqpn,               _QPA_DQPN_B),
        (0x0E,               _QPA_QPACCFLAGS_B),
        (_CAP_VALUE,         _QPA_CAP_B),
        (0xFFFF,             _QPA_PKEY_B),
        (0,                  _QPA_SQDRAINING_B),
        (_MAX_QP_RD_ATOM,    _QPA_MAXREADATOMIC_B),
        (_MAX_QP_RD_ATOM,    _QPA_MAXDESTRD_B),
        (min_rnr_timer,      _QPA_RNRTIMER_B),
        (_DEFAULT_TIMEOUT,   _QPA_TIMEOUT_B),
        (retry_count,        _QPA_RETRYCNT_B),
        (rnr_retry,          _QPA_RNRRETRY_B),
    ]:
        fields.append((int(value), width))
    fields.append((_IBV_QPT_RC, _QPI_TYPE_B))
    fields.append((0,           _QPI_SQSIGALL_B))
    return _mk_bus(_METADATA_QP_T, *fields)


# ---------------------------------------------------------------------------
# RX bus decoders — mirror BusStructs.py slice_vec / get_bool exactly
#
# Convention: bit 0 = LSB of the response integer.
# Fields extracted as: (rx >> lsb) & ((1 << width) - 1)
#
# respPd layout (from BusStructs.py):
#   bits [PD_KEY_B-1 : 0]                = pdKey      [31:0]
#   bits [PD_KEY_B+PD_HANDLER_B-1 : 32]  = pdHandler  [63:32]
#   bit  [PD_KEY_B+PD_HANDLER_B]         = successOrNot  bit 64
#   bits [275:274]                        = busType
#
# respMr layout:
#   bits [31:0]   = rKey
#   bits [63:32]  = lKey
#   ...more fields...
#   bit  [success_bit]  = successOrNot
#   bits [275:274]      = busType
#
# respQp layout:
#   bit  273      = successOrNot
#   bits [272:249] = qpn
#   bits [216:213] = qpaQpState
#   bits [275:274] = busType
# ---------------------------------------------------------------------------

def _decode_resp_type(rx):
    """Extract busType from bits [275:274] (LSB convention)."""
    return (rx >> 274) & 0x3


def _decode_pd_resp(rx):
    """
    Decode PD allocation response.
    Returns (success: bool, pd_handler: int).
    """
    success    = bool((rx >> (_PD_KEY_B + _PD_HANDLER_B)) & 1)
    pd_handler = (rx >> _PD_KEY_B) & ((1 << _PD_HANDLER_B) - 1)
    return success, pd_handler


def _decode_mr_resp(rx):
    """
    Decode MR allocation response.
    Returns (success: bool, lkey: int, rkey: int).
    From respMr.__init__: rKey at [31:0], lKey at [63:32].
    """
    success_bit = (_MR_KEY_B + _MR_KEY_B + _MR_RKEYPART_B + _MR_LKEYPART_B +
                   _MR_PDHANDLER_B + _MR_ACCFLAGS_B + _MR_LEN_B + _MR_LADDR_B)
    success = bool((rx >> success_bit) & 1)
    rkey    = rx & ((1 << _MR_KEY_B) - 1)
    lkey    = (rx >> _MR_KEY_B) & ((1 << _MR_KEY_B) - 1)
    return success, lkey, rkey


def _decode_qp_resp(rx):
    """
    Decode QP create/modify response.
    Returns (success: bool, qpn: int, qp_state: int).
    From respQp.__init__: successOrNot at bit 273, qpn at [272:249],
    qpaQpState at [216:213].
    """
    success  = bool((rx >> 273) & 1)
    qpn      = (rx >> 249) & ((1 << 24) - 1)
    qp_state = (rx >> 213) & 0xF
    return success, qpn, qp_state


# ---------------------------------------------------------------------------
# Metadata bus transport helpers
# ---------------------------------------------------------------------------

def _send_meta(engine, bus_value):
    """
    Send a metadata bus message via any RoceEngine-compatible object.

    The firmware triggers on the RISING EDGE of metaDataIsSet (0→1).
    Writing 0 first ensures a clean rising edge every time.
    """
    engine.SendMetaData.set(0)
    engine.MetaDataTx.set(bus_value)
    engine.SendMetaData.set(1)
    engine.SendMetaData.set(0)


def _wait_resp(engine, timeout_s=5.0):
    """
    Wait for firmware to process the request and return MetaDataRx value.

    The firmware clears metaDataIsReady on rising edge, sets it back when done.
    Processing takes microseconds so the 0 state may be too brief to observe.
    We briefly try to catch the 0, then wait for the 1.
    """
    deadline      = _time.monotonic() + timeout_s
    zero_deadline = _time.monotonic() + 0.02

    # Try briefly to observe RecvMetaData → 0 (firmware started). The 0 pulse
    # can be shorter than Python's polling resolution, so do not wait long here
    # when the response is already back to 1.
    while engine.RecvMetaData.get() != 0:
        if _time.monotonic() > zero_deadline:
            break
        _time.sleep(0.001)

    # Wait for RecvMetaData → 1 (response ready)
    while engine.RecvMetaData.get() != 1:
        if _time.monotonic() > deadline:
            raise rogue.GeneralError(
                '_wait_resp',
                'Timeout waiting for RoceEngine response '
                '(RecvMetaData never went to 1)')
        _time.sleep(0.05)

    return engine.MetaDataRx.get()


# ---------------------------------------------------------------------------
# QP teardown / reconnect helpers
# ---------------------------------------------------------------------------

def _encode_dealloc_mr(pd_handler, lkey, rkey):
    """Dealloc MR: allocOrNot=0, same field layout as alloc."""
    return _mk_bus(_METADATA_MR_T,
        (0,          _MR_ALLOC_OR_NOT_B),  # allocOrNot=0
        (0,          _MR_LADDR_B),
        (0,          _MR_LEN_B),
        (0,          _MR_ACCFLAGS_B),
        (pd_handler, _MR_PDHANDLER_B),
        (0,          _MR_LKEYPART_B),
        (0,          _MR_RKEYPART_B),
        (0,          _MR_LKEYORNOT_B),
        (lkey,       _MR_KEY_B),
        (rkey,       _MR_KEY_B),
    )


def _encode_dealloc_pd(pd_handler):
    """Dealloc PD: allocOrNot=0."""
    return _mk_bus(_METADATA_PD_T,
        (0,          _PD_ALLOC_OR_NOT_B),  # allocOrNot=0
        (0,          _PD_KEY_B),
        (pd_handler, _PD_HANDLER_B),
    )


def _encode_err_qp(qpn):
    """REQ_QP_MODIFY → IBV_QPS_ERR — only IBV_QP_STATE in attr mask."""
    return _encode_modify_qp(qpn, _IBV_QP_STATE, _IBV_QPS_ERR, 1)


def _encode_destroy_qp(qpn):
    """REQ_QP_DESTROY — only valid from ERR state."""
    fields = [
        (_REQ_QP_DESTROY, _QP_REQTYPE_B),
        (0,               _QP_PDHANDLER_B),
        (qpn,             _QP_QPN_B),
        (0,               _QP_ATTRMASK_B),
    ]
    for w in [_QPA_QPSTATE_B, _QPA_CURRQPSTATE_B, _QPA_PMTU_B,
              _QPA_QKEY_B, _QPA_RQPSN_B, _QPA_SQPSN_B, _QPA_DQPN_B,
              _QPA_QPACCFLAGS_B, _QPA_CAP_B, _QPA_PKEY_B,
              _QPA_SQDRAINING_B, _QPA_MAXREADATOMIC_B, _QPA_MAXDESTRD_B,
              _QPA_RNRTIMER_B, _QPA_TIMEOUT_B, _QPA_RETRYCNT_B,
              _QPA_RNRRETRY_B, _QPI_TYPE_B, _QPI_SQSIGALL_B]:
        fields.append((0, w))
    return _mk_bus(_METADATA_QP_T, *fields)


def _roce_teardown(engine, fpga_qpn, pd_handler=0, lkey=0, rkey=0, log=None):
    """
    Full FPGA resource teardown: QP ERR → DESTROY → MR dealloc → PD dealloc.

    Sends all requests unconditionally — the firmware rejects them with
    successOrNot=False if resources are already freed, which we ignore.
    All errors are caught and logged as warnings.
    """
    def warn(msg):
        if log:
            log.warning(msg)
    def info(msg):
        if log:
            log.info(msg)

    engine.SendMetaData.set(0)
    _time.sleep(0.1)

    # Step 1: QP → ERR
    info(f"RoceEngine: teardown — sending ERR for QP 0x{fpga_qpn:06x}")
    _send_meta(engine, _encode_err_qp(fpga_qpn))
    try:
        rx = _wait_resp(engine, timeout_s=3.0)
        ok, _, state = _decode_qp_resp(rx)
        info(f"RoceEngine: ERR response ok={ok} state={state}")
    except Exception:
        warn("RoceEngine: ERR timed out — proceeding anyway")

    # Step 2: QP DESTROY
    info(f"RoceEngine: teardown — sending DESTROY for QP 0x{fpga_qpn:06x}")
    _send_meta(engine, _encode_destroy_qp(fpga_qpn))
    try:
        rx = _wait_resp(engine, timeout_s=5.0)
        ok, _, _ = _decode_qp_resp(rx)
        info(f"RoceEngine: DESTROY response ok={ok}")
    except Exception:
        warn("RoceEngine: DESTROY timed out — proceeding anyway")

    # Step 3: MR dealloc (only if we have the keys)
    if pd_handler != 0:
        info(f"RoceEngine: teardown — dealloc MR lkey=0x{lkey:08x}")
        _send_meta(engine, _encode_dealloc_mr(pd_handler, lkey, rkey))
        try:
            rx = _wait_resp(engine, timeout_s=3.0)
            ok, _, _ = _decode_mr_resp(rx)
            info(f"RoceEngine: MR dealloc response ok={ok}")
        except Exception:
            warn("RoceEngine: MR dealloc timed out — proceeding anyway")

        # Step 4: PD dealloc
        info(f"RoceEngine: teardown — dealloc PD handler=0x{pd_handler:08x}")
        _send_meta(engine, _encode_dealloc_pd(pd_handler))
        try:
            rx = _wait_resp(engine, timeout_s=3.0)
            ok, _ = _decode_pd_resp(rx)
            info(f"RoceEngine: PD dealloc response ok={ok}")
        except Exception:
            warn("RoceEngine: PD dealloc timed out — proceeding anyway")

    _time.sleep(0.1)


# ---------------------------------------------------------------------------
# Full FPGA connection sequence
# ---------------------------------------------------------------------------

def _roce_setup_connection(engine, host_qpn, host_rq_psn, host_sq_psn,
                           mr_laddr, mr_len, pmtu, min_rnr_timer=1,
                           rnr_retry=7, retry_count=3, log=None):
    """
    Drive any RoceEngine-compatible object (surf or our own) through:
    PD alloc → MR alloc → QP create → INIT → RTR → RTS.

    The FPGA is expected to be in a clean state (QP destroyed, PD freed)
    before this is called. Teardown is handled in _stop() so the firmware
    is always clean when rogue exits.

    Any failure in stages 2-6 triggers a reverse-order rollback of every
    resource that was successfully allocated before the failure, so the
    FPGA is never left with a stranded PD / MR / QP when setup aborts
    partway through.  The original exception re-raises after rollback.

    Returns (fpga_qpn, lkey, pd_handler, rkey).
    """
    def info(msg):
        if log:
            log.info(msg)

    def warn(msg):
        if log:
            log.warning(msg)

    def _rollback_step(encoder_args, wait_timeout_s):
        # Best-effort teardown step: send the encoded request, swallow any
        # response failure (timeout / StopIteration in tests / decode error).
        # We never want rollback failures to mask the original exception.
        try:
            _send_meta(engine, encoder_args)
        except Exception as e:
            warn(f"RoceEngine: rollback _send_meta failed: {e}")
            return
        try:
            _wait_resp(engine, timeout_s=wait_timeout_s)
        except Exception:
            pass

    # Ensure SendMetaData starts at 0 for a clean first rising edge
    engine.SendMetaData.set(0)
    _time.sleep(0.1)

    # 1. Alloc PD — nothing to roll back if this stage itself fails.
    _send_meta(engine, _encode_alloc_pd(_random.getrandbits(_PD_KEY_B)))
    rx = _wait_resp(engine)
    actual_type = _decode_resp_type(rx)
    if actual_type != _METADATA_PD_T:
        raise rogue.GeneralError(
            "_roce_setup_connection",
            f"Expected PD response (type=0), got type={actual_type}")
    ok, pd_handler = _decode_pd_resp(rx)
    if not ok:
        raise rogue.GeneralError(
            "_roce_setup_connection",
            "FPGA PD allocation failed — the FPGA RoCEv2 engine likely has "
            "stale resources from a previous session that crashed without a "
            "clean teardown. Reprogram the FPGA bitfile to reset its state."
        )
    info(f"RoceEngine: PD allocated handler=0x{pd_handler:08x}")

    # Past stage 1, every subsequent failure must release the PD (and any
    # MR / QP allocated since) before re-raising.  Track allocation state
    # so rollback only deallocs what actually exists on the FPGA.
    lkey = 0
    rkey = 0
    fpga_qpn = 0
    mr_allocated = False
    qp_created = False

    try:
        # 2. Alloc MR
        _send_meta(engine, _encode_alloc_mr(
            pd_handler = pd_handler,
            laddr      = mr_laddr,
            length     = mr_len,
            lkey_part  = _random.getrandbits(_MR_LKEYPART_B),
            rkey_part  = _random.getrandbits(_MR_RKEYPART_B),
        ))
        rx = _wait_resp(engine)
        actual_type = _decode_resp_type(rx)
        if actual_type != _METADATA_MR_T:
            raise rogue.GeneralError(
                "_roce_setup_connection",
                f"Expected MR response (type=1), got type={actual_type}")
        ok, lkey, rkey = _decode_mr_resp(rx)
        if not ok:
            raise rogue.GeneralError(
                "_roce_setup_connection",
                "FPGA MR allocation failed — the FPGA RoCEv2 engine likely has "
                "stale resources from a previous session that crashed without a "
                "clean teardown. Reprogram the FPGA bitfile to reset its state."
            )
        mr_allocated = True
        info(f"RoceEngine: MR allocated lkey=0x{lkey:08x} rkey=0x{rkey:08x}")

        # 3. Create QP (RC)
        _send_meta(engine, _encode_create_qp(pd_handler))
        rx = _wait_resp(engine)
        actual_type = _decode_resp_type(rx)
        if actual_type != _METADATA_QP_T:
            raise rogue.GeneralError(
                "_roce_setup_connection",
                f"Expected QP response (type=2), got type={actual_type}")
        ok, fpga_qpn, _ = _decode_qp_resp(rx)
        if not ok:
            raise rogue.GeneralError(
                "_roce_setup_connection",
                "FPGA QP creation failed — the FPGA RoCEv2 engine likely has "
                "stale resources from a previous session that crashed without a "
                "clean teardown. Reprogram the FPGA bitfile to reset its state."
            )
        qp_created = True
        info(f"RoceEngine: QP created fpga_qpn=0x{fpga_qpn:06x}")

        # 4. QP → INIT
        init_mask = _IBV_QP_STATE | _IBV_QP_PKEY_INDEX | _IBV_QP_ACCESS_FLAGS
        _send_meta(engine, _encode_modify_qp(fpga_qpn, init_mask, _IBV_QPS_INIT, pmtu))
        rx = _wait_resp(engine)
        ok, _, state = _decode_qp_resp(rx)
        if not (ok and state == _IBV_QPS_INIT):
            raise rogue.GeneralError(
                "_roce_setup_connection",
                f"FPGA QP→INIT failed (ok={ok} state={state})")
        info("RoceEngine: QP → INIT")

        # 5. QP → RTR
        rtr_mask = (_IBV_QP_STATE | _IBV_QP_PATH_MTU | _IBV_QP_DEST_QPN |
                    _IBV_QP_RQ_PSN | _IBV_QP_MAX_DEST_RD_ATOMIC | _IBV_QP_MIN_RNR_TIMER)
        _send_meta(engine, _encode_modify_qp(
            fpga_qpn, rtr_mask, _IBV_QPS_RTR, pmtu,
            dqpn=host_qpn, rq_psn=host_rq_psn,
            min_rnr_timer=min_rnr_timer))
        rx = _wait_resp(engine)
        ok, _, state = _decode_qp_resp(rx)
        if not (ok and state == _IBV_QPS_RTR):
            raise rogue.GeneralError(
                "_roce_setup_connection",
                f"FPGA QP→RTR failed (ok={ok} state={state})")
        info(f"RoceEngine: QP → RTR targeting host qpn=0x{host_qpn:06x}")

        # 6. QP → RTS
        rts_mask = (_IBV_QP_STATE | _IBV_QP_SQ_PSN | _IBV_QP_TIMEOUT |
                    _IBV_QP_RETRY_CNT | _IBV_QP_RNR_RETRY | _IBV_QP_MAX_QP_RD_ATOMIC)
        _send_meta(engine, _encode_modify_qp(
            fpga_qpn, rts_mask, _IBV_QPS_RTS, pmtu,
            sq_psn=host_sq_psn, min_rnr_timer=min_rnr_timer,
            rnr_retry=rnr_retry, retry_count=retry_count))
        rx = _wait_resp(engine)
        ok, _, state = _decode_qp_resp(rx)
        if not (ok and state == _IBV_QPS_RTS):
            raise rogue.GeneralError(
                "_roce_setup_connection",
                f"FPGA QP→RTS failed (ok={ok} state={state})")
        info("RoceEngine: QP → RTS — FPGA ready to send RDMA WRITEs")

    except Exception:
        # Reverse-order rollback of everything that was allocated so far.
        # Uses the same metadata-bus encoders as _roce_teardown but skips
        # stages whose resources were never allocated, so the rollback's
        # TX-write count matches the allocation count exactly.
        warn("RoceEngine: rolling back partial setup")
        if qp_created:
            _rollback_step(_encode_err_qp(fpga_qpn),       3.0)
            _rollback_step(_encode_destroy_qp(fpga_qpn),   5.0)
        if mr_allocated:
            _rollback_step(_encode_dealloc_mr(pd_handler, lkey, rkey), 3.0)
        _rollback_step(_encode_dealloc_pd(pd_handler), 3.0)
        raise

    if log:
        log.info("=" * 60)
        log.info("RoCEv2 FPGA connection summary")
        log.info(f"  FPGA QPN    : 0x{fpga_qpn:06x}")
        log.info(f"  FPGA lkey   : 0x{lkey:08x}")
        log.info("  FPGA state  : RTS (ready to send RDMA WRITEs)")
        log.info(f"  Host QPN    : 0x{host_qpn:06x}")
        log.info(f"  Host RQ PSN : 0x{host_rq_psn:06x}")
        log.info(f"  Host SQ PSN : 0x{host_sq_psn:06x}")
        log.info(f"  MR addr     : 0x{mr_laddr:016x}")
        log.info(f"  MR length   : {mr_len} bytes")
        log.info(f"  Path MTU    : {pmtu} ({[256,512,1024,2048,4096][pmtu-1]} bytes)")
        log.info("=" * 60)

    return fpga_qpn, lkey, pd_handler, rkey


# ---------------------------------------------------------------------------
# RoCEv2Server — pyrogue Device
# ---------------------------------------------------------------------------

class RoCEv2Server(pr.Device):
    """
    RoCEv2 RC receive server — pyrogue Device.

    Mirrors the interface of UdpRssiPack so the two can be used
    interchangeably inside a Root.

    Parameters
    ----------
    ip : str
        FPGA IP address. Used to derive the FPGA GID (IPv4-mapped IPv6).
    deviceName : str
        ibverbs device name (e.g. 'rxe0' for softRoCE, 'mlx5_0' for HW NIC).
    ibPort : int
        ibverbs port number (default: 1).
    gidIndex : int
        GID table index for the host NIC's RoCEv2 IPv4 address.
    maxPayload : int
        Maximum bytes per RDMA WRITE (default: 9000).
    rxQueueDepth : int
        Number of pre-posted receive slots (default: 256).
    roceEngineOffset : int
        AXI-lite offset of the RoCEv2 engine register block.
    roceMemBase : object
        memBase for the RoceEngine child device (the SRP object).
    roceEngine : object
        Pass an existing RoceEngine instance to avoid duplicate address mapping.
        When set, no child RoceEngine device is created.
    pmtu : int
        Path MTU enum: 1=256 2=512 3=1024 4=2048 5=4096 (default: 5).
    minRnrTimer : int
        IB-spec RNR NAK timer code embedded in the QP attributes on RTR.
        1=0.01ms, 14=1ms, 18=4ms, 22=16ms, 31=491ms (default: 31).
    rnrRetry : int
        FPGA QP RNR retry count. 7 means "retry indefinitely" (default: 7).
    retryCount : int
        FPGA QP retry count for non-RNR transport errors (default: 3).
    pollInterval : int
        Poll interval in seconds for status variables (default: 1).
    """

    def __init__(
        self,
        *,
        ip:               str,
        deviceName:       str,
        ibPort:           int    = 1,
        gidIndex:         int    = 0,
        maxPayload:       int    = 9000,
        rxQueueDepth:     int    = 256,
        roceEngineOffset: int    = 0,
        roceMemBase               = None,
        roceEngine                = None,
        pmtu:             int    = 5,
        minRnrTimer:      int    = 31,   # IB spec: 31 = 491ms, 1 = 0.01ms
        rnrRetry:         int    = 7,    # FPGA RNR retry count (7 = infinite)
        retryCount:       int    = 3,    # FPGA retry count for other errors
        pollInterval:     int    = 1,
        **kwargs,
    ) -> None:
        if not _ROCEV2_AVAILABLE:
            raise ImportError(
                "RoCEv2Server requires a Linux build of rogue with "
                "libibverbs/rdma-core available at runtime.  Install "
                "rdma-core (`conda install -c conda-forge rdma-core` or "
                "`apt install libibverbs-dev`) and rebuild rogue on Linux "
                "with those libraries available."
            )
        if not (1 <= pmtu <= 5):
            raise rogue.GeneralError(
                "RoCEv2Server.__init__",
                f"pmtu must be in the range 1..5 (1=256 2=512 3=1024 "
                f"4=2048 5=4096); got {pmtu}",
            )
        super().__init__(**kwargs)

        self._deviceName    = deviceName
        self._ibPort        = ibPort
        self._gidIndex      = gidIndex
        self._maxPayload    = maxPayload
        self._rxQueueDepth  = rxQueueDepth
        self._pmtu          = pmtu
        self._minRnrTimer   = minRnrTimer
        self._rnrRetry      = rnrRetry
        self._retryCount    = retryCount
        self._extRoceEngine = roceEngine
        self._fpga_qpn        = 0   # set after successful connection
        self._fpga_pd_handler = 0
        self._fpga_lkey       = 0
        self._fpga_rkey       = 0
        self._fpgaGidBytes  = _ip_to_gid_bytes(ip)

        # C++ RC server — ibverbs resources up to QP INIT
        self._server = rogue.protocols.rocev2.Server.create(
            deviceName, ibPort, gidIndex, maxPayload, rxQueueDepth)

        # Add RoceEngine child only if no external engine was provided
        if roceEngine is None:
            from surf.ethernet.roce._RoceEngine import RoceEngine as _RE
            self.add(_RE(
                name    = 'RoceEngine',
                offset  = roceEngineOffset,
                memBase = roceMemBase,
            ))

        # Status variables
        self.add(pr.LocalVariable(
            name='FpgaIp', mode='RO', value=ip,
            description='FPGA IP address used for GID derivation'))

        self.add(pr.LocalVariable(
            name='FpgaGid', mode='RO',
            value=_gid_bytes_to_str(self._fpgaGidBytes),
            description='FPGA GID (IPv4-mapped IPv6)'))

        self.add(pr.LocalVariable(
            name='HostQpn', mode='RO', value=0, typeStr='UInt32',
            localGet=lambda: self._server.getQpn(),
            description='Host RC QP number'))

        self.add(pr.LocalVariable(
            name='HostGid', mode='RO', value='',
            localGet=lambda: self._server.getGid(),
            description='Host GID (NIC RoCEv2 address)'))

        self.add(pr.LocalVariable(
            name='MrAddr', mode='RO', value=0, typeStr='UInt64',
            localGet=lambda: self._server.getMrAddr(),
            description='Host MR virtual address (FPGA writes here)'))

        self.add(pr.LocalVariable(
            name='MrRkey', mode='RO', value=0, typeStr='UInt32',
            localGet=lambda: self._server.getMrRkey(),
            description='Host MR rkey (given to FPGA)'))

        self.add(pr.LocalVariable(
            name='RxFrameCount', mode='RO', value=0, typeStr='UInt64',
            localGet=lambda: self._server.getFrameCount(),
            pollInterval=pollInterval,
            description='Total frames received'))

        self.add(pr.LocalVariable(
            name='RxByteCount', mode='RO', value=0, typeStr='UInt64',
            localGet=lambda: self._server.getByteCount(),
            pollInterval=pollInterval,
            description='Total bytes received'))

        self.add(pr.LocalVariable(
            name='ConnectionState', mode='RO', value='Disconnected',
            description='RC connection state'))

        self.add(pr.LocalVariable(
            name        = 'MaxPayload',
            description = 'Max payload bytes per RDMA WRITE slot',
            mode        = 'RO',
            value       = maxPayload,
            typeStr     = 'UInt32',
        ))

        self.add(pr.LocalVariable(
            name        = 'RxQueueDepth',
            description = 'Number of receive slots (rxQueueDepth)',
            mode        = 'RO',
            value       = rxQueueDepth,
            typeStr     = 'UInt32',
        ))

        self.add(pr.LocalVariable(
            name        = 'HostRqPsn',
            description = 'Host starting receive PSN — FPGA SQ PSN must match this',
            mode        = 'RO',
            value       = 0,
            typeStr     = 'UInt32',
            localGet    = lambda: self._server.getRqPsn(),
        ))

        self.add(pr.LocalVariable(
            name        = 'HostSqPsn',
            description = 'Host starting send PSN — FPGA RQ PSN must match this',
            mode        = 'RO',
            value       = 0,
            typeStr     = 'UInt32',
            localGet    = lambda: self._server.getSqPsn(),
        ))

        self.add(pr.LocalVariable(
            name        = 'FpgaQpn',
            description = 'FPGA QP number — set after RC connection is established',
            mode        = 'RO',
            value       = 0,
            typeStr     = 'UInt32',
        ))

        self.add(pr.LocalVariable(
            name        = 'FpgaLkey',
            description = 'FPGA MR local key — set after RC connection is established',
            mode        = 'RO',
            value       = 0,
            typeStr     = 'UInt32',
        ))

    @property
    def stream(self):
        """Direct access to the C++ stream master — receives every channel
        the FPGA emits.  Use ``getChannel(n)`` instead to get a filtered
        view of a single RDMA-immediate channel id (the per-channel
        analogue of ``UdpRssiPack.application(n)``)."""
        return self._server

    def getChannel(self, channel: int):
        """Return a channel-filtered view (channel id from immediate value bits [7:0]).

        The RDMA WRITE-with-Immediate carries the channel id in the low 8
        bits of the immediate value (Server.cpp runThread decodes
        `wc.imm_data & 0xFF`), so valid channel ids are 0..255.  Out-of-
        range values would previously blow up with `OverflowError` inside
        the Filter ctor — validate up front and raise a clear
        `rogue.GeneralError` instead.
        """
        if not 0 <= channel <= 0xFF:
            raise rogue.GeneralError(
                "RoCEv2Server.getChannel",
                f"channel must be in the range 0..255 (bits [7:0] of the "
                f"RDMA immediate value, see Server.cpp::runThread); "
                f"got {channel}")
        filt = rogue.interfaces.stream.Filter(False, channel)
        self._server >> filt
        return filt

    def _start(self) -> None:
        self.ConnectionState.set('Connecting')

        # Push FPGA GID to C++ server
        self._server.setFpgaGid(bytes(self._fpgaGidBytes))

        host_qpn    = self._server.getQpn()
        host_rq_psn = self._server.getRqPsn()
        host_sq_psn = self._server.getSqPsn()
        mr_addr     = self._server.getMrAddr()
        mr_len      = self._maxPayload * self._rxQueueDepth

        if mr_len >= (1 << 32):
            raise rogue.GeneralError(
                f"FPGA MR length {mr_len} bytes ({mr_len / 2**30:.1f} GiB) exceeds "
                f"the 32-bit field of the metadata bus. "
                f"Reduce --roceMaxPay ({self._maxPayload}) or --roceQDepth ({self._rxQueueDepth})."
            )

        self._log.info(
            f"RoCEv2 '{self.name}': QPN=0x{host_qpn:06x} "
            f"GID={self._server.getGid()} "
            f"MR=0x{mr_addr:016x} rkey=0x{self._server.getMrRkey():08x} "
            f"FPGA GID={_gid_bytes_to_str(self._fpgaGidBytes)}"
        )

        _engine = (self._extRoceEngine if self._extRoceEngine is not None
                   else self.RoceEngine)

        fpga_qpn, fpga_lkey, fpga_pd_handler, fpga_rkey = _roce_setup_connection(
            engine        = _engine,
            host_qpn      = host_qpn,
            host_rq_psn   = host_rq_psn,
            host_sq_psn   = host_sq_psn,
            mr_laddr      = mr_addr,
            mr_len        = mr_len,
            pmtu          = self._pmtu,
            min_rnr_timer = self._minRnrTimer,
            rnr_retry     = self._rnrRetry,
            retry_count   = self._retryCount,
            log           = self._log,
        )

        # Capture shadow state immediately after the FPGA-side resources
        # are live so teardownFpgaQp() can reach them even if the host-side
        # completeConnection() below raises (otherwise the FPGA's PD / MR /
        # QP would leak — _roce_teardown's internal rollback only covers
        # failures inside _roce_setup_connection itself).
        self._fpga_qpn        = fpga_qpn
        self._fpga_pd_handler = fpga_pd_handler
        self._fpga_lkey       = fpga_lkey
        self._fpga_rkey       = fpga_rkey

        self._server.completeConnection(
            fpgaQpn     = fpga_qpn,
            fpgaRqPsn   = host_sq_psn,
            pmtu        = self._pmtu,
            minRnrTimer = self._minRnrTimer,
        )

        self.FpgaQpn.set(fpga_qpn)
        self.FpgaLkey.set(fpga_lkey)
        self.ConnectionState.set('Connected')
        self._log.info("=" * 60)
        self._log.info("RoCEv2 host RC connection summary")
        self._log.info(f"  Device      : {self._deviceName}  port={self._ibPort}  GID idx={self._gidIndex}")
        self._log.info(f"  Host QPN    : 0x{host_qpn:06x}")
        self._log.info(f"  Host GID    : {self._server.getGid()}")
        self._log.info("  Host state  : RTS")
        self._log.info(f"  MR addr     : 0x{mr_addr:016x}")
        self._log.info(f"  MR rkey     : 0x{self._server.getMrRkey():08x}")
        self._log.info(f"  MR size     : {mr_len} bytes  ({self._rxQueueDepth} slots x {self._maxPayload} bytes)")
        self._log.info(f"  FPGA QPN    : 0x{fpga_qpn:06x}")
        self._log.info(f"  FPGA lkey   : 0x{fpga_lkey:08x}")
        self._log.info(f"  FPGA GID    : {_gid_bytes_to_str(self._fpgaGidBytes)}")
        self._log.info(f"  Path MTU    : {self._pmtu} ({[256,512,1024,2048,4096][self._pmtu-1]} bytes)")
        self._log.info(f"  MinRnrTimer : {self._minRnrTimer}")
        self._log.info(f"  RnrRetry    : {self._rnrRetry}")
        self._log.info(f"  RetryCount  : {self._retryCount}")
        self._log.info("  RC connection established — ready to receive RDMA WRITEs")
        self._log.info("=" * 60)

        super()._start()

    def teardownFpgaQp(self) -> None:
        """
        Tear down the FPGA QP via the metadata bus.
        Called explicitly from Root.stop() before the transport is torn down.
        """
        fpga_qpn = self._fpga_qpn
        if fpga_qpn == 0:
            return
        _engine = self._extRoceEngine if self._extRoceEngine is not None else self.RoceEngine
        try:
            self._log.info(
                f"RoCEv2 '{self.name}': tearing down FPGA QP 0x{fpga_qpn:06x}")
            _roce_teardown(_engine, fpga_qpn,
                           pd_handler = self._fpga_pd_handler,
                           lkey       = self._fpga_lkey,
                           rkey       = self._fpga_rkey,
                           log        = self._log)
            self._fpga_qpn        = 0
            self._fpga_pd_handler = 0
            self._fpga_lkey       = 0
            self._fpga_rkey       = 0
            self.FpgaQpn.set(0)
            self.FpgaLkey.set(0)
        except Exception as e:
            self._log.warning(f"RoCEv2 teardown failed: {e}")

    def _stop(self) -> None:
        # Tear down the FPGA QP before stopping the host-side server or
        # propagating stop() to children — RoceEngine must still be alive
        # to drive the metadata bus. teardownFpgaQp() is a no-op when the
        # FPGA QPN is 0 (never connected or already torn down).
        self.teardownFpgaQp()
        self._server.stop()
        self.ConnectionState.set('Disconnected')
        super()._stop()
