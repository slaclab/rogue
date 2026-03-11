.. _pyrogue_tree_node_variable_remote_variable:

==============
RemoteVariable
==============

:py:class:`~pyrogue.RemoteVariable` maps a Variable to hardware-accessible memory.
For example, a register in an attached FPGA
It is the standard choice for register-style control and monitoring.

Behavior
========

A RemoteVariable is defined by register mapping metadata such as:

* ``offset``
* ``bitSize``
* ``bitOffset``
* Optional ``base``/type Model and packing parameters

These define where the register exists in the hardware address space, and what type of value it is e.g. unsigned integer, floating point, etc.

Read/write calls trigger Block transactions through the Device/Root transaction
pipeline.

``offset``, ``bitSize``, and ``bitOffset`` can each be either a single value or
lists. List form is used when one logical Variable is split across multiple
register locations.

Examples
========

Single Register Field
---------------------
The following example defines a control register with a single 8-bit unsigned
integer field at address offset ``0x00``.

.. code-block:: python

   import pyrogue as pr

   class MyDevice(pr.Device):
       def __init__(self, **kwargs):
           super().__init__(**kwargs)

           self.add(pr.RemoteVariable(
               name='Control',
               description='Control register field',
               offset=0x00,
               bitSize=8,
               bitOffset=0,
               mode='RW',
               base=pr.UInt,
           ))

Split Variable Across Two Addresses (SURF Style)
------------------------------------------------
The following pattern is used in SURF transceiver maps for fields that span
register boundaries.

In this example, one logical 7-bit field is split across two 32-bit words in
the memory map:

* ``offset=0x34`` contributes bit 15 (1 bit)
* ``offset=0x38`` contributes bits 5:0 (6 bits)

PyRogue combines those segments in list order into one Variable value.

.. code-block:: python

   import pyrogue as pr

   class GtRegs(pr.Device):
       def __init__(self, **kwargs):
           super().__init__(**kwargs)

           # Modeled after surf.xilinx._Gtxe2Channel
           self.add(pr.RemoteVariable(
               name='RXDFELPMRESET_TIME',
               offset=[0x34, 0x38],
               bitOffset=[15, 0],
               bitSize=[1, 6],
               mode='RW',
               base=pr.UInt,
           ))

Wide Vector Spanning Multiple Registers (SURF Style)
----------------------------------------------------
List form also works well for read-only counters or masks split across many
consecutive words.

For ``ES_QUALIFIER``, the logical value is assembled from five 16-bit segments:

* ``offset=0xB0`` -> bits 15:0
* ``offset=0xB4`` -> bits 31:16
* ``offset=0xB8`` -> bits 47:32
* ``offset=0xBC`` -> bits 63:48
* ``offset=0xC0`` -> bits 79:64

For ``RX_PRBS_ERR_CNT``, the logical value is assembled from two 16-bit
segments:

* ``offset=0x978`` -> bits 15:0
* ``offset=0x97C`` -> bits 31:16

.. code-block:: python

   import pyrogue as pr

   class EyeScanRegs(pr.Device):
       def __init__(self, **kwargs):
           super().__init__(**kwargs)

           # Modeled after surf.xilinx._Gtxe2Channel
           self.add(pr.RemoteVariable(
               name='ES_QUALIFIER',
               offset=[0xB0, 0xB4, 0xB8, 0xBC, 0xC0],
               bitOffset=[0, 0, 0, 0, 0],
               bitSize=[16, 16, 16, 16, 16],
               mode='RO',
               base=pr.UInt,
           ))

           # Modeled after surf.xilinx._Gtye4Channel
           self.add(pr.RemoteVariable(
               name='RX_PRBS_ERR_CNT',
               offset=[0x978, 0x97C],
               bitOffset=[0, 0],
               bitSize=[16, 16],
               mode='RO',
               base=pr.UInt,
           ))

API Reference
=============

See :doc:`/api/python/remotevariable` for generated API details.
