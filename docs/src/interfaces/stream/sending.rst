.. _interfaces_stream_sending:

==============
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

Python and C++ subclasses of the Master class can be used interchangeably, allowing c++ subclasses
to receive Frames from python masters and python subclasses to receive Frames from c++ masters.

Python Master Subclass
======================

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
           # Locations not explicitly written, but below the highest written
           # index, will be considered valid, but may contain random data
           ba = bytearray([i*2 for i in range (10)])
           frame.write(ba,50)

           # At this point locations 0 - 9 and 50 - 59 contain known values
           # The new payload size is now 60, but locations 10 - 49 may
           # contain random data

           # Send the frame to the currently attached slaves
           # The method returns once all the slaves have received the
           # frame and their acceptFrame methods have returned
           self._sendFrame(frame)

C++ Master Subclass
===================

Creating a Master sub-class in c++ is done in a similar fashion. A new frame is
requested just as it is in python and the sendFrame() method is used to pass the
frame to the connected Slaves. The main difference is that accessing the Frame
data can be done more directly using an iterator.

In order to use a custom c++ Master subclass, you will need to build it into a c++ python module or into
a c++ application. See the sections :ref:`custom_module` and :ref:`installing_application`.

The example below shows the most direct method for updating data within a frame using
an iterator. Here we both de-reference the iterator directly to update specific locations
and we use std::copy to move data from data buffer into the Frame.

.. code-block:: c

   #import <rogue/interfaces/stream/Master.h>
   #import <rogue/interfaces/stream/Frame.h>
   #import <rogue/interfaces/stream/FrameIterator.h>

   class MyCustomMaster : public rogue::interfaces::stream::Master {
      public:

         // Create a static class creator to return our custom class
         // wrapped with a shared pointer
         static std::shared_ptr<MyCustomMaster> create() {
            static std::shared_ptr<MyCustomMaster> ret =
               std::make_shared<MyCustomMaster>();
            return(ret);
         }

         // Standard class creator which is called by create
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

            // Unlike the python API we must now specify the new payload size
            frame->setPayload(20);

            // Here we get an iterator to the frame data
            it = frame->begin();

            // Set an incrementing value to the first 10 locations
            for (x=0; x < 10; x++) {
               *it = x;
               it++;
            }

            // Use std::copy to copy data from a data buffer
            // Here we copy 10 bytes starting a the current position of 10
            // Update the iterator
            it = std::copy(data, data+10, it);

            //Send frame
            sendFrame(frame);
         }
   };

   // Shared pointer alias
   typedef std::shared_ptr<MyCustomMaster> MyCustomMasterPtr;


The std::copy call is the safest method for moving frame data round using The FrameIterator class. It will
properly deal with iterators which manage non-contiguous buffers, which may be the case when allocating
new Frames. For example when sending large data frames over a UDP interface, the Slave which allocates the
buffer may create a Frame consisting up a number of 1500 byte frames which may exist at random locations
in memory.

This however comes at a performance penalty as the iterator is updated on each access to the underlying Frame data. In
order to move data in the most effecient way, it is best to use std::memcpy with the data pointer interface
provided by the Buffer class.  The Rogue :ref:`interfaces_stream_frame_iterator` provides
mechanisms for iterating through each contiguous buffer. The following example performs a data copy from
a passed data buffer into the Rogue frame, ensuring that the most efficient copy methods are used:

.. code-block:: c

   uint32_t  size;
   uint8_t * data;

   // Request a new buffer with 100 bytes
   frame = reqFrame(100,true);

   // Update the new payload size
   frame->setPayload(100);

   // Get an iterator to the start of the Frame
   it = frame->begin();

   // Keep going until we get to the end of the Frame, assume the passed data pointer has 100 bytes
   while ( it != frame->end() ) {

      // The rem buffer method returns the number of bytes left in the current contiguous buffer
      size = it->remBuffer();

      // Copy the data using the iterator ptr method
      std::memcpy(data, it->ptr(), size);

      // Update the pointer and the iterator
      data += size;
      it += size;
   }


Alternatively if the user wishes to access individual values in the data frame at various offsets,
they can make use of the toFrame helper function defined in :ref:`interfaces_stream_helpers`.

.. code-block:: c

   uint64_t data64;
   uint32_t data32;
   uint8_t  data8;

   // Update frame payload size
   frame->setPayload(13);

   it = frame->begin();

   // Write 64-bits and advance iterator 8 bytes
   toFrame(it, 8, &data64);

   // Write 32-bits and advance iterator 4 bytes
   toFrame(it, 4, &data32);

   // Write 8-bits and advance iterator 1 byte
   toFrame(it, 1, &data8);

In some cases the user will need high performance element level access to the frame data. The :ref:`interfaces_stream_frame_accessor`
provides a memory pointer mapped view of the frame data. There is a limitation in the use of a FrameAccessor in that it can
only map frame data that is represented by a single buffer. If the range to be accessed spans multiple buffers, attempting
to use a FrameAccessor will throw an exception. Luckily there is a helper in the :ref:`interfaces_stream_master` class
class which will verify that a given frame is representated by a single buffer. If this is not the case it create a copy of the
Frame into a new Frame which is made up of a single buffer.

The user must be carefull to not "flatten" a frame that is purposely segmented into multiple buffers (i.e. createa a frame for
sending over a UDP interface). The :ref:`interfaces_stream_frame_accessor` in combination with the ensureSingleBuffer() call on
received frames.

.. code-block:: c

   // First lets make sure the frame is made up of a single buffer
   // Set the request enable flag to true, allowing a new frame to
   // be created. (be carefull with this call, see note above)
   self->ensureSingleBuffer(frame,True);

   // Update frame payload size
   frame->setPayload(800);

   // Get the iterator
   it = frame->begin();

   // Create accessor at current iterator position
   // We want to access 100 64-bit values
   rogue::interfaces::stream::FrameAccessor<uint64_t> acc = rogue::interfaces::stream::FrameAccessor<uint64_t>(it,100);

   // We can now access the values as an array:
   acc[0] = value1;
   acc[1] = value2;

Further study of the :ref:`interfaces_stream_frame` and :ref:`interfaces_stream_buffer` APIs will reveal more
advanced methods of access frame and buffer data.

