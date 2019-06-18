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

    def __init__(self, filename, configChan=None, dtype={}):
        self._filename   = filename

        # Dtype is a dictionary
        self._dtype = dtype

        # ConfigChan can be a single channel or list
        if isinstance(configChan,list):
            self._configChan = configChane
        elif configChan is not None:
            self._configChane = [configChan]
        else:
            self._configChane = []

        # Update data types for config
        for chan in configChan:
            dtype[chan] = str

        # Config tracking dictionary
        self._config = {}

    def _checkConfig(self):

        fh = FileHeader


    def config(self):
        return self._config

    @property
    def next(self):

        




