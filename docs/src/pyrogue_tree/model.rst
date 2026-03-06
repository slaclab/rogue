.. _pyrogue_tree_model:

=====
Model
=====

Models define how values are encoded to bytes and decoded back to Python types.
In practice, a model is selected per variable (usually with ``base=...`` on
``RemoteVariable``), and block transactions apply that model during read/write.

=========
Model API
=========

PyRogue models define how variable values are represented, converted to/from
bytes, and interpreted for display/type behavior.

Most users interact with models indirectly through variable ``base`` and related
type configuration. Advanced users can use model classes directly for custom
encoding/decoding workflows.

Why models exist
================

Models separate three concerns:

1. hardware representation (bits/bytes, endianness, signedness)
2. Python-facing type and formatting behavior
3. conversion logic used during block access

This keeps variable definitions clear and lets the same conversion behavior be
reused across many registers.

Built-in model families
=======================

Common built-in models include:

* integer: ``UInt``, ``UIntBE``, ``UIntReversed``, ``Int``, ``IntBE``
* boolean: ``Bool``
* text/bytes: ``String``, ``Bytes``
* floating point: ``Float``, ``FloatBE``, ``Double``, ``DoubleBE``
* fixed point: ``Fixed``, ``UFixed``
* custom conversion hook: ``PyFunc``

Built-in model types
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

For low-level model class reference and constants, see
:doc:`/api/cpp/interfaces/memory/model`.

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
               base=pr.UInt,   # model selection
           ))

Model conversion flow
=====================

When a variable is read or written:

1. variable logic resolves its model and layout metadata
2. block conversion methods pack/unpack values for that model
3. block transaction methods move bytes to/from hardware

Model selection answers "how bytes map to values"; block transactions answer
"when bytes move."

For transaction flow details, see :doc:`/pyrogue_tree/blocks`.

Custom model example
====================

Use a custom model when built-ins do not match an encoding format.

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
               offset=0x1000,
               bitSize=32,
               bitOffset=0,
               mode='RW',
               base=MyUInt,
           ))

Reference links
===============

* Python model base/reference: :doc:`/api/python/model`
* C++ memory model reference: :doc:`/api/cpp/interfaces/memory/model`
* Model helpers: :doc:`/api/python/wordcount`, :doc:`/api/python/bytecount`,
  :doc:`/api/python/reversebits`, :doc:`/api/python/twoscomplement`

Where to explore next
=====================

* Block transaction and grouping behavior: :doc:`/pyrogue_tree/blocks`
* Variable usage patterns: :doc:`/pyrogue_tree/node/variable/index`
