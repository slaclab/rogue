# ----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
# ----------------------------------------------------------------------------
"""``Root.stop()`` must stop the UDP receive thread of a ``UdpRssiPack``.

Before the fix only the RSSI controller was stopped, so the UDP worker kept
forwarding datagrams into the tree until garbage collection.
"""

import socket
import threading
import time

import pytest

import pyrogue as pr
import pyrogue.protocols
import rogue.interfaces.stream

pytestmark = pytest.mark.integration


class _CountingSink(rogue.interfaces.stream.Slave):
    def __init__(self):
        super().__init__()
        self.calls = 0

    def _acceptFrame(self, frame):
        self.calls += 1


class _ChatteringPeer:
    """UDP peer that answers the pack's first datagram with a steady stream.

    The RSSI client sends SYN packets as soon as it starts, which tells the
    peer where to send. The steady traffic keeps the pack's receive thread
    busy, so the test observes the thread being stopped rather than idle.
    """

    def __init__(self):
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.bind(('127.0.0.1', 0))
        self._sock.settimeout(0.05)
        self.port = self._sock.getsockname()[1]
        self._run = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _loop(self):
        peer = None
        while self._run:
            if peer is None:
                try:
                    _, peer = self._sock.recvfrom(2048)
                except socket.timeout:
                    continue
            try:
                # Eight zero bytes fail the RSSI header check and are dropped
                # by the transport, but still pass through the UDP master.
                self._sock.sendto(bytes(8), peer)
            except OSError:
                pass
            time.sleep(0.002)

    def close(self):
        self._run = False
        self._thread.join()
        self._sock.close()


def test_root_stop_stops_udp_receive_thread(wait_until):
    peer = _ChatteringPeer()
    sink = _CountingSink()
    try:
        root = pr.Root(name='root', pollEn=False)
        pack = pyrogue.protocols.UdpRssiPack(name='Net', host='127.0.0.1', port=peer.port, wait=False)
        root.add(pack)
        pack._udp >> sink

        with root:
            assert wait_until(lambda: sink.calls > 0, timeout=5.0)

        # Root.stop() has returned with the receive thread joined and the
        # socket closed, so the peer's datagrams no longer reach the tree.
        settled = sink.calls
        assert not wait_until(lambda: sink.calls > settled, timeout=0.3)
    finally:
        peer.close()
