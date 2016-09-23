#!/usr/bin/env python

import rogue.hardware.pgp
import rogue.utilities 
import rogue.interfaces.stream
import time

class testSlave(rogue.interfaces.stream.Slave):

   def __init__(self):
      rogue.interfaces.stream.Slave.__init__(self)
      self.byteCnt = 0
      self.packCnt = 0

   def acceptFrame(self,frame,timeout):
      self.byteCnt += frame.getPayload()
      self.packCnt += 1
      p = bytearray(frame.getPayload())
      frame.read(p,0);
      if ( frame.getPayload() <= 100 ):
         print("Got size=%i Data: %s" % (len(p),"".join("%02x:" % b for b in p)))
      return(True)

pgpA = rogue.hardware.pgp.PgpCard()
pgpA.open("/dev/pgpcard_0",0,0)
pgpA.setLoop(1)

print("PGP Card Version: %x" % (pgpA.getInfo().version))

prbsA = rogue.utilities.Prbs()
prbsB = rogue.utilities.Prbs()

#prbsA.setSlave(pgpA)
prbsA.setSlave(prbsB)
pgpA.setSlave(prbsB)

ts1 = testSlave()
prbsA.addSlave(ts1)

#prbsA.enMessages(True)
#prbsB.enMessages(True)
prbsA.enable(1000)

tm = rogue.interfaces.stream.Master()
ts2 = testSlave()
tm.setSlave(ts2)

prbsC = rogue.utilities.Prbs()
ts3 = testSlave()
prbsC.setSlave(ts3)

count = 0

while (True) :
   
   print("")
   print("  PGP: Alloc Bytes %i, Count %i" % (pgpA.getAllocBytes(),pgpA.getAllocCount()))
   print("  Src: Count %i, Bytes %i" % (prbsA.getTxCount(),prbsA.getTxBytes()))
   print(" Dest: Count %i, Bytes %i, Alloc %i, Errors %i" % (prbsB.getRxCount(),prbsB.getRxBytes(),prbsB.getAllocBytes(),prbsB.getRxErrors()))
   print("Test1: Count %i, Bytes %i" % (ts1.packCnt,ts1.byteCnt))
   print("Test2: Count %i, Bytes %i, Alloc %i" % (ts2.packCnt,ts2.byteCnt,ts2.getAllocBytes()))
   print("")
   count += 1

   f = tm.reqFrame(1000000,True,0)
   q = bytearray([10,20,30,40])
   f.write(q,0)
   tm.sendFrame(f,0)

   prbsC.genFrame(100)

   time.sleep(1)

