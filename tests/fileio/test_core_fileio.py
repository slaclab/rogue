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

import pyrogue as pr
import pyrogue.utilities.fileio
import pytest
import yaml


class FakeChannel:
    def __init__(self):
        self.wait_requests = []

    def waitFrameCount(self, count, timeout):
        self.wait_requests.append((count, timeout))
        return True


class FakeWriter:
    def __init__(self):
        self.raw = False
        self.opened = None
        self.closed = False
        self.buffer_size = None
        self.max_size = None
        self.channel = FakeChannel()
        self.frame_count = 11

    def setRaw(self, value):
        self.raw = value

    def open(self, path):
        self.opened = path

    def close(self):
        self.closed = True

    def isOpen(self):
        return self.opened is not None and not self.closed

    def setBufferSize(self, value):
        self.buffer_size = value

    def setMaxSize(self, value):
        self.max_size = value

    def getCurrentSize(self):
        return 123

    def getTotalSize(self):
        return 456

    def getBandwidth(self):
        return 78.5

    def getFrameCount(self):
        return self.frame_count

    def waitFrameCount(self, count, timeout):
        self.wait_request = (count, timeout)
        return True

    def getChannel(self, chan):
        assert chan == 2
        return self.channel

    def setDropErrors(self, drop):
        self.drop_errors = drop


def _write_record(path, channel, payload, flags=0, error=0):
    # Match the canonical Rogue on-disk record header layout.
    header = struct.pack("IHBB", len(payload) + 4, flags, error, channel)
    path.write_bytes(header + payload)


def test_file_reader_reads_records_and_config(tmp_path):
    data_path = tmp_path / "records.dat"
    config_payload = yaml.dump({"root.Child.Value": 9}).encode("utf-8")
    data_payload = bytes([1, 2, 3, 4])

    data_path.write_bytes(
        # Prepend a config-channel record so FileReader has to merge YAML before
        # yielding the first data frame.
        struct.pack("IHBB", len(config_payload) + 4, 0, 0, 7) + config_payload +
        struct.pack("IHBB", len(data_payload) + 4, 1, 0, 1) + data_payload
    )

    reader = pyrogue.utilities.fileio.FileReader(files=str(data_path), configChan=7)
    records = list(reader.records())

    assert len(records) == 1
    header, data = records[0]
    assert header.channel == 1
    assert header.flags == 1
    assert header.size == 4
    assert data.tolist() == [1, 2, 3, 4]
    assert reader.currCount == 1
    assert reader.totCount == 1
    assert reader.configDict == {"root": {"Child": {"Value": 9}}}
    assert reader.configValue("root.Child.Value") == 9


def test_file_reader_missing_path_raises(tmp_path):
    data_path = tmp_path / "empty.dat"
    _write_record(data_path, 1, bytes([9, 8]))

    reader = pyrogue.utilities.fileio.FileReader(files=str(data_path))
    list(reader.records())

    with pytest.raises(pyrogue.utilities.fileio.FileReaderException, match="Failed to find path"):
        reader.configValue("missing.path")


def test_stream_writer_wrapper_delegates_to_underlying_writer(tmp_path):
    fake = FakeWriter()
    writer = pyrogue.utilities.fileio.StreamWriter(
        name="Writer",
        writer=fake,
        rawMode=True,
    )

    root = pr.Root(name="root", pollEn=False)
    # Attach the wrapper to a real Root so LocalVariable/LocalCommand plumbing
    # behaves the same way it does in normal runtime use.
    root.add(writer)
    with root:
        output = tmp_path / "stream.dat"
        writer.DataFile.set(str(output))

        writer.Open()
        assert fake.raw is True
        assert fake.opened == str(output)
        assert writer.IsOpen.get() is True

        writer.BufferSize.set(512)
        writer.MaxFileSize.set(1024)
        assert fake.buffer_size == 512
        assert fake.max_size == 1024
        assert writer.CurrentSize.get() == 123
        assert writer.TotalSize.get() == 456
        assert writer.Bandwidth.get() == 78.5
        assert writer.FrameCount.get() == 11
        assert writer._waitFrameCount(4, timeout=0.25) is True
        assert fake.wait_request == (4, 250000.0)
        assert writer._waitFrameChannelCount(2, 5, timeout=0.5) is True
        assert fake.channel.wait_requests == [(5, 500000.0)]

        writer.setDropErrors(True)
        assert fake.drop_errors is True

        writer.Close()
        assert fake.closed is True
