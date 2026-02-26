.. _protocols_rssi_classes_header:

======
Header
======

.. note::
   Canonical generated C++ API docs are centralized at :ref:`api_reference`.



``Header`` is a helper codec/container for RSSI header fields. It parses frame
bytes into structured fields (`verify()`), and encodes fields back into frame
bytes with updated checksum (`update()`).


