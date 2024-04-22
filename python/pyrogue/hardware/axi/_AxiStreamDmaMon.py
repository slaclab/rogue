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

class AxiStreamDmaMon(pr.Device):
    def __init__(self, axiStreamDma, pollInterval=1, **kwargs):
        super(self.__class__, self).__init__(**kwargs)

        # Create a pointer to the AXI Stream DMA object
        self._dma = axiStreamDma

        # Add variables
        self.add(pr.LocalVariable(
            name        = 'BuffSize',
            description = 'size of buffers (RX/TX)',
            mode        = 'RO',
            value       = 0x0,
            typeStr     = 'UInt32',
            units       = 'Bytes',
            disp        = '{:#x}',
            localGet    = lambda: self._dma.getBuffSize(),
        ))

        self.add(pr.LocalVariable(
            name        = 'RxBuffCount',
            description = 'Get the number of RX buffers',
            mode        = 'RO',
            value       = 0,
            typeStr     = 'UInt32',
            localGet    = lambda: self._dma.getRxBuffCount(),
        ))

        self.add(pr.LocalVariable(
            name        = 'TxBuffCount',
            description = 'Get the number of TX buffers',
            mode        = 'RO',
            value       = 0,
            typeStr     = 'UInt32',
            localGet    = lambda: self._dma.getTxBuffCount(),
        ))

        self.add(pr.LocalVariable(
            name        = 'TxBuffinUserCount',
            description = 'TX buffer in User count',
            mode        = 'RO',
            value       = 0,
            typeStr     = 'UInt32',
            localGet    = lambda: self._dma.getTxBuffinUserCount(),
            pollInterval= pollInterval,
        ))

        self.add(pr.LocalVariable(
            name        = 'TxBuffinHwCount',
            description = 'TX buffer in HW count',
            mode        = 'RO',
            value       = 0,
            typeStr     = 'UInt32',
            localGet    = lambda: self._dma.getTxBuffinHwCount(),
            pollInterval= pollInterval,
        ))

        self.add(pr.LocalVariable(
            name        = 'TxBuffinPreHwQCount',
            description = 'TX buffer in Pre-HW Queue count',
            mode        = 'RO',
            value       = 0,
            typeStr     = 'UInt32',
            localGet    = lambda: self._dma.getTxBuffinPreHwQCount(),
            pollInterval= pollInterval,
        ))

        self.add(pr.LocalVariable(
            name        = 'TxBuffinSwQCount',
            description = 'TX buffer in SW Queue count',
            mode        = 'RO',
            value       = 0,
            typeStr     = 'UInt32',
            localGet    = lambda: self._dma.getTxBuffinSwQCount(),
            pollInterval= pollInterval,
        ))

        self.add(pr.LocalVariable(
            name        = 'getTxBuffMissCount',
            description = 'TX buffer missing count',
            mode        = 'RO',
            value       = 0,
            typeStr     = 'UInt32',
            localGet    = lambda: self._dma.getTxBuffMissCount(),
            pollInterval= pollInterval,
        ))
