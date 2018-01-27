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

import pyrogue
import Pyro4
import threading

class VariableLink(QObject):
    """Bridge between the pyrogue tree and the display element"""

    def __init__(self,*,tree,parent,variable,expand):
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

        variable.addListener(self)

        if expand:
            self.setup(None)
        else:
            self._tree.itemExpanded.connect(self.setup)

    def setup(self,item):
        with self._lock:
            if self._widget is not None or (item is not None and item != self._parent):
                return

            if self._variable.disp == 'enum' and self._variable.enum is not None and self._variable.mode != 'RO':
                self._widget = QComboBox()
                self._widget.activated.connect(self.guiChanged)
                self.connect(self,SIGNAL('updateGui'),self._widget.setCurrentIndex)
                self._widget.setToolTip(self._variable.description)

                for i in self._variable.enum:
                    self._widget.addItem(self._variable.enum[i])

            elif self._variable.disp == 'range':
                self._widget = QSpinBox();
                self._widget.setMinimum(self._variable.minimum)
                self._widget.setMaximum(self._variable.maximum)
                self._widget.valueChanged.connect(self.guiChanged)
                self.connect(self,SIGNAL('updateGui'),self._widget.setValue)
                self._widget.setToolTip(self._variable.description)

            else:
                self._widget = QLineEdit()
                self._widget.returnPressed.connect(self.returnPressed)
                self._widget.textEdited.connect(self.valueChanged)
                self.connect(self,SIGNAL('updateGui'),self._widget.setText)
                self._widget.setToolTip(self._variable.description)

            if self._variable.mode == 'RO':
                self._widget.setReadOnly(True)

            self._tree.setItemWidget(self._item,3,self._widget)
        self.varListener(None,self._variable.value(),self._variable.valueDisp())

        for i in range(0,4):
            self._tree.resizeColumnToContents(i)

    @Pyro4.expose
    def varListener(self, path, value, disp):
        #print('{} varListener ( {} {} )'.format(self.variable, type(value), value))
        with self._lock:
            if self._widget is None or self._inEdit is True:
                return

            self._swSet = True

            if isinstance(self._widget, QComboBox):
                if self._widget.currentIndex() != self._widget.findText(disp):
                    self.emit(SIGNAL("updateGui"), self._widget.findText(disp))
            elif isinstance(self._widget, QSpinBox):
                if self._widget.value != value:
                    self.emit(SIGNAL("updateGui"), value)
            else:
                if self._widget.text() != disp:
                    self.emit(SIGNAL("updateGui"), disp)

            self._swSet = False

    def valueChanged(self):
        self._inEdit = True
        p = QPalette()
        p.setColor(QPalette.Base,Qt.yellow)
        self._widget.setPalette(p)

    def returnPressed(self):
        p = QPalette()
        p.setColor(QPalette.Base,Qt.white)
        self._widget.setPalette(p)

        self.guiChanged(self._widget.text())
        self._inEdit = False
        self.emit(SIGNAL("updateGui"), self._variable.valueDisp())

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

        self.devList = []

    def addTree(self,root):
        self.roots.append(root)

        r = QTreeWidgetItem(self.top)
        r.setText(0,root.name)
        r.setExpanded(True)
        self.addTreeItems(r,root,True)

    def readPressed(self):
        for root in self.roots:
            root.ReadAll()

    def addTreeItems(self,parent,d,expand):

        # First create variables
        for key,val in d.getNodes(typ=pyrogue.BaseVariable,exc=pyrogue.BaseCommand,hidden=False).items():
            var = VariableLink(tree=self.tree,parent=parent,variable=val,expand=expand)

        # Then create devices
        for key,val in d.getNodes(typ=pyrogue.Device,hidden=False).items():
            nxtExpand = expand if val.expand else False

            w = QTreeWidgetItem(parent)
            w.setText(0,val.name)
            w.setExpanded(nxtExpand)
            self.addTreeItems(w,val,nxtExpand)
            self.devList.append({'dev':val,'item':w})


