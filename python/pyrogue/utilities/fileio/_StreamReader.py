#-----------------------------------------------------------------------------
# Title      : PyRogue FileIO - Stream Reader
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


class StreamReader(pyrogue.Device):
    """Stream Reader Wrapper"""

    def __init__(self, **kwargs):
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

    def _open(self):
        self._reader.open(self.DataFile.value())

    def _close(self):
        self._reader.close()

    def _isOpen(self):
        return self._reader.isOpen()

    def _getStreamMaster(self):
        return self._reader

    def __rshift__(self,other):
        pyrogue.streamConnect(self,other)
