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
# Regression test for ESROGUE-734: timeout on init of multiple carriers
# simultaneously. When a register transaction times out during the initial
# read (Root.start with initRead=True), the root must log the error and
# continue starting rather than crashing with an unhandled exception.

import threading
import pyrogue as pr
import pyrogue.interfaces.simulation
import pytest

pytestmark = pytest.mark.integration


class TimeoutMemEmulate(pr.interfaces.simulation.MemEmulate):
    """Memory emulator that silently drops a configurable number of
    transactions, causing them to time out.  Used to simulate PCIe bus
    contention when multiple carriers initialise simultaneously."""

    def __init__(self, *, dropCount=0, **kwargs):
        super().__init__(**kwargs)
        self._dropTotal = dropCount
        self._dropped = 0

    def _doTransaction(self, transaction):
        if self._dropped < self._dropTotal:
            self._dropped += 1
            # Don't call transaction.done() or transaction.error() —
            # the transaction will time out.
            return
        super()._doTransaction(transaction)


class TimeoutDevice(pr.Device):
    """Simple device with several remote variables to exercise bulk reads."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        for i in range(4):
            self.add(pr.RemoteVariable(
                name      = f'Reg{i}',
                offset    = 0x04 * i,
                bitSize   = 32,
                bitOffset = 0,
                base      = pr.UInt,
                mode      = 'RW',
            ))


class TimeoutRoot(pr.Root):
    def __init__(self, dropCount=0):
        super().__init__(
            name='timeoutRoot',
            description='Root for timeout regression test',
            timeout=0.01,   # 10 ms — fast timeout for testing
            initRead=True,
            pollEn=False,
        )
        sim = TimeoutMemEmulate(dropCount=dropCount)
        self.addInterface(sim)
        self.add(TimeoutDevice(
            name    = 'Dev',
            offset  = 0x0,
            memBase = sim,
        ))


def test_init_read_timeout_does_not_crash():
    """Root.start() must survive a transaction timeout during the initial
    read.  Before the fix, the GeneralError propagated out of _read() and
    killed the entire start sequence."""
    root = TimeoutRoot(dropCount=1)
    # Should NOT raise — the timeout is caught and logged internally.
    with root:
        # Root started successfully despite the timeout.
        assert root.running is True


def test_read_raises_on_timeout():
    """Root._read() must raise GeneralError when a transaction times out,
    so that callers (e.g. scripts calling Read()) see the exception."""
    import rogue

    class AlwaysDropRoot(pr.Root):
        """Root whose memory slave always drops, ensuring _read raises."""
        def __init__(self):
            super().__init__(
                name='alwaysDropRoot',
                description='Root for exception-propagation test',
                timeout=0.01,
                initRead=False,  # We call _read manually
                pollEn=False,
            )
            sim = TimeoutMemEmulate(dropCount=999)
            self.addInterface(sim)
            self.add(TimeoutDevice(
                name='Dev', offset=0x0, memBase=sim,
            ))

    root = AlwaysDropRoot()
    root.start()
    try:
        with pytest.raises(rogue.GeneralError):
            root._read()
    finally:
        root.stop()


def test_init_read_succeeds_without_timeout():
    """Sanity check: init read succeeds normally when nothing times out."""
    root = TimeoutRoot(dropCount=0)
    with root:
        assert root.running is True
        assert root.Dev.Reg0.get() == 0


def test_concurrent_root_start_with_timeouts():
    """Simulate the reported scenario: multiple roots starting simultaneously,
    some experiencing transaction timeouts.  All roots must start successfully
    even if individual register reads time out."""
    num_roots = 6
    roots = []
    errors = []

    def start_root(idx, drop):
        r = None
        try:
            r = TimeoutRoot(dropCount=drop)
            r.start()
            roots.append(r)
        except Exception as e:
            if r is not None:
                try:
                    r.stop()
                except Exception:
                    pass
            errors.append((idx, e))

    threads = []
    for i in range(num_roots):
        # Roots 2 and 4 experience timeouts (like the 2-3 of 6 in the report)
        drop = 1 if i in (2, 4) else 0
        t = threading.Thread(target=start_root, args=(i, drop))
        threads.append(t)
        t.start()

    for t in threads:
        t.join(timeout=30)

    try:
        for t in threads:
            assert not t.is_alive(), f"Thread {t.name} did not finish within 30 s"

        assert len(errors) == 0, f"Root start failures: {errors}"
        assert len(roots) == num_roots
    finally:
        for r in roots:
            r.stop()


def test_init_write_timeout_does_not_crash():
    """Root.start() must survive a transaction timeout during the initial
    write (initWrite=True).  The GeneralError is caught and logged so
    startup continues."""

    class WriteTimeoutRoot(pr.Root):
        def __init__(self):
            super().__init__(
                name='writeTimeoutRoot',
                description='Root for init-write timeout test',
                timeout=0.01,
                initRead=False,
                initWrite=True,
                pollEn=False,
            )
            sim = TimeoutMemEmulate(dropCount=1)
            self.addInterface(sim)
            self.add(TimeoutDevice(
                name='Dev', offset=0x0, memBase=sim,
            ))

    root = WriteTimeoutRoot()
    with root:
        assert root.running is True


if __name__ == "__main__":
    test_init_read_timeout_does_not_crash()
    test_read_raises_on_timeout()
    test_init_read_succeeds_without_timeout()
    test_concurrent_root_start_with_timeouts()
    test_init_write_timeout_does_not_crash()
    print("All tests passed.")
