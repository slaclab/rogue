.. _pyrogue_tree_node_variable_remote_variable:

==============
RemoteVariable
==============

:py:class:`~pyrogue.RemoteVariable` maps a ``Variable`` onto
hardware-accessible memory. In most PyRogue applications, this means a
register or bit field in an FPGA or in a device reachable through the Rogue
memory path. It is the standard choice for register-style control and
monitoring.

When To Use RemoteVariable
==========================

Use ``RemoteVariable`` when the tree value should correspond to a specific
memory-mapped hardware location.

That usually means:

* Configuration registers
* Status registers
* Counters, flags, masks, and control fields
* Wide logical values assembled from more than one register location

Unlike ``LocalVariable``, a ``RemoteVariable`` participates in the hardware
transaction path. Reads and writes flow through the parent ``Device``, the
``Block`` structure built during attachment, and the underlying memory
interface.

What You Usually Set
====================

Most ``RemoteVariable`` definitions combine the shared Variable parameters from
:doc:`/pyrogue_tree/core/variable` with a small set of hardware-mapping
parameters:

* ``offset`` for the memory location.
* ``bitSize`` and ``bitOffset`` for the field layout.
* ``base`` for the typed interpretation of the data.
* ``verify`` when write-back verification policy matters.
* ``overlapEn`` when multiple Variables share one register word.
* ``numValues``, ``valueBits``, and ``valueStride`` for arrays or tables.
* ``bulkOpEn`` when large Variables need different transaction behavior.

Memory Mapping Parameters
=========================

A ``RemoteVariable`` is defined by memory-mapping parameters such as:

* ``offset``
* ``bitSize``
* ``bitOffset``
* Optional ``base``/type Model and packing parameters

These define where the value exists in the hardware address space and how its
bits should be interpreted. The ``base`` Model tells PyRogue whether the value
should behave like an unsigned integer, signed integer, boolean, floating
point quantity, byte array, and so on.

At the tree level, this means a ``RemoteVariable`` gives users a typed,
formatted value-oriented interface while PyRogue handles the lower-level
details of byte packing, block grouping, and memory transactions underneath.

``offset``, ``bitSize``, and ``bitOffset`` can each be either a single value or
lists. List form is used when one logical Variable is split across multiple
register locations.

If the value uses a fixed-point interpretation such as ``base=pr.Fixed(...)``
or ``base=pr.UFixed(...)``, see :doc:`/pyrogue_tree/core/fixed_point_models`
for the scaling and display model behind those types.

Behavior And Transaction Options
================================

``verify``
----------

``verify`` enables write verification for the Variable. It is useful for
registers where write confirmation matters, but it can add noticeable traffic
for large arrays or heavy configuration sequences.

``overlapEn``
-------------

Use ``overlapEn=True`` when this Variable intentionally shares memory space
with another Variable.

``numValues``, ``valueBits``, And ``valueStride``
-------------------------------------------------

These parameters turn the Variable into an array-like view over a packed block
of register-backed values.

``bulkOpEn``
------------

``bulkOpEn`` controls whether the Variable participates in bulk block
operations.

How RemoteVariable Fits The Tree
================================

``RemoteVariable`` is where the ``Variable`` and ``Device`` narratives meet:

* ``Variable`` provides the user-facing typed value interface
* ``Device`` provides the write/verify/read/check transaction model
* ``Block`` groups one or more compatible RemoteVariables into efficient
  transaction units

So when a user calls ``get(read=True)`` or ``set(write=True)``, the actual
hardware activity still runs through the parent ``Device`` and its Block
operations.

Examples
========

Most ``RemoteVariable`` definitions in real PyRogue device trees fall into a
small set of patterns:

* A single control or status field in one register word
* An enumerated field where raw bit values map to named hardware modes
* A logical value assembled from multiple register locations
* A packed array exposed through ``numValues``, ``valueBits``, and
  ``valueStride``
* Multiple Variables intentionally sharing one register word through
  ``overlapEn=True``

The examples below mirror those patterns.

Single Register Fields
----------------------

This is the most common case: a normal register field with a fixed offset,
bit position, and access mode.

.. code-block:: python

   import pyrogue as pr

   class MyDevice(pr.Device):
       def __init__(self, **kwargs):
           super().__init__(**kwargs)

           self.add(pr.RemoteVariable(
               name='ScratchPad',
               description='Register used to test reads and writes',
               offset=0x00,
               bitSize=32,
               bitOffset=0,
               mode='RW',
               base=pr.UInt,
               disp='{:#08x}',
           ))

           self.add(pr.RemoteVariable(
               name='RxReady',
               description='Polled status bit',
               offset=0x04,
               bitSize=1,
               bitOffset=0,
               mode='RO',
               base=pr.Bool,
               pollInterval=1,
           ))

Enumerated Fields
-----------------

Enum mappings are also common. They let the Variable present hardware-meaningful
state names while still using the underlying integer register field.

.. code-block:: python

   import pyrogue as pr

   class MyDevice(pr.Device):
       def __init__(self, **kwargs):
           super().__init__(**kwargs)

           self.add(pr.RemoteVariable(
               name='RxDataWidth',
               offset=0x10,
               bitOffset=11,
               bitSize=3,
               mode='RW',
               base=pr.UInt,
               enum={
                   2: '16',
                   3: '20',
                   4: '32',
                   5: '40',
                   6: '64',
                   7: '80',
               },
           ))

Split Variables Across Multiple Addresses
-----------------------------------------

Some hardware maps place one logical field across multiple words. In that
case, pass lists for ``offset``, ``bitOffset``, and ``bitSize``.

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

           self.add(pr.RemoteVariable(
               name='RXDFELPMRESET_TIME',
               offset=[0x34, 0x38],
               bitOffset=[15, 0],
               bitSize=[1, 6],
               mode='RW',
               base=pr.UInt,
           ))

Packed Arrays
-------------

When hardware exposes a register table or memory-backed array, use
``numValues``, ``valueBits``, and ``valueStride``. This pattern is common for
tables, coefficient memories, and page/register dumps.

The array below exposes 256 32-bit elements at one base offset.

.. code-block:: python

   import pyrogue as pr

   class TableRegs(pr.Device):
       def __init__(self, **kwargs):
           super().__init__(**kwargs)

           self.add(pr.RemoteVariable(
               name='DataBlock',
               offset=0x0000,
               bitSize=32 * 0x100,
               bitOffset=0,
               numValues=0x100,
               valueBits=32,
               valueStride=32,
               updateNotify=True,
               bulkOpEn=True,
               overlapEn=True,
               verify=True,
               hidden=True,
               base=pr.UInt,
               mode='RW',
               groups=['NoStream', 'NoState', 'NoConfig'],
           ))

For very large arrays, projects often disable per-write verification or bulk
operations to control traffic and latency.

.. code-block:: python

   self.add(pr.RemoteVariable(
       name='PixelData',
       offset=0x4000,
       bitSize=32 * num_cols,
       bitOffset=0,
       numValues=num_cols,
       valueBits=32,
       valueStride=32,
       bulkOpEn=False,
       verify=False,
       hidden=True,
       base=pr.UInt,
       mode='RW',
       groups=['NoStream', 'NoState', 'NoConfig'],
   ))

Overlapping Variables In One Register
-------------------------------------

Sometimes one register word is exposed both as a full-word access point and as
smaller subfields. In that case, each Variable sharing the same address range
must enable ``overlapEn=True``.

.. code-block:: python

   import pyrogue as pr

   class SharedWordRegs(pr.Device):
       def __init__(self, **kwargs):
           super().__init__(**kwargs)

           self.add(pr.RemoteVariable(
               name='ConnectionConfig',
               offset=0x4014,
               base=pr.UIntBE,
               mode='WO',
               overlapEn=True,
           ))

           self.add(pr.RemoteVariable(
               name='ConnectionSpeed',
               offset=0x4014,
               bitSize=16,
               bitOffset=16,
               mode='RO',
               overlapEn=True,
               enum={
                   0x28: 'CXP_1',
                   0x30: 'CXP_2',
                   0x38: 'CXP_3',
                   0x40: 'CXP_5',
                   0x48: 'CXP_6',
                   0x50: 'CXP_10',
                   0x58: 'CXP_12',
               },
               base=pr.UIntBE,
           ))

Wide Values Across Many Registers
---------------------------------

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

           self.add(pr.RemoteVariable(
               name='ES_QUALIFIER',
               offset=[0xB0, 0xB4, 0xB8, 0xBC, 0xC0],
               bitOffset=[0, 0, 0, 0, 0],
               bitSize=[16, 16, 16, 16, 16],
               mode='RO',
               base=pr.UInt,
           ))

           self.add(pr.RemoteVariable(
               name='RX_PRBS_ERR_CNT',
               offset=[0x978, 0x97C],
               bitOffset=[0, 0],
               bitSize=[16, 16],
               mode='RO',
               base=pr.UInt,
           ))

What To Explore Next
====================

* Software-owned Variables: :doc:`/pyrogue_tree/core/local_variable`
* Derived Variables: :doc:`/pyrogue_tree/core/link_variable`
* Block grouping and transaction units: :doc:`/pyrogue_tree/core/block`
* Device transaction sequencing: :doc:`/pyrogue_tree/core/block_operations`

API Reference
=============

See :doc:`/api/python/pyrogue/remotevariable` for generated API details.
