.. _interfaces_stream_fifo:

Fifo
=====

A Fifo allows :ref:`interfaces_stream_frame` data to be buffered between the Master and Slave. This can be usefull for absorbing
backpressure in a streaming DAQ system. Frame data is received by the FIFO and then sent to its attached Slave 
objects in an indepdent thread. It can also be used when tapping the main data path to a seperate
Frame Slave device such as a live display GUI. Use of a FIFO in that situation isolates the main
data path from the slow GUI. 

The FIFO object can either create a copy of the Frame or insert the original Frame object into the 
FIFO. When operating in copy mode the Fifo can be configured to only copy a maximum amount of data 
into the new Frame.

When operating in fixed size mode, the FIFO will only accept a defined number of Frame. Once it has
reached the defined threshold, incoming frames will be dropped.

Examples of using a Fifo are described in :ref:`interfaces_stream_using_fifo`.

The Fifo class generates log entries with the path: "pyrogue.stream.Fifo"

Fifo objects in C++ are referenced by the following shared pointer typedef:

.. doxygentypedef:: rogue::interfaces::stream::FifoPtr

The class description is shown below:

.. doxygenclass:: rogue::interfaces::stream::Fifo
   :members:

