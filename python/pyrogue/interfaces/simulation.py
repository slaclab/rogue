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

class SidebandSim():

    def __init__(self,*,host,port):
        self._ctx = zmq.Context()
        self._obSock = self._ctx.socket(zmq.REQ)
        self._obSock.connect("tcp://%s:%i" % (host,port))

    def sendOpCode(self,opCode):
        ba = bytearray(2)
        ba[0] = 0xAA
        ba[1] = opCode
        self._ocSock.send(ba)

        # Wait for ack
        self._ocSock.recv_multipart()

    def setData(self,data):
        ba = bytearray(2)
        ba[0] = 0xBB
        ba[1] = data
        self._sbSock.send(ba)

        # Wait for ack
        self._sbSock.recv_multipart()

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

