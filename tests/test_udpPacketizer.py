#!/usr/bin/env python3
#-----------------------------------------------------------------------------
# Title      : Data over udp/packetizer/rssi test script
#-----------------------------------------------------------------------------
# File       : test_udpPacketizer.py
# Created    : 2018-03-02
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

#rogue.Logging.setLevel(rogue.Logging.Debug)

FrameCount = 10000
FrameSize  = 10000

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
        sPack = rogue.protocols.packetizer.CoreV2(False,True,True)
        cPack = rogue.protocols.packetizer.CoreV2(False,True,True)

    # PRBS
    prbsTx = rogue.utilities.Prbs()
    prbsRx = rogue.utilities.Prbs()

    # Client stream
    pyrogue.streamConnect(prbsTx,cPack.application(0))
    pyrogue.streamConnectBiDir(cRssi.application(),cPack.transport())
    pyrogue.streamConnectBiDir(client,cRssi.transport())

    # Server stream
    pyrogue.streamConnectBiDir(serv,sRssi.transport())
    pyrogue.streamConnectBiDir(sRssi.application(),sPack.transport())
    pyrogue.streamConnect(sPack.application(0),prbsRx)

    # Start RSSI
    sRssi.start()
    cRssi.start()

    # Wait for connection
    cnt = 0
    print("Waiting for RSSI connection")
    while not cRssi.getOpen():
        time.sleep(1)
        cnt += 1

        if cnt == 10:
            cRssi.stop()
            sRssi.stop()
            raise AssertionError('RSSI timeout error. Ver={} Jumbo={}'.format(ver,jumbo))

    print("Generating Frames")
    for _ in range(FrameCount):
        prbsTx.genFrame(FrameSize)
    time.sleep(1)

    # Stop connection
    print("Closing Link")
    cRssi.stop()
    sRssi.stop()

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

