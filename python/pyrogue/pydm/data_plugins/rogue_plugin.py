#-----------------------------------------------------------------------------
# Title      : PyRogue PyDM data plug-in
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
import numpy as np
import os
# import time

from pydm.data_plugins.plugin import PyDMPlugin, PyDMConnection
from PyQt5.QtCore import pyqtSlot, Qt
from PyQt5.QtWidgets import QApplication
from pydm import utilities

import pyrogue
from pyrogue.interfaces import VirtualClient


logger = logging.getLogger(__name__)

AlarmToInt = {'None':0, 'Good':0, 'AlarmMinor':1, 'AlarmMajor':2}


def parseAddress(address):
    # "rogue://index/<path>/<mode>"
    # or
    # "rogue://host:port/<path>/<mode>"
    # Mode: 'Value', 'Disp', 'Name' or 'Path'
    envList = os.getenv('ROGUE_SERVERS')

    if envList is None:
        alist = ['localhost:9099']
    else:
        alist = envList.split(',')

    if address[0:8] == 'rogue://':
        address = address[8:]

    data = address.split("/")

    if ":" in data[0]:
        data_server = data[0].split(":")
    else:
        data_server = alist[int(data[0])].split(":")

    host = data_server[0]
    port = int(data_server[1])
    path = data[1]
    mode = 'value' if (len(data) < 3) else data[2]

    return (host,port,path,mode)


def nodeFromAddress(address):
    host, port, path, mode = parseAddress(address)
    client = VirtualClient(host, port)
    return client.root.getNode(path)


class RogueConnection(PyDMConnection):

    def __init__(self, channel, address, protocol=None, parent=None):
        super(RogueConnection, self).__init__(channel, address, protocol, parent)

        self.app = QApplication.instance()

        self._host, self._port, self._path, self._mode = parseAddress(address)

        self._cmd    = False
        self._int    = False
        self._node   = None
        self._enum   = None
        self._notDev = False
        self._address = address

        if utilities.is_pydm_app():
            self._client = pyrogue.interfaces.VirtualClient(self._host, self._port)
            self._node = self._client.root.getNode(self._path)

        if self._node is not None and not self._node.isinstance(pyrogue.Device):
            self._node.addListener(self._updateVariable)
            self._notDev = True

            if self._node.isinstance(pyrogue.BaseCommand):
                self._cmd = True

            if self._node.disp == 'enum' and self._node.enum is not None and self._node.mode != 'RO':
                self._enum = list(self._node.enum.values())

            elif self._mode == 'value' and ('Int' in self._node.typeStr or self._node.typeStr == 'int'):
                self._int = True

        self.add_listener(channel)
        self._client.addLinkMonitor(self.linkState)

    def linkState(self, state):
        if state:
            self.connection_state_signal.emit(True)
        else:
            self.connection_state_signal.emit(False)


    def _updateVariable(self,path,varValue):
        if self._mode == 'name':
            self.new_value_signal[str].emit(self._node.name)
        elif self._mode == 'path':
            self.new_value_signal[str].emit(self._node.path)
        elif self._mode == 'disp':
            self.new_value_signal[str].emit(varValue.valueDisp)
        elif self._enum is not None:
            self.new_value_signal[int].emit(self._enum.index(varValue.valueDisp))
        else:
            self.new_value_signal[type(varValue.value)].emit(varValue.value)

        self.new_severity_signal.emit(AlarmToInt[varValue.severity])


    @pyqtSlot(int)
    @pyqtSlot(float)
    @pyqtSlot(str)
    @pyqtSlot(np.ndarray)
    def put_value(self, new_value):
        if self._node is None or not self._notDev:
            return

        if new_value is None:
            val = None
        elif self._enum is not None and not isinstance(new_value,str):
            val = self._enum[new_value]
        elif self._int:
            val = int(new_value)
        else:
            val = new_value

        if self._cmd:
            self._node.__call__(val)
        else:
            self._node.setDisp(val)


    def add_listener(self, channel):
        super(RogueConnection, self).add_listener(channel)
        self.connection_state_signal.emit(True)

        # If the channel is used for writing to PVs, hook it up to the 'put' methods.
        if channel.value_signal is not None:
            try:
                channel.value_signal[str].connect(self.put_value, Qt.QueuedConnection)
            except KeyError:
                pass
            try:
                channel.value_signal[int].connect(self.put_value, Qt.QueuedConnection)
            except KeyError:
                pass
            try:
                channel.value_signal[float].connect(self.put_value, Qt.QueuedConnection)
            except KeyError:
                pass
            try:
                channel.value_signal[np.ndarray].connect(self.put_value, Qt.QueuedConnection)
            except KeyError:
                pass

        if self._notDev:

            if self._node.units is not None:
                self.unit_signal.emit(self._node.units)

            if self._node.minimum is not None and self._node.maximum is not None:
                self.upper_ctrl_limit_signal.emit(self._node.maximum)
                self.lower_ctrl_limit_signal.emit(self._node.minimum)

            if self._enum is not None:
                self.enum_strings_signal.emit(tuple(self._enum))

            self.prec_signal.emit(self._node.precision)

            if self._mode == 'name':
                self.write_access_signal.emit(False)
                self.new_value_signal[str].emit(self._node.name)
            elif self._mode == 'path' or self._mode == 'path':
                self.write_access_signal.emit(False)
                self.new_value_signal[str].emit(self._node.path)
            else:
                self.write_access_signal.emit(self._cmd or self._node.mode!='RO')
                self._updateVariable(self._node.path,self._node.getVariableValue(read=False))

        else:
            self.new_value_signal[str].emit(self._node.name)

    def remove_listener(self, channel, destroying):
        self._client.remLinkMonitor(self.linkState)
        self._client.stop()
        #if channel.value_signal is not None:
        #    #try:
        #    #    channel.value_signal[str].disconnect(self.put_value)
        #    #except KeyError:
        #    #    pass
        #    try:
        #        channel.value_signal[int].disconnect(self.put_value)
        #    except KeyError:
        #        pass
        #    try:
        #        channel.value_signal[float].disconnect(self.put_value)
        #    except KeyError:
        #        pass
        #    try:
        #        channel.value_signal[np.ndarray].disconnect(self.put_value)
        #    except KeyError:
        #        pass

        #super(RogueConnection, self).remove_listener(channel)
        pass

    def close(self):
        pass


class RoguePlugin(PyDMPlugin):
    protocol = "rogue"
    connection_class = RogueConnection
