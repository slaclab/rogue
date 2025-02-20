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

        if address not in self._cmdList:
            transaction.error(f"Transaction address {address:#08x} not found in os command list")
            return

        # Write
        if type == rogue.interfaces.memory.Write or type == rogue.interfaces.memory.Post:

            try:
                ba = bytearray(size)
                transaction.getData(ba,0)

                arg = self._cmdList[address]['base'].fromBytes(ba)
                self._cmdList[address]['func'](self,arg=arg)
                transaction.done()
            except Exception as msg:
                transaction.error(f"Transaction write error in command at {address:#08x}: {msg}")

        # Read
        else:

            try:
                ret = self._cmdList[address]['func'](self,arg=None)
                ba = self._cmdList[address]['base'].toBytes(ret)

                transaction.setData(ba,0)
                transaction.done()

            except Exception as msg:
                transaction.error(f"Transaction read error in command at {address:#08x}: {msg}")

    def command(self, addr, base):
        def _decorator(func):

            if addr in self._cmdList:
                raise pyrogue.CommandError("Duplicate address in command generation")

            self._cmdList[addr] = {'base' : base, 'func' : func}

            return func
        return _decorator
