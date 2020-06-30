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
import pyrogue
import time
import threading

#rogue.Logging.setLevel(rogue.Logging.Debug)

FrameCount = 10000
FrameSize  = 10000

class RssiOutOfOrder(rogue.interfaces.stream.Slave, rogue.interfaces.stream.Master):

    def __init__(self, period=0):
        rogue.interfaces.stream.Slave.__init__(self)
        rogue.interfaces.stream.Master.__init__(self)

        self._period = period
        self._lock   = threading.Lock()
        self._last   = None
        self._cnt    = 0

    @property
    def period(self,value):
        return self._period

    @period.setter
    def period(self,value):
        with self._lock:
            self._period = value

            # Send any cached frames if period is now 0
            if self._period == 0 and self._last is not None:
                self._sendFrame(self._last)
                self._last = None

    def _acceptFrame(self,frame):

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


def data_path(ver,jumbo):
    print("Testing ver={} jumbo={}".format(ver,jumbo))

    # UDP Server
    serv = rogue.protocols.udp.Server(0,jumbo);
    port = serv.getPort()

    # UDP Client
    client = rogue.protocols.udp.Client("127.0.0.1",port,jumbo);

    # RSSI
    sRssi = rogue.protocols.rssi.Server(serv.maxPayload())
    cRssi = rogue.protocols.rssi.Client(client.maxPayload())

    # Packetizer
    if ver == 1:
        sPack = rogue.protocols.packetizer.Core(True)
        cPack = rogue.protocols.packetizer.Core(True)
    else:
        sPack = rogue.protocols.packetizer.CoreV2(True,True,True)
        cPack = rogue.protocols.packetizer.CoreV2(True,True,True)

    # PRBS
    prbsTx = rogue.utilities.Prbs()
    prbsRx = rogue.utilities.Prbs()

    # Out of order module on client side
    coo = RssiOutOfOrder(period=0)

    # Client stream
    prbsTx >> cPack.application(0)
    cRssi.application() == cPack.transport()

    # Insert out of order in the outbound direction
    cRssi.transport() >> coo >> client >> cRssi.transport()

    # Server stream
    serv == sRssi.transport()
    sRssi.application() == sPack.transport()
    sPack.application(0) >> prbsRx

    # Start RSSI with out of order disabled
    sRssi._start()
    cRssi._start()

    # Wait for connection
    cnt = 0
    print("Waiting for RSSI connection")
    while not cRssi.getOpen():
        time.sleep(1)
        cnt += 1

        if cnt == 10:
            cRssi._stop()
            sRssi._stop()
            raise AssertionError('RSSI timeout error. Ver={} Jumbo={}'.format(ver,jumbo))

    # Enable out of order with a period of 10
    coo.period = 10

    print("Generating Frames")
    for _ in range(FrameCount):
        prbsTx.genFrame(FrameSize)
    time.sleep(1)

    # Disable out of order
    coo.period = 0

    # Stop connection
    print("Closing Link")
    cRssi._stop()
    sRssi._stop()

    if prbsRx.getRxCount() != FrameCount:
        raise AssertionError('Frame count error. Ver={} Jumbo={} Got = {} expected = {}'.format(ver,jumbo,prbsRx.getRxCount(),FrameCount))

    if prbsRx.getRxErrors() != 0:
        raise AssertionError('PRBS Frame errors detected! Ver={} Jumbo={}'.format(ver,jumbo))

    print("Done testing ver={} jumbo={}".format(ver,jumbo))

def test_data_path():
    data_path(1,True)
    data_path(2,True)
    data_path(1,False)
    data_path(2,False)

if __name__ == "__main__":
    test_data_path()

