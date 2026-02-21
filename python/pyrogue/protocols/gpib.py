#-----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
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

# The following is required to use this Device:
#
# https://gist.github.com/ochococo/8362414fff28fa593bc8f368ba94d46a
#
# Install the gpib_cytpes python package from https://pypi.org/project/gpib-ctypes/
#    pip install gpib_ctypes

from gpib_ctypes import Gpib # pip install gpib_ctypes
import rogue.interfaces.memory
import pyrogue
import queue
import threading
from typing import Any


class GpibController(rogue.interfaces.memory.Slave):
    """
    GPIB-based memory slave interface for SCPI-style instrument control.

    Translates memory-mapped read/write transactions into GPIB SCPI commands
    using variable 'key' attributes as command prefixes.

    Parameters
    ----------
    gpibAddr : int
        GPIB primary address of the device.
    gpibBoard : int, optional
        GPIB interface board number.
    timeout : object, optional
        GPIB timeout constant.
    """

    def __init__(
        self,
        *,
        gpibAddr: int,
        gpibBoard: int = 0,
        timeout: Any = Gpib.gpib.T1s,
    ) -> None:
        super().__init__(1, 4096)

        self._log = pyrogue.logInit(cls=self, name=f'GPIB.{gpibBoard}.{gpibAddr}')
        self._gpib = Gpib.Gpib(gpibBoard,gpibAddr,0,timeout)

        self._workerQueue = queue.Queue()
        self._workerThread = threading.Thread(target=self._worker)
        self._workerThread.start()
        self._map = {}

    def _addVariable(self, var: Any) -> None:
        """Register a variable for GPIB translation by offset."""
        self._map[var.offset] = var

    def _stop(self) -> None:
        """Stop the worker thread."""
        self._workerQueue.put(None)
        self._workerThread.join()

    def _doTransaction(self, transaction: Any) -> None:
        """Queue a memory transaction for the worker thread."""
        self._workerQueue.put(transaction)

    def _worker(self) -> None:
        """Worker thread that processes GPIB transactions."""
        while True:
            transaction = self._workerQueue.get()

            if transaction is None:
                return

            with transaction.lock():

                # First lookup address
                addr = transaction.address()
                if addr not in self._map:
                    transaction.error(f'Unknown address: {addr}')
                    continue

                var = self._map[addr]
                byteSize = pyrogue.byteCount(var.base.bitSize)
                readLen = 1024 if byteSize < 1024 else byteSize+10

                # Check transaction size
                if byteSize != transaction.size():
                    transaction.error(f'Transaction size mismatch: Got={transaction.size()}, Exp={byteSize}')
                    continue

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
    """
    PyRogue Device wrapper for GPIB instruments.

    Provides a Device interface with automatic protocol and variable registration
    for GPIB-controlled instruments using SCPI-style commands.

    Parameters
    ----------
    gpibAddr : int
        GPIB primary address of the instrument.
    gpibBoard : int, optional
        GPIB interface board number.
    timeout : int, optional
        Timeout value for GPIB operations.
    **kwargs : Any
        Additional arguments passed to :class:`pyrogue.Device`.
    """

    def __init__(
        self,
        *,
        gpibAddr: int,
        gpibBoard: int = 0,
        timeout: int = 11,
        **kwargs: Any,
    ) -> None:
        self._gpib = GpibController(gpibAddr=gpibAddr, gpibBoard=gpibBoard, timeout=timeout)
        pyrogue.Device.__init__(self, memBase=self._gpib, **kwargs)
        self.addProtocol(self._gpib)
        self._nextAddr = 0

    @property
    def nextAddr(self) -> int:
        """Get the next available address for variable registration."""
        return self._nextAddr

    def add(self, node: Any) -> None:
        """Add a node and register GPIB variables that have a 'key' attribute."""
        super().add(node)
        if node.getExtraAttribute('key') is not None:
            self._gpib._addVariable(node)
            self._nextAddr += (node.offset + node.varBytes)
