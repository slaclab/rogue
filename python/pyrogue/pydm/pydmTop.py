#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Title      : PyRogue PyDM Top Level GUI
#-----------------------------------------------------------------------------
# File       : pyrogue/pydm/pydmTop.py
# Created    : 2019-09-18
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to 
# the license terms in the LICENSE.txt file found in the top-level directory 
# of this distribution and at: 
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html. 
# No part of the rogue software platform, including this file, may be 
# copied, modified, propagated, or distributed except according to the terms 
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

import os
from qtpy import QtCore
from pydm import Display
from qtpy.QtWidgets import (QVBoxLayout, QTabWidget)

from pyrogue.pydm.widgets import VariableTree
from pyrogue.pydm.widgets import CommandTree
from pyrogue.pydm.widgets import SystemWindow

Channel = 'rogue://0/root'

class DefaultTop(Display):
    def __init__(self, parent=None, args=[], macros=None):
        super(DefaultTop, self).__init__(parent=parent, args=args, macros=None)

        self.setWindowTitle("Rogue Server: {}".format(os.getenv('ROGUE_SERVERS')))

        vb = QVBoxLayout()
        self.setLayout(vb)

        self.tab = QTabWidget()
        vb.addWidget(self.tab)

        var = VariableTree(parent=None, init_channel=Channel)
        self.tab.addTab(var,'Variables')

        cmd = CommandTree(parent=None, init_channel=Channel)
        self.tab.addTab(cmd,'Commands')

        sys = SystemWindow(parent=None, init_channel=Channel)
        self.tab.addTab(sys,'System')

    def minimumSizeHint(self):
        # This is the default recommended size
        # for this screen
        return QtCore.QSize(700, 900)

    def ui_filepath(self):
        # No UI file is being used
        return None

