#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Title      : Eval board instance
#-----------------------------------------------------------------------------
# File       : evalBoard.py
# Author     : Ryan Herbst, rherbst@slac.stanford.edu
# Created    : 2016-09-29
# Last update: 2016-09-29
#-----------------------------------------------------------------------------
# Description:
# Rogue interface to eval board
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
import pyrogue.devices.axi_version
import pyrogue.devices.axi_prbstx
import pyrogue.utilities.prbs
import pyrogue.utilities.fileio
import pyrogue.mesh
import pyrogue.epics
import threading
import signal
import atexit
import yaml
import time
import sys

# Set base
evalBoard = pyrogue.Root('testBoard','Evaluation Board')

# File writer
dataWriter = pyrogue.utilities.fileio.StreamWriter('dataWriter')
evalBoard.add(dataWriter)

srp = rogue.protocols.srp.SrpV0()

# Add configuration stream to file as channel 0
pyrogue.streamConnect(evalBoard,dataWriter.getChannel(0x0))

# Add Devices
evalBoard.add(pyrogue.devices.axi_version.create(name='axiVersion',memBase=srp,offset=0x0))
evalBoard.add(pyrogue.devices.axi_prbstx.create(name='axiPrbsTx',memBase=srp,offset=0x30000))

# Create mesh node
mNode = pyrogue.mesh.MeshNode('rogueTest',root=evalBoard)
mNode.start()

# Create epics node
epics = pyrogue.epics.EpicsCaServer('rogueTest',evalBoard)
epics.start()

# Close window and stop polling
def stop():
    mNode.stop()
    epics.stop()
    evalBoard.stop()
    exit()

# Start with ipython -i scripts/evalBoard.py
print("Started rogue mesh and epics V3 server. To exit type stop()")

