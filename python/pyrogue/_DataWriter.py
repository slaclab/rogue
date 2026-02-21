#-----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
#-----------------------------------------------------------------------------
#  Description:
#       PyRogue base module - Data Writer Class
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
from __future__ import annotations

import datetime
from typing import Any

import pyrogue as pr


class DataWriter(pr.Device):
    """Base class for constructing data writer devices.

    Parameters
    ----------
    hidden : bool, optional (default = True)
        If True, add the device to the ``Hidden`` group.
    bufferSize : int, optional (default = 0)
        File buffer size in bytes.
    maxFileSize : int, optional (default = 0)
        Maximum file size in bytes before rolling.
    **kwargs : Any
        Additional arguments forwarded to ``Device``.
    """

    def __init__(
        self,
        *,
        hidden: bool = True,
        bufferSize: int = 0,
        maxFileSize: int = 0,
        **kwargs: Any,
    ) -> None:
        """Initialize the data writer device.

        Parameters
        ----------
        hidden : bool, optional
            If ``True``, add the device to the ``Hidden`` group.
        bufferSize : int, optional
            File buffer size in bytes.
        maxFileSize : int, optional
            Maximum file size in bytes before rolling.
        **kwargs : Any
            Additional keyword arguments forwarded to :class:`pyrogue.Device`.
        """

        pr.Device.__init__(self,
                           hidden=hidden,
                           description = 'Class which stores received data to a file.',
                           **kwargs)

        self.add(pr.LocalVariable(
            name='DataFile',
            mode='RW',
            value='',
            description='Data file for storing frames for connected streams.'
                        'This is the file opened when the Open command is executed.'))

        self.add(pr.LocalCommand(
            name='Open',
            function=self._open,
            description='Open data file. The new file name will be the contents of the DataFile variable.'))

        self.add(pr.LocalCommand(
            name='Close',
            function=self._close,
            description='Close data file.'))

        self.add(pr.LocalVariable(
            name='IsOpen',
            mode='RO',
            value=False,
            localGet=self._isOpen,
            description='Status field which is True when the Data file is open.'))

        self.add(pr.LocalVariable(
            name='BufferSize',
            mode='RW',
            value=bufferSize,
            typeStr='UInt32',
            localSet=self._setBufferSize,
            description='File buffering size. Enables caching of data before call to file system.'))

        self.add(pr.LocalVariable(
            name='MaxFileSize',
            mode='RW',
            value=maxFileSize,
            typeStr='UInt64',
            localSet=self._setMaxFileSize,
            description='Maximum size for an individual file. Setting to a non zero splits the run data into multiple files.'))

        self.add(pr.LocalVariable(
            name='CurrentSize',
            mode='RO',
            value=0,
            typeStr='UInt64',
            pollInterval=1,
            localGet=self._getCurrentSize,
            description='Size of current data files in bytes.'))

        self.add(pr.LocalVariable(
            name='TotalSize',
            mode='RO',
            value=0,
            typeStr='UInt64',
            pollInterval=1,
            localGet=self._getTotalSize,
            description='Total bytes written.'))

        self.add(pr.LocalVariable(
            name='Bandwidth',
            mode='RO',
            value=0.0,
            typeStr='Float64',
            pollInterval=1,
            localGet=self._getBandwidth,
            units='Bytes/sec',
            disp='{:,.3f}',
            description='Instantaneous write bandwidth in bytes per second.'))

        self.add(pr.LocalVariable(
            name='FrameCount',
            mode='RO',
            value=0,
            typeStr='UInt32',
            pollInterval=1,
            localGet=self._getFrameCount,
            description='Total frames received and written.'))

        self.add(pr.LocalCommand(
            name='AutoName',
            function=self._genFileName,
            description='Auto create data file name using data and time.'))

    def _open(self) -> None:
        """Open the currently selected output file.

        Notes
        -----
        Override in subclasses.
        """
        pass

    def _close(self) -> None:
        """Close the current output file.

        Notes
        -----
        Override in subclasses.
        """
        pass

    def _isOpen(self) -> bool:
        """Return file-open status.

        Returns
        -------
        bool
            ``True`` if a file is currently open, else ``False``.

        Notes
        -----
        Override in subclasses.
        """
        return False

    def _setBufferSize(self, value: int) -> None:
        """Set file buffer size.

        Parameters
        ----------
        value : int
            Buffer size in bytes.

        Notes
        -----
        Override in subclasses.
        """
        pass

    def _setMaxFileSize(self, value: int) -> None:
        """Set maximum file size before rolling.

        Parameters
        ----------
        value : int
            Maximum file size in bytes. Non-zero enables file splitting.

        Notes
        -----
        Override in subclasses.
        """
        pass

    def _getCurrentSize(self) -> int:
        """Return current output file size.

        Returns
        -------
        int
            Current file size in bytes.

        Notes
        -----
        Override in subclasses.
        """
        return 0

    def _getTotalSize(self) -> int:
        """Return total bytes written.

        Returns
        -------
        int
            Total number of bytes written across files.

        Notes
        -----
        Override in subclasses.
        """
        return 0

    def _getBandwidth(self, dev: pr.Device | None = None, var: pr.Variable | None = None) -> float:
        """Return instantaneous write bandwidth.

        Parameters
        ----------
        dev : pyrogue.Device or None, optional
            Optional callback context passed by LocalVariable polling.
        var : pyrogue.Variable or None, optional
            Optional callback context passed by LocalVariable polling.

        Returns
        -------
        float
            Instantaneous bandwidth in bytes/second.

        Notes
        -----
        Override in subclasses.
        """
        return 0.0

    def _getFrameCount(self) -> int:
        """Return total frame count.

        Returns
        -------
        int
            Total number of frames written.

        Notes
        -----
        Override in subclasses.
        """
        return 0

    def _genFileName(self) -> None:
        """Generate a timestamped output filename.

        Generates ``data_%Y%m%d_%H%M%S.dat`` and preserves the directory part
        of the current ``DataFile`` value, if present.
        """
        idx = self.DataFile.value().rfind('/')

        if idx < 0:
            base = ''
        else:
            base = self.DataFile.value()[:idx+1]

        self.DataFile.set(base + datetime.datetime.now().strftime("data_%Y%m%d_%H%M%S.dat"))
