#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to 
# the license terms in the LICENSE.txt file found in the top-level directory 
# of this distribution and at: 
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html. 
# No part of the rogue software platform, including this file, may be 
# copied, modified, propagated, or distributed except according to the terms 
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

#from os import path
from pydm.widgets.frame import PyDMFrame
from pydm.widgets import PyDMLineEdit, PyDMSpinbox, PyDMPushButton, PyDMEnumComboBox
#from pydm import widgets
from pydm import utilities
from pyrogue.pydm.data_plugins.rogue_plugin import ParseAddress
import pyrogue.interfaces
from qtpy.QtCore import Qt, Property, QObject, Q_ENUMS, Slot, QPoint
from qtpy.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy, QMenu, QDialog, QPushButton
from qtpy.QtWidgets import QWidget, QGridLayout, QTreeWidgetItem, QTreeWidget, QLineEdit, QFormLayout

class VariableDev(QTreeWidgetItem):

    def __init__(self,*, top, parent, dev, noExpand):
        QTreeWidgetItem.__init__(self,parent)
        self._top      = top
        self._parent   = parent
        self._dev      = dev
        self._children = []

        self.setText(0,self._dev.name)
        self.setToolTip(0,self._dev.description)

        if self._top._node == dev:
            self._parent.addTopLevelItem(self)

        if (not noExpand) and self._dev.expand:
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

        for i in range(0,5):
            self._top._tree.resizeColumnToContents(i)

    def _expand(self):
        if self._dummy is None:
            return

        self.removeChild(self._dummy)
        self._dummy = None
        self._setup(True)

    def _menu(self,pos):
        menu = QMenu()

        dev_info = menu.addAction('Device Information')
        read_recurse = menu.addAction('Read Recursive')
        write_recurse = menu.addAction('Write Recursive')
        read_device = menu.addAction('Read Device')
        write_device = menu.addAction('Write Device')

        action = menu.exec_(self._top._tree.mapToGlobal(pos))

        if action == dev_info:
            self._infoDialog()
        elif action == read_recurse:
            self._dev.ReadDevice(True)
        elif action == write_recurse:
            self._dev.WriteDevice(True)
        elif action == read_device:
            self._dev.ReadDevice(False)
        elif action == write_device:
            self._dev.WriteDevice(False)

    def _infoDialog(self):

        attrs = ['name', 'path', 'description', 'hidden', 'groups']

        msgBox = QDialog()
        msgBox.setWindowTitle("Device Information For {}".format(self._dev.name))
        msgBox.setMinimumWidth(400)

        vb = QVBoxLayout()
        msgBox.setLayout(vb)

        fl = QFormLayout()
        fl.setRowWrapPolicy(QFormLayout.DontWrapRows)
        fl.setFormAlignment(Qt.AlignHCenter | Qt.AlignTop)
        fl.setLabelAlignment(Qt.AlignRight)
        vb.addLayout(fl)

        pb = QPushButton('Close')
        pb.pressed.connect(msgBox.close)
        vb.addWidget(pb)

        for a in attrs:
            le = QLineEdit()
            le.setReadOnly(True)
            le.setText(str(getattr(self._dev,a)))
            fl.addRow(a,le)

        msgBox.exec()


class VariableHolder(QTreeWidgetItem):

    def __init__(self,*,top,parent,variable):
        QTreeWidgetItem.__init__(self,parent)
        self._top    = top
        self._parent = parent
        self._var    = variable

        self._path = 'rogue://{}:{}/{}'.format(self._top._addr,self._top._port,self._var.path)

        self.setText(0,self._var.name)
        self.setText(1,self._var.mode)
        self.setText(2,self._var.typeStr)

        self.setToolTip(0,self._var.description)

        if self._var.disp == 'enum' and self._var.enum is not None and self._var.mode != 'RO':
            self._path += '/True'
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
            self._path += '/True'
            w = PyDMLineEdit(parent=None, init_channel=self._path)
            w.showUnits             = False
            w.precisionFromPV       = True
            w.alarmSensitiveContent = False
            w.alarmSensitiveBorder  = True
            #w.displayFormat         = 'String'

        self._top._tree.setItemWidget(self,3,w)

        if self._var.units:
            self.setText(4,str(self._var.units))

    def _menu(self,pos):
        menu = QMenu()
        read_variable  = None
        write_variable = None

        var_info = menu.addAction('Variable Information')

        if self._var.mode != 'WO':
            read_variable = menu.addAction('Read Variable')
        if self._var.mode != 'RO':
            write_variable = menu.addAction('Write Variable')

        action = menu.exec_(self._top._tree.mapToGlobal(pos))

        if action == var_info:
            self._infoDialog()
        elif action == read_variable:
            self._var.get()
        elif action == write_variable:
            self._var.write()

    def _infoDialog(self):

        attrs = ['name', 'path', 'description', 'hidden', 'groups', 'enum', 
                 'typeStr', 'disp', 'precision', 'mode', 'units', 'minimum', 
                 'maximum', 'lowWarning', 'lowAlarm', 'highWarning', 
                 'highAlarm', 'alarmStatus', 'alarmSeverity', 'pollInterval']

        if self._var.isinstance(pyrogue.RemoteVariable):
            attrs += ['offset', 'bitSize', 'bitOffset', 'verify', 'varBytes']

        msgBox = QDialog()
        msgBox.setWindowTitle("Variable Information For {}".format(self._var.name))
        msgBox.setMinimumWidth(400)

        vb = QVBoxLayout()
        msgBox.setLayout(vb)

        fl = QFormLayout()
        fl.setRowWrapPolicy(QFormLayout.DontWrapRows)
        fl.setFormAlignment(Qt.AlignHCenter | Qt.AlignTop)
        fl.setLabelAlignment(Qt.AlignRight)
        vb.addLayout(fl)

        pb = QPushButton('Close')
        pb.pressed.connect(msgBox.close)
        vb.addWidget(pb)

        for a in attrs:
            le = QLineEdit()
            le.setReadOnly(True)
            le.setText(str(getattr(self._var,a)))
            fl.addRow(a,le)

        le = QLineEdit()
        le.setReadOnly(True)
        le.setText(self._path)
        fl.addRow('PyDM Path',le)

        msgBox.exec()


class VariableTree(PyDMFrame):
    def __init__(self, parent=None, init_channel=None):
        PyDMFrame.__init__(self, parent, init_channel)

        self._client = None
        self._node   = None

        self._lchannel  = init_channel
        self._incGroups = None
        self._excGroups = ['Hidden']
        self._tree      = None
        self._addr      = None
        self._port      = None
        self._children  = []

    def _build(self):
        if (not utilities.is_pydm_app()) or self._lchannel is None:
            return

        self._addr, self._port, path, disp = ParseAddress(self._lchannel)

        self._client = pyrogue.interfaces.VirtualClient(self._addr, self._port)
        self._node   = self._client.root.getNode(path)

        vb = QVBoxLayout()
        self.setLayout(vb)
        self._tree = QTreeWidget()
        vb.addWidget(self._tree)

        self._tree.setColumnCount(5)
        self._tree.setHeaderLabels(['Variable','Mode','Type','Value','Units'])

        self._tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self._tree.customContextMenuRequested.connect(self._openMenu)

        self._tree.itemExpanded.connect(self._expandCb)

        hb = QHBoxLayout()
        vb.addLayout(hb)

        if self._node == self._client.root:
            chan = 'rogue://{}:{}/root.ReadAll'.format(self._addr,self._port)
        else:
            chan = 'rogue://{}:{}/{}.ReadDevice'.format(self._addr,self._port,self._node.path)

        pb = PyDMPushButton(label='Read',pressValue=1,init_channel=chan)

        hb.addWidget(pb)

        self._children.append(VariableDev(top=self, parent=self._tree, dev=self._node, noExpand=False))

    @Slot(QTreeWidgetItem)
    def _expandCb(self,item):
        item._expand()

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

    @Property(str)
    def path(self):
        return self._lchannel

    @path.setter
    def path(self, newPath):
        self._lchannel = newPath
        self._build()


#    def __init__(self, parent=None, args=None, macros=None):
#        super(RogueWidget, self).__init__(parent=parent, args=args, macros=None)
#        print("Args = {}".format(args))
#        print("Macros = {}".format(macros))
#
#    def ui_filename(self):
#        # Point to our UI file
#        return 'test_widget.ui'
#
#    def ui_filepath(self):
#        # Return the full path to the UI file
#        return path.join(path.dirname(path.realpath(__file__)), self.ui_filename())

