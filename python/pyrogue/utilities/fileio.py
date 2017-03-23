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
        if var.value != value:
            if value == False:
                # Dump config/status to file
                self._root._streamYamlVariables()
                self._writer.close()
            else:
                self._writer.open(self.dataFile)

                # Dump config/status to file
                self._root._streamYamlVariables()
            var.value = value

    def _setBufferSize(self,dev,var,value):
        var.value = value
        self._writer.setBufferSize(value)

    def _setMaxFileSize(self,dev,var,value):
        var.value = value
        self._writer.setMaxSize(value)

    def _getFileSize(self,dev,var):
        return self._writer.getSize()

    def _getFrameCount(self,dev,var):
        return self._writer.getFrameCount()

    def waitFrameCount(self, count):
        self._writer.waitFrameCount(count)

    def getChannel(self,chan):
        return self._writer.getChannel(chan)


class StreamReader(pyrogue.Device):
    """Stream Reader Wrapper"""

    def __init__(self, name):

        pyrogue.Device.__init__(self, name=name, description='Stream Writer', 
                                memBase=None, offset=0)

        self._reader      = rogue.utilities.fileio.StreamReader()
        self._bufferSize  = 0
        self._maxFileSize = 0

        self.add(
            pyrogue.Variable(name='dataFile', value='', local=True, description='Data File'),
            pyrogue.Variable(name='open', value=False, local=True, mode='RW',
                             setFunction=self._setOpen,
                             description='Data file open state'))

    def _setOpen(self, dev, var, value):
        if dev.open != int(value):
            if value == False:
                dev._reader.close()
            else:
                dev._reader.open(dev.dataFile)
            var.value = value

    def _getStreamMaster(self):
        return self._reader

