#!/usr/bin/env python3
#-----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
#-----------------------------------------------------------------------------
#  Description:
#       File capture tutorial: write a stream to disk, read it back, and
#       compare an uncompressed capture against a compressed one.
#
#       Runs with no hardware. This file is included into
#       docs/src/tutorials/file_capture.rst and is exercised by
#       tests/docs/test_docs_tutorial_examples.py.
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

import os
import tempfile
import time

import pyrogue as pr
import pyrogue.utilities.fileio
import pyrogue.utilities.prbs
import rogue.interfaces.stream
import rogue.utilities


class CaptureRoot(pr.Root):
    """PRBS generator -> rate limiter -> file writer.

    The ``RateDrop`` stage matters. An unthrottled ``PrbsTx`` saturates the
    CPU and writes hundreds of megabytes per second, which is useful for
    benchmarking and hostile to a tutorial. ``RateDrop(True, period)`` forwards
    at most one frame per ``period`` seconds.
    """

    def __init__(self, period=0.01, **kwargs):
        super().__init__(description='Throttled capture to disk', **kwargs)

        self._prbs = pr.utilities.prbs.PrbsTx(name='PrbsTx')
        self.add(self._prbs)

        # True selects time-based dropping; period is in seconds.
        self._rate = rogue.interfaces.stream.RateDrop(True, period)

        self._writer = pr.utilities.fileio.StreamWriter(name='Writer')
        self.add(self._writer)

        self._prbs >> self._rate >> self._writer.getChannel(0)

    def captureTo(self, path, seconds=1.0):
        """Record for a fixed wall-clock duration, then close the file.

        The file must be closed before it is read: the writer buffers, so a
        reader opening it early sees a truncated final record.
        """
        self.Writer.DataFile.set(path)
        self.Writer.Open()

        self.PrbsTx.txEnable.set(True)
        time.sleep(seconds)
        self.PrbsTx.txEnable.set(False)

        self.Writer.Close()
        return os.path.getsize(path)


class CompressedCaptureRoot(pr.Root):
    """The same capture path with compression inserted before the writer.

    ``StreamZip`` compresses each frame as it passes. PRBS data is
    pseudo-random and therefore close to incompressible, so expect little or
    no saving here -- real detector payloads with headers, padding, or idle
    regions compress far better.
    """

    def __init__(self, period=0.01, **kwargs):
        super().__init__(description='Compressed capture to disk', **kwargs)

        self._prbs = pr.utilities.prbs.PrbsTx(name='PrbsTx')
        self.add(self._prbs)

        self._rate = rogue.interfaces.stream.RateDrop(True, period)
        self._zip = rogue.utilities.StreamZip()

        self._writer = pr.utilities.fileio.StreamWriter(name='Writer')
        self.add(self._writer)

        self._prbs >> self._rate >> self._zip >> self._writer.getChannel(0)

    def captureTo(self, path, seconds=1.0):
        self.Writer.DataFile.set(path)
        self.Writer.Open()
        self.PrbsTx.txEnable.set(True)
        time.sleep(seconds)
        self.PrbsTx.txEnable.set(False)
        self.Writer.Close()
        return os.path.getsize(path)


def countRecords(path, limit=None):
    """Replay a capture file and count the records inside it.

    ``FileReader`` iterates records rather than raw bytes, so each iteration
    hands back one frame's worth of payload with its channel intact.
    """
    reader = pr.utilities.fileio.FileReader(path)
    count = 0
    for _ in reader.records():
        count += 1
        if limit is not None and count >= limit:
            break
    return count


def roundTripCheck(payload=b'ABCD' * 256):
    """Prove StreamZip/StreamUnZip is lossless, without involving a file."""

    class Source(rogue.interfaces.stream.Master):
        def sendBytes(self, data):
            frame = self._reqFrame(len(data), True)
            with frame.lock():
                frame.write(data)
            self._sendFrame(frame)

    class Capture(rogue.interfaces.stream.Slave):
        def __init__(self):
            super().__init__()
            self.data = None

        def _acceptFrame(self, frame):
            with frame.lock():
                buffer = bytearray(frame.getPayload())
                frame.read(buffer, 0)
                self.data = bytes(buffer)

    source = Source()
    capture = Capture()
    source >> rogue.utilities.StreamZip() >> rogue.utilities.StreamUnZip() >> capture

    source.sendBytes(payload)
    time.sleep(0.5)
    return capture.data == payload


if __name__ == '__main__':
    with tempfile.TemporaryDirectory() as workdir:
        plain = os.path.join(workdir, 'capture.dat')
        packed = os.path.join(workdir, 'capture_zip.dat')

        with CaptureRoot() as root:
            plainSize = root.captureTo(plain, seconds=1.0)
        print('plain capture bytes      :', plainSize)
        print('records read back        :', countRecords(plain))

        with CompressedCaptureRoot() as root:
            packedSize = root.captureTo(packed, seconds=1.0)
        print('compressed capture bytes :', packedSize)

        print('zip -> unzip is lossless :', roundTripCheck())
