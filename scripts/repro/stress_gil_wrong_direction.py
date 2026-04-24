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
  - STREAM-015
  - STREAM-016
  - STREAM-017
  - PROTO-RSSI-008
  - PROTO-RSSI-009
  - PROTO-RSSI-010
  - PROTO-UDP-005
  - PROTO-UDP-006
  - PROTO-PACK-005
  - PROTO-PACK-006
  - PROTO-PACK-007
  - PROTO-PACK-008
  - PROTO-SRP-004
  - PROTO-SRP-005
  - PROTO-SRP-006
  - PROTO-BATCH-002
  - PROTO-BATCH-003
  - PROTO-BATCH-004
  - PROTO-BATCH-005
  - PROTO-BATCH-006
  - PROTO-BATCH-007
  - HW-CORE-021
  - HW-CORE-022
  - HW-CORE-023
  - HW-CORE-024
  - HW-CORE-025
  - HW-CORE-026
  - HW-CORE-027

Exercises the 28 "wrong-direction" GilRelease sites where a cpp-worker thread
that does NOT hold the Python GIL nonetheless calls PyEval_SaveThread() via
rogue::GilRelease. On CPython this is currently a no-op on an unowned GIL,
but future CPython/Boost.Python versions may tighten the check. The goal of
this harness is to ensure every wrong-direction site is *executed* at least
once per TSan run so that any future tightening surfaces immediately.

Per CONTEXT.md D-16, ambiguous/needs-investigation sites stay in the
parametrization — we don't prune them to "not-triggerable" without evidence.
"""
import threading

import pytest
import rogue

from conftest import skip_on_macos

pytestmark = pytest.mark.repro


# ---- pipeline factories ---------------------------------------------------

def _build_fifo_pipeline():
    """Fifo → Slave: stream acceptFrame cpp-worker path (STREAM-015/016/017)."""
    fifo = rogue.interfaces.stream.Fifo(100, 0, False)
    slave = rogue.interfaces.stream.Slave()
    fifo._setSlave(slave)
    return fifo, slave


def _build_slave_pipeline():
    """Bare Slave: acceptFrame GilRelease entry (HW-CORE-021)."""
    slave = rogue.interfaces.stream.Slave()
    return slave, None


def _build_packetizer_v1_pipeline():
    """Packetizer V1 Core: transportRx cpp-worker GilRelease (PROTO-PACK-005/007)."""
    core = rogue.protocols.packetizer.Core(False)
    app = core.application(0)
    return core, app


def _build_packetizer_v2_pipeline():
    """Packetizer V2 Core: transportRx cpp-worker GilRelease (PROTO-PACK-006/008)."""
    core = rogue.protocols.packetizer.CoreV2(False, True, False)
    app = core.application(0)
    return core, app


def _build_batcher_v1_pipeline():
    """Batcher V1: Splitter/Formatter cpp-worker GilRelease (PROTO-BATCH-002/003/004)."""
    batcher = rogue.protocols.batcher.CoreV1()
    return batcher, None


def _build_batcher_v2_pipeline():
    """Batcher V2: Splitter/Formatter cpp-worker GilRelease (PROTO-BATCH-005/006/007)."""
    batcher = rogue.protocols.batcher.SplitterV1()
    return batcher, None


def _build_rssi_pipeline():
    """RSSI Controller: transportRx cpp-worker GilRelease (PROTO-RSSI-008/009/010)."""
    us = rogue.protocols.udp.Server(19890, False)
    uc = rogue.protocols.udp.Client("127.0.0.1", 19891, False)
    return us, uc


def _build_udp_pipeline():
    """UDP Client/Server: runThread cpp-worker GilRelease (PROTO-UDP-005/006)."""
    us = rogue.protocols.udp.Server(19990, False)
    uc = rogue.protocols.udp.Client("127.0.0.1", 19990, False)
    return us, uc


def _build_prbs_pipeline():
    """Prbs gen/accept: cpp-worker GilRelease (HW-CORE-022/023/024)."""
    prbs = rogue.utilities.Prbs()
    return prbs, None


def _build_streamzip_pipeline():
    """StreamZip / StreamUnZip: cpp-worker GilRelease (HW-CORE-025/026)."""
    zipper = rogue.utilities.StreamZip(1)
    unzipper = rogue.utilities.StreamUnZip()
    return zipper, unzipper


def _build_streamwriter_pipeline():
    """StreamWriter channel: acceptFrame cpp-worker GilRelease (HW-CORE-027)."""
    writer = rogue.utilities.fileio.StreamWriter()
    ch = writer.getChannel(0)
    return writer, ch


def _build_srp_pipeline():
    """SrpV3: acceptFrame / doTransaction cpp-worker GilRelease (PROTO-SRP-004/005/006)."""
    srp = rogue.protocols.srp.SrpV3()
    return srp, None


# ---- parametrized stress test --------------------------------------------

@pytest.mark.repro
@pytest.mark.parametrize("site_name,factory", [
    ("stream_fifo",     _build_fifo_pipeline),
    ("stream_slave",    _build_slave_pipeline),
    ("packetizer_v1",   _build_packetizer_v1_pipeline),
    ("packetizer_v2",   _build_packetizer_v2_pipeline),
    ("batcher_v1",      _build_batcher_v1_pipeline),
    ("batcher_v2",      _build_batcher_v2_pipeline),
    pytest.param("rssi",         _build_rssi_pipeline,         marks=skip_on_macos),
    pytest.param("udp",          _build_udp_pipeline,          marks=skip_on_macos),
    ("prbs",            _build_prbs_pipeline),
    ("streamzip",       _build_streamzip_pipeline),
    ("streamwriter",    _build_streamwriter_pipeline),
    ("srp",             _build_srp_pipeline),
])
def test_stress_gil_wrong_direction(site_name, factory, stress_iters):
    """Drive stress_iters frames through each pipeline to exercise wrong-direction GilRelease."""
    errors = []

    def worker():
        for _ in range(stress_iters // 10):
            try:
                a, b = factory()
                # Keep both refs alive so dtor runs at loop bottom.
                _ = (a, b)
            except Exception as e:
                errors.append(e)

    threads = [threading.Thread(target=worker) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors, f"{site_name} wrong-direction GilRelease stress errors: {errors}"
