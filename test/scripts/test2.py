#!/usr/bin/env python

import py_rogue
import time

class testSlave(py_rogue.Slave):

   def __init__(self):
      py_rogue.Slave.__init__(self)
      self.byteCnt = 0
      self.packCnt = 0

   def acceptFrame(self,frame):
      self.byteCnt += frame.getPayload()
      self.packCnt += 1
      #p = bytearray(frame.read())
      #if ( len(p) < 20 ):
         #print("Got size=%i Data: %s" % (len(p),"".join("%02x:" % b for b in p)))
      return(True)

prbsA = py_rogue.Prbs()
prbsB = py_rogue.Prbs()

prbsA.setSlave(prbsB)

ts1 = testSlave()
prbsA.addSlave(ts1)

#prbsA.enMessages(True)
#prbsB.enMessages(True)
prbsA.enable(1000)

tm = py_rogue.Master()
ts2 = testSlave()
tm.setSlave(ts2)

count = 0

while (True) :
   
   print("")
   print("  Src: Count %i, Bytes %i" % (prbsA.getCount(),prbsA.getBytes()))
   print(" Dest: Count %i, Bytes %i, Alloc %i, Errors %i" % (prbsB.getCount(),prbsB.getBytes(),prbsB.getAlloc(),prbsB.getErrors()))
   print("Test1: Count %i, Bytes %i" % (ts1.packCnt,ts1.byteCnt))
   print("Test2: Count %i, Bytes %i, Alloc %i" % (ts2.packCnt,ts2.getAlloc(),ts2.byteCnt))
   print("")
   count += 1

   f = tm.reqFrame(1000000,True)
   q = bytearray([10,20,30,40])
   f.write(q)
   tm.sendFrame(f)

   time.sleep(1)

