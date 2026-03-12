.. _pyrogue_tree_model:

=====
Model
=====

Models define how values are encoded to bytes and decoded back to Python types.
In practice, a Model is selected per Variable (usually with ``base=...`` on
``RemoteVariable``), and Block transactions apply that Model during read/write.

Most users interact with Models indirectly through Variable ``base`` and related
type configuration. Advanced users can use Model classes directly for custom
encoding/decoding workflows.

Why Models Exist
================

Models separate three concerns:

1. Hardware representation (bits/bytes, endianness, signedness)
2. Python-facing type and formatting behavior
3. Conversion logic used during Block access

This keeps Variable definitions clear and lets the same conversion behavior be
reused across many registers.

Model selection in Variables
============================

Most users select a Model when defining each ``RemoteVariable``.

.. code-block:: python

   import pyrogue as pr

   class MyRegs(pr.Device):
       def __init__(self, **kwargs):
           super().__init__(**kwargs)
           self.add(pr.RemoteVariable(
               name='Status',
               offset=0x00,
               bitSize=32,
               mode='RO',
               base=pr.UInt,   # Model selection
           ))

Built-in Model families
=======================

Common built-in Models include:

* Integer: ``UInt``, ``UIntBE``, ``UIntReversed``, ``Int``, ``IntBE``
* Boolean: ``Bool``
* Text/bytes: ``String``, ``Bytes``
* Floating point: ``Float``, ``FloatBE``, ``Double``, ``DoubleBE``
* Fixed point: ``Fixed``, ``UFixed``
* Custom conversion hook: ``PyFunc``

Built-in Model types
====================

+---------------------------------------------+-----------------------+-------------------+----------------+------------------------------------------------+
| Model                                       | Hardware Type         | Python Type       | Bit Size       | Notes                                          |
+=============================================+=======================+===================+================+================================================+
| :ref:`interfaces_memory_model_uint`         | unsigned integer      | int               | unconstrained  | Little endian                                  |
+---------------------------------------------+-----------------------+-------------------+----------------+------------------------------------------------+
| :ref:`interfaces_memory_model_uintbe`       | unsigned integer      | int               | unconstrained  | Big endian                                     |
+---------------------------------------------+-----------------------+-------------------+----------------+------------------------------------------------+
| :ref:`interfaces_memory_model_uintreversed` | unsigned integer      | int               | unconstrained  | Reversed bit order                             |
+---------------------------------------------+-----------------------+-------------------+----------------+------------------------------------------------+
| :ref:`interfaces_memory_model_int`          | signed integer        | int               | unconstrained  | Little endian                                  |
+---------------------------------------------+-----------------------+-------------------+----------------+------------------------------------------------+
| :ref:`interfaces_memory_model_intbe`        | signed integer        | int               | unconstrained  | Big endian                                     |
+---------------------------------------------+-----------------------+-------------------+----------------+------------------------------------------------+
| :ref:`interfaces_memory_model_bool`         | bit                   | bool              | 1-bit          |                                                |
+---------------------------------------------+-----------------------+-------------------+----------------+------------------------------------------------+
| :ref:`interfaces_memory_model_string`       | bytes                 | string            | unconstrained  |                                                |
+---------------------------------------------+-----------------------+-------------------+----------------+------------------------------------------------+
| :ref:`interfaces_memory_model_float`        | 32-bit float          | float             | 32-bits        |                                                |
+---------------------------------------------+-----------------------+-------------------+----------------+------------------------------------------------+
| :ref:`interfaces_memory_model_floatbe`      | 32-bit float          | float             | 32-bits        | Big endian                                     |
+---------------------------------------------+-----------------------+-------------------+----------------+------------------------------------------------+
| :ref:`interfaces_memory_model_double`       | 64-bit float          | float             | 64-bits        |                                                |
+---------------------------------------------+-----------------------+-------------------+----------------+------------------------------------------------+
| :ref:`interfaces_memory_model_doublebe`     | 64-bit float          | float             | 64-bits        | Big endian                                     |
+---------------------------------------------+-----------------------+-------------------+----------------+------------------------------------------------+
| :ref:`interfaces_memory_model_fixed`        | fixed point           | float             | unconstrained  | Fixed-point conversion                         |
+---------------------------------------------+-----------------------+-------------------+----------------+------------------------------------------------+
| :ref:`interfaces_memory_model_ufixed`       | fixed point           | float             | unconstrained  | Unsigned fixed-point conversion                |
+---------------------------------------------+-----------------------+-------------------+----------------+------------------------------------------------+

For low-level Model class reference and constants, see
:doc:`/api/cpp/interfaces/memory/model`.

Model conversion flow in Block access
=====================================

When a Variable is read or written:

1. Variable logic resolves its Model and layout metadata
2. Block conversion methods pack/unpack values for that Model
3. Block transaction methods move bytes to/from hardware

Model selection answers "how bytes map to values"; Block transactions answer
"when bytes move."

For transaction flow details, see :doc:`/pyrogue_tree/core/block`.

Custom Model example
====================

Use a custom Model when built-ins do not match an encoding format.

.. code-block:: python

   import pyrogue as pr
   import rogue.interfaces.memory as rim

   class BitReversedUInt(pr.Model):
       pytype = int
       defaultdisp = '{:#x}'
       modelId = rim.PyFunc

       def __init__(self, bitsize):
           super().__init__(bitsize)

       def toBytes(self, value):
           # Reverse bit order so MSB appears at bit position 0 in memory.
           raw_normal = int(value)
           raw_reversed = pr.reverseBits(raw_normal, self.bitSize)
           return raw_reversed.to_bytes(pr.byteCount(self.bitSize), 'little', signed=False)

       def fromBytes(self, ba):
           raw_reversed = int.from_bytes(ba, 'little', signed=False)
           return pr.reverseBits(raw_reversed, self.bitSize)

       def fromString(self, string):
           return int(string, 0)

       def minValue(self):
           return 0

       def maxValue(self):
           return (2 ** self.bitSize) - 1

   class MyDevice(pr.Device):
       def __init__(self, **kwargs):
           super().__init__(**kwargs)
           self.add(pr.RemoteVariable(
               name='AsicStatus',
               offset=0x1000,
               bitSize=16,
               bitOffset=0,
               mode='RW',
               base=BitReversedUInt,
           ))

How ``BitReversedUInt`` differs from built-in ``UInt``
=======================================================

This example shows a register layout where hardware bit order differs from
normal integer interpretation:

* Built-in ``UInt`` assumes standard bit significance ordering
* ``BitReversedUInt`` reverses bits on write/read so software uses normal
  integer semantics while memory uses reversed bit positions
* This is useful for some custom ASIC or I2C peripheral register definitions

For examples of built-in and custom Model definitions, see
``python/pyrogue/_Model.py``.

Reference links
===============

* Python Model base/reference: :doc:`/api/python/pyrogue/model`
* C++ memory Model reference: :doc:`/api/cpp/interfaces/memory/model`
* Model helpers: :doc:`/api/python/pyrogue/wordcount`, :doc:`/api/python/pyrogue/bytecount`,
  :doc:`/api/python/pyrogue/reversebits`, :doc:`/api/python/pyrogue/twoscomplement`

Where to explore next
=====================

* Block transaction and grouping behavior: :doc:`/pyrogue_tree/core/block`
* Variable usage patterns: :doc:`/pyrogue_tree/core/variable`
