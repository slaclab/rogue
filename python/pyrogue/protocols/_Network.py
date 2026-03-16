#-----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
#-----------------------------------------------------------------------------
# Description:
#       PyRogue protocols / Network wrappers
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
import pyrogue as pr
import rogue.protocols.udp
import rogue.protocols.rssi
import rogue.protocols.packetizer
import time
import threading
from typing import Any


class UdpRssiPack(pr.Device):
    """
    UDP-based network device with RSSI and Packetizer protocols.

    Combines UDP transport with reliable stream protocol (rUDP) and packetizer
    for communication over network links.

    Parameters
    ----------
    port : int
        UDP port number for the connection.
    host : str, optional
        Host address.
    jumbo : bool, optional
        Enable jumbo frames.
    wait : bool, optional
        Wait for link-up before finishing start.
    packVer : int, optional
        Packetizer version (1 or 2).
    pollInterval : int, optional
        Poll interval in seconds for status variables.
    enSsi : bool, optional
        Enable SSI in the packetizer.
    server : bool, optional
        Run as server instead of client.
    **kwargs : Any
        Additional arguments passed to :class:`pyrogue.Device`.
    """

    def __init__(
        self,
        *,
        port: int,
        host: str = '127.0.0.1',
        jumbo: bool = False,
        wait: bool = True,
        packVer: int = 1,
        pollInterval: int = 1,
        enSsi: bool = True,
        server: bool = False,
        **kwargs: Any,
    ) -> None:
        super(self.__class__, self).__init__(**kwargs)

        # Local copy host/port arg values
        self._host = host
        self._port = port
        self._wait = wait
        self._jumbo = jumbo
        self._server = server
        self._rxBufferConfigured = False
        self._rxBufferThreadStop = False

        # Check if running as server
        if server:
            self._udp  = rogue.protocols.udp.Server(port,jumbo)
            self._rssi = rogue.protocols.rssi.Server(self._udp.maxPayload()-8)

        # Else running as client
        else:
            self._udp  = rogue.protocols.udp.Client(host,port,jumbo)
            self._rssi = rogue.protocols.rssi.Client(self._udp.maxPayload()-8)

        # Check if Packeterizer Version 2: https://confluence.slac.stanford.edu/x/3nh4DQ
        if packVer == 2:
            self._pack = rogue.protocols.packetizer.CoreV2(False,True,enSsi) # ibCRC = False, obCRC = True

        # Else using Packeterizer Version 1: https://confluence.slac.stanford.edu/x/1oyfD
        else:
            self._pack = rogue.protocols.packetizer.Core(enSsi)

        # Connect the streams together
        self._udp == self._rssi.transport()
        self._rssi.application() == self._pack.transport()

        # Set any user override of defaults
        defaults = kwargs.get('defaults', {})
        param_setters = {
            'locMaxBuffers' : self._rssi.setLocMaxBuffers,
            'locCumAckTout' : self._rssi.setLocCumAckTout,
            'locRetranTout' : self._rssi.setLocRetranTout,
            'locNullTout'   : self._rssi.setLocNullTout,
            'locMaxRetran'  : self._rssi.setLocMaxRetran,
            'locMaxCumAck'  : self._rssi.setLocMaxCumAck,
        }
        for key, setter in param_setters.items():
            if key in defaults:
                setter(defaults[key])

        # Add variables
        self.add(pr.LocalVariable(
            name        = 'rssiOpen',
            mode        = 'RO',
            value       = False,
            localGet    = lambda: self._rssi.getOpen(),
            pollInterval= pollInterval,
        ))

        self.add(pr.LocalVariable(
            name        = 'rssiDownCount',
            mode        = 'RO',
            value       = 0,
            typeStr     = 'UInt32',
            localGet    = lambda: self._rssi.getDownCount(),
            pollInterval= pollInterval,
        ))

        self.add(pr.LocalVariable(
            name        = 'rssiDropCount',
            mode        = 'RO',
            value       = 0,
            typeStr     = 'UInt32',
            localGet    = lambda: self._rssi.getDropCount(),
            pollInterval= pollInterval,
        ))

        self.add(pr.LocalVariable(
            name        = 'rssiRetranCount',
            mode        = 'RO',
            value       = 0,
            typeStr     = 'UInt32',
            localGet    = lambda: self._rssi.getRetranCount(),
            pollInterval= pollInterval,
        ))

        self.add(pr.LocalVariable(
            name        = 'locBusy',
            mode        = 'RO',
            value       = True,
            localGet    = lambda: self._rssi.getLocBusy(),
            hidden      = True,
            pollInterval= pollInterval,
        ))

        self.add(pr.LocalVariable(
            name        = 'locBusyCnt',
            mode        = 'RO',
            value       = 0,
            typeStr     = 'UInt32',
            localGet    = lambda: self._rssi.getLocBusyCnt(),
            pollInterval= pollInterval,
        ))

        self.add(pr.LocalVariable(
            name        = 'remBusy',
            mode        = 'RO',
            value       = True,
            localGet    = lambda: self._rssi.getRemBusy(),
            hidden      = True,
            pollInterval= pollInterval,
        ))

        self.add(pr.LocalVariable(
            name        = 'remBusyCnt',
            mode        = 'RO',
            value       = 0,
            typeStr     = 'UInt32',
            localGet    = lambda: self._rssi.getRemBusyCnt(),
            pollInterval= pollInterval,
        ))

        self.add(pr.LocalVariable(
            name        = 'locTryPeriod',
            mode        = 'RW',
            value       = self._rssi.getLocTryPeriod(),
            typeStr     = 'UInt32',
            localGet    = lambda: self._rssi.getLocTryPeriod(),
            localSet    = lambda value: self._rssi.setLocTryPeriod(value)
        ))

        self.add(pr.LocalVariable(
            name        = 'locMaxBuffers',
            mode        = 'RW',
            value       = self._rssi.getLocMaxBuffers(),
            typeStr     = 'UInt8',
            localGet    = lambda: self._rssi.getLocMaxBuffers(),
            localSet    = lambda value: self._rssi.setLocMaxBuffers(value)
        ))

        self.add(pr.LocalVariable(
            name        = 'locMaxSegment',
            mode        = 'RW',
            value       = self._rssi.getLocMaxSegment(),
            typeStr     = 'UInt16',
            localGet    = lambda: self._rssi.getLocMaxSegment(),
            localSet    = lambda value: self._rssi.setLocMaxSegment(value)
        ))

        self.add(pr.LocalVariable(
            name        = 'locCumAckTout',
            mode        = 'RW',
            value       = self._rssi.getLocCumAckTout(),
            typeStr     = 'UInt16',
            localGet    = lambda: self._rssi.getLocCumAckTout(),
            localSet    = lambda value: self._rssi.setLocCumAckTout(value)
        ))

        self.add(pr.LocalVariable(
            name        = 'locRetranTout',
            mode        = 'RW',
            value       = self._rssi.getLocRetranTout(),
            typeStr     = 'UInt16',
            localGet    = lambda: self._rssi.getLocRetranTout(),
            localSet    = lambda value: self._rssi.setLocRetranTout(value)
        ))

        self.add(pr.LocalVariable(
            name        = 'locNullTout',
            mode        = 'RW',
            value       = self._rssi.getLocNullTout(),
            typeStr     = 'UInt16',
            localGet    = lambda: self._rssi.getLocNullTout(),
            localSet    = lambda value: self._rssi.setLocNullTout(value)
        ))

        self.add(pr.LocalVariable(
            name        = 'locMaxRetran',
            mode        = 'RW',
            value       = self._rssi.getLocMaxRetran(),
            typeStr     = 'UInt8',
            localGet    = lambda: self._rssi.getLocMaxRetran(),
            localSet    = lambda value: self._rssi.setLocMaxRetran(value)
        ))

        self.add(pr.LocalVariable(
            name        = 'locMaxCumAck',
            mode        = 'RW',
            value       = self._rssi.getLocMaxCumAck(),
            typeStr     = 'UInt8',
            localGet    = lambda: self._rssi.getLocMaxCumAck(),
            localSet    = lambda value: self._rssi.setLocMaxCumAck(value)
        ))

        self.add(pr.LocalVariable(
            name        = 'curMaxBuffers',
            mode        = 'RO',
            value       = 0,
            typeStr     = 'UInt8',
            localGet    = lambda: self._rssi.curMaxBuffers(),
            pollInterval= pollInterval
        ))

        self.add(pr.LocalVariable(
            name        = 'curMaxSegment',
            mode        = 'RO',
            value       = 0,
            typeStr     = 'UInt16',
            localGet    = lambda: self._rssi.curMaxSegment(),
            pollInterval= pollInterval
        ))

        self.add(pr.LocalVariable(
            name        = 'curCumAckTout',
            mode        = 'RO',
            value       = 0,
            typeStr     = 'UInt16',
            localGet    = lambda: self._rssi.curCumAckTout(),
            pollInterval= pollInterval
        ))

        self.add(pr.LocalVariable(
            name        = 'curRetranTout',
            mode        = 'RO',
            value       = 0,
            typeStr     = 'UInt16',
            localGet    = lambda: self._rssi.curRetranTout(),
            pollInterval= pollInterval
        ))

        self.add(pr.LocalVariable(
            name        = 'curNullTout',
            mode        = 'RO',
            value       = 0,
            typeStr     = 'UInt16',
            localGet    = lambda: self._rssi.curNullTout(),
            pollInterval= pollInterval
        ))

        self.add(pr.LocalVariable(
            name        = 'curMaxRetran',
            mode        = 'RO',
            value       = 0,
            typeStr     = 'UInt8',
            localGet    = lambda: self._rssi.curMaxRetran(),
            pollInterval= pollInterval
        ))

        self.add(pr.LocalVariable(
            name        = 'curMaxCumAck',
            mode        = 'RO',
            value       = 0,
            typeStr     = 'UInt8',
            localGet    = lambda: self._rssi.curMaxCumAck(),
            pollInterval= pollInterval
        ))

        self.add(pr.LocalCommand(
            name        = 'stop',
            function    = self._stop
        ))

        self.add(pr.LocalCommand(
            name        = 'start',
            function    = lambda: self._rssi._start()
        ))

    def application(self, dest: int) -> rogue.protocols.packetizer.Application:
        """
        Get the application interface for connecting to a destination.

        Parameters
        ----------
        dest : object
            Destination protocol/device to connect to.

        Returns
        -------
        object
            Application interface for the packetizer.
        """
        return self._pack.application(dest)

    def countReset(self) -> None:
        """Reset RSSI connection counters."""
        self._rssi.resetCounters()

    def _start(self) -> None:
        """Start RSSI/UDP transport and optionally wait for link-up."""
        # Start the RSSI connection
        self._rxBufferThreadStop = False
        self._rssi._start()

        if self._wait and not self._server:
            curr = int(time.time())
            last = curr
            cnt = 0

            while not self._rssi.getOpen():
                time.sleep(.0001)
                curr = int(time.time())
                if last != curr:
                    last = curr

                    if self._jumbo:
                        cnt += 1

                    if cnt < 10:
                        self._log.warning("host=%s, port=%d -> Establishing link ...", self._host, self._port)

                    else:
                        self._log.warning(
                            "host=%s, port=%d -> Failing to connect using jumbo frames. "
                            "Check interface MTU settings with ifconfig -a",
                            self._host,
                            self._port,
                        )

            self._log.info(
                "host=%s, port=%d -> Link established. jumbo=%s, maxPayload=%s",
                self._host,
                self._port,
                self._jumbo,
                self._udp.maxPayload(),
            )


        # On the client side, getOpen() only returns after negotiation is
        # complete, so curMaxBuffers() is stable here. On the server side,
        # waiting in _start() can deadlock if both endpoints are managed in the
        # same Root, so defer buffer programming until the link actually opens.
        if self._server:
            self._armServerRxBufferUpdate()
        else:
            self._applyNegotiatedRxBufferCount()

        super()._start()

    def _applyNegotiatedRxBufferCount(self) -> None:
        """Program UDP RX buffers from the negotiated RSSI max-buffer count."""
        if self._rxBufferConfigured:
            return

        self._udp.setRxBufferCount(self._rssi.curMaxBuffers())
        self._log.info(
            "host=%s, port=%d -> Configured UDP RX buffer count to %s",
            self._host,
            self._port,
            self._rssi.curMaxBuffers(),
        )
        self._rxBufferConfigured = True

    def _armServerRxBufferUpdate(self) -> None:
        """Wait for server-side RSSI open, then program the negotiated RX depth."""
        self._rxBufferConfigured = False

        def _wait_open() -> None:
            while not self._rxBufferThreadStop and not self._rssi.getOpen():
                time.sleep(0.0001)

            if not self._rxBufferThreadStop and self._rssi.getOpen():
                self._applyNegotiatedRxBufferCount()

        threading.Thread(target=_wait_open, daemon=True).start()

    def _stop(self) -> None:
        """Stop the UDP/RSSI connection and clean up resources."""
        self._rxBufferThreadStop = True
        self._rssi._stop()
        self._rxBufferConfigured = False

        # This Device may not necessarily be added to a tree
        # So check if it has a parent first
        if self.parent is not None:
            self.rssiOpen.get()
