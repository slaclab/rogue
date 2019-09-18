#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to 
# the license terms in the LICENSE.txt file found in the top-level directory 
# of this distribution and at: 
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html. 
# No part of the rogue software platform, including this file, may be 
# copied, modified, propagated, or distributed except according to the terms 
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

#from os import path
from pydm.widgets.frame import PyDMFrame
from pydm.widgets import PyDMLineEdit, PyDMSpinbox, PyDMPushButton, PyDMEnumComboBox
#from pydm import widgets
from pydm import utilities
from pyrogue.pydm.data_plugins.rogue_plugin import ServerTable
import pyrogue.interfaces
from qtpy.QtCore import Qt, Property, QObject, Q_ENUMS, Slot, QPoint
from qtpy.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy, QMenu, QDialog, QPushButton
from qtpy.QtWidgets import QWidget, QGridLayout, QTreeWidgetItem, QTreeWidget, QLineEdit, QFormLayout, QGroupBox
from pyrogue.pydm.widgets import RootControl
from pyrogue.pydm.widgets import DataWriter
from pyrogue.pydm.widgets import RunControl
from pyrogue.pydm.widgets import SystemLog

class SystemWindow(PyDMFrame):
    def __init__(self, parent=None, init_channel=None):
        PyDMFrame.__init__(self, parent, init_channel)
        self._en = False

        if init_channel is not None:
            self._en = True
            self._build()

    def _build(self):
        if (not self._en) or (not utilities.is_pydm_app()) or self.channel is None:
            return

        addr, port, path, disp = ServerTable.parse(self.channel)

        client = pyrogue.interfaces.VirtualClient(addr, port)
        base = 'rogue://{}:{}/'.format(addr,port)

        vb = QVBoxLayout()
        self.setLayout(vb)

        rc = RootControl(parent=None, init_channel=self.channel)
        vb.addWidget(rc)

        for key,val in client.root.getNodes(typ=pyrogue.DataWriter).items():
            vb.addWidget(DataWriter(parent=None, init_channel=base+val.path))

        for key,val in client.root.getNodes(typ=pyrogue.RunControl).items():
            vb.addWidget(RunControl(parent=None, init_channel=base+val.path))

        sl = SystemLog(parent=None, init_channel=base+'root.SystemLog')
        vb.addWidget(sl)

    @Property(bool)
    def rogueEnabled(self):
        return self._en

    @rogueEnabled.setter
    def rogueEnabled(self, value):
        self._en = value
        self._build()

