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

Creating a Master sub-class in c++ is done in a similiar fashion. A new frame is 
requested just as it is in python and the sendFrame() method is used to pass the
frame to the connected Slaves. The main difference is that accessing the Frame
data can be done more directly using an interator. 

The example below shows the most direct method for updating data within a frame using 
an iterator. Here we both de-reference the iterator directly to update specific locations 
and we use std::copy to move data from data buffer into the Frame.

.. code-block:: c

   #import <rogue/interfaces/stream/Master.h>
   #import <rogue/interfaces/stream/Frame.h>
   #import <rogue/interfaces/stream/FrameIterator.h>

   class MyCustomMaster : public rogue::interfaces::stream::Master {
      public:

         MyCustomMaster() : rogue::interfaces::stream::Master() { }

         void myFrameGen() {
            rogue::interfaces::stream::FramePtr frame;
            rogue::interfaces::stream::FrameIterator it;
            uint32_t x;

            // First request an empty from from the primary slave
            // The first arg is the size, the second arg is a boolean
            // indicating if we can allow zero copy buffers, usually set to true

            // Here we request a frame capable of holding 100 bytes
            frame = reqFrame(100,true);

            // Here we get an iterator to the frame data in write mode
            it = frame->beginWrite();

            // Set an incrementing value to the first 10 locations
            for (x=0; x < 10; x++) {
               *it = x;
               it++;
            }

            // Use std::copy to copy data from a data buffer
            // Here we copy 10 bytes starting a the current position of 10
            // Update the iterator
            it = std::copy(data, data+10, it);

            // Unlink the python API we must now specify the new payload size
            frame->setPayload(20);

            //Send frame
            sendFrame(frame);
         }
   };

The std::copy call works very well for moving data between two standard C++ iterators. It will
properly deal with iterators which manage non-contigous buffers, which may be the case when allocating 
new Frames. For example when sending large data frames over a UDP interface, the Slave which allocates the 
buffer may create a Frame consistaing up a number of 1500 byte frames which may exist at random locations
in memory. If we are to use std::copy in this case, it will detect that the passed iterator range is non-contigous, and default to a less performant method of copying data byte by byte.

In order to ensure the best possible performance, the Rogue :ref:`interfaces_stream_frame_iterator` provides
mechanisms for iterating through each contigous buffer. The following example performs a data copy from 
a passed data buffer into the Rogue frame, ensuring that the most effeciant copy methods are used:

.. code-block:: c

   #import <rogue/interfaces/stream/Frame.h>
   #import <rogue/interfaces/stream/FrameIterator.h>

   rogue::interfaces::stream::FrameIterator it;
   rogue::interfaces::stream::FramePtr frame;
   uint32_t  size;
   uint8_t * data;

   // Request a new buffer with 100 bytes
   frame = reqFrame(100,true);

   // Get an iterator to the start of the Frame
   it = frame->beginWrite();

   // Keep going until we get to the end of the Frame, assume the passed data pointer has 100 bytes
   while ( it != frame->endWrite() ) {

      // The rem buffer method returns the number of bytes left in the current contigous buffer
      size = it->remBuffer();

      // Copy size number of bytes, updating both pointers
      it = std::copy(data, data+size; it);
      data += size;
   }

   // Remember to update the new payload size 
   frame->setPayload(100);
     
Further study of the :ref:`interfaces_stream_frame` and :ref:`interfaces_stream_buffer` APIs will reveal more 
advanced methods of access frame and buffer data. 

