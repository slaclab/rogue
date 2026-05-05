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

Covers two behaviors that were previously broken:
  - intLog must propagate Python-handler exceptions instead of swallowing
    bp::error_already_set via PyErr_Print().
  - logInit() must call logging.basicConfig() at most once across repeated
    invocations.
"""

import logging

import rogue
import rogue.interfaces.memory as rim
import pyrogue as pr
import pyrogue._Logging as _pr_logging


def test_intlog_propagates_python_handler_exception(monkeypatch):
    """Exceptions raised in Python log handlers must propagate through intLog.

    intLog in src/rogue/Logging.cpp previously caught bp::error_already_set
    (raised when a Python log handler throws) and called PyErr_Print(),
    silently discarding the exception — the Python log call returned normally.
    This test installs a raising handler and asserts the exception propagates.
    """
    rogue.Logging.setForwardPython(True)
    # Drop level to Warning for the duration of this test; restore the
    # gblLevel_ default (Error == 40, see src/rogue/Logging.cpp) afterwards
    # so subsequent tests are not order-dependent on this mutation.
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

    exception_propagated = False
    try:
        # Creating an Emulate object triggers a C++ "Starting logger..." warning
        # which goes through intLog -> Python handler (if forwardPython is True).
        mem = rim.Emulate(4, 0x100)
        del mem
    except RuntimeError as exc:
        if sentinel in str(exc):
            exception_propagated = True
    finally:
        root_log.removeHandler(h)
        root_log.setLevel(old_level)
        rogue.Logging.setForwardPython(False)
        rogue.Logging.setLevel(rogue.Logging.Error)

    assert exception_propagated, (
        "bp::error_already_set was silently swallowed by intLog; "
        "RuntimeError from Python log handler did not propagate"
    )


def test_logging_basicconfig_called_at_most_once(monkeypatch):
    """logInit() must call logging.basicConfig() at most once.

    logInit() in python/pyrogue/_Logging.py previously called
    logging.basicConfig() unconditionally on every invocation. This test
    patches basicConfig with a counter and calls logInit() three times.
    """
    # Reset the module-global guard so the assertion exercises the new
    # idempotency check rather than passing vacuously when an earlier
    # test in the process has already set _LOG_INIT_DONE = True.
    monkeypatch.setattr(_pr_logging, '_LOG_INIT_DONE', False)

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
    assert n == 1, (
        f"logInit() called basicConfig() {n} times; expected exactly 1 after "
        "resetting the guard. basicConfig() should be guarded so repeated "
        "logInit() calls are idempotent."
    )
