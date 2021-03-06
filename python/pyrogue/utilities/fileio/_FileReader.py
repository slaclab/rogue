#-----------------------------------------------------------------------------
# Title      : PyRogue FileIO - File Reader
#-----------------------------------------------------------------------------
# Description:
# Module for reading file data.
# This is a standalone module and can be used outside of a pyrogue installation.
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
from collections import namedtuple
import os
import struct
import numpy
import yaml
import logging

RogueHeaderSize  = 8
RogueHeaderPack  = 'IHBB'

# Default header as a named tuple
RogueHeader = namedtuple(
    'RogueHeader',
    ['size'   ,  # 4 Bytes, uint32, I
    'flags'   ,  # 2 bytes, uint16, H
    'error'   ,  # 1 bytes, uint8,  B
    'channel' ]  # 1 bytes, uint8,  B
)
""" Header data

    Attributes
    ----------
    size : int
        Size of the record

    flags : int
        Frame flags for the record

    error : int
        Error status for the record

    channel : int
        Channel id for the record

"""


class FileReaderException(Exception):
    """ File reader exception """
    pass


class FileReader(object):
    """
    A lightweight file reader for Rogue.

    Parameters
    ----------
    files : str or list
        Filename or list of filenams to read data from

    configChan : int
        Channel id of configuration/status stream in the data file. Set to None to disable processing configuration.

    log : obj
        Logging object to use. If set to None a new logger will be created with the name "pyrogue.FileReader".

    Attributes
    ----------
    currCount: int
        Number of data records processed from current file

    totCount: int
        Total number of data records processed from

    configDig: obj
        Current configuration/status dictionary
    """

    def __init__(self, files, configChan=None, log=None):
        self._configChan = configChan
        self._currFile   = None
        self._fileSize   = 0
        self._header     = None
        self._data       = None
        self._config     = {}
        self._currFName  = ""
        self._currCount  = 0
        self._totCount   = 0

        if log is None:
            self._log = logging.getLogger('pyrogue.FileReader')
        else:
            self._log = log

        if isinstance(files,list):
            self._fileList = files
        else:
            self._fileList = [files]

        # Check to make sure all the files are readable
        for fn in self._fileList:
            if not os.access(fn,os.R_OK):
                raise FileReaderException("Failed to read file {}".format(fn))

    def _nextRecord(self):
        while True:

            # Hit end of file
            if self._currFile.tell() == self._fileSize:
                return False

            # Not enough data left in the file
            if (self._fileSize - self._currFile.tell()) < RogueHeaderSize:
                self._log.warning(f'File under run reading {self._currFName}')
                return False

            self._header = RogueHeader._make(struct.Struct(RogueHeaderPack).unpack(self._currFile.read(RogueHeaderSize)))
            payload = self._header.size - 4

            # Set next frame position
            recEnd = self._currFile.tell() + payload

            # Sanity check
            if recEnd > self._fileSize:
                self._log.warning(f"File under run reading {self._currFName}")
                return False

            # Process meta data
            if self._configChan is not None and self._header.channel == self._configChan:
                self._updateConfig(yaml.load(self._currFile.read(payload).decode('utf-8')))

            # This is a data channel
            else:
                try:
                    self._data = numpy.fromfile(self._currFile, dtype=numpy.int8, count=payload)
                except Exception:
                    raise FileReaderException(f'Failed to read data from {self._currFname}')

                self._currCount += 1
                self._totCount += 1
                return True

    def records(self):
        """
        Generator which returns (header, data) tuples

        Returns
        -------
        RogueHeader, bytearray
            (header, data) tuple where header is a dictionary and data is a byte array.

        """
        self._config = {}
        self._currCount = 0
        self._totCount  = 0

        for fn in self._fileList:
            self._fileSize = os.path.getsize(fn)
            self._currFName = fn
            self._currCount = 0

            self._log.debug(f"Processing data records from {self._currFName}")
            with open(fn,'rb') as f:
                self._currFile = f

                while self._nextRecord():
                    yield (self._header, self._data)

            self._log.debug(f"Processed {self._currCount} data records from {self._currFName}")

        self._log.debug(f"Processed a total of {self._totCount} data records")

    @property
    def currCount(self):
        return self._currCount

    @property
    def totCount(self):
        return self._totCount

    @property
    def configDict(self):
        return self._config

    def configValue(self, path):
        """
        Get a configuration or status value

        Parameters
        ----------
        path : str
            Path of the config/status value to return

        Returns
        -------
        obj
            Requested configuration or status value

        """

        obj = self._config

        if '.' in path:
            lst = path.split('.')
        else:
            lst = [path]

        for a in lst:
            if a in obj:
                obj = obj[a]
            else:
                raise FileReaderException("Failed to find path {}".format(path))

        return obj

    def _updateConfig(self, new):
        # Combination of dictUpdate and keyValueUpdate from pyrogue helpers

        for k,v in new.items():
            if '.' in k:
                d = self._config
                parts = k.split('.')
                for part in parts[:-1]:
                    if part not in d:
                        d[part] = {}
                    d = d.get(part)
                d[parts[-1]] = v
            elif k in self._config:
                self._config[k].update(v)
            else:
                self._config[k] = v

    def __enter__(self):
        return self

    def __exit__(self, type, value, tb):
        pass
