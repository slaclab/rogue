#!/usr/bin/env python3
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
"""Regression: memory transactions re-entered from Python must be released with the GIL.

A Python memory Slave or Hub subclass that forwards the transaction it received
back into C++ (``super()._doTransaction(transaction)``, the documented pattern)
re-enters through Boost.Python's from-python shared_ptr converter. That converter
attaches a ``shared_ptr_deleter`` owning the PyObject, whose ``Py_DECREF`` does
not acquire the GIL itself. Releasing the last such reference from a C++ worker
thread, which has no PyThreadState, aborted the interpreter with
"PyThreadState_Get: the function must be called with the GIL held".

``bp::no_init`` on Transaction does not prevent this: it only suppresses
``__init__``, while ``class_::initialize()`` still registers the converter.

Two drop sites had to be fixed for this to pass: the expired-entry erase in
``Slave::getTransaction`` and the per-iteration release in
``memory::TcpClient::runThread``.

Runs in a subprocess because the unpatched failure is a fatal interpreter abort,
which would take down the xdist worker rather than failing this test.
"""

import subprocess
import sys
import textwrap

import pytest

pytestmark = pytest.mark.integration

CHILD = textwrap.dedent(
    """
    import time

    import rogue.interfaces.memory as rim

    emu = rim.Emulate(4, 0x1000)
    srv = rim.TcpServer("127.0.0.1", {port})
    emu << srv
    cli = rim.TcpClient("127.0.0.1", {port}, True)


    class ForwardingSlave(rim.Slave):
        \"\"\"Forwards each transaction back into C++, attaching a Python deleter.\"\"\"

        def __init__(self, dest):
            rim.Slave.__init__(self, 4, 0xFFFF)
            self._dest = dest

        def _doTransaction(self, transaction):
            self._dest._doTransaction(transaction)


    fwd = ForwardingSlave(cli)
    mst = rim.Master()
    mst >> fwd

    for _ in range(30):
        mst._reqTransaction(0, bytearray(4), 0, 0, rim.Write)
        mst._waitTransaction(0)
        time.sleep(0.01)

    print("OK")
    """
)


def test_memory_releases_python_owned_transactions(free_tcp_port):
    result = subprocess.run(
        [sys.executable, "-c", CHILD.format(port=free_tcp_port)],
        capture_output=True,
        text=True,
        timeout=120,
    )

    # An unpatched build dies on SIGABRT from the fatal Python error, so a clean
    # exit is the assertion. Surface the child's diagnostics on failure.
    assert result.returncode == 0, (
        f"child exited {result.returncode}\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    assert "OK" in result.stdout
