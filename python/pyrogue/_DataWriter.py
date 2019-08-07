#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Title      : PyRogue base module - Data Writer Class
#-----------------------------------------------------------------------------
# File       : pyrogue/_DataWriter.py
# Created    : 2017-05-16
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to 
# the license terms in the LICENSE.txt file found in the top-level directory 
# of this distribution and at: 
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html. 
# No part of the rogue software platform, including this file, may be 
# copied, modified, propagated, or distributed except according to the terms 
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
import rogue.interfaces.memory as rim
import collections
import datetime
import functools as ft
import pyrogue as pr
import inspect
import threading
import math
import time


class DataWriter(pr.Device):
    """Special base class to control data files. TODO: Update comments"""

    def __init__(self, *, hidden=True, **kwargs):
        """Initialize device class"""

        pr.Device.__init__(self, hidden=hidden, **kwargs)

        self.add(pr.LocalVariable(
            name='dataFile',
            mode='RW',
            value='',
            description='Data file for storing frames for connected streams.'))

        self.add(pr.LocalCommand(
            name='open',
            function=self._open,
            description='Open data file.'))

        self.add(pr.LocalCommand(
            name='close',
            function=self._close,
            description='Close data file.'))

        self.add(pr.LocalVariable(
            name='isOpen',
            value=False,
            localGet=self._isOpen,
            description='Data file is open.'))

        self.add(pr.LocalVariable(
            name='bufferSize',
            mode='RW',
            value=0,
            typeStr='UInt32',
            localSet=self._setBufferSize,
            description='File buffering size. Enables caching of data before call to file system.'))

        self.add(pr.LocalVariable(
            name='maxFileSize',
            mode='RW',
            value=0,
            typeStr='UInt64',
            localSet=self._setMaxFileSize,
            description='Maximum size for an individual file. Setting to a non zero splits the run data into multiple files.'))

        self.add(pr.LocalVariable(
            name='currentSize',
            mode='RO',
            value=0,
            typeStr='UInt64',
            pollInterval=1,
            localGet=self._getCurrentSize,
            description='Size of current data files(s) for current open session in bytes.'))

        self.add(pr.LocalVariable(
            name='totalSize',
            mode='RO',
            value=0,
            typeStr='UInt64',
            pollInterval=1,
            localGet=self._getTotalSize,
            description='Size of all data sub-files(s) for current open session in bytes.'))

        self.add(pr.LocalVariable(
            name='frameCount',
            mode='RO',
            value=0,
            typeStr='UInt32',
            pollInterval=1,
            localGet=self._getFrameCount,
            description='Frame in data file(s) for current open session in bytes.'))

        self.add(pr.LocalCommand(
            name='autoName',
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
        """Set buffer size. Override in sub-class"""
        pass

    def _setMaxFileSize(self,value):
        """Set max file size. Override in sub-class"""
        pass

    def _getCurrentSize(self):
        """get current file size. Override in sub-class"""
        return(0)

    def _getTotalSize(self):
        """get total file size. Override in sub-class"""
        return(0)

    def _getFrameCount(self):
        """get current file frame count. Override in sub-class"""
        return(0)

    def _genFileName(self):
        """
        Auto create data file name based upon date and time.
        Preserve file's location in path.
        """
        idx = self.dataFile.value().rfind('/')

        if idx < 0:
            base = ''
        else:
            base = self.dataFile.value()[:idx+1]

        self.dataFile.set(base + datetime.datetime.now().strftime("data_%Y%m%d_%H%M%S.dat")) 

