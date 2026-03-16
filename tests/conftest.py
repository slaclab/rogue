import time

import pyrogue as pr
import pytest
import rogue.interfaces.memory


def wait_for(predicate, timeout=2.0, interval=0.01):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return predicate()


class MemoryRoot(pr.Root):
    def __init__(self, **kwargs):
        super().__init__(pollEn=False, **kwargs)
        # Use a local memory emulator so tests can exercise RemoteVariable paths
        # without needing external hardware or sockets.
        self._mem = rogue.interfaces.memory.Emulate(4, 0x4000)
        self.addInterface(self._mem)


@pytest.fixture
def wait_until():
    return wait_for


@pytest.fixture
def memory_root():
    root = MemoryRoot(name="root")
    with root:
        yield root
