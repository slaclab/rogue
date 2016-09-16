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
      #p = frame.read()
      #print(p)
      return(True)

prbsA = py_rogue.Prbs()
prbsB = py_rogue.Prbs()

prbsA.setSlave(prbsB)

ts1 = testSlave()
prbsA.addSlave(ts1)

prbsA.enMessages(True)
prbsB.enMessages(True)
#prbsA.enable(1000)

tm = py_rogue.Master()
ts2 = testSlave()
tm.setSlave(ts2)

count = 0

while (True) :
   prbsA.genFrame(1000)
   f = tm.reqFrame(1000000,True)

   b = bytearray(10)
   print("data")
   print(b)
   print("end")
   f.write(b)
   tm.sendFrame(f)

   print("  Src: Count %i, Bytes %i" % (prbsA.getCount(),prbsA.getBytes()))
   print(" Dest: Count %i, Bytes %i, Errors %i" % (prbsB.getCount(),prbsB.getBytes(),prbsB.getErrors()))
   print("Test1: Count %i, Bytes %i" % (ts1.packCnt,ts1.byteCnt))
   print("Test2: Count %i, Bytes %i" % (ts2.packCnt,ts2.byteCnt))
   print("")
   count += 1

   time.sleep(1)

