#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Title      : PyRogue PyDM Run Control Widget
#-----------------------------------------------------------------------------
# File       : pyrogue/pydm/widgets/run_control.py
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
from pydm.widgets import PyDMLineEdit, PyDMEnumComboBox
from pydm import utilities
from qtpy.QtCore import Qt, Property
from qtpy.QtWidgets import QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox

class RunControl(PyDMFrame):
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

        gb = QGroupBox('Run Control ({})'.format(name))
        vb.addWidget(gb)

        vb = QVBoxLayout()
        gb.setLayout(vb)

        fl = QFormLayout()
        fl.setRowWrapPolicy(QFormLayout.DontWrapRows)
        fl.setFormAlignment(Qt.AlignHCenter | Qt.AlignTop)
        fl.setLabelAlignment(Qt.AlignRight)
        vb.addLayout(fl)

        w = PyDMEnumComboBox(parent=None, init_channel=self.channel + '.runRate')
        w.alarmSensitiveContent = False
        w.alarmSensitiveBorder  = False
        fl.addRow('Run Rate:',w)

        hb = QHBoxLayout()
        vb.addLayout(hb)

        fl = QFormLayout()
        fl.setRowWrapPolicy(QFormLayout.DontWrapRows)
        fl.setFormAlignment(Qt.AlignHCenter | Qt.AlignTop)
        fl.setLabelAlignment(Qt.AlignRight)
        hb.addLayout(fl)

        w = PyDMEnumComboBox(parent=None, init_channel=self.channel + '.runState')
        w.alarmSensitiveContent = False
        w.alarmSensitiveBorder  = False
        fl.addRow('Run State:',w)

        fl = QFormLayout()
        fl.setRowWrapPolicy(QFormLayout.DontWrapRows)
        fl.setFormAlignment(Qt.AlignHCenter | Qt.AlignTop)
        fl.setLabelAlignment(Qt.AlignRight)
        hb.addLayout(fl)

        w = PyDMLineEdit(parent=None, init_channel=self.channel + '.runCount')
        w.showUnits             = False
        w.precisionFromPV       = True
        w.alarmSensitiveContent = False
        w.alarmSensitiveBorder  = False

        fl.addRow('Run Count:',w)

    @Property(bool)
    def rogueEnabled(self):
        return self._en

    @rogueEnabled.setter
    def rogueEnabled(self, value):
        self._en = value
        self._build()

