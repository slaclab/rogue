#-----------------------------------------------------------------------------
# Title      : Command windows for GUI
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
from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem, QPushButton, QComboBox, QSpinBox
from PyQt5.QtWidgets import QLineEdit, QWidget, QVBoxLayout, QHBoxLayout
from PyQt5.QtCore    import QObject, pyqtSlot, QCoreApplication, QEvent

import pyrogue


class CommandDev(QObject):
    def __init__(self,*,tree,parent,dev,noExpand,top,incGroups,excGroups):
        QObject.__init__(self)
        self._parent   = parent
        self._tree     = tree
        self._dev      = dev
        self._children = []

        self._widget = QTreeWidgetItem(parent)
        self._widget.setText(0,self._dev.name)
        self._incGroups=incGroups
        self._excGroups=excGroups

        if top:
            self._parent.addTopLevelItem(self._widget)

        if (not noExpand) and self._dev.expand:
            self._dummy = None
            self._widget.setExpanded(True)
            self.setup(False)
        else:
            self._dummy = QTreeWidgetItem(self._widget) # One dummy item to add expand control
            self._widget.setExpanded(False)
            self._tree.itemExpanded.connect(self.expandCb)


    @pyqtSlot()
    def expandCb(self):
        if self._dummy is None or not self._widget.isExpanded():
            return

        self._tree.setUpdatesEnabled(False)
        self._widget.removeChild(self._dummy)
        self._dummy = None
        self.setup(True)
        self._tree.setUpdatesEnabled(True)

    def setup(self,noExpand):

        # First create commands
        for key,val in self._dev.commandsByGroup(incGroups=self._incGroups,excGroups=self._excGroups).items():
            self._children.append(CommandLink(tree=self._tree,
                                              parent=self._widget,
                                              command=val))
            QCoreApplication.processEvents()

        # Then create devices
        for key,val in self._dev.devicesByGroup(incGroups=self._incGroups,excGroups=self._excGroups).items():
            self._children.append(CommandDev(tree=self._tree,
                                             parent=self._widget,
                                             dev=val,
                                             noExpand=noExpand,
                                             top=False,
                                             incGroups=self._incGroups,
                                             excGroups=self._excGroups))

        for i in range(0,4):
            self._tree.resizeColumnToContents(i)


class CommandLink(QObject):
    """Bridge between the pyrogue tree and the display element"""

    def __init__(self,*,tree,parent,command):
        QObject.__init__(self)
        self._command = command
        self._parent  = parent
        self._tree    = tree
        self._widget  = None
        self._pb      = None

        self._item = QTreeWidgetItem(parent)
        self._item.setText(0,command.name)
        self._item.setText(1,command.typeStr)

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
                self._widget.installEventFilter(self)

            elif self._command.minimum is not None and self._command.maximum is not None:
                self._widget = QSpinBox()
                self._widget.setMinimum(self._command.minimum)
                self._widget.setMaximum(self._command.maximum)
                self._widget.setValue(self._command.value())
                self._widget.installEventFilter(self)

            else:
                self._widget = QLineEdit()
                self._widget.setText(self._command.valueDisp())

            self._tree.setItemWidget(self._item,3,self._widget)

    @pyqtSlot()
    def execPressed(self):
        if self._widget is not None:
            value = str(self._widget.text())
        else:
            value=None

        try:
            if self._command.arg:
                self._command(self._command.parseDisp(value))
            else:
                self._command()
        except Exception as msg:
            print(f"Got Exception: {msg}")

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Wheel:
            return True
        else:
            return False


class CommandWidget(QWidget):
    def __init__(self, *, parent=None):
        super(CommandWidget, self).__init__(parent)

        self.roots = []
        self._children = []

        vb = QVBoxLayout()
        self.setLayout(vb)
        self.tree = QTreeWidget()
        vb.addWidget(self.tree)

        self.tree.setColumnCount(2)
        self.tree.setHeaderLabels(['Command','Base','Execute','Arg'])

        hb = QHBoxLayout()
        vb.addLayout(hb)

        self.devTop = None

    @pyqtSlot(pyrogue.Root,list,list)
    @pyqtSlot(pyrogue.interfaces.VirtualNode,list,list)
    def addTree(self,root,incGroups,excGroups):
        self.roots.append(root)
        self._children.append(CommandDev(tree=self.tree,
                                         parent=self.tree,
                                         dev=root,
                                         noExpand=False,
                                         top=True,
                                         incGroups=incGroups,
                                         excGroups=excGroups))
