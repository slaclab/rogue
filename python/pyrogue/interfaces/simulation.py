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

class SideBandSim():

    def __init__(self,host,port):

        self._log = pyrogue.logInit(cls=self)

        self._ctx = zmq.Context()
        self._sbPush = self._ctx.socket(zmq.PUSH)
        self._sbPush.connect(f"tcp://{host}:{port+1}")
        self._sbPull = self._ctx.socket(zmq.PULL)        
        self._sbPull.connect(f"tcp://{host}:{port}")

        self._log.info("Connected to port {} on host {}".format(port,host))
        
        self._recvCb = self._defaultRecvCb
        self._ackCond = threading.Condition()
        self._recvThread = threading.Thread(target=self._recvWorker)
        self._recvThread.start()

    def _defaultRecvCb(self, opCode, remData):
        if opCode is not None:
            print(f'Received opCode: {opCode:02x}')
        if remDataNew is not None:
            print(f'Received remData: {remData:02x}')

    def setRecvCb(self, cbFunc):
        self._recvCb = cbFunc

    def send(self,opCode=None, remData=None):
        ba = bytearray(4)
        if opCode is not None:
            ba[0] = 0x01
            ba[1] = opCode
        if remData is not None:
            ba[2] = 0x01
            ba[3] = remData
            
        self._sbPush.send(ba)

        # Wait for ack
        with self._ackCond:
            self._ackCond.wait()

    def _recvWorker(self):
        while True:
            # Wait for new data
            ba = self._sbPull.recv()

            # Check for an ack
            if len(ba) == 1 and ba[0] == 0xFF:
                with self._ackCond:
                    self._ackCond.notify()
                continue

            # Got normal data
            opCode = None
            remData = None
            if ba[0] == 0x01:
                opCode = ba[1]
            if ba[2] == 0x01:
                remData = ba[3]
            self._recvCb(opCode, remData)

class Pgp2bSim():
    def __init__(self, vcCount, host, port):
        # virtual channels
        self.vc = [rogue.interfaces.stream.TcpClient(host, p) for p in range(port, port+(vcCount*2), 2)]

        # sideband
        self.sb = SideBandSim(host, port+8)

def connectPgp2bSim(pgpA, pgpB):
    for a,b in zip(pgpA.vc, pgpB.vc):
        pyrogue.streamConnectBiDir(a, b)

    pgpA.sb.setRecvCb(pgpB.sb.send)
    pgpB.sb.setRecvCb(pgpA.sb.send)

class MemEmulate(rogue.interfaces.memory.Slave):

    def __init__(self, *, minWidth=4, maxSize=0xFFFFFFFF):
        rogue.interfaces.memory.Slave.__init__(self,4,4)
        self._minWidth = minWidth
        self._maxSize  = maxSize
        self._data = {}
        self._cb   = {}

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

