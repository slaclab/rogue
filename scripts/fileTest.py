#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Title      : File read and write test
#-----------------------------------------------------------------------------
# File       : exoTest.py
# Author     : Ryan Herbst, rherbst@slac.stanford.edu
# Created    : 2016-09-29
# Last update: 2016-09-29
#-----------------------------------------------------------------------------
# Description:
# File read and write test
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
import rogue.utilities 
import rogue.interfaces.stream
import pyrogue
import time

fwr = rogue.utilities.fileio.StreamWriter()
fwr.setBufferSize(100004)
fwr.setMaxSize(1000003)

prbsA = rogue.utilities.Prbs()
pyrogue.streamConnect(prbsA,fwr.getChannel(0x5))

fwr.open("test.dat")

prbsA.enable(1000)
time.sleep(5)
prbsA.disable()
time.sleep(1)
fwr.close()

print("Generated: Count %i, Bytes %i" % (prbsA.getTxCount(),prbsA.getTxBytes()))
print("     File: Count %i, Bytes %i" % (fwr.getBankCount(),fwr.getSize()))

frd = rogue.utilities.fileio.StreamReader()

prbsB = rogue.utilities.Prbs()
pyrogue.streamConnect(frd,prbsB)

frd.open("test.dat.1")
#frd.open("test.dat")

while (True):

   print("")
   print(" Dest: Count %i, Bytes %i, Alloc %i, Errors %i" % (prbsB.getRxCount(),prbsB.getRxBytes(),prbsB.getAllocBytes(),prbsB.getRxErrors()))
   time.sleep(1)

