#-----------------------------------------------------------------------------
# Title      : AXI Stream FIFO
#-----------------------------------------------------------------------------
# Description:
# Python wrapper for the AXI Stream FIFO C++ device.
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

import rogue
import pyrogue

class Fifo(pyrogue.Device):
    def __init__(self, *, name, description, maxDepth=0, trimSize=0, noCopy=False, **kwargs):
        pyrogue.Device.__init__(self, name=name, description=description, **kwargs)
        self._fifo = rogue.interfaces.stream.Fifo(maxDepth, trimSize, noCopy)

        # Maximum Depth
        self.add(pyrogue.LocalVariable(
            name='MaxDepth',
            description='Maximum depth of the Fifo',
            mode='RO',
            value=maxDepth))

        # Number of elements in the Fifo
        self.add(pyrogue.LocalVariable(
            name='Size',
            description='Number of elements in the Fifo',
            mode='RO',
            value=0,
            typeStr='UInt64',
            pollInterval=1,
            localGet=self._fifo.size))

        # Number of dropped frames
        self.add(pyrogue.LocalVariable(
            name='FrameDropCnt',
            description='Number of dropped frames',
            mode='RO',
            value=0,
            typeStr='UInt64',
            pollInterval=1,
            localGet=self._fifo.dropCnt))

        # Command to clear all the counters
        self.add(pyrogue.LocalCommand(
            name='ClearCnt',
            description='Clear all counters',
            function=self._fifo.clearCnt))

    def _getStreamSlave(self):
        return self._fifo

    def _getStreamMaster(self):
        return self._fifo

    def __lshift__(self,other):
        pyrogue.streamConnect(other,self)
        return other

    def __rshift__(self,other):
        pyrogue.streamConnect(self,other)
        return other
