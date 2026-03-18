#!/usr/bin/env python3
#-----------------------------------------------------------------------------
# Title      : Data over udp/packetizer/rssi test script
#-----------------------------------------------------------------------------
# This file is part of the rogue_example software. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue_example software, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
import rogue.utilities
import rogue.protocols.udp
import rogue.interfaces.stream
import rogue
import time
import threading
import pytest

pytestmark = pytest.mark.integration

# This is a protocol-stack regression test for UDP/RSSI/packetizer behavior,
# including out-of-order delivery. Smaller frame counts are enough to validate
# the path without turning the test into a stress benchmark.
FRAME_COUNT = 200
FRAME_SIZE = 2048
DRAIN_TIMEOUT = 10.0
CONNECTION_TIMEOUT = 10

class RssiOutOfOrder(rogue.interfaces.stream.Slave, rogue.interfaces.stream.Master):

    def __init__(self, period=0):
        rogue.interfaces.stream.Slave.__init__(self)
        rogue.interfaces.stream.Master.__init__(self)

        self._period = period
        self._lock   = threading.Lock()
        self._last   = None
        self._cnt    = 0

    @property
    def period(self):
        return self._period

    @period.setter
    def period(self, value):
        with self._lock:
            self._period = value

            # Send any cached frames if period is now 0
            if self._period == 0 and self._last is not None:
                self._sendFrame(self._last)
                self._last = None

    def _acceptFrame(self, frame: rogue.interfaces.stream.Frame) -> None:

        with self._lock:
            self._cnt += 1

            # Frame is cached, send current frame before cached frame
            if self._last is not None:
                self._sendFrame(frame)
                self._sendFrame(self._last)
                self._last = None

            # Out of order period has elapsed, store frame
            elif self._period > 0 and (self._cnt % self._period) == 0:
                self._last = frame

            # Otherwise just forward the frame
            else:
                self._sendFrame(frame)


def build_packetizer_pair(version):
    """Return matching packetizer endpoints for the requested wire version."""
    if version == 1:
        return rogue.protocols.packetizer.Core(True), rogue.protocols.packetizer.Core(True)
    return rogue.protocols.packetizer.CoreV2(True, True, True), rogue.protocols.packetizer.CoreV2(True, True, True)


def run_udp_packetizer_path(version, jumbo):
    """Validate UDP/RSSI/packetizer delivery under periodic out-of-order frames."""
    server = rogue.protocols.udp.Server(0, jumbo)
    port = server.getPort()
    client = rogue.protocols.udp.Client("127.0.0.1", port, jumbo)

    server_rssi = rogue.protocols.rssi.Server(server.maxPayload() - 8)
    client_rssi = rogue.protocols.rssi.Client(client.maxPayload() - 8)

    server_pack, client_pack = build_packetizer_pair(version)

    prbs_tx = rogue.utilities.Prbs()
    prbs_rx = rogue.utilities.Prbs()
    out_of_order = RssiOutOfOrder(period=0)

    prbs_tx >> client_pack.application(0)
    client_rssi.application() == client_pack.transport()
    client_rssi.transport() >> out_of_order >> client >> client_rssi.transport()

    server == server_rssi.transport()
    server_rssi.application() == server_pack.transport()
    server_pack.application(0) >> prbs_rx

    # Start with orderly transport first so the RSSI session comes up cleanly
    # before periodic reordering is introduced.
    server_rssi._start()
    client_rssi._start()

    waited = 0
    while not client_rssi.getOpen():
        time.sleep(1)
        waited += 1
        if waited == CONNECTION_TIMEOUT:
            client_rssi._stop()
            server_rssi._stop()
            raise AssertionError(f"RSSI timeout error. Ver={version} Jumbo={jumbo}")

    out_of_order.period = 10
    for _ in range(FRAME_COUNT):
        prbs_tx.genFrame(FRAME_SIZE)

    out_of_order.period = 0

    start = time.time()
    while prbs_rx.getRxCount() != FRAME_COUNT:
        time.sleep(0.1)
        if (time.time() - start) > DRAIN_TIMEOUT:
            client_rssi._stop()
            server_rssi._stop()
            raise AssertionError(
                f"Frame drain timeout. Ver={version} Jumbo={jumbo} "
                f"Got = {prbs_rx.getRxCount()} expected = {FRAME_COUNT}"
            )

    client_rssi._stop()
    server_rssi._stop()

    assert prbs_rx.getRxErrors() == 0


@pytest.mark.parametrize("version,jumbo", [(1, True), (2, True), (1, False), (2, False)])
def test_data_path(version, jumbo):
    run_udp_packetizer_path(version, jumbo)

if __name__ == "__main__":
    for version, jumbo in [(1, True), (2, True), (1, False), (2, False)]:
        run_udp_packetizer_path(version, jumbo)
