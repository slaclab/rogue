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
from qtpy.QtCore import Qt, Property, QObject, Q_ENUMS, Slot
from qtpy.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy, QWidget, QGridLayout, QTreeWidgetItem, QTreeWidget

class VariableDev(QObject):

    def __init__(self,*, top, parent, dev, noExpand):
        QObject.__init__(self)
        self._top      = top
        self._parent   = parent
        self._dev      = dev
        self._children = []

        self._widget = QTreeWidgetItem(parent)
        self._widget.setText(0,self._dev.name)

        if self._top._node == dev:
            self._parent.addTopLevelItem(self._widget)

        if (not noExpand) and self._dev.expand:
            self._dummy = None
            self._widget.setExpanded(True)
            self.setup(False)
        else:
            self._dummy = QTreeWidgetItem(self._widget) # One dummy item to add expand control
            self._widget.setExpanded(False)
            self._top._tree.itemExpanded.connect(self.expandCb)

    @Slot()
    def expandCb(self):
        if self._dummy is None or not self._widget.isExpanded():
            return

        self._widget.removeChild(self._dummy)
        self._dummy = None
        self.setup(True)

    def setup(self,noExpand):

        # First create variables
        for key,val in self._dev.variablesByGroup(incGroups=self._top._incGroups,
                                                  excGroups=self._top._excGroups).items():
            path = 'rogue://{}:{}/{}'.format(self._top._addr,self._top._port,val.path)

            item = QTreeWidgetItem(self._widget)
            item.setText(0,val.name)
            item.setText(1,val.mode)
            item.setText(2,val.typeStr)

            if val.units:
                item.setText(4,str(val.units))

            #alarm = QLineEdit()
            #alarm.setReadOnly(True)
            #alarm.setText('None')
            #if val.hasAlarm:
                #self._tree.setItemWidget(self._item,5,self._alarm)

            if val.disp == 'enum' and val.enum is not None and val.mode != 'RO':
                w = PyDMEnumComboBox(parent=None, init_channel=path + '/True')

                for k,v in val.enum.items():
                    w.addItem(v)

            elif val.minimum is not None and val.maximum is not None and \
                 val.disp == '{}' and val.mode != 'RO':

                w = PyDMSpinbox(parent=None, init_channel=path)
                w.setMinimum(val.minimum)
                w.setMaximum(val.maximum)

            else:
                w = PyDMLineEdit(parent=None, init_channel=path + '/True')

            if val.mode == 'RO':
                w.setReadOnly(True)

            self._top._tree.setItemWidget(item,3,w)

        # Then create devices
        for key,val in self._dev.devicesByGroup(incGroups=self._top._incGroups,
                                                excGroups=self._top._excGroups).items():

            self._children.append(VariableDev(top=self._top,
                                              parent=self._widget,
                                              dev=val,
                                              noExpand=noExpand))

        for i in range(0,4):
            self._top._tree.resizeColumnToContents(i)


class VariableTree(PyDMFrame):
    def __init__(self, parent=None, init_channel=None):
        PyDMFrame.__init__(self, parent, init_channel)

        self._client = None
        self._node   = None

        self._rawPath   = None
        self._incGroups = None
        self._excGroups = None
        self._tree      = None
        self._addr      = None
        self._port      = None
        self._children  = []

    def _build(self):
        if (not utilities.is_pydm_app()) or self._rawPath is None:
            return

        self._addr, self._port, path, disp = ParseAddress(self._rawPath)

        self._client = pyrogue.interfaces.VirtualClient(self._addr, self._port)


        print("Path={}".format(path))
        self._node = self._client.root.getNode(path)
        print("Node={}".format(self._node))

        vb = QVBoxLayout()
        self.setLayout(vb)
        self._tree = QTreeWidget()
        vb.addWidget(self._tree)

        self._tree.setColumnCount(2)
        self._tree.setHeaderLabels(['Variable','Mode','Type','Value','Units', 'Alarm', ''])

        hb = QHBoxLayout()
        vb.addLayout(hb)

        pb = PyDMPushButton(label='Read',pressValue=1,
                            init_channel='rogue://{}:{}/root.ReadAll'.format(self._addr,self._port))

        hb.addWidget(pb)

        self._children.append(VariableDev(top=self,
                                          parent=self._tree,
                                          dev=self._node,
                                          noExpand=False))


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
        return self._rawPath

    @path.setter
    def path(self, newPath):
        self._rawPath = newPath
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

