#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

import datetime

import pyrogue as pr
import pyrogue.utilities.fileio


class FakeChannel:
    def __init__(self):
        self.wait_calls = []

    def waitFrameCount(self, count, timeout):
        self.wait_calls.append((count, timeout))
        return True


class FakeConfigStream:
    def __init__(self):
        self.yaml_calls = 0

    def streamYaml(self):
        self.yaml_calls += 1


class FakeWriter:
    def __init__(self):
        self.raw = False
        self.opened = None
        self.closed = False
        self.buffer_size = None
        self.max_size = None
        self.drop_errors = None
        self.current_size = 17
        self.total_size = 33
        self.bandwidth = 4.5
        self.frame_count = 6
        self.channels = {}

    def setRaw(self, value):
        self.raw = value

    def getChannel(self, chan):
        if chan not in self.channels:
            self.channels[chan] = FakeChannel()
        return self.channels[chan]

    def open(self, path):
        self.opened = path
        self.closed = False

    def close(self):
        self.closed = True

    def isOpen(self):
        return self.opened is not None and not self.closed

    def setBufferSize(self, value):
        self.buffer_size = value

    def setMaxSize(self, value):
        self.max_size = value

    def getCurrentSize(self):
        return self.current_size

    def getTotalSize(self):
        return self.total_size

    def getBandwidth(self):
        return self.bandwidth

    def getFrameCount(self):
        return self.frame_count

    def waitFrameCount(self, count, timeout):
        self.last_wait = (count, timeout)
        return True

    def setDropErrors(self, drop):
        self.drop_errors = drop


class FixedDatetime(datetime.datetime):
    @classmethod
    def now(cls):
        return cls(2024, 1, 2, 3, 4, 5)


def test_data_writer_auto_name_and_default_metrics(monkeypatch):
    class BasicWriter(pr.DataWriter):
        pass

    monkeypatch.setattr(pr._DataWriter.datetime, "datetime", FixedDatetime)

    root = pr.Root(name="root", pollEn=False)
    writer = BasicWriter(name="Writer")
    root.add(writer)

    with root:
        writer.DataFile.set("/tmp/output/current.dat")
        writer.AutoName()

        # AutoName should preserve the parent directory while replacing the basename.
        assert writer.DataFile.get() == "/tmp/output/data_20240102_030405.dat"
        assert writer.IsOpen.get() is False
        assert writer.CurrentSize.get() == 0
        assert writer.TotalSize.get() == 0
        assert writer.Bandwidth.get() == 0.0
        assert writer.FrameCount.get() == 0


def test_stream_writer_wrapper_open_close_and_status(monkeypatch, tmp_path):
    fake_writer = FakeWriter()
    cfg0 = FakeConfigStream()
    cfg1 = FakeConfigStream()
    connections = []

    # Patch the backend factory so the wrapper can be exercised without a real
    # Rogue file writer or live stream endpoints.
    monkeypatch.setattr(pr.utilities.fileio.rogue.utilities.fileio, "StreamWriter", lambda: fake_writer)
    monkeypatch.setattr(pr, "streamConnect", lambda source, dest: connections.append((source, dest)))

    root = pr.Root(name="root", pollEn=False)
    writer = pr.utilities.fileio.StreamWriter(
        name="Writer",
        configStream={0: cfg0, 3: cfg1},
        rawMode=True,
    )
    root.add(writer)

    with root:
        assert fake_writer.raw is True
        assert connections == [
            (cfg0, fake_writer.getChannel(0)),
            (cfg1, fake_writer.getChannel(3)),
        ]

        out_file = tmp_path / "output.dat"
        writer.DataFile.set(str(out_file))
        writer.Open()

        assert fake_writer.opened == str(out_file)
        assert cfg0.yaml_calls == 1
        assert cfg1.yaml_calls == 1
        assert writer.IsOpen.get() is True

        writer.BufferSize.set(1024)
        writer.MaxFileSize.set(4096)
        writer.setDropErrors(True)

        assert fake_writer.buffer_size == 1024
        assert fake_writer.max_size == 4096
        assert fake_writer.drop_errors is True
        assert writer.CurrentSize.get() == 17
        assert writer.TotalSize.get() == 33
        assert writer.Bandwidth.get() == 4.5
        assert writer.FrameCount.get() == 6

        assert writer._waitFrameCount(8, timeout=0.25) is True
        assert fake_writer.last_wait == (8, 250000.0)
        assert writer._waitFrameChannelCount(3, 2, timeout=0.5) is True
        assert fake_writer.getChannel(3).wait_calls == [(2, 500000.0)]

        assert writer.getChannel(0) is fake_writer.getChannel(0)

        writer.Close()
        assert cfg0.yaml_calls == 2
        assert cfg1.yaml_calls == 2
        assert fake_writer.closed is True
        assert writer.IsOpen.get() is False
