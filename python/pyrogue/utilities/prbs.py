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

        pyrogue.Device.__init__(self, name=name, description='PRBS Software Receiver', 
                                size=0, memBase=None, offset=0)

        self._prbs       = rogue.utilities.Prbs()
        self._enMessages = False

        self.add(pyrogue.Variable(name='rxErrors', description='RX Error Count',
                                  bitSize=32, bitOffset=0, base='uint', mode='RO',
                                  setFunction=None, getFunction='value = dev._prbs.getRxErrors()'))

        self.add(pyrogue.Variable(name='rxCount', description='RX Count',
                                  bitSize=32, bitOffset=0, base='uint', mode='RO',
                                  setFunction=None, getFunction='value = dev._prbs.getRxCount()'))

        self.add(pyrogue.Variable(name='rxBytes', description='RX Bytes',
                                  bitSize=32, bitOffset=0, base='uint', mode='RO',
                                  setFunction=None, getFunction='value = dev._prbs.getRxBytes()'))

        self.add(pyrogue.Command(name='resetCount',description='Reset counters',
                                 function='dev._prbs.resetCount()'))

        self.add(pyrogue.Variable(name='enMessages', description='Enable error messages',
                                  bitSize=1, bitOffset=0, base='bool', mode='RW',
                                  setFunction="""\
                                                  dev._enMessages = value
                                                  dev._prbs.enMessages(int(dev._enMessages))
                                              """,
                                  getFunction='value = dev._enMessages'))

    def _getStreamSlave(self):
        return self._prbs

    def _read(self):
        self.rxErrors.get()
        self.rxCount.get()
        self.rxBytes.get()
        pyrogue.Device._read(self)

    def _poll(self):
        self.rxErrors.get()
        self.rxCount.get()
        self.rxBytes.get()
        pyrogue.Device._poll(self)


class PrbsTx(pyrogue.Device):
    """PRBS TX Wrapper"""

    def __init__(self, name):

        pyrogue.Device.__init__(self, name=name, description='PRBS Software Transmitter', 
                                size=0, memBase=None, offset=0)

        self._prbs       = rogue.utilities.Prbs()
        self._txEnable   = False
        self._size       = 1000

        dev.add(pyrogue.Variable(name='txSize', description='PRBS Frame Size', base='uint', mode='RW',
                                 setFunction='dev._size = value',
                                 getFunction='value = dev._size'))

        dev.add(pyrogue.Variable(name='txEnable', description='PRBS Run Enable', base='bool', mode='RW',
                                 setFunction="""\
                                             if dev._txEnable != int(value):
                                                 if int(value) == 0:
                                                     dev._prbs.disable()
                                                 else:
                                                     dev._prbs.enable(dev._size)
                                                 dev._txEnable = int(value)
                                             """,
                                 getFunction='value = dev._txEnable'))

        dev.add(pyrogue.Command(name='genFrame',description='Generate a single frame',
                                function='dev._prbs.genFrame(dev._size)'))

        dev.add(pyrogue.Variable(name='txErrors', description='TX Error Count', base='uint', mode='RO',
                                 setFunction=None, getFunction='value = dev._prbs.getTxErrors()'))

        dev.add(pyrogue.Variable(name='txCount', description='TX Count', base='uint', mode='RO',
                                 setFunction=None, getFunction='value = dev._prbs.getTxCount()'))

        dev.add(pyrogue.Variable(name='txBytes', description='TX Bytes', base='uint', mode='RO',
                                 setFunction=None, getFunction='value = dev._prbs.getTxBytes()'))

        dev.add(pyrogue.Command(name='resetCount',description='Reset counters',
                                function='dev._prbs.resetCount()'))

    def _getStreamMaster(self):
        return self._prbs

    def _read(self):
        self.txErrors.get()
        self.txCount.get()
        self.txBytes.get()
        pyrogue.Device._read(self)

    def _poll(self):
        self.txErrors.get()
        self.txCount.get()
        self.txBytes.get()
        pyrogue.Device._poll(self)



