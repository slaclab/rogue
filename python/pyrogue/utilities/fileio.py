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

class StreamWriterDevice(pyrogue.Device):
    """Stream Writer Device Wrapper"""

    def __init__(self, parent, name):

        pyrogue.Device.__init__(self, parent=parent, name=name, description='Stream Writer', 
                                size=0, memBase=None, offset=0)

        self._writer      = rogue.utilities.fileio.StreamWriter()
        self._file        = ""
        self._open        = False
        self._bufferSize  = 0
        self._maxFileSize = 0

        pyrogue.Variable(parent=self, name='dataFile', description='Data File',
                         bitSize=0, bitOffset=0, base='string', mode='RW',
                         setFunction='self._parent._file = value',
                         getFunction='value = self._parent._file')

        pyrogue.Variable(parent=self, name='open', description='Data file open state',
                         bitSize=1, bitOffset=0, base='bool', mode='RW',
                         setFunction="""\
                                     if self._parent._open != value:
                                         if value == 0:
                                             self._parent._writer.close()
                                         else:
                                             self._parent._writer.open(self._parent._file)
                                         self._parent._enable = value
                                     """,
                         getFunction='value = self._parent._open')

        pyrogue.Variable(parent=self, name='bufferSize', description='File buffering size',
                         bitSize=32, bitOffset=0, base='uint', mode='RW',
                         setFunction="""
                                     self._parent._bufferSize = value
                                     self._parent._writer.setBufferSize(value)
                                     """,
                         getFunction='value = self._parent._bufferSize')

        pyrogue.Variable(parent=self, name='maxSize', description='File maximum size',
                         bitSize=32, bitOffset=0, base='uint', mode='RW',
                         setFunction="""
                                     self._parent._maxFileSize = value
                                     self._parent._writer.setMaxSize(value)
                                     """,
                         getFunction='value = self._parent._maxFileSize')

        pyrogue.Variable(parent=self, name='fileSize', description='File size in bytes',
                         bitSize=32, bitOffset=0, base='uint', mode='RO',
                         setFunction=None, getFunction='value = self._parent._writer.getSize()')

        pyrogue.Variable(parent=self, name='bankCount', description='Total banks in file',
                         bitSize=32, bitOffset=0, base='uint', mode='RO',
                         setFunction=None, getFunction='value = self._parent._writer.getBankCount()')

    def readAll(self):
        self.readPoll()

    def readPoll(self):
        self.fileSize.readAndGet()
        self.bankCount.readAndGet()

    def getWriter(self):
        return self._writer


class StreamReaderDevice(pyrogue.Device):
    """Stream Reader Device Wrapper"""

    def __init__(self, parent, name):

        pyrogue.Device.__init__(self, parent=parent, name=name, description='Stream Writer', 
                                size=0, memBase=None, offset=0)

        self._reader      = rogue.utilities.fileio.StreamReader()
        self._file        = ""
        self._open        = False
        self._bufferSize  = 0
        self._maxFileSize = 0

        pyrogue.Variable(parent=self, name='dataFile', description='Data File',
                         bitSize=0, bitOffset=0, base='string', mode='RW',
                         setFunction='self._parent._file = value',
                         getFunction='value = self._parent._file')

        pyrogue.Variable(parent=self, name='open', description='Data file open state',
                         bitSize=1, bitOffset=0, base='bool', mode='RW',
                         setFunction="""\
                                     if self._parent._open != int(value):
                                         if int(value) == 0:
                                             self._parent._writer.close()
                                         else:
                                             self._parent._writer.open(self._parent._file)
                                         self._parent._enable = int(value)
                                     """,
                         getFunction='value = self._parent._open')

    def getReader(self):
        return self._writer

