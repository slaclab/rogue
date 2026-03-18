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
import logging

import pyrogue as pr
import pytest
import rogue
import rogue.interfaces.memory


def wait_for(predicate, timeout=2.0, interval=0.01):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return predicate()


class MemoryRoot(pr.Root):
    def __init__(self, *, mem_width=4, mem_size=0x4000, **kwargs):
        super().__init__(pollEn=False, **kwargs)
        # Use a local memory emulator so tests can exercise RemoteVariable paths
        # without needing external hardware or sockets.
        self._mem = rogue.interfaces.memory.Emulate(mem_width, mem_size)
        self.addInterface(self._mem)


@pytest.fixture(autouse=True)
def quiet_memory_emulate_logs():
    # The shared memory-emulator fixtures create a lot of low-value startup and
    # allocation chatter. Keep the default suite readable while still allowing
    # individual tests to raise this logger when they explicitly care.
    logger = logging.getLogger("pyrogue.memory.Emulate")
    old_level = logger.level
    logger.setLevel(logging.WARNING)
    try:
        yield
    finally:
        logger.setLevel(old_level)


@pytest.fixture(autouse=True)
def quiet_rogue_stdout_logs():
    # Native Rogue stdout logging is useful for manual debugging, but it
    # overwhelms normal test output once many memory-emulator fixtures run.
    old_stdout = rogue.Logging.emitStdout()
    rogue.Logging.setEmitStdout(False)
    try:
        yield
    finally:
        rogue.Logging.setEmitStdout(old_stdout)


@pytest.fixture
def wait_until():
    return wait_for


@pytest.fixture
def memory_root():
    root = MemoryRoot(name="root")
    with root:
        yield root
