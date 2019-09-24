#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Title      : PyRogue PyDM Variable Tree Widget
#-----------------------------------------------------------------------------
# File       : pyrogue/pydm/widgets/variable_tree.py
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
from pydm.widgets.frame import PyDMFrame
from pydm.widgets import PyDMLineEdit, PyDMLabel, PyDMSpinbox, PyDMPushButton, PyDMEnumComboBox
from pyrogue.pydm.data_plugins.rogue_plugin import parseAddress
from pyrogue.interfaces import VirtualClient
from qtpy.QtCore import Qt, Property, Slot
from qtpy.QtWidgets import QVBoxLayout, QHBoxLayout, QMenu, QDialog, QPushButton
from qtpy.QtWidgets import QTreeWidgetItem, QTreeWidget, QLineEdit, QFormLayout

class VariableDev(QTreeWidgetItem):

    def __init__(self,*, top, parent, dev, noExpand):
        QTreeWidgetItem.__init__(self,parent)
        self._top      = top
        self._parent   = parent
        self._dev      = dev
        self._children = []
        self._dummy    = None

        self._path = 'rogue://{}:{}/{}/name'.format(self._top._addr,self._top._port,self._dev.path)

        w = PyDMLabel(parent=None, init_channel=self._path)
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
            self._dummy = None
            self.setExpanded(True)
            self._setup(False)
        else:
            self._dummy = QTreeWidgetItem(self) # One dummy item to add expand control
            self.setExpanded(False)

    def _setup(self,noExpand):

        # First create variables
        for key,val in self._dev.variablesByGroup(incGroups=self._top._incGroups,
                                                  excGroups=self._top._excGroups).items():

            self._children.append(VariableHolder(top=self._top, parent=self, variable=val))

        # Then create devices
        for key,val in self._dev.devicesByGroup(incGroups=self._top._incGroups,
                                                excGroups=self._top._excGroups).items():

            self._children.append(VariableDev(top=self._top, parent=self, dev=val, noExpand=noExpand))

    def _expand(self):
        if self._dummy is None:
            return

        self.removeChild(self._dummy)
        self._dummy = None
        self._setup(True)

class VariableHolder(QTreeWidgetItem):

    def __init__(self,*,top,parent,variable):
        QTreeWidgetItem.__init__(self,parent)
        self._top    = top
        self._parent = parent
        self._var    = variable

        self._path = 'rogue://{}:{}/{}'.format(self._top._addr,self._top._port,self._var.path)

        w = PyDMLabel(parent=None, init_channel=self._path + '/name')
        w.showUnits             = False
        w.precisionFromPV       = False
        w.alarmSensitiveContent = False
        w.alarmSensitiveBorder  = True

        self._top._tree.setItemWidget(self,0,w)
        self.setToolTip(0,self._var.description)

        self.setText(1,self._var.mode)
        self.setText(2,self._var.typeStr)

        self.setToolTip(0,self._var.description)

        if self._var.disp == 'enum' and self._var.enum is not None and self._var.mode != 'RO':
            w = PyDMEnumComboBox(parent=None, init_channel=self._path)
            w.alarmSensitiveContent = False
            w.alarmSensitiveBorder  = True

        elif self._var.minimum is not None and self._var.maximum is not None and self._var.disp == '{}' and self._var.mode != 'RO':
            w = PyDMSpinbox(parent=None, init_channel=self._path)
            w.precision             = 0
            w.showUnits             = False
            w.precisionFromPV       = False
            w.alarmSensitiveContent = False
            w.alarmSensitiveBorder  = True
            w.showStepExponent      = False

        else:
            self._path += '/disp'
            w = PyDMLineEdit(parent=None, init_channel=self._path)
            w.showUnits             = False
            w.precisionFromPV       = True
            w.alarmSensitiveContent = False
            w.alarmSensitiveBorder  = True
            #w.displayFormat         = 'String'

        self._top._tree.setItemWidget(self,3,w)

        if self._var.units:
            self.setText(4,str(self._var.units))


class VariableTree(PyDMFrame):
    def __init__(self, parent=None, init_channel=None, incGroups=None, excGroups=['Hidden']):
        PyDMFrame.__init__(self, parent, init_channel)

        self._client = None
        self._node   = None

        self._incGroups = incGroups
        self._excGroups = excGroups
        self._tree      = None
        self._addr      = None
        self._port      = None
        self._children  = []

    def connection_changed(self, connected):
        build = self._connected != connected and connected == True
        super(VariableTree, self).connection_changed(connected)

        if not build: return

        self._addr, self._port, path, mode = parseAddress(self.channel)

        self._client = VirtualClient(self._addr, self._port)
        self._node   = self._client.root.getNode(path)

        vb = QVBoxLayout()
        self.setLayout(vb)

        self._tree = QTreeWidget()
        vb.addWidget(self._tree)

        self._tree.setColumnCount(5)
        self._tree.setHeaderLabels(['Variable','Mode','Type','Value','Units'])

        self._tree.itemExpanded.connect(self._expandCb)

        hb = QHBoxLayout()
        vb.addLayout(hb)

        if self._node == self._client.root:
            hb.addWidget(PyDMPushButton(label='Read All',
                                        pressValue=True,
                                        init_channel='rogue://{}:{}/root.ReadAll'.format(self._addr,self._port)))
        else:
            hb.addWidget(PyDMPushButton(label='Read Recursive',
                                        pressValue=True,
                                        init_channel='rogue://{}:{}/{}.ReadDevice'.format(self._addr,self._port,self._node.path)))


        self.setUpdatesEnabled(False)
        self._children.append(VariableDev(top=self, parent=self._tree, dev=self._node, noExpand=False))
        self.setUpdatesEnabled(True)

    @Slot(QTreeWidgetItem)
    def _expandCb(self,item):
        self.setUpdatesEnabled(False)
        item._expand()

        self._tree.setColumnWidth(0,250)
        self._tree.setColumnWidth(1,50)
        self._tree.setColumnWidth(2,75)
        self._tree.setColumnWidth(3,200)
        self._tree.setColumnWidth(4,50)

        self.setUpdatesEnabled(True)

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

