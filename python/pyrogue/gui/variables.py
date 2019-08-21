#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Title      : Variable display for rogue GUI
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
import threading

class VariableDev(QObject):

    def __init__(self,*,tree,parent,dev,noExpand,top,minVisibility):
        QObject.__init__(self)
        self._parent   = parent
        self._tree     = tree
        self._dev      = dev
        self._children = []

        self._widget = QTreeWidgetItem(parent)
        self._widget.setText(0,self._dev.name)
        self._minVisibility = minVisibility

        if top:
            self._parent.addTopLevelItem(self._widget)

        if (not noExpand) and self._dev.expand:
            self._dummy = None
            self._widget.setExpanded(True)
            self.setup(False)
        else:
            self._dummy = QTreeWidgetItem(self._widget) # One dummy item to add expand control
            self._widget.setExpanded(False)
            self._tree.itemExpanded.connect(self.expandCb)

    @pyqtSlot()
    def expandCb(self):
        if self._dummy is None or not self._widget.isExpanded():
            return

        self._widget.removeChild(self._dummy)
        self._dummy = None
        self.setup(True)

    def setup(self,noExpand):

        # First create variables
        for key,val in self._dev.visibleVariables(self._minVisibility).items():
            self._children.append(VariableLink(tree=self._tree,
                                               parent=self._widget,
                                               variable=val))
            QCoreApplication.processEvents()

        # Then create devices
        for key,val in self._dev.visibleDevices(self._minVisibility).items():
            self._children.append(VariableDev(tree=self._tree,
                                              parent=self._widget,
                                              dev=val,
                                              noExpand=noExpand,
                                              top=False,
                                              minVisibility=self._minVisibility))

        for i in range(0,4):
            self._tree.resizeColumnToContents(i)

class VariableLink(QObject):
    """Bridge between the pyrogue tree and the display element"""

    updateGui = pyqtSignal([int],[str])

    def __init__(self,*,tree,parent,variable):
        QObject.__init__(self)
        self._variable = variable
        self._lock     = threading.Lock()
        self._parent   = parent
        self._tree     = tree
        self._inEdit   = False
        self._swSet    = False
        self._widget   = None

        self._item = QTreeWidgetItem(parent)
        self._item.setText(0,variable.name)
        self._item.setText(1,variable.mode)
        self._item.setText(2,variable.typeStr)

        
        self._alarm = QLineEdit()
        self._alarm.setReadOnly(True)
        #self._alarm.setText('None')
        if variable.hasAlarm:
            self._tree.setItemWidget(self._item,5,self._alarm)

        if variable.units:
            self._item.setText(4,str(variable.units))

        if self._variable.disp == 'enum' and self._variable.enum is not None and self._variable.mode != 'RO':
            self._widget = QComboBox()
            self._widget.activated.connect(self.cbChanged)

            self.updateGui.connect(self._widget.setCurrentIndex)

            for i in self._variable.enum:
                self._widget.addItem(self._variable.enum[i])

        elif self._variable.minimum is not None and self._variable.maximum is not None and \
             self._variable.disp == '{}' and self._variable.mode != 'RO':
            self._widget = QSpinBox();
            self._widget.setMinimum(self._variable.minimum)
            self._widget.setMaximum(self._variable.maximum)
            self._widget.valueChanged.connect(self.sbChanged)

            self.updateGui.connect(self._widget.setValue)

        else:
            self._widget = QLineEdit()
            self._widget.returnPressed.connect(self.returnPressed)
            self._widget.textEdited.connect(self.valueChanged)

            self.updateGui[str].connect(self._widget.setText)

        self._widget.setToolTip(self._variable.description)
        self._widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self._widget.customContextMenuRequested.connect(self.openMenu)

        if self._variable.mode == 'RO':
            self._widget.setReadOnly(True)

        self._tree.setItemWidget(self._item,3,self._widget)
        self.varListener(None,self._variable.getVariableValue(read=False))

        variable.addListener(self.varListener)

    def openMenu(self, event):
        menu = QMenu()
        read_variable  = None
        write_variable = None

        var_info = menu.addAction('Variable Information')
        read_recurse = menu.addAction('Read Recursive')
        write_recurse = menu.addAction('Write Recursive')
        read_device = menu.addAction('Read Device')
        write_device = menu.addAction('Write Device')

        if self._variable.mode != 'WO':
            read_variable = menu.addAction('Read Variable')
        if self._variable.mode != 'RO':
            write_variable = menu.addAction('Write Variable')

        action = menu.exec_(self._widget.mapToGlobal(event))

        if action == var_info:
            self.infoDialog()
        elif action == read_recurse:
            self._variable.parent.ReadDevice(True)
        elif action == write_recurse:
            self._variable.parent.WriteDevice(True)
        elif action == read_device:
            self._variable.parent.ReadDevice(False)
        elif action == write_device:
            self._variable.parent.WriteDevice(False)
        elif action == read_variable:
            self._variable.get()
        elif action == write_variable:
            if isinstance(self._widget, QComboBox):
                self._variable.setDisp(self._widget.currentText())
            elif isinstance(self._widget, QSpinBox):
                self._variable.set(self._widget.value())
            else:
                self._variable.setDisp(self._widget.text())

    def infoDialog(self):

        attrs = ['name', 'path', 'description', 'visibility', 'enum', 
                 'typeStr', 'disp', 'precision', 'mode', 'units', 'minimum', 
                 'maximum', 'lowWarning', 'lowAlarm', 'highWarning', 
                 'highAlarm', 'alarmStatus', 'alarmSeverity', 'pollInterval']

        if self._variable.isinstance(pyrogue.RemoteVariable):
            attrs += ['offset', 'bitSize', 'bitOffset', 'verify', 'varBytes']

        msgBox = QDialog()
        msgBox.setWindowTitle("Variable Information For {}".format(self._variable.name))
        msgBox.setMinimumWidth(400)

        vb = QVBoxLayout()
        msgBox.setLayout(vb)

        fl = QFormLayout()
        fl.setRowWrapPolicy(QFormLayout.DontWrapRows)
        fl.setFormAlignment(Qt.AlignHCenter | Qt.AlignTop)
        fl.setLabelAlignment(Qt.AlignRight)
        vb.addLayout(fl)

        pb = QPushButton('Close')
        pb.pressed.connect(msgBox.close)
        vb.addWidget(pb)

        for a in attrs:
            le = QLineEdit()
            le.setReadOnly(True)
            le.setText(str(getattr(self._variable,a)))
            fl.addRow(a,le)
        msgBox.exec()

    def varListener(self, path, varVal):
        with self._lock:
            if self._widget is None or self._inEdit is True:
                return

            self._swSet = True

            if isinstance(self._widget, QComboBox):
                i = self._widget.findText(varVal.valueDisp)

                if i < 0: i = 0

                if self._widget.currentIndex() != i:
                    self.updateGui.emit(i)
            elif isinstance(self._widget, QSpinBox):
                if self._widget.value != varVal.value:
                    self.updateGui.emit(varVal.value)
            else:
                if self._widget.text() != varVal.valueDisp:
                    self.updateGui[str].emit(varVal.valueDisp)

            if varVal.severity == 'AlarmMajor':
                self._alarm.setText('Major')
                p = QPalette()
                p.setColor(QPalette.Base,Qt.red)
                p.setColor(QPalette.Text,Qt.black)
                self._alarm.setPalette(p)

            elif varVal.severity == 'AlarmMinor':
                self._alarm.setText('Minor')
                p = QPalette()
                p.setColor(QPalette.Base,Qt.yellow)
                p.setColor(QPalette.Text,Qt.black)
                self._alarm.setPalette(p)

            elif varVal.severity == 'Good':
                self._alarm.setText('Good')
                p = QPalette()
                p.setColor(QPalette.Base,Qt.green)
                p.setColor(QPalette.Text,Qt.black)
                self._alarm.setPalette(p)

            else:
                self._alarm.setText('')
                p = QPalette()
                self._alarm.setPalette(p)

            self._swSet = False

    @pyqtSlot()
    def valueChanged(self):
        self._inEdit = True
        p = QPalette()
        p.setColor(QPalette.Base,Qt.yellow)
        p.setColor(QPalette.Text,Qt.black)
        self._widget.setPalette(p)

    @pyqtSlot()
    def returnPressed(self):
        p = QPalette()
        self._widget.setPalette(p)

        self._variable.setDisp(self._widget.text())
        self._inEdit = False
        self.updateGui.emit(self._variable.valueDisp())

    @pyqtSlot(int)
    def sbChanged(self, value):
        if self._swSet:
            return
        
        self._inEdit = True
        self._variable.setDisp(value)
        self._inEdit = False

    @pyqtSlot(int)
    def cbChanged(self, value):
        if self._swSet:
            return

        self._inEdit = True
            self._variable.setDisp(self._widget.itemText(value))
        self._inEdit = False


class VariableWidget(QWidget):
    def __init__(self, *, parent=None):
        super(VariableWidget, self).__init__(parent)

        self.roots = []
        self._children = []

        vb = QVBoxLayout()
        self.setLayout(vb)
        self.tree = QTreeWidget()
        vb.addWidget(self.tree)

        self.tree.setColumnCount(2)
        self.tree.setHeaderLabels(['Variable','Mode','Type','Value','Units', 'Alarm', ''])

        hb = QHBoxLayout()
        vb.addLayout(hb)

        pb = QPushButton('Read')
        pb.pressed.connect(self.readPressed)
        hb.addWidget(pb)

        self.devTop = None

    @pyqtSlot(pyrogue.Root,int)
    @pyqtSlot(pyrogue.VirtualNode,int)
    def addTree(self,root, minVisibility):
        self.roots.append(root)
        self._children.append(VariableDev(tree=self.tree,
                                          parent=self.tree,
                                          dev=root,
                                          noExpand=False,
                                          top=True,
                                          minVisibility=minVisibility))

    @pyqtSlot()
    def readPressed(self):
        for root in self.roots:
            root.ReadAll()

