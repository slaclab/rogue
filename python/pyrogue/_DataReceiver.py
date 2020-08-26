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
import rogue.interfaces.stream as ris
import pyrogue as pr
import numpy
import time


class DataReceiver(pr.Device,ris.Slave):
    """Data Receiver Devicer."""

    def __init__(self, *, **kwargs):
        pr.Device.__init__(self, **kwargs)

        self.add(pr.LocalVariable(name='RxEnable',
                                  value=True,
                                  description='Frame Rx Enable'))

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

            with self.FrameCount.lock:
                self.FrameCount.set(self.FrameCount.value() + 1, write=False)

            with self.ByteCount.lock:
                self.ByteCount.set(self.ByteCount.value() + fl, write=False)

            # User overridable method for data restructuring
            self.process(frame)


    def process(self,frame):
        """
        The user can use this method to process the data, by default a byte numpy array is generated
        This may include separating data, header and other payload sub-fields
        This all occurs with the frame lock held
        """

        # Get data from frame
        fl = frame.getPayload()
        dat = frame.getNumpy(0,fl)  # uint8

        # Update data
        self.Data.set(dat,write=doWrite)
        self.Updated.set(True,write=doWrite)
