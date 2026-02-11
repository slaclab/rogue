.. _pyrogue_tree_node_device_memorydevice:

=========================
MemoryDevice Configuration
=========================

``MemoryDevice`` is a lightweight helper descriptor used by some tooling flows
(for example HLS register-interface parsers) to describe direct memory regions
that should be loaded from YAML-style data.

Unlike regular variable-centric devices, this pattern is intended for bulk or
sparse memory writes where values are indexed by address offsets.

The descriptor fields are:

* ``name``
* ``offset``
* ``size``
* ``wordBitSize``
* ``stride``
* ``base``

Example
=======

.. code-block:: python

   # Example conceptual shape:
   # MemoryDeviceName:
   #   256: [0x12, 0x13, 0x14, 0x15]
   #   512: [0x22, 0x23, 0x24, 0x25]

   # With wordBitSize=32 and stride=4 this maps to:
   # 256, 260, 264, 268 and 512, 516, 520, 524.
