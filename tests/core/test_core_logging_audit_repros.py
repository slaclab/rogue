#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
"""Audit repros for CORE-004, CORE-008, CORE-015 in the Logging subsystem.

CORE-004: intLog catches bp::error_already_set and calls PyErr_Print(),
          silently discarding the exception instead of re-raising or logging.
CORE-008: Logging.cpp line 94 contains the typo "Crate logger" (should be
          "Create logger").
CORE-015: logInit() calls logging.basicConfig() on every invocation; it
          should be guarded to call it at most once.
"""

import logging
import pathlib

import rogue
import rogue.interfaces.memory as rim
import pyrogue as pr


def test_intlog_swallowed_python_exception_core_004(monkeypatch):
    """Verify that exceptions raised in Python log handlers are not swallowed.

    On HEAD, intLog in src/rogue/Logging.cpp catches bp::error_already_set
    (raised when a Python log handler throws) and calls PyErr_Print(), but
    silently discards the exception — the Python log call returns normally.
    This test installs a raising handler and asserts the exception propagates.
    On HEAD the assertion fails: the RuntimeError is swallowed and
    `exception_propagated` remains False.
    """
    rogue.Logging.setForwardPython(True)
    rogue.Logging.setLevel(rogue.Logging.Warning)

    class RaisingHandler(logging.Handler):
        def emit(self, record):
            if getattr(record, 'rogue_cpp', False):
                raise RuntimeError('CORE-004-intlog-sentinel')

    h = RaisingHandler()
    root_log = logging.getLogger()
    root_log.addHandler(h)
    old_level = root_log.level
    root_log.setLevel(logging.DEBUG)

    exception_propagated = False
    try:
        # Creating an Emulate object triggers a C++ "Starting logger..." warning
        # which goes through intLog -> Python handler (if forwardPython is True).
        mem = rim.Emulate(4, 0x100)
        del mem
    except RuntimeError as exc:
        if 'CORE-004-intlog-sentinel' in str(exc):
            exception_propagated = True
    finally:
        root_log.removeHandler(h)
        root_log.setLevel(old_level)
        rogue.Logging.setForwardPython(False)

    assert exception_propagated, (
        "CORE-004: bp::error_already_set silently swallowed by intLog; "
        "RuntimeError from Python log handler was not propagated — "
        "PyErr_Print() was called but the exception was discarded"
    )


def test_logging_basicconfig_called_more_than_once_core_015(monkeypatch):
    """Verify logInit() calls logging.basicConfig() at most once.

    On HEAD, logInit() in python/pyrogue/_Logging.py calls
    logging.basicConfig() unconditionally on every invocation. This test
    patches basicConfig with a counter and calls logInit() three times. On
    HEAD the counter exceeds 1, failing the assertion.
    """
    call_count = [0]
    original_basicConfig = logging.basicConfig

    def counting_basicConfig(*args, **kwargs):
        call_count[0] += 1
        return original_basicConfig(*args, **kwargs)

    monkeypatch.setattr(logging, 'basicConfig', counting_basicConfig)

    pr.logInit()
    pr.logInit()
    pr.logInit()

    n = call_count[0]
    assert n <= 1, (
        "CORE-015: logInit() calls basicConfig() per-invocation; "
        f"expected at most 1 call but got {n}. "
        "basicConfig() should be guarded (e.g. checked via root handler list)"
    )


def test_logging_ctor_typo_smell_core_008():
    """Verify the 'Crate logger' typo in Logging.cpp is absent.

    On HEAD, src/rogue/Logging.cpp line 94 contains the comment
    '// Crate logger' (should be '// Create logger'). This test reads the
    source file as text and asserts the typo is not present.
    """
    src_file = pathlib.Path(__file__).parent.parent.parent / 'src' / 'rogue' / 'Logging.cpp'

    assert src_file.exists(), (
        "CORE-008: cannot locate src/rogue/Logging.cpp relative to test tree"
    )

    content = src_file.read_text()

    assert 'Crate logger' not in content, (
        "CORE-008: 'Crate logger' typo present in src/rogue/Logging.cpp; "
        "comment should read 'Create logger'"
    )
