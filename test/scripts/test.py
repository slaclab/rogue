#!/usr/bin/env python

import py_rouge
import time

class testDest(py_rouge.StreamDest):

   def __init__(self):
      py_rouge.StreamDest.__init__(self)
      self.byteCnt = 0
      self.packCnt = 0

   def pushBuffer(self,data):
      self.byteCnt += data.size
      self.packCnt += 1
      return(True)

class blahDest(py_rouge.StreamDest):

   def __init__(self):
      py_rouge.StreamDest.__init__(self)

   def pushBuffer(self,data):
      print("Got data. size=%i" % (data.size))
      print("")
      return(True)

tdest = testDest()

pgpA = py_rouge.PgpCardStream()
pgpA.open("/dev/pgpcard_0",0,0)
pgpA.setLoop(0,1)
pgpA.setName("pgpA")

psrc   = py_rouge.PrbsDataSrc(100000)
psrc.setName("prbs")

pdestA = py_rouge.PrbsDataDest()
pdestB = py_rouge.PrbsDataDest()
pdestC = py_rouge.PrbsDataDest()

psrc.addDest(pgpA)
psrc.addDest(pdestA)
psrc.setLaneVc(0,0)

pgpA.addDest(pdestB)
pgpA.addDest(pdestC)
pgpA.addDest(tdest)
psrc.enable()

pgpB = py_rouge.PgpCardStream()
pgpB.open("/dev/pgpcard_0",1,0)
pgpB.setLoop(1,1)
pgpB.setName("pgpB")

bdest = blahDest()
bsrc  = py_rouge.StreamSrc()
bsrc.setLaneVc(1,0)

bsrc.addDest(pgpB)
pgpB.addDest(bdest)
size = 100

lastCnt = 0
lastTot = 0
while (True) :
   print("  Src: Count %i, Bytes %i" % (psrc.getCount(),psrc.getBytes()))
   print("DestA: Count %i, Bytes %i, Errors %i" % (pdestA.getCount(),pdestA.getBytes(),pdestA.getErrors()))
   print("DestB: Count %i, Bytes %i, Errors %i" % (pdestB.getCount(),pdestB.getBytes(),pdestB.getErrors()))
   print("DestC: Count %i, Bytes %i, Errors %i" % (pdestC.getCount(),pdestC.getBytes(),pdestC.getErrors()))
   print("Local: Count %i, Bytes %i" % (tdest.packCnt,tdest.byteCnt))

   print("Rate: %i - BW %f Gbps" % ((pdestB.getCount() - lastCnt), (pdestB.getBytes() - lastTot)*8.0/1e9))
   print("")

   buff = bsrc.destGetBuffer(100)
   if ( buff ):
      buff.size = size
      bsrc.destPushBuffer(buff)
      size += 4

   lastCnt = pdestB.getCount()
   lastTot = pdestB.getBytes()
   time.sleep(1)

