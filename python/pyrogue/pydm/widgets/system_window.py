#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Title      : PyRogue PyDM System Window Widget
#-----------------------------------------------------------------------------
# File       : pyrogue/pydm/widgets/system_window.py
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

from pydm.widgets.frame import PyDMFrame
import pyrogue
from pyrogue.pydm.data_plugins.rogue_plugin import parseAddress
from pyrogue.interfaces import VirtualClient
from qtpy.QtCore import Qt, Property
from qtpy.QtWidgets import QVBoxLayout
from pyrogue.pydm.widgets import RootControl
from pyrogue.pydm.widgets import DataWriter
from pyrogue.pydm.widgets import RunControl
from pyrogue.pydm.widgets import SystemLog

class SystemWindow(PyDMFrame):
    def __init__(self, parent=None, init_channel=None):
        PyDMFrame.__init__(self, parent, init_channel)

    def connection_changed(self, connected):
        super(CommandTree, self).connection_changed(connected)

        if not connected: return

        addr, port, path, disp = parseAddress(self.channel)

        client = VirtualClient(addr, port)
        base = 'rogue://{}:{}/'.format(addr,port)

        vb = QVBoxLayout()
        self.setLayout(vb)

        rc = RootControl(parent=None, init_channel=base+'root')
        vb.addWidget(rc)

        for key,val in client.root.getNodes(typ=pyrogue.DataWriter).items():
            vb.addWidget(DataWriter(parent=None, init_channel=base+val.path))

        for key,val in client.root.getNodes(typ=pyrogue.RunControl).items():
            vb.addWidget(RunControl(parent=None, init_channel=base+val.path))

        sl = SystemLog(parent=None, init_channel=base+'root.SystemLog')
        vb.addWidget(sl)

