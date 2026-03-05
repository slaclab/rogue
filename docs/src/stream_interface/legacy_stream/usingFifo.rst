.. _interfaces_stream_using_fifo:

============
Using A Fifo
============

A :ref:`interfaces_stream_fifo` object provides an elastic buffer between a stream Master and stream Slave. This can be
useful when absorbing flow control situations or providing a point where data Frames can be cleanly
dropped when the receiver can not keep up with a source. The use of a Fifo can can also be helpful
for tapping stream data for consumption by a slower process which may not be able to keep up with
the primary path data rate and may not want to consume all of the available data.

The Fifo has copy mode and trimSize attributes which support the following combinations:
* noCopy = True and trimSize = 0, original incoming Frames are inserted into the FIfo
* noCopy = False and trimSize = o, a full copy of the original frame is inserted into the Fifo
* noCopy = False and trimSize != 0, a partial copy of up to trimSize bytes is inserted into the Fifo

Additionally the Fifo has a maxDepth attribute which controls how it buffers data. When maxDepth = 0
the Fifo size is unlimited and Frames are never dropped. When maxDepth != 0 Frame data is dropped
once the Fifo Frame count reaches the maxDepth size.

In Line Fifo Example
====================

The following python example shows how to add a noCopy FIFO with maxDepth of 100 between a master
and a slave. The first arg maxDepth is set to 100, trimSize is set to 0, and noCopy is set True.

.. code-block:: python

   import rogue.interfaces.stream
   import pyrogue

   # Data source
   src = MyCustomMaster()

   # Data destination
   dst = MyCustomSlave()

   # Create a Fifo with maxDepth=100, trimSize=0, noCopy=True
   fifo = rogue.interfaces.stream.Fifo(100, 0, True)

   # Connect the fifo to the source and on to the destination
   src >> fifo >> dst

Below is the equivalent code in C++

.. code-block:: c

   #include <rogue/interfaces/stream/Fifo.h>
   #include <MyCustomMaster.h>
   #include <MyCustomSlave.h>

   // Data source
   MyCustomMasterPtr src = MyCustomMaster::create()

   // Data destination
   MyCustomSlavePtr dst = MyCustomSlave::create();

   // Create a Fifo with maxDepth=100, trimSize=0, noCopy=true
   rogue::interfaces::stream::FifoPtr fifo = rogue::interfaces::stream::Fifo::create(100, 0, true)

   // Connect the fifo to the source and on to the dst
   *(*src >> fifo) >> dst;

Stream Tap Fifo Example
=======================

The following python example shows how to add a copy  FIFO with maxDepth of 150 between a master
and a slave. This Fifo is configured to only copy the first 20 bytes of the Frame data.

.. code-block:: python

   import rogue.interfaces.stream
   import pyrogue

   # Data source
   src = MyCustomMaster()

   # Data desination
   dst = MyCustomMaster()

   # Additional monitor
   mon = MyCustomMonitor()

   # Create a Fifo with maxDepth=150, trimSize=20, noCopy=False
   fifo = rogue.interfaces.stream.Fifo(150, 20, False)

   # Connect the src and dst
   src >> dst

   # Add the FIFO as a second slave and on to the monitor, (using reverse operators as an example)
   mon << fifo << src

Below is the equivalent code in C++

.. code-block:: c

   #include <rogue/interfaces/stream/Fifo.h>
   #include <MyCustomMaster.h>

   // Data source
   MyCustomMasterPtr src = MyCustomMaster::create();

   // Data destination
   MyCustomSlavePtr dst = MyCustomSlave::create();

   // Additional monitor
   MyCustomMonitorPtr mon = MyCustomMonitor::create();

   # Create a Fifo with maxDepth=150, trimSize=20, noCopy=false
   rogue::interfaces::stream::FifoPtr fifo = rogue::interfaces::stream::Fifo::create(150, 20, false);

   # Connect the src and dst
   src >> dst;

   # Add the Fifo as a second stream and on to the monitor (reverse order show as an example)
   *( *mon << fifo ) << src;

