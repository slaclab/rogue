#-----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
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
from dataclasses import dataclass
import os
import struct
from typing import Any, Iterator

import numpy
import numpy.typing as npt
import logging

import pyrogue as pr

RogueHeaderSize  = 8
RogueHeaderPack  = 'IHBB'

# Default header as a named tuple
@dataclass
class RogueHeader:
    """Rogue frame header.

    Attributes
    ----------
    size : int
        Payload size of the record in bytes (header-adjusted by this reader).
    flags : int
        Frame flags for the record.
    error : int
        Error status for the record.
    channel : int
        Channel id for the record.
    """

    size : int     # 4 Bytes, uint32, I
    flags: int     # 2 bytes, uint16, H
    error: int     # 1 bytes, uint8,  B
    channel: int   # 1 bytes, uint8,  B

BatchHeaderSize  = 8
BatchHeaderPack  = 'IBBBB'

# Batcher Header
@dataclass
class BatchHeader:
    """Batch sub-frame header.

    Attributes
    ----------
    size : int
        Sub-frame payload size in bytes.
    tdest : int
        TDEST value from AXI Stream frame metadata.
    fUser : int
        First USER value from AXI Stream frame metadata.
    lUser : int
        Last USER value from AXI Stream frame metadata.
    width : int
        Width of the batched data in bytes.
    """

    size: int   # 4 Bytes, uint32, I
    tdest: int  # 1 Byte, uint8, B
    fUser: int  # 1 Byte, uint8, B
    lUser: int  # 1 Byte, uint8, B
    width: int  # 1 Byte, uint8, B

DataArray = npt.NDArray[numpy.int8]
Record = tuple[RogueHeader, DataArray]
BatchRecord = tuple[RogueHeader, BatchHeader, DataArray]

class FileReaderException(Exception):
    """File reader exception."""


class FileReader(object):
    """
    A lightweight file reader for Rogue.

    Parameters
    ----------
    files : str or list[str]
        Filename or list of filenames to read data from.
    configChan : int | None
        Channel id of configuration/status stream in the data file. Set to
        ``None`` to disable configuration processing.
    log : logging.Logger | None
        Logger to use. If ``None``, a new logger with name
        ``"pyrogue.FileReader"`` is created.
    batched : bool
        Flag indicating if the data file contains batched data.

    Attributes
    ----------
    currCount: int
        Number of data records processed from current file

    totCount: int
        Total number of data records processed from

    configDict : dict[str, Any]
        Current configuration/status dictionary.
    """

    def __init__(
        self,
        files: str | list[str],
        configChan: int | None = None,
        log: logging.Logger | None = None,
        batched: bool = False,
    ) -> None:
        self._configChan = configChan
        self._currFile   = None
        self._fileSize   = 0
        self._header     = None
        self._config     = {}
        self._currFName  = ""
        self._currCount  = 0
        self._totCount   = 0
        self._batched    = batched

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

    def _nextRecord(self) -> bool:
        while True:

            # Hit end of file
            if self._currFile.tell() == self._fileSize:
                return False

            # Not enough data left in the file
            if (self._fileSize - self._currFile.tell()) < RogueHeaderSize:
                self._log.warning("File underrun reading %s", self._currFName)
                return False

            self._header = RogueHeader(*struct.unpack(RogueHeaderPack, self._currFile.read(RogueHeaderSize)))
            self._header.size -= 4

            # Set next frame position
            recEnd = self._currFile.tell() + self._header.size

            # Sanity check
            if recEnd > self._fileSize:
                self._log.warning("File underrun reading %s", self._currFName)
                return False

            # Process meta data
            if self._configChan is not None and self._header.channel == self._configChan:
                self._updateConfig(pr.yamlToData(stream=self._currFile.read(self._header.size).decode('utf-8')))

            # This is a data channel
            else:

                self._currCount += 1
                self._totCount += 1
                return True

    def records(self) -> Iterator[Record | BatchRecord]:
        """
        Yield data records from all configured files.

        Returns
        -------
        Iterator[Record | BatchRecord]
            For ``batched=False``, yields ``(RogueHeader, numpy.ndarray[int8])``.
            For ``batched=True``, yields ``(RogueHeader, BatchHeader, numpy.ndarray[int8])``.
        """
        self._config = {}
        self._currCount = 0
        self._totCount  = 0

        for fn in self._fileList:
            self._fileSize = os.path.getsize(fn)
            self._currFName = fn
            self._currCount = 0

            self._log.debug("Processing data records from %s", self._currFName)
            with open(fn,'rb') as f:
                self._currFile = f

                while self._nextRecord():

                    # Batch Mode
                    if self._batched:

                        curIdx = 0

                        while True:

                            # Check header size
                            if curIdx + 8 > self._header.size:
                                raise FileReaderException(f'Batch frame header underrun in {self._currFName}')

                            # Read in header data
                            bHead = BatchHeader(*struct.unpack(BatchHeaderPack, self._currFile.read(BatchHeaderSize)))
                            curIdx += 8

                            # Fix header width
                            bHead.width = [2, 4, 8, 16][bHead.width]

                            # Skip rest of header if more than 64-bits
                            if bHead.width > 8:

                                if curIdx + (bHead.width-8) > self._header.size:
                                    raise FileReaderException(f'Batch frame header underrun in {self._currFName}')

                                self._currFile.seek(bHead.width-8)

                            # Check payload size
                            if curIdx + bHead.size > self._header.size:
                                raise FileReaderException(f'Batch frame data underrun in {self._currFName}')

                            # Get data
                            data = numpy.fromfile(self._currFile, dtype=numpy.int8, count=bHead.size)
                            curIdx += bHead.size

                            yield (self._header, bHead, data)

                            if self._header.size == curIdx:
                                break

                    else:
                        try:
                            data = numpy.fromfile(self._currFile, dtype=numpy.int8, count=self._header.size)
                        except Exception:
                            raise FileReaderException(f'Failed to read data from {self._currFName}')

                        yield (self._header, data)

            self._log.debug("Processed %s data records from %s", self._currCount, self._currFName)

        self._log.debug("Processed a total of %s data records", self._totCount)

    @property
    def currCount(self) -> int:
        """Return number of records read from the current file."""
        return self._currCount

    @property
    def totCount(self) -> int:
        """Return total number of records read across all files."""
        return self._totCount

    @property
    def configDict(self) -> dict[str, Any]:
        """Return merged configuration/status dictionary."""
        return self._config

    def configValue(self, path: str) -> Any:
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

    def _updateConfig(self, new: dict[str, Any]) -> None:
        """Merge a status/config update dictionary into ``self._config``."""
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

    def __enter__(self) -> "FileReader":
        """Return self for context-manager use."""
        return self

    def __exit__(self, exc_type: Any, value: Any, tb: Any) -> None:
        """No-op context-manager exit hook."""
        pass
