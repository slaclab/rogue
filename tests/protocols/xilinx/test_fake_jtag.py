#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
"""Unit tests for FakeJtag.

These tests exercise:

  * The pure-Python scan-chain oracle (`FakeJtag.expected_tdo`).
  * The AxisToJtag header layout for CMD_Q and CMD_S replies.
  * Word-by-word interleaved TMS/TDI parsing (per JtagDriver::sendVectors).
  * XID preservation across shift round-trips.
  * Trailing-bit masking in the last TDO byte.

Zero Xvc C++ server / TCP involvement.  A `_Source(ris.Master)` and
`_Sink(ris.Slave)` are wired up in a local stream graph:

    source  -->  fake  -->  sink
      push        _acceptFrame reply

After `source.push(req_bytes)` returns, the sink has captured the reply
frame; the test reads its payload and asserts byte-level layout.
"""
import struct
import threading

import pytest

import rogue.interfaces.stream as ris

from fake_jtag import FakeJtag


# ---------------------------------------------------------------------------
# Stream graph scaffolding (in-process, no TCP, no Xvc C++).
# ---------------------------------------------------------------------------


class _Source(ris.Master):
    """Minimal ris.Master that emits an arbitrary byte payload as a frame."""

    def push(self, payload):
        frame = self._reqFrame(len(payload), True)
        frame.write(bytearray(payload), 0)
        self._sendFrame(frame)


class _Sink(ris.Slave):
    """ris.Slave that records every received frame as bytes."""

    def __init__(self):
        ris.Slave.__init__(self)
        self._lock   = threading.Lock()
        self.frames  = []

    def _acceptFrame(self, frame):
        with self._lock:
            size = frame.getPayload()
            buf  = bytearray(size)
            frame.read(buf, 0)
            self.frames.append(bytes(buf))


def _wire(word_size=4, mem_depth=1, period_raw=0):
    """Build source -> fake -> sink; return (source, fake, sink)."""
    source = _Source()
    fake   = FakeJtag(word_size=word_size, mem_depth=mem_depth,
                     period_raw=period_raw)
    sink   = _Sink()
    source._addSlave(fake)
    fake._addSlave(sink)
    return source, fake, sink


# ---------------------------------------------------------------------------
# Request builders (mirror JtagDriver.cpp layout).
# ---------------------------------------------------------------------------


def _mk_query_req(word_size=4):
    """CMD_Q request: one header word, zero-padded to word_size."""
    hdr = 0x00000000  # PVERS=0 | CMD_Q=0 | XID_ANY=0
    req = bytearray(word_size)
    struct.pack_into("<I", req, 0, hdr)
    return bytes(req), 0  # (req_bytes, xid)


def _mk_shift_req(nbits, tms, tdi, word_size=4, xid=0x42):
    """CMD_S request: header word + word-by-word interleaved TMS/TDI."""
    wsz         = word_size
    bytes_ceil  = (nbits + 7) // 8
    whole_words = bytes_ceil // wsz
    whole_wb    = whole_words * wsz
    bytes_left  = bytes_ceil - whole_wb
    word_ceil   = ((bytes_ceil + wsz - 1) // wsz) * wsz

    hdr  = 0x10000000                    # PVERS=0 | CMD_S
    hdr |= (xid & 0xFF) << 20
    hdr |= (nbits - 1) & 0x000FFFFF

    req = bytearray(wsz + 2 * word_ceil)
    struct.pack_into("<I", req, 0, hdr)

    w = wsz  # write cursor; start past header
    for idx in range(0, whole_wb, wsz):
        req[w:w + wsz]       = tms[idx:idx + wsz]
        w += wsz
        req[w:w + wsz]       = tdi[idx:idx + wsz]
        w += wsz

    if bytes_left:
        req[w:w + bytes_left] = tms[whole_wb:whole_wb + bytes_left]
        w += wsz
        req[w:w + bytes_left] = tdi[whole_wb:whole_wb + bytes_left]
        w += wsz

    return bytes(req), xid


# ===========================================================================
# 1. Pure oracle determinism
# ===========================================================================


def test_expected_tdo_deterministic():
    tms = b'\xAA\x55\x0F\xF0'
    tdi = b'\x5A\xA5\xC3\x3C'
    a = FakeJtag.expected_tdo(32, tms, tdi)
    b = FakeJtag.expected_tdo(32, tms, tdi)
    c = FakeJtag.expected_tdo(32, tms, tdi)
    assert a == b == c
    # And bit-exact against the spec:
    assert a == bytes([(tms[i] ^ tdi[i] ^ 0x5A) & 0xFF for i in range(4)])


@pytest.mark.parametrize("nbits", [1, 7, 8, 9, 15, 16, 17, 32, 64])
def test_expected_tdo_byte_count(nbits):
    # Use deterministic patterns sized generously (ceil(64/8) = 8 bytes max).
    tms = bytes([(0x5A + i) & 0xFF for i in range(8)])
    tdi = bytes([(0xA5 - i) & 0xFF for i in range(8)])
    out = FakeJtag.expected_tdo(nbits, tms, tdi)
    assert len(out) == (nbits + 7) // 8


def test_scan_chain_trailing_bits_masked():
    # nbits=9 -> 1 bit of real data in byte[1]; bits 1..7 must be zero.
    tms = b'\xAA\xFF'
    tdi = b'\x55\xFF'
    out = FakeJtag.expected_tdo(9, tms, tdi)
    assert len(out) == 2
    # bit0 = (0xFF ^ 0xFF ^ 0x5A) & 0x01 = 0x5A & 0x01 = 0
    assert out[1] == 0
    # bits 1..7 of out[1] must be zero regardless of input.
    assert out[1] & 0xFE == 0


# ===========================================================================
# 2. CMD_Q reply header layout
# ===========================================================================


def test_query_reply_header_layout():
    source, fake, sink = _wire(word_size=4, mem_depth=1, period_raw=0)
    req, xid = _mk_query_req(word_size=4)

    source.push(req)

    assert len(sink.frames) == 1, "fake did not reply to CMD_Q"
    reply = sink.frames[0]
    assert len(reply) == 4   # word_size bytes, no payload

    hdr = struct.unpack("<I", reply[:4])[0]
    # JtagDriver::wordSize(reply) = (reply & 0x0F) + 1 == word_size
    assert (hdr & 0x0F) + 1 == fake.word_size
    # JtagDriver::memDepth(reply) = (reply >> 4) & 0xFFFF == mem_depth
    assert (hdr >> 4) & 0xFFFF == fake.mem_depth
    # JtagDriver::cvtPerNs raw byte = (reply >> 20) & 0xFF == period_raw (0)
    assert (hdr >> 20) & 0xFF == fake.period_raw
    # CMD == CMD_Q
    assert (hdr & 0x30000000) == 0x00000000
    # Calls log updated
    assert fake.calls == [("query", xid)]


def test_query_reply_reports_custom_params():
    source, _fake, _sink = _wire(word_size=4, mem_depth=7, period_raw=0x42)
    # period_raw lives in the XID slot; _query_reply_hdr only installs it
    # when xid == 0 (the XID_ANY convention used by Xvc for queries).
    source.push(_mk_query_req(word_size=4)[0])
    hdr = struct.unpack("<I", _sink.frames[0][:4])[0]
    assert (hdr & 0x0F) + 1       == 4
    assert (hdr >> 4) & 0xFFFF    == 7
    assert (hdr >> 20) & 0xFF     == 0x42


# ===========================================================================
# 3. CMD_S reply layout + TDO correctness
# ===========================================================================


@pytest.mark.parametrize("nbits", [1, 8, 32])
def test_shift_reply_payload_length(nbits):
    tms = bytes([(0x5A + i) & 0xFF for i in range(8)])
    tdi = bytes([(0xA5 - i) & 0xFF for i in range(8)])
    source, fake, sink = _wire()
    req, xid = _mk_shift_req(nbits, tms, tdi, xid=0x17)

    source.push(req)

    assert len(sink.frames) == 1
    reply = sink.frames[0]
    bytes_ceil = (nbits + 7) // 8
    # Reply = header word + TDO bytes.
    assert len(reply) == fake.word_size + bytes_ceil

    tdo = reply[fake.word_size:]
    assert tdo == FakeJtag.expected_tdo(nbits, tms, tdi)
    # Calls log
    assert fake.calls == [("shift", 0x17, nbits)]


def test_shift_preserves_xid():
    tms = b'\xAB'
    tdi = b'\xCD'
    source, _fake, sink = _wire()
    req, xid = _mk_shift_req(8, tms, tdi, xid=0x99)

    source.push(req)

    hdr = struct.unpack("<I", sink.frames[0][:4])[0]
    # XID in bits 20-27 must echo the request XID.
    assert (hdr >> 20) & 0xFF == 0x99
    # CMD bits == CMD_S
    assert (hdr & 0x30000000) == 0x10000000
    # LEN bits == nbits - 1
    assert (hdr & 0x000FFFFF) == 8 - 1


def test_shift_partial_word_layout():
    # nbits=9 exercises the bytes_left tail path in both request builder and
    # FakeJtag._parse_shift_vectors.
    tms = b'\xAB\x01'
    tdi = b'\xCD\x00'
    source, fake, sink = _wire()
    req, _xid = _mk_shift_req(9, tms, tdi, xid=0x33)

    source.push(req)

    reply = sink.frames[0]
    tdo = reply[fake.word_size:]
    assert tdo == FakeJtag.expected_tdo(9, tms, tdi)
    assert len(tdo) == 2
    # Second byte has only bit 0 valid; bits 1..7 must be zero.
    assert tdo[1] & 0xFE == 0


def test_shift_64_bits_round_trip():
    # nbits=64 exercises the full 8-byte (2 whole-word) interleave path.
    tms = bytes(range(8))
    tdi = bytes(range(0xF0, 0xF8))
    source, fake, sink = _wire()
    req, _xid = _mk_shift_req(64, tms, tdi, xid=0x55)

    source.push(req)

    tdo = sink.frames[0][fake.word_size:]
    assert len(tdo) == 8
    assert tdo == bytes([(tms[i] ^ tdi[i] ^ 0x5A) & 0xFF for i in range(8)])


# ===========================================================================
# 4. Unknown-command error path
# ===========================================================================


def test_unknown_command_emits_error_reply():
    source, fake, sink = _wire()
    # CMD_E itself is an "error" command; the fake treats unknown CMDs as
    # errors, which means CMD_E requests are unknown here too.
    hdr = 0x20000000 | (0x77 << 20)  # CMD_E with XID=0x77
    req = bytearray(4)
    struct.pack_into("<I", req, 0, hdr)
    source.push(bytes(req))

    assert len(sink.frames) == 1
    reply_hdr = struct.unpack("<I", sink.frames[0][:4])[0]
    # CMD bits must be CMD_E (0b10 << 28)
    assert (reply_hdr & 0x30000000) == 0x20000000
    # XID preserved
    assert (reply_hdr >> 20) & 0xFF == 0x77
