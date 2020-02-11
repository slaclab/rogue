#-----------------------------------------------------------------------------
# Title      : PyRogue FileIO - File Reader
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
import pyrogue
import rogue

import os
import struct
import numpy
from collections import namedtuple

RogueHeaderSize  = 8
RogueHeaderPack  = 'IHBB'

# Default header as a named tuple
RogueHeader = namedtuple( 'RogueHeader',
                         [ 'size'                ,  # 4 Bytes, uint32, I
                           'flags'               ,  # 2 bytes, uint16, H
                           'error'               ,  # 1 bytes, uint8,  B
                           'channel'                # 1 bytes, uint8,  B
                         ] )


class FileReader(object):

    def __init__(self, files, configChan=None):
        self._configChan = configChan
        self._currFile   = None
        self._fileSize   = 0
        self._header     = None
        self._data       = None
        self._config     = {}
        self._currFName  = ""
        self._currCount  = 0
        self._totCount   = 0

        self._log = pyrogue.logInit(self)

        if isinstance(files,list):
            self._fileList = files
        else:
            self._fileList = [files]

        # Check to make sure all the files are readable
        for fn in self._fileList:
            if not os.access(fn,os.R_OK):
                raise rogue.GeneralError("filio.FileReader","Failed to read file {}".format(fn))

    def _nextRecord(self):
        while True:

            # Hit end of file
            if self._currFile.tell() == self._fileSize:
                return False

            # Not enough data left in the file
            if (self._fileSize - self._currFile.tell()) < RogueHeaderSize:
                self._log.warning(f"File under run reading {self._currFName}")
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
                try:
                    pyrogue.yamlUpdate(self._config, self._currFile.read(payload).decode('utf-8'))
                except:
                    self._log.warning(f"Error processing meta data in {self._currFName}")

            # This is a data channel
            else: 
                try:
                    self._data = numpy.fromfile(self._currFile, dtype=numpy.int8, count=payload)
                except:
                    raise rogue.GeneralError(f"fileio.FileReader","Failed to read data from {self._currFname}")

                self._currCount += 1
                self._totCount += 1
                return True

    def records(self):
        """
        Generator which returns (header, data) tuples
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
    def configDict(self):
        return self._config

    def configValue(self, path):
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

    def __enter__(self):
        return self

    def __exit__(self, type, value, tb):
        pass
