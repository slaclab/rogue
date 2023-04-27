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

import Gpib # pip install gpib_ctypes
import rogue.interfaces.memory
import pyrogue
import queue
import threading

class GpibController(rogue.interfaces.memory.Slave):
    def __init__(self, *, gpibAddr, gpibBoard=0, timeout=11):
        super().__init__(8,4096) # 1KByte For Serial Data

        self._log = pyrogue.logInit(cls=self, name=f'{GPIB.{gpibBoard}.{gpibAddr}}')
        self._gpib = Gpib.Gpib(gpibBoard,gpibAddr,0,timeout)
        self._serSize = serSize

        self._workerQueue = queue.Queue()
        self._workerThread = threading.Thread(target=self._worker)
        self._workerThread.start()
        self._map = {}
        self._nextAddr = 0

    def _addVariable(self, addr, key, base):
        self._map[addr] = (key, base)

    def _stop(self):
        self._workerQueue.put(None)
        self._workerQueue.join()

    def _doTransaction(self, transaction):
        self._workerQueue.put(transaction)

    def _worker(self):
        while True:
            transaction = self._workerQueue.get()

            if transaction is None:
                break

            with transaction.lock():

                # First lookup address
                addr = transaction.address()
                if not addr in self._map:
                    transaction.error(f'Unknown address: {addr}')

                key, base = self._map[addr]
                byteSize = pyrogue.byteCount(base.bitSize)

                # Check transaction size
                if byteSize == transaction.size():
                    transaction.error(f'Transaction size mismatch: Got={transaction.size()}, Exp={byteSize}')

                # Write path
                if transaction.type() == rogue.interfaces.memory.Write:
                    valBytes = bytearray(byteSize)
                    transaction.getData(valBytes, 0)
                    val = base.fromBytes(valBytes)
                    self._gpib.write(f"{key} {val}".encode('UTF-8'))
                    transaction.done()

                # Read Path
                elif (transaction.type() == rogue.interfaces.memory.Read or transaction.type() == rogue.interfaces.memory.Verify):
                    self._gpib.write(f"{key}?".encode('UTF-8'))
                    valStr = self._gpib.read(self._serSize).decode('UTF-8').rstrip()
                    val = base.fromString(valStr)
                    valBytes = base.toBytes(val)
                    transaction.setData(valBytes, 0)
                    transaction.done()

                else:
                    # Posted writes not supported (for now)
                    transaction.error(f'Unsupported transaction type: {transaction.type()}')


class GpibDevice(pyrogue.Device):

    def __init__(self, *, gpibAddr, gpibBoard=0, timeout=11, **kwargs):
        self._gpib = GpibController(gpibAddr=gpibAddr, gpibBoard=gpibBoard, timeout=timeout)
        super().__init__(membase=self._gpib, **kwargs)

    def add(self, key, node):
        pr.Device.add(self, node)
        self._gpib._addVariable(node.address, key, node.base)

