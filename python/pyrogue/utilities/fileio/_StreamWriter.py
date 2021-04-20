#-----------------------------------------------------------------------------
# Title      : PyRogue FileIO - Stream Writer
#-----------------------------------------------------------------------------
# Description:
# Module for writing stream data.
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


class StreamWriter(pyrogue.DataWriter):
    """Stream Writer Wrapper"""

    def __init__(self, *, configEn=False, writer=None, **kwargs):
        pyrogue.DataWriter.__init__(self, **kwargs)
        self._configEn = configEn

        if writer is None:
            self._writer = rogue.utilities.fileio.StreamWriter()
        else:
            self._writer = writer

    def _open(self):
        self._writer.open(self.DataFile.value())

        # Dump config/status to file
        if self._configEn:
            self.root.streamYaml()
        self.FrameCount.set(0)
        self.IsOpen.get()

    def _close(self):
        # Dump config/status to file
        if self._configEn:
            self.root.streamYaml()
        self._writer.close()
        self.IsOpen.get()

    def _isOpen(self):
        return self._writer.isOpen()

    def _setBufferSize(self,dev,var,value):
        self._writer.setBufferSize(value)

    def _setMaxFileSize(self,dev,var,value):
        self._writer.setMaxSize(value)

    def _getCurrentSize(self,dev,var):
        return self._writer.getCurrentSize()

    def _getTotalSize(self,dev,var):
        return self._writer.getTotalSize()

    def _getFrameCount(self,dev,var):
        return self._writer.getFrameCount()

    def _waitFrameCount(self, count, timeout=0):
        return self._writer.waitFrameCount(count,timeout*1000000)

    def _waitFrameChannelCount(self, chan, count, timeout=0):
        return self._writer.getChannel(chan).waitFrameCount(count,timeout*1000000)

    def getChannel(self,chan):
        return self._writer.getChannel(chan)

    def setDropErrors(self,drop):
        self._writer.setDropErrors(drop)


class LegacyStreamWriter(StreamWriter):
    def __init__(self, **kwargs):
        super().__init__(writer=rogue.utilities.fileio.LegacyStreamWriter(), **kwargs)

    def getDataChannel(self):
        return self._writer.getDataChannel()

    def getYamlChannel(self):
        return self._writer.getYamlChannel()
