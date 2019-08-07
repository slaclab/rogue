#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Title      : PyRogue FileIO Utilities base module
#-----------------------------------------------------------------------------
# File       : pyrogue/utilities/filio.py
# Author     : Ryan Herbst, rherbst@slac.stanford.edu
# Created    : 2016-09-29
# Last update: 2016-09-29
#-----------------------------------------------------------------------------
# Description:
# Module containing the filio utilities module class and methods
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

    def __init__(self, *, configEn=False, **kwargs):
        pyrogue.DataWriter.__init__(self, **kwargs)
        self._writer   = rogue.utilities.fileio.StreamWriter()
        self._configEn = configEn

    def _open(self):
        try:
            self._writer.open(self.dataFile.value())
        except Exception as e:
            self._log.exception(e)

        # Dump config/status to file
        if self._configEn: self.root._streamYaml()
        self.frameCount.set(0)
        self.isOpen.get()

    def _close(self):

        # Dump config/status to file
        if self._configEn: self.root._streamYaml()
        self._writer.close()
        self.isOpen.get()

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
    def __init__(self, *, configEn=False, **kwargs):
        pyrogue.DataWriter.__init__(self, **kwargs)
        self._writer   = rogue.utilities.fileio.LegacyStreamWriter()
        self._configEn = configEn

    def getDataChannel(self):
        return self._writer.getDataChannel()

    def getYamlChannel(self):
        return self._writer.getYamlChannel()

class StreamReader(pyrogue.Device):
    """Stream Reader Wrapper"""

    def __init__(self, **kwargs):
        pyrogue.Device.__init__(self, **kwargs)
        self._reader = rogue.utilities.fileio.StreamReader()

        self.add(pyrogue.LocalVariable(
            name='dataFile', 
            description='Data File',
            mode='RW', 
            value=''))

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
            function=self._isOpen,
            description='Data file is open.'))

    def _open(self):
        dev._reader.open(self.dataFile.value())

    def _close(self):
        dev._reader.close()

    def _isOpen(self):
        return self._reader.isOpen()

    def _getStreamMaster(self):
        return self._reader


class FileData(object):
    def __init__(self, rdata):
        self._size    = int.from_bytes(rdata.read(4),'little',signed=False)
        self._flags   = int.from_bytes(rdata.read(2),'little',signed=False)
        self._error   = int.from_bytes(rdata.read(1),'little',signed=False)
        self._channel = int.from_bytes(rdata.read(1),'little',signed=False)
        self._data    = rdata.read(self._size-4)

    @property
    def size(self):
        return self._size

    @property
    def flags(self):
        return self._flags

    @property
    def error(self):
        return self._error

    @property
    def channel(self):
        return self._channel

    @property
    def data(self):
        return self._data

class FileReader(object):

    def __init__(self, filename, configChan=None):
        self._filename   = filename
        self._configChan = configChan

        # Config tracking dictionary
        self._config = {}

        # Open file and get size
        self._fdata = open(self._filename,'rb')
        self._fdata.seek(0,2)
        self._size = self._fdata.tell()
        self._fdata.seek(0,0)

    @property
    def next(self):
        while self._fdata.tell() != self._size:
            try:
                fd = FileData(self._fdata)
            except:
                raise rogue.GeneralError("filio.FileReader","Underrun while reading from {}".format(self._filename))

            if fd.channel == self._configChan:
                try:
                    pyrogue.dictUpdate(self._config,pyrogue.yamlToData(fd.data.decode('utf-8')))
                except:
                    raise rogue.GeneralError("filio.FileReader","Failed to read config from {}".format(self._filename))
            else:
                return fd

        return None

    def config(self):
        return self._config

