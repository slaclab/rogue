#-----------------------------------------------------------------------------
# Title      : PyRogue PyDM Root Control Widget
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
from pydm.widgets import PyDMPushButton
from pyrogue.pydm.data_plugins.rogue_plugin import nodeFromAddress
from qtpy.QtCore import Slot
from qtpy.QtWidgets import QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog, QGroupBox, QLineEdit
import datetime


class RootControl(PyDMFrame):
    def __init__(self, parent=None, init_channel=None):
        PyDMFrame.__init__(self, parent, init_channel)
        self._node = None

    def connection_changed(self, connected):
        build = (self._node is None) and (self._connected != connected and connected is True)
        super(RootControl, self).connection_changed(connected)

        if not build:
            return

        self._node = nodeFromAddress(self.channel)
        self._path = self.channel

        vb = QVBoxLayout()
        self.setLayout(vb)

        gb = QGroupBox('Reset And Configuration')
        vb.addWidget(gb)

        vb = QVBoxLayout()
        gb.setLayout(vb)

        hb = QHBoxLayout()
        vb.addLayout(hb)

        w = PyDMPushButton(label='Hard Reset',pressValue=1,init_channel=self._path + '.HardReset')
        hb.addWidget(w)

        w = PyDMPushButton(label='Initialize',pressValue=1,init_channel=self._path + '.Initialize')
        hb.addWidget(w)

        w = PyDMPushButton(label='Count Reset',pressValue=1,init_channel=self._path + '.CountReset')
        hb.addWidget(w)

        # Load Config
        # This needs to be changed to the new pydm command interface with the push
        # button committing the line edit value
        hb = QHBoxLayout()
        vb.addLayout(hb)

        self._loadConfigCmd = PyDMPushButton(label='Load Config',
                                             pressValue='',
                                             init_channel=self._path + '.LoadConfig')

        hb.addWidget(self._loadConfigCmd)

        self._loadConfigValue = QLineEdit()
        self._loadConfigValue.textChanged.connect(self._loadConfigChanged)
        hb.addWidget(self._loadConfigValue)

        pb = QPushButton('Browse')
        pb.clicked.connect(self._loadConfigBrowse)
        hb.addWidget(pb)

        # Save Config
        # This needs to be changed to the new pydm command interface with the push
        # button committing the line edit value
        hb = QHBoxLayout()
        vb.addLayout(hb)

        self._saveConfigCmd = PyDMPushButton(label='Save Config',
                                             pressValue='',
                                             init_channel=self._path + '.SaveConfig')

        hb.addWidget(self._saveConfigCmd)

        self._saveConfigValue = QLineEdit()
        self._saveConfigValue.textChanged.connect(self._saveConfigChanged)
        hb.addWidget(self._saveConfigValue)

        pb = QPushButton('Browse')
        pb.clicked.connect(self._saveConfigBrowse)
        hb.addWidget(pb)

        # Save State
        # This needs to be changed to the new pydm command interface with the push
        # button committing the line edit value
        hb = QHBoxLayout()
        vb.addLayout(hb)

        self._saveStateCmd = PyDMPushButton(label='Save State ',
                                            pressValue='',
                                            init_channel=self._path + '.SaveState')

        hb.addWidget(self._saveStateCmd)

        self._saveStateValue = QLineEdit()
        self._saveStateValue.textChanged.connect(self._saveStateChanged)
        hb.addWidget(self._saveStateValue)

        pb = QPushButton('Browse')
        pb.clicked.connect(self._saveStateBrowse)
        hb.addWidget(pb)

        # Dump Remote Variables
        # This needs to be changed to the new pydm command interface with the push
        # button committing the line edit value
        hb = QHBoxLayout()
        vb.addLayout(hb)

        self._dumpCfgVarsCmd = PyDMPushButton(label='DumpCfgVars',
                                            pressValue='',
                                            init_channel=self._path + '.DumpCfgVars')

        hb.addWidget(self._dumpCfgVarsCmd)

        self._dumpCfgVarsValue = QLineEdit()
        self._dumpCfgVarsValue.textChanged.connect(self._dumpCfgVarsChanged)
        hb.addWidget(self._dumpCfgVarsValue)

        pb = QPushButton('Browse')
        pb.clicked.connect(self._dumpCfgVarsBrowse)
        hb.addWidget(pb)

    @Slot(str)
    def _loadConfigChanged(self,value):
        self._loadConfigCmd.pressValue = value

    @Slot()
    def _loadConfigBrowse(self):
        dlg = QFileDialog()

        loadFile = dlg.getOpenFileNames(caption='Read config file', filter='Config Files(*.yml);;All Files(*.*)')

        # Detect QT5 return
        if isinstance(loadFile,tuple):
            loadFile = loadFile[0]

        if loadFile != '':
            self._loadConfigValue.setText(','.join(loadFile))

    @Slot(str)
    def _saveConfigChanged(self,value):
        self._saveConfigCmd.pressValue = value

    @Slot()
    def _saveConfigBrowse(self):
        dlg = QFileDialog()
        sug = datetime.datetime.now().strftime("config_%Y%m%d_%H%M%S.yml")

        saveFile = dlg.getSaveFileName(caption='Save config file', directory=sug, filter='Config Files(*.yml);;All Files(*.*)')

        # Detect QT5 return
        if isinstance(saveFile,tuple):
            saveFile = saveFile[0]

        if saveFile != '':
            self._saveConfigValue.setText(saveFile)

    @Slot(str)
    def _saveStateChanged(self,value):
        self._saveStateCmd.pressValue = value

    @Slot()
    def _saveStateBrowse(self):
        dlg = QFileDialog()
        sug = datetime.datetime.now().strftime("state_%Y%m%d_%H%M%S.yml.zip")

        stateFile = dlg.getSaveFileName(caption='Save State file', directory=sug, filter='State Files(*.yml *.yml.zip);;All Files(*.*)')

        # Detect QT5 return
        if isinstance(stateFile,tuple):
            stateFile = stateFile[0]

        if stateFile != '':
            self._saveStateValue.setText(stateFile)

    @Slot(str)
    def _dumpCfgVarsChanged(self,value):
        self._dumpCfgVarsCmd.pressValue = value

    @Slot()
    def _dumpCfgVarsBrowse(self):
        dlg = QFileDialog()
        sug = datetime.datetime.now().strftime("cfgdump_%Y%m%d_%H%M%S.txt")

        stateFile = dlg.getSaveFileName(caption='DumpCfgVars file', directory=sug, filter='Dump Files(*.yml);;All Files(*.*)')

        # Detect QT5 return
        if isinstance(stateFile,tuple):
            stateFile = stateFile[0]

        if stateFile != '':
            self._dumpCfgVarsValue.setText(stateFile)
