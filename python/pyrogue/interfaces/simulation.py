#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Title      : PyRogue simulation support
#-----------------------------------------------------------------------------
# File       : pyrogue/interfaces/simulation.py
# Created    : 2016-09-29
#-----------------------------------------------------------------------------
# Description:
# Module containing simulation support classes and routines
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to 
# the license terms in the LICENSE.txt file found in the top-level directory 
# of this distribution and at: 
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html. 
# No part of the rogue software platform, including this file, may be 
# copied, modified, propagated, or distributed except according to the terms 
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
import threading
import pyrogue
import rogue.interfaces.stream
import time
import zmq

class StreamSim(rogue.interfaces.stream.Master, 
                rogue.interfaces.stream.Slave, 
                threading.Thread):

    def __init__(self,*,host,dest,uid,ssi=False):
        rogue.interfaces.stream.Master.__init__(self)
        rogue.interfaces.stream.Slave.__init__(self)
        threading.Thread.__init__(self)

        self._log = pyrogue.logInit(self)

        ibPort = 5000 + dest + uid*100
        obPort = 6000 + dest + uid*100
        ocPort = 7000 + dest + uid*100
        sbPort = 8000 + dest + uid*100

        self._ctx = zmq.Context()
        self._ibSock = self._ctx.socket(zmq.REP)
        self._obSock = self._ctx.socket(zmq.REQ)
        self._ocSock = self._ctx.socket(zmq.REQ)
        self._sbSock = self._ctx.socket(zmq.REQ)
        self._ibSock.connect("tcp://%s:%i" % (host,ibPort))
        self._obSock.connect("tcp://%s:%i" % (host,obPort))
        self._ocSock.connect("tcp://%s:%i" % (host,ocPort))
        self._sbSock.connect("tcp://%s:%i" % (host,sbPort))

        self._log.info("Destination %i : id = %i, ib = %i, ob = %i, Code = %i, Side Data = %i" %
              (dest,uid,ibPort,obPort,ocPort,sbPort))

        self._ssi     = ssi
        self._enable  = True
        self.rxCount  = 0
        self.txCount  = 0

        self.start()

    def stop(self):
        self._enable = False

    def sendOpCode(self,opCode):
        ba = bytearray(1)
        ba[0] = opCode
        self._ocSock.send(ba)

        # Wait for ack
        self._ocSock.recv_multipart()

    def setData(self,data):
        ba = bytearray(1)
        ba[0] = data
        self._sbSock.send(ba)

        # Wait for ack
        self._sbSock.recv_multipart()

    def _acceptFrame(self,frame):
        """ Forward frame to simulation """

        flock = frame.lock();
        flags = frame.getFlags()
        fuser = flags & 0xFF
        luser = (flags >> 8) & 0xFF

        if ( self._ssi ):
            fuser = fuser | 0x2 # SOF
            if ( frame.getError() ): luser = luser | 0x1 # EOFE

        ba = bytearray(1)
        bb = bytearray(1)
        bc = bytearray(frame.getPayload())

        ba[0] = fuser
        bb[0] = luser
        frame.read(bc,0)

        self._obSock.send(ba,zmq.SNDMORE)
        self._obSock.send(bb,zmq.SNDMORE)
        self._obSock.send(bc)
        self.txCount += 1

        # Wait for ack
        self._obSock.recv_multipart()

    def run(self):
        """Receive frame from simulation"""

        while(self._enable):
            r = self._ibSock.recv_multipart()

            fuser = bytearray(r[0])[0]
            luser = bytearray(r[1])[0]
            data  = bytearray(r[2])

            frame = self._reqFrame(len(data),True)

            if ( self._ssi and (luser & 0x1)): frame.setError(1)

            frame.write(data,0)
            self._sendFrame(frame)
            self.rxCount += 1

            # Send ack
            ba = bytearray(1)
            ba[0] = 0xFF
            self._ibSock.send(ba)


class MemEmulate(rogue.interfaces.memory.Slave):

    def __init__(self, *, minWidth=4, maxSize=0xFFFFFFFF):
        rogue.interfaces.memory.Slave.__init__(self,4,4)
        self._minWidth = minWidth
        self._maxSize  = maxSize
        self._data = {}

    def _checkRange(self, address, size):
        return 0

    def _doMaxAccess(self):
        return(self._maxSize)

    def _doMinAccess(self):
        return(self._minWidth)

    def _doTransaction(self,transaction):
        address = transaction.address()
        size    = transaction.size()
        type    = transaction.type()

        if (address % self._minWidth) != 0:
            transaction.done(rogue.interfaces.memory.AddressError)
            return
        elif size > self._maxSize:
            transaction.done(rogue.interfaces.memory.SizeError)
            return

        for i in range (0, size):
            if not (address+i) in self._data:
                self._data[address+i] = 0

        ba = bytearray(size)

        if type == rogue.interfaces.memory.Write or type == rogue.interfaces.memory.Post:
            transaction.getData(ba,0)

            for i in range(0, size):
                self._data[address+i] = ba[i]

            transaction.done(0)

        else:
            for i in range(0, size):
                ba[i] = self._data[address+i]

            transaction.setData(ba,0)
            transaction.done(0)

