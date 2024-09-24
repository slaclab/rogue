#!/usr/bin/env python3
#-----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
#-----------------------------------------------------------------------------
#  Description:
#       Large Device Test Group
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
import pyrogue

class LargeDevice(pyrogue.Device):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


        for i in range(4096):
            b = (i // 100) * 100
            t = (i // 100) * 100 + 99
            self.add(pyrogue.LocalVariable(
                name = f'TestValue[{i}]',
                mode = 'RW',
                guiGroup=f'TestLargeGroup[{b}-{t}]',
                value = 0))
