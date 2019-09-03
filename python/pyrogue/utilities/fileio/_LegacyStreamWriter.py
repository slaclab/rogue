#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Title      : PyRogue FileIO - Legacy Stream Writer
#-----------------------------------------------------------------------------
# File       : pyrogue/utilities/filio/_LegacyStreamWriter.py
# Created    : 2016-09-29
#-----------------------------------------------------------------------------
# Description:
# Module for writing legacy stream data.
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
import pyrogue.utilities.fileio
import rogue.utilities.fileio

class LegacyStreamWriter(pyrogue.utilities.fileio.StreamWriter):
    def __init__(self, *, configEn=False, **kwargs):
        pyrogue.DataWriter.__init__(self, **kwargs)
        self._writer   = rogue.utilities.fileio.LegacyStreamWriter()
        self._configEn = configEn

    def getDataChannel(self):
        return self._writer.getDataChannel()

    def getYamlChannel(self):
        return self._writer.getYamlChannel()

