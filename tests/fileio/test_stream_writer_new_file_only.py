#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
# Regression for slaclab/rogue#1328: StreamWriter is a write-once data logger.
# open() and the max-size rollover path must refuse to open a path that already
# exists instead of silently overwriting or appending to a previous session.

import pytest
import rogue
import rogue.interfaces.stream
import rogue.utilities.fileio

FrameSize = 100
# Non-raw record = 4 byte size + 4 byte header + payload
RecordSize = FrameSize + 8


class FrameSource(rogue.interfaces.stream.Master):
    def send(self, size):
        frame = self._reqFrame(size, True)
        frame.write(bytearray(range(size % 256)) * (size // 256 + 1), 0)
        self._sendFrame(frame)


class FrameSink(rogue.interfaces.stream.Slave):
    def __init__(self):
        super().__init__()
        self.payloads = []

    def _acceptFrame(self, frame):
        data = bytearray(frame.getPayload())
        frame.read(data, 0)
        self.payloads.append(bytes(data))


def read_frames(path):
    # Note: when opened on a ".1" file StreamReader follows ".2", ".3", ...
    reader = rogue.utilities.fileio.StreamReader()
    sink = FrameSink()
    reader >> sink
    reader.open(str(path))
    reader.closeWait()
    return sink.payloads


def write_frames(path, count, max_size=0):
    writer = rogue.utilities.fileio.StreamWriter()
    writer.setBufferSize(0)
    writer.setMaxSize(max_size)
    src = FrameSource()
    src >> writer.getChannel(0)
    writer.open(str(path))
    for _ in range(count):
        src.send(FrameSize)
    assert writer.getFrameCount() == count
    writer.close()
    return writer


def test_open_existing_file_raises_and_leaves_file_untouched(tmp_path):
    path = tmp_path / "data.dat"
    writer = write_frames(path, 5)

    original = path.read_bytes()
    assert len(original) == 5 * RecordSize

    with pytest.raises(rogue.GeneralError, match="already exists"):
        writer.open(str(path))

    assert writer.isOpen() is False
    assert path.read_bytes() == original

    frames = read_frames(path)
    assert len(frames) == 5
    assert all(len(frame) == FrameSize for frame in frames)

    # A fresh path still opens normally after the error.
    fresh = tmp_path / "fresh.dat"
    writer.open(str(fresh))
    assert writer.isOpen() is True
    writer.close()
    assert fresh.exists()


def test_open_existing_file_does_not_reset_counters(tmp_path):
    path = tmp_path / "data.dat"
    writer = write_frames(path, 3)
    assert writer.getFrameCount() == 3
    assert writer.getTotalSize() == 3 * RecordSize

    with pytest.raises(rogue.GeneralError):
        writer.open(str(path))

    assert writer.getFrameCount() == 3
    assert writer.getTotalSize() == 3 * RecordSize


def test_rollover_onto_existing_file_raises(tmp_path):
    base = tmp_path / "split.dat"
    # Two records fit in each file, the third write must roll over to .2
    max_size = 2 * RecordSize

    leftover = base.with_name(base.name + ".2")
    leftover.write_bytes(b"leftover from a previous session")
    original = leftover.read_bytes()

    writer = rogue.utilities.fileio.StreamWriter()
    writer.setBufferSize(0)
    writer.setMaxSize(max_size)
    src = FrameSource()
    src >> writer.getChannel(0)

    writer.open(str(base))
    src.send(FrameSize)
    src.send(FrameSize)
    assert writer.getFrameCount() == 2

    with pytest.raises(rogue.GeneralError, match="already exists"):
        src.send(FrameSize)

    # The writer is closed and the leftover file was not written into.
    assert writer.isOpen() is False
    assert leftover.read_bytes() == original
    assert base.with_name(base.name + ".1").stat().st_size == 2 * RecordSize
    assert not base.with_name(base.name + ".3").exists()
    writer.close()


def test_rollover_onto_fresh_files_still_works(tmp_path):
    base = tmp_path / "split.dat"
    write_frames(base, 5, max_size=2 * RecordSize)

    assert base.with_name(base.name + ".1").stat().st_size == 2 * RecordSize
    assert base.with_name(base.name + ".2").stat().st_size == 2 * RecordSize
    assert base.with_name(base.name + ".3").stat().st_size == 1 * RecordSize

    # The reader follows the split files, so all frames come back from ".1"
    frames = read_frames(base.with_name(base.name + ".1"))
    assert len(frames) == 5
    assert all(len(frame) == FrameSize for frame in frames)
