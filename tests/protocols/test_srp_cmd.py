#!/usr/bin/env python3
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

import struct

import rogue.interfaces.stream
import rogue.protocols.srp
import pytest


class FrameCapture(rogue.interfaces.stream.Slave):
    """Capture frames emitted by Cmd."""

    def __init__(self):
        super().__init__()
        self.frames = []

    def _acceptFrame(self, frame):
        self.frames.append(bytes(frame.getBa()))


def test_cmd_frame_is_16_bytes():
    cmd = rogue.protocols.srp.Cmd()
    capture = FrameCapture()
    cmd >> capture

    cmd.sendCmd(0x01, 0x00000000)
    assert len(capture.frames) == 1
    assert len(capture.frames[0]) == 16


def test_cmd_frame_structure():
    cmd = rogue.protocols.srp.Cmd()
    capture = FrameCapture()
    cmd >> capture

    cmd.sendCmd(0x42, 0xDEADBEEF)

    frame = capture.frames[0]
    w0, w1, w2, w3 = struct.unpack('<IIII', frame)

    assert w0 == 0xDEADBEEF  # context
    assert w1 == 0x42         # opCode
    assert w2 == 0            # reserved
    assert w3 == 0            # reserved


@pytest.mark.parametrize("opcode,context", [
    (0x00, 0x00000000),
    (0xFF, 0xFFFFFFFF),
    (0x01, 0x12345678),
    (0xAB, 0x00000001),
])
def test_cmd_various_opcodes(opcode, context):
    cmd = rogue.protocols.srp.Cmd()
    capture = FrameCapture()
    cmd >> capture

    cmd.sendCmd(opcode, context)

    frame = capture.frames[0]
    w0, w1, w2, w3 = struct.unpack('<IIII', frame)
    assert w0 == context
    assert w1 == opcode
    assert w2 == 0
    assert w3 == 0


def test_cmd_multiple_sends():
    cmd = rogue.protocols.srp.Cmd()
    capture = FrameCapture()
    cmd >> capture

    for i in range(5):
        cmd.sendCmd(i, i * 0x100)

    assert len(capture.frames) == 5
    for i, frame in enumerate(capture.frames):
        w0, w1, _, _ = struct.unpack('<IIII', frame)
        assert w0 == i * 0x100
        assert w1 == i


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
