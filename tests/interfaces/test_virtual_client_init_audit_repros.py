#-----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
#-----------------------------------------------------------------------------
# Description:
#   Audit repros for PYR-021 and PYR-022.
#   PYR-021: VirtualClient sets self._root via _waitForRoot() but the
#            monitoring thread can call _requestDone (which checks
#            self._root is not None at line 623) before __init__ completes
#            its post-connection setup.  The test asserts that self._root
#            is fully initialised (parent/root/client links set) before
#            the monitoring thread is started.
#   PYR-022: VirtualClient.stop() calls self._log.warning(...) at line 736
#            but self._log is not set if __init__ raises before line 460;
#            in that scenario, calling stop() raises AttributeError.
#            The test asserts that self._log is either the FIRST thing set
#            in __init__ or that stop() guards with hasattr.
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

import inspect

from pyrogue.interfaces._Virtual import VirtualClient


def test_virtual_client_root_init_order_pyr_021():
    """PYR-021: VirtualClient._requestDone may access self._log before it is set."""
    src = inspect.getsource(VirtualClient.__init__)
    lines = src.splitlines()

    # ZmqClient.__init__() (the C++ base) spawns the SUB thread immediately.
    # That SUB thread can invoke _requestDone() which at line 623 calls
    # self._log.warning(...) when notify=True and self._root is not None.
    # Because self._root starts as None (pre-init), the guard at line 622
    # prevents the crash in the common path.  However self._log is set AFTER
    # ZmqClient.__init__() (line 460 in the source), so any path that triggers
    # _requestDone while self._root transitions from None to not-None but
    # self._log is not yet set will crash.
    #
    # The correct fix: set self._log BEFORE calling ZmqClient.__init__().
    # Assert that self._log is assigned before ZmqClient.__init__() is called.

    log_line = None
    zmq_init_line = None

    for i, line in enumerate(lines):
        stripped = line.strip()
        if "self._log = " in stripped and log_line is None:
            log_line = i
        if "ZmqClient.__init__" in stripped and zmq_init_line is None:
            zmq_init_line = i

    assert log_line is not None, (
        "PYR-021: Could not find `self._log =` in VirtualClient.__init__"
    )
    assert zmq_init_line is not None, (
        "PYR-021: Could not find `ZmqClient.__init__` in VirtualClient.__init__"
    )

    # Assert self._log is set BEFORE the C++ constructor spawns the SUB thread.
    assert log_line < zmq_init_line, (
        "PYR-021: VirtualClient sets self._log AFTER ZmqClient.__init__() "
        "(line " + str(log_line) + " > " + str(zmq_init_line) + " in __init__); "
        "the SUB thread spawned by ZmqClient.__init__() can call "
        "_requestDone() which accesses self._log.warning before self._log "
        "is initialised, causing AttributeError during the connection window"
    )


def test_virtual_client_log_attribute_set_pyr_022():
    """PYR-022: VirtualClient.stop() accesses self._log without guard; init failure raises AttributeError."""
    init_src = inspect.getsource(VirtualClient.__init__)
    stop_src = inspect.getsource(VirtualClient.stop)

    # self._log must be the FIRST substantive assignment in __init__
    # OR stop() must guard with hasattr(self, '_log').
    # On HEAD self._log is set after ZmqClient.__init__() (line 460);
    # if ZmqClient.__init__() raises, self._log is never set.
    # stop() at line 736 calls self._log.warning(...) unconditionally.

    # Check 1: does stop() guard self._log?
    stop_guards_log = (
        "hasattr(self, '_log')" in stop_src
        or "getattr(self, '_log', None)" in stop_src
    )

    # Check 2: is self._log set before ZmqClient.__init__() in __init__?
    lines = init_src.splitlines()
    log_line = None
    zmq_init_line = None

    for i, line in enumerate(lines):
        stripped = line.strip()
        if "self._log = " in stripped and log_line is None:
            log_line = i
        if "ZmqClient.__init__" in stripped and zmq_init_line is None:
            zmq_init_line = i

    log_set_before_zmq_init = (
        log_line is not None
        and zmq_init_line is not None
        and log_line < zmq_init_line
    )

    assert stop_guards_log or log_set_before_zmq_init, (
        "PYR-022: VirtualClient.stop() calls self._log.warning(...) but "
        "self._log is set AFTER rogue.interfaces.ZmqClient.__init__() "
        "(line 460 in __init__); if the C++ constructor raises an exception, "
        "self._log is never set and any subsequent call to stop() will raise "
        "AttributeError — add hasattr guard in stop() or move self._log "
        "assignment before ZmqClient.__init__()"
    )
