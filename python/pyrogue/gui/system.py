#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Title      : System display for rogue GUI
#-----------------------------------------------------------------------------
# File       : pyrogue/gui/variables.py
# Author     : Ryan Herbst, rherbst@slac.stanford.edu
# Created    : 2016-10-03
# Last update: 2016-10-03
#-----------------------------------------------------------------------------
# Description:
# Module for functions and classes related to variable display in the rogue GUI
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to 
# the license terms in the LICENSE.txt file found in the top-level directory 
# of this distribution and at: 
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html. 
# No part of the rogue software platform, including this file, may be 
# copied, modified, propagated, or distributed except according to the terms 
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
try:
    from PyQt5.QtWidgets import *
    from PyQt5.QtCore    import *
    from PyQt5.QtGui     import *
except ImportError:
    from PyQt4.QtCore    import *
    from PyQt4.QtGui     import *

import pyrogue
import datetime

class DataLink(QObject):

    updateDataFile   = pyqtSignal(str)
    updateOpenState  = pyqtSignal(int)
    updateBufferSize = pyqtSignal(str)
    updateMaxSize    = pyqtSignal(str)
    updateFileSize   = pyqtSignal(str)
    updateFrameCount = pyqtSignal(str)

    def __init__(self,*,layout,writer):
        QObject.__init__(self)
        self.writer = writer
        self.block = False

        gb = QGroupBox('Data File Control (%s)' % (writer.name))
        layout.addWidget(gb)

        vb = QVBoxLayout()
        gb.setLayout(vb)

        fl = QFormLayout()
        fl.setRowWrapPolicy(QFormLayout.DontWrapRows)
        fl.setFormAlignment(Qt.AlignHCenter | Qt.AlignTop)
        fl.setLabelAlignment(Qt.AlignRight)
        vb.addLayout(fl)

        self.writer.dataFile.addListener(self.varListener)
        self.dataFile = QLineEdit()
        self.dataFile.setText(self.writer.dataFile.valueDisp())
        self.dataFile.textEdited.connect(self.dataFileEdited)
        self.dataFile.returnPressed.connect(self.dataFileChanged)

        self.updateDataFile.connect(self.dataFile.setText)

        fl.addRow('Data File:',self.dataFile)

        hb = QHBoxLayout()
        vb.addLayout(hb)

        fl = QFormLayout()
        fl.setRowWrapPolicy(QFormLayout.DontWrapRows)
        fl.setFormAlignment(Qt.AlignHCenter | Qt.AlignTop)
        fl.setLabelAlignment(Qt.AlignRight)
        hb.addLayout(fl)

        self.writer.open.addListener(self.varListener)
        self.openState = QComboBox()
        self.openState.addItem('False')
        self.openState.addItem('True')
        self.openState.setCurrentIndex(0)
        self.openState.activated.connect(self.openStateChanged)

        self.updateOpenState.connect(self.openState.setCurrentIndex)

        fl.addRow('File Open:',self.openState)

        self.writer.bufferSize.addListener(self.varListener)
        self.bufferSize = QLineEdit()
        self.bufferSize.setText(self.writer.bufferSize.valueDisp())
        self.bufferSize.textEdited.connect(self.bufferSizeEdited)
        self.bufferSize.returnPressed.connect(self.bufferSizeChanged)

        self.updateBufferSize.connect(self.bufferSize.setText)

        fl.addRow('Buffer Size:',self.bufferSize)

        self.writer.fileSize.addListener(self.varListener)
        self.totSize = QLineEdit()
        self.totSize.setText(self.writer.fileSize.valueDisp())
        self.totSize.setReadOnly(True)

        self.updateFileSize.connect(self.totSize.setText)

        fl.addRow('Total File Size:',self.totSize)

        fl = QFormLayout()
        fl.setRowWrapPolicy(QFormLayout.DontWrapRows)
        fl.setFormAlignment(Qt.AlignHCenter | Qt.AlignTop)
        fl.setLabelAlignment(Qt.AlignRight)
        hb.addLayout(fl)

        pb1 = QPushButton('Browse')
        pb1.clicked.connect(self._browse)

        pb2 = QPushButton('Auto Name')
        pb2.clicked.connect(self._genName)
        fl.addRow(pb1,pb2)

        self.writer.maxFileSize.addListener(self.varListener)
        self.maxSize = QLineEdit()
        self.maxSize.setText(self.writer.maxFileSize.valueDisp())
        self.maxSize.textEdited.connect(self.maxSizeEdited)
        self.maxSize.returnPressed.connect(self.maxSizeChanged)

        self.updateMaxSize.connect(self.maxSize.setText)

        fl.addRow('Max Size:',self.maxSize)

        self.writer.frameCount.addListener(self.varListener)
        self.frameCount = QLineEdit()
        self.frameCount.setText(self.writer.frameCount.valueDisp())
        self.frameCount.setReadOnly(True)

        self.updateFrameCount.connect(self.frameCount.setText)

        fl.addRow('Frame Count:',self.frameCount)

    def _browse(self):
        dlg = QFileDialog()
        sug = datetime.datetime.now().strftime("data_%Y%m%d_%H%M%S.dat") 

        dataFile = dlg.getSaveFileName(options=QFileDialog.DontConfirmOverwrite, directory=sug, caption='Select data file', filter='Data Files(*.dat);;All Files(*.*)')

        # Detect QT5 return
        if isinstance(dataFile,tuple):
            dataFile = dataFile[0]

        if dataFile != '':
            self.writer.dataFile.setDisp(dataFile)
    
    def _genName(self):
        self.writer.autoName()
        pass

    def varListener(self,path,value):
        if self.block: return

        name = path.split('.')[-1]

        if name == 'dataFile':
            self.updateDataFile.emit(value.valueDisp)

        elif name == 'open':
            self.updateOpenState.emit(self.openState.findText(value.valueDisp))

        elif name == 'bufferSize':
            self.updateBufferSize.emit(value.valueDisp)

        elif name == 'maxFileSize':
            self.updateMaxSize.emit(value.valueDisp)

        elif name == 'fileSize':
            self.updateFileSize.emit(value.valueDisp)

        elif name == 'frameCount':
            self.updateFrameCount.emit(value.valueDisp)

    @pyqtSlot()
    def dataFileEdited(self):
        p = QPalette()
        p.setColor(QPalette.Base,Qt.yellow)
        p.setColor(QPalette.Text,Qt.black)
        self.dataFile.setPalette(p)

    @pyqtSlot()
    def dataFileChanged(self):
        p = QPalette()
        self.dataFile.setPalette(p)

        self.block = True
        self.writer.dataFile.setDisp(self.dataFile.text())
        self.block = False

    @pyqtSlot(int)
    def openStateChanged(self,value):
        self.block = True
        self.writer.open.setDisp(self.openState.itemText(value))
        self.block = False

    @pyqtSlot()
    def bufferSizeEdited(self):
        p = QPalette()
        p.setColor(QPalette.Base,Qt.yellow)
        p.setColor(QPalette.Text,Qt.black)
        self.bufferSize.setPalette(p)

    @pyqtSlot()
    def bufferSizeChanged(self):
        p = QPalette()
        self.bufferSize.setPalette(p)

        self.block = True
        self.writer.bufferSize.setDisp(self.bufferSize.text())
        self.block = False

    @pyqtSlot()
    def maxSizeEdited(self):
        p = QPalette()
        p.setColor(QPalette.Base,Qt.yellow)
        p.setColor(QPalette.Text,Qt.black)
        self.maxSize.setPalette(p)

    @pyqtSlot()
    def maxSizeChanged(self):
        p = QPalette()
        self.maxSize.setPalette(p)

        self.block = True
        self.writer.maxFileSize.setDisp(self.maxSize.text())
        self.block = False


class ControlLink(QObject):

    updateState = pyqtSignal(int)
    updateRate  = pyqtSignal(int)
    updateCount = pyqtSignal(str)

    def __init__(self,*,layout,control):
        QObject.__init__(self)
        self.control = control
        self.block = False

        gb = QGroupBox('Run Control (%s)' % (control.name))
        layout.addWidget(gb)

        vb = QVBoxLayout()
        gb.setLayout(vb)

        fl = QFormLayout()
        fl.setRowWrapPolicy(QFormLayout.DontWrapRows)
        fl.setFormAlignment(Qt.AlignHCenter | Qt.AlignTop)
        fl.setLabelAlignment(Qt.AlignRight)
        vb.addLayout(fl)

        self.control.runRate.addListener(self.varListener)
        self.runRate = QComboBox()
        self.runRate.activated.connect(self.runRateChanged)
        self.updateRate.connect(self.runRate.setCurrentIndex)
        for key in sorted(self.control.runRate.enum):
            self.runRate.addItem(self.control.runRate.enum[key])
        self.runRate.setCurrentIndex(self.runRate.findText(self.control.runRate.valueDisp()))

        fl.addRow('Run Rate:',self.runRate)

        hb = QHBoxLayout()
        vb.addLayout(hb)

        fl = QFormLayout()
        fl.setRowWrapPolicy(QFormLayout.DontWrapRows)
        fl.setFormAlignment(Qt.AlignHCenter | Qt.AlignTop)
        fl.setLabelAlignment(Qt.AlignRight)
        hb.addLayout(fl)

        self.control.runState.addListener(self.varListener)
        self.runState = QComboBox()
        self.runState.activated.connect(self.runStateChanged)
        self.updateState.connect(self.runState.setCurrentIndex)
        for key in sorted(self.control.runState.enum):
            self.runState.addItem(self.control.runState.enum[key])
        self.runState.setCurrentIndex(self.runState.findText(self.control.runState.valueDisp()))

        fl.addRow('Run State:',self.runState)

        fl = QFormLayout()
        fl.setRowWrapPolicy(QFormLayout.DontWrapRows)
        fl.setFormAlignment(Qt.AlignHCenter | Qt.AlignTop)
        fl.setLabelAlignment(Qt.AlignRight)
        hb.addLayout(fl)

        self.control.runCount.addListener(self.varListener)
        self.runCount = QLineEdit()
        self.runCount.setText(self.control.runCount.valueDisp())
        self.runCount.setReadOnly(True)
        self.updateCount.connect(self.runCount.setText)

        fl.addRow('Run Count:',self.runCount)

    def varListener(self,path,value):
        if self.block: return

        name = path.split('.')[-1]

        if name == 'runState':
            self.updateState.emit(self.runState.findText(value.valueDisp))

        elif name == 'runRate':
            self.updateRate.emit(self.runRate.findText(value.valueDisp))

        elif name == 'runCount':
            self.updateCount.emit(value.valueDisp)

    @pyqtSlot(int)
    def runStateChanged(self,value):
        self.block = True
        self.control.runState.setDisp(self.runState.itemText(value))
        self.block = False

    @pyqtSlot(int)
    def runRateChanged(self,value):
        self.block = True
        self.control.runRate.setDisp(self.runRate.itemText(value))
        self.block = False


class SystemWidget(QWidget):

    updateLog = pyqtSignal(str)

    def __init__(self, *, root, parent=None):
        super(SystemWidget, self).__init__(parent)

        self.holders = []
        self.root = root

        tl = QVBoxLayout()
        self.setLayout(tl)

        ###################
        # Group Box
        ###################
        gb = QGroupBox('Reset And Configuration')
        tl.addWidget(gb)

        vb = QVBoxLayout()
        gb.setLayout(vb)

        hb = QHBoxLayout()
        vb.addLayout(hb)

        pb = QPushButton('Hard Reset')
        pb.clicked.connect(self.hardReset)
        hb.addWidget(pb)

        pb = QPushButton('Initialize')
        pb.clicked.connect(self.initialize)
        hb.addWidget(pb)

        pb = QPushButton('Count Reset')
        pb.clicked.connect(self.countReset)
        hb.addWidget(pb)

        hb = QHBoxLayout()
        vb.addLayout(hb)

        pb = QPushButton('Load Settings')
        pb.clicked.connect(self.loadSettings)
        hb.addWidget(pb)

        pb = QPushButton('Save Settings')
        pb.clicked.connect(self.saveSettings)
        hb.addWidget(pb)

        pb = QPushButton('Save State')
        pb.clicked.connect(self.saveState)
        hb.addWidget(pb)

        ###################
        # Data Controllers
        ###################
        for key,val in root.getNodes(typ=pyrogue.DataWriter,hidden=True).items():
            self.holders.append(DataLink(layout=tl,writer=val))

        ###################
        # Run Controllers
        ###################
        for key,val in root.getNodes(typ=pyrogue.RunControl,hidden=True).items():
            self.holders.append(ControlLink(layout=tl,control=val))

        ###################
        # System Log
        ###################
        gb = QGroupBox('System Log')
        tl.addWidget(gb)

        vb = QVBoxLayout()
        gb.setLayout(vb)

        self.systemLog = QTextEdit()
        self.systemLog.setReadOnly(True)
        vb.addWidget(self.systemLog)

        root.SystemLog.addListener(self.varListener)
        self.updateLog.connect(self.systemLog.setText)
        self.systemLog.setText(root.SystemLog.valueDisp())
        
        pb = QPushButton('Clear Log')
        pb.clicked.connect(self.resetLog)
        vb.addWidget(pb)

        QCoreApplication.processEvents()

    @pyqtSlot()
    def resetLog(self):
        self.root.ClearLog()

    def varListener(self,path,value):
        name = path.split('.')[-1]

        if name == 'SystemLog':
            self.updateLog.emit(value.valueDisp)

    @pyqtSlot()
    def hardReset(self):
        self.root.HardReset()

    @pyqtSlot()
    def initialize(self):
        self.root.Initialize()

    @pyqtSlot()
    def countReset(self):
        self.root.CountReset()

    @pyqtSlot()
    def loadSettings(self):
        dlg = QFileDialog()

        loadFile = dlg.getOpenFileName(caption='Read config file', filter='Config Files(*.yml);;All Files(*.*)')

        # Detect QT5 return
        if isinstance(loadFile,tuple):
            loadFile = loadFile[0]

        if loadFile != '':
            self.root.LoadConfig(loadFile)

    @pyqtSlot()
    def saveSettings(self):
        dlg = QFileDialog()
        sug = datetime.datetime.now().strftime("config_%Y%m%d_%H%M%S.yml") 

        saveFile = dlg.getSaveFileName(caption='Save config file', directory=sug, filter='Config Files(*.yml);;All Files(*.*)')

        # Detect QT5 return
        if isinstance(saveFile,tuple):
            saveFile = saveFile[0]

        if saveFile != '':
            self.root.SaveConfig(saveFile)

    @pyqtSlot()
    def saveState(self):
        dlg = QFileDialog()
        sug = datetime.datetime.now().strftime("state_%Y%m%d_%H%M%S.yml") 

        stateFile = dlg.getSaveFileName(caption='Save State file', directory=sug, filter='State Files(*.yml);;All Files(*.*)')

        # Detect QT5 return
        if isinstance(stateFile,tuple):
            stateFile = stateFile[0]

        if stateFile != '':
            self.root.SaveState(stateFile)

