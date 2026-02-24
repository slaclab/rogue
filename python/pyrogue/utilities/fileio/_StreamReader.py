#-----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
#-----------------------------------------------------------------------------
# Description:
# Module for reading stream data.
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
import rogue.utilities
import rogue.utilities.fileio
import pyrogue
import rogue
from typing import Any


class StreamReader(pyrogue.Device):
    """Wrapper ``pyrogue.Device`` around ``rogue.utilities.fileio.StreamReader``.

    See Also
    --------
    :ref:`utilities_fileio_reader`
        StreamReader utility documentation.
    :ref:`utilities_fileio_format`
        Canonical Rogue file record format consumed by StreamReader.

    Parameters
    ----------
    **kwargs : Any
        Additional keyword arguments forwarded to ``pyrogue.Device``.
    """

    def __init__(self, **kwargs: Any) -> None:
        pyrogue.Device.__init__(self, **kwargs)
        self._reader = rogue.utilities.fileio.StreamReader()

        self.add(pyrogue.LocalVariable(
            name='DataFile',
            description='Data File',
            mode='RW',
            value=''))

        self.add(pyrogue.LocalCommand(
            name='Open',
            function=self._open,
            description='Open data file.'))

        self.add(pyrogue.LocalCommand(
            name='Close',
            function=self._close,
            description='Close data file.'))

        self.add(pyrogue.LocalVariable(
            name='isOpen',
            function=self._isOpen,
            description='Data file is open.'))

    def _open(self) -> None:
        """Open the configured input file."""
        self._reader.open(self.DataFile.value())

    def _close(self) -> None:
        """Close the current input file."""
        self._reader.close()

    def _isOpen(self) -> bool:
        """Return whether the reader has an open file."""
        return self._reader.isOpen()

    def _getStreamMaster(self) -> rogue.utilities.fileio.StreamReader:
        """Return wrapped stream reader endpoint."""
        return self._reader

    def __rshift__(self, other: Any) -> Any:
        """Connect this reader to ``other`` via stream API."""
        pyrogue.streamConnect(self, other)
        return other
