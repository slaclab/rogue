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
from pydm.widgets import PyDMLineEdit, PyDMSpinbox, PyDMPushButton, PyDMEnumComboBox, PyDMScaleIndicator
#from pydm import widgets
from pydm import utilities
import pyrogue.interfaces
from pyrogue.pydm.data_plugins.rogue_plugin import parseAddress
from qtpy.QtCore import Qt, Property, QObject, Q_ENUMS, Slot, QPoint
from qtpy.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy, QMenu, QDialog, QPushButton
from qtpy.QtWidgets import QWidget, QGridLayout, QTreeWidgetItem, QTreeWidget, QLineEdit, QFormLayout, QGroupBox
import jsonpickle
import time

class Process(PyDMFrame):
    def __init__(self, parent=None, init_channel=None):
        PyDMFrame.__init__(self, parent, init_channel)
        self._en = False

        if init_channel is not None:
            self._en = True
            self._build()

    def _build(self):
        if (not self._en) or (not utilities.is_pydm_app()) or self.channel is None:
            return

        name = self.channel.split('.')[-1]

        vb = QVBoxLayout()
        self.setLayout(vb)

        gb = QGroupBox('Process ({})'.format(name))
        vb.addWidget(gb)

        vb = QVBoxLayout()
        gb.setLayout(vb)

        hb = QHBoxLayout()
        vb.addLayout(hb)

        w = PyDMPushButton(label='Start',pressValue=1,init_channel=self.channel + '.Start')
        hb.addWidget(w)

        w = PyDMPushButton(label='Stop',pressValue=1,init_channel=self.channel + '.Stop')
        hb.addWidget(w)

        fl = QFormLayout()
        fl.setRowWrapPolicy(QFormLayout.DontWrapRows)
        fl.setFormAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        fl.setLabelAlignment(Qt.AlignRight)
        hb.addLayout(fl)

        w = PyDMLineEdit(parent=None, init_channel=self.channel + '.Running/True')
        w.showUnits             = False
        w.precisionFromPV       = False
        w.alarmSensitiveContent = False
        w.alarmSensitiveBorder  = False

        fl.addRow('Running:',w)

        fl = QFormLayout()
        fl.setRowWrapPolicy(QFormLayout.DontWrapRows)
        fl.setFormAlignment(Qt.AlignHCenter | Qt.AlignTop)
        fl.setLabelAlignment(Qt.AlignRight)
        vb.addLayout(fl)

        w = PyDMScaleIndicator(parent=None, init_channel=self.channel + '.Progress')
        w.showUnits             = False
        w.precisionFromPV       = True
        w.alarmSensitiveContent = False
        w.alarmSensitiveBorder  = False
        w.showValue             = False
        w.showLimits            = False
        w.showTicks             = False
        w.barIndicator          = True 

        fl.addRow('Progress:',w)

        w = PyDMLineEdit(parent=None, init_channel=self.channel + '.Message/True')
        w.showUnits             = False
        w.precisionFromPV       = False
        w.alarmSensitiveContent = False
        w.alarmSensitiveBorder  = False

        fl.addRow('Message:',w)

        # Auto add aditional fields
        noAdd = ['enable','Start','Stop','Running','Progress','Message']

        addr, port, path, disp = parseAddress(self.channel)
        client = pyrogue.interfaces.VirtualClient(addr, port)
        prc = client.root.getNode(path)

        for k,v in prc.nodes.items():
            if v.name not in noAdd and not v.hidden:
                w = PyDMLineEdit(parent=None, init_channel=self.channel + '.{}/True'.format(v.name))
                w.showUnits             = False
                w.precisionFromPV       = True 
                w.alarmSensitiveContent = False
                w.alarmSensitiveBorder  = False

                fl.addRow(v.name + ':',w)

    @Property(bool)
    def rogueEnabled(self):
        return self._en

    @rogueEnabled.setter
    def rogueEnabled(self, value):
        self._en = value
        self._build()

