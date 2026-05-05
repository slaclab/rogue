#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
"""Regression tests for the Logging subsystem.

Covers intLog behavior: exceptions raised in Python log handlers must be
surfaced via PyErr_Print (stderr) rather than silently discarded.
"""

import logging

import rogue
import rogue.interfaces.memory as rim


def test_intlog_surfaces_python_handler_exception(monkeypatch, capsys):
    """Exceptions raised in Python log handlers must be surfaced via stderr.

    intLog catches bp::error_already_set and calls PyErr_Print(), which
    prints the traceback to stderr.  Logging must never re-throw because
    it is called from noexcept destructor paths (e.g. ZmqServer, Client).
    """
    rogue.Logging.setForwardPython(True)
    rogue.Logging.setLevel(rogue.Logging.Warning)

    sentinel = 'rogue-intlog-handler-sentinel'

    class RaisingHandler(logging.Handler):
        def emit(self, record):
            if getattr(record, 'rogue_cpp', False):
                raise RuntimeError(sentinel)

    h = RaisingHandler()
    root_log = logging.getLogger()
    root_log.addHandler(h)
    old_level = root_log.level
    root_log.setLevel(logging.DEBUG)

    try:
        mem = rim.Emulate(4, 0x100)
        del mem
    finally:
        root_log.removeHandler(h)
        root_log.setLevel(old_level)
        rogue.Logging.setForwardPython(False)
        rogue.Logging.setLevel(rogue.Logging.Error)

    captured = capsys.readouterr()
    assert sentinel in captured.err, (
        "intLog did not surface the Python handler exception via PyErr_Print; "
        f"expected '{sentinel}' in stderr but got: {captured.err!r}"
    )
