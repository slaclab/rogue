#!/usr/bin/env python3
#-----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
#-----------------------------------------------------------------------------
#  Description:
#       Custom C++ module tutorial: drive the compiled BitInverter module from
#       Python and wrap it in a PyRogue Device.
#
#       Requires the module built per docs/src/tutorials/custom_cpp_module.rst.
#       Runs with no hardware. Included into that page and exercised by
#       tests/docs/test_docs_tutorial_examples.py, which skips when the
#       compiled module is not on PYTHONPATH.
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

import time

import pyrogue as pr
import rogue.interfaces.stream


class ByteSource(rogue.interfaces.stream.Master):
    """Sends one frame carrying the supplied bytes."""

    def sendBytes(self, data):
        frame = self._reqFrame(len(data), True)
        with frame.lock():
            frame.write(bytes(data))
        self._sendFrame(frame)


class ByteCapture(rogue.interfaces.stream.Slave):
    """Keeps the payload of every frame it receives."""

    def __init__(self):
        super().__init__()
        self.frames = []

    def _acceptFrame(self, frame):
        with frame.lock():
            buffer = bytearray(frame.getPayload())
            frame.read(buffer, 0)
            self.frames.append(bytes(buffer))


class BitInverterDevice(pr.Device):
    """Wraps the C++ module so it belongs to a tree.

    The C++ object is a stream endpoint, not a Device, so it has no place in a
    tree by itself. A thin Device wrapper gives it a name, a description, and
    somewhere to hang status Variables -- and exposes the raw object so stream
    connections can still be made.
    """

    def __init__(self, inverter, **kwargs):
        super().__init__(description='C++ bit-inverting stream module', **kwargs)
        self._inverter = inverter

        self.add(pr.LocalVariable(
            name        = 'Description',
            description = 'What the underlying C++ module does',
            mode        = 'RO',
            value       = 'Inverts every payload byte (b ^ 0xFF)'))

    def __rshift__(self, other):
        """Let the wrapper sit in a ``a >> wrapper >> b`` chain."""
        self._inverter >> other
        return other

    def __lshift__(self, other):
        self._inverter << other
        return other


def invertThroughModule(payload):
    """Push bytes through the compiled module and return what comes out."""
    import BitInverter

    source = ByteSource()
    capture = ByteCapture()

    source >> BitInverter.BitInverter() >> capture
    source.sendBytes(payload)
    time.sleep(0.5)

    return capture.frames[0] if capture.frames else None


if __name__ == '__main__':
    sample = bytes([0x00, 0x0F, 0xFF])
    result = invertThroughModule(sample)

    print('input  :', sample.hex())
    print('output :', result.hex())
    print('correct:', result == bytes(byte ^ 0xFF for byte in sample))
