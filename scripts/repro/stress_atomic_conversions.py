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
  - STREAM-003
  - STREAM-004
  - STREAM-005
  - MEM-003
  - MEM-004
  - PROTO-UDP-001
  - HW-CORE-008
  - HW-CORE-014

Stress non-atomic threadEn_/bool field writes from stop() vs reads from
runThread() across multiple subsystems. Each test constructs a service,
starts its worker thread, then triggers stop() via destruction/close while
the worker is in its tight-loop read of threadEn_. TSan flags the
unsynchronized bool access.
"""
import os
import threading

import pytest
import rogue

from conftest import skip_on_macos  # UDP/TCP tests need macOS skip per PROTO-RSSI-006 / PROTO-UDP-002

pytestmark = pytest.mark.repro


@pytest.mark.repro
def test_stress_tcpcore_threaden(stress_iters):
    """TcpCore::stop() writes threadEn_ while runThread reads it (STREAM-003)."""
    errors = []

    def cycle():
        for _ in range(stress_iters // 10):
            try:
                tc = rogue.interfaces.stream.TcpCore("127.0.0.1", 19090, False)
                del tc  # dtor triggers stop() path → writes threadEn_
            except Exception as e:
                errors.append(e)

    threads = [threading.Thread(target=cycle) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors, f"TcpCore stress errors: {errors}"


@pytest.mark.repro
def test_stress_zmqclient_threaden(stress_iters):
    """ZmqClient::stop() writes threadEn_ while runThread reads it (STREAM-004)."""
    errors = []

    def cycle():
        for _ in range(stress_iters // 10):
            try:
                zc = rogue.interfaces.ZmqClient("127.0.0.1", 19190, False)
                del zc
            except Exception as e:
                errors.append(e)

    threads = [threading.Thread(target=cycle) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors, f"ZmqClient stress errors: {errors}"


@pytest.mark.repro
def test_stress_zmqserver_threaden(stress_iters):
    """ZmqServer::stop() writes threadEn_ while runThread reads it (STREAM-005)."""
    errors = []

    def cycle():
        for i in range(stress_iters // 10):
            try:
                zs = rogue.interfaces.ZmqServer("127.0.0.1", 19290 + i)
                del zs
            except Exception as e:
                errors.append(e)

    threads = [threading.Thread(target=cycle) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors, f"ZmqServer stress errors: {errors}"


@pytest.mark.repro
@skip_on_macos
def test_stress_tcpclient_threaden(stress_iters):
    """TcpClient::stop() threadEn_ race (MEM-003)."""
    errors = []

    def cycle():
        for _ in range(stress_iters // 10):
            try:
                tc = rogue.interfaces.memory.TcpClient("127.0.0.1", 19390)
                del tc
            except Exception as e:
                errors.append(e)

    threads = [threading.Thread(target=cycle) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors, f"TcpClient stress errors: {errors}"


@pytest.mark.repro
@skip_on_macos
def test_stress_tcpserver_threaden(stress_iters):
    """TcpServer::stop() threadEn_ race (MEM-004)."""
    errors = []

    def cycle():
        for i in range(stress_iters // 10):
            try:
                ts = rogue.interfaces.memory.TcpServer("127.0.0.1", 19490 + i)
                del ts
            except Exception as e:
                errors.append(e)

    threads = [threading.Thread(target=cycle) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors, f"TcpServer stress errors: {errors}"


@pytest.mark.repro
@skip_on_macos
def test_stress_udp_threaden(stress_iters):
    """UDP Client/Server stop() threadEn_ race (PROTO-UDP-001)."""
    errors = []

    def cycle():
        for i in range(stress_iters // 10):
            try:
                us = rogue.protocols.udp.Server(19590 + i, False)
                uc = rogue.protocols.udp.Client("127.0.0.1", 19590 + i, False)
                del uc
                del us
            except Exception as e:
                errors.append(e)

    threads = [threading.Thread(target=cycle) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors, f"UDP stress errors: {errors}"


@pytest.mark.repro
def test_stress_prbs_threaden(stress_iters):
    """Prbs::runThread threadEn_ and txSize_ non-atomic reads (HW-CORE-014)."""
    errors = []

    def cycle():
        for _ in range(stress_iters // 10):
            try:
                p = rogue.utilities.Prbs()
                p.genFrame(1024)
                p.setRxEnable(False)
            except Exception as e:
                errors.append(e)

    threads = [threading.Thread(target=cycle) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors, f"Prbs stress errors: {errors}"


@pytest.mark.repro
def test_stress_axistreamdma_threaden(stress_iters):
    """AxiStreamDma::runThread threadEn_ non-atomic read (HW-CORE-008).

    Hardware device /dev/axi_stream_dma_0 is not present in CI; this test
    constructs only when the device exists (gracefully skip otherwise), so
    that local hardware-present runs exercise the race. In CI the skip
    produces a passing no-op; that is acceptable since HW-CORE-008 is
    latent without the hardware loop active.
    """
    if not os.path.exists("/dev/axi_stream_dma_0"):
        pytest.skip("no AxiStreamDma hardware device present")
    errors = []

    def cycle():
        for _ in range(stress_iters // 10):
            try:
                d = rogue.hardware.axi.AxiStreamDma("/dev/axi_stream_dma_0", 0, True)
                del d
            except Exception as e:
                errors.append(e)

    threads = [threading.Thread(target=cycle) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors, f"AxiStreamDma stress errors: {errors}"
