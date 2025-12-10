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
import datetime
import pyrogue as pr


class DataWriter(pr.Device):
    """Special base class to control data files. TODO: Update comments"""

    def __init__(self, *, hidden=True, bufferSize=0, maxFileSize=0, **kwargs):
        """
        Initialize device class
        Parameters
        ----------
        * :

        hidden=True :

        **kwargs :

        Returns
        -------

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
            disp='{:0.3f}',
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

    def _open(self):
        """Open file. Override in sub-class"""
        pass

    def _close(self):
        """Close file. Override in sub-class"""
        pass

    def _isOpen(self):
        """File open status. Override in sub-class"""
        pass

    def _setBufferSize(self,value):
        """
        Set buffer size. Override in sub-class

        Parameters
        ----------
        value :


        Returns
        -------

        """
        pass

    def _setMaxFileSize(self,value):
        """
        Set max file size. Override in sub-class

        Parameters
        ----------
        value :


        Returns
        -------

        """
        pass

    def _getCurrentSize(self):
        """get current file size. Override in sub-class"""
        return 0

    def _getTotalSize(self):
        """get total file size. Override in sub-class"""
        return 0

    def _getBandwidth(self, dev=None, var=None):
        """get instantaneous bandwidth. Override in sub-class"""
        return 0.0

    def _getFrameCount(self):
        """get current file frame count. Override in sub-class"""
        return 0

    def _genFileName(self):
        """
        Auto create data file name based upon date and time.
        Preserve file's location in path.

        Parameters
        ----------

        Returns
        -------

        """
        idx = self.DataFile.value().rfind('/')

        if idx < 0:
            base = ''
        else:
            base = self.DataFile.value()[:idx+1]

        self.DataFile.set(base + datetime.datetime.now().strftime("data_%Y%m%d_%H%M%S.dat"))
