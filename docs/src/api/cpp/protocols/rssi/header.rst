.. _protocols_rssi_classes_header:

======
Header
======

``Header`` is a helper codec/container for RSSI header fields. It parses frame
bytes into structured fields (`verify()`), and encodes fields back into frame
bytes with updated checksum (`update()`).


.. doxygentypedef:: rogue::protocols::rssi::HeaderPtr

.. doxygenclass:: rogue::protocols::rssi::Header
   :members:
