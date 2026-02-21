#-----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
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
from typing import Any


class Fifo(pyrogue.Device):
    """Pyrogue Device wrapper for the rogue.interfaces.stream.Fifo class.

    Parameters
    ----------
    name : str
        Device name.
    description : str, optional
        Human-readable description.
    maxDepth : int, optional
        Maximum FIFO depth.
    trimSize : int, optional
        Trim size for frames.
    noCopy : bool, optional
        If ``True``, avoid copying frame data.
    **kwargs : Any
        Additional arguments passed to :class:`pyrogue.Device`.
    """

    def __init__(
        self,
        *,
        name: str,
        description: str = '',
        maxDepth: int = 0,
        trimSize: int = 0,
        noCopy: bool = False,
        **kwargs: Any,
    ) -> None:
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

    def _getStreamSlave(self) -> rogue.interfaces.stream.Slave:
        """Return the underlying FIFO as a stream slave interface."""
        return self._fifo

    def _getStreamMaster(self) -> rogue.interfaces.stream.Master:
        """Return the underlying FIFO as a stream master interface."""
        return self._fifo

    def __lshift__(self, other: rogue.interfaces.stream.Master) -> rogue.interfaces.stream.Master:
        """Connect other -> self. Returns other."""
        pyrogue.streamConnect(other, self)
        return other

    def __rshift__(self, other: rogue.interfaces.stream.Slave) -> rogue.interfaces.stream.Slave:
        """Connect self -> other. Returns other."""
        pyrogue.streamConnect(self, other)
        return other

    def countReset(self) -> None:
        """Clear all FIFO counters."""
        self._fifo.clearCnt()
