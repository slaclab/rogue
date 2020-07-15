#-----------------------------------------------------------------------------
# Title      : System display for rogue GUI
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
from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem, QPushButton, QComboBox, QFileDialog
from PyQt5.QtWidgets import QLineEdit, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox
from PyQt5.QtCore    import QObject, pyqtSlot, pyqtSignal, QCoreApplication, Qt
from PyQt5.QtGui     import QPalette

import pyrogue
import datetime
import jsonpickle
import time


class DataLink(QObject):

    updateDataFile    = pyqtSignal(str)
    updateOpenState   = pyqtSignal(str)
    updateBufferSize  = pyqtSignal(str)
    updateMaxSize     = pyqtSignal(str)
    updateTotalSize   = pyqtSignal(str)
    updateCurrentSize = pyqtSignal(str)
    updateFrameCount  = pyqtSignal(str)

    def __init__(self,*,layout,writer):
        QObject.__init__(self)
        self.writer = writer
        self.block = False

        gb = QGroupBox('Data File Control (%s) ' % (writer.name))
        layout.addWidget(gb)

        vb = QVBoxLayout()
        gb.setLayout(vb)

        fl = QFormLayout()
        fl.setRowWrapPolicy(QFormLayout.DontWrapRows)
        fl.setFormAlignment(Qt.AlignHCenter | Qt.AlignTop)
        fl.setLabelAlignment(Qt.AlignRight)
        vb.addLayout(fl)

        self.writer.DataFile.addListener(self.varListener)
        self.dataFile = QLineEdit()
        self.dataFile.setText(self.writer.DataFile.valueDisp())
        self.dataFile.textEdited.connect(self.dataFileEdited)
        self.dataFile.returnPressed.connect(self.dataFileChanged)
        self.updateDataFile.connect(self.dataFile.setText)

        fl.addRow('Data File:',self.dataFile)

        hb = QHBoxLayout()
        vb.addLayout(hb)

        pb = QPushButton('Browse')
        pb.clicked.connect(self.browse)
        hb.addWidget(pb)

        pb = QPushButton('Auto Name')
        pb.clicked.connect(self.genName)
        hb.addWidget(pb)

        pb = QPushButton('Open')
        pb.clicked.connect(self.open)
        hb.addWidget(pb)

        pb = QPushButton('Close')
        pb.clicked.connect(self.close)
        hb.addWidget(pb)

        hb = QHBoxLayout()
        vb.addLayout(hb)

        vbl = QVBoxLayout()
        hb.addLayout(vbl)

        fl = QFormLayout()
        fl.setRowWrapPolicy(QFormLayout.DontWrapRows)
        fl.setFormAlignment(Qt.AlignHCenter | Qt.AlignTop)
        fl.setLabelAlignment(Qt.AlignRight)
        vbl.addLayout(fl)

        self.writer.BufferSize.addListener(self.varListener)
        self.bufferSize = QLineEdit()
        self.bufferSize.setText(self.writer.BufferSize.valueDisp())
        self.bufferSize.textEdited.connect(self.bufferSizeEdited)
        self.bufferSize.returnPressed.connect(self.bufferSizeChanged)
        self.updateBufferSize.connect(self.bufferSize.setText)
        fl.addRow('Buffer Size:',self.bufferSize)

        self.writer.IsOpen.addListener(self.varListener)
        self.openState = QLineEdit()
        self.openState.setText(self.writer.IsOpen.valueDisp())
        self.openState.setReadOnly(True)
        self.updateOpenState.connect(self.openState.setText)
        fl.addRow('File Open:',self.openState)

        self.writer.CurrentSize.addListener(self.varListener)
        self.curSize = QLineEdit()
        self.curSize.setText(self.writer.CurrentSize.valueDisp())
        self.curSize.setReadOnly(True)
        self.updateCurrentSize.connect(self.curSize.setText)
        fl.addRow('Current File Size:',self.curSize)

        vbr = QVBoxLayout()
        hb.addLayout(vbr)

        fl = QFormLayout()
        fl.setRowWrapPolicy(QFormLayout.DontWrapRows)
        fl.setFormAlignment(Qt.AlignHCenter | Qt.AlignTop)
        fl.setLabelAlignment(Qt.AlignRight)
        vbr.addLayout(fl)

        self.writer.MaxFileSize.addListener(self.varListener)
        self.maxSize = QLineEdit()
        self.maxSize.setText(self.writer.MaxFileSize.valueDisp())
        self.maxSize.textEdited.connect(self.maxSizeEdited)
        self.maxSize.returnPressed.connect(self.maxSizeChanged)
        self.updateMaxSize.connect(self.maxSize.setText)
        fl.addRow('Max Size:',self.maxSize)

        self.writer.FrameCount.addListener(self.varListener)
        self.frameCount = QLineEdit()
        self.frameCount.setText(self.writer.FrameCount.valueDisp())
        self.frameCount.setReadOnly(True)
        self.updateFrameCount.connect(self.frameCount.setText)
        fl.addRow('Frame Count:',self.frameCount)

        self.writer.TotalSize.addListener(self.varListener)
        self.totSize = QLineEdit()
        self.totSize.setText(self.writer.TotalSize.valueDisp())
        self.totSize.setReadOnly(True)
        self.updateTotalSize.connect(self.totSize.setText)
        fl.addRow('Total File Size:',self.totSize)

    @pyqtSlot()
    def browse(self):
        dlg = QFileDialog()
        sug = datetime.datetime.now().strftime("data_%Y%m%d_%H%M%S.dat")

        dataFile = dlg.getSaveFileName(options=QFileDialog.DontConfirmOverwrite, directory=sug, caption='Select data file', filter='Data Files(*.dat);;All Files(*.*)')

        # Detect QT5 return
        if isinstance(dataFile,tuple):
            dataFile = dataFile[0]

        if dataFile != '':
            try:
                self.writer.DataFile.setDisp(dataFile)
            except Exception as msg:
                print(f"Got Exception: {msg}")

    def genName(self):
        try:
            self.writer.AutoName()
        except Exception as msg:
            print(f"Got Exception: {msg}")

    def varListener(self,path,value):
        if self.block:
            return

        name = path.split('.')[-1]

        if name == 'DataFile':
            self.updateDataFile.emit(value.valueDisp)

        elif name == 'IsOpen':
            self.updateOpenState.emit(value.valueDisp)

        elif name == 'BufferSize':
            self.updateBufferSize.emit(value.valueDisp)

        elif name == 'MaxFileSize':
            self.updateMaxSize.emit(value.valueDisp)

        elif name == 'TotalSize':
            self.updateTotalSize.emit(value.valueDisp)

        elif name == 'CurrentSize':
            self.updateCurrentSize.emit(value.valueDisp)

        elif name == 'FrameCount':
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
        try:
            self.writer.DataFile.setDisp(self.dataFile.text())
        except Exception as msg:
            print(f"Got Exception: {msg}")

        self.block = False

    @pyqtSlot()
    def open(self):
        try:
            self.writer.Open()
        except Exception as msg:
            print(f"Got Exception: {msg}")

    @pyqtSlot()
    def close(self):
        try:
            self.writer.Close()
        except Exception as msg:
            print(f"Got Exception: {msg}")

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
        try:
            self.writer.BufferSize.setDisp(self.bufferSize.text())
        except Exception as msg:
            print(f"Got Exception: {msg}")
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
        try:
            self.writer.MaxFileSize.setDisp(self.maxSize.text())
        except Exception as msg:
            print(f"Got Exception: {msg}")
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
        if self.block:
            return

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
        try:
            self.control.runState.setDisp(self.runState.itemText(value))
        except Exception as msg:
            print(f"Got Exception: {msg}")
        self.block = False

    @pyqtSlot(int)
    def runRateChanged(self,value):
        self.block = True
        try:
            self.control.runRate.setDisp(self.runRate.itemText(value))
        except Exception as msg:
            print(f"Got Exception: {msg}")
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
        for key,val in root.getNodes(typ=pyrogue.DataWriter).items():
            self.holders.append(DataLink(layout=tl,writer=val))

        ###################
        # Run Controllers
        ###################
        for key,val in root.getNodes(typ=pyrogue.RunControl).items():
            self.holders.append(ControlLink(layout=tl,control=val))

        ###################
        # System Log
        ###################
        gb = QGroupBox('System Log')
        tl.addWidget(gb)

        vb = QVBoxLayout()
        gb.setLayout(vb)

        self.systemLog = QTreeWidget()
        vb.addWidget(self.systemLog)

        self.systemLog.setColumnCount(2)
        self.systemLog.setHeaderLabels(['Field','Value'])
        self.systemLog.setColumnWidth(0,200)

        self.logCount = 0

        self.updateLog.connect(self.updateSyslog)
        root.SystemLog.addListener(self.varListener)

        self.updateLog.emit(root.SystemLog.valueDisp())

        pb = QPushButton('Clear Log')
        pb.clicked.connect(self.resetLog)
        vb.addWidget(pb)

        QCoreApplication.processEvents()

    @pyqtSlot(str)
    def updateSyslog(self,value):
        lst = jsonpickle.decode(value)

        if len(lst) == 0:
            self.systemLog.clear()

        elif len(lst) > self.logCount:
            for i in range(self.logCount,len(lst)):
                widget = QTreeWidgetItem(self.systemLog)
                widget.setText(0, time.strftime("%Y-%m-%d %H:%M:%S %Z", time.localtime(lst[i]['created'])))

                widget.setText(1,lst[i]['message'])
                widget.setExpanded(False)
                widget.setTextAlignment(0,Qt.AlignTop)

                temp = QTreeWidgetItem(widget)
                temp.setText(0,'Name')
                temp.setText(1,str(lst[i]['name']))
                temp.setTextAlignment(0,Qt.AlignRight)

                temp = QTreeWidgetItem(widget)
                temp.setText(0,'Level')
                temp.setText(1,'{} ({})'.format(lst[i]['levelName'],lst[i]['levelNumber']))
                temp.setTextAlignment(0,Qt.AlignRight)

                if lst[i]['exception'] is not None:
                    exc = QTreeWidgetItem(widget)
                    exc.setText(0,'exception')
                    exc.setText(1,str(lst[i]['exception']))
                    exc.setExpanded(False)
                    exc.setTextAlignment(0,Qt.AlignRight)

                    for v in lst[i]['traceBack']:
                        temp = QTreeWidgetItem(exc)
                        temp.setText(0,'')
                        temp.setText(1,v)

        self.logCount = len(lst)

    @pyqtSlot()
    def resetLog(self):
        try:
            self.root.ClearLog()
        except Exception as msg:
            print(f"Got Exception: {msg}")

    def varListener(self,path,value):
        name = path.split('.')[-1]

        if name == 'SystemLog':
            self.updateLog.emit(value.valueDisp)

    @pyqtSlot()
    def hardReset(self):
        try:
            self.root.HardReset()
        except Exception as msg:
            print(f"Got Exception: {msg}")

    @pyqtSlot()
    def initialize(self):
        try:
            self.root.Initialize()
        except Exception as msg:
            print(f"Got Exception: {msg}")

    @pyqtSlot()
    def countReset(self):
        try:
            self.root.CountReset()
        except Exception as msg:
            print(f"Got Exception: {msg}")

    @pyqtSlot()
    def loadSettings(self):
        dlg = QFileDialog()

        loadFile = dlg.getOpenFileNames(caption='Read config file', filter='Config Files(*.yml);;All Files(*.*)')

        # Detect QT5 return
        if isinstance(loadFile,tuple):
            loadFile = loadFile[0]

        if loadFile != '':
            try:
                self.root.LoadConfig(loadFile)
            except Exception as msg:
                print(f"Got Exception: {msg}")

    @pyqtSlot()
    def dumpVars(self):
        dlg = QFileDialog()
        sug = datetime.datetime.now().strftime("dump_%Y%m%d_%H%M%S.yml")

        saveFile = dlg.getSaveFileName(caption='Dump Vars file', directory=sug, filter='Config Files(*.yml);;All Files(*.*)')

        # Detect QT5 return
        if isinstance(saveFile,tuple):
            saveFile = saveFile[0]

        if saveFile != '':
            try:
                self.root.DumpVars(saveFile)
            except Exception as msg:
                print(f"Got Exception: {msg}")

    @pyqtSlot()
    def saveSettings(self):
        dlg = QFileDialog()
        sug = datetime.datetime.now().strftime("config_%Y%m%d_%H%M%S.yml")

        saveFile = dlg.getSaveFileName(caption='Save config file', directory=sug, filter='Config Files(*.yml);;All Files(*.*)')

        # Detect QT5 return
        if isinstance(saveFile,tuple):
            saveFile = saveFile[0]

        if saveFile != '':
            try:
                self.root.SaveConfig(saveFile)
            except Exception as msg:
                print(f"Got Exception: {msg}")

    @pyqtSlot()
    def saveState(self):
        dlg = QFileDialog()
        sug = datetime.datetime.now().strftime("state_%Y%m%d_%H%M%S.yml.zip")

        stateFile = dlg.getSaveFileName(caption='Save State file', directory=sug, filter='State Files(*.yml *.yml.zip);;All Files(*.*)')

        # Detect QT5 return
        if isinstance(stateFile,tuple):
            stateFile = stateFile[0]

        if stateFile != '':
            try:
                self.root.SaveState(stateFile)
            except Exception as msg:
                print(f"Got Exception: {msg}")
