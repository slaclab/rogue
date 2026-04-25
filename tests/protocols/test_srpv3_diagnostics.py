#!/usr/bin/env python3
#-----------------------------------------------------------------------------
# Title      : SrpV3 error-message diagnostic regression tests
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
# Pins the post-PR diagnostic strings for the SrpV3::acceptFrame() error
# branches that propagate to user code via ``tran->error(...)``. The PR
# replaced terse generic strings with field-anchored diagnostics so a
# field engineer can identify the offending transaction from a single log
# line. Reverting the changes in src/rogue/protocols/srp/SrpV3.cpp drops
# the field anchors and trips the assertions below.
#
# The bad-header path (id=, addr=) is already pinned by
# tests/protocols/test_srpv3_concurrent.py::
#   test_srpv3_header_mismatch_error_includes_diagnostics.
#
# This file covers the size-mismatch path (id=, frameSize=, expectedSize=,
# tranSize=, headerSize=) which the existing diagnostic test does not
# exercise — it requires a frame whose header[0..4] still match the
# expected pattern but whose payload length is wrong, so the protocol-
# header compare passes and execution reaches the size-mismatch branch.

import pyrogue as pr
import pytest
import rogue
import rogue.interfaces.stream
import rogue.protocols.srp

pytestmark = pytest.mark.integration


class FrameLengthCorruptor(rogue.interfaces.stream.Slave,
                           rogue.interfaces.stream.Master):
    """Intercept SrpV3 server response frames and append junk bytes.

    The header bytes are left untouched so the protocol-header compare
    in SrpV3::acceptFrame still passes; only ``frame->getPayload()`` is
    larger than the value the SrpV3 master computed in setupHeader(),
    which is exactly what trips the size-mismatch branch (``fSize !=
    expFrameLen``).
    """

    def __init__(self) -> None:
        rogue.interfaces.stream.Slave.__init__(self)
        rogue.interfaces.stream.Master.__init__(self)
        self.corrupt_next = False

    def _acceptFrame(self, frame):
        ba = bytearray(frame.getBa())
        if self.corrupt_next:
            # Append 8 bytes of junk past the legitimate tail. The real
            # response data and header[0..4] are preserved.
            ba.extend(b"\x00" * 8)
            self.corrupt_next = False
        new_frame = self._reqFrame(len(ba), True)
        new_frame.write(ba)
        self._sendFrame(new_frame)


def test_srpv3_size_mismatch_error_includes_diagnostics():
    """The size-mismatch error must include id/frameSize/expectedSize/etc.

    On unpatched code the message is the terse:
      "Received SRPV3 message had a header size mismatch"
    After the PR's diagnostic enrichment it includes id=, frameSize=,
    expectedSize=, tranSize=, headerSize= so the offending transaction
    can be reconstructed from a single log line.
    """
    srp_client = rogue.protocols.srp.SrpV3()
    srp_server = rogue.protocols.srp.SrpV3Emulation()
    corruptor = FrameLengthCorruptor()

    # Wire: client -> server -> corruptor -> client
    srp_client >> srp_server
    srp_server >> corruptor
    corruptor >> srp_client

    dev = pr.Device(name="Dev", offset=0x0, memBase=srp_client)
    dev.add(pr.RemoteVariable(
        name="Reg0", offset=0x0, bitSize=32, mode="RW", base=pr.UInt,
    ))

    root = pr.Root(name="SrpV3SizeMismatchRoot", timeout=1.0, pollEn=False)
    root.add(dev)
    root.start()
    try:
        # Prime the emulator with known data.
        root.Dev.Reg0.set(0xCAFE)

        # Corrupt the next response frame's length only.
        corruptor.corrupt_next = True

        with pytest.raises(rogue.GeneralError) as exc_info:
            root.Dev.Reg0.get()

        err_msg = str(exc_info.value)

        # Each anchor must be present individually so a partial revert
        # of the diagnostic enrichment still trips a clear assertion.
        for anchor in ("id=", "frameSize=", "expectedSize=",
                       "tranSize=", "headerSize="):
            assert anchor in err_msg, (
                f"Size-mismatch error lacks {anchor!r} diagnostic anchor. "
                f"Got: {err_msg!r}"
            )
    finally:
        root.stop()


def test_srpv3_size_mismatch_diagnostics_carry_actual_values():
    """The diagnostic anchors must surface real numbers, not ``%PRIu32``.

    A regression where the format-string substitution silently fails
    (e.g. wrong PRIu macro for a renamed type) would still satisfy the
    substring checks above; this test asserts that at least one anchor
    carries a numeric tail that round-trips through int() so the
    formatting machinery is exercised end-to-end.
    """
    srp_client = rogue.protocols.srp.SrpV3()
    srp_server = rogue.protocols.srp.SrpV3Emulation()
    corruptor = FrameLengthCorruptor()

    srp_client >> srp_server
    srp_server >> corruptor
    corruptor >> srp_client

    dev = pr.Device(name="Dev", offset=0x0, memBase=srp_client)
    dev.add(pr.RemoteVariable(
        name="Reg0", offset=0x0, bitSize=32, mode="RW", base=pr.UInt,
    ))

    root = pr.Root(name="SrpV3SizeMismatchValuesRoot", timeout=1.0, pollEn=False)
    root.add(dev)
    root.start()
    try:
        root.Dev.Reg0.set(0xCAFE)
        corruptor.corrupt_next = True

        with pytest.raises(rogue.GeneralError) as exc_info:
            root.Dev.Reg0.get()

        err_msg = str(exc_info.value)

        # ``frameSize=`` is the simplest one to parse out: the corruptor
        # appended 8 bytes, so the real frame size is the canonical one
        # plus 8. Just assert the substring is followed by a base-10 int
        # — the exact value depends on internal SrpV3 framing constants
        # we don't want to hard-code here.
        idx = err_msg.find("frameSize=")
        assert idx >= 0, f"frameSize anchor missing: {err_msg!r}"
        tail = err_msg[idx + len("frameSize="):]
        digits = ""
        for ch in tail:
            if ch.isdigit():
                digits += ch
            else:
                break
        assert digits, (
            f"frameSize= is not followed by a decimal value. Tail: {tail!r}"
        )
        # Just confirm it's parseable as a positive integer.
        assert int(digits) > 0
    finally:
        root.stop()
