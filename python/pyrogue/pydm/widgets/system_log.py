#-----------------------------------------------------------------------------
# Title      : PyRogue PyDM System Log Widget
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
from pydm.widgets import PyDMPushButton
from pyrogue.pydm.data_plugins.rogue_plugin import nodeFromAddress
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QVBoxLayout, QTreeWidgetItem, QTreeWidget, QGroupBox
import json
import time


class SystemLog(PyDMFrame):
    def __init__(self, parent=None, init_channel=None):
        PyDMFrame.__init__(self, parent, init_channel)

        self._systemLog = None
        self._node = None

    def connection_changed(self, connected):
        build = (self._node is None) and (self._connected != connected and connected is True)
        super(SystemLog, self).connection_changed(connected)

        if not build:
            return

        self._node = nodeFromAddress(self.channel)
        self._path = self.channel.replace('SystemLog','ClearLog')

        vb = QVBoxLayout()
        self.setLayout(vb)

        gb = QGroupBox('System Log (20 most recent entries)')
        vb.addWidget(gb)

        vb = QVBoxLayout()
        gb.setLayout(vb)

        self._systemLog = QTreeWidget()
        vb.addWidget(self._systemLog)

        self._systemLog.setColumnCount(2)
        self._systemLog.setHeaderLabels(['Field','Value'])
        self._systemLog.setColumnWidth(0,200)

        self._pb = PyDMPushButton(label='Clear Log',pressValue=1,init_channel=self._path)
        vb.addWidget(self._pb)

    def value_changed(self, new_val):
        lst = json.loads(new_val)

        self._systemLog.clear()

        # Show only the last 20 entries
        # In the future we can consider a pop up dialog with the full log.
        # Unclear if that is neccessary.
        for ent in lst[-20:]:
            widget = QTreeWidgetItem(self._systemLog)
            widget.setText(0, time.strftime("%Y-%m-%d %H:%M:%S %Z", time.localtime(ent['created'])))

            widget.setText(1,ent['message'])
            widget.setExpanded(False)
            widget.setTextAlignment(0,Qt.AlignTop)

            temp = QTreeWidgetItem(widget)
            temp.setText(0,'Name')
            temp.setText(1,str(ent['name']))
            temp.setTextAlignment(0,Qt.AlignRight)

            temp = QTreeWidgetItem(widget)
            temp.setText(0,'Level')
            temp.setText(1,'{} ({})'.format(ent['levelName'],ent['levelNumber']))
            temp.setTextAlignment(0,Qt.AlignRight)

            if ent['exception'] is not None:
                exc = QTreeWidgetItem(widget)
                exc.setText(0,'exception')
                exc.setText(1,str(ent['exception']))
                exc.setExpanded(False)
                exc.setTextAlignment(0,Qt.AlignRight)

                for v in ent['traceBack']:
                    temp = QTreeWidgetItem(exc)
                    temp.setText(0,'')
                    temp.setText(1,v)
