.. _interfaces_stream_sending:

Sending Frames
==============

Frames are transmitted by a subclass of the :ref:`interfaces_stream_master` class in rogue.
This subclass can be created either in python or in c++. In order to send a Frame, the 
master sub-class must first request the creation of a new Frame with enough space available for 
the intended payload. This is done by generating a Frame request to the primary slave with two
parameters: the Frame size and a zero copy enable flag. In most cases the implementer will
want to set the zero copy flag to True, allowing the primary slave to determine if it will
use zero copy buffers for the new Frame. If the master intends to re-use the Frame, i.e. sending it 
multiple times, it will want to disallow the creation of zero copy buffers. A Frame with 
zero copy buffers is usually emptied when it is passed to the primary slave and cannot be
reused.

Python and C++ subclasses of the Master class can be used interchagably, allowing c++ subclasses 
to receive Frames from python masters and python subclasses to receive Frames from c++ masters.

Python Master Subclass
----------------------

Implementing a Master subclass in python is easy, but may result in a lower level of performance.

.. code-block:: python

   import rogue.interfaces.stream

   class MyCustomMaster(rogue.interfaces.stream.Master):

       # Init method must call the parent class init
       def __init__(self):
           super().__init__()

       # Method for generating a frame
       def myFrameGen(self):

           # First request an empty from from the primary slave
           # The first arg is the size, the second arg is a boolean
           # indicating if we can allow zero copy buffers, usually set to true

           # Here we request a frame capable of holding 100 bytes
           frame = self._reqFrame(100, True)

           # Create a 10 byte array with an incrementing value
           ba = bytearray([i for i in range(10)])

           # Write the data to the frame at offset 0
           # The payload size of the frame is automatically updated
           # to the highest index which as written to.
           # A lock is not required because we are the only instance
           # which knows about this frame at this point

           # The frame will now have a payload size of 10
           frame.write(ba,0)

           # The user may also write to an arbitrary offset, the valid payload
           # size of the frame is set to the highest index written. 
           # Locations not explicity written, but below the highest written
           # index, will be considered valid, but may contain random data
           ba = bytearray([i*2 for i in range 10])
           frame.write(ba,50)

           # At this point locations 0 - 9 and 50 - 59 contain known values
           # The new payload size is now 60, but locations 10 - 49 may 
           # contain random data

           # Send the frame to the currently attached slaves
           # The method returns once all the slaves have received the
           # frame and their acceptFrame methods have returned
           self._sendFrame(frame)

C++ Master Subclass
-------------------


