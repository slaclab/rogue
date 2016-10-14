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
import pyrogue.devices.axi_version
import pyrogue.devices.axi_prbstx
import pyrogue.utilities.prbs
import pyrogue.utilities.fileio
import pyrogue.gui
import pyrogue.mesh
import pyrogue.epics
import threading
import signal
import atexit
import yaml
import time
import sys
import PyQt4.QtGui

# Set base
evalBoard = pyrogue.Root('evalBoard','Evaluation Board')
srp = rogue.protocols.srp.SrpV0()
dataWriter = pyrogue.utilities.fileio.StreamWriter('dataWriter')
evalBoard.add(dataWriter)
prbsRx = pyrogue.utilities.prbs.PrbsRx('prbsRx')
evalBoard.add(prbsRx)

evalBoard.add(pyrogue.devices.axi_version.create(name='axiVersion',memBase=srp,offset=0x0))
evalBoard.add(pyrogue.devices.axi_prbstx.create(name='axiPrbsTx',memBase=srp,offset=0x30000))

appTop = PyQt4.QtGui.QApplication(sys.argv)
guiTop = pyrogue.gui.GuiTop('rogue')
guiTop.addRoot(evalBoard)

# Create mesh node
mNode = pyrogue.mesh.MeshNode('rogue',iface='wlan6',root=evalBoard)

# Create epics node
epics = pyrogue.epics.EpicsCaServer('rogue',evalBoard)

appTop.exec_()

# Close window and stop polling
def stop():
    guiTop.close()
    mNode.stop()
    evalBoard.stop()

