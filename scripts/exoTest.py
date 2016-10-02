#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Title      : EXO Interface Test
#-----------------------------------------------------------------------------
# File       : exoTest.py
# Author     : Ryan Herbst, rherbst@slac.stanford.edu
# Created    : 2016-09-29
# Last update: 2016-09-29
#-----------------------------------------------------------------------------
# Description:
# EXO Interface Testing
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to 
# the license terms in the LICENSE.txt file found in the top-level directory 
# of this distribution and at: 
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html. 
# No part of the rogue software platform, including this file, may be 
# copied, modified, propagated, or distributed except according to the terms 
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
import rogue.hardware.exo
import rogue.interfaces.stream
import time
import pyrogue

class exoDataRx(rogue.interfaces.stream.Slave):

   def __init__(self):
      rogue.interfaces.stream.Slave.__init__(self)

   def _acceptFrame(self,frame):
      print("Got Data size=%i" % (frame.getPayload()))

class exoCmdRx(rogue.interfaces.stream.Slave):

   def __init__(self):
      rogue.interfaces.stream.Slave.__init__(self)

   def checkParity(self,ba):
      for i in range (0,len(ba),2):
         bcnt = 0
         val = ba[i] | (ba[i+1] << 8)

         for j in range (0,15):
            if (val & (1 << j)) != 0: bcnt += 1

         if (bcnt % 2): return(False)
      return(True)

   def _acceptFrame(self,frame):
      ba = bytearray(frame.getPayload())
      frame.read(ba,0)
      ia = [(ba[x] | (ba[x+1]<<8)) for x in range(0,len(ba),2)]
      print("Got size=%i Data:  %s" % (len(ba),"".join("%04x:" % i for i in ia)))

      regAddr = (ba[0] & 0x3F) | ((ba[1] << 3) & 0x40)
      modAddr = ((ba[0] >> 6) & 0x3) | ((ba[1] << 2) & 0x1C)
      data    = ba[4] | (ba[2]<<8) | ((ba[5] << 16) & 0x3F0000) | ((ba[3] << 22) & 0xFC00000)

      print("ModAddr=0x%02x, RegAddr=0x%02x, Data=0x%08x, Parity=%i" % (modAddr,regAddr,data,self.checkParity(ba)))

class exoCmdTx(rogue.interfaces.stream.Master):

   def __init__(self):
      rogue.interfaces.stream.Master.__init__(self)

   def addParity(self,ba):
      for i in range (0,len(ba),2):
         bcnt = 0
         val = ba[i] | (ba[i+1] << 8)

         for j in range (0,15):
            if (val & (1 << j)) != 0: bcnt += 1

         if (bcnt % 2): ba[i+1] |= 0x40

   def sendCmd(self,ba):
      self.addParity(ba)
      ia = [(ba[x] | (ba[x+1]<<8)) for x in range(0,len(ba),2)]
      print("Gen size=%i Data:  %s" % (len(ba),"".join("%04x:" % i for i in ia)))
      frame = self._reqFrame(len(ba),True,0)
      frame.write(ba,0)
      self._sendFrame(frame)

   def genHeader(self,write,modAddr,regAddr):
      ba = bytearray(8)
      ba[0] = (regAddr & 0x3F) | ((modAddr << 6) & 0xC0)
      ba[1] = ((modAddr >> 2) & 0x7) | ((regAddr >> 3) & 0x8)
      if write:
         ba[1] |= 0x20
      ba[1] |= 0x80
      return(ba)

   def write(self,modAddr,regAddr,data):
      ba = self.genHeader(False,modAddr,regAddr)
      ba[2] = (data >> 8) & 0x7F
      ba[3] = (data >> 22) & 0x3F
      ba[4] = data & 0xFF
      ba[5] = (data >> 16) & 0x3F
      self.sendCmd(ba)

   def read(self,modAddr,regAddr):
      ba = self.genHeader(True,modAddr,regAddr)
      self.sendCmd(ba)

exoCmd  = rogue.hardware.exo.TemCmd()
exoData = rogue.hardware.exo.TemData()

print("Exo PCI Version = 0x%08x" % (exoCmd.getInfo().version))
print("Exo PCI Build   = %s"     % (exoCmd.getInfo().buildString()))

cmdTx = exoCmdTx()
cmdRx = exoCmdRx()
dataRx = exoDataRx()

pyrogue.streamConnect(exoCmd,cmdRx)
pyrogue.streamConnect(exoData,dataRx)
pyrogue.streamConnect(cmdTx,exoCmd)

while (True) :
   cmdTx.write(0xA,0xB,0x1234567)
   #cmdTx.read(0xA,0xB)
   time.sleep(5)

