#-----------------------------------------------------------------------------
# Title      : PyRogue protocols / Network wrappers
#-----------------------------------------------------------------------------
# Description:
# Module containing protocol modules
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
import pyrogue as pr
import rogue.protocols.udp
import rogue.protocols.rssi
import rogue.protocols.packetizer
import time


class UdpRssiPack(pr.Device):

    def __init__(self,*, port, host='127.0.0.1', jumbo=False, wait=True, packVer=1, pollInterval=1, enSsi=True, server=False, **kwargs):
        super(self.__class__, self).__init__(**kwargs)
        self._host = host
        self._port = port

        if server:
            self._udp  = rogue.protocols.udp.Server(port,jumbo)
            self._rssi = rogue.protocols.rssi.Server(self._udp.maxPayload())
        else:
            self._udp  = rogue.protocols.udp.Client(host,port,jumbo)
            self._rssi = rogue.protocols.rssi.Client(self._udp.maxPayload())

        if packVer == 2:
            self._pack = rogue.protocols.packetizer.CoreV2(False,True,enSsi) # ibCRC = False, obCRC = True
        else:
            self._pack = rogue.protocols.packetizer.Core(enSsi)

        self._udp == self._rssi.transport()
        self._rssi.application() == self._pack.transport()

        self._rssi._start()

        if wait and not server:
            curr = int(time.time())
            last = curr
            cnt = 0

            while not self._rssi.getOpen():
                time.sleep(.0001)
                curr = int(time.time())
                if last != curr:
                    last = curr

                    if jumbo:
                        cnt += 1

                    if cnt < 10:
                        self._log.warning("host=%s, port=%d -> Establishing link ..." % (host,port))

                    else:
                        self._log.warning('host=%s, port=%d -> Failing to connect using jumbo frames! Be sure to check interface MTU settings with ifconig -a' % (host,port))


        self._udp.setRxBufferCount(self._rssi.curMaxBuffers())

        # Add variables
        self.add(pr.LocalVariable(
            name        = 'rssiOpen',
            mode        = 'RO',
            value       = False,
            localGet    = lambda: self._rssi.getOpen(),
            pollInterval= pollInterval,
        ))

        self.add(pr.LocalVariable(
            name        = 'rssiDownCount',
            mode        = 'RO',
            value       = 0,
            typeStr     = 'UInt32',
            localGet    = lambda: self._rssi.getDownCount(),
            pollInterval= pollInterval,
        ))

        self.add(pr.LocalVariable(
            name        = 'rssiDropCount',
            mode        = 'RO',
            value       = 0,
            typeStr     = 'UInt32',
            localGet    = lambda: self._rssi.getDropCount(),
            pollInterval= pollInterval,
        ))

        self.add(pr.LocalVariable(
            name        = 'rssiRetranCount',
            mode        = 'RO',
            value       = 0,
            typeStr     = 'UInt32',
            localGet    = lambda: self._rssi.getRetranCount(),
            pollInterval= pollInterval,
        ))

        self.add(pr.LocalVariable(
            name        = 'locBusy',
            mode        = 'RO',
            value       = True,
            localGet    = lambda: self._rssi.getLocBusy(),
            hidden      = True,
            pollInterval= pollInterval,
        ))

        self.add(pr.LocalVariable(
            name        = 'locBusyCnt',
            mode        = 'RO',
            value       = 0,
            typeStr     = 'UInt32',
            localGet    = lambda: self._rssi.getLocBusyCnt(),
            pollInterval= pollInterval,
        ))

        self.add(pr.LocalVariable(
            name        = 'remBusy',
            mode        = 'RO',
            value       = True,
            localGet    = lambda: self._rssi.getRemBusy(),
            hidden      = True,
            pollInterval= pollInterval,
        ))

        self.add(pr.LocalVariable(
            name        = 'remBusyCnt',
            mode        = 'RO',
            value       = 0,
            typeStr     = 'UInt32',
            localGet    = lambda: self._rssi.getRemBusyCnt(),
            pollInterval= pollInterval,
        ))

        self.add(pr.LocalVariable(
            name        = 'locTryPeriod',
            mode        = 'RW',
            value       = self._rssi.getLocTryPeriod(),
            typeStr     = 'UInt32',
            localGet    = lambda: self._rssi.getLocTryPeriod(),
            localSet    = lambda value: self._rssi.setLocTryPeriod(value)
        ))

        self.add(pr.LocalVariable(
            name        = 'locMaxBuffers',
            mode        = 'RW',
            value       = self._rssi.getLocMaxBuffers(),
            typeStr     = 'UInt8',
            localGet    = lambda: self._rssi.getLocMaxBuffers(),
            localSet    = lambda value: self._rssi.setLocMaxBuffers(value)
        ))

        self.add(pr.LocalVariable(
            name        = 'locMaxSegment',
            mode        = 'RW',
            value       = self._rssi.getLocMaxSegment(),
            typeStr     = 'UInt16',
            localGet    = lambda: self._rssi.getLocMaxSegment(),
            localSet    = lambda value: self._rssi.setLocMaxSegment(value)
        ))

        self.add(pr.LocalVariable(
            name        = 'locCumAckTout',
            mode        = 'RW',
            value       = self._rssi.getLocCumAckTout(),
            typeStr     = 'UInt16',
            localGet    = lambda: self._rssi.getLocCumAckTout(),
            localSet    = lambda value: self._rssi.setLocCumAckTout(value)
        ))

        self.add(pr.LocalVariable(
            name        = 'locRetranTout',
            mode        = 'RW',
            value       = self._rssi.getLocRetranTout(),
            typeStr     = 'UInt16',
            localGet    = lambda: self._rssi.getLocRetranTout(),
            localSet    = lambda value: self._rssi.setLocRetranTout(value)
        ))

        self.add(pr.LocalVariable(
            name        = 'locNullTout',
            mode        = 'RW',
            value       = self._rssi.getLocNullTout(),
            typeStr     = 'UInt16',
            localGet    = lambda: self._rssi.getLocNullTout(),
            localSet    = lambda value: self._rssi.setLocNullTout(value)
        ))

        self.add(pr.LocalVariable(
            name        = 'locMaxRetran',
            mode        = 'RW',
            value       = self._rssi.getLocMaxRetran(),
            typeStr     = 'UInt8',
            localGet    = lambda: self._rssi.getLocMaxRetran(),
            localSet    = lambda value: self._rssi.setLocMaxRetran(value)
        ))

        self.add(pr.LocalVariable(
            name        = 'locMaxCumAck',
            mode        = 'RW',
            value       = self._rssi.getLocMaxCumAck(),
            typeStr     = 'UInt8',
            localGet    = lambda: self._rssi.getLocMaxCumAck(),
            localSet    = lambda value: self._rssi.setLocMaxCumAck(value)
        ))

        self.add(pr.LocalVariable(
            name        = 'curMaxBuffers',
            mode        = 'RO',
            value       = 0,
            typeStr     = 'UInt8',
            localGet    = lambda: self._rssi.curMaxBuffers(),
            pollInterval= pollInterval
        ))

        self.add(pr.LocalVariable(
            name        = 'curMaxSegment',
            mode        = 'RO',
            value       = 0,
            typeStr     = 'UInt16',
            localGet    = lambda: self._rssi.curMaxSegment(),
            pollInterval= pollInterval
        ))

        self.add(pr.LocalVariable(
            name        = 'curCumAckTout',
            mode        = 'RO',
            value       = 0,
            typeStr     = 'UInt16',
            localGet    = lambda: self._rssi.curCumAckTout(),
            pollInterval= pollInterval
        ))

        self.add(pr.LocalVariable(
            name        = 'curRetranTout',
            mode        = 'RO',
            value       = 0,
            typeStr     = 'UInt16',
            localGet    = lambda: self._rssi.curRetranTout(),
            pollInterval= pollInterval
        ))

        self.add(pr.LocalVariable(
            name        = 'curNullTout',
            mode        = 'RO',
            value       = 0,
            typeStr     = 'UInt16',
            localGet    = lambda: self._rssi.curNullTout(),
            pollInterval= pollInterval
        ))

        self.add(pr.LocalVariable(
            name        = 'curMaxRetran',
            mode        = 'RO',
            value       = 0,
            typeStr     = 'UInt8',
            localGet    = lambda: self._rssi.curMaxRetran(),
            pollInterval= pollInterval
        ))

        self.add(pr.LocalVariable(
            name        = 'curMaxCumAck',
            mode        = 'RO',
            value       = 0,
            typeStr     = 'UInt8',
            localGet    = lambda: self._rssi.curMaxCumAck(),
            pollInterval= pollInterval
        ))

        self.add(pr.LocalCommand(
            name        = 'stop',
            function    = self._stop
        ))

        self.add(pr.LocalCommand(
            name        = 'start',
            function    = lambda: self._rssi._start()
        ))

    def application(self,dest):
        return(self._pack.application(dest))

    def _stop(self):
        self._rssi._stop()

        # This Device may not necessarily be added to a tree
        # So check if it has a parent first
        if self.parent is not None:
            self.rssiOpen.get()
