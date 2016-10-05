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
from PyQt4.QtWebKit import *

import pyrogue


class CommandLink(QObject):
    """Bridge between the pyrogue tree and the display element"""

    def __init__(self,parent,command):
        QObject.__init__(self)
        self.command = command

        item = QTreeWidgetItem(parent)
        parent.addChild(item)
        item.setText(0,command.name)
        item.setText(1,command.base)

        if command.base != 'None':
            self.widget = QLineEdit()
            item.treeWidget().setItemWidget(item,2,self.widget)
        else:
            self.widget = None

        pb = QPushButton('Execute')
        item.treeWidget().setItemWidget(item,3,pb)
        pb.clicked.connect(self.execPressed)

    def execPressed(self):
        if self.widget != None:
            value = str(self.widget.text())
        else:
            value=None

        if self.command.base == 'hex':
            try:
                self.command(int(value,16))
            except Exception:
                pass

        elif self.command.base == 'uint':
            try:
                self.command(int(value))
            except Exception:
                pass

        elif self.command.base == 'float':
            try:
                self.command(float(value))
            except Exception:
                pass

        elif self.command.base == 'string':
            self.command(value)

        else:
            self.command()


class CommandWidget(QWidget):
    def __init__(self, root, parent=None):
        super(CommandWidget, self).__init__(parent)

        self.root = root
        self.commands = []

        vb = QVBoxLayout()
        self.setLayout(vb)
        tree = QTreeWidget()
        vb.addWidget(tree)

        tree.setColumnCount(2)
        tree.setHeaderLabels(['Command','Base','Arg','Execute'])

        top = QTreeWidgetItem(tree)
        top.setText(0,root.name)
        tree.addTopLevelItem(top)
        top.setExpanded(True)
        self.addTreeItems(top,root)
        for i in range(0,3):
            tree.resizeColumnToContents(i)

        hb = QHBoxLayout()
        vb.addLayout(hb)

    def addTreeItems(self,tree,d):

        # First create commands
        for key,val in d._nodes.iteritems():
            if isinstance(val,pyrogue.Command):
                if not(key.startswith('_') or val.hidden):
                    self.commands.append(CommandLink(tree,val))

        # Then create devices
        for key,val in d._nodes.iteritems():
            if isinstance(val,pyrogue.Device):
                if not(key.startswith('_') or val.hidden):
                    w = QTreeWidgetItem(tree)
                    w.setText(0,val.name)
                    w.setExpanded(True)
                    self.addTreeItems(w,val)

