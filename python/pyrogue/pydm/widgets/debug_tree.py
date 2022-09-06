#-----------------------------------------------------------------------------
# Title      : PyRogue PyDM Debug Tree Widget
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
from pydm.widgets import PyDMLabel, PyDMSpinbox, PyDMPushButton, PyDMEnumComboBox
from pyrogue.pydm.data_plugins.rogue_plugin import nodeFromAddress
from pyrogue.pydm.widgets import PyRogueLineEdit
from qtpy.QtCore import Property, Slot, QEvent, Qt
from qtpy.QtWidgets import QVBoxLayout, QHBoxLayout, QGridLayout, QWidget
from qtpy.QtWidgets import QTreeWidgetItem, QTreeWidget, QLabel
from qtpy.QtGui import QFontMetrics

class deviceLabelReadAll(QWidget):
    def __init__(self, parent, init_channel):
        QWidget.__init__(self, parent)
        label = PyDMLabel(parent=None, init_channel=init_channel + '/name')
        label.showUnits             = False
        label.precisionFromPV       = False
        label.alarmSensitiveContent = False
        label.alarmSensitiveBorder  = False
        readAll = PyDMPushButton(label='Read Device',
                                pressValue=True,
                                init_channel=init_channel + '.ReadDevice')
        grid = QGridLayout()
        grid.addWidget(label, 0, 0)
        grid.addWidget(readAll, 0, 1)
        grid.setVerticalSpacing(0)
        grid.setHorizontalSpacing(0)
        grid.setContentsMargins(0, 0, 0, 0)
        self.setLayout(grid)

class DebugDev(QTreeWidgetItem):

    def __init__(self,*, path, top, parent, dev, noExpand):
        QTreeWidgetItem.__init__(self,parent)
        self._top      = top
        self._parent   = parent
        self._dev      = dev
        self._dummy    = None
        self._path     = path
        self._groups   = {}

        if isinstance(parent,DebugDev):
            self._depth = parent._depth+1
        else:
            self._depth = 1

        w = deviceLabelReadAll(parent=None, init_channel=self._path)
        # w = PyDMLabel(parent=None, init_channel=self._path + '/name')
        # w.showUnits             = False
        # w.precisionFromPV       = False
        # w.alarmSensitiveContent = False
        # w.alarmSensitiveBorder  = False

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

        # Get dictionary of variables followed by commands
        lst = self._dev.variablesByGroup(incGroups=self._top._incGroups,
                                         excGroups=self._top._excGroups)


        lst.update(self._dev.commandsByGroup(incGroups=self._top._incGroups,
                                             excGroups=self._top._excGroups))

        # First create variables/commands
        for key,val in lst.items():
            if val.guiGroup is not None:
                if val.guiGroup not in self._groups:
                    self._groups[val.guiGroup] = DebugGroup(path=self._path, top=self._top, parent=self, name=val.guiGroup)

                self._groups[val.guiGroup].addNode(val)

            else:
                DebugHolder(path=self._path + '.' + val.name, top=self._top, parent=self, variable=val)
        # Then create devices
        for key,val in self._dev.devicesByGroup(incGroups=self._top._incGroups, excGroups=self._top._excGroups).items():

            if val.guiGroup is not None:
                if val.guiGroup not in self._groups:
                    self._groups[val.guiGroup] = DebugGroup(path=self._path, top=self._top, parent=self, name=val.guiGroup)

                self._groups[val.guiGroup].addNode(val)

            else:
                DebugDev(path=self._path + '.' + val.name, top=self._top, parent=self, dev=val, noExpand=noExpand)

    def _expand(self):
        if self._dummy is None:
            return

        self.removeChild(self._dummy)
        self._dummy = None
        self._setup(True)


class DebugGroup(QTreeWidgetItem):

    def __init__(self,*, path, top, parent, name):
        QTreeWidgetItem.__init__(self,parent)
        self._top      = top
        self._parent   = parent
        self._name     = name
        self._dummy    = None
        self._path     = path
        self._list     = []
        self._depth    = parent._depth+1

        self._lab = QLabel(parent=None, text=self._name)

        self._top._tree.setItemWidget(self,0,self._lab)
        self._dummy = QTreeWidgetItem(self) # One dummy item to add expand control
        self.setExpanded(False)

    def _setup(self):

        # Create variables
        for n in self._list:
            if n.isDevice:
                DebugDev(path=self._path + '.' + n.name,
                         top=self._top,
                         parent=self,
                         dev=n,
                         noExpand=True)
            elif n.isVariable or n.isCommand:
                DebugHolder(path=self._path + '.' + n.name,
                            top=self._top,
                            parent=self,
                            variable=n)

    def _expand(self):
        if self._dummy is None:
            return

        self.removeChild(self._dummy)
        self._dummy = None
        self._setup()

    def addNode(self,node):
        self._list.append(node)

class overlayPyRogueLineEdit(QWidget):
    def __init__(self, parent, init_channel, units):
        QWidget.__init__(self, parent)
        lineEdit1 = PyRogueLineEdit(parent = parent, init_channel = init_channel)
        lineEdit2 = PyRogueLineEdit(parent = parent, init_channel = None)
        lineEdit1.precisionFromPV       = True
        lineEdit1.alarmSensitiveContent = False
        lineEdit1.alarmSensitiveBorder  = True
        lineEdit2.precisionFromPV       = True
        lineEdit2.alarmSensitiveContent = False
        lineEdit2.alarmSensitiveBorder  = True
        lineEdit1.setStyleSheet("* { background-color: rgba(0, 0, 0, 0); }")
        if units:
            lineEdit2.setText(str(units))
        else:
            lineEdit2.setText("")
        lineEdit2.set_opacity(0.7)
        lineEdit2.setAlignment(Qt.AlignRight)
        grid = QGridLayout()
        grid.addWidget(lineEdit2, 0, 0)
        grid.addWidget(lineEdit1, 0, 0)
        grid.setVerticalSpacing(0)
        grid.setHorizontalSpacing(0)
        grid.setContentsMargins(0, 0, 0, 0)
        self.setLayout(grid)

class overlayPyDMLabel(QWidget):
    def __init__(self, parent, init_channel, units):
        QWidget.__init__(self, parent)
        label1 = PyDMLabel(parent = parent, init_channel = init_channel)
        label2 = PyDMLabel(parent = parent, init_channel = None)
        label1.precisionFromPV       = True
        label1.alarmSensitiveContent = False
        label1.alarmSensitiveBorder  = True
        label2.precisionFromPV       = True
        label2.alarmSensitiveContent = False
        label2.alarmSensitiveBorder  = True
        label1.setStyleSheet("* { background-color: rgba(0, 0, 0, 0); }")
        if units:
            label2.setText(str(units))
        else:
            label2.setText("")
        label2.set_opacity(0.7)
        label2.setAlignment(Qt.AlignRight)
        grid = QGridLayout()
        grid.addWidget(label2, 0, 0)
        grid.addWidget(label1, 0, 0)
        grid.setVerticalSpacing(0)
        grid.setHorizontalSpacing(0)
        grid.setContentsMargins(0, 0, 0, 0)
        self.setLayout(grid)

class DebugHolder(QTreeWidgetItem):

    def __init__(self,*,path,top,parent,variable):
        QTreeWidgetItem.__init__(self,parent)
        self._top    = top
        self._parent = parent
        self._var    = variable
        self._path   = path
        self._depth  = parent._depth+1
        self._isCommand = False

        w = None
        if self._var.isCommand and not self._var.arg:
            w = PyDMPushButton(label=self._var.name,
                               pressValue=1,
                               init_channel=self._path + '/disp')
            self._isCommand = True
        else:
            w = PyDMLabel(parent=None, init_channel=self._path + '/name')
            w.showUnits             = False
            w.precisionFromPV       = False

        w.alarmSensitiveContent = False
        w.alarmSensitiveBorder  = True

        fm = QFontMetrics(w.font())
        width = int(fm.width(self._path.split('.')[-1]) * 1.1)

        rightEdge = width + (self._top._tree.indentation() * self._depth)

        if rightEdge > self._top._colWidths[0]:
            self._top._colWidths[0] = rightEdge

        self._top._tree.setItemWidget(self,0,w)
        self.setToolTip(0,self._var.description)

        self.setText(1,self._var.mode)
        self.setText(2,self._var.typeStr)
        self.setToolTip(0,self._var.description)
        if self._isCommand:
            return

        # if self._var.isCommand and not self._var.arg:

        #     w = PyDMPushButton(label='Exec',
        #                        pressValue=1,
        #                        init_channel=self._path + '/disp')


        if self._var.disp == 'enum' and self._var.enum is not None and (self._var.mode != 'RO' or self._var.isCommand) and self._var.typeStr != 'list':
            w = PyDMEnumComboBox(parent=None, init_channel=self._path)
            w.alarmSensitiveContent = False
            w.alarmSensitiveBorder  = True
            w.installEventFilter(self._top)

        elif self._var.minimum is not None and self._var.maximum is not None and self._var.disp == '{}' and (self._var.mode != 'RO' or self._var.isCommand):
            w = PyDMSpinbox(parent=None, init_channel=self._path)
            w.precision             = 0
            w.showUnits             = False
            w.precisionFromPV       = False
            w.alarmSensitiveContent = False
            w.alarmSensitiveBorder  = True
            w.showStepExponent      = False
            w.writeOnPress          = True
            w.installEventFilter(self._top)

        elif self._var.mode == 'RO' and not self._var.isCommand:
            w = overlayPyDMLabel(parent=None, init_channel=self._path + '/disp', units=self._var.units)
            # w.showUnits             = (self._var.units is not None)
            # w.unit_changed(self._var.units)
            # w.precisionFromPV       = True
            # w.alarmSensitiveContent = False
            # w.alarmSensitiveBorder  = True
        else:
            w = overlayPyRogueLineEdit(parent=None, init_channel=self._path + '/disp', units=self._var.units)
            # PyRogueLineEdit(parent=None, init_channel=self._path + '/disp')
            # w.precisionFromPV       = True
            # w.alarmSensitiveContent = False
            # w.alarmSensitiveBorder  = True
            # w.displayFormat         = 'String'

        # if self._var.isCommand:
        #     self._top._tree.setItemWidget(self,4,w)
        #     width = fm.width('0xAAAAAAAA    ')

        #     if width > self._top._colWidths[4]:
        #         self._top._colWidths[4] = width



        # else:
        self._top._tree.setItemWidget(self,3,w)
        width = fm.width('0xAAAAAAAA    ')

        if width > self._top._colWidths[3]:
            self._top._colWidths[3] = width

        # if self._var.units:
        #     self.setText(5,str(self._var.units))


class DebugTree(PyDMFrame):
    def __init__(self, parent=None, init_channel=None, incGroups=None, excGroups=['Hidden']):
        PyDMFrame.__init__(self, parent, init_channel)

        self._node = None
        self._path = None

        self._incGroups = incGroups
        self._excGroups = excGroups
        self._tree      = None

        self._colWidths = [250,50,75,200]
        self._expandedOnce = False

    def connection_changed(self, connected):
        build = (self._node is None) and (self._connected != connected and connected is True)
        super(DebugTree, self).connection_changed(connected)

        if not build:
            return

        self._node = nodeFromAddress(self.channel)
        self._path = self.channel

        vb = QVBoxLayout()
        self.setLayout(vb)

        self._tree = QTreeWidget()
        vb.addWidget(self._tree)

        self._tree.setColumnCount(4)
        self._tree.setHeaderLabels(['Node','Mode','Type','Value'])

        self._tree.itemExpanded.connect(self._expandCb)

        hb = QHBoxLayout()
        vb.addLayout(hb)

        if self._node.isinstance(pyrogue.Root):
            hb.addWidget(PyDMPushButton(label='Read All',
                                        pressValue=True,
                                        init_channel=self._path + '.ReadAll'))
        else:
            hb.addWidget(PyDMPushButton(label='Read Recursive',
                                        pressValue=True,
                                        init_channel=self._path + '.ReadDevice'))


        self.setUpdatesEnabled(False)
        DebugDev(path = self._path, top=self, parent=self._tree, dev=self._node, noExpand=False)
        self.setUpdatesEnabled(True)

    @Slot(QTreeWidgetItem)
    def _expandCb(self,item):
        if self._expandedOnce:
            self.setUpdatesEnabled(False)
            item._expand()
            self.setUpdatesEnabled(True)
        else:
            self._expandedOnce = True
            self.setUpdatesEnabled(False)
            item._expand()
            self._tree.setColumnWidth(0,self._colWidths[0])
            self._tree.resizeColumnToContents(1)
            self._tree.resizeColumnToContents(2)
            self._tree.setColumnWidth(3,self._colWidths[3])
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

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Wheel:
            return True
        else:
            return False
