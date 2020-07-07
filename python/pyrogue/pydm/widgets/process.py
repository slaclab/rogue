#-----------------------------------------------------------------------------
# Title      : PyRogue PyDM Process Widget
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
from pydm.widgets import PyDMPushButton, PyDMScaleIndicator
from pyrogue.pydm.data_plugins.rogue_plugin import nodeFromAddress
from pyrogue.pydm.widgets import PyRogueLineEdit
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox


class Process(PyDMFrame):
    def __init__(self, parent=None, init_channel=None):
        PyDMFrame.__init__(self, parent, init_channel)
        self._node = None

    def connection_changed(self, connected):
        build = (self._node is None) and (self._connected != connected and connected is True)
        super(Process, self).connection_changed(connected)

        if not build:
            return

        self._node = nodeFromAddress(self.channel)
        self._path = self.channel

        vb = QVBoxLayout()
        self.setLayout(vb)

        gb = QGroupBox('Process ({})'.format(self._node.name))
        vb.addWidget(gb)

        vb = QVBoxLayout()
        gb.setLayout(vb)

        hb = QHBoxLayout()
        vb.addLayout(hb)

        w = PyDMPushButton(label='Start',pressValue=1,init_channel=self._path + '.Start')
        hb.addWidget(w)

        w = PyDMPushButton(label='Stop',pressValue=1,init_channel=self._path + '.Stop')
        hb.addWidget(w)

        fl = QFormLayout()
        fl.setRowWrapPolicy(QFormLayout.DontWrapRows)
        fl.setFormAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        fl.setLabelAlignment(Qt.AlignRight)
        hb.addLayout(fl)

        w = PyRogueLineEdit(parent=None, init_channel=self._path + '.Running/disp')
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

        w = PyDMScaleIndicator(parent=None, init_channel=self._path + '.Progress')
        w.showUnits             = False
        w.precisionFromPV       = True
        w.alarmSensitiveContent = False
        w.alarmSensitiveBorder  = False
        w.showValue             = False
        w.showLimits            = False
        w.showTicks             = False
        w.barIndicator          = True

        fl.addRow('Progress:',w)

        w = PyRogueLineEdit(parent=None, init_channel=self._path + '.Message/disp')
        w.showUnits             = False
        w.precisionFromPV       = False
        w.alarmSensitiveContent = False
        w.alarmSensitiveBorder  = False

        fl.addRow('Message:',w)

        # Auto add additional fields
        noAdd = ['enable','Start','Stop','Running','Progress','Message']

        prc = nodeFromAddress(self.channel)

        for k,v in prc.nodes.items():
            if v.name not in noAdd and not v.hidden:
                w = PyRogueLineEdit(parent=None, init_channel=self._path + '.{}/disp'.format(v.name))
                w.showUnits             = False
                w.precisionFromPV       = True
                w.alarmSensitiveContent = False
                w.alarmSensitiveBorder  = False

                fl.addRow(v.name + ':',w)
