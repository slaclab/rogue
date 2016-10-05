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
from PyQt4.QtCore   import *
from PyQt4.QtGui    import *
from PyQt4.QtWebKit import *

import pyrogue

class DataLink(QObject):

    def __init__(self,layout,writer):
        QObject.__init__(self)
        self.writer = writer
        self.block = False

        gb = QGroupBox('Data File Control (%s)' % (writer.name))
        layout.addWidget(gb)





class ControlLink(QObject):

    def __init__(self,layout,control):
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

        self.control.runRate._addListener(self)
        self.runRate = QComboBox()
        self.runRate.activated.connect(self.runRateChanged)
        self.connect(self,SIGNAL('updateRate'),self.runRate.setCurrentIndex)
        for key in sorted(self.control.runRate.enum):
            self.runRate.addItem(self.control.runRate.enum[key])

        self.control.runState._addListener(self)
        self.runState = QComboBox()
        self.runState.activated.connect(self.runStateChanged)
        self.connect(self,SIGNAL('updateState'),self.runState.setCurrentIndex)
        for key in sorted(self.control.runState.enum):
            self.runState.addItem(self.control.runState.enum[key])

        self.control.runCount._addListener(self)
        self.runCount = QLineEdit()
        self.runCount.setReadOnly(True)
        self.connect(self,SIGNAL('updateCount'),self.runCount.setText)

        fl.addRow('Run State:',self.runState)
        fl.addRow('Run Rate:',self.runRate)
        fl.addRow('Run Count:',self.runCount)

    def newValue(self,var):
        if self.block: return

        if var.name == 'runState':
            self.emit(SIGNAL("updateState"),self.runState.findText(str(var.get())))

        elif var.name == 'runRate':
            self.emit(SIGNAL("updateRate"),self.runRate.findText(str(var.get())))

        elif var.name == 'runCount':
            self.emit(SIGNAL("updateCount"),str(var.get()))

    def runStateChanged(self,value):
        self.block = True
        self.control.runState.set(str(self.runState.itemText(value)))
        self.block = False

    def runRateChanged(self,value):
        self.block = True
        self.control.runRate.set(str(self.runRate.itemText(value)))
        self.block = False

#    def newValue(self,var):
#        if self.block: return
#
#        value = self.variable.get()
#
#        if self.variable.mode == 'RW' and (self.variable.base == 'enum' or self.variable.base == 'bool'):
#            self.emit(SIGNAL("updateGui"),self.widget.findText(str(value)))
#
#        elif self.variable.base == 'range':
#            self.emit(SIGNAL("updateGui"),value)
#
#        elif self.variable.base == 'hex':
#            self.emit(SIGNAL("updateGui"),'0x%x' % (value))
#
#        else:
#            self.emit(SIGNAL("updateGui"),str(value))
#

class SystemWidget(QWidget):
    def __init__(self, root, parent=None):
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

        pb = QPushButton('Soft Reset')
        pb.clicked.connect(self.softReset)
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

        ###################
        # Data Controllers
        ###################
        for key,val in root._nodes.iteritems():
            if isinstance(val,pyrogue.DataWriter):
                self.holders.append(DataLink(tl,val))

        ###################
        # Run Controllers
        ###################
        for key,val in root._nodes.iteritems():
            if isinstance(val,pyrogue.RunControl):
                self.holders.append(ControlLink(tl,val))

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

        self.root.systemLog._addListener(self)
        self.connect(self,SIGNAL('updateLog'),self.systemLog.setText)
        
        pb = QPushButton('Clear Log')
        pb.clicked.connect(self.resetLog)
        vb.addWidget(pb)

    def resetLog(self):
        self.root.clearLog()

    def newValue(self,var):
        if var.name == 'systemLog':
            self.emit(SIGNAL("updateLog"),var.get())

    def hardReset(self):
        self.root.hardReset()

    def softReset(self):
        self.root.softReset()

    def countReset(self):
        self.root.countReset()

    def loadSettings(self):
        dlg = QFileDialog()
        dlg.setFileMode(QFileDialog.AnyFile)
        dlg.setFilter('Config Files (*.yml)')

        if dlg.exec_():
           loadFile = str(dlg.selectedFiles()[0])
           self.root.readConfig(loadFile)

    def saveSettings(self):
        dlg = QFileDialog()
        dlg.setFileMode(QFileDialog.AnyFile)
        dlg.setFilter('Config Files (*.yml)')

        if dlg.exec_():
           saveFile = str(dlg.selectedFiles()[0])
           self.root.writeConfig(saveFile)

