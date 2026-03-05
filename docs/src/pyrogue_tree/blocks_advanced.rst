.. _pyrogue_tree_blocks_advanced:
.. _interfaces_memory_blocks_advanced:

========================
Advanced Usage Of Blocks
========================

This section describes how Block conversion methods are selected and how they interact with
variable metadata and transactions.

Model-Driven Method Dispatch
----------------------------

``Variable`` does not hardcode a single getter/setter implementation. Instead, it binds function
pointers to specific ``Block`` methods based on the variable model and size constraints.

Typical mapping:

+--------------------+-----------------------------+-------------------------------+----------------------------------------------+
| Model              | C++ path                    | Python path                   | Notes                                        |
+====================+=============================+===============================+==============================================+
| ``Bytes``          | ``set/getByteArray``        | ``set/getByteArrayPy``        | Raw byte semantics.                          |
+--------------------+-----------------------------+-------------------------------+----------------------------------------------+
| ``UInt``           | ``set/getUInt``             | ``set/getUIntPy``             | Uses byte-array/PyFunc fallback when >64-bit |
+--------------------+-----------------------------+-------------------------------+----------------------------------------------+
| ``Int``            | ``set/getInt``              | ``set/getIntPy``              | Uses byte-array/PyFunc fallback when >64-bit |
+--------------------+-----------------------------+-------------------------------+----------------------------------------------+
| ``Bool``           | ``set/getBool``             | ``set/getBoolPy``             | Bit-width usually 1.                         |
+--------------------+-----------------------------+-------------------------------+----------------------------------------------+
| ``String``         | ``set/getString``           | ``set/getStringPy``           | Byte payload interpreted as string.          |
+--------------------+-----------------------------+-------------------------------+----------------------------------------------+
| ``Float``          | ``set/getFloat``            | ``set/getFloatPy``            | 32-bit float conversion.                     |
+--------------------+-----------------------------+-------------------------------+----------------------------------------------+
| ``Double``         | ``set/getDouble``           | ``set/getDoublePy``           | 64-bit float conversion.                     |
+--------------------+-----------------------------+-------------------------------+----------------------------------------------+
| ``Fixed``          | ``set/getFixed``            | ``set/getFixedPy``            | Uses binary-point metadata.                  |
+--------------------+-----------------------------+-------------------------------+----------------------------------------------+
| ``PyFunc``         | (Python-focused)            | ``set/getPyFunc``             | Delegates conversion to model hooks.         |
+--------------------+-----------------------------+-------------------------------+----------------------------------------------+

Conversion vs Transaction
-------------------------

The Block API has two layers:

- Conversion layer:
  ``set*/get*`` methods convert between native types and staged block bytes.
- Transaction layer:
  ``write/read/startTransaction/checkTransaction`` moves staged bytes to and from hardware.

In the C++ ``Variable`` API, a typed set call performs both steps:

1. Conversion into staged bytes via bound ``Block`` method.
2. ``Block::write()`` (write + verify/check sequence).

A typed get call similarly performs:

1. ``Block::read()``.
2. Conversion from staged bytes via bound ``Block`` method.

Packing Rules and Variable Layout
---------------------------------

The internal ``setBytes``/``getBytes`` helpers are used by all typed methods and apply variable
layout metadata:

- Bit offsets and bit sizes (including disjoint fields)
- List semantics (``numValues``, ``valueStride``)
- Fast contiguous byte-copy optimization when possible
- Byte reversal and bit-order constraints

Because every typed method funnels through these helpers, custom subclasses can extend behavior
while preserving the same packing model.

Custom Models (Complete Example)
--------------------------------

Custom models are a good fit when built-in model classes do not match the
desired encoding/decoding behavior.

The example below defines a complete ``MyUInt`` custom model and then uses it
in a ``RemoteVariable``.

.. code-block:: python

   import pyrogue as pr
   import rogue.interfaces.memory as rim

   class MyUInt(pr.Model):
       ptype = int
       defaultdisp = '{:#x}'
       modelId = rim.PyFunc

       def __init__(self, bitsize):
           super().__init__(bitsize)

       def toBytes(self, value):
           return int(value).to_bytes(pr.byteCount(self.bitSize), 'little', signed=False)

       def fromBytes(self, ba):
           return int.from_bytes(ba, 'little', signed=False)

       def fromString(self, string):
           return int(string, 0)

       def minValue(self):
           return 0

       def maxValue(self):
           return (1 << self.bitSize) - 1

   class MyDevice(pr.Device):
       def __init__(self, **kwargs):
           super().__init__(**kwargs)
           self.add(pr.RemoteVariable(
               name='MyRegister',
               description='Register with custom model',
               offset=0x1000,
               bitSize=32,
               bitOffset=0,
               base=MyUInt,
               mode='RW',
           ))

``RemoteVariable(base=MyUInt, ...)`` binds this model to block conversion for
that variable.

Pre-Allocating Blocks
---------------------

When you need a specific transaction grouping, pre-create a block and then add
variables that overlap that address range.

.. code-block:: python

   import pyrogue as pr
   import rogue.interfaces.memory as rim

   class MyDevice(pr.Device):
       def __init__(self, **kwargs):
           super().__init__(**kwargs)

           # Pre-allocate a 128-byte block at offset 0x1000.
           self.addCustomBlock(rim.Block(0x1000, 128))

           self.add(pr.RemoteVariable(
               name='MyRegister',
               offset=0x1000,
               bitSize=32,
               bitOffset=0,
               base=pr.UInt,
               mode='RW',
           ))

This can improve throughput for use cases that benefit from larger grouped
transactions.

For C++ Block API details, see :doc:`/api/cpp/interfaces/memory/block`.
