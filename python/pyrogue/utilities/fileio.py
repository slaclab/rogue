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

    def _setBufferSize(self,dev,var,value):
        self._writer.setBufferSize(value)

    def _setMaxFileSize(self,dev,var,value):
        self._writer.setMaxSize(value)

    def _getFileSize(self,dev,var):
        return self._writer.getSize()

    def _getFrameCount(self,dev,var):
        return self._writer.getFrameCount()

    def _waitFrameCount(self, count):
        self._writer.waitFrameCount(count)

    def getChannel(self,chan):
        return self._writer.getChannel(chan)

    def setDropErrors(self,drop):
        self._writer.setDropErrors(drop)


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

