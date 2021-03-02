.. _interfaces_stream_using_rate_drop:

========================
Using A Rate Drop Object
========================

A :ref:`interfaces_stream_rate_drop` object provides a mechanism for rate limiting stream frames
for receivers which can not keep up with data at the expected full rate. The RateDrop class allows
the user to drop limit the frame rate either by dropping every n frames, or by specifying a minimum time
period between frames.

RateDrop Example
================

The following python example shows how to limit the data rate in an incoming stream to 10hz.

.. code-block:: python

   import rogue.interfaces.stream
   import pyrogue

   # Data source
   src = MyCustomMaster()

   # Data destination
   dst = MyCustomSlave()

   # Create a rate drop module, with the period flag set to true and the
   # period value set to 0.01 seconds
   rate = rogue.interfaces.stream.RateDrop(True,0.01)

   # Connect the rate drop object to the source and on to the destination
   src >> rate >> dst

Below is the equivalent code in C++

.. code-block:: c

   #include <rogue/interfaces/stream/RateDrop.h>
   #include <MyCustomMaster.h>
   #include <MyCustomSlave.h>

   // Data source
   MyCustomMasterPtr src = MyCustomMaster::create()

   // Data destination
   MyCustomSlavePtr dst = MyCustomSlave::create();

   // Create a rate drop module, with the period flag set to true and the
   // period value set to 0.01 seconds
   rogue::interfaces::stream::RateDropPtr rate = rogue::interfaces::stream::RateDrop::create(True, 0.01);

   // Connect the rate drop object to the source and on to the dst
   *(*src >> fifo) >> dst;

