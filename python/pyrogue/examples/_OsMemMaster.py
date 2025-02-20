#-----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
#-----------------------------------------------------------------------------
# Description:
# Example device talking to a Os Command Memory Slave
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

class OsMemMaster(pr.Device):

    # Last comment added by rherbst for demonstration.
    def __init__(
            self,
            name             = 'OsMemMaster',
            description      = 'OS Memory Master Device',
            **kwargs):

        super().__init__(
            name        = name,
            description = description,
            **kwargs)

        ##############################
        # Variables
        ##############################

        self.add(pr.RemoteVariable(
            name         = 'Uptime',
            description  = 'System Uptime In Seconds',
            offset       = 0x00,
            bitSize      = 32,
            base         = pr.Float,
            mode         = 'RO',
            pollInterval = 1
        ))

        self.add(pr.RemoteVariable(
            name         = 'SysLoad1Min',
            description  = '1 Minute System Load',
            offset       = 0x04,
            bitSize      = 32,
            base         = pr.Float,
            mode         = 'RO',
            pollInterval = 1
        ))

        self.add(pr.RemoteVariable(
            name         = 'SysLoad5Min',
            description  = '5 Minute System Load',
            offset       = 0x08,
            bitSize      = 32,
            base         = pr.Float,
            mode         = 'RO',
            pollInterval = 1
        ))

        self.add(pr.RemoteVariable(
            name         = 'SysLoad15Min',
            description  = '15 Minute System Load',
            offset       = 0x0C,
            bitSize      = 32,
            base         = pr.Float,
            mode         = 'RO',
            pollInterval = 1
        ))

        self.add(pr.RemoteVariable(
            name         = 'FileTest',
            description  = 'File Read Write Test',
            offset       = 0x10,
            bitSize      = 32,
            base         = pr.UInt,
            mode         = 'RW',
        ))


