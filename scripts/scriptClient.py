#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Title      : Script Client
#-----------------------------------------------------------------------------
# File       : guiClient.py
# Author     : Ryan Herbst, rherbst@slac.stanford.edu
# Created    : 2016-09-29
# Last update: 2016-09-29
#-----------------------------------------------------------------------------
# Description:
# Generic Script client for rogue
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to 
# the license terms in the LICENSE.txt file found in the top-level directory 
# of this distribution and at: 
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html. 
# No part of the rogue software platform, including this file, may be 
# copied, modified, propagated, or distributed except according to the terms 
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
import pyrogue.mesh
import pyrogue.gui
import PyQt4.QtGui
import sys

group = 'rogueTest'
iface = 'eth3'

# Create mesh node
node = pyrogue.mesh.MeshNode(group,iface=iface)

# Start mesh
node.start()

# Wait for our node
print("Waiting for evalBoard")
evalBoard = node.waitTree('evalBoard')
print("Got evalBoard. Type stop() to exit.")

def stop():
    node.stop()
    exit()

