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


logger = logging.getLogger(__name__)


class PydmRogueClient(object):
    sock_cache = {}

    def __init__(self, host, port):
        if self.make_hash(host, port) in PydmRogueClient.sock_cache:
            return

        self._host = host
        self._port = port
        self._client = None
        logger.info("Will open Rogue server at: {}:{}".format(self._host, self._port))

        try:
            self._client = VirtualClient(self._host, self._port)
            logger.info("Connected to Rogue server at: {}:{}".format(self._host, self._port))
        except Exception as ex:
            logger.error('Error connecting to Rogue. {}'.format(str(ex)))

        PydmRogueClient.sock_cache[self.make_hash(self._host, self._port)] = self

    @property
    def root(self):
        return self._client.root

    def __new__(cls, host, port):
        obj_hash = PydmRogueClient.make_hash(host, port)

        if obj_hash in cls.sock_cache:
            return PydmRogueClient.sock_cache[obj_hash]
        else:
            server = super(PydmRogueClient, cls).__new__(cls)
            return server

    def __hash__(self):
        return self.make_hash(self.host, self.port)

    def __eq__(self, other):
        return (self.host, self.port) == (other.ip, other.port)

    def __ne__(self, other):
        return not (self == other)

    @staticmethod
    def make_hash(host, port):
        return hash((host, port))


class PydmRogueConnection(PyDMConnection):
    ADDRESS_FORMAT = "rogue://<host>:<port>/<path>/<polling|0.1>"

    # These values will be passed in the command line
    serverIndices = {
        0 : "localhost:9099",
        1 : "localhost:9097"
    }

    def __init__(self, channel, address, protocol=None, parent=None):
        super(PydmRogueConnection, self).__init__(channel, address, protocol, parent)
        self.app = QApplication.instance()

        # Default Values
        self._host = 'localhost'
        self._port = 9099
        self._path = 'dummyTree.AxiVersion.ScratchPad'

        self._parse_address(address)

        self.add_listener(channel)

        self._client = PydmRogueClient(self._host, self._port)
        self._node = self._client.root.getNode(self._path)

        if self._node is not None:

            self._node.addListener(self._updateVariable)
            self.connection_state_signal.emit(True)
            self._updateVariable(self._node.path,self._node.getVariableValue(read=False))

            if self._node.units is not None:
                #self.units = " | " + rNode.name + " | " + rNode.mode + " | " + rNode.base.name(rNode.bitSize[0])
                #self._units = " | " + self._node.name + " | " + self._node.mode + " | "
                self.unit_signal.emit(self._nodes.units)

            self.write_access_signal.emit(self._node.mode=='RW')


    def _parse_address(self, address):

        data = address.split("/")

        if ":" in data[0]:
            data_server = data[0].split(":")
        else:
            data_server = self.serverIndices[int(data[0])].split(":")

        self._host = data_server[0]
        self._port = int(data_server[1])
        self._path = data[1]


    def _updateVariable(self,path,varValue):
        new_data = varValue.value

        self.new_value_signal[type(new_data)].emit(new_data)


    @pyqtSlot(int)
    @pyqtSlot(float)
    @pyqtSlot(str)
    @pyqtSlot(np.ndarray)
    def put_value(self, new_value):
        if self._node is None or (utilities.is_pydm_app() and self.app.is_read_only()):
            return

        try:
            self._node.set(new_value)
        except:
            logger.error("Unable to put %s to %s.  Exception: %s", new_val, self.address, str(e))


    def add_listener(self, channel):
        super(PydmRogueConnection, self).add_listener(channel)

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

        super(PydmRogueConnection, self).remove_listener(channel)

    def close(self):
        pass

class RoguePlugin(PyDMPlugin):
    protocol = "rogue"
    connection_class = PydmRogueConnection

