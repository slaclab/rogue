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
import socket
import numpy as np
import threading

# from pydm.data_plugins.plugin import PyDMPlugin, PyDMConnection
# from pydm.PyQt.QtCore import pyqtSignal, pyqtSlot, Qt, QThread, QTimer, QMutex
# from pydm.PyQt.QtGui import QApplication
# from pydm.utilities import is_pydm_app

from pydm.data_plugins.plugin import PyDMPlugin, PyDMConnection
from PyQt5.QtCore import pyqtSignal, pyqtSlot, Qt, QThread, QTimer, QMutex
# from PyQt5.QtGui import QApplication
from PyQt5.QtWidgets import QApplication
# from pydm.utilities import is_pydm_app
from pydm import utilities
from pydm.data_plugins import is_read_only as read_only

from pyrogue.interfaces import VirtualClient
import pyrogue
import threading


logger = logging.getLogger(__name__)



def ParseAddress(address):
    # "rogue://index/<path>/<disp>"
    # or
    # "rogue://host:port/<path>/<disp>"

    rogueAddresses = {0: "localhost:9099"}

    data = address.split("/")

    if ":" in data[0]:
        data_server = data[0].split(":")
    else:
        data_server = rogueAddresses[int(data[0])].split(":")

    host = data_server[0]
    port = int(data_server[1])
    path = data[1]
    disp = (len(data) > 2) and (data[2] == 'True')

    return (host,port,path,disp)


class RogueConnection(PyDMConnection):

    def __init__(self, channel, address, protocol=None, parent=None):
        super(RogueConnection, self).__init__(channel, address, protocol, parent)

        self.app = QApplication.instance()

        self._host, self._port, self._path, self._disp = ParseAddress(address)

        if utilities.is_pydm_app():
            self._client = pyrogue.interfaces.VirtualClient(self._host, self._port)
            self._node   = self._client.root.getNode(self._path)
            self._cmd    = False
        else:
            self._node = None

        if self._node is not None:
            self.add_listener(channel)
            self.connection_state_signal.emit(True)

            # Command
            if self._node.isinstance(pyrogue.BaseCommand):
                self.write_access_signal.emit(True)
                self._cmd = True
            else:
                self._node.addListener(self._updateVariable)
                self._updateVariable(self._node.path,self._node.getVariableValue(read=False))
                self.write_access_signal.emit(self._node.mode=='RW')

            if self._node.units is not None:
                #self.units = " | " + rNode.name + " | " + rNode.mode + " | " + rNode.base.name(rNode.bitSize[0])
                #self._units = " | " + self._node.name + " | " + self._node.mode + " | "
                self.unit_signal.emit(self._nodes.units)


    def _updateVariable(self,path,varValue):
        if type(varValue.value) == bool:
            self.new_value_signal[int].emit(int(varValue.value))
        elif self._disp:
            self.new_value_signal[str].emit(varValue.valueDisp)
        else:
            self.new_value_signal[type(varValue.value)].emit(varValue.value)


    @pyqtSlot(int)
    @pyqtSlot(float)
    @pyqtSlot(str)
    @pyqtSlot(np.ndarray)
    def put_value(self, new_value):
        if self._node is None or (utilities.is_pydm_app() and self.app.is_read_only()):
            return

        try:
            if self._cmd:
                self._node.__call__(new_value)
            else:
                self._node.setDisp(new_value)
        except:
            logger.error("Unable to put %s to %s.  Exception: %s", new_val, self.address, str(e))


    def add_listener(self, channel):
        super(RogueConnection, self).add_listener(channel)

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

    def remove_listener(self, channel):
        if channel.value_signal is not None:
            try:
                channel.value_signal[str].disconnect(self.put_value)
            except KeyError:
                pass
            try:
                channel.value_signal[int].disconnect(self.put_value)
            except KeyError:
                pass
            try:
                channel.value_signal[float].disconnect(self.put_value)
            except KeyError:
                pass
            try:
                channel.value_signal[np.ndarray].disconnect(self.put_value)
            except KeyError:
                pass

        super(RogueConnection, self).remove_listener(channel)

    def close(self):
        pass

class RoguePlugin(PyDMPlugin):
    protocol = "rogue"
    connection_class = RogueConnection

