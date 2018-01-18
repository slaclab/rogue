#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Title      : Command windows for GUI
#-----------------------------------------------------------------------------
# File       : pyrogue/gui/commands.py
# Author     : Ryan Herbst, rherbst@slac.stanford.edu
# Created    : 2016-10-03
# Last update: 2016-10-03
#-----------------------------------------------------------------------------
# Description:
# Module for functions and classes related to command display in the rogue GUI
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


class CommandLink(QObject):
    """Bridge between the pyrogue tree and the display element"""

    def __init__(self,*,tree,parent,command,expand):
        QObject.__init__(self)
        self._command = command
        self._parent  = parent
        self._tree    = tree
        self._widget  = None
        self._pb      = None

        self._item = QTreeWidgetItem(parent)
        self._item.setText(0,command.name)
        self._item.setText(1,command.typeStr)

        if expand:
            self.setup(None)
        else:
            self._tree.itemExpanded.connect(self.setup)

    def setup(self,item):
        if self._pb is not None or (item is not None and item != self._parent):
            return

        self._pb = QPushButton('Execute')
        self._tree.setItemWidget(self._item,2,self._pb)
        self._pb.clicked.connect(self.execPressed)
        self._pb.setToolTip(self._command.description)

        if self._command.arg:
            if self._command.disp == 'enum' and self._command.enum is not None:
                self._widget = QComboBox()
                for i in self._command.enum:
                    self._widget.addItem(self._command.enum[i])
                self._widget.setCurrentIndex(self._widget.findText(self._command.valueDisp()))

            elif self._command.disp == 'range':
                self._widget = QSpinBox();
                self._widget.setMinimum(self._command.minimum)
                self._widget.setMaximum(self._command.maximum)
                self._widget.setValue(self._command.value())

            else:
                self._widget = QLineEdit()
                self._widget.setText(self._command.valueDisp())

            self._tree.setItemWidget(self._item,3,self._widget)

        for i in range(0,3):
            self._tree.resizeColumnToContents(i)

    def execPressed(self):
        if self._widget is not None:
            value = str(self._widget.text())
        else:
            value=None

        if self._command.arg:
            try:
                self._command.call(self._command.parseDisp(value))
            except Exception:
                pass
        else:
            self._command.call()

class CommandWidget(QWidget):
    def __init__(self, *, group, parent=None):
        super(CommandWidget, self).__init__(parent)

        self.roots = []
        self.commands = []

        vb = QVBoxLayout()
        self.setLayout(vb)
        self.tree = QTreeWidget()
        vb.addWidget(self.tree)

        self.tree.setColumnCount(2)
        self.tree.setHeaderLabels(['Command','Base','Execute','Arg'])

        self.top = QTreeWidgetItem(self.tree)
        self.top.setText(0,group)
        self.tree.addTopLevelItem(self.top)
        self.top.setExpanded(True)

        hb = QHBoxLayout()
        vb.addLayout(hb)

        self.devList = []

    def addTree(self,root):
        self.roots.append(root)

        r = QTreeWidgetItem(self.top)
        r.setText(0,root.name)
        r.setExpanded(True)
        self.addTreeItems(r,root,True)

    def addTreeItems(self,parent,d,expand):

        # First create commands
        for key,val in d.getNodes(typ=pyrogue.BaseCommand,hidden=False).items():
            self.commands.append(CommandLink(tree=self.tree,parent=parent,command=val,expand=expand))

        # Then create devices
        for key,val in d.getNodes(typ=pyrogue.Device,hidden=False).items():
            if not val.expand:
                expand = False

            w = QTreeWidgetItem(parent)
            w.setText(0,val.name)
            w.setExpanded(expand)
            self.addTreeItems(w,val,expand)
            self.devList.append({'dev':val,'item':w})

