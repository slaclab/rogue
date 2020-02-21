#-----------------------------------------------------------------------------
# Title      : PyRogue Utilities base module
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

    def __init__(self, *, width=None, checkPayload=True, taps=None, stream=None, **kwargs ):

        pyrogue.Device.__init__(self, description='PRBS Software Receiver', **kwargs)
        self._prbs = rogue.utilities.Prbs()

        if width is not None:
            self._prbs.setWidth(width)

        if taps is not None:
            self._prbs.setTaps(taps)

        if stream is not None:
            pyrogue.streamConnect(stream, self)

        self.add(pyrogue.LocalVariable(name='rxEnable', description='RX Enable',
                                       mode='RW', value=True,
                                       localGet=lambda : self._prbs.getRxEnable(),
                                       localSet=lambda value: self._prbs.setRxEnable(value)))

        self.add(pyrogue.LocalVariable(name='rxErrors', description='RX Error Count',
                                       mode='RO', pollInterval=1, value=0, typeStr='UInt32',
                                       localGet=self._prbs.getRxErrors))

        self.add(pyrogue.LocalVariable(name='rxCount', description='RX Count',
                                       mode='RO', pollInterval=1, value=0, typeStr='UInt32',
                                       localGet=self._prbs.getRxCount))

        self.add(pyrogue.LocalVariable(name='rxBytes', description='RX Bytes',
                                       mode='RO', pollInterval=1, value=0, typeStr='UInt32',
                                       localGet=self._prbs.getRxBytes))

        self.add(pyrogue.LocalVariable(name='rxRate', description='RX Rate', disp="{:.3e}",
                                       mode='RO', pollInterval=1, value=0.0, units='Frames/s',
                                       localGet=self._prbs.getRxRate))

        self.add(pyrogue.LocalVariable(name='rxBw', description='RX BW', disp="{:.3e}",
                                       mode='RO', pollInterval=1, value=0.0, units='Bytes/s',
                                       localGet=self._prbs.getRxBw))

        self.add(pyrogue.LocalVariable(name='checkPayload', description='Payload Check Enable',
                                       mode='RW', value=checkPayload, localSet=self._plEnable))

    def _plEnable(self,value,changed):
        self._prbs.checkPayload(value)

    def countReset(self):
        self._prbs.resetCount()
        super().countReset()

    def _getStreamSlave(self):
        return self._prbs

    def __lshift__(self,other):
        pyrogue.streamConnect(other,self)
        return other

    def setWidth(self,width):
        self._prbs.setWidth(width)

    def setTaps(self,taps):
        self._prbs.setTaps(taps)


class PrbsTx(pyrogue.Device):
    """PRBS TX Wrapper"""

    def __init__(self, *, sendCount=False, width=None, taps=None, stream=None, **kwargs ):

        pyrogue.Device.__init__(self, description='PRBS Software Transmitter', **kwargs)
        self._prbs = rogue.utilities.Prbs()

        if width is not None:
            self._prbs.setWidth(width)

        if taps is not None:
            self._prbs.setTaps(taps)

        if stream is not None:
            pyrogue.streamConnect(self, stream)

        self._prbs.sendCount(sendCount)

        self.add(pyrogue.LocalVariable(name='txSize', description='PRBS Frame Size', units='Bytes',
                                       localSet=self._txSize, mode='RW', value=1024, typeStr='UInt32'))

        self.add(pyrogue.LocalVariable(name='txEnable', description='PRBS Run Enable', mode='RW',
                                       value=False, localSet=self._txEnable))

        self.add(pyrogue.LocalCommand(name='genFrame',description='Generate n frames',value=1,
                                      function=self._genFrame))

        self.add(pyrogue.LocalVariable(name='txErrors', description='TX Error Count', mode='RO', pollInterval = 1,
                                       value=0, typeStr='UInt32', localGet=self._prbs.getTxErrors))

        self.add(pyrogue.LocalVariable(name='txCount', description='TX Count', mode='RO', pollInterval = 1,
                                       value=0, typeStr='UInt32', localGet=self._prbs.getTxCount))

        self.add(pyrogue.LocalVariable(name='txBytes', description='TX Bytes', mode='RO', pollInterval = 1,
                                       value=0, typeStr='UInt32', localGet=self._prbs.getTxBytes))

        self.add(pyrogue.LocalVariable(name='genPayload', description='Payload Generate Enable',
                                       mode='RW', value=True, localSet=self._plEnable))

        self.add(pyrogue.LocalVariable(name='txRate', description='TX Rate',  disp="{:.3e}",
                                       mode='RO', pollInterval=1, value=0.0, units='Frames/s',
                                       localGet=self._prbs.getTxRate))

        self.add(pyrogue.LocalVariable(name='txBw', description='TX BW',  disp="{:.3e}",
                                       mode='RO', pollInterval=1, value=0.0, units='Bytes/s',
                                       localGet=self._prbs.getTxBw))

    def _plEnable(self,value,changed):
        self._prbs.genPayload(value)

    def countReset(self):
        self._prbs.resetCount()
        super().countReset()

    def _genFrame(self,arg=1):
        for i in range(arg):
            self._prbs.genFrame(self.txSize.value())

    def _txSize(self,value,changed):
        if changed and int(self.txEnable.value()) == 1:
            self._prbs.disable()
            self._prbs.enable(value)

    def _txEnable(self,value,changed):
        if changed:
            if int(value) == 0:
                self._prbs.disable()
            else:
                self._prbs.enable(self.txSize.value())

    def _getStreamMaster(self):
        return self._prbs

    def __rshift__(self,other):
        pyrogue.streamConnect(self,other)
        return other

    def setWidth(self,width):
        self._prbs.setWidth(width)

    def setTaps(self,taps):
        self._prbs.setTaps(taps)

    def sendCount(self,en):
        self._prbs.sendCount(en)


class PrbsPair(pyrogue.Device):
    def __init__(self, width=None, taps=None, sendCount=False, txStream=None, rxStream=None, **kwargs):
        super().__init__(self, **kwargs)
        self.add(PrbsTx(width=width, taps=taps, stream=txStream))
        self.add(PrbsRx(sendCount=sendCount, width=width, taps=taps, stream=rxStream))

    def setWidth(self, width):
        self.PrbsTx.setWidth(width)
        self.PrbsRx.setWidth(width)

    def setTaps(self, taps):
        self.PrbsTx.setTaps(taps)
        self.PrbsRx.setTaps(taps)

    def setCount(self, count):
        self.PrbsRx.setCount(count)

    def _getStreamMaster(self):
        return self.PrbsRx._getStreamMaster()

    def _getStreamSlave(self):
        return self.PrbsTx._getStreamSlave()

    def __rshift__(self,other):
        pyrogue.streamConnect(self,other)
        return other

    def __lshift__(self,other):
        pyrogue.streamConnect(other,self)
        return other

    def __eq__(self,other):
        pyrogue.streamConnectBiDir(other,self)
