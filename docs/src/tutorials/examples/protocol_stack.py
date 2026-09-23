#!/usr/bin/env python3
#-----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
#-----------------------------------------------------------------------------
#  Description:
#       Protocol stack tutorial: reach registers through SRP, then through a
#       TCP bridge, then through a full UDP + RSSI + packetizer stack.
#
#       Runs with no hardware. This file is included into
#       docs/src/tutorials/protocol_stack.rst and is exercised by
#       tests/docs/test_docs_tutorial_examples.py.
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

import time

import pyrogue as pr
import pyrogue.protocols
import rogue.interfaces.memory
import rogue.protocols.srp


class ScratchDevice(pr.Device):
    """One read/write register, used to prove each transport works."""

    def __init__(self, **kwargs):
        super().__init__(description='Register map reached over a protocol stack',
                         **kwargs)

        self.add(pr.RemoteVariable(
            name        = 'ScratchPad',
            description = 'Read/write test register',
            offset      = 0x04,
            bitSize     = 32,
            base        = pr.UInt,
            mode        = 'RW',
            disp        = '{:#010x}'))


class SrpRoot(pr.Root):
    """Stage 1: SRPv3 talking to a software SRP endpoint.

    ``SrpV3Emulation`` answers SRP requests from an internal memory store, so
    the whole register path is exercised with no transport and no hardware.
    """

    def __init__(self, **kwargs):
        super().__init__(description='SRP over emulation', timeout=2.0, **kwargs)

        self._srp = rogue.protocols.srp.SrpV3()
        self._emu = rogue.protocols.srp.SrpV3Emulation()

        # Bi-directional: requests flow to the emulator, responses come back.
        self._srp == self._emu

        self.addInterface(self._srp)
        self.addInterface(self._emu)

        self.add(ScratchDevice(name='Dev', memBase=self._srp, offset=0x0))


class TcpBridgeRoot(pr.Root):
    """Stage 2: the same register path crossing a TCP socket.

    ``TcpServer`` fronts the memory slave and ``TcpClient`` feeds the Device.
    In a real system these two halves live in different processes, or on
    different machines; here both ends run locally so the example is runnable.
    """

    def __init__(self, port=11000, **kwargs):
        super().__init__(description='Registers over a TCP bridge',
                         timeout=5.0, **kwargs)

        self._sim = rogue.interfaces.memory.Emulate(4, 0x1000)

        # Server side: bridge -> emulated memory space.
        self._server = rogue.interfaces.memory.TcpServer('127.0.0.1', port)
        self._server >> self._sim

        # Client side: Device -> bridge.
        self._client = rogue.interfaces.memory.TcpClient('127.0.0.1', port)

        for interface in (self._sim, self._server, self._client):
            self.addInterface(interface)

        self.add(ScratchDevice(name='Dev', memBase=self._client, offset=0x0))


class NetworkRoot(pr.Root):
    """Stage 3: UDP + RSSI + packetizer + SRP, client and server on loopback.

    ``UdpRssiPack`` bundles the three transport layers that normally sit
    between a host and a board. Running it twice -- once with ``server=True``
    -- gives a complete link with no NIC or firmware involved.
    """

    def __init__(self, port=8192, **kwargs):
        super().__init__(description='Registers over UDP + RSSI + packetizer',
                         timeout=10.0, **kwargs)

        # Firmware side: server transport with an SRP endpoint behind it.
        self._server = pr.protocols.UdpRssiPack(
            name='Server', host='127.0.0.1', port=port,
            server=True, jumbo=False, wait=False, packVer=2)
        self.add(self._server)

        self._emu = rogue.protocols.srp.SrpV3Emulation()
        self.addInterface(self._emu)
        self._server.application(0) == self._emu

        # Host side: client transport driving an SRP master.
        self._client = pr.protocols.UdpRssiPack(
            name='Client', host='127.0.0.1', port=port,
            server=False, jumbo=False, wait=False, packVer=2)
        self.add(self._client)

        self._srp = rogue.protocols.srp.SrpV3()
        self.addInterface(self._srp)
        self._client.application(0) == self._srp

        self.add(ScratchDevice(name='Dev', memBase=self._srp, offset=0x0))

    def waitForLink(self, timeout=15.0):
        """Block until RSSI reports the link open.

        RSSI performs a handshake, so the link is not usable the instant the
        tree starts. Poll rather than guessing a sleep duration.
        """
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.Client.rssiOpen.get():
                return True
            time.sleep(0.25)
        return False


if __name__ == '__main__':
    print('--- Stage 1: SRP over emulation')
    with SrpRoot() as root:
        root.Dev.ScratchPad.set(0xCAFEBABE)
        print('   ScratchPad =', root.Dev.ScratchPad.valueDisp())

    print('--- Stage 2: registers over a TCP bridge')
    with TcpBridgeRoot() as root:
        time.sleep(1.0)   # let the socket pair establish
        root.Dev.ScratchPad.set(0xABCD1234)
        print('   ScratchPad =', root.Dev.ScratchPad.valueDisp())

    print('--- Stage 3: registers over UDP + RSSI + packetizer')
    with NetworkRoot() as root:
        print('   rssi link open:', root.waitForLink())
        root.Dev.ScratchPad.set(0xFEEDFACE)
        print('   ScratchPad =', root.Dev.ScratchPad.valueDisp())
