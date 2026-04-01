#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

import pyrogue as pr
import pyrogue.utilities.fileio


class FakeReader:
    def __init__(self):
        self.opened = None
        self.closed = False

    def open(self, path):
        self.opened = path

    def close(self):
        self.closed = True

    def isOpen(self):
        return self.opened is not None and not self.closed


def test_stream_reader_wrapper_open_close_and_connect(monkeypatch, tmp_path):
    fake = FakeReader()
    # Swap in a deterministic backend so the wrapper can be tested without
    # opening a real Rogue file stream.
    monkeypatch.setattr(pr.utilities.fileio.rogue.utilities.fileio, "StreamReader", lambda: fake)

    reader = pr.utilities.fileio.StreamReader(name="Reader")
    root = pr.Root(name="root", pollEn=False)
    root.add(reader)

    connections = []
    monkeypatch.setattr(pr, "streamConnect", lambda source, dest: connections.append((source, dest)))

    with root:
        data_file = tmp_path / "input.dat"
        reader.DataFile.set(str(data_file))

        reader.Open()
        assert fake.opened == str(data_file)
        assert reader.isOpen.get() is True
        assert reader._getStreamMaster() is fake

        marker = object()
        assert (reader >> marker) is marker
        assert connections == [(reader, marker)]

        reader.Close()
        assert fake.closed is True
        assert reader.isOpen.get() is False
