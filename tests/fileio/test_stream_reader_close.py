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
import threading
import time

import rogue.interfaces.stream
import rogue.utilities.fileio

FRAME_COUNT = 4096
FRAME_SIZE = 1024
SLAVE_DELAY = 0.005
CLOSE_TIMEOUT = 5.0


class SlowSlave(rogue.interfaces.stream.Slave):
    def __init__(self):
        super().__init__()
        self.count = 0

    def _acceptFrame(self, frame):
        self.count += 1
        time.sleep(SLAVE_DELAY)


def test_stream_reader_close_while_active_returns(tmp_path, wait_until):
    # ~4 MB of records; at SLAVE_DELAY per frame the reader needs ~20 s to
    # reach EOF, so close() is guaranteed to land while it is still active.
    data_path = tmp_path / "records.dat"
    header = struct.pack("IHBB", FRAME_SIZE + 4, 0, 0, 0)
    data_path.write_bytes((header + bytes(FRAME_SIZE)) * FRAME_COUNT)

    reader = rogue.utilities.fileio.StreamReader()
    slave = SlowSlave()
    reader >> slave

    reader.open(str(data_path))
    assert wait_until(lambda: slave.count > 0, timeout=5.0)
    assert reader.isActive()

    # Run close() on a watchdog thread: before the fix it joined the read
    # thread while holding the mutex the read thread needs to exit.
    closer = threading.Thread(target=reader.close, daemon=True)
    closer.start()
    closer.join(CLOSE_TIMEOUT)

    assert not closer.is_alive(), "StreamReader.close() deadlocked against an active reader"
    assert not reader.isActive()
    assert not reader.isOpen()
    assert slave.count < FRAME_COUNT
