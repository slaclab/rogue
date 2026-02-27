#-----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
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
from typing import Any


class StreamWriter(pyrogue.DataWriter):
    """Wrapper ``pyrogue.DataWriter`` around ``rogue.utilities.fileio.StreamWriter``.

    See Also
    --------
    :ref:`utilities_fileio_format`
        Canonical Rogue file record format written by StreamWriter.
    :ref:`utilities_fileio_reading`
        Notes on how files are decoded back into stream frames.

    Parameters
    ----------
    configStream : dict[int, rogue.interfaces.stream.Master], optional
        Mapping of stream channel index to configuration/status source object.
    writer : rogue.utilities.fileio.StreamWriter, optional
        Existing Rogue stream writer instance. When ``None``, a new one is created.
    rawMode : bool, optional (default = False)
        If ``False`` (default), each frame is written in Rogue file format with
        per-frame metadata headers (payload length, channel, error, and flags)
        followed by payload bytes. If ``True``, only raw frame payload bytes are
        written, with no per-frame Rogue headers.
    **kwargs : Any
        Additional keyword arguments forwarded to ``pyrogue.DataWriter``.
    """

    def __init__(
        self,
        *,
        configStream: dict[int, rogue.interfaces.stream.Master] | None = None,
        writer: rogue.utilities.fileio.StreamWriter | None = None,
        rawMode: bool = False,
        **kwargs: Any,
    ) -> None:
        pyrogue.DataWriter.__init__(self, **kwargs)
        self._configStream = {} if configStream is None else configStream

        if writer is None:
            self._writer = rogue.utilities.fileio.StreamWriter()
        else:
            self._writer = writer

        if rawMode:
            self._writer.setRaw(True)

        # Connect configuration stream
        for k,v in self._configStream.items():
            pyrogue.streamConnect(v, self._writer.getChannel(k))

    def _open(self) -> None:
        """Open output file and emit initial configuration records."""
        self._writer.open(self.DataFile.value())

        # Dump config/status to file
        for k,v in self._configStream.items():
            v.streamYaml()

        self.FrameCount.set(0)
        self.IsOpen.get()

    def _close(self) -> None:
        """Emit final configuration records and close output file."""

        # Dump config/status to file
        for k,v in self._configStream.items():
            v.streamYaml()

        self._writer.close()
        self.IsOpen.get()

    def _isOpen(self) -> bool:
        """Return whether the writer currently has an open file."""
        return self._writer.isOpen()

    def _setBufferSize(self, value: int) -> None:
        """Update writer file buffer size."""
        self._writer.setBufferSize(value)

    def _setMaxFileSize(self, value: int) -> None:
        """Update writer maximum file size."""
        self._writer.setMaxSize(value)

    def _getCurrentSize(self) -> int:
        """Return current output file size in bytes."""
        return self._writer.getCurrentSize()

    def _getTotalSize(self) -> int:
        """Return total bytes written across files."""
        return self._writer.getTotalSize()

    def _getBandwidth(self) -> float:
        """Return file-write bandwidth in bytes/second over the recent ~1 second window."""
        return self._writer.getBandwidth()

    def _getFrameCount(self) -> int:
        """Return total written frame count."""
        return self._writer.getFrameCount()

    def _waitFrameCount(self, count: int, timeout: float = 0) -> bool:
        """Wait for total frame count to reach ``count`` within timeout seconds."""
        return self._writer.waitFrameCount(count, timeout * 1000000)

    def _waitFrameChannelCount(self, chan: int, count: int, timeout: float = 0) -> bool:
        """Wait for channel frame count to reach ``count`` within timeout seconds."""
        return self._writer.getChannel(chan).waitFrameCount(count, timeout * 1000000)

    def getChannel(self, chan: int) -> rogue.interfaces.stream.Slave:
        """Return writer channel object by index."""
        return self._writer.getChannel(chan)

    def setDropErrors(self, drop: bool) -> None:
        """Enable or disable dropping errored frames."""
        self._writer.setDropErrors(drop)
