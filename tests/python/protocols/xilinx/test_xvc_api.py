#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
"""Python-side smoke for the Xvc API: preserved surface, getPort(), GIL release."""
import threading
import time

import rogue.protocols.xilinx as xvc_mod


def test_api_preserved():
    """Xvc(uint16), _start, _stop surface unchanged."""
    assert hasattr(xvc_mod, "Xvc"), "rogue.protocols.xilinx.Xvc missing"
    cls = xvc_mod.Xvc
    # Construction with single positional uint16 must work
    obj = cls(0)
    assert hasattr(obj, "_start"), "._start binding missing"
    assert hasattr(obj, "_stop"), "._stop binding missing"
    assert callable(obj._start)
    assert callable(obj._stop)


def test_get_port(xvc_server):
    """port-0 bind + getPort() returns kernel-assigned port."""
    assert hasattr(xvc_server, "getPort"), "Xvc.getPort() binding missing"
    port = xvc_server.getPort()
    assert isinstance(port, int)
    assert 0 < port < 65536, f"expected kernel port, got {port}"


def test_gil_release(xvc_server):
    """Python threads run freely while Xvc server thread is active."""
    results = []

    def sleeper():
        t0 = time.monotonic()
        time.sleep(0.05)
        results.append(time.monotonic() - t0)

    ths = [threading.Thread(target=sleeper) for _ in range(4)]
    for t in ths:
        t.start()
    for t in ths:
        t.join(timeout=1.0)
        assert not t.is_alive(), "Python thread starved — GIL held by C++?"
    assert len(results) == len(ths), f"Expected {len(ths)} sleep results, got {len(results)}: {results}"
    assert all(d < 0.5 for d in results), f"Suspicious sleep durations: {results}"
