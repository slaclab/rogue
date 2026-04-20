#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
"""Fake JTAG endpoint for the Xvc stream graph.

`FakeJtag` is a `rogue.interfaces.stream.Slave` + `Master` hybrid that:

  1. Receives AxisToJtag request frames from `Xvc::xfer()` (downstream Slave).
  2. Parses the 32-bit little-endian header (see JtagDriver::getHdr).
  3. For CMD_Q (query): replies with (wordSize-1, memDepth, periodRaw)
     packed per JtagDriver::wordSize/memDepth/cvtPerNs (word-size byte reply).
  4. For CMD_S (shift): parses TMS / TDI per sendVectors (word-by-word
     interleaved; see JtagDriver::sendVectors), computes TDO via a
     deterministic scan-chain model, and replies with header + TDO.
  5. Sends the reply frame back upstream (as Master) into Xvc::acceptFrame,
     which queues it for the blocking xfer() pop.

Scan-chain model: TDO[i] = TMS[i] ^ TDI[i] ^ 0x5A, with trailing bits in the
last byte masked to zero (only the low `nbits % 8` bits kept).  This is
deterministic, pure, and reversible -- same (nbits, tms, tdi) -> same TDO
every run across any number of invocations.

The `expected_tdo(nbits, tms, tdi) -> bytes` staticmethod is a pure-Python
oracle that callers can use to assert TDO without instantiating FakeJtag.
"""
import struct
import threading

import rogue.interfaces.stream as ris


class FakeJtag(ris.Master, ris.Slave):
    """Deterministic fake JTAG endpoint for Xvc stream-graph tests.

    Parameters
    ----------
    word_size : int, default 4
        Bytes per frame "word" -- reported in the CMD_Q reply and used as
        the header size on both request and reply frames.
    mem_depth : int, default 1
        Target memory depth in words (reported in CMD_Q reply).  With
        word_size=4 and mem_depth=1, the XVC server computes
        supVecLen_ = 4 bytes = 32 bits, so nbits=64 splits into 2 chunks.
    period_raw : int, default 0
        The raw period byte reported in CMD_Q reply bits 20-27.  0 ==
        UNKNOWN_PERIOD (see JtagDriver::cvtPerNs).
    """

    # --- AxisToJtag protocol constants (mirror JtagDriver.h) ---
    PVERS       = 0x00000000  # bits 30-31 = 0
    CMD_Q       = 0x00000000  # bits 28-29 = 0b00
    CMD_S       = 0x10000000  # bits 28-29 = 0b01
    CMD_E       = 0x20000000  # bits 28-29 = 0b10 (error reply)
    CMD_MASK    = 0x30000000
    XID_SHIFT   = 20
    XID_MASK    = 0x0FF00000
    LEN_MASK    = 0x000FFFFF   # CMD_S: nbits - 1

    # XOR mask for the scan-chain model (picked so 0^0^mask != 0 and
    # mask^mask^mask = mask -- any non-zero / non-trivial constant works).
    SCAN_XOR = 0x5A

    def __init__(self, word_size=4, mem_depth=1, period_raw=0):
        ris.Master.__init__(self)
        ris.Slave.__init__(self)

        if word_size < 4:
            raise ValueError("word_size must be >= 4 (header is 4 bytes)")
        if not (0 <= period_raw <= 0xFF):
            raise ValueError("period_raw must fit in 8 bits")
        if not (1 <= mem_depth <= 0xFFFF):
            raise ValueError("mem_depth must fit in 16 bits")

        self.word_size  = int(word_size)
        self.mem_depth  = int(mem_depth)
        self.period_raw = int(period_raw)

        # _acceptFrame may be invoked on the Xvc C++ worker thread.
        self._lock = threading.Lock()

        # Test-observable log of every request the fake served.
        # Each entry is a tuple: ("query", xid)  or  ("shift", xid, nbits).
        self.calls = []

    # ------------------------------------------------------------------
    # Pure oracle -- usable without instantiating FakeJtag.
    # ------------------------------------------------------------------
    @staticmethod
    def expected_tdo(nbits, tms, tdi):
        """Compute the deterministic TDO vector for a given (tms, tdi).

        Parameters
        ----------
        nbits : int
            Number of shift bits.  Must be > 0.
        tms : bytes-like
            TMS vector, at least ceil(nbits/8) bytes.
        tdi : bytes-like
            TDI vector, at least ceil(nbits/8) bytes.

        Returns
        -------
        bytes
            Exactly ceil(nbits/8) bytes.  Trailing bits above `nbits`
            in the last byte are zeroed.
        """
        if nbits <= 0:
            raise ValueError("nbits must be > 0")

        n_bytes = (nbits + 7) // 8
        out = bytearray(n_bytes)
        for i in range(n_bytes):
            out[i] = (tms[i] ^ tdi[i] ^ FakeJtag.SCAN_XOR) & 0xFF

        trailing = nbits % 8
        if trailing:
            mask = (1 << trailing) - 1
            out[-1] &= mask

        return bytes(out)

    # ------------------------------------------------------------------
    # AxisToJtag header helpers (little-endian u32).
    # ------------------------------------------------------------------
    @classmethod
    def _get_cmd(cls, hdr):
        return hdr & cls.CMD_MASK

    @classmethod
    def _get_xid(cls, hdr):
        return (hdr & cls.XID_MASK) >> cls.XID_SHIFT

    @classmethod
    def _get_nbits(cls, hdr):
        # CMD_S: LEN field = nbits - 1 (see JtagDriver::mkShift).
        return (hdr & cls.LEN_MASK) + 1

    def _query_reply_hdr(self, xid):
        # JtagDriver::wordSize(reply) = (reply & 0x0F) + 1  -> store word_size-1
        # JtagDriver::memDepth(reply) = (reply >> 4) & 0xFFFF
        # JtagDriver::cvtPerNs uses bits 20-27 as raw period byte (0 == UNKNOWN)
        hdr  = self.PVERS | self.CMD_Q
        hdr |= (xid & 0xFF) << self.XID_SHIFT  # preserve XID (XID_ANY echoes as 0)
        hdr |= (self.word_size - 1) & 0x0F
        hdr |= (self.mem_depth & 0xFFFF) << 4
        # cvtPerNs reads (reply >> 20) & 0xFF == (xid | period_raw).  Per
        # JtagDriver::cvtPerNs we need the low 8 bits to be period_raw.
        # But bits 20-27 are the XID field.  The C++ driver treats this
        # field as the period byte only when reading the QUERY reply and
        # reports XID_ANY=0 on query by convention.  We therefore OR
        # period_raw into the XID byte when xid == 0 (the XID_ANY case
        # that Xvc uses for queries).  If a caller sends a non-zero XID
        # in a query (unusual), we still echo it verbatim and let the
        # periodRaw field collide, matching the literal bit layout.
        if xid == 0:
            hdr |= (self.period_raw & 0xFF) << self.XID_SHIFT
        return hdr

    def _shift_reply_hdr(self, xid, nbits):
        hdr  = self.PVERS | self.CMD_S
        hdr |= (xid & 0xFF) << self.XID_SHIFT
        hdr |= (nbits - 1) & self.LEN_MASK
        return hdr

    # ------------------------------------------------------------------
    # Frame helpers.
    # ------------------------------------------------------------------
    def _send_payload(self, payload):
        """Allocate a frame, write `payload` bytes at offset 0, send it."""
        frame = self._reqFrame(len(payload), True)
        ba    = bytearray(payload)
        frame.write(ba, 0)
        self._sendFrame(frame)

    # ------------------------------------------------------------------
    # Shift parsing per JtagDriver::sendVectors (word-by-word interleave).
    # ------------------------------------------------------------------
    def _parse_shift_vectors(self, body, nbits, wsz):
        """Un-interleave TMS / TDI from the word-by-word interleaved body.

        Layout (see JtagDriver::sendVectors):
            for each whole word (wsz bytes):
                wsz bytes TMS, then wsz bytes TDI
            if bytesLeft (last partial word):
                bytesLeft of TMS, pad to wsz, then bytesLeft of TDI, pad.

        Returns (tms, tdi) as bytes, each exactly ceil(nbits/8) long.
        """
        bytes_ceil      = (nbits + 7) // 8
        whole_words     = bytes_ceil // wsz
        whole_word_bytes = whole_words * wsz
        bytes_left      = bytes_ceil - whole_word_bytes

        tms = bytearray(bytes_ceil)
        tdi = bytearray(bytes_ceil)

        # Whole words: [tms(wsz)][tdi(wsz)] pairs.
        src = 0
        for idx in range(0, whole_word_bytes, wsz):
            tms[idx:idx + wsz] = body[src:src + wsz]
            src += wsz
            tdi[idx:idx + wsz] = body[src:src + wsz]
            src += wsz

        # Partial tail: wsz bytes of TMS (partial+pad) then wsz bytes of TDI.
        if bytes_left:
            tms[whole_word_bytes:bytes_ceil] = body[src:src + bytes_left]
            src += wsz  # skip full word slot (bytes_left valid, rest padding)
            tdi[whole_word_bytes:bytes_ceil] = body[src:src + bytes_left]
            src += wsz

        return bytes(tms), bytes(tdi)

    # ------------------------------------------------------------------
    # ris.Slave override: called by Xvc (upstream Master) for every frame.
    # ------------------------------------------------------------------
    def _acceptFrame(self, frame):
        with self._lock:
            size = frame.getPayload()
            if size < 4:
                # Malformed -- cannot even read header.  Drop silently.
                return

            buf = bytearray(size)
            frame.read(buf, 0)

            hdr = struct.unpack("<I", bytes(buf[:4]))[0]
            cmd = self._get_cmd(hdr)
            xid = self._get_xid(hdr)

            if cmd == self.CMD_Q:
                self.calls.append(("query", xid))
                reply_hdr = self._query_reply_hdr(xid)
                reply     = bytearray(self.word_size)
                struct.pack_into("<I", reply, 0, reply_hdr)
                self._send_payload(bytes(reply))
                return

            if cmd == self.CMD_S:
                nbits      = self._get_nbits(hdr)
                bytes_ceil = (nbits + 7) // 8
                wsz        = self.word_size

                # Body starts at wsz (header may pad past 4 bytes).
                # sendVectors uses ceil(bytes_ceil / wsz) * wsz * 2 bytes
                # of interleaved TMS/TDI payload after the header word.
                word_ceil_bytes = ((bytes_ceil + wsz - 1) // wsz) * wsz
                body_len        = 2 * word_ceil_bytes
                body_end        = wsz + body_len

                if size < body_end:
                    # Truncated -- emit error reply preserving XID.
                    err_hdr  = self.PVERS | self.CMD_E
                    err_hdr |= (xid & 0xFF) << self.XID_SHIFT
                    err_hdr |= 0x3  # ERR_TRUNCATED
                    reply = bytearray(self.word_size)
                    struct.pack_into("<I", reply, 0, err_hdr)
                    self._send_payload(bytes(reply))
                    return

                body = bytes(buf[wsz:body_end])
                tms, tdi = self._parse_shift_vectors(body, nbits, wsz)
                tdo = self.expected_tdo(nbits, tms, tdi)

                self.calls.append(("shift", xid, nbits))

                # Reply = header word + TDO bytes (bytes_ceil long, unpadded).
                reply_hdr = self._shift_reply_hdr(xid, nbits)
                reply     = bytearray(self.word_size + bytes_ceil)
                struct.pack_into("<I", reply, 0, reply_hdr)
                reply[self.word_size:self.word_size + bytes_ceil] = tdo
                self._send_payload(bytes(reply))
                return

            # Unknown command -- emit BAD_COMMAND error reply.
            err_hdr  = self.PVERS | self.CMD_E
            err_hdr |= (xid & 0xFF) << self.XID_SHIFT
            err_hdr |= 0x2  # ERR_BAD_COMMAND
            reply = bytearray(self.word_size)
            struct.pack_into("<I", reply, 0, err_hdr)
            self._send_payload(bytes(reply))
