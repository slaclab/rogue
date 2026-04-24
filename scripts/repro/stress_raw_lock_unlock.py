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
  - HW-CORE-001
  - HW-CORE-002
  - MEM-001
  - MEM-002
  - HW-CORE-012
  - HW-CORE-013

Stress the raw mutex lock()/unlock() pairs in Logging.cpp levelMtx_,
memory/Slave.cpp and memory/Transaction.cpp classMtx_, and utilities/Prbs.cpp
pMtx_ under concurrent construction and enable/disable cycles. Any exception
between the raw lock()/unlock() pairs would permanently wedge the mutex; this
script exercises the critical sections under TSan.
"""
import threading

import pytest
import rogue

pytestmark = pytest.mark.repro


@pytest.mark.repro
def test_stress_logging_raw_lock(stress_iters):
    """Concurrent Logging::create exercises Logging.cpp levelMtx_.lock/unlock (HW-CORE-001/002)."""
    errors = []

    def worker():
        for i in range(stress_iters // 10):
            try:
                # Each pr.logInit / Logger() construction traverses Logging::create
                # which takes levelMtx_.lock()/unlock() without RAII.
                logger = rogue.Logging.create(f"stress_raw_lock_{i}")
                logger.setLevel(rogue.Logging.Info)
            except Exception as e:
                errors.append(e)

    threads = [threading.Thread(target=worker) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors, f"Errors during Logging stress: {errors}"


@pytest.mark.repro
def test_stress_memory_slave_raw_lock(stress_iters):
    """Concurrent memory Slave construction exercises Slave.cpp classMtx_.lock/unlock (MEM-001)."""
    errors = []

    def worker():
        for _ in range(stress_iters // 10):
            try:
                # rogue.interfaces.memory.Emulate constructs a memory Slave whose
                # ctor takes classMtx_.lock()/unlock() at lines 55-59 of Slave.cpp.
                s = rogue.interfaces.memory.Emulate(4, 0x1000)
                del s
            except Exception as e:
                errors.append(e)

    threads = [threading.Thread(target=worker) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors, f"Errors during memory Slave stress: {errors}"


@pytest.mark.repro
def test_stress_memory_transaction_raw_lock(memory_root, stress_iters):
    """Concurrent Transaction creation exercises Transaction.cpp classMtx_ (MEM-002)."""
    errors = []

    def worker():
        for _ in range(stress_iters // 10):
            try:
                # Issuing an address query on the memory emulator drives the
                # Transaction ctor path that takes classMtx_.lock()/unlock()
                # at lines 94-98 of Transaction.cpp.
                _ = memory_root._mem.getAddress()
            except Exception as e:
                errors.append(e)

    threads = [threading.Thread(target=worker) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors, f"Errors during Transaction stress: {errors}"


@pytest.mark.repro
def test_stress_prbs_raw_lock(stress_iters):
    """Concurrent Prbs enable/disable exercises Prbs.cpp pMtx_.lock/unlock (HW-CORE-012/013)."""
    errors = []

    prbs = rogue.utilities.Prbs()

    def worker():
        for i in range(stress_iters // 10):
            try:
                prbs.setRxEnable(i & 1 == 0)  # alternate enable/disable
                prbs.resetCount()              # exercises pMtx_.lock/unlock separately
            except Exception as e:
                errors.append(e)

    threads = [threading.Thread(target=worker) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors, f"Errors during Prbs stress: {errors}"
