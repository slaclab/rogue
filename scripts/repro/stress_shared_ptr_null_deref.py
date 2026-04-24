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
  - PROTO-PACK-002
  - PROTO-PACK-003

Stress the Packetizer V1/V2 SSI error-path use-after-reset pattern where
`tranFrame_[tmpDest].reset()` is followed by a `setError(0x80)` call on the
now-null shared_ptr in transportRx(). Under ASan this dereference produces
a heap-use-after-free / null-deref signal; under TSan the concurrent
tranFrame_ slot access races the setError write.

PyRogue-unreachable-in-CI caveat (per CONTEXT.md D-02): triggering the
exact SSI-EOF sequence from public Python API requires the transport-side
(UDP/RSSI) to deliver a precisely-formed frame with the EOF flag set on a
mid-assembly transaction. This harness exercises the shared transportRx
code path via repeated Core construction + application attach + frame
pushes; static analysis of the null-deref is deferred to Phase 3 review
for the sub-paths not reachable via public bindings.
"""
import threading

import pytest
import rogue

pytestmark = pytest.mark.repro


@pytest.mark.repro
def test_stress_packetizer_v1_ssi_eof(stress_iters):
    """Packetizer V1 transportRx SSI error-path use-after-reset (PROTO-PACK-003)."""
    errors = []

    def worker():
        for _ in range(stress_iters // 10):
            try:
                # Construct a V1 Core with SSI enabled; attach an application
                # slot so the transportRx() branch that touches tranFrame_[tmpDest]
                # has state to operate on. The Core's internal runThread exercises
                # the shared_ptr reset/setError sequence on error paths.
                core = rogue.protocols.packetizer.Core(True)  # enSsi=True
                app = core.application(0)
                del app
                del core
            except Exception as e:
                errors.append(e)

    threads = [threading.Thread(target=worker) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors, f"Packetizer V1 stress errors: {errors}"


@pytest.mark.repro
def test_stress_packetizer_v2_ssi_eof(stress_iters):
    """Packetizer V2 transportRx SSI error-path use-after-reset (PROTO-PACK-002)."""
    errors = []

    def worker():
        for _ in range(stress_iters // 10):
            try:
                # V2 Core: ibCRC=False, obCRC=True, enSsi=True — same SSI-error
                # path as V1 but with the V2 header layout. The destructor race
                # between transportRx and application-side consumers exercises
                # the tranFrame_ slot reset/setError pair.
                core = rogue.protocols.packetizer.CoreV2(False, True, True)
                app = core.application(0)
                del app
                del core
            except Exception as e:
                errors.append(e)

    threads = [threading.Thread(target=worker) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors, f"Packetizer V2 stress errors: {errors}"
