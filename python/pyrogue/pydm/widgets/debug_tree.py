#-----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
#-----------------------------------------------------------------------------
#  Description:
#       PyRogue PyDM Debug Tree Widget
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
from pyrogue.pydm.data_plugins.rogue_plugin import nodeFromAddress
from pyrogue.pydm.widgets import PyRogueLineEdit

from pydm.widgets.frame import PyDMFrame
from pydm.widgets import PyDMLabel, PyDMSpinbox, PyDMPushButton, PyDMEnumComboBox

from qtpy.QtCore import Property, Slot, QEvent, Qt, QPoint
from qtpy.QtWidgets import QVBoxLayout, QHBoxLayout, QHeaderView
from qtpy.QtWidgets import QTreeWidgetItem, QTreeWidget, QLabel
from qtpy.QtGui import QFontMetrics, QGuiApplication

class Col:
    """
    Column indices
    """
    Node    = 0
    Mode    = 1
    Type    = 2
    Offset  = 3
    Value   = 4
    Command = 5

    NumCols = 6
    ColumnNames =  ['Node', 'Mode', 'Type', 'ByteOffset [BitRange]', 'Value', 'Command']
    ColumnWidths = [ 300,    50,     75,     100,                400,     75]       # Default column widths



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

        w = PyDMLabel(parent=None, init_channel=self._path + '/name')
        w.showUnits             = False
        w.precisionFromPV       = False
        w.alarmSensitiveContent = False
        w.alarmSensitiveBorder  = False

        self._top._tree.setItemWidget(self, Col.Node, w)
        self.setToolTip(Col.Node, self._dev.description)

        self._top._tree.setItemWidget(self, Col.Offset, QLabel(f'0x{self._dev.offset:X}', parent=None))

        w = PyDMPushButton(
            label='Read',
            pressValue=True,
            init_channel=self._path + '.ReadDevice')

        self._top._tree.setItemWidget(self, Col.Command, w)


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

        self._top._tree.setItemWidget(self, Col.Node, self._lab)
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

def makeVariableViewWidget(parent):
    if parent._var.isCommand and not parent._var.arg:
        w = PyDMPushButton(label='Exec',
                           pressValue=1,
                           init_channel=parent._path + '/disp')

    elif parent._var.disp == 'enum' and parent._var.enum is not None and (parent._var.mode != 'RO' or parent._var.isCommand) and parent._var.typeStr != 'list':
        w = PyDMEnumComboBox(parent=None, init_channel=parent._path)
        w.alarmSensitiveContent = False
        w.alarmSensitiveBorder  = True
        w.installEventFilter(parent._top)

    else:
        w = PyRogueLineEdit(parent=None, init_channel=parent._path + '/disp')

    return w


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

        w = PyDMLabel(parent=None, init_channel=self._path + '/name')
        w.showUnits             = False
        w.precisionFromPV       = False

        w.alarmSensitiveContent = False
        w.alarmSensitiveBorder  = True

        fm = QFontMetrics(w.font())
        label = self._path.split('.')[-1]
        width = int(fm.width(label) * 1.1)

        rightEdge = width + (self._top._tree.indentation() * self._depth)

        if rightEdge > self._top._colWidths[0]:
            self._top._colWidths[0] = rightEdge

        self._top._tree.setItemWidget(self, Col.Node, w)
        self.setToolTip(Col.Node, self._var.description)

        self.setText(Col.Mode, self._var.mode)
        self.setText(Col.Type, f'{self._var.typeStr}   ') # Pad to look nicer
        if hasattr(self._var, 'offset') and hasattr(self._var, 'bitOffset') and hasattr(self._var, 'bitSize'):
            bo = self._var.bitOffset[0]
            self.setText(Col.Offset, f'0x{self._var.offset:X} [{bo+self._var.bitSize[0]-1}:{bo}]')
        self.setToolTip(Col.Node,self._var.description)

        w = makeVariableViewWidget(self)

        if self._var.isCommand:
            self._top._tree.setItemWidget(self, Col.Command,w)
            width = fm.width('0xAAAAAAAA    ')
            if width > self._top._colWidths[Col.Command]:
                self._top._colWidths[Col.Command] = width
        else:
            self._top._tree.setItemWidget(self,Col.Value,w)
            width = fm.width('0xAAAAAAAA    ')
            if width > self._top._colWidths[Col.Value]:
                self._top._colWidths[Col.Value] = width


class DebugTree(PyDMFrame):
    def __init__(self, parent=None, init_channel=None, incGroups=None, excGroups=['Hidden']):
        PyDMFrame.__init__(self, parent, init_channel)

        self._node = None
        self._path = None

        self._incGroups = incGroups
        self._excGroups = excGroups
        self._tree      = None

        self._colWidths = Col.ColumnWidths.copy()

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

        self._tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self._tree.customContextMenuRequested.connect(self._openContextMenu)

        self._tree.setColumnCount(Col.NumCols)
        self._tree.setHeaderLabels(Col.ColumnNames)
        header = self._tree.header()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(Col.Value, QHeaderView.Stretch)

        self._tree.setColumnHidden(Col.Offset, True)

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

    def _copyPath(self, checked, point):
        item = self._tree.itemAt(point)
        if item is not None and hasattr(item, '_path'):
            QGuiApplication.clipboard().setText(item._path)

    def _copyColumnText(self, checked, point: QPoint):
        item = self._tree.itemAt(point)
        if item is not None:
            QGuiApplication.clipboard().setText(
                item.text(self._tree.columnAt(point.x()))
            )

    def _hideColumn(self, checked, point: QPoint):
        self._tree.setColumnHidden(self._tree.columnAt(point.x()), True)

    def _toggleColumn(self, checked, col: int):
        self._tree.setColumnHidden(col, not checked)

    def _showAllCols(self, checked):
        for i in range(Col.NumCols):
            self._tree.setColumnHidden(i, False)

    def _openContextMenu(self, point):
        # Generate base context menu from PyDM. We can't override generate_context_menu because
        # it doesn't give us the point where the mouse right clicked, which we need to implement the 'copy' actions
        menu = super(DebugTree, self).generate_context_menu()
        menu.addSeparator()
        menu.addAction('&Copy').triggered.connect(
            lambda c : self._copyColumnText(c, point)
        )
        menu.addAction('Copy Path').triggered.connect(
            lambda c : self._copyPath(c, point)
        )
        menu.addSeparator()
        menu.addAction('&Hide Column').triggered.connect(
            lambda c : self._hideColumn(c, point)
        )
        menu.addAction('Show All Columns').triggered.connect(self._showAllCols)

        menu.addSection('Columns')
        for i in range(Col.NumCols):
            a = menu.addAction(Col.ColumnNames[i])
            a.setCheckable(True)
            a.setChecked(not self._tree.isColumnHidden(i))
            a.triggered.connect(
                lambda c, i=i: self._toggleColumn(c, int(i))
            )

        menu.exec_(self._tree.viewport().mapToGlobal(point))

    @Slot(QTreeWidgetItem)
    def _expandCb(self,item):
        self.setUpdatesEnabled(False)
        item._expand()
        self._tree.setColumnWidth(Col.Node, self._colWidths[Col.Node])
        self._tree.setColumnWidth(Col.Offset, self._colWidths[Col.Offset])
        self._tree.resizeColumnToContents(Col.Mode)
        self._tree.resizeColumnToContents(Col.Type)
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
