.. _interfaces_stream_receiving:

================
Receiving Frames
================

Frames are received by a subclass of the :ref:`interfaces_stream_slave` class in rogue.
This subclass can be created either in python or in c++. In either case a received frame
results in the execution of the the acceptFrame method in the subclass instance. Python
and C++ subclasses of the Slave class can be used interchangeably, allowing c++ subclasses 
to receive frames from python masters and python subclasses to receive frames from c++ masters.

Python Slave Subclass
=====================

Implementing a Slave subclass in python is easy, but may result in a lower level of performance.

.. code-block:: python

   import rogue.interfaces.stream

   class MyCustomSlave(rogue.interfaces.stream.Slave):

       # Init method must call the parent class init
       def __init__(self):
           super().__init__()

       # Method which is called when a frame is received
       def _acceptFrame(self,frame):

           # First it is good practice to hold a lock on the frame data.
           with frame.lock():

               # Next we can get the size of the frame payload
               size = frame.getPayload()

               # To access the data we need to create a byte array to hold the data
               fullData = bytearray(size)

               # Next we read the frame data into the byte array, from offset 0
               frame.read(fullData,0)

               # Alternatively we can copy a portion of the data from an arbitrary offset
               partialData = bytearray(10)

               # Read 10 bytes starting at offset 100
               frame.read(partialData,5) 

           # Since the data is coped into the passed byte arrays we are free to
           # access the copied data outside of the lock
           print("First byte is {:#}".format(fullData[0]))
           print("Byte 6 is {:#}".format(partialData[1]))

C++ Slave Subclass
==================

Creating a Slave sub-class in c++ is done in a similar fashion. In order to use a custom
c++ Slave subclass, you will need to build it into a c++ python module or into
a c++ application. See the sections :ref:`custom_module` and :ref:`installing_application`.

The example below shows the most direct method for receiving data from a Frame using 
an iterator. Here we both de-reference the iterator directly to update specific locations 
and we use std::copy to move data from the Frame to a data buffer.

.. code-block:: c

   #include <rogue/interfaces/stream/Slave.h>
   #include <rogue/interfaces/stream/Frame.h>
   #include <rogue/interfaces/stream/FrameIterator.h>
   #include <rogue/interfaces/stream/FrameLock.h>

   class MyCustomSlave : public rogue::interfaces::stream::Slave {
      public:

         // Create a static class creator to return our custom class
         // wrapped with a shared pointer
         static std::shared_ptr<MyCustomSlave> create() {
            static std::shared_ptr<MyCustomSlave> ret =
               std::make_shared<MyCustomSlave>();
            return(ret);
         }

         MyCustomSlave() : rogue::interfaces::stream::Slave() { }

         void acceptFrame ( std::shared_ptr<rogue::interfaces::stream::Frame> frame ) {
            rogue::interfaces::stream::FrameIterator it;
            uint32_t x;

            // Acquire lock on frame. Will be release when lock class goes out of scope
            rogue::interfaces::stream::FrameLock lock = frame->lock();

            // Here we get an iterator to the frame data
            it = frame->begin();

            // Print the values in the first 10 locations
            for (x=0; x < 10; x++) {
               printf("Location %i = 0x%x\n", *it);
               it++;
            }

            // Use std::copy to copy data to a data buffer
            // Here we copy the entire frame payload to the data buffer
            std::copy(frame->begin(), frame->end(), data);
         }
   };

   // Shared pointer alias
   typedef std::shared_ptr<MyCustomSlave> MyCustomSlavePtr;

The std::copy call works very well for moving data between two standard C++ iterators. It will
properly deal with iterators which manage non-contiguous buffers, which may be the case when receiving
Frames. For example when receiving large data frames from a UDP interface, the incoming data may
exist within a number of 1500 byte Buffers which may exist at random locations in memory. If we are to 
use std::copy in this case, it will detect that the passed iterator range is non-contiguous, and default to a 
less performant method of copying data byte by byte.

In order to ensure the best possible performance, the Rogue :ref:`interfaces_stream_frame_iterator` provides
mechanisms for iterating through each contiguous buffer. The following example performs a copy from 
the received Frame to a memory array.

.. code-block:: c

   // Get an iterator to the start of the Frame
   it = frame->begin();

   // Keep going until we get to the end of the Frame
   while ( it != frame->end() ) {

      // Copy the buffer data
      data = std::copy(it, it->endBuffer(), data);
      it = it->endBuffer();
   }

Alternatively if the user wishes to access individual values in the data frame at various offsets, 
they can make use of the fromFrame helper function defined in :ref:`interfaces_stream_helpers`. 

.. code-block:: c

   uint64_t data64;
   uint32_t data32;
   uint8_t  data8;
  
   it = frame->begin(); 

   // Read 64-bits and advance iterator 8 bytes 
   fromFrame(it, 8, &data64); 

   // Read 32-bits and advance iterator 4 bytes
   fromFrame(it, 4, &data32);

   // Read 8-bits and advance iterator 1 byte
   fromFrame(it, 1, &data8);

Further study of the :ref:`interfaces_stream_frame` and :ref:`interfaces_stream_buffer` APIs will reveal more 
advanced methods of access frame and buffer data. 

