#-----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
#-----------------------------------------------------------------------------
# Description:
# OS Command Slave Module
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
import rogue.interfaces.stream

class OsCommandMemorySlave(rogue.interfaces.memory.Slave):

    def __init__(self, *, minWidth=4, maxSize=1024):
        rogue.interfaces.memory.Slave.__init__(self,minWidth,maxSize)
        self._cmdList = {}

    def _doTransaction(self,transaction):
        address = transaction.address()
        size    = transaction.size()
        type    = transaction.type()

        if (address % self._minWidth) != 0:
            transaction.error("Transaction address {address:#x} is not aligned to min width {self._minWidth:#x}")
            return
        elif size > self._maxSize:
            transaction.error("Transaction size {size} exceeds max {self._maxSize}")
            return
        elif address not in self._cmdList:
            transaction.error("Transaction address {address:#08x} not found in os command list")
            return

        # Write
        if type == rogue.interfaces.memory.Write or type == rogue.interfaces.memory.Post:

            try:
                ba = bytearray(size)
                transaction.getData(ba,0)

                arg = self._cmdList['base'].fromBytes(ba)
                self._cmdList.['func'](arg=arg)
                transaction.done()
            except Exception:
                transaction.error("Transaction write error in command at {address:#08x}")

        # Read
        else:

            try:
                ret = self._cmdList.['func'](arg=None)
                ba = self._cmdList['base'].toBytes(ret)

                transaction.setData(ba,0)
                transaction.done()

            except Exception:
                transaction.error("Transaction read error in command at {address:#08x}")

    def command(self, *, addr, base):
        def _decorator(func):

            if addr in self._cmdList:
                raise pyrogue.CommandError(f"Duplicate address in command generation")

            self._cmdList[addr] = {'base' : base, 'func' : func}

            return func
        return _decorator

