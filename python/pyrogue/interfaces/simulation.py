#-----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
#-----------------------------------------------------------------------------
# Description:
# Module containing simulation support classes and routines
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

import threading
import pyrogue
import rogue.interfaces.stream
import zmq
from typing import Any, Callable


class SideBandSim():
    """Sideband simulator using paired ZMQ sockets.

    Parameters
    ----------
    host : str
        Hostname or IP address.
    port : int
        Base sideband port.
    """

    def __init__(self, host: str, port: int) -> None:
        self._log = pyrogue.logInit(cls=self, name=f'{host}.{port}')

        self._ctx = zmq.Context()
        self._sbPush = self._ctx.socket(zmq.PUSH)
        self._sbPush.connect(f"tcp://{host}:{port+1}")
        self._sbPull = self._ctx.socket(zmq.PULL)
        self._sbPull.connect(f"tcp://{host}:{port}")

        self._log.info("Connected to port %s on host %s", port, host)

        self._recvCb = self._defaultRecvCb
        self._lock = threading.Lock()
        self._run = True
        self._recvThread = threading.Thread(target=self._recvWorker)
        self._recvThread.start()

    def _defaultRecvCb(self, opCode: int | None, remData: int | None) -> None:
        """Default callback that prints received opCode and remData."""
        if opCode is not None:
            print(f'Received opCode: {opCode:02x}')
        if remData is not None:
            print(f'Received remData: {remData:02x}')

    def setRecvCb(self, cbFunc: Callable[[int | None, int | None], Any]) -> None:
        """Set the callback for received sideband data.

        Parameters
        ----------
        cbFunc : callable
            Callback of the form ``cbFunc(opCode, remData)``.
        """
        self._recvCb = cbFunc

    def send(self, opCode: int | None = None, remData: int | None = None) -> None:
        """Send opCode and/or remData on the sideband channel.

        Parameters
        ----------
        opCode : int, optional
            Operation code to send.
        remData : int, optional
            Remote data byte to send.
        """
        ba = bytearray(4)
        if opCode is not None:
            ba[0] = 0x01
            ba[1] = opCode
        if remData is not None:
            ba[2] = 0x01
            ba[3] = remData

        self._sbPush.send(ba)
        self._log.debug("Sent opCode=%s remData=%s", opCode, remData)

    def _stop(self) -> None:
        """Stop the receive thread."""
        with self._lock:
            self._log.debug('Stopping receive thread')
            self._run = False

    def __enter__(self) -> "SideBandSim":
        """Return self for context-manager use."""
        return self

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        """Stop receive worker on context-manager exit."""
        self._stop()

    def _recvWorker(self) -> None:
        """Worker thread that receives sideband data and invokes the callback."""
        while True:
            # Exit thread when stop() called
            with self._lock:
                if self._run is False:
                    self._log.debug('Exiting receive thread')
                    return

            # Wait for new data
            socks, x, y = zmq.select([self._sbPull], [], [], 1.0)
            if self._sbPull in socks:
                ba = self._sbPull.recv()

                if len(ba) != 4:
                    self._log.error("Got bad size frame: %r size: %s", ba, len(ba))

                # Got normal data
                opCode = None
                remData = None
                if ba[0] == 0x01:
                    opCode = ba[1]
                if ba[2] == 0x01:
                    remData = ba[3]

                self._log.debug("Received opCode=%s remData=%s", opCode, remData)
                self._recvCb(opCode, remData)


class Pgp2bSim():
    """Simulated PGP2B with virtual channels and sideband.

    Parameters
    ----------
    vcCount : int
        Number of virtual channels.
    host : str
        Host address.
    port : int
        Base port number.
    """

    def __init__(self, vcCount: int, host: str, port: int) -> None:
        # virtual channels
        self.vc = [rogue.interfaces.stream.TcpClient(host, p) for p in range(port, port+(vcCount*2), 2)]

        # sideband
        self.sb = SideBandSim(host, port+8)

    def _stop(self) -> None:
        """Stop the sideband simulation."""
        self.sb._stop()

    def __enter__(self) -> "Pgp2bSim":
        """Return self for context-manager use."""
        return self

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        """Stop simulator resources on context-manager exit."""
        self._stop()


def connectPgp2bSim(pgpA: "Pgp2bSim", pgpB: "Pgp2bSim") -> None:
    """Connect two PGP2B simulators bidirectionally.

    Parameters
    ----------
    pgpA : Pgp2bSim
        First PGP2B simulator.
    pgpB : Pgp2bSim
        Second PGP2B simulator.
    """
    for a,b in zip(pgpA.vc, pgpB.vc):
        pyrogue.streamConnectBiDir(a, b)

    pgpA.sb.setRecvCb(pgpB.sb.send)
    pgpB.sb.setRecvCb(pgpA.sb.send)


class MemEmulate(rogue.interfaces.memory.Slave):
    """In-memory emulation of a memory slave device.

    Parameters
    ----------
    minWidth : int, optional
        Minimum access width in bytes.
    maxSize : int, optional
        Maximum transaction size in bytes.
    dropCount : int, optional
        Number of transactions to drop before accepting (for testing).
    """

    def __init__(
        self,
        *,
        minWidth: int = 4,
        maxSize: int = 0xFFFFFFFF,
        dropCount: int = 0,
    ) -> None:
        rogue.interfaces.memory.Slave.__init__(self,4,4)
        self._minWidth = minWidth
        self._maxSize  = maxSize
        self._data = {}
        self._cb   = {}

        self._count = 0
        self._dropCount = dropCount

    def _checkRange(self, address: int, size: int) -> int:
        """Check if address range is valid. Returns 0 for valid."""
        return 0

    def _doMaxAccess(self) -> int:
        """Return maximum access size."""
        return self._maxSize

    def _doMinAccess(self) -> int:
        """Return minimum access width."""
        return self._minWidth

    def _doTransaction(self, transaction: Any) -> None:
        """Process a memory read or write transaction."""
        address = transaction.address()
        size    = transaction.size()
        type    = transaction.type()

        if self._count < self._dropCount:
            self._count += 1
            return

        self._count = 0

        if (address % self._minWidth) != 0:
            transaction.error(
                f"Transaction address {address:#x} is not aligned to min width {self._minWidth:#x}"
            )
            return
        elif size > self._maxSize:
            transaction.error(f"Transaction size {size} exceeds max {self._maxSize}")
            return

        for i in range (0, size):
            if not (address+i) in self._data:
                self._data[address+i] = 0

        ba = bytearray(size)

        if type == rogue.interfaces.memory.Write or type == rogue.interfaces.memory.Post:
            transaction.getData(ba,0)

            for i in range(0, size):
                self._data[address+i] = ba[i]

            transaction.done()

        else:
            for i in range(0, size):
                ba[i] = self._data[address+i]

            transaction.setData(ba,0)
            transaction.done()
