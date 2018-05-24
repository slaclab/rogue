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

    def __init__(self,*,host,port,size=None, jumbo=False, wait=True, packVer=1, pollInterval=1, **kwargs):
        super(self.__class__, self).__init__(**kwargs)
        self._host = host
        self._port = port

        if size is not None:
            self._log.critical("Size arg is deprecated. Use jumbo arg instead")

        self._udp  = rogue.protocols.udp.Client(host,port,jumbo)

        self._rssi = rogue.protocols.rssi.Client(self._udp.maxPayload())
        self._udp.setRxBufferCount(self._rssi.getRemMaxSegment());

        if packVer == 2:
            self._pack = rogue.protocols.packetizer.CoreV2(False,True) # ibCRC = False, obCRC = True
        else:
            self._pack = rogue.protocols.packetizer.Core()

        self._udp._setSlave(self._rssi.transport())
        self._rssi.transport()._setSlave(self._udp)

        self._rssi.application()._setSlave(self._pack.transport())
        self._pack.transport()._setSlave(self._rssi.application())
        
        if wait:
            curr = int(time.time())
            last = curr

            while not self._rssi.getOpen():
                time.sleep(.0001)
                curr = int(time.time())
                if last != curr:
                    self._log.warning("host=%s, port=%d -> Establishing link ..." % (host,port))
                    last = curr

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
            localGet    = lambda: self._rssi.getDownCount(),
            pollInterval= pollInterval, 
        )) 

        self.add(pr.LocalVariable(
            name        = 'rssiDropCount',
            mode        = 'RO', 
            value       = 0, 
            localGet    = lambda: self._rssi.getDropCount(),
            pollInterval= pollInterval, 
        ))  

        self.add(pr.LocalVariable(
            name        = 'rssiRetranCount',
            mode        = 'RO', 
            value       = 0, 
            localGet    = lambda: self._rssi.getRetranCount(),
            pollInterval= pollInterval, 
        ))  
        
        self.add(pr.LocalVariable(
            name        = 'locBusy',
            mode        = 'RO', 
            value       = False, 
            localGet    = lambda: self._rssi.getLocBusy(),
            hidden      = True,
            pollInterval= pollInterval, 
        )) 
        
        self.add(pr.LocalVariable(
            name        = 'locBusyCnt',
            mode        = 'RO', 
            value       = 0, 
            localGet    = lambda: self._rssi.getLocBusyCnt(),
            pollInterval= pollInterval, 
        ))         
        
        self.add(pr.LocalVariable(
            name        = 'remBusy',
            mode        = 'RO', 
            value       = False, 
            localGet    = lambda: self._rssi.getRemBusy(),
            hidden      = True,
            pollInterval= pollInterval, 
        )) 
        
        self.add(pr.LocalVariable(
            name        = 'remBusyCnt',
            mode        = 'RO', 
            value       = 0, 
            localGet    = lambda: self._rssi.getRemBusyCnt(),
            pollInterval= pollInterval, 
        ))                 

        self.add(pr.LocalVariable(
            name        = 'maxRetran',
            mode        = 'RO', 
            value       = 0, 
            localGet    = lambda: self._rssi.getMaxRetran(),
            pollInterval= pollInterval, 
        ))    

        self.add(pr.LocalVariable(
            name        = 'remMaxBuffers',
            mode        = 'RO', 
            value       = 0, 
            localGet    = lambda: self._rssi.getRemMaxBuffers(),
            pollInterval= pollInterval, 
        )) 

        self.add(pr.LocalVariable(
            name        = 'remMaxSegment',
            mode        = 'RO', 
            value       = 0, 
            localGet    = lambda: self._rssi.getRemMaxSegment(),
            units       = 'Bytes', 
            pollInterval= pollInterval, 
        ))   

        self.add(pr.LocalVariable(
            name        = 'retranTout',
            mode        = 'RO', 
            value       = 0, 
            localGet    = lambda: self._rssi.getRetranTout(),
            units       = 'ms', 
            pollInterval= pollInterval, 
        ))  

        self.add(pr.LocalVariable(
            name        = 'cumAckTout',
            mode        = 'RO', 
            value       = 0, 
            localGet    = lambda: self._rssi.getCumAckTout(),
            units       = 'ms', 
            pollInterval= pollInterval, 
        ))  

        self.add(pr.LocalVariable(
            name        = 'nullTout',
            mode        = 'RO', 
            value       = 0, 
            localGet    = lambda: self._rssi.getNullTout(),
            units       = 'ms', 
            pollInterval= pollInterval, 
        ))

        self.add(pr.LocalVariable(
            name        = 'maxCumAck',
            mode        = 'RO', 
            value       = 0, 
            localGet    = lambda: self._rssi.getMaxCumAck(),
            pollInterval= pollInterval, 
        ))  

        self.add(pr.LocalVariable(
            name        = 'segmentSize',
            mode        = 'RO', 
            value       = 0, 
            localGet    = lambda: self._rssi.getSegmentSize(),
            units       = 'Bytes',
            pollInterval= pollInterval, 
        ))                    
                            
    def application(self,dest):
        return(self._pack.application(dest))

    def stop(self):
        self._rssi.stop()
