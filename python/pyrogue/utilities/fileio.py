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
import numpy

class StreamWriter(pyrogue.DataWriter):
    """Stream Writer Wrapper"""

    def __init__(self, *, configEn=False, **kwargs):
        pyrogue.DataWriter.__init__(self, **kwargs)
        self._writer   = rogue.utilities.fileio.StreamWriter()
        self._configEn = configEn

    def _setOpen(self,dev,var,value,changed):
        if changed:
            if value == False:

                # Dump config/status to file
                if self._configEn: self.root._streamYaml()
                self._writer.close()
            else:
                self._writer.open(self.dataFile.value())

                # Dump config/status to file
                if self._configEn: self.root._streamYaml()
                self.frameCount.set(0)

    def _setBufferSize(self,dev,var,value):
        self._writer.setBufferSize(value)

    def _setMaxFileSize(self,dev,var,value):
        self._writer.setMaxSize(value)

    def _getFileSize(self,dev,var):
        return self._writer.getSize()

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

        self.add(pyrogue.LocalVariable(name='dataFile', description='Data File',
                                       mode='RW', value=''))

        self.add(pyrogue.LocalVariable(name='open', description='Data file open state',
                                  bitSize=1, bitOffset=0, mode='RW', value=False,
                                  localSet=self._setOpen))

    def _setOpen(self,value,changed):
        if changed:
            if value == False:
                dev._reader.close()
            else:
                dev._reader.open(self.dataFile.value())

    def _getStreamMaster(self):
        return self._reader


class FileHeader(object):
    def __init__(self, fdata):
        self._size    = numpy.fromfile(fdata,dtype=numpy.uint32,1)
        self._flags   = numpy.fromfile(fdata,dtype=numpy.uint16,1)
        self._error   = numpy.fromfile(fdata,dtype=numpy.uint8,1)
        self._channel = numpy.fromfile(fdata,dtype=numpy.uint8,1)

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


class FileReader(object):

    def __init__(self, filename, configChan=None):
        self._filename   = filename
        self._configChan = configChan

        # Config tracking dictionary
        self._config = {}

        # Open file and get size
        self._fdata = open(filename,'rb')
        self._fdata.seek(0,2)
        self._size = self._fdata.tell()
        self._fdata.seek(0,0)

    @property
    def next(self):
        pos = self._fdata.tell()

        while pos != self._fdata._size:

            if (self._size - pos) < 8:
                raise pyrogue.GeneralException("Header Underrun in {}".format(self._filename))

            head = FileHeader(self._fdata)
            pos = self._fdata.tell()

            if pos + (head.size-4)  > self._size:
                raise pyrogue.GeneralException("Data Underrun in {}".format(self._filename))

            data = numpy.fromfile(self._fdata,dtype=numpy.uint8,h.size-4)
            pos = self._fdata.tell()
       
            if h.channel == self._configChan:
                cfg = pyrogue.yamlToData(data.decode('utf-8'))
                self._config.update(cfg)
            else:
                return head, data

        return None, None

    def config(self):
        return self._config

