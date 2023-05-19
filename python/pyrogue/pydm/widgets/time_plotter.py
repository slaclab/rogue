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
from pyrogue.pydm.data_plugins.rogue_plugin import nodeFromAddress
from pyrogue.pydm.widgets.debug_tree import makeVariableViewWidget

from pydm import Display
from pydm.widgets.frame import PyDMFrame
from pydm.widgets import PyDMLabel, PyDMPushButton
import pydm.widgets.timeplot as pwt

from qtpy import QtCore
from qtpy.QtCore import Property, Slot, QEvent
from qtpy.QtGui import QFontMetrics
from qtpy.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QTreeWidgetItem, QTreeWidget, QLabel,
    QGroupBox, QLineEdit, QPushButton, QScrollArea, QFrame, QWidget)

from pyqtgraph import ViewBox

from PyQt5.QtWidgets import QSplitter
from PyQt5.QtCore import Qt

import random


class DebugDev(QTreeWidgetItem):

    def __init__(self,main,*, path, top, parent, dev, noExpand):
        QTreeWidgetItem.__init__(self,parent)
        self._main=main
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


#         lst.update(self._dev.commandsByGroup(incGroups=self._top._incGroups,
#                                              excGroups=self._top._excGroups))

        # First create variables/commands
        for key,val in lst.items():

            if val.guiGroup is not None:
                if val.guiGroup not in self._groups:
                    self._groups[val.guiGroup] = DebugGroup(path=self._path, main=self._main, top=self._top, parent=self, name=val.guiGroup)

                self._groups[val.guiGroup].addNode(val)

            else:
                DebugHolder(main=self._main,path=self._path + '.' + val.name, top=self._top, parent=self, variable=val)

        # Then create devices
        for key,val in self._dev.devicesByGroup(incGroups=self._top._incGroups, excGroups=self._top._excGroups).items():

            if val.guiGroup is not None:
                if val.guiGroup not in self._groups:
                    self._groups[val.guiGroup] = DebugGroup(path=self._path, main=self._main, top=self._top, parent=self, name=val.guiGroup)

                self._groups[val.guiGroup].addNode(val)

            else:
                DebugDev(main = self._main,path=self._path + '.' + val.name, top=self._top, parent=self, dev=val, noExpand=noExpand)

    def _expand(self):
        if self._dummy is None:
            return

        self.removeChild(self._dummy)
        self._dummy = None
        self._setup(True)


class DebugGroup(QTreeWidgetItem):

    def __init__(self,main,*, path, top, parent, name):
        QTreeWidgetItem.__init__(self,parent)
        self._main = main
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
                DebugDev(main=self._main,
                         path=self._path + '.' + n.name,
                         top=self._top,
                         parent=self,
                         dev=n,
                         noExpand=True)

            elif n.isVariable or n.isCommand:
                DebugHolder(main=self._main,
                            path=self._path + '.' + n.name,
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


class DebugHolder(QTreeWidgetItem):

    def __init__(self,main,*,path,top,parent,variable):
        QTreeWidgetItem.__init__(self,parent)
        self._main   = main
        self._top    = top
        self._parent = parent
        self._var    = variable
        self._path   = path
        self._depth  = parent._depth+1

        # print(f'DebugHolder: {self._var=}, {self._var.name=}, {self._var.path=}, {self._var.pollInterval=}')

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

        w = makeVariableViewWidget(self)
        self._top._tree.setItemWidget(self, 1, w)

        pe = QLineEdit(parent=None)

        def _makeSetPoll(le):
            def _setPoll():
                print(self._var)
                print(le.text())
                self._var.setPollInterval(float(le.text()))
            return _setPoll

        pe.returnPressed.connect(_makeSetPoll(pe))
        pe.setText(str(self._var.pollInterval))

        self._top._tree.setItemWidget(self, 3, pe)
        #self.setText(3,str(self._var.pollInterval))
        # self.setText(4,str(self._var._value))


        def funcgen(str):
            def ret():
                #calls the button's toggle method, and also changes the state of DefaultTop so that the correct color will be used in the plot
                if w._state is True:
                    self._main.do_remove(str)
                else:
                    self._main.do_add(str)
                w.toggle()
            return ret

        f = funcgen(self._path)
        w = ToggleButton(main=self._main, state=False, path=self._path)
        w.setText('Add')
        w.clicked.connect(f)


        self._top._tree.setItemWidget(self,2,w)
        width = fm.width('0xAAAAAAAA    ')

        if width > self._top._colWidths[1]:
            self._top._colWidths[1] = width



class SelectionTree(PyDMFrame):
    def __init__(self, main, parent=None, init_channel=None, incGroups=None, excGroups=['Hidden']):
        PyDMFrame.__init__(self, parent, init_channel)

        self._main = main
        self._node = None
        self._path = None

        self._incGroups = incGroups
        self._excGroups = excGroups
        self._tree      = None

        self._colWidths = [250,50,150,50,50]

        print("Selection tree created")

    def connection_changed(self, connected):

        build = (self._node is None) and (self._connected != connected and connected is True)
        super(SelectionTree, self).connection_changed(connected)

        if not build:
            return

        self._node = nodeFromAddress(self.channel)
        self._path = self.channel

        vb = QVBoxLayout()
        self.setLayout(vb)

        self._tree = QTreeWidget()
        vb.addWidget(self._tree)

        self._tree.setColumnCount(4)
        self._tree.setHeaderLabels(['Node','Value','Plot','Poll Interval'])

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
        DebugDev(main = self._main, path = self._path, top=self, parent=self._tree, dev=self._node, noExpand=False)
        self.setUpdatesEnabled(True)

    @Slot(QTreeWidgetItem)
    def _expandCb(self,item):
        self.setUpdatesEnabled(False)
        item._expand()

        self._tree.setColumnWidth(0,self._colWidths[0])
        self._tree.setColumnWidth(1,self._colWidths[1])
        # self._tree.resizeColumnToContents(1)
        # self._tree.resizeColumnToContents(2)
        self._tree.setColumnWidth(2,self._colWidths[2])
        self._tree.setColumnWidth(3,self._colWidths[3])
        self._tree.setColumnWidth(4,self._colWidths[4])
        # self._tree.setColumnWidth(4,self._colWidths[4])
        # self._tree.resizeColumnToContents(5)

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

class ToggleButton(QPushButton):
    def __init__(self,main,state,path):
        super().__init__()
        self._main = main
        self._state = state
        self._path = path
        self.styleSheet = 'QPushButton {background-color: %s;\
                                          color: black;\
                                          border: none;\
                                          font: bold}'

        self.setStyleSheet(self.styleSheet%self._main._addColor)

    def toggle(self):
        if self._state is True:
            self.setText('Add')
            self._state = False
            self.setStyleSheet(self.styleSheet%self._main._addColor)
        else:
            self.setText('Remove')
            self._state = True
            self.setStyleSheet(self.styleSheet%self._main._colorSelector.current_color())


    def setStyle(self,color):
        self.setStyleSheet(self.styleSheet%color)

class TimePlotter(PyDMFrame):
    def __init__(self, parent=None, init_channel=None):
        super().__init__(parent, init_channel)
        self._node = None

        self._addColor = '#dddddd'
        self._colorSelector = ColorSelector()

    def connection_changed(self, connected):

        build = (self._node is None) and (self._connected != connected and connected is True)
        super(TimePlotter, self).connection_changed(connected)

        if not build:
            return

        print("Calling setup UI")

        self._node = nodeFromAddress(self.channel)
        self.setup_ui()

    def setup_ui(self):

        vb = QVBoxLayout()
        self.setLayout(vb)

        main_layout = QHBoxLayout()
        main_box = QGroupBox(parent=self)
        main_box.setLayout(main_layout)

        buttons_layout = QHBoxLayout()
        buttons_box = QGroupBox(parent=self)
        buttons_box.setLayout(buttons_layout)

        self.width_edit = QLineEdit()
        apply_btn = QPushButton()
        apply_btn.setText("Set width")
        apply_btn.clicked.connect(self.do_setwidth)

        auto_axis_btn = QPushButton()
        auto_axis_btn.setText("Auto height")
        auto_axis_btn.clicked.connect(self.do_autoheight)

        # Create the legend layout
        self.legend_layout = QVBoxLayout()
        self.legend_layout.setContentsMargins(10, 10, 10, 10)

        # Create a Frame to host the items in the legend
        self.frm_legend = QFrame(parent=self)
        self.frm_legend.setLayout(self.legend_layout)

        # Create a ScrollArea
        self.scroll_area = QScrollArea(parent=self)
        self.scroll_area.setMinimumHeight(200)
        self.scroll_area.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        self.scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setAlignment(QtCore.Qt.AlignTop)

        # Add the Frame to the scroll area
        self.scroll_area.setWidget(self.frm_legend)

        buttons_layout.addWidget(self.width_edit)
        buttons_layout.addWidget(apply_btn)
        buttons_layout.addWidget(auto_axis_btn)

        plots_layout = QHBoxLayout()
        plots_box = QGroupBox(parent=self)
        plots_box.setLayout(plots_layout)

        self.plots = pwt.PyDMTimePlot(parent=None, background = '#f6f6f6', plot_by_timestamps = True)
        self.plots.setShowLegend(False)
        self.plots.setShowXGrid(True)
        self.plots.setShowYGrid(True)
        self.plots.setTitle('Plots')
        self.plots.setTimeSpan(100)

        plots_layout.addWidget(self.plots)
        plots_layout.addWidget(buttons_box)

        selection_layout = QVBoxLayout()
        self.selection_tree = SelectionTree(main=self,parent=None,init_channel=self.channel)
        self.selection_tree.setMinimumWidth(718)
        selection_layout.addWidget(self.selection_tree)
        selection_layout.addWidget(self.scroll_area)
        selection_box = QGroupBox()
        selection_box.setLayout(selection_layout)

        selection_splitter = QSplitter(Qt.Vertical)
        selection_splitter.addWidget(self.selection_tree)
        selection_splitter.addWidget(self.scroll_area)

        graphs_layout = QVBoxLayout()
        graphs_layout.addWidget(self.plots)
        graphs_layout.addWidget(buttons_box)
        graphs_box = QGroupBox()
        graphs_box.setLayout(graphs_layout)

        main_splitter = QSplitter(Qt.Horizontal)

        main_splitter.addWidget(selection_splitter)
        main_splitter.addWidget(graphs_box)
        main_layout.addWidget(main_splitter)

        vb.addWidget(main_box)

    def do_add(self,path):
        self.plots.addYChannel(y_channel=path,
                color = self._colorSelector.take_color(path),
                lineWidth = 5)
        self.plots.setShowLegend(False)

        disp = LegendRow(parent = self,path=path,main = self)
        disp.setMaximumHeight(50)
        self.legend_layout.addWidget(disp)

    def do_remove(self,path):
        curve = self.plots.findCurve(path)
        self.plots.removeYChannel(curve)
        for widget in self.frm_legend.findChildren(QWidget):
            if isinstance(widget,LegendRow) and widget._path == path:
                widget.setParent(None)
                widget.deleteLater()

    def do_setwidth(self):
        text = self.width_edit.text()

        try:
            val = float(text)
            self.plots.setTimeSpan(val)
        except Exception:
            pass

    def do_autoheight(self):
        print('setting')
        # self.plots.setAutoRangeY(True)
        # self.plots.autoRangeY = True
        self.plots.plotItem.enableAutoRange(ViewBox.YAxis, enable=True)

    def minimumSizeHint(self):
        return QtCore.QSize(1500, 1000)

    def ui_filepath(self):
        return None

class LegendRow(Display):
    def __init__(self, parent=None, args=[], macros=None,path=None,main=None):
        super(LegendRow, self).__init__(parent=parent, args=args, macros=None)

        self._path = path
        self.sizeX = 40
        self.sizeY = 40
        self._main = main

        self.setMaximumHeight(50)
        self.setup_ui()

    def setup_ui(self):

        #setup main layout
        main_layout = QHBoxLayout()
        main_box = QGroupBox(parent=self)
        main_box.setLayout(main_layout)

        #Add widgets to layout
        main_layout.addWidget(QLabel(self._path))
        button = ToggleButton(main=self._main, state = True, path = self._path)
        button.setStyle(self._main._colorSelector.current_color())
        button.setMaximumWidth(150)
        button.setMaximumHeight(50)
        button.setText('Remove')

        def legendbuttonfuncgen(path):
            def f():
                self._main.do_remove(path)
                for widget in self._main.selection_tree.findChildren(QWidget):
                    if isinstance(widget,ToggleButton) and widget._path == path:
                        widget.toggle()
            return f

        button.clicked.connect(legendbuttonfuncgen(self._path))
        main_layout.addWidget(button)

        self.setLayout(main_layout)

    def ui_filepath(self):
        # No UI file is being used
        return None

class ColorSelector():

    def __init__(self):
        self._colorList = ['#F94144', '#F3722C', '#F8961E', '#F9844A', '#F9C74F', '#90BE6D', '#43AA8B', '#4D908E', '#577590', '#277DA1','#f70a0a','#f75d0a','#f7a00a','#f7f30a','#98f70a','#1af70a','#0af7c0','#0accf7','#0a75f7','#0a1ef7','#710af7','#e70af7','#f70a71','#8a2d06','#838a06''#188a06','#188a06','#188a06']
        self._currentDict = {}
        self._currentColor = None

    def take_color(self,channel):

        if len(self._colorList) == 0:
            self._colorList.append(self.generate_new_color())

        random.shuffle(self._colorList)
        color = self._colorList.pop()
        self._currentDict[channel] = color
        self._currentColor = color
        return color

    def give_back_color(self,channel):

        color = self.currentDict.pop(channel)
        self._colorList.append(color)
        random.shuffle(self._colorList)

    def current_color(self):

        return self._currentColor

    def generate_new_color(self):

        return '#' + hex(random.randint(0x100000,0xffffff))[2:] #<----------Change this
