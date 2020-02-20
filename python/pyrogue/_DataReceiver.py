#-----------------------------------------------------------------------------
# Title      : PyRogue base module - Data Receiver Device
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
import rogue.interfaces.memory as rim
import rogue.interfaces.stream as ris
import pyrogue as pr
import numpy
import time

class DataReceiver(pr.Device,ris.Slave):
    """Data Receiver Devicer."""

    def __init__(self, *, maxRate=30, **kwargs):
        py.Device.__init__(self, **kwargs)
        self._lastTime = time.time()

        self.add(pr.LocalVariable(name='RxEnable',
                                  value=True,
                                  description='Frame Rx Enable'))

        self.add(pr.LocalVariable(name='MaxRxRate',
                                  value=maxRate,
                                  units='Hz',
                                  description='Max allowed Rx Frame Rate'))

        self.add(pr.LocalVariable(name='FrameCount',
                                  value=0,
                                  pollInterval=1,
                                  description='Frame Rx Counter'))

        self.add(pr.LocalVariable(name='ErrorCount',
                                  value=0,
                                  pollInterval=1,
                                  description='Frame Error Counter'))

        self.add(pr.LocalVariable(name='ByteCount',
                                  value=0,
                                  pollInterval=1,
                                  description='Byte Rx Counter'))

        self.add(pr.LocalVariable(name='Updated',
                                  value=False,
                                  description='Data has been updated flag'))

        self.add(pr.LocalVariable(name='Data',
                                  hidden=True,
                                  value=numpy.empty(shape=0, dtype=numpy.Int8, order='C'),
                                  description='Data Frame Container'))

    def countReset(self):
        self.FrameCount.set(0)
        self.ErrorCount.set(0)
        self.ByteCount.set(0)
        super().countReset()

    def _acceptFrame(self, frame):

        # Lock frame
        with frame.lock():

            # Drop errored frames
            if frame.getError() != 0:
                with self.ErrorCount.lock:
                    self.ErrorCount.set(self.ErrorCount.value() + 1, write=False)

                return

            # Get numpy array from frame
            fl = frame.getPayload()
            nb = frame.getNumpy(0,fl)  # uint8

            with self.FrameCount.lock:
                self.FrameCount.set(self.FrameCount.value() + 1, write=False)

            with self.ByteCount.lock:
                self.ByteCount.set(self.ByteCount.value() + fl, write=False)

        # User overridable method for numpy restructuring
        self.process(nb)


    def process(self,npArray):
        """
        The user can use this method to restructure the numpy array.
        This may include separating data, header and other payload sub-fields
        The user should track the max refresh rate using the self._lastTime variable.
        """
        doWrite = False

        # Check for min period
        if (time.time() - self._lastTime) > (1.0 / float(MaxRxRate.value())):
            doWrite = True
            self._lastTime = time.time()

        # Update data
        self.Data.set(npArray,write=doWrite)
        self.Updated.set(True,write=doWrite)
