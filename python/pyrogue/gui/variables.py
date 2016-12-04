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

import parse

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

        if variable.units:
           item.setText(4,str(variable.units))

        if variable.base == 'enum' and variable.mode=='RW':
            self.widget = QComboBox()
            self.widget.activated.connect(self.guiChanged)
            self.connect(self,SIGNAL('updateGui'),self.widget.setCurrentIndex)

            for i in sorted(variable.enum):
                self.widget.addItem(variable.enum[i])

        elif variable.base == 'bool' and variable.mode=='RW':
            self.widget = QComboBox()
            self.widget.addItem('False')
            self.widget.addItem('True')
            self.widget.activated.connect(self.guiChanged)
            self.connect(self,SIGNAL('updateGui'),self.widget.setCurrentIndex)

        elif variable.base == 'range':
            self.widget.setMaximum(variable.maximum)
            self.widget.valueChanged.connect(self.guiChanged)
            self.connect(self,SIGNAL('updateGui'),self.widget.setValue)

        else:
            self.widget = QLineEdit()
            self.widget.returnPressed.connect(self.returnPressed)
            self.connect(self,SIGNAL('updateGui'),self.widget.setText)

        if variable.mode == 'RO':
            self.widget.setReadOnly(True)

        item.treeWidget().setItemWidget(item,3,self.widget)
        variable.addListener(self.newValue)
        self.newValue(None,variable.get(read=False))

    def newValue(self,var,value):
        if self.block: return

        if self.variable.mode=='RW' and (self.variable.base == 'enum' or self.variable.base == 'bool'):
            self.emit(SIGNAL("updateGui"),self.widget.findText(str(value)))

        elif self.variable.base == 'range':
            self.emit(SIGNAL("updateGui"),value)

        elif self.variable.base == 'hex':
            self.emit(SIGNAL("updateGui"),'0x%x' % (value))

        elif self.variable.base == 'bin':
            self.emit(SIGNAL("updateGui"), '0b{0:b}'.format(value))

        elif self.variable.base == 'float' or self.variable.base == 'string':
            self.emit(SIGNAL("updateGui"), str(value))
            
        else:
            self.emit(SIGNAL("updateGui"), str(value))
            #self.emit(SIGNAL("updateGui"), self.variable.base.format(value)) # Broken
            

    def returnPressed(self):
        self.guiChanged(self.widget.text())

    def guiChanged(self,value):
        self.block = True

        if self.variable.base == 'enum':
            self.variable.set(self.widget.itemText(value))

        elif self.variable.base == 'bool':
            self.variable.set(self.widget.itemText(value) == 'True')

        elif self.variable.base == 'range':
            self.variable.set(value)

        elif self.variable.base == 'hex':
            self.variable.set(int(str(value),16))

        elif self.variable.base == 'uint':
            self.variable.set(int(str(value)))

        elif self.variable.base == 'bin':
            self.variable.set(int(str(value), 2))

        elif self.variable.base == 'float':
            self.variable.set(float(str(value)))
                      
        elif self.variable.base == 'string':
            self.variable.set(str(value))

        else:
            #self.variable.set(parse.parse(self.variable.base, value)[0])  # Broken
            self.variable.set(str(value))
            
        self.block = False


class VariableWidget(QWidget):
    def __init__(self, group, parent=None):
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

    def addTree(self,root):
        self.roots.append(root)

        r = QTreeWidgetItem(self.top)
        r.setText(0,root.name)
        r.setExpanded(True)
        self.addTreeItems(r,root)

        for i in range(0,4):
            self.tree.resizeColumnToContents(i)

    def readPressed(self):
        for root in self.roots:
            root.readAll()

    def addTreeItems(self,tree,d):

        # First create variables
        for key,val in d.getNodes(pyrogue.Variable).iteritems():
            if not val.hidden and val.mode != 'CMD':
                var = VariableLink(tree,val)

        # Then create devices
        for key,val in d.getNodes(pyrogue.Device).iteritems():
            if not val.hidden:
                w = QTreeWidgetItem(tree)
                w.setText(0,val.name)
                w.setExpanded(val.expand)
                self.addTreeItems(w,val)

