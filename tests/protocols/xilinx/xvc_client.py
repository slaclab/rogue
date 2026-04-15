#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
"""Pure-Python XVC wire-protocol client.

Implements the three XVC commands consumed by rogue.protocols.xilinx.Xvc
with byte-for-byte framing matching XvcConnection::run dispatch logic:

    getinfo:                           -> b"xvcServer_v1.0:<N>\\n"
    settck: + <u32 LE period>          -> <u32 LE effective period>
    shift:  + <u32 LE nbits> + tms + tdi -> tdo bytes, len == (nbits+7)//8

Stdlib-only (socket + struct + re). Deliberately has NO `import rogue` /
`import pyrogue` so the framing layer remains verifiable against a mock
server even when the C++ build is broken or absent.
"""
import re
import socket
import struct


_INFO_RE = re.compile(rb"^(xvcServer_v[0-9]+\.[0-9]+):([0-9]+)\n$")


class XvcClient:
    """Minimal synchronous XVC client.

    Context-manager-friendly:
        with XvcClient(host="127.0.0.1", port=p) as c:
            version, maxVec = c.getinfo()
            period          = c.settck(25)
            tdo             = c.shift(9, b"\\xAB\\x01", b"\\xCD\\x00")
    """

    def __init__(self, host="127.0.0.1", port=0, timeout=5.0):
        self._host    = host
        self._port    = int(port)
        self._timeout = float(timeout)
        self._sock    = None

    # -- lifecycle --------------------------------------------------------

    def connect(self):
        """Open TCP connection; idempotent."""
        if self._sock is not None:
            return
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.settimeout(self._timeout)
            s.connect((self._host, self._port))
            s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            self._sock = s
        except Exception:
            try:
                s.close()
            except OSError:
                pass
            raise

    def close(self):
        """Close socket; safe to call repeatedly."""
        s, self._sock = self._sock, None
        if s is not None:
            try:
                s.close()
            except OSError:
                pass

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False

    # -- low-level helpers ------------------------------------------------

    def _send_all(self, data):
        self._sock.sendall(bytes(data))

    def _recv_exact(self, n):
        """Receive exactly n bytes or raise RuntimeError on EOF."""
        buf = bytearray()
        while len(buf) < n:
            chunk = self._sock.recv(n - len(buf))
            if not chunk:
                raise RuntimeError(
                    "EOF before {} bytes (got {})".format(n, len(buf)))
            buf.extend(chunk)
        return bytes(buf)

    def _recv_line(self, limit=128):
        """Read up to and including newline, bounded at `limit` bytes."""
        buf = bytearray()
        while True:
            b = self._sock.recv(1)
            if not b:
                raise RuntimeError(
                    "EOF before newline (got {!r})".format(bytes(buf)))
            buf.extend(b)
            if b == b"\n":
                return bytes(buf)
            if len(buf) >= limit:
                raise ValueError(
                    "getinfo response exceeded {} bytes without newline".format(limit))

    # -- commands ---------------------------------------------------------

    def getinfo(self):
        """Send `getinfo:`; return (version_str, max_vec_len).

        Parses server reply `xvcServer_vX.Y:<N>\\n` exactly.  Raises
        ValueError on any deviation.
        """
        self._send_all(b"getinfo:")
        line = self._recv_line()
        m = _INFO_RE.match(line)
        if m is None:
            raise ValueError("Malformed getinfo response: {!r}".format(line))
        return m.group(1).decode("ascii"), int(m.group(2))

    def settck(self, period_ns):
        """Send `settck:<u32 LE>`; return effective period (int)."""
        frame = b"settck:" + struct.pack("<I", int(period_ns))
        if len(frame) != 11:
            raise ValueError("settck frame must be 11 bytes, got {}".format(len(frame)))
        self._send_all(frame)
        reply = self._recv_exact(4)
        return struct.unpack("<I", reply)[0]

    def shift(self, nbits, tms, tdi):
        """Send `shift:<u32 LE nbits> + tms + tdi`; return tdo bytes.

        `tms` and `tdi` must each be exactly ceil(nbits/8) bytes.  Returned
        TDO buffer is the same length.
        """
        nbits = int(nbits)
        if nbits <= 0:
            raise ValueError("nbits must be positive: {}".format(nbits))
        nbytes = (nbits + 7) // 8
        tms_b = bytes(tms)
        tdi_b = bytes(tdi)
        if len(tms_b) != nbytes:
            raise ValueError(
                "tms length {} != ceil(nbits/8)={}".format(len(tms_b), nbytes))
        if len(tdi_b) != nbytes:
            raise ValueError(
                "tdi length {} != ceil(nbits/8)={}".format(len(tdi_b), nbytes))
        header = b"shift:" + struct.pack("<I", nbits)
        if len(header) != 10:
            raise ValueError("shift header must be 10 bytes, got {}".format(len(header)))
        self._send_all(header + tms_b + tdi_b)
        return self._recv_exact(nbytes)
