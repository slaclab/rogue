#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Title      : PyRogue FileIO - File Reader
#-----------------------------------------------------------------------------
# File       : pyrogue/utilities/fileio/_FileReader.py
# Created    : 2016-09-29
#-----------------------------------------------------------------------------
# Description:
# Module for reading file data.
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

        # Init records
        self._size    = 0
        self._flags   = 0
        self._error   = 0
        self._channel = 0
        self._data    = numpy.empty(0,dtype=numpy.int8)


    @property
    def next(self):
        while True:

            # Check record size
            if (self._fdata.tell() == self._size) or ((self._size - self._fdata.tell()) < 4):
                return False

            self._size    = int.from_bytes(self._fdata.read(4),'little',signed=False)
            self._flags   = int.from_bytes(self._fdata.read(2),'little',signed=False)
            self._error   = int.from_bytes(self._fdata.read(1),'little',signed=False)
            self._channel = int.from_bytes(self._fdata.read(1),'little',signed=False)

            if (self._configChan is not None) and (self._configChan == self._channel):
                self._processConfig()
            else:
                return self._processData()


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

    def configDict(self):
        return self._config

    def configPath(self, path):
        obj = self._config

        if '.' in path:
            lst = path.split('.')
        else:
            lst = [path]

        for a in lst:
            if a in obj:
                obj = obj[a]
            else:
                raise rogue.GeneralError("filio.FileReader","Failed to find path {}".format(path))

        return obj


    def _processConfig(self):
        try:
            d = self._fdata.read(sef._size).decode('utf-8')
            pyrogue.dictUpdate(self._config,pyrogue.yamlToData(d))
        except:
            raise rogue.GeneralError("filio.FileReader","Failed to read config from {}".format(self._filename))


    def _processData(self, d):
        try:
            self._data = numpy.fromfile(self._fdata,dtype=numpy.int8,count=self._size)
        except:
            raise rogue.GeneralError("filio.FileReader","Failed to read data from {}".format(self._filename))


