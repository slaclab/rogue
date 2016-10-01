#!/usr/bin/env python

import rogue.utilities
import pyrogue

class PrbsDevice(pyrogue.Device):
    """PRBS Device Wrapper"""

    def __init__(self, parent, name):

        pyrogue.Device.__init__(self, parent=parent, name=name, description='PRBS Software Receiver', 
                                size=0, memBase=None, offset=0)

        self._prbs       = rogue.utilities.Prbs()
        self._enable     = False
        self._size       = 1000
        self._enMessages = False

        pyrogue.Variable(parent=self, name='txSize', description='PRBS Frame Size',
                         bitSize=32, bitOffset=0, base='uint', mode='RW',
                         setFunction='self._parent._size = value',
                         getFunction='value = self._parent._size')

        pyrogue.Variable(parent=self, name='txEnable', description='PRBS Run Enable',
                         bitSize=1, bitOffset=0, base='bool', mode='RW',
                         setFunction="""\
                                     if self._parent._enable != int(value):
                                         if int(value) == 0:
                                             self._parent._prbs.disable()
                                         else:
                                             self._parent._prbs.enable(self._parent._size)
                                         self._parent._enable = int(value)
                                     """,
                         getFunction='value = self._parent._enable')

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

        pyrogue.Variable(parent=self, name='rxErrors', description='RX Error Count',
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
                                         self._parent._enable = int(value)
                                         self._parent._prbs.enMessages(self._parent._enable)
                                     """,
                         getFunction='value = self._parent._enMessages')

    def readAll(self):
        self.readPoll()

    def readPoll(self):
        self.rxErrors.readAndGet()
        self.rxCount.readAndGet()
        self.rxBytes.readAndGet()
        self.rxErrors.readAndGet()
        self.rxCount.readAndGet()
        self.txBytes.readAndGet()

    def getPrbs(self):
        return self._prbs

