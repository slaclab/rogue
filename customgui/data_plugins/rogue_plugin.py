import logging
import socket
import numpy as np

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

from pyrogue import VirtualClient


logger = logging.getLogger(__name__)


class RogueServer(QThread):
    sock_cache = {}

    def __init__(self, host, port):
        super(QThread, self).__init__()
        if self.make_hash(host, port) in RogueServer.sock_cache:
            return
        self.host = host
        self.port = port
        self.system = None
        logger.info("Will open Rogue server at: {}:{}".format(self.host, self.port))

        self.mutex = QMutex()
        self.connected = False
        self.connect()

        self.mutexW = QMutex()
        self.connectedW = False
        self.connectW()

        self.start()
        RogueServer.sock_cache[self.make_hash(host, port)] = self

    def __new__(cls, host, port):
        obj_hash = RogueServer.make_hash(host, port)
        if obj_hash in cls.sock_cache:
            return RogueServer.sock_cache[obj_hash]
        else:
            server = super(RogueServer, cls).__new__(cls)
            return server

    def run(self):
        while not self.isInterruptionRequested():
            if not self.connected:
                self.mutex.lock()
                self.connect()
                self.mutex.unlock()

            if not self.connectedW:
                self.mutexW.lock()
                self.connectW()
                self.mutexW.unlock()

            self.sleep(1)

    def connect(self):
        if self.connected:
            return

        try:
            self.system = None
            self.system = VirtualClient(self.host, self.port)
            self.connected = True
            logger.info("Connected to Rogue server at: {}:{}".format(self.host, self.port))
        except Exception as ex:
            logger.error('Error connecting to Rogue. {}'.format(str(ex)))

    def connectW(self):
        if self.connectedW:
            return

        try:
            self.systemW = None
            self.systemW = VirtualClient(self.host, self.port)
            self.connectedW = True
            logger.info("Connected to Rogue W server at: {}:{}".format(self.host, self.port))
        except Exception as ex:
            logger.error('Error connecting to W Rogue. {}'.format(str(ex)))

    def disconnect(self):
        if not self.connected:
            return

        try:
            self.system = None
            self.connected = False
        except Exception as ex:
            logger.error('Error disconnecting from Rogue read socket. {}'.format(str(ex)))

        try:
            self.W = None
            self.connectedW = False
        except Exception as ex:
            logger.error('Error disconnecting from Rogue write socket. {}'.format(str(ex)))

    def __hash__(self):
        return self.make_hash(self.host, self.port)

    def __eq__(self, other):
        return (self.host, self.port) == (other.ip, other.port)

    def __ne__(self, other):
        return not (self == other)

    @staticmethod
    def make_hash(host, port):
        return hash((host, port))

class DataThread(QThread):
    new_data_signal = pyqtSignal([float], [int], [str])

    def __init__(self, host, port, path, poll_interval=0.1):
        super(QThread, self).__init__()
        self.host = host
        self.port = port
        self.path = path
        self.poll_interval = poll_interval

        self.node = None
        self.nodeW = None

        self.server = RogueServer(self.host, self.port)

    def run(self):
        while not self.isInterruptionRequested():
            self.update_data()

            self.msleep(int(self.poll_interval*1000))

    def update_data(self):
        if self.server.connected:
            data = self.read_data()
            if data is not None:
                self.new_data_signal.emit(data)

    def write(self, new_value):
        if self.server.connected and self.node.mode == "RW":
            self.write_data(new_value)

    def read_data(self):
        self.server.mutex.lock()
        try:
            if self.node is None:
                self.node = self.server.system.root.getNode(self.path)

            response = self.node.get()
            return response

        except:
            pass

        finally:
            self.server.mutex.unlock()

        # Add exceptions to this functions

    def write_data(self, new_value):
        self.server.mutexW.lock()
        try:
            if self.nodeW is None:
                self.nodeW = self.server.systemW.root.getNode(self.path)
                self.nodeW.set(int(new_value))
            else:
                self.nodeW.set(int(new_value))
        except:
            pass

        finally:
            self.server.mutexW.unlock()

            self.update_data()

class Connection(PyDMConnection):
    ADDRESS_FORMAT = "rogue://<host>:<port>/<path>/<polling|0.1>"

    # These values will be passed in the command line
    serverIndices = {
        0 : "localhost:9099",
        1 : "localhost:9097"
    }

    def __init__(self, channel, address, protocol=None, parent=None):
        super(Connection, self).__init__(channel, address, protocol, parent)
        self.app = QApplication.instance()

        # Default Values
        self.server = None
        self.host = 'localhost'
        self.port = 9099
        self.path = 'dummyTree.AxiVersion.ScratchPad'
        self.poll = 1
        self.units = None



        self.parse_address(address)

        self.add_listener(channel)

        self.data_thread = DataThread(self.host, self.port, self.path, self.poll)

        self.data_thread.new_data_signal.connect(self.emit_data, Qt.QueuedConnection)
        self.data_thread.start()

        self.metadata_timer = QTimer()
        self.metadata_timer.setInterval(500)
        self.metadata_timer.timeout.connect(self.emit_metadata)
        self.metadata_timer.start()

    def parse_address(self, address):

        data = address.split("/")

        if ":" in data[0]:
            data_server = data[0].split(":")
        else:
            data_server = self.serverIndices[int(data[0])].split(":")

        self.host = data_server[0]
        self.port = int(data_server[1])

        self.path = data[1]
        self.poll = float(data[2])

    def emit_metadata(self):
        self.emit_access_state()
        self.emit_connection_state(self.data_thread.server.connected and self.data_thread.node is not None )

    @pyqtSlot(int)
    @pyqtSlot(float)
    @pyqtSlot(str)
    @pyqtSlot(bool)
    def emit_data(self, new_data):
        if new_data is not None:
            self.new_value_signal[type(new_data)].emit(new_data)
        if self.units is None:
            rNode = self.data_thread.node
            self.units = " | " + rNode.name + " | " + rNode.mode + " | " + rNode.base.name(rNode.bitSize[0])
            self.unit_signal.emit(self.units)

    def emit_access_state(self):
        if utilities.is_pydm_app() and self.app.is_read_only():
        # if self.app.is_read_only():
            self.write_access_signal.emit(False)
            return

        self.write_access_signal.emit(True)

    def emit_connection_state(self, conn):
        if conn:
            self.connection_state_signal.emit(True)
        else:
            self.connection_state_signal.emit(False)

    @pyqtSlot(int)
    @pyqtSlot(float)
    @pyqtSlot(str)
    @pyqtSlot(np.ndarray)
    def put_value(self, new_val):
        if utilities.is_pydm_app() and self.app.is_read_only():
        # if self.app.is_read_only():
            return

        try:
            self.data_thread.write(new_val)
        except Exception as e:
            logger.error("Unable to put %s to %s.  Exception: %s",
                         new_val, self.address, str(e))

    def add_listener(self, channel):
        super(Connection, self).add_listener(channel)

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

        super(Connection, self).remove_listener(channel)

    def close(self):
        self.data_thread.server.requestInterruption()
        self.data_thread.requestInterruption()
        self.data_thread.server.disconnect()
#        self.data_thread.terminate()

class RoguePlugin(PyDMPlugin):
    protocol = "rogue"
    connection_class = Connection
