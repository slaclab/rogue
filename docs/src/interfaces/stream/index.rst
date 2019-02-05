.. _interfaces_stream:

Stream Interface
================

The stream interface provides a mechanism for moving bulk data between 
modules within Rogue. This interface consists of a Frame container which
contains a series of Buffers which contain the payload data. A stream interface
consists of a Master which is the source of the Rogue Frame and a slave which
is the destination of the Frame. 

A stream master and slave are connected using the following command in python:

.. code:: python

   import pyrogue

   pyrogue.streamConnect(myMaster, mySlave)

A similiar line of code is used to connect a master and slave in c++:

.. code:: cpp

   #include <rogue/Helpers.h>

   streamConnect(myMaster, mySlave)

The above commands connect the Master to its primary Slave interface. This is
an important connection because the the Master will use this Slave to allocate new
frames in most cases. The process of allocating new frames is described in more detail
in the :ref:'interface_stream_frame' section of this document. The primary Slave is always
the last Slave to receive the Frame.

Additional receivers can be added to a master using a streamTap function. This allows more than
one Slave to receive data from a Master. The following python command will add a secondary 
Slave to a Master:

.. code:: python

   import pyrogue

   pyrogue.streamTap(myMaster, mySlave)

And in C++:

.. code:: cpp

   #include <rogue/Helpers.h>

   streamTap(myMaster, mySlave)

A entity can server as both a stream Master and Slave. This is often the case when
using a network protocol such as UDP or TCP. Two dual purpose enpoints can be connected together
to create a bi-directional data stream using the following command in python:

.. code:: python

   import pyrogue

   pyrogue.streamConnectBiDir(enPointA, endPointB)

This command sets endPointB as the primary Slave for endPointA at the same time setting endPointA as the
primary slave for endPointB. A similiar command is available in C++:

.. code:: cpp

   #include <rogue/Helpers.h>

   streamConnectBiDir(endPointA, endPointB)

More documentation of using the stream interface can be found in the following sections:

.. toctree::
   :maxdepth: 1
   :caption: Stream Interface:

   frame
   frameIterator
   frameLock
   buffer
   master
   slave
   pool
   bridge
   fifo
   filter

