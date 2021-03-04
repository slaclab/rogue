.. _interfaces_stream_debug_streams:

=================
Debugging Streams
=================

The base stream :ref:`interfaces_stream_Slave` class can server as a debug Frame receiver. This can
be useful when you want to display some or all of the data streams used in your designs. In most
cases the debug Slave module will be used as a secondary slave. In order to enable debugging the setDebug()
method of the Stream class must be called.

The following is an example of using the base Slave class as a debug monitor on a stream between
between an existing Master and Slave instance.

.. code-block:: python

   import rogue.interfaces.stream
   import pyrogue

   # Data source
   src = MyCustomMaster()

   # Data destination
   dst = MyCustomMaster()

   # Debug Slave
   dbg = rogue.interfaces.stream.slave()

   # Set debug mode for first 100 bytes, with name myDebug
   dbg.setDebug(100,"myDebug")

   # Connect the src and dst
   src >> dst

   # Add the debug slave as a second slave
   src >> dbg

Below is the equivalent code in C++

.. code-block:: c

   #include <rogue/interfaces/stream/Fifo.h>
   #include <MyCustomMaster.h>

   // Data source
   MyCustomMasterPtr src = MyCustomMaster::create()

   // Data destination
   MyCustomSlavePtr dst = MyCustomSlave::create();

   // Debug Slave
   rogue::interfaces::stream:;SlavePtr dbg = rogue::interfaces;:stream::Slave::create();

   // Set debug mode for first 100 bytes, with name myDebug
   dbg->setDebug(100,"myDebug");

   # Connect the src and dst
   *src >> dst;

   # Add the debug slave as a second slave
   *src >> dbg;

