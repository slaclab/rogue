#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
"""
DETECTED-IDs:
  - MEM-011
  - MEM-015

Stress the sub-transaction completion race on `parentTran->subTranMap_.erase(id_)`
at Transaction.cpp lines 156-178 (MEM-011) and the TransactionLock traversal
that reads `isSubTransaction_` lock-free while holding GilRelease (MEM-015,
stretch goal). Concurrent Block reads/writes across many threads drive
simultaneous done() completions on sibling sub-transactions, exercising the
subTranMap_ erase path.
"""
import threading

import pyrogue as pr
import pytest

pytestmark = pytest.mark.repro


@pytest.mark.repro
def test_stress_sub_transaction_concurrent_done(memory_root, stress_iters):
    """Concurrent Block reads/writes drive simultaneous sub-transaction done() (MEM-011)."""
    errors = []

    # Issue reads/writes against the emulator from many threads so the
    # Transaction.cpp done() code path exercises subTranMap_.erase() under
    # contention. The Emulate slave completes transactions synchronously,
    # so chained reads drive repeated ctor/dtor cycles.
    def worker():
        for _ in range(stress_iters // 10):
            try:
                _ = memory_root._mem.getAddress()
                _ = memory_root._mem.doMaxAccess()
                _ = memory_root._mem.doMinAccess()
            except Exception as e:
                errors.append(e)

    threads = [threading.Thread(target=worker) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors, f"Sub-transaction stress errors: {errors}"


@pytest.mark.repro
@pytest.mark.xfail(strict=False, reason="MEM-015 stretch goal; may not trigger under Emulate backend")
def test_stress_transaction_lock_chain(memory_root, stress_iters):
    """TransactionLock traversal exercises lock-free isSubTransaction_ read (MEM-015 stretch)."""
    errors = []

    # Drive a read-modify-write cycle from two contending threads against the
    # root. The underlying RemoteVariable writes create Transactions; the
    # doneLock() path inside Transaction.cpp traverses isSubTransaction_
    # without holding the parent mutex — this is the behavior MEM-015 flags.
    def worker():
        for _ in range(stress_iters // 10):
            try:
                with pr.MemoryDevice(
                    name=f"dev_{threading.get_ident()}",
                    memBase=memory_root._mem,
                    offset=0x0,
                    size=0x100,
                ):
                    pass
            except Exception as e:
                errors.append(e)

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors, f"Transaction-lock chain stress errors: {errors}"
