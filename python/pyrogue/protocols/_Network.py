#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Title      : PyRogue protocols / Network wrappers
#-----------------------------------------------------------------------------
# File       : pyrogue/protocols/_Network.py
# Created    : 2017-01-15
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

    def __init__(self,*,host,port,size=None, jumbo=False, wait=True, packVer=1, pollInterval=1, enSsi=True, **kwargs):
        super(self.__class__, self).__init__(**kwargs)
        self._host = host
        self._port = port

        if size is not None:
            self._log.critical("Size arg is deprecated. Use jumbo arg instead")

        self._udp  = rogue.protocols.udp.Client(host,port,jumbo)

        self._rssi = rogue.protocols.rssi.Client(self._udp.maxPayload())

        if packVer == 2:
            self._pack = rogue.protocols.packetizer.CoreV2(False,True,enSsi) # ibCRC = False, obCRC = True
        else:
            self._pack = rogue.protocols.packetizer.Core(enSsi)

        self._udp._setSlave(self._rssi.transport())
        self._rssi.transport()._setSlave(self._udp)

        self._rssi.application()._setSlave(self._pack.transport())
        self._pack.transport()._setSlave(self._rssi.application())

        self._rssi.start()

        if wait:
            curr = int(time.time())
            last = curr

            while not self._rssi.getOpen():
                time.sleep(.0001)
                curr = int(time.time())
                if last != curr:
                    self._log.warning("host=%s, port=%d -> Establishing link ..." % (host,port))
                    last = curr

        self._udp.setRxBufferCount(self._rssi.curMaxBuffers());

        # Add variables
        self.add(pr.LocalVariable(
            name        = 'rssiOpen',
            mode        = 'RO', 
            localGet    = lambda: self._rssi.getOpen(),
            pollInterval= pollInterval, 
        ))
        
        self.add(pr.LocalVariable(
            name        = 'rssiDownCount',
            mode        = 'RO', 
            localGet    = lambda: self._rssi.getDownCount(),
            pollInterval= pollInterval, 
        )) 

        self.add(pr.LocalVariable(
            name        = 'rssiDropCount',
            mode        = 'RO', 
            localGet    = lambda: self._rssi.getDropCount(),
            pollInterval= pollInterval, 
        ))  

        self.add(pr.LocalVariable(
            name        = 'rssiRetranCount',
            mode        = 'RO', 
            localGet    = lambda: self._rssi.getRetranCount(),
            pollInterval= pollInterval, 
        ))  
        
        self.add(pr.LocalVariable(
            name        = 'locBusy',
            mode        = 'RO', 
            localGet    = lambda: self._rssi.getLocBusy(),
            hidden      = True,
            pollInterval= pollInterval, 
        )) 
        
        self.add(pr.LocalVariable(
            name        = 'locBusyCnt',
            mode        = 'RO', 
            localGet    = lambda: self._rssi.getLocBusyCnt(),
            pollInterval= pollInterval, 
        ))         
        
        self.add(pr.LocalVariable(
            name        = 'remBusy',
            mode        = 'RO', 
            localGet    = lambda: self._rssi.getRemBusy(),
            hidden      = True,
            pollInterval= pollInterval, 
        )) 
        
        self.add(pr.LocalVariable(
            name        = 'remBusyCnt',
            mode        = 'RO', 
            localGet    = lambda: self._rssi.getRemBusyCnt(),
            pollInterval= pollInterval, 
        ))                 

        self.add(pr.LocalVariable(
            name        = 'locTryPeriod',
            mode        = 'RW', 
            localGet    = lambda: self._rssi.getLocTryPeriod(),
            localSet    = lambda value: self._rssi.setLocTryPeriod(value)
        ))                 

        self.add(pr.LocalVariable(
            name        = 'locBusyThold',
            mode        = 'RW', 
            localGet    = lambda: self._rssi.getLocBusyThold(),
            localSet    = lambda value: self._rssi.setLocBusyThold(value)
        ))                 

        self.add(pr.LocalVariable(
            name        = 'locMaxBuffers',
            mode        = 'RW', 
            localGet    = lambda: self._rssi.getLocMaxBuffers(),
            localSet    = lambda value: self._rssi.setLocMaxBuffers(value)
        ))                 

        self.add(pr.LocalVariable(
            name        = 'locMaxSegment',
            mode        = 'RW', 
            localGet    = lambda: self._rssi.getLocMaxSegment(),
            localSet    = lambda value: self._rssi.setLocMaxSegment(value)
        ))                 

        self.add(pr.LocalVariable(
            name        = 'locCumAckTout',
            mode        = 'RW', 
            localGet    = lambda: self._rssi.getLocCumAckTout(),
            localSet    = lambda value: self._rssi.setLocCumAckTout(value)
        ))                 

        self.add(pr.LocalVariable(
            name        = 'locRetranTout',
            mode        = 'RW', 
            localGet    = lambda: self._rssi.getLocRetranTout(),
            localSet    = lambda value: self._rssi.setLocRetranTout(value)
        ))                 

        self.add(pr.LocalVariable(
            name        = 'locNullTout',
            mode        = 'RW', 
            localGet    = lambda: self._rssi.getLocNullTout(),
            localSet    = lambda value: self._rssi.setLocNullTout(value)
        ))                 

        self.add(pr.LocalVariable(
            name        = 'locMaxRetran',
            mode        = 'RW', 
            localGet    = lambda: self._rssi.getLocMaxRetran(),
            localSet    = lambda value: self._rssi.setLocMaxRetran(value)
        ))                 

        self.add(pr.LocalVariable(
            name        = 'locMaxCumAck',
            mode        = 'RW', 
            localGet    = lambda: self._rssi.getLocMaxCumAck(),
            localSet    = lambda value: self._rssi.setLocMaxCumAck(value)
        ))                 

        self.add(pr.LocalVariable(
            name        = 'curMaxBuffers',
            mode        = 'RO', 
            localGet    = lambda: self._rssi.curMaxBuffers(),
            pollInterval= pollInterval 
        ))                 

        self.add(pr.LocalVariable(
            name        = 'curMaxSegment',
            mode        = 'RO', 
            localGet    = lambda: self._rssi.curMaxSegment(),
            pollInterval= pollInterval 
        ))                 

        self.add(pr.LocalVariable(
            name        = 'curCumAckTout',
            mode        = 'RO', 
            localGet    = lambda: self._rssi.curCumAckTout(),
            pollInterval= pollInterval 
        ))                 

        self.add(pr.LocalVariable(
            name        = 'curRetranTout',
            mode        = 'RO', 
            localGet    = lambda: self._rssi.curRetranTout(),
            pollInterval= pollInterval 
        ))                 

        self.add(pr.LocalVariable(
            name        = 'curNullTout',
            mode        = 'RO', 
            localGet    = lambda: self._rssi.curNullTout(),
            pollInterval= pollInterval 
        ))                 

        self.add(pr.LocalVariable(
            name        = 'curMaxRetran',
            mode        = 'RO', 
            localGet    = lambda: self._rssi.curMaxRetran(),
            pollInterval= pollInterval 
        ))                 

        self.add(pr.LocalVariable(
            name        = 'curMaxCumAck',
            mode        = 'RO', 
            localGet    = lambda: self._rssi.curMaxCumAck(),
            pollInterval= pollInterval 
        ))                 
                            
        self.add(pr.LocalCommand(
            name        = 'stop',
            function    = self._stop
        ))

        self.add(pr.LocalCommand(
            name        = 'start',
            function    = lambda: self._rssi.start()
        ))

    def application(self,dest):
        return(self._pack.application(dest))

    def _stop(self):
        self._rssi.stop()
        self.rssiOpen.get()

