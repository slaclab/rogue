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
#
# Regression tests for error propagation through the ZmqServer pickle path.
#
# test_doRequest_always_returns_plain_exception: FAILS on unpatched code
# because _doRequest tries pickle.dumps(msg) first, which for picklable
# exceptions sends back the original type (e.g., rogue.GeneralError).
# After the fix, _doRequest always converts to Exception with a
# type-qualified message, guaranteeing pickle round-trip fidelity.

import pickle

import pyrogue as pr
import pyrogue.interfaces.simulation
import pyrogue.interfaces._ZmqServer as zmq_server_mod
import pytest
import rogue

pytestmark = pytest.mark.integration


class TimeoutMemEmulate(pr.interfaces.simulation.MemEmulate):
    """Memory emulator that drops transactions to force timeouts."""

    def __init__(self, *, dropCount=0, **kwargs):
        super().__init__(**kwargs)
        self._dropTotal = dropCount
        self._dropped = 0

    def _doTransaction(self, transaction):
        if self._dropped < self._dropTotal:
            self._dropped += 1
            return
        super()._doTransaction(transaction)


class ErrorPropDevice(pr.Device):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        for i in range(4):
            self.add(pr.RemoteVariable(
                name=f'Reg{i}',
                offset=0x04 * i,
                bitSize=32,
                base=pr.UInt,
                mode='RW',
            ))


class _StubZmqServer:
    """Lightweight stand-in for ZmqServer that exercises the pure-Python
    request-handling path without constructing the real server.

    The real :class:`ZmqServer` inherits from the pybind11-bound C++ server,
    whose constructor allocates a ZMQ context and whose ``stop()`` only
    releases it when ``threadEn_`` was set by ``start()``.  Tests that only
    need the pickle-conversion logic in ``_doRequest``/``_doOperation``
    should not allocate real ZMQ resources.
    """

    _doOperation = zmq_server_mod.ZmqServer._doOperation
    _doRequest = zmq_server_mod.ZmqServer._doRequest

    def __init__(self, root):
        self._root = root


def test_doRequest_always_returns_plain_exception():
    """_doRequest must always convert exceptions to plain Exception.

    On unpatched code, _doRequest tries pickle.dumps(msg) first.
    For picklable exceptions like rogue.GeneralError, this succeeds
    and the original C++ exception type is sent back.  This is fragile:
    the client must have the same C++ type available for unpickling.

    After the fix, _doRequest always wraps in Exception(type_qualified_msg),
    so the result is always a plain Exception with the type name in the
    message string.
    """
    root = pr.Root(name='TestRoot', pollEn=False)
    root.add(pr.Device(name='Dev'))
    server = _StubZmqServer(root=root)

    # Trigger a rogue.GeneralError from the server side
    def raise_general_error(*args, **kwargs):
        raise rogue.GeneralError("test_source", "test error message")

    root.Dev.bogus_method = raise_general_error

    request = pickle.dumps({
        "path": "TestRoot.Dev",
        "attr": "bogus_method",
    })
    result = pickle.loads(server._doRequest(request))

    assert isinstance(result, Exception), (
        f"Expected Exception, got {type(result).__name__}"
    )
    # The result must be a plain Exception, NOT rogue.GeneralError.
    # On unpatched code, it's rogue.GeneralError (pickle round-trips it).
    assert type(result) is Exception, (
        f"Expected plain Exception, got {type(result).__name__}. "
        "_doRequest should always convert to Exception for pickle safety."
    )
    assert "test error message" in str(result), (
        f"Error message lost: {str(result)!r}"
    )


def test_doRequest_includes_type_name_in_message():
    """The wrapped Exception must include the original type name.

    When _doRequest converts to Exception, the message must include
    the qualified type name so the caller can identify the original
    exception type.  On unpatched code, picklable exceptions are sent
    verbatim, so the type name is NOT in the message string.
    """
    root = pr.Root(name='TestRoot', pollEn=False)
    root.add(pr.Device(name='Dev'))
    server = _StubZmqServer(root=root)

    def raise_general_error(*args, **kwargs):
        raise rogue.GeneralError("test_source", "some error")

    root.Dev.bogus_method = raise_general_error

    request = pickle.dumps({
        "path": "TestRoot.Dev",
        "attr": "bogus_method",
    })
    result = pickle.loads(server._doRequest(request))

    msg = str(result)
    assert "GeneralError" in msg, (
        f"Exception message should include type name 'GeneralError'. "
        f"Got: {msg!r}"
    )


def test_general_error_str_preserves_message():
    """str(rogue.GeneralError) must include the error text."""
    err = rogue.GeneralError("Block::checkTransaction", "Timeout message")
    msg = str(err)
    assert "Timeout message" in msg, (
        f"str(rogue.GeneralError) lost the message: {msg!r}"
    )


def test_timeout_error_propagates_through_direct_read():
    """Server-side timeout must raise an exception on the caller."""
    class AlwaysDropRoot(pr.Root):
        def __init__(self):
            super().__init__(
                name='dropRoot',
                description='Always-drop root',
                timeout=0.01,
                initRead=False,
                pollEn=False,
            )
            sim = TimeoutMemEmulate(dropCount=999)
            self.addInterface(sim)
            self.add(ErrorPropDevice(
                name='Dev', offset=0x0, memBase=sim,
            ))

    root = AlwaysDropRoot()
    root.start()
    try:
        with pytest.raises(rogue.GeneralError, match="Timeout"):
            root.Dev.Reg0.get()
    finally:
        root.stop()


def test_server_recovers_after_timeout():
    """After a timeout, the server must recover for subsequent reads."""
    class RecoverRoot(pr.Root):
        def __init__(self):
            super().__init__(
                name='recoverRoot',
                description='Recovery test',
                timeout=0.01,
                initRead=False,
                pollEn=False,
            )
            sim = TimeoutMemEmulate(dropCount=1)
            self.addInterface(sim)
            self.add(ErrorPropDevice(
                name='Dev', offset=0x0, memBase=sim,
            ))

    root = RecoverRoot()
    root.start()
    try:
        with pytest.raises(rogue.GeneralError, match="Timeout"):
            root.Dev.Reg0.get()

        root.Dev.Reg1.set(0xCAFE)
        val = root.Dev.Reg1.get()
        assert val == 0xCAFE, (
            f"Server did not recover: got 0x{val:08x}, expected 0xCAFE"
        )
    finally:
        root.stop()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
