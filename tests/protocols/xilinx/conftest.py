#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
"""Pytest fixtures for XVC end-to-end tests.

Provides `xvc_session` -- a composed fixture that wires the real C++ Xvc
server to a Python `FakeJtag` emulator BEFORE `_start()` so the very first
`Xvc::xfer()` call has a responder waiting.  Uses port 0 + getPort() for
dynamic port discovery, so multiple concurrent sessions never collide
(pytest-xdist friendly).
"""
import os
import sys
import time

_here = os.path.dirname(os.path.abspath(__file__))
if _here not in sys.path:
    sys.path.insert(0, _here)

import pytest  # noqa: E402
import pyrogue as pr  # noqa: E402
import rogue.protocols.xilinx as xvc_mod  # noqa: E402

from fake_jtag import FakeJtag  # noqa: E402


@pytest.fixture
def xvc_session():
    """Composed Xvc + FakeJtag fixture for E2E tests.

    Yields (xvc, fake, port).  Port-0 bind + getPort() discovery: multiple
    workers cannot collide.  Function-scoped so every test gets a clean
    server lifecycle; teardown asserts `_stop()` returns in < 500ms
    (event-driven shutdown guarantee).

    Wiring order matters: FakeJtag MUST be stream-connected in BOTH
    directions BEFORE `xvc._start()`, otherwise the first `drv_->query()`
    call inside the XVC run loop blocks forever on `queue_.pop()` because
    no upstream Master has pushed a reply frame.
    """
    xvc  = xvc_mod.Xvc(0)
    fake = FakeJtag()

    # Wire driver BEFORE _start() so the very first query() has a responder.
    # Request path  : Xvc (Master) --> FakeJtag (Slave)
    # Reply path    : FakeJtag (Master) --> Xvc (Slave)
    pr.streamConnect(xvc, fake)
    pr.streamConnect(fake, xvc)

    xvc._start()
    try:
        port = xvc.getPort()
        assert 0 < port < 65536, f"xvc.getPort() returned implausible port {port}"
        yield xvc, fake, port
    finally:
        t0 = time.monotonic()
        xvc._stop()
        elapsed = time.monotonic() - t0
        assert elapsed < 0.5, f"xvc._stop() took {elapsed:.3f}s (>0.5s budget)"
