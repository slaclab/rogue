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

class StreamWriter(pyrogue.DataWriter):
    """Stream Writer Wrapper"""

    def __init__(self, parent, name):
        pyrogue.DataWriter.__init__(self,parent=parent, name=name)
        self._writer = rogue.utilities.fileio.StreamWriter()

    def _setOpen(self,cmd,arg):
        if self._open != value:
            if arg == False:
                self._writer.close()
            else:
                self._writer.open(self._dataFile)
            self._open = value

    def _setBufferSize(self,cmd,arg):
        self._bufferSize = value
        self._writer.setBufferSize(value)

    def _setMaxSize(self,cmd,arg):
        self._maxFileSize = value
        self._writer.setMaxSize(value)

    def _getFileSize(self,cmd):
        return self._writer.getSize()

    def _getFrameCount(self,cmd):
        return self._writer.getFrameCount()

    def getChannel(self,chan):
        return self._writer.getChannel(chan)


class StreamReader(pyrogue.Device):
    """Stream Reader Wrapper"""

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
                                         if value == False:
                                             self._parent._reader.close()
                                         else:
                                             self._parent._reader.open(self._parent._file)
                                         self._parent._open = value
                                     """,
                         getFunction='value = self._parent._open')

    def _getStreamMaster(self):
        return self._reader

