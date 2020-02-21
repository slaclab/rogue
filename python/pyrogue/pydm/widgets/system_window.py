#-----------------------------------------------------------------------------
# Title      : PyRogue PyDM System Window Widget
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
from pyrogue.pydm.data_plugins.rogue_plugin import nodeFromAddress
from qtpy.QtWidgets import QVBoxLayout
from pyrogue.pydm.widgets import RootControl
from pyrogue.pydm.widgets import DataWriter
from pyrogue.pydm.widgets import RunControl
from pyrogue.pydm.widgets import SystemLog


class SystemWindow(PyDMFrame):
    def __init__(self, parent=None, init_channel=None):
        PyDMFrame.__init__(self, parent, init_channel)
        self._node = None

    def connection_changed(self, connected):
        build = (self._node is None) and (self._connected != connected and connected is True)
        super(SystemWindow, self).connection_changed(connected)

        if not build:
            return

        self._node = nodeFromAddress(self.channel)
        self._path = self.channel

        vb = QVBoxLayout()
        self.setLayout(vb)

        rc = RootControl(parent=None, init_channel=self._path)
        vb.addWidget(rc)

        for key,val in self._node.getNodes(typ=pyrogue.DataWriter).items():
            vb.addWidget(DataWriter(parent=None, init_channel=self._path + '.' + val.name))

        for key,val in self._node.getNodes(typ=pyrogue.RunControl).items():
            vb.addWidget(RunControl(parent=None, init_channel=self._path + '.' + val.name))

        sl = SystemLog(parent=None, init_channel=self._path + '.SystemLog')
        vb.addWidget(sl)
