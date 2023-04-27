#-----------------------------------------------------------------------------
# Title      : PyRogue protocols / GPIB register protocol
#-----------------------------------------------------------------------------
# Description:
# Module to interface to GPIB devices
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

from gpib_ctypes import Gpib # pip install gpib_ctypes
import rogue.interfaces.memory
import pyrogue
import queue
import threading

class GpibController(rogue.interfaces.memory.Slave):
    def __init__(self, *, gpibAddr, gpibBoard=0, timeout=Gpib.gpib.T1s):
        """
        Possible Timeout Values:
            T1000s
            T300s
            T100s
            T30s
            T10s
            T3s
            T1s
            T300ms
            T100ms
            T30ms
            T10ms
            T3ms
            T1ms
            T300us
            T100us
            T30us
            T10us
            TNONE
        """
        super().__init__(1,4096)

        self._log = pyrogue.logInit(cls=self, name=f'GPIB.{gpibBoard}.{gpibAddr}')
        self._gpib = Gpib.Gpib(gpibBoard,gpibAddr,0,timeout)

        self._workerQueue = queue.Queue()
        self._workerThread = threading.Thread(target=self._worker)
        self._workerThread.start()
        self._map = {}

    def _addVariable(self, var):
        self._map[var.offset] = var

    def _stop(self):
        self._workerQueue.put(None)
        self._workerThread.join()

    def _doTransaction(self, transaction):
        self._workerQueue.put(transaction)

    def _worker(self):
        while True:
            transaction = self._workerQueue.get()

            if transaction is None:
                return

            with transaction.lock():

                # First lookup address
                addr = transaction.address()
                if addr not in self._map:
                    transaction.error(f'Unknown address: {addr}')

                var = self._map[addr]
                byteSize = pyrogue.byteCount(var.base.bitSize)
                readLen = 1024 if byteSize < 1024 else byteSize+10

                # Check transaction size
                if byteSize != transaction.size():
                    transaction.error(f'Transaction size mismatch: Got={transaction.size()}, Exp={byteSize}')

                # Write path
                if transaction.type() == rogue.interfaces.memory.Write:
                    valBytes = bytearray(byteSize)
                    transaction.getData(valBytes, 0)
                    val = var.base.fromBytes(valBytes)
                    send = var.getExtraAttribute('key') + " " + var.genDisp(val)
                    self._log.debug(f"Write Sending {send}")
                    self._gpib.write(send.encode('UTF-8'))
                    transaction.done()

                # Read Path
                elif (transaction.type() == rogue.interfaces.memory.Read or transaction.type() == rogue.interfaces.memory.Verify):
                    send = var.getExtraAttribute('key') + "?"
                    self._log.debug(f"Read Sending {send}")
                    self._gpib.write(send.encode('UTF-8'))
                    valStr = self._gpib.read(readLen).decode('UTF-8').rstrip()
                    self._log.debug(f"Read Got: {valStr}")
                    val = var.parseDisp(valStr)
                    valBytes = var.base.toBytes(val)
                    transaction.setData(valBytes, 0)
                    transaction.done()

                else:
                    # Posted writes not supported (for now)
                    transaction.error(f'Unsupported transaction type: {transaction.type()}')


class GpibDevice(pyrogue.Device):

    def __init__(self, *, gpibAddr, gpibBoard=0, timeout=11, **kwargs):
        self._gpib = GpibController(gpibAddr=gpibAddr, gpibBoard=gpibBoard, timeout=timeout)
        pyrogue.Device.__init__(self, memBase=self._gpib, **kwargs)
        self.addProtocol(self._gpib)
        self._nextAddr = 0

    @property
    def nextAddr(self):
        return self._nextAddr

    def add(self, node):
        super().add(node)
        if node.getExtraAttribute('key') is not None:
            self._gpib._addVariable(node)
            self._nextAddr += (node.offset + node.varBytes)
