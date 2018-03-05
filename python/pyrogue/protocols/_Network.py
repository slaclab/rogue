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

    def __init__(self,*,host,port,size=1400,packVer=1,wait=True, **kwargs):
        super(self.__class__, self).__init__(**kwargs)
        self._host = host
        self._port = port
        if(size<=1500):
            self._size = 1400
        else:
            self._size = 8900
        
        self._udp  = rogue.protocols.udp.Client(host,port,self._size)
        self._rssi = rogue.protocols.rssi.Client(self._size)

        if packVer == 2:
            self._pack = rogue.protocols.packetizer.CoreV2(self._size)
        else:
            self._pack = rogue.protocols.packetizer.Core(self._size)

        self._udp._setSlave(self._rssi.transport())
        self._rssi.transport()._setSlave(self._udp)

        self._rssi.application()._setSlave(self._pack.transport())
        self._pack.transport()._setSlave(self._rssi.application())

        self.add(pr.LocalVariable(name='rssiOpen',        mode='RO', value=0, pollInterval=1, localGet=self.getRssiOpen))
        self.add(pr.LocalVariable(name='rssiDownCount',   mode='RO', value=0, pollInterval=1, localGet=self.getRssiDownCount))
        self.add(pr.LocalVariable(name='rssiDropCount',   mode='RO', value=0, pollInterval=1, localGet=self.getRssiDropCount))
        self.add(pr.LocalVariable(name='rssiRetranCount', mode='RO', value=0, pollInterval=1, localGet=self.getRssiRetranCount))
        self.add(pr.LocalVariable(name='packDropCount',   mode='RO', value=0, pollInterval=1, localGet=self.getPackDropCount))
        self.add(pr.LocalVariable(name='rssiBusy',        mode='RO', value=0, pollInterval=1, localGet=self.getRssiBusy))

        if wait:
            curr = int(time.time())
            last = curr

            while not self._rssi.getOpen():
                time.sleep(.0001)
                curr = int(time.time())
                if last != curr:
                    self._log.warning("host=%s, port=%d -> Establishing link ..." % (host,port))
                    last = curr

    def application(self,dest):
        return(self._pack.application(dest))

    def getRssiOpen(self,dev=None,cmd=None):
        return(self._rssi.getOpen())

    def getRssiDownCount(self,dev=None,cmd=None):
        return(self._rssi.getDownCount())

    def getRssiDropCount(self,dev=None,cmd=None):
        return(self._rssi.getDropCount())

    def getRssiRetranCount(self,dev=None,cmd=None):
        return(self._rssi.getRetranCount())

    def getPackDropCount(self,dev=None,cmd=None):
        return(self._pack.getDropCount())

    def getRssiBusy(self,dev=None,cmd=None):
        return(self._rssi.getBusy())

