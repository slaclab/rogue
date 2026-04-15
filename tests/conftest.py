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
import socket

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


def _find_free_port_block(host="127.0.0.1", count=3, start=20000, stop=60000):
    for base in range(start, stop - count):
        sockets = []
        try:
            for port in range(base, base + count):
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.bind((host, port))
                sockets.append(sock)
            return base
        except OSError:
            pass
        finally:
            for sock in sockets:
                sock.close()

    raise RuntimeError(f"Unable to find {count} consecutive free ports on {host}")


def _worker_port_search_range(worker_id, *, start=20000, stop=60000, span=256):
    # xdist workers probe ports in parallel. Give each worker a disjoint slice
    # so they do not race on the same consecutive port block.
    if not worker_id or worker_id == "master":
        return start, stop

    if worker_id.startswith("gw") and worker_id[2:].isdigit():
        worker_index = int(worker_id[2:])
        worker_start = start + (worker_index * span)
        worker_stop = min(worker_start + span, stop)
        if worker_start < worker_stop:
            return worker_start, worker_stop

    return start, stop


@pytest.fixture
def free_zmq_port(worker_id):
    # Rogue's ZMQ server uses a base port plus adjacent ports, so integration
    # tests need a free consecutive block rather than a single ephemeral port.
    #
    # When pytest-xdist is active, multiple workers may probe ports at the same
    # time. Searching within worker-specific slices avoids collisions between
    # concurrent integration tests on the same host.
    start, stop = _worker_port_search_range(worker_id)
    return _find_free_port_block(start=start, stop=stop)


@pytest.fixture
def free_tcp_port():
    # Most TCP-backed integration tests only need one caller-selected port.
    return _find_free_port_block(count=1)


@pytest.fixture
def memory_root():
    root = MemoryRoot(name="root")
    with root:
        yield root


# ---- XVC fixtures ----
@pytest.fixture
def xvc_server():
    """Construct an Xvc server on kernel-assigned port (0) + start/stop.

    Wires a FakeJtag responder so ``init()`` (which calls ``query()`` →
    ``xfer()`` → ``queue_.pop()``) completes and the server thread reaches
    ``XvcServer::run()`` / ``select()``.  Without this, the thread blocks
    forever in ``queue_.pop()`` and never exercises the event-driven path.

    Yields the started Xvc instance; test code uses ``xvc_server.getPort()``.
    Teardown asserts ``_stop()`` returns quickly (event-driven shutdown);
    the harder timing check lives in the gtest suite.
    """
    import os
    import sys
    xilinx_path = os.path.join(os.path.dirname(__file__),
                               "protocols", "xilinx")
    if xilinx_path not in sys.path:
        sys.path.insert(0, xilinx_path)
    from fake_jtag import FakeJtag

    import rogue.protocols.xilinx as _xvc_mod
    xvc = _xvc_mod.Xvc(0)
    fake = FakeJtag()

    pr.streamConnect(xvc, fake)
    pr.streamConnect(fake, xvc)

    xvc._start()
    try:
        yield xvc
    finally:
        t0 = time.monotonic()
        xvc._stop()
        elapsed = time.monotonic() - t0
        assert elapsed < 0.5, f"xvc._stop() took {elapsed:.3f}s (>0.5s budget)"
