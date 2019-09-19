#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Title      : PyRogue PyDM Root Control Widget
#-----------------------------------------------------------------------------
# File       : pyrogue/pydm/widgets/root_control.py
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
from pydm.widgets import PyDMLineEdit, PyDMPushButton
from pydm import utilities
from qtpy.QtCore import Qt, Property, Slot
from qtpy.QtWidgets import QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog, QGroupBox
import datetime

class RootControl(PyDMFrame):
    def __init__(self, parent=None, init_channel=None):
        PyDMFrame.__init__(self, parent, init_channel)
        self._en = False

        if init_channel is not None:
            self._en = True
            self._build()

    def _build(self):
        if (not self._en) or (not utilities.is_pydm_app()) or self.channel is None:
            return

        vb = QVBoxLayout()
        self.setLayout(vb)

        gb = QGroupBox('Reset And Configuration')
        vb.addWidget(gb)

        vb = QVBoxLayout()
        gb.setLayout(vb)

        hb = QHBoxLayout()
        vb.addLayout(hb)

        w = PyDMPushButton(label='Hard Reset',pressValue=1,init_channel=self.channel + '.HardReset')
        hb.addWidget(w)

        w = PyDMPushButton(label='Initialize',pressValue=1,init_channel=self.channel + '.Initialize')
        hb.addWidget(w)

        w = PyDMPushButton(label='Count Reset',pressValue=1,init_channel=self.channel + '.CountReset')
        hb.addWidget(w)

        hb = QHBoxLayout()
        vb.addLayout(hb)

        # Hidden boxes which are updated by file browse for now
        self._loadSettingsCmd = PyDMLineEdit(parent=None, init_channel=self.channel + '.LoadConfig')
        self._saveSettingsCmd = PyDMLineEdit(parent=None, init_channel=self.channel + '.SaveConfig')
        self._saveStateCmd    = PyDMLineEdit(parent=None, init_channel=self.channel + '.SaveState')

        pb = QPushButton('Load Settings')
        pb.clicked.connect(self._loadSettings)
        hb.addWidget(pb)

        pb = QPushButton('Save Settings')
        pb.clicked.connect(self._saveSettings)
        hb.addWidget(pb)

        pb = QPushButton('Save State')
        pb.clicked.connect(self._saveState)
        hb.addWidget(pb)

    @Slot()
    def _loadSettings(self):
        dlg = QFileDialog()

        loadFile = dlg.getOpenFileNames(caption='Read config file', filter='Config Files(*.yml);;All Files(*.*)')

        # Detect QT5 return
        if isinstance(loadFile,tuple):
            loadFile = loadFile[0]

        if loadFile != '':
            self._loadSettingsCmd.setText(','.join(loadFile))
            self._loadSettingsCmd.send_value()

    @Slot()
    def _saveSettings(self):
        dlg = QFileDialog()
        sug = datetime.datetime.now().strftime("config_%Y%m%d_%H%M%S.yml") 

        saveFile = dlg.getSaveFileName(caption='Save config file', directory=sug, filter='Config Files(*.yml);;All Files(*.*)')

        # Detect QT5 return
        if isinstance(saveFile,tuple):
            saveFile = saveFile[0]

        if saveFile != '':
            self._saveSettingsCmd.setText(saveFile)
            self._saveSettingsCmd.send_value()

    @Slot()
    def _saveState(self):
        dlg = QFileDialog()
        sug = datetime.datetime.now().strftime("state_%Y%m%d_%H%M%S.yml.gz")

        stateFile = dlg.getSaveFileName(caption='Save State file', directory=sug, filter='State Files(*.yml *.yml.gz);;All Files(*.*)')

        # Detect QT5 return
        if isinstance(stateFile,tuple):
            stateFile = stateFile[0]

        if stateFile != '':
            self._saveStateCmd.setText(stateFile)
            self._saveStateCmd.send_value()

    @Property(bool)
    def rogueEnabled(self):
        return self._en

    @rogueEnabled.setter
    def rogueEnabled(self, value):
        self._en = value
        self._build()

