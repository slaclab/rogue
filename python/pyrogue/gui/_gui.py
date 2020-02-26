#-----------------------------------------------------------------------------
# Title      : PyRogue GUI module
#-----------------------------------------------------------------------------
# Description:
# Python code for pyrogue GUI
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
from PyQt5.QtWidgets import QVBoxLayout, QTabWidget, QApplication, QWidget
from PyQt5.QtCore    import pyqtSignal, pyqtSlot
from PyQt5.QtNetwork import QAbstractSocket

import pyrogue
import pyrogue.interfaces
import pyrogue.gui
import pyrogue.gui.variables
import pyrogue.gui.commands
import pyrogue.gui.system
import socket
import sys
import os
import signal


def runGui(root,incGroups=None,excGroups=None,title=None,sizeX=800,sizeY=1000):

    appTop = QApplication(sys.argv)
    RogueSignalWakeupHandler(appTop)

    def signalRx(self,*args):
        print("Got signal, exiting")
        appTop.quit()

    signal.signal(signal.SIGTERM, signalRx)
    signal.signal(signal.SIGINT,  signalRx)

    guiTop = pyrogue.gui.GuiTop(incGroups=incGroups,excGroups=excGroups)
    if title is None:
        title = "Rogue Server: {}".format(socket.gethostname())
    guiTop.setWindowTitle(title)
    guiTop.addTree(root)
    guiTop.resize(sizeX,sizeY)

    print(f'Running GUI. Close window, hit cntrl-c or send SIGTERM to {os.getpid()} to exit.')
    appTop.exec_()


def application(argv):
    return QApplication(argv)


class GuiTop(QWidget):

    newRoot = pyqtSignal(pyrogue.Root,list,list)
    newVirt = pyqtSignal(pyrogue.interfaces.VirtualNode,list,list)

    def __init__(self,*, parent=None, incGroups=None, excGroups=None, group=None):
        super(GuiTop,self).__init__(parent)

        print("-------------------------------------------------------------------------")
        print("The legacy GUI is now deprecated. Please use pyDM.")
        print("")
        print("   To use pydm serverPort must be set in root.start():")
        print("")
        print("      root.start(serverPort=9099)")
        print("")
        print("    when using a fixed port or for auto port assignment you can use:")
        print("")
        print("      root.start(serverPort=0)")
        print("")
        print("   To start pydm client from command line:")
        print("")
        print("      python -m pyrogue gui --server=localhost:9099")
        print("")
        print("   To start in top level python script:")
        print("")
        print("      pyrogue.pydm.runPyDM(root=root)")
        print("")
        print("   the server port will be extracted from the root object.")
        print("-------------------------------------------------------------------------")

        if incGroups is None:
            self._incGroups=[]
        elif isinstance(incGroups,list):
            self._incGroups=incGroups
        else:
            self._incGroups=[incGroups]

        if excGroups is None:
            self._excGroups=['Hidden']
        elif isinstance(excGroups,list):
            self._excGroups=excGroups
        else:
            self._excGroups=[excGroups]

        vb = QVBoxLayout()
        self.setLayout(vb)

        self.tab = QTabWidget()
        vb.addWidget(self.tab)

        self.var = pyrogue.gui.variables.VariableWidget(parent=self.tab)
        self.tab.addTab(self.var,'Variables')

        self.cmd = pyrogue.gui.commands.CommandWidget(parent=self.tab)
        self.tab.addTab(self.cmd,'Commands')
        self.show()

        self.newRoot.connect(self._addTree)
        self.newRoot.connect(self.var.addTree)
        self.newRoot.connect(self.cmd.addTree)

        self.newVirt.connect(self._addTree)
        self.newVirt.connect(self.var.addTree)
        self.newVirt.connect(self.cmd.addTree)

        self._appTop = None

    def addTree(self,root):
        if not root.running:
            raise Exception("GUI can not be attached to a tree which is not started")

        if isinstance(root,pyrogue.interfaces.VirtualNode):
            self.newVirt.emit(root,self._incGroups,self._excGroups)
        else:
            self.newRoot.emit(root,self._incGroups,self._excGroups)

    @pyqtSlot(pyrogue.Root,list,list)
    @pyqtSlot(pyrogue.interfaces.VirtualNode,list,list)
    def _addTree(self,root,incGroups,excGroups):
        self.sys = pyrogue.gui.system.SystemWidget(root=root,parent=self.tab)
        self.tab.addTab(self.sys,root.name)
        self.adjustSize()


class RogueSignalWakeupHandler(QAbstractSocket):

    def __init__(self, parent=None):
        super().__init__(QAbstractSocket.UdpSocket, parent)
        self.old_fd = None
        # Create a socket pair
        self.wsock, self.rsock = socket.socketpair(type=socket.SOCK_DGRAM)
        # Let Qt listen on the one end
        self.setSocketDescriptor(self.rsock.fileno())
        # And let Python write on the other end
        self.wsock.setblocking(False)
        self.old_fd = signal.set_wakeup_fd(self.wsock.fileno())
        # First Python code executed gets any exception from
        # the signal handler, so add a dummy handler first
        self.readyRead.connect(lambda : None)
        # Second handler does the real handling
        self.readyRead.connect(self._readSignal)

    def __del__(self):
        # Restore any old handler on deletion
        if self.old_fd is not None and signal and signal.set_wakeup_fd:
            signal.set_wakeup_fd(self.old_fd)

    def _readSignal(self):
        # Read the written byte.
        # Note: readyRead is blocked from occurring again until readData()
        # was called, so call it, even if you don't need the value.
        data = self.readData(1)
        # Emit a Qt signal for convenience
        self.signalReceived.emit(data[0])

    signalReceived = pyqtSignal(int)
