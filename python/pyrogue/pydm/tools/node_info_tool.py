#-----------------------------------------------------------------------------
# Title      : PyRogue PyDM Node Info Tool
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

import logging
from pydm.tools import ExternalTool
from pydm.utilities.iconfont import IconFont
from qtpy.QtWidgets import QVBoxLayout, QDialog, QPushButton, QFormLayout, QLineEdit
from qtpy.QtCore import Qt

import pyrogue
from pyrogue.interfaces import VirtualClient
from pyrogue.pydm.data_plugins.rogue_plugin import parseAddress

logger = logging.getLogger(__name__)


class NodeInformation(ExternalTool):

    def __init__(self):
        icon = IconFont().icon("cogs")
        name = "Node Information"
        group = "Rogue"
        use_with_widgets = True
        ExternalTool.__init__(self, icon=icon, name=name, group=group, use_with_widgets=use_with_widgets)

    def call(self, channels, sender):
        addr, port, path, mode = parseAddress(channels[0].address)
        self._client = VirtualClient(addr, port)
        node = self._client.root.getNode(path)

        if node.isinstance(pyrogue.Device):
            self._device(node,channels[0])
        elif node.isinstance(pyrogue.BaseVariable):
            self._variable(node,channels[0])

        elif node.isinstance(pyrogue.BaseCommand):
            self._command(node,channels[0])

    def _variable(self, node, channel):
        attrs = ['name', 'path', 'description', 'hidden', 'groups', 'enum',
                 'typeStr', 'disp', 'precision', 'mode', 'units', 'minimum',
                 'maximum', 'lowWarning', 'lowAlarm', 'highWarning',
                 'highAlarm', 'alarmStatus', 'alarmSeverity', 'pollInterval']

        if node.isinstance(pyrogue.RemoteVariable):
            attrs += ['offset', 'bitSize', 'bitOffset', 'verify', 'varBytes']

        msgBox = QDialog()
        msgBox.setWindowTitle("Variable Information For {}".format(node.name))
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
            le.setText(str(getattr(node,a)))
            fl.addRow(a,le)

        le = QLineEdit()
        le.setReadOnly(True)
        le.setText(channel.address)
        fl.addRow('PyDM Path',le)

        msgBox.exec()


    def _command(self, node, channel):
        attrs = ['name', 'path', 'description', 'hidden', 'groups', 'enum', 'typeStr', 'disp']

        if node.isinstance(pyrogue.RemoteCommand):
            attrs += ['offset', 'bitSize', 'bitOffset', 'varBytes']

        msgBox = QDialog()
        msgBox.setWindowTitle("Command Information For {}".format(node.name))
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
            le.setText(str(getattr(node,a)))
            fl.addRow(a,le)

        le = QLineEdit()
        le.setReadOnly(True)
        le.setText(channel.address)
        fl.addRow('PyDM Path',le)

        msgBox.exec()


    def _device(self, node, channel):
        attrs = ['name', 'path', 'description', 'hidden', 'groups']

        msgBox = QDialog()
        msgBox.setWindowTitle("Device Information For {}".format(node.name))
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
            le.setText(str(getattr(node,a)))
            fl.addRow(a,le)

        le = QLineEdit()
        le.setReadOnly(True)
        le.setText(channel.address)
        fl.addRow('PyDM Path',le)

        msgBox.exec()

    def to_json(self):
        return ""

    def from_json(self, content):
        pass

    def get_info(self):
        ret = ExternalTool.get_info(self)
        ret.update({'file': __file__})
        return ret
