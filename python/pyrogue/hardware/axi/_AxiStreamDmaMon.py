#-----------------------------------------------------------------------------
# Company: SLAC National Accelerator Laboratory
#-----------------------------------------------------------------------------
# Description: Module for monitoring the DMA kernel driver
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

class AxiStreamDmaMonRx(pr.Device):
    def __init__(self, axiStreamDma, pollInterval=1, **kwargs):
        super(self.__class__, self).__init__(**kwargs)

        # Create a pointer to the AXI Stream DMA object
        self._dma = axiStreamDma

        # Add variables
        self.add(pr.LocalVariable(
            name        = 'BuffCount',
            description = 'Get the number of RX buffers',
            mode        = 'RO',
            value       = 0,
            typeStr     = 'UInt32',
            localGet    = lambda: self._dma.getRxBuffCount(),
        ))

        self.add(pr.LocalVariable(
            name        = 'BuffinUserCount',
            description = 'RX buffer in User count',
            mode        = 'RO',
            value       = 0,
            typeStr     = 'UInt32',
            localGet    = lambda: self._dma.getRxBuffinUserCount(),
            pollInterval= pollInterval,
        ))

        self.add(pr.LocalVariable(
            name        = 'BuffinHwCount',
            description = 'RX buffer in HW count',
            mode        = 'RO',
            value       = 0,
            typeStr     = 'UInt32',
            localGet    = lambda: self._dma.getRxBuffinHwCount(),
            pollInterval= pollInterval,
        ))

        self.add(pr.LocalVariable(
            name        = 'BuffinPreHwQCount',
            description = 'RX buffer in Pre-HW Queue count',
            mode        = 'RO',
            value       = 0,
            typeStr     = 'UInt32',
            localGet    = lambda: self._dma.getRxBuffinPreHwQCount(),
            pollInterval= pollInterval,
        ))

        self.add(pr.LocalVariable(
            name        = 'BuffinSwQCount',
            description = 'RX buffer in SW Queue count',
            mode        = 'RO',
            value       = 0,
            typeStr     = 'UInt32',
            localGet    = lambda: self._dma.getRxBuffinSwQCount(),
            pollInterval= pollInterval,
        ))

        self.add(pr.LocalVariable(
            name        = 'BuffMissCount',
            description = 'RX buffer missing count',
            mode        = 'RO',
            value       = 0,
            typeStr     = 'UInt32',
            localGet    = lambda: self._dma.getRxBuffMissCount(),
            pollInterval= pollInterval,
        ))

class AxiStreamDmaMonTx(pr.Device):
    def __init__(self, axiStreamDma, pollInterval=1, **kwargs):
        super(self.__class__, self).__init__(**kwargs)

        # Create a pointer to the AXI Stream DMA object
        self._dma = axiStreamDma

        # Add variables
        self.add(pr.LocalVariable(
            name        = 'BuffCount',
            description = 'Get the number of TX buffers',
            mode        = 'RO',
            value       = 0,
            typeStr     = 'UInt32',
            localGet    = lambda: self._dma.getTxBuffCount(),
        ))

        self.add(pr.LocalVariable(
            name        = 'BuffinUserCount',
            description = 'TX buffer in User count',
            mode        = 'RO',
            value       = 0,
            typeStr     = 'UInt32',
            localGet    = lambda: self._dma.getTxBuffinUserCount(),
            pollInterval= pollInterval,
        ))

        self.add(pr.LocalVariable(
            name        = 'BuffinHwCount',
            description = 'TX buffer in HW count',
            mode        = 'RO',
            value       = 0,
            typeStr     = 'UInt32',
            localGet    = lambda: self._dma.getTxBuffinHwCount(),
            pollInterval= pollInterval,
        ))

        self.add(pr.LocalVariable(
            name        = 'BuffinPreHwQCount',
            description = 'TX buffer in Pre-HW Queue count',
            mode        = 'RO',
            value       = 0,
            typeStr     = 'UInt32',
            localGet    = lambda: self._dma.getTxBuffinPreHwQCount(),
            pollInterval= pollInterval,
        ))

        self.add(pr.LocalVariable(
            name        = 'BuffinSwQCount',
            description = 'TX buffer in SW Queue count',
            mode        = 'RO',
            value       = 0,
            typeStr     = 'UInt32',
            localGet    = lambda: self._dma.getTxBuffinSwQCount(),
            pollInterval= pollInterval,
        ))

        self.add(pr.LocalVariable(
            name        = 'BuffMissCount',
            description = 'TX buffer missing count',
            mode        = 'RO',
            value       = 0,
            typeStr     = 'UInt32',
            localGet    = lambda: self._dma.getTxBuffMissCount(),
            pollInterval= pollInterval,
        ))

class AxiStreamDmaMon(pr.Device):
    def __init__(self, axiStreamDma, pollInterval=1, **kwargs):
        super(self.__class__, self).__init__(**kwargs)

        # Create a pointer to the AXI Stream DMA object
        self._dma = axiStreamDma

        # Add variables
        self.add(pr.LocalVariable(
            name        = 'GitVersion',
            description = 'DMA\'s Driver GIT Version string',
            mode        = 'RO',
            value       = '',
            localGet    = lambda: self._dma.getGitVersion(),
        ))

        self.add(pr.LocalVariable(
            name        = 'ApiVersion',
            description = 'DMA\'s Driver API Version',
            mode        = 'RO',
            value       = 0x0,
            typeStr     = 'UInt8',
            units       = 'Bytes',
            disp        = '{:#x}',
            localGet    = lambda: self._dma.getApiVersion(),
        ))

        self.add(pr.LocalVariable(
            name        = 'BuffSize',
            description = 'Size of buffers (RX/TX)',
            mode        = 'RO',
            value       = 0x0,
            typeStr     = 'UInt32',
            units       = 'Bytes',
            disp        = '{:#x}',
            localGet    = lambda: self._dma.getBuffSize(),
        ))

        self.add(AxiStreamDmaMonRx(
            name         = 'Rx',
            axiStreamDma = axiStreamDma,
            pollInterval = pollInterval,
        ))

        self.add(AxiStreamDmaMonTx(
            name         = 'Tx',
            axiStreamDma = axiStreamDma,
            pollInterval = pollInterval,
        ))
