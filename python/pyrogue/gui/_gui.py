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
import pyrogue.gui
import pyrogue.gui.variables
import pyrogue.gui.commands
import pyrogue.gui.system
import threading
import sys


def application(argv):
    return QApplication(argv)

class GuiTop(QWidget):

    newRoot = pyqtSignal(pyrogue.Root)
    newPyro = pyqtSignal(pyrogue.PyroRoot)

    def __init__(self,*, group,parent=None):
        super(GuiTop,self).__init__(parent)

        vb = QVBoxLayout()
        self.setLayout(vb)

        self.tab = QTabWidget()
        vb.addWidget(self.tab)

        self.var = pyrogue.gui.variables.VariableWidget(group=group,parent=self.tab)
        self.tab.addTab(self.var,'Variables')

        self.cmd = pyrogue.gui.commands.CommandWidget(group=group,parent=self.tab)
        self.tab.addTab(self.cmd,'Commands')
        self.show()

        self.newRoot.connect(self._addTree)
        self.newRoot.connect(self.var.addTree)
        self.newRoot.connect(self.cmd.addTree)

        self.newPyro.connect(self._addTree)
        self.newPyro.connect(self.var.addTree)
        self.newPyro.connect(self.cmd.addTree)

        self._appTop = None

    def addTree(self,root):
        if not root.running:
            raise Exception("GUI can not be attached to a tree which is not started")

        if isinstance(root,pyrogue.PyroRoot):
            self.newPyro.emit(root)
        else:
            self.newRoot.emit(root)

    @pyqtSlot(pyrogue.Root)
    @pyqtSlot(pyrogue.PyroRoot)
    def _addTree(self,root):
        self.sys = pyrogue.gui.system.SystemWidget(root=root,parent=self.tab)
        self.tab.addTab(self.sys,root.name)
        self.adjustSize()

