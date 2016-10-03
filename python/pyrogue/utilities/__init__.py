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

class Prbs(pyrogue.Device):
    """PRBS Wrapper"""

    def __init__(self, parent, name):

        pyrogue.Device.__init__(self, parent=parent, name=name, description='PRBS Software Receiver', 
                                size=0, memBase=None, offset=0)

        self._prbs       = rogue.utilities.Prbs()
        self._txEnable   = False
        self._size       = 1000
        self._enMessages = False

        pyrogue.Variable(parent=self, name='txSize', description='PRBS Frame Size',
                         bitSize=32, bitOffset=0, base='uint', mode='RW',
                         setFunction='self._parent._size = value',
                         getFunction='value = self._parent._size')

        pyrogue.Variable(parent=self, name='txEnable', description='PRBS Run Enable',
                         bitSize=1, bitOffset=0, base='bool', mode='RW',
                         setFunction="""\
                                     if self._parent._txEnable != int(value):
                                         if int(value) == 0:
                                             self._parent._prbs.disable()
                                         else:
                                             self._parent._prbs.enable(self._parent._size)
                                         self._parent._txEnable = int(value)
                                     """,
                         getFunction='value = self._parent._txEnable')

        pyrogue.Command(parent=self, name='genFrame',description='Generate a single frame',
                        function='self._parent._prbs.genFrame(self._parent._size)')

        pyrogue.Variable(parent=self, name='rxErrors', description='RX Error Count',
                         bitSize=32, bitOffset=0, base='uint', mode='RO',
                         setFunction=None, getFunction='value = self._parent._prbs.getRxErrors()')

        pyrogue.Variable(parent=self, name='rxCount', description='RX Count',
                         bitSize=32, bitOffset=0, base='uint', mode='RO',
                         setFunction=None, getFunction='value = self._parent._prbs.getRxCount()')

        pyrogue.Variable(parent=self, name='rxBytes', description='RX Bytes',
                         bitSize=32, bitOffset=0, base='uint', mode='RO',
                         setFunction=None, getFunction='value = self._parent._prbs.getRxBytes()')

        pyrogue.Variable(parent=self, name='txErrors', description='TX Error Count',
                         bitSize=32, bitOffset=0, base='uint', mode='RO',
                         setFunction=None, getFunction='value = self._parent._prbs.getTxErrors()')

        pyrogue.Variable(parent=self, name='txCount', description='TX Count',
                         bitSize=32, bitOffset=0, base='uint', mode='RO',
                         setFunction=None, getFunction='value = self._parent._prbs.getTxCount()')

        pyrogue.Variable(parent=self, name='txBytes', description='TX Bytes',
                         bitSize=32, bitOffset=0, base='uint', mode='RO',
                         setFunction=None, getFunction='value = self._parent._prbs.getTxBytes()')

        pyrogue.Command(parent=self, name='resetCount',description='Reset counters',
                        function='self._parent._prbs.resetCount()')

        pyrogue.Variable(parent=self, name='enMessages', description='PRBS Run Enable',
                         bitSize=1, bitOffset=0, base='bool', mode='RW',
                         setFunction="""\
                                         self._parent._enMessages = int(value)
                                         self._parent._prbs.enMessages(self._parent._enMessages)
                                     """,
                         getFunction='value = self._parent._enMessages')

    def _getStreamSlave(self):
        return self._prbs

    def _getStreamMaster(self):
        return self._prbs

    def _readOthers(self):
        self.rxErrors.read()
        self.rxCount.read()
        self.rxBytes.read()
        self.rxErrors.read()
        self.rxCount.read()
        self.txBytes.read()

        self.rxErrors._updated()
        self.rxCount._updated()
        self.rxBytes._updated()
        self.rxErrors._updated()
        self.rxCount._updated()
        self.txBytes._updated()

    def _pollOthers(self):
        self._readOthers()

