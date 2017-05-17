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

    def __init__(self, name):

        pyrogue.Device.__init__(self, name=name, description='PRBS Software Receiver')
        self._prbs = rogue.utilities.Prbs()

        self.add(pyrogue.LocalVariable(name='rxErrors', description='RX Error Count',
                                       base='uint', mode='RO', pollInterval=1, value=0,
                                       getFunction='value = dev._prbs.getRxErrors()'))

        self.add(pyrogue.LocalVariable(name='rxCount', description='RX Count',
                                       base='uint', mode='RO', pollInterval=1, value=0,
                                       getFunction='value = dev._prbs.getRxCount()'))

        self.add(pyrogue.LocalVariable(name='rxBytes', description='RX Bytes',
                                       base='uint', mode='RO', pollInterval=1, value=0,
                                       getFunction='value = dev._prbs.getRxBytes()'))

        self.add(pyrogue.LocalCommand(name='resetCount',description='Reset counters',
                                      function='dev._prbs.resetCount()'))

    def _getStreamSlave(self):
        return self._prbs


class PrbsTx(pyrogue.Device):
    """PRBS TX Wrapper"""

    def __init__(self, name):

        pyrogue.Device.__init__(self, name=name, description='PRBS Software Transmitter')

        self._prbs = rogue.utilities.Prbs()

        self.add(pyrogue.LocalVariable(name='txSize', description='PRBS Frame Size', 
                                       base='uint', mode='RW', value=0))

        self.add(pyrogue.LocalVariable(name='txEnable', description='PRBS Run Enable', base='bool', mode='RW',
                                       value=0, setFunction=self._txEnable))

        self.add(pyrogue.LocalCommand(name='genFrame',description='Generate a single frame',
                                      function='dev._prbs.genFrame(dev.txSize.get(read=False))'))

        self.add(pyrogue.LocalVariable(name='txErrors', description='TX Error Count', base='uint', mode='RO', pollPeriod = 1,
                                       value=0, getFunction='value = dev._prbs.getTxErrors()'))

        self.add(pyrogue.LocalVariable(name='txCount', description='TX Count', base='uint', mode='RO', pollPeriod = 1,
                                       value=0, getFunction='value = dev._prbs.getTxCount()'))

        self.add(pyrogue.LocalVariable(name='txBytes', description='TX Bytes', base='uint', mode='RO', pollPeriod = 1,
                                       value=0, getFunction='value = dev._prbs.getTxBytes()'))

        self.add(pyrogue.LocalCommand(name='resetCount',description='Reset counters',
                                      function='dev._prbs.resetCount()'))

    def _txEnable(self,dev,var,value,changed):
        if changed:
            if int(value) == 0:
                dev._prbs.disable()
            else:
                dev._prbs.enable(dev.txSize.get(read=False))

    def _getStreamMaster(self):
        return self._prbs

