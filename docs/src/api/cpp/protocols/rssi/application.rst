.. _protocols_rssi_classes_application:

===========
Application
===========

``Application`` is the upper RSSI stream endpoint. It carries payload frames
between user protocol layers and the RSSI controller.


Application objects in C++ are referenced by the following shared pointer typedef:

.. doxygentypedef:: rogue::protocols::rssi::ApplicationPtr

The class description is shown below:

.. doxygenclass:: rogue::protocols::rssi::Application
   :members:
