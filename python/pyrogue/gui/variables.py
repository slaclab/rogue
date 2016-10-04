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
from PyQt4.QtCore   import *
from PyQt4.QtGui    import *
from PyQt4.QtWebKit import *

import pyrogue


class VariableLink(QObject):
    """Bridge between the pyrogue tree and the display element"""

    def __init__(self,parent,variable):
        QObject.__init__(self)
        self.variable = variable
        self.block = False

        item = QTreeWidgetItem(parent)
        parent.addChild(item)
        item.setText(0,variable.name)
        item.setText(1,variable.mode)
        item.setText(2,variable.base)

        if variable.base == 'enum':
            self.widget = QComboBox()
            self.widget.activated.connect(self.guiChanged)
            self.connect(self,SIGNAL('updateGui'),self.widget.setCurrentIndex)

            for i in sorted(variable.enum):
                self.widget.addItem(i)

        elif variable.base == 'bool':
            self.widget = QComboBox()
            self.widget.addItem('False')
            self.widget.addItem('True')
            self.widget.activated.connect(self.guiChanged)
            self.connect(self,SIGNAL('updateGui'),self.widget.setCurrentIndex)

        elif variable.base == 'range':
            self.widget = QSpinBox()
            self.widget.setMinimum(variable.minimum)
            self.widget.setMaximum(variable.maximum)
            self.widget.valueChanged.connect(self.guiChanged)
            self.connect(self,SIGNAL('updateGui'),self.widget.setValue)

        else:
            self.widget = QLineEdit()
            self.widget.textEdited.connect(self.guiChanged)
            self.connect(self,SIGNAL('updateGui'),self.widget.setText)

        if variable.mode == 'RO':
            self.widget.setReadOnly(True)

        item.treeWidget().setItemWidget(item,3,self.widget)
        variable._addListener(self)
        self.newValue(None)

    def newValue(self,var):
        if self.block: return

        value = self.variable.get()

        if self.variable.base == 'enum' or self.variable.base == 'bool':
            self.emit(SIGNAL("updateGui"),self.widget.findText(str(value)))

        elif self.variable.base == 'range':
            self.emit(SIGNAL("updateGui"),value)

        elif self.variable.base == 'hex':
            self.emit(SIGNAL("updateGui"),'0x%x' % (value))

        else:
            self.emit(SIGNAL("updateGui"),str(value))

    def guiChanged(self,value):
        self.block = True

        if self.variable.base == 'enum':
            self.variable.set(self.widget.itemText(value))

        elif self.variable.base == 'bool':
            self.variable.set(self.widget.itemText(value) == 'True')

        elif self.variable.base == 'range':
            self.variable.set(value)

        elif self.variable.base == 'hex':
            try:
                self.variable.set(int(str(value),16))
            except Exception:
                pass

        elif self.variable.base == 'uint':
            try:
                self.variable.set(int(str(value)))
            except Exception:
                pass

        elif self.variable.base == 'float':
            try:
                self.variable.set(float(str(value)))
            except Exception:
                pass

        else:
            self.variable.set(str(value))
        self.block = False


class VariableWidget(QWidget):
    def __init__(self, root, parent=None):
        super(VariableWidget, self).__init__(parent)

        self.root = root

        vb = QVBoxLayout()
        self.setLayout(vb)
        tree = QTreeWidget()
        vb.addWidget(tree)

        tree.setColumnCount(2)
        tree.setHeaderLabels(['Variable','Mode','Base','Value'])

        top = QTreeWidgetItem(tree)
        top.setText(0,root.name)
        tree.addTopLevelItem(top)
        top.setExpanded(True)
        self.addTreeItems(top,root)
        for i in range(0,4):
            tree.resizeColumnToContents(i)

        hb = QHBoxLayout()
        vb.addLayout(hb)

        pb = QPushButton('Read All')
        pb.pressed.connect(self.readAllPressed)
        hb.addWidget(pb)

        pb = QPushButton('Write All')
        pb.pressed.connect(self.writeAllPressed)
        hb.addWidget(pb)

        pb = QPushButton('Write Stale')
        pb.pressed.connect(self.writeStalePressed)
        hb.addWidget(pb)

        pb = QPushButton('Verify')
        pb.pressed.connect(self.verifyPressed)
        hb.addWidget(pb)

    def readAllPressed(self):
        self.root.readAll()

    def writeAllPressed(self):
        self.root.writeAll()

    def writeStalePressed(self):
        self.root.writeStale()

    def verifyPressed(self):
        self.root.verify()

    def addTreeItems(self,tree,d):

        # First create variables
        for key in sorted(d.__dict__):
            val = getattr(d,key)
            if isinstance(val,pyrogue.Variable):
                if not(key.startswith('_') or val.hidden):
                    var = VariableLink(tree,val)

        # Then create devices
        for key in sorted(d.__dict__):
            val = getattr(d,key)
            if isinstance(val,pyrogue.Device):
                if not(key.startswith('_') or val.hidden):
                    w = QTreeWidgetItem(tree)
                    w.setText(0,val.name)
                    w.setExpanded(True)
                    self.addTreeItems(w,val)

