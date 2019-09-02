#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Title      : PyRogue base module - Data Receiver Device
#-----------------------------------------------------------------------------
# File       : pyrogue/_DataReceiver.py
# Created    : 2019-09-19
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

class DataReceiver(pr.Device,ris.slave):
    """Data Receiver Devicer."""

    def __init__(self, **kwargs):
        py.Device.__init__(self, **kwargs)

        self.add(pr.LocalVariable(name='FrameCount', 
                                  value=0, 
                                  pollInterval=1,
                                  description='Frame Rx Counter'))

        self.add(pr.LocalVariable(name='ByteCount',  
                                  value=0, 
                                  pollInterval=1,
                                  description='Byte Rx Counter'))

        self.add(pr.LocalVariable(name='Data',       
                                  value=numpy.empty(shape=0, dtype=numpy.Int8, order='C'),
                                  description='Data Frame Container'))


    def _acceptFrame(self, frame):

        # The following block of lines needs to be made more effecient
        fl =  frame.getPayload()
        ba = bytearray(fl)
        frame.read(ba)

        # including this line, can we do this directly from a frame?
        nb = numpy.frombuffer(ba, dtype=int8, count=-1, offset=0)

        with self.FrameCount.lock:
            self.FrameCount.set(self.FrameCount.value() + 1, write=False)

        with self.ByteCount.lock:
            self.ByteCount.set(self.ByteCount.value() + fl, write=False)

        # Sub-process numpy restructuring
        self.process(nb)


    def process(self,npArray):
        """ 
        The user can use this method to restructure the numpy array.
        This may include seperating data, header and other payload types.
        """
        self.Data.set(npArray)


