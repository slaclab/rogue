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
DETECTED-IDs:
  - HW-CORE-018

Stress the StreamReader fd_ race: StreamReader.cpp line 180 reads fd_
without mtx_ while StreamReader::intClose at line 144 writes it under the
same mutex only on the close path. Concurrent read + close from different
threads exposes the unsynchronized fd_ access.
"""
import os
import threading

import pytest
import rogue

pytestmark = pytest.mark.repro


@pytest.mark.repro
def test_stress_streamreader_fd_race(stress_iters, tmp_path):
    """StreamReader runThread fd_ read vs close() write (HW-CORE-018)."""
    errors = []

    # Create a moderately-sized input file; larger than one frame so
    # runThread issues multiple reads during the stress window.
    target = tmp_path / "stress_fd.dat"
    data = os.urandom(1 << 16)  # 64 KiB
    target.write_bytes(data)

    def cycle():
        for _ in range(stress_iters // 10):
            try:
                reader = rogue.utilities.fileio.StreamReader()
                reader.open(str(target))
                # Immediately close from the same thread; the reader's
                # runThread is racing its own intClose() on fd_.
                reader.close()
            except Exception as e:
                errors.append(e)

    def closer_from_other_thread():
        for _ in range(stress_iters // 10):
            try:
                reader = rogue.utilities.fileio.StreamReader()
                reader.open(str(target))
                # Spawn a close-from-other-thread to race runThread's fd_ read.
                t = threading.Thread(target=reader.close)
                t.start()
                t.join()
            except Exception as e:
                errors.append(e)

    threads = [threading.Thread(target=cycle) for _ in range(5)]
    threads += [threading.Thread(target=closer_from_other_thread) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors, f"StreamReader fd race stress errors: {errors}"
