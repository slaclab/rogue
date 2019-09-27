#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Title      : PyRogue GUI module
#-----------------------------------------------------------------------------
# File       : pyrogue/gui/_gui.py
# Author     : Ryan Herbst, rherbst@slac.stanford.edu
# Created    : 2016-09-29
# Last update: 2016-09-29
#-----------------------------------------------------------------------------
# Description:
# Python code for pyrogue GUI
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to 
# the license terms in the LICENSE.txt file found in the top-level directory 
# of this distribution and at: 
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html. 
# No part of the rogue software platform, including this file, may be 
# copied, modified, propagated, or distributed except according to the terms 
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
try:
    from PyQt5.QtWidgets import *
    from PyQt5.QtCore    import *
    from PyQt5.QtGui     import *
except ImportError:
    from PyQt4.QtCore    import *
    from PyQt4.QtGui     import *

import pyrogue
import pyrogue.interfaces
import pyrogue.gui
import pyrogue.gui.variables
import pyrogue.gui.commands
import pyrogue.gui.system
import threading
import socket
import sys

def runGui(root,incGroups=None,excGroups=None):
    appTop = QApplication(sys.argv)
    guiTop = pyrogue.gui.GuiTop(incGroups=incGroups,excGroups=excGroups)
    guiTop.setWindowTitle("Rogue Server: {}".format(socket.gethostname()))
    guiTop.addTree(root)
    appTop.exec_()

def application(argv):
    return QApplication(argv)

class GuiTop(QWidget):

    newRoot = pyqtSignal(pyrogue.Root,list,list)
    newVirt = pyqtSignal(pyrogue.interfaces.VirtualNode,list,list)

    def __init__(self,*, parent=None, incGroups=None, excGroups=None, group=None):
        super(GuiTop,self).__init__(parent)

        print("-------------------------------------------------------------------------")
        print("The legacy GUI is now deprecated. Please use pyDM.")
        print("")
        print("   To use pydm serverPort must be set in root.start():")
        print("")
        print("      root.start(serverPort=9099)")
        print("")
        print("    when using a fixed port or for auto port assignment you can use:")
        print("")
        print("      root.start(serverPort=0)")
        print("")
        print("   To start pydm client from command line:")
        print("")
        print("      python -m pyrogue gui --server=localhost:9099")
        print("")
        print("   To start in top level python script:")
        print("")
        print("      pyrogue.pydm.runPyDM(root=root)")
        print("")
        print("   the server port will be extracted from the root object.")
        print("-------------------------------------------------------------------------")

        if incGroups is None:
            self._incGroups=[]
        elif isinstance(incGroups,list):
            self._incGroups=incGroups
        else:
            self._incGroups=[incGroups]

        if excGroups is None:
            self._excGroups=['Hidden']
        elif isinstance(excGroups,list):
            self._excGroups=excGroups
        else:
            self._excGroups=[excGroups]

        vb = QVBoxLayout()
        self.setLayout(vb)

        self.tab = QTabWidget()
        vb.addWidget(self.tab)

        self.var = pyrogue.gui.variables.VariableWidget(parent=self.tab)
        self.tab.addTab(self.var,'Variables')

        self.cmd = pyrogue.gui.commands.CommandWidget(parent=self.tab)
        self.tab.addTab(self.cmd,'Commands')
        self.show()

        self.newRoot.connect(self._addTree)
        self.newRoot.connect(self.var.addTree)
        self.newRoot.connect(self.cmd.addTree)

        self.newVirt.connect(self._addTree)
        self.newVirt.connect(self.var.addTree)
        self.newVirt.connect(self.cmd.addTree)

        self._appTop = None

    def addTree(self,root):
        if not root.running:
            raise Exception("GUI can not be attached to a tree which is not started")

        if isinstance(root,pyrogue.interfaces.VirtualNode):
            self.newVirt.emit(root,self._incGroups,self._excGroups)
        else:
            self.newRoot.emit(root,self._incGroups,self._excGroups)

    @pyqtSlot(pyrogue.Root,list,list)
    @pyqtSlot(pyrogue.interfaces.VirtualNode,list,list)
    def _addTree(self,root,incGroups,excGroups):
        self.sys = pyrogue.gui.system.SystemWidget(root=root,parent=self.tab)
        self.tab.addTab(self.sys,root.name)
        self.adjustSize()

