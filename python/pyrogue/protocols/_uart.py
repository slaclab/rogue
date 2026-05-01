#-----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
#-----------------------------------------------------------------------------
# Description:
#       PyRogue protocols / UART register protocol
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

import rogue.interfaces.memory
import pyrogue
import serial
import queue
import threading
from typing import Any


class UartMemory(rogue.interfaces.memory.Slave):
    """
    UART-based memory slave interface for register access over serial.

    Implements a simple text-based protocol for reading and writing 32-bit
    register values over a serial UART connection.

    Parameters
    ----------
    device : str
        Serial device path (for example ``/dev/ttyUSB0`` or ``COM1``).
    baud : int
        Baud rate for serial communication.
    timeout : float, optional
        Read timeout in seconds.
    **kwargs : Any
        Additional keyword arguments passed to :class:`serial.Serial`.
    """

    def __init__(
        self,
        device: str,
        baud: int,
        timeout: float = 1,
        **kwargs: Any,
    ) -> None:
        super().__init__(4,4096) # Set min and max size to 4 bytes

        self._log = pyrogue.logInit(cls=self, name=f'{device}')
        self.serialPort = serial.Serial(device, baud, timeout=timeout, **kwargs)

        self._workerQueue = queue.Queue()
        self._workerThread = threading.Thread(target=self._worker)
        self._workerThread.start()

    def _stop(self) -> None:
        """Stop the worker thread and close the serial port."""
        self._workerQueue.put(None)
        self._workerQueue.join()

        # queue.join() only waits for task_done() on the sentinel; thread.join()
        # ensures the worker has actually exited before serialPort.close().
        # Self-thread guard prevents deadlock if called from inside the worker.
        thr = self._workerThread
        if (thr is not None
                and hasattr(thr, 'is_alive') and thr.is_alive()
                and hasattr(thr, 'join')
                and threading.current_thread() is not thr):
            thr.join()

        self.serialPort.close()

    def __enter__(self) -> "UartMemory":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        """Context manager exit; stops the interface."""
        self._stop()

    def readline(self) -> str:
        """
        Read a line from the serial port until newline or carriage return.

        Returns
        -------
        str
            Line read from the serial port (empty on timeout).
        """
        line = []
        while True:
            ch = self.serialPort.read().decode('ASCII')
            # Break and return if timeout occurs
            if len(ch) == 0:
                break
            line.append(ch)
            if ch == '\n' or ch == '\r':
                break
        return ''.join(line)

    def _doTransaction(self, transaction: rogue.interfaces.memory.Transaction) -> None:
        """
        Queue a memory transaction for processing by the worker thread.

        Parameters
        ----------
        transaction : object
            Memory transaction to execute.
        """
        self._workerQueue.put(transaction)


    def _doWrite(self, transaction: rogue.interfaces.memory.Transaction) -> None:
        """Execute a write transaction over the UART register protocol."""

        address = transaction.address()
        dataBa = bytearray(transaction.size())
        transaction.getData(dataBa, 0)
        dataWords = [int.from_bytes(dataBa[i:i+4], 'little', signed=False) for i in range(0, len(dataBa), 4)]

        # Need to issue a UART command for each 32 bit word
        for i, (addr, data) in enumerate(zip(range(address, address+len(dataBa), 4), dataWords)):
            sendString = f'w {addr:08x} {data:08x} \n'.encode('ASCII')
            self._log.debug("Sending write transaction part %s: %r", i, sendString)
            self.serialPort.write(sendString)
            response = self.readline() #self.serialPort.readline().decode('ASCII')

            # If response is empty, a timeout occurred
            if len(response) == 0:
                transaction.error(f'Empty transaction response (likely timeout) for transaction part {i}: {repr(sendString)}')
                return

            # parse the response string
            parts = response.split()

            # Check for correct response
            if (len(parts) != 4 or parts[0].lower() != 'w' or int(parts[1], 16) != addr or int(parts[2],16) != data):
                transaction.error(f'Malformed response for part {i}: {repr(response)} to transaction: {repr(sendString)}')
                return
            else:
                self._log.debug("Write transaction part %s completed successfully", i)

            # Check response code
            resp = int(parts[3],16)

            if resp != 0:
                transaction.error(f"Non zero status message returned on axi bus in hardware: {resp:#x}")
                return

        self._log.debug(
            "Completed UART write transaction: address=%#x, size=%s",
            address,
            len(dataBa),
        )
        transaction.done()


    def _doRead(self, transaction: rogue.interfaces.memory.Transaction) -> None:
        """Execute a read transaction over the UART register protocol."""

        address = transaction.address()
        size = transaction.size()

        for i, addr in enumerate(range(address, address+size, 4)):
            sendString = f'r {addr:08x} \n'.encode('ASCII')
            self._log.debug("Sending read transaction part %s: %r", i, sendString)
            self.serialPort.write(sendString)
            response = self.readline() #self.serialPort.readline().decode('ASCII')

            # If response is empty, a timeout occurred
            if len(response) == 0:
                transaction.error(f'Empty transaction response (likely timeout) for transaction part {i}: {repr(sendString)}')
                return

            # parse the response string
            parts = response.split()

            if (len(parts) != 4 or parts[0].lower() != 'r' or int(parts[1], 16) != addr):
                transaction.error(f'Malformed response part {i}: {repr(response)} to transaction: {repr(sendString)}')
            else:
                dataInt = int(parts[2], 16)
                rdData = bytearray(dataInt.to_bytes(4, 'little', signed=False))
                transaction.setData(rdData, i*4)
                self._log.debug(
                    "Read transaction part %s completed successfully with data=%#08x",
                    i,
                    dataInt,
                )

            # Check response code
            resp = int(parts[3],16)

            if resp != 0:
                transaction.error(f"Non zero status message returned on axi bus in hardware: {resp:#x}")
                return

        self._log.debug(
            "Completed UART read transaction: address=%#x, size=%s",
            address,
            size,
        )
        transaction.done()


    def _worker(self) -> None:
        """Worker thread that processes queued memory transactions."""
        while True:
            transaction = self._workerQueue.get()

            if transaction is None:
                self._workerQueue.task_done()
                break

            try:
                with transaction.lock():

                    # Write path
                    if transaction.type() == rogue.interfaces.memory.Write:
                        self._doWrite(transaction)

                    elif (transaction.type() == rogue.interfaces.memory.Read or transaction.type() == rogue.interfaces.memory.Verify):
                        self._doRead(transaction)
                    else:
                        # Posted writes not supported (for now)
                        transaction.error(f'Unsupported transaction type: {transaction.type()}')
            except Exception as e:
                pyrogue.logException(self._log, e)
                transaction.error(f'Unhandled UART worker exception: {e}')
            finally:
                self._workerQueue.task_done()
