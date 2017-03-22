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

    def __init__(self, name, hidden=True):
        pyrogue.DataWriter.__init__(self, name=name, description='Stream Writer',hidden=hidden)
        self._writer = rogue.utilities.fileio.StreamWriter()

    def _setOpen(self,dev,var,value):
        if self._open != value:
            if value == False:

                # Dump config/status to file
                self._root._streamYamlVariables()
                self._writer.close()
            else:
                self._writer.open(self._dataFile)

                # Dump config/status to file
                self._root._streamYamlVariables()
            self._open = value

    def _setBufferSize(self,dev,var,value):
        self._bufferSize = value
        self._writer.setBufferSize(value)

    def _setMaxFileSize(self,dev,var,value):
        self._maxFileSize = value
        self._writer.setMaxSize(value)

    def _getFileSize(self,dev,var):
        return self._writer.getSize()

    def _getFrameCount(self,dev,var):
        return self._writer.getFrameCount()

    def _waitFrameCount(self, count):
        self._writer.waitFrameCount(count)

    def getChannel(self,chan):
        return self._writer.getChannel(chan)


class StreamReader(pyrogue.Device):
    """Stream Reader Wrapper"""

    def __init__(self, name):

        pyrogue.Device.__init__(self, name=name, description='Stream Writer', 
                                size=0, memBase=None, offset=0)

        self._reader      = rogue.utilities.fileio.StreamReader()
        self._file        = ""
        self._open        = False
        self._bufferSize  = 0
        self._maxFileSize = 0

        self.add(pyrogue.Variable(name='dataFile', description='Data File',
                                  bitSize=0, bitOffset=0, base='string', mode='RW',
                                  setFunction='dev._file = value',
                                  getFunction='value = dev._file'))

        self.add(pyrogue.Variable(name='open', description='Data file open state',
                                  bitSize=1, bitOffset=0, base='bool', mode='RW',
                                  setFunction="""\
                                              if dev._open != int(value):
                                                  if value == False:
                                                      dev._reader.close()
                                                  else:
                                                      dev._reader.open(dev._file)
                                                  dev._open = value
                                              """,
                                  getFunction='value = dev._open'))

    def _getStreamMaster(self):
        return self._reader

