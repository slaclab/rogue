#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Title      : Python package test 
#-----------------------------------------------------------------------------
# File       : exoTest.py
# Author     : Ryan Herbst, rherbst@slac.stanford.edu
# Created    : 2016-09-29
# Last update: 2016-09-29
#-----------------------------------------------------------------------------
# Description:
# Python package test
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to 
# the license terms in the LICENSE.txt file found in the top-level directory 
# of this distribution and at: 
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html. 
# No part of the rogue software platform, including this file, may be 
# copied, modified, propagated, or distributed except according to the terms 
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
import rogue.hardware.pgp
import pyrogue.devices.axi
import pyrogue.utilities.prbs
import pyrogue.utilities.fileio
import pyrogue.gui
import threading
import yaml
import time
import sys
import PyQt4.QtCore

# Microblaze console printout
class MbDebug(rogue.interfaces.stream.Slave):

   def __init__(self):
      rogue.interfaces.stream.Slave.__init__(self)
      self.enable = False

   def _acceptFrame(self,frame):
      if self.enable:
         p = bytearray(frame.getPayload())
         frame.read(p,0)
         print('-------- Microblaze Console --------')
         print(p.decode('utf-8'))


# Custom run control
class MyRunControl(pyrogue.RunControl,threading.Thread):
   def __init__(self,parent,name):
      threading.Thread.__init__(self)
      pyrogue.RunControl.__init__(self,parent,name)

   def _setRunState(self,cmd,value):
      if self._runState != value:
         self._runState = value

         if self._runState == 'Running':
            self.start()

   def run(self):

      while (self._runState == 'Running'):
         delay = 1.0 / ({value: key for key,value in self.runRate.enum.iteritems()}[self._runRate])
         time.sleep(delay)
         self._root.axiPrbsTx.oneShot()


# Set base
evalBoard = pyrogue.Root('evalBoard')

# Create the PGP interfaces
pgpVc0 = rogue.hardware.pgp.PgpCard('/dev/pgpcard_0',0,0)
pgpVc1 = rogue.hardware.pgp.PgpCard('/dev/pgpcard_0',0,1)
pgpVc3 = rogue.hardware.pgp.PgpCard('/dev/pgpcard_0',0,3)

print("")
print("PGP Card Version: %x" % (pgpVc0.getInfo().version))

# Create and Connect SRP to VC0
srp = rogue.protocols.srp.SrpV0()
pyrogue.streamConnectBiDir(pgpVc0,srp)

# File writer 
dataWriter = pyrogue.utilities.fileio.StreamWriter(evalBoard,'dataWriter')

# Add data stream to file as channel 1
pyrogue.streamConnect(pgpVc1,dataWriter.getChannel(0x1))

## Add console stream to file as channel 2
pyrogue.streamConnect(pgpVc3,dataWriter.getChannel(0x2))

# Add configuration stream to file as channel 0
pyrogue.streamConnect(evalBoard,dataWriter.getChannel(0x0))

# PRBS Receiver as secdonary receiver for VC1
prbsRx = pyrogue.utilities.prbs.PrbsRx(evalBoard,'prbsRx')
pyrogue.streamTap(pgpVc1,prbsRx)

# Microblaze console connected to VC2
mbcon = MbDebug()
pyrogue.streamTap(pgpVc3,mbcon)

# Add run control
runC = MyRunControl(evalBoard,'runControl')

# Add Devices
version = pyrogue.devices.axi.AxiVersion(parent=evalBoard,name='axiVersion',memBase=srp,offset=0x0)
hwPrbs  = pyrogue.devices.axi.AxiPrbsTx(parent=evalBoard,name='axiPrbsTx',memBase=srp,offset=0x30000)

# Create GUI
gui = pyrogue.gui.GuiThread(evalBoard)

