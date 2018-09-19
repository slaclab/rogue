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
import Pyro4
import threading

class VariableDev(QObject):

    def __init__(self,*,tree,parent,dev,noExpand):
        QObject.__init__(self)
        self._parent   = parent
        self._tree     = tree
        self._dev      = dev
        self._children = []

        self._widget = QTreeWidgetItem(parent)
        self._widget.setText(0,self._dev.name)

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
        for key,val in self._dev.visableVariables.items():
            self._children.append(VariableLink(tree=self._tree,parent=self._widget,variable=val))
            QCoreApplication.processEvents()

        # Then create devices
        for key,val in self._dev.visableDevices.items():
            self._children.append(VariableDev(tree=self._tree,parent=self._widget,dev=val,noExpand=noExpand))

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
        self._item.setText(2,variable.typeStr) # Fix this. Should show base and size

        if variable.units:
            self._item.setText(4,str(variable.units))

        if self._variable.disp == 'enum' and self._variable.enum is not None and self._variable.mode != 'RO':
            self._widget = QComboBox()
            self._widget.activated.connect(self.guiChanged)
            self._widget.setToolTip(self._variable.description)

            self.updateGui.connect(self._widget.setCurrentIndex)

            for i in self._variable.enum:
                self._widget.addItem(self._variable.enum[i])

        elif self._variable.minimum is not None and self._variable.maximum is not None:
            self._widget = QSpinBox();
            self._widget.setMinimum(self._variable.minimum)
            self._widget.setMaximum(self._variable.maximum)
            self._widget.valueChanged.connect(self.guiChanged)
            self._widget.setToolTip(self._variable.description)

            self.updateGui.connect(self._widget.setValue)

        else:
            self._widget = QLineEdit()
            self._widget.returnPressed.connect(self.returnPressed)
            self._widget.textEdited.connect(self.valueChanged)
            self._widget.setToolTip(self._variable.description)

            self.updateGui[str].connect(self._widget.setText)

        if self._variable.mode == 'RO':
            self._widget.setReadOnly(True)

        self._tree.setItemWidget(self._item,3,self._widget)
        self.varListener(None,self._variable.value(),self._variable.valueDisp())

        variable.addListener(self)

    @Pyro4.expose
    def varListener(self, path, value, disp):
        with self._lock:
            if self._widget is None or self._inEdit is True:
                return

            self._swSet = True

            if isinstance(self._widget, QComboBox):
                if self._widget.currentIndex() != self._widget.findText(disp):
                    self.updateGui.emit(self._widget.findText(disp))
            elif isinstance(self._widget, QSpinBox):
                if self._widget.value != value:
                    self.updateGui.emit(value)
            else:
                if self._widget.text() != disp:
                    self.updateGui[str].emit(disp)

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

        self.guiChanged(self._widget.text())
        self._inEdit = False
        self.updateGui.emit(self._variable.valueDisp())

    @pyqtSlot(int)
    @pyqtSlot(str)
    def guiChanged(self, value):
        if self._swSet:
            return

        if self._variable.disp == 'enum':
            # For enums, value will be index of selected item
            # Need to call itemText to convert to string
            self._variable.setDisp(self._widget.itemText(value))

        else:
            # For non enums, value will be string entered in box
            self._variable.setDisp(value)


class VariableWidget(QWidget):
    def __init__(self, *, group, parent=None):
        super(VariableWidget, self).__init__(parent)

        self.roots = []

        vb = QVBoxLayout()
        self.setLayout(vb)
        self.tree = QTreeWidget()
        vb.addWidget(self.tree)

        self.tree.setColumnCount(2)
        self.tree.setHeaderLabels(['Variable','Mode','Base','Value','Units'])

        self.top = QTreeWidgetItem(self.tree)
        self.top.setText(0,group)
        self.tree.addTopLevelItem(self.top)
        self.top.setExpanded(True)

        hb = QHBoxLayout()
        vb.addLayout(hb)

        pb = QPushButton('Read')
        pb.pressed.connect(self.readPressed)
        hb.addWidget(pb)

        self.devTop = None

    @pyqtSlot(pyrogue.Root)
    @pyqtSlot(pyrogue.PyroRoot)
    def addTree(self,root):
        self.roots.append(root)
        self.devTop = VariableDev(tree=self.tree,parent=self.top,dev=root,noExpand=False)

    @pyqtSlot()
    def readPressed(self):
        for root in self.roots:
            root.ReadAll()

