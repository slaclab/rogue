#!/usr/bin/env python

import pyrogue.mesh
import pyrogue.gui
import PyQt4.QtGui
import sys

# Create mesh node
node = pyrogue.mesh.MeshNode('rogue',iface='eth0')

appTop = PyQt4.QtGui.QApplication(sys.argv)
guiTop = pyrogue.gui.GuiTop('rogue')

node.setNewNodeCb(guiTop.addRoot)

appTop.exec_()
