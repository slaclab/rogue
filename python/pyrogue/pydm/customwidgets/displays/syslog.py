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
from qtpy.QtWidgets import QWidget, QGridLayout, QTreeWidgetItem, QTreeWidget, QLineEdit, QFormLayout, QGroupBox
import jsonpickle
import time

class SyslogWindow(PyDMFrame):
    def __init__(self, parent=None, init_channel=None):
        PyDMFrame.__init__(self, parent, init_channel)

        self._systemLog = None
        self._logCount  = 0
        self._en        = False

        if init_channel is not None:
            self._en = True
            self._build()

    def _build(self):
        if (not self._en) or (not utilities.is_pydm_app()) or self.channel is None:
            return

        self._addr, self._port, path, disp = ParseAddress(self.channel)
        cpath = 'rogue://{}:{}/{}.ClearLog'.format(self._addr,self._port,path.split('.')[0])

        vb = QVBoxLayout()
        self.setLayout(vb)

        gb = QGroupBox('System Log')
        vb.addWidget(gb)

        vb = QVBoxLayout()
        gb.setLayout(vb)

        self._systemLog = QTreeWidget()
        vb.addWidget(self._systemLog)

        self._systemLog.setColumnCount(2)
        self._systemLog.setHeaderLabels(['Field','Value'])

        self._logCount = 0

        self._pb = PyDMPushButton(label='Clear Log',pressValue=1,init_channel=cpath)
        vb.addWidget(self._pb)

    def value_changed(self, new_val):
        lst = jsonpickle.decode(new_val)

        if len(lst) == 0:
            self._systemLog.clear()

        elif len(lst) > self._logCount:
            for i in range(self._logCount,len(lst)):
                widget = QTreeWidgetItem(self._systemLog)
                widget.setText(0, time.strftime("%Y-%m-%d %H:%M:%S %Z", time.localtime(lst[i]['created'])))

                widget.setText(1,lst[i]['message'])
                widget.setExpanded(False)
                widget.setTextAlignment(0,Qt.AlignTop)

                temp = QTreeWidgetItem(widget)
                temp.setText(0,'Name')
                temp.setText(1,str(lst[i]['name']))
                temp.setTextAlignment(0,Qt.AlignRight)

                temp = QTreeWidgetItem(widget)
                temp.setText(0,'Level')
                temp.setText(1,'{} ({})'.format(lst[i]['levelName'],lst[i]['levelNumber']))
                temp.setTextAlignment(0,Qt.AlignRight)

                if lst[i]['exception'] is not None:
                    exc = QTreeWidgetItem(widget)
                    exc.setText(0,'exception')
                    exc.setText(1,str(lst[i]['exception']))
                    exc.setExpanded(False)
                    exc.setTextAlignment(0,Qt.AlignRight)

                    for v in lst[i]['traceBack']:
                        temp = QTreeWidgetItem(exc)
                        temp.setText(0,'')
                        temp.setText(1,v)

        self._systemLog.resizeColumnToContents(0)
        self._logCount = len(lst)

    @Property(bool)
    def rogueEnabled(self):
        return self._en

    @rogueEnabled.setter
    def rogueEnabled(self, value):
        self._en = value
        self._build()

