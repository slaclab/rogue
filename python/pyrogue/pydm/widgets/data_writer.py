#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Title      : PyRogue PyDM Data Writer Widget
#-----------------------------------------------------------------------------
# File       : pyrogue/pydm/widgets/data_writer.py
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
from pydm.widgets import PyDMLineEdit, PyDMPushButton
from qtpy.QtCore import Qt, Property, Slot
from qtpy.QtWidgets import QVBoxLayout, QHBoxLayout, QPushButton
from qtpy.QtWidgets import QFormLayout, QGroupBox, QFileDialog
import datetime

class DataWriter(PyDMFrame):
    def __init__(self, parent=None, init_channel=None):
        PyDMFrame.__init__(self, parent, init_channel)

    def connection_changed(self, connected):
        build = self._connected != connected and connected == True
        super(DataWriter, self).connection_changed(connected)

        if not build: return

        name = self.channel.split('.')[-1]

        vb = QVBoxLayout()
        self.setLayout(vb)

        gb = QGroupBox('Data File Control ({}) '.format(name))
        vb.addWidget(gb)

        vb = QVBoxLayout()
        gb.setLayout(vb)

        fl = QFormLayout()
        fl.setRowWrapPolicy(QFormLayout.DontWrapRows)
        fl.setFormAlignment(Qt.AlignHCenter | Qt.AlignTop)
        fl.setLabelAlignment(Qt.AlignRight)
        vb.addLayout(fl)

        self._dataFile = PyDMLineEdit(parent=None, init_channel=self.channel + '.DataFile')
        self._dataFile.alarmSensitiveContent = False
        self._dataFile.alarmSensitiveBorder  = True
        fl.addRow('Data File:',self._dataFile)

        hb = QHBoxLayout()
        vb.addLayout(hb)

        pb = QPushButton('Browse')
        pb.clicked.connect(self._browse)
        hb.addWidget(pb)

        w = PyDMPushButton(label='Auto Name',pressValue=1,init_channel=self.channel + '.AutoName')
        hb.addWidget(w)

        w = PyDMPushButton(label='Open',pressValue=1,init_channel=self.channel + '.Open')
        hb.addWidget(w)

        w = PyDMPushButton(label='Close',pressValue=1,init_channel=self.channel + '.Close')
        hb.addWidget(w)

        hb = QHBoxLayout()
        vb.addLayout(hb)

        vbl = QVBoxLayout()
        hb.addLayout(vbl)

        fl = QFormLayout()
        fl.setRowWrapPolicy(QFormLayout.DontWrapRows)
        fl.setFormAlignment(Qt.AlignHCenter | Qt.AlignTop)
        fl.setLabelAlignment(Qt.AlignRight)
        vbl.addLayout(fl)

        w = PyDMLineEdit(parent=None, init_channel=self.channel + '.BufferSize')
        w.alarmSensitiveContent = False
        w.alarmSensitiveBorder  = True
        fl.addRow('Buffer Size:',w)

        w = PyDMLineEdit(parent=None, init_channel=self.channel + '.IsOpen/disp')
        w.alarmSensitiveContent = False
        w.alarmSensitiveBorder  = True
        fl.addRow('File Open:',w)

        w = PyDMLineEdit(parent=None, init_channel=self.channel + '.CurrentSize')
        w.alarmSensitiveContent = False
        w.alarmSensitiveBorder  = True
        fl.addRow('Current File Size:',w)

        vbr = QVBoxLayout()
        hb.addLayout(vbr)

        fl = QFormLayout()
        fl.setRowWrapPolicy(QFormLayout.DontWrapRows)
        fl.setFormAlignment(Qt.AlignHCenter | Qt.AlignTop)
        fl.setLabelAlignment(Qt.AlignRight)
        vbr.addLayout(fl)

        w = PyDMLineEdit(parent=None, init_channel=self.channel + '.MaxFileSize')
        w.alarmSensitiveContent = False
        w.alarmSensitiveBorder  = True
        fl.addRow('Max Size:',w)

        w = PyDMLineEdit(parent=None, init_channel=self.channel + '.FrameCount')
        w.alarmSensitiveContent = False
        w.alarmSensitiveBorder  = True
        fl.addRow('Frame Count:',w)

        w = PyDMLineEdit(parent=None, init_channel=self.channel + '.TotalSize')
        w.alarmSensitiveContent = False
        w.alarmSensitiveBorder  = True
        fl.addRow('Total File Size:',w)

    @Slot()
    def _browse(self):
        dlg = QFileDialog()
        sug = datetime.datetime.now().strftime("data_%Y%m%d_%H%M%S.dat") 

        dataFile = dlg.getSaveFileName(options=QFileDialog.DontConfirmOverwrite, directory=sug, caption='Select data file', filter='Data Files(*.dat);;All Files(*.*)')

        # Detect QT5 return
        if isinstance(dataFile,tuple):
            dataFile = dataFile[0]

        if dataFile != '':
            self._dataFile.setText(dataFile)
            self._dataFile.send_value()


