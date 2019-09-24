#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Title      : PyRogue PyDM Command Widget
#-----------------------------------------------------------------------------
# File       : pyrogue/pydm/widgets/command.py
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

import pyrogue
from pydm.widgets.frame import PyDMFrame
from pydm.widgets import PyDMSpinbox, PyDMPushButton
from pyrogue.pydm.data_plugins.rogue_plugin import nodeFromAddress
from qtpy.QtCore import Qt, Property, Slot, Signal
from qtpy.QtWidgets import QHBoxLayout, QLineEdit, QPushButton, QComboBox, QSizePolicy
import jsonpickle
import time

class Command(PyDMFrame):
    send_value_signal = Signal([str])

    def __init__(self, parent=None, init_channel=None):
        PyDMFrame.__init__(self, parent, init_channel)

    def connection_changed(self, connected):
        build = self._connected != connected and connected == True
        super(Command, self).connection_changed(connected)

        if not build: return

        self._node   = nodeFromAddress(self.channel)
        self._path   = self.channel
        self._value  = ''
        self._widget = None

        hb = QHBoxLayout()
        self.setLayout(hb)

        if self._node.arg:

            if self._node.disp == 'enum' and self._node.enum is not None:
                self._widget = QComboBox()
                for i in self._node.enum:
                    self._widget.addItem(self._node.enum[i])

                self._value = self._node.valueDisp()
                self._widget.setCurrentIndex(self._widget.findText(self._value))
                self._widget.setToolTip(self._node.description)

                self._widget.currentTextChanged.connect(self._argChanged)

            else:
                self._widget = QLineEdit()

                self._value = self._node.valueDisp()
                self._widget.setText(self._value)
                self._widget.setToolTip(self._node.description)

                self._widget.textChanged.connect(self._argChanged)

            hb.addWidget(self._widget)

        self._btn = PyDMPushButton(label='Exec',
                                   pressValue=self._value,
                                   init_channel=self._path + '/disp')
        self._btn.setToolTip(self._node.description)

        hb.addWidget(self._btn)

    @Slot(str)
    def _argChanged(self,value):
        self._btn.pressValue = value

    def value_changed(self, new_val):
        pass


