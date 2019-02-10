.. _interfaces_stream_filter:

Filter
======

A Filter allows :ref:`interfaces_stream_frame` objects to be filtered, only allow 
frames for a particular channel to be passed. Optionally errored frames can be filtered as well.

Examples of using a Filter are described in :ref:`interfaces_stream_using_filter`.

Filter objects in C++ are referenced by the following shared pointer typedef:

.. doxygentypedef:: rogue::interfaces::stream::FilterPtr

The class description is shown below:

.. doxygenclass:: rogue::interfaces::stream::Filter
   :members:
