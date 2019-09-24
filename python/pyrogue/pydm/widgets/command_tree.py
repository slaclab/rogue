#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Title      : PyRogue PyDM Command Tree Widget
#-----------------------------------------------------------------------------
# File       : pyrogue/pydm/widgets/command_tree.py
# Created    : 2019-09-18
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to 
# the license terms in the LICENSE.txt file found in the top-level directory 
# of this distribution and at: 
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html. 
# No part of the rogue software platform, including this file, may be 
# copied, modified, propagated, or distributed except according to the terms 
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

import pyrogue
import pyrogue.pydm.widgets
from pydm.widgets.frame import PyDMFrame
from pydm.widgets import PyDMLineEdit, PyDMLabel, PyDMSpinbox, PyDMPushButton, PyDMEnumComboBox
from pyrogue.pydm.data_plugins.rogue_plugin import nodeFromAddress
from pyrogue.interfaces import VirtualClient
from qtpy.QtCore import Qt, Property, Slot, QPoint
from qtpy.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy, QMenu, QDialog, QPushButton
from qtpy.QtWidgets import QTreeWidgetItem, QTreeWidget, QLineEdit, QFormLayout, QGroupBox

class CommandDev(QTreeWidgetItem):

    def __init__(self,*, path, top, parent, dev, noExpand):
        QTreeWidgetItem.__init__(self,parent)
        self._top      = top
        self._parent   = parent
        self._dev      = dev
        self._dummy    = None
        self._path     = path

        w = PyDMLabel(parent=None, init_channel=self._path + '/name')
        w.showUnits             = False
        w.precisionFromPV       = False
        w.alarmSensitiveContent = False
        w.alarmSensitiveBorder  = False

        self._top._tree.setItemWidget(self,0,w)
        self.setToolTip(0,self._dev.description)

        if self._top._node == dev:
            self._parent.addTopLevelItem(self)
            self.setExpanded(True)
            self._setup(False)

        elif (not noExpand) and self._dev.expand:
            self.setExpanded(True)
            self._setup(False)
        else:
            self._dummy = QTreeWidgetItem(self) # One dummy item to add expand control
            self.setExpanded(False)

    def _setup(self,noExpand):

        # First create commands
        for key,val in self._dev.commandsByGroup(incGroups=self._top._incGroups,
                                                 excGroups=self._top._excGroups).items():

            CommandHolder(path=self._path + '.' + val.name,
                          top=self._top, 
                          parent=self, 
                          command=val)

        # Then create devices
        for key,val in self._dev.devicesByGroup(incGroups=self._top._incGroups,
                                                excGroups=self._top._excGroups).items():

            CommandDev(path=self._path + '.' + val.name,
                       top=self._top, 
                       parent=self, 
                       dev=val, 
                       noExpand=noExpand)

    def _expand(self):
        if self._dummy is None:
            return

        self.removeChild(self._dummy)
        self._dummy = None
        self._setup(True)

class CommandHolder(QTreeWidgetItem):

    def __init__(self,*,path,top,parent,command):
        QTreeWidgetItem.__init__(self,parent)
        self._top    = top
        self._parent = parent
        self._cmd    = command
        self._path   = path

        w = PyDMLabel(parent=None, init_channel=self._path + '/name')
        w.showUnits             = False
        w.precisionFromPV       = False
        w.alarmSensitiveContent = False
        w.alarmSensitiveBorder  = True

        self._top._tree.setItemWidget(self,0,w)
        self.setToolTip(0,self._cmd.description)

        self.setText(1,self._cmd.typeStr)

        self._cmd = pyrogue.pydm.widgets.Command(init_channel=self._path)
        self._top._tree.setItemWidget(self,2,self._cmd)

        #if self._cmd.arg:

            #if self._cmd.disp == 'enum' and self._cmd.enum is not None and self._cmd.mode != 'RO':
                #w = PyDMEnumComboBox(parent=None, init_channel=self._path)
                #w.alarmSensitiveContent = False
                #w.alarmSensitiveBorder  = False
            #else:
                #self._path += '/disp'
                #w = PyDMLineEdit(parent=None, init_channel=self._path)
                #w.showUnits             = False
                #w.precisionFromPV       = True
                #w.alarmSensitiveContent = False
                #w.alarmSensitiveBorder  = False
        #else:
            #w = PyDMPushButton(label='Exec',pressValue=1,init_channel=self._path)

        #self._top._tree.setItemWidget(self,2,w)


class CommandTree(PyDMFrame):
    def __init__(self, parent=None, init_channel=None, incGroups=None, excGroups=['Hidden']):
        PyDMFrame.__init__(self, parent, init_channel)

        self._node = None
        self._path = None

        self._incGroups = incGroups
        self._excGroups = excGroups
        self._tree      = None
        self._children  = []

    def connection_changed(self, connected):
        build = self._connected != connected and connected == True
        super(CommandTree, self).connection_changed(connected)

        if not build: return

        self._node = nodeFromAddress(self.channel)
        self._path = self.channel

        vb = QVBoxLayout()
        self.setLayout(vb)

        self._tree = QTreeWidget()
        vb.addWidget(self._tree)

        self._tree.setColumnCount(3)
        self._tree.setHeaderLabels(['Command','Base','Execute / Arg'])

        self._tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self._tree.customContextMenuRequested.connect(self._openMenu)

        self._tree.itemExpanded.connect(self._expandCb)

        #self.setUpdatesEnabled(False)
        CommandDev(path=self._path,
                   top=self,
                   parent=self._tree,
                   dev=self._node,
                   noExpand=False)
        #self.setUpdatesEnabled(True)

    @Slot(QTreeWidgetItem)
    def _expandCb(self,item):
        #self.setUpdatesEnabled(False)
        item._expand()

        self._tree.setColumnWidth(0,250)
        self._tree.setColumnWidth(1,50)
        self._tree.setColumnWidth(2,200)

        #self.setUpdatesEnabled(True)

    def _openMenu(self, pos):
        item = self._tree.itemAt(pos)
        item._menu(pos)

    @Property(str)
    def incGroups(self):
        if self._incGroups is None or len(self._incGroups) == 0:
            return ''
        else:
            return ','.join(self._incGroups)

    @incGroups.setter
    def incGroups(self, value):
        if value == '':
            self._incGroups = None
        else:
            self._incGroups = value.split(',')

    @Property(str)
    def excGroups(self):
        if self._excGroups is None or len(self._excGroups) == 0:
            return ''
        else:
            return ','.join(self._excGroups)

    @excGroups.setter
    def excGroups(self, value):
        if value == '':
            self._excGroups = None
        else:
            self._excGroups = value.split(',')

