#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
"""
Drives the downstream BitInverter boost.python module built via
find_package(Rogue) and asserts that it inverts every payload byte.

The module directory (the cmake build dir holding BitInverter.so) must be on
PYTHONPATH. Run standalone (``python verify_bit_inversion.py``) or under pytest.
"""

import sys

import rogue.interfaces.stream

import BitInverter


class FrameSource(rogue.interfaces.stream.Master):
    """Sends a single frame carrying the supplied bytes."""

    def sendData(self, data):
        frame = self._reqFrame(len(data), True)
        frame.write(bytearray(data))
        self._sendFrame(frame)


class CaptureSink(rogue.interfaces.stream.Slave):
    """Collects raw bytes of every frame it receives."""

    def __init__(self):
        super().__init__()
        self.frames = []

    def _acceptFrame(self, frame):
        with frame.lock():
            self.frames.append(bytes(frame.getBa()))


def run():
    payload  = [0x00, 0xFF, 0xAA, 0x55, 0x0F, 0xF0]
    expected = bytes(b ^ 0xFF for b in payload)

    source   = FrameSource()
    inverter = BitInverter.BitInverter()
    sink     = CaptureSink()

    # source -> inverter -> sink
    source >> inverter >> sink

    source.sendData(payload)

    assert len(sink.frames) == 1, \
        f"expected 1 forwarded frame, got {len(sink.frames)}"
    assert sink.frames[0] == expected, \
        f"bit inversion mismatch: got {sink.frames[0].hex()}, expected {expected.hex()}"

    print(f"PASS: {len(payload)} bytes inverted correctly via find_package(Rogue)")


def test_bit_inversion():
    run()


if __name__ == "__main__":
    try:
        run()
    except AssertionError as exc:
        print(f"FAIL: {exc}")
        sys.exit(1)
    sys.exit(0)
