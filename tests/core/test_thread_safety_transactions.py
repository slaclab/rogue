#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
"""Thread-safety tests for concurrent variable writes through the Transaction path.

Concurrent LocalVariable.set() calls from multiple threads exercise the
sub-transaction creation and completion machinery. This test verifies that
no stale or orphan transactions are left behind under contention.
"""
import threading

import pyrogue as pr


class TxnRoot(pr.Root):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        dev = pr.Device(name='Blk')
        dev.add(pr.LocalVariable(name='RegA', value=0, mode='RW'))
        dev.add(pr.LocalVariable(name='RegB', value=0, mode='RW'))
        self.add(dev)


def test_concurrent_variable_writes_no_stale_transaction():
    """Concurrent writes should not leave stale/orphan transactions."""
    errors = []

    with TxnRoot() as root:
        stop = threading.Event()

        def write_loop(var_name):
            try:
                i = 0
                while not stop.is_set() and i < 500:
                    getattr(root.Blk, var_name).set(i)
                    i += 1
            except Exception as e:
                if not stop.is_set():
                    errors.append((var_name, e))

        t1 = threading.Thread(target=write_loop, args=('RegA',), daemon=True)
        t2 = threading.Thread(target=write_loop, args=('RegB',), daemon=True)
        t1.start()
        t2.start()

        t1.join(timeout=30)
        t2.join(timeout=30)
        stop.set()

        assert not t1.is_alive(), "write_loop(RegA) hung"
        assert not t2.is_alive(), "write_loop(RegB) hung"

    assert not errors, f"Transaction errors: {errors}"
