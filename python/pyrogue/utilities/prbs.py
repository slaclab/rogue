#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Title      : PyRogue Utilities base module
#-----------------------------------------------------------------------------
# File       : pyrogue/utilities/__init__.py
# Author     : Ryan Herbst, rherbst@slac.stanford.edu
# Created    : 2016-09-29
# Last update: 2016-09-29
#-----------------------------------------------------------------------------
# Description:
# Module containing the utilities module class and methods
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
import pyrogue

class PrbsRx(pyrogue.Device):
    """PRBS RX Wrapper"""

    def __init__(self, *, name):

        pyrogue.Device.__init__(self, name=name, description='PRBS Software Receiver')
        self._prbs = rogue.utilities.Prbs()

        self.add(pyrogue.LocalVariable(name='rxErrors', description='RX Error Count',
                                       mode='RO', pollInterval=1, value=0,
                                       localGet=self._prbs.getRxErrors))

        self.add(pyrogue.LocalVariable(name='rxCount', description='RX Count',
                                       mode='RO', pollInterval=1, value=0,
                                       localGet=self._prbs.getRxCount))

        self.add(pyrogue.LocalVariable(name='rxBytes', description='RX Bytes',
                                       mode='RO', pollInterval=1, value=0,
                                       localGet=self._prbs.getRxBytes))

        self.add(pyrogue.LocalVariable(name='checkPayload', description='Payload Check Enable',
                                       mode='RW', value=True, localSet=self._plEnable))

    def _plEnable(self,value,changed):
        self._prbs.checkPayload(value)

    def countReset(self):
        self._prbs.resetCount()

    def _getStreamSlave(self):
        return self._prbs

    def setWidth(self,width):
        self._prbs.setWidth(width)

    def setTaps(self,taps):
        self._prbs.setTaps(taps)

class PrbsTx(pyrogue.Device):
    """PRBS TX Wrapper"""

    def __init__(self, *, name):

        pyrogue.Device.__init__(self, name=name, description='PRBS Software Transmitter')

        self._prbs = rogue.utilities.Prbs()

        self.add(pyrogue.LocalVariable(name='txSize', description='PRBS Frame Size', 
                                       mode='RW', value=0))

        self.add(pyrogue.LocalVariable(name='txEnable', description='PRBS Run Enable', mode='RW',
                                       value=False, localSet=self._txEnable))

        self.add(pyrogue.LocalCommand(name='genFrame',description='Generate a single frame',
                                      function=self._genFrame))

        self.add(pyrogue.LocalVariable(name='txErrors', description='TX Error Count', mode='RO', pollInterval = 1,
                                       value=0, localGet=self._prbs.getTxErrors))

        self.add(pyrogue.LocalVariable(name='txCount', description='TX Count', mode='RO', pollInterval = 1,
                                       value=0, localGet=self._prbs.getTxCount))

        self.add(pyrogue.LocalVariable(name='txBytes', description='TX Bytes', mode='RO', pollInterval = 1,
                                       value=0, localGet=self._prbs.getTxBytes))

    def countReset(self):
        self._prbs.resetCount()

    def _genFrame(self):
        self._prbs.genFrame(self.txSize.value())

    def _txEnable(self,value,changed):
        if changed:
            if int(value) == 0:
                self._prbs.disable()
            else:
                self._prbs.enable(self.txSize.value())

    def _getStreamMaster(self):
        return self._prbs

    def setWidth(self,width):
        self._prbs.setWidth(width)

    def setTaps(self,taps):
        self._prbs.setTaps(taps)

