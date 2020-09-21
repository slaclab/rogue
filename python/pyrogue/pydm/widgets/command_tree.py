#-----------------------------------------------------------------------------
# Title      : PyRogue PyDM Command Tree Widget
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

from pydm.widgets.frame import PyDMFrame
from pydm.widgets import PyDMLabel, PyDMPushButton
from pyrogue.pydm.data_plugins.rogue_plugin import nodeFromAddress
from qtpy.QtCore import Qt, Property, Slot, QEvent
from qtpy.QtWidgets import QVBoxLayout, QComboBox, QLabel
from qtpy.QtWidgets import QTreeWidgetItem, QTreeWidget, QLineEdit
from qtpy.QtGui import QFontMetrics

class CommandDev(QTreeWidgetItem):

    def __init__(self,*, path, top, parent, dev, noExpand):
        QTreeWidgetItem.__init__(self,parent)
        self._top      = top
        self._parent   = parent
        self._dev      = dev
        self._dummy    = None
        self._path     = path
        self._groups   = {}

        if isinstance(parent,CommandDev):
            self._depth = parent._depth+1
        else:
            self._depth = 1

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

            if val.guiGroup is not None:
                if val.guiGroup not in self._groups:
                    self._groups[val.guiGroup] = CommandGroup(path=self._path,
                                                              top=self._top,
                                                              parent=self,
                                                              name=val.guiGroup)

                self._groups[val.guiGroup].addNode(val)

            else:
                CommandHolder(path=self._path + '.' + val.name,
                              top=self._top,
                              parent=self,
                              command=val)

        # Then create devices
        for key,val in self._dev.devicesByGroup(incGroups=self._top._incGroups,
                                                excGroups=self._top._excGroups).items():

            if val.guiGroup is not None:
                if val.guiGroup not in self._groups:
                    self._groups[val.guiGroup] = CommandGroup(path=self._path,
                                                              top=self._top,
                                                              parent=self,
                                                              name=val.guiGroup)

                self._groups[val.guiGroup].addNode(val)

            else:
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


class CommandGroup(QTreeWidgetItem):

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
                CommandDev(path=self._path + '.' + n.name,
                           top=self._top,
                           parent=self,
                           dev=n,
                           noExpand=True)

            elif n.isVariable:
                CommandHolder(path=self._path + '.' + n.name,
                              top=self._top,
                              parent=self,
                              command=n)

    def _expand(self):
        if self._dummy is None:
            return

        self.removeChild(self._dummy)
        self._dummy = None
        self._setup()

    def addNode(self,node):
        self._list.append(node)


class CommandHolder(QTreeWidgetItem):

    def __init__(self,*,path,top,parent,command):
        QTreeWidgetItem.__init__(self,parent)
        self._top    = top
        self._parent = parent
        self._cmd    = command
        self._path   = path
        self._widget = None
        self._value  = self._cmd.valueDisp()
        self._depth  = parent._depth+1

        if self._value is None:
            self._value = ''

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
        self.setToolTip(0,self._cmd.description)

        self.setText(1,self._cmd.typeStr)

        # This needs to be changed when pydm is updated. In the future the primary
        # channel interface will be the input widget, with the button generating a
        # update of the channel.
        self._btn = PyDMPushButton(label='Exec',
                                   pressValue=self._value,
                                   init_channel=self._path + '/disp')
        self._btn.setToolTip(self._cmd.description)

        self._top._tree.setItemWidget(self,2,self._btn)

        if self._cmd.arg:

            if self._cmd.disp == 'enum' and self._cmd.enum is not None:
                self._widget = QComboBox()
                for i in self._cmd.enum:
                    self._widget.addItem(self._cmd.enum[i])

                self._value = self._cmd.valueDisp()
                self._widget.setCurrentIndex(self._widget.findText(self._value))
                self._widget.setToolTip(self._cmd.description)

                self._widget.currentTextChanged.connect(self._argChanged)
                self._widget.installEventFilter(self._top)

            else:
                self._widget = QLineEdit()

                self._value = self._cmd.valueDisp()
                self._widget.setText(self._value)
                self._widget.setToolTip(self._cmd.description)

                self._widget.textChanged.connect(self._argChanged)

            self._top._tree.setItemWidget(self,3,self._widget)

            width = fm.width('0xAAAAAAAA    ')

            if width > self._top._colWidths[3]:
                self._top._colWidths[3] = width


    def _argChanged(self,value):
        self._btn.pressValue = value


class CommandTree(PyDMFrame):
    def __init__(self, parent=None, init_channel=None, incGroups=None, excGroups=['Hidden']):
        PyDMFrame.__init__(self, parent, init_channel)

        self._node = None
        self._path = None

        self._incGroups = incGroups
        self._excGroups = excGroups
        self._tree      = None
        self._children  = []

        self._colWidths = [250,50,50,200]

    def connection_changed(self, connected):
        build = (self._node is None) and (self._connected != connected and connected is True)
        super(CommandTree, self).connection_changed(connected)

        if not build:
            return

        self._node = nodeFromAddress(self.channel)
        self._path = self.channel

        vb = QVBoxLayout()
        self.setLayout(vb)

        self._tree = QTreeWidget()
        vb.addWidget(self._tree)

        self._tree.setColumnCount(3)
        self._tree.setHeaderLabels(['Command','Base','Execute','Arg'])

        self._tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self._tree.customContextMenuRequested.connect(self._openMenu)

        self._tree.itemExpanded.connect(self._expandCb)

        self.setUpdatesEnabled(False)
        CommandDev(path=self._path,
                   top=self,
                   parent=self._tree,
                   dev=self._node,
                   noExpand=False)
        self.setUpdatesEnabled(True)

    @Slot(QTreeWidgetItem)
    def _expandCb(self,item):
        self.setUpdatesEnabled(False)
        item._expand()

        self._tree.setColumnWidth(0,self._colWidths[0])
        self._tree.resizeColumnToContents(1)
        self._tree.resizeColumnToContents(2)
        self._tree.setColumnWidth(3,self._colWidths[3])

        self.setUpdatesEnabled(True)

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

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Wheel:
            return True
        else:
            return False
