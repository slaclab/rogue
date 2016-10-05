#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Title      : PyRogue GUI module
#-----------------------------------------------------------------------------
# File       : pyrogue/gui/__init__.py
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
from PyQt4.QtCore   import *
from PyQt4.QtGui    import *
from PyQt4.QtWebKit import *

import pyrogue
import pyrogue.gui
import pyrogue.gui.variables
import pyrogue.gui.commands
import pyrogue.gui.system
import threading
import sys


class GuiTop(QWidget):

    def __init__(self,root,parent=None):
        super(GuiTop,self).__init__(parent)

        vb = QVBoxLayout()
        self.setLayout(vb)

        tab = QTabWidget()
        vb.addWidget(tab)

        vw = pyrogue.gui.system.SystemWidget(root,tab)
        tab.addTab(vw,'System')

        vw = pyrogue.gui.variables.VariableWidget(root,tab)
        tab.addTab(vw,'Variables')

        vw = pyrogue.gui.commands.CommandWidget(root,tab)
        tab.addTab(vw,'Commands')
        self.show()


