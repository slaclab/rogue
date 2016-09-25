#!/usr/bin/env python

import rogue.hardware.pgp
import rogue.utilities 
import rogue.interfaces.stream
import time

# Microblaze console printout
class mbDebug(rogue.interfaces.stream.Slave):

   def __init__(self):
      rogue.interfaces.stream.Slave.__init__(self)

   def acceptFrame(self,frame):
      p = bytearray(frame.getPayload())
      frame.read(p,0)
      print("-------- Microblaze Console --------")
      print(p.decode("utf-8"))
      return False

pgpVc0 = rogue.hardware.pgp.PgpCard("/dev/pgpcard_0",0,0)
pgpVc1 = rogue.hardware.pgp.PgpCard("/dev/pgpcard_0",0,1)
pgpVc3 = rogue.hardware.pgp.PgpCard("/dev/pgpcard_0",0,3)

print("PGP Card Version: %x" % (pgpVc0.getInfo().version))

# Create and Connect SRP
srp = rogue.protocols.srp.Bridge(0)
srp.setSlave(pgpVc0)
pgpVc0.setSlave(srp)

probeA = rogue.interfaces.stream.Slave()
probeA.setDebug(16,"SRP Rx")
pgpVc0.addSlave(probeA)

probeB = rogue.interfaces.stream.Slave()
probeB.setDebug(16,"SRP Tx")
#srp.addSlave(probeB)

# Connect Data
dataRx = rogue.interfaces.stream.Slave()
dataRx.setDebug(10,"Data")
pgpVc1.setSlave(dataRx)

# Create registers
fwVersion  = rogue.interfaces.memory.Block(0x00000,4)
scratchpad = rogue.interfaces.memory.Block(0x00004,4)
deviceDna  = rogue.interfaces.memory.Block(0x00008,8)
heartbeat  = rogue.interfaces.memory.Block(0x00024,4)
buildstamp = rogue.interfaces.memory.Block(0x00800,256)
genPrbs    = rogue.interfaces.memory.Block(0x30000,4)
prbsLength = rogue.interfaces.memory.Block(0x30004,4)

# Connect to SRP
fwVersion.setSlave(srp)
scratchpad.setSlave(srp)
deviceDna.setSlave(srp)
heartbeat.setSlave(srp)
buildstamp.setSlave(srp)
genPrbs.setSlave(srp)
prbsLength.setSlave(srp)

# Post read transactions
fwVersion.doTransaction(False,False)
fwVersion.waitComplete(10000)
scratchpad.doTransaction(False,False)
scratchpad.waitComplete(10000)
deviceDna.doTransaction(False,False)
deviceDna.waitComplete(10000)
heartbeat.doTransaction(False,False)
heartbeat.waitComplete(10000)
buildstamp.doTransaction(False,False)
buildstamp.waitComplete(10000)
genPrbs.doTransaction(False,False)
genPrbs.waitComplete(10000)
prbsLength.doTransaction(False,False)
prbsLength.waitComplete(10000)

# Show results
print("")
print("Fw Version: 0x%08x"  % ( fwVersion.getUInt32(0)))
print("Scratchpad: 0x%08x"  % ( scratchpad.getUInt32(0)))
print("DeviceDna:  0x%016x" % ( deviceDna.getUInt64(0)))
print("Heartbeat:  0x%08x"  % ( heartbeat.getUInt32(0)))
print("BuildStamp: %s"      % ( buildstamp.getString()))
print("GenPrbs:    0x%08x"  % ( genPrbs.getUInt32(0)))
print("PrbsLength: 0x%08x"  % ( prbsLength.getUInt32(0)))
print("")

# Set scratchpad
print("Set scratchpad = 0x11111111")
scratchpad.setUInt32(0,0x11111111)
scratchpad.doTransaction(True,False) # Write
scratchpad.waitComplete(10000)
scratchpad.setUInt32(0,0x00000000) # test clear
scratchpad.doTransaction(False,False) # Write
scratchpad.waitComplete(10000)
print("Scratchpad: 0x%08x" % ( scratchpad.getUInt32(0)))
print("Set scratchpad = 0x22222222")
scratchpad.setUInt32(0,0x22222222)
scratchpad.doTransaction(True,False) # Write
scratchpad.waitComplete(10000)
scratchpad.setUInt32(0,0x00000000) # test clear
scratchpad.doTransaction(False,False) # Write
scratchpad.waitComplete(10000)
print("Scratchpad: 0x%08x" % ( scratchpad.getUInt32(0)))

# Wait a moment before connecting microblaze
time.sleep(1)
mbCon = mbDebug()
pgpVc3.setSlave(mbCon)

while (True):
   time.sleep(5)

