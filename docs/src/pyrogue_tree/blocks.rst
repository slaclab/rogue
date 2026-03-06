.. _pyrogue_tree_blocks:
.. _pyrogue_tree_node_block:
.. _interfaces_memory_blocks:
.. _interfaces_memory_blocks_advanced:

===============
Blocks & Models
===============

A block is the transaction unit used by PyRogue memory access. Variables map
bit fields into block byte ranges, and hardware reads/writes execute at block
level.

What a block does
=================

Each block combines two roles:

1. value staging and conversion (pack/unpack variable values into bytes)
2. transaction transport (enqueue/check read/write/verify operations)

This separation is important:

* model selection defines how bytes represent values
* block APIs define when bytes move to and from hardware

Conversion vs Transaction
=========================

The Block API has two layers:

* Conversion layer:
  ``set*/get*`` methods convert between native types and staged block bytes.
* Transaction layer:
  ``write/read/startTransaction/checkTransaction`` moves staged bytes to and
  from hardware.

In the C++ ``Variable`` API, a typed set call performs both steps:

1. conversion into staged bytes via a bound ``Block`` method
2. ``Block::write()`` (write + verify/check sequence)

A typed get call similarly performs:

1. ``Block::read()``
2. conversion from staged bytes via a bound ``Block`` method

Packing Rules and Variable Layout
=================================

The internal ``setBytes``/``getBytes`` helpers are used by all typed methods
and apply variable layout metadata:

* bit offsets and bit sizes (including disjoint fields)
* list semantics (``numValues``, ``valueStride``)
* fast contiguous byte-copy optimization when possible
* byte reversal and bit-order constraints

Because every typed method funnels through these helpers, custom subclasses can
extend behavior while preserving the same packing model.

How variables map into blocks
=============================

When devices attach to a root, compatible ``RemoteVariable`` instances are
grouped into blocks. Grouping follows address/size compatibility and memory
path constraints (for example minimum access width).

Implications:

* several variables can share one block transaction
* partial updates can target changed sub-ranges
* grouped block operations reduce transaction overhead

``LocalVariable`` is not hardware-backed and uses ``LocalBlock`` behavior.

How Variables Use Blocks
========================

For :py:class:`pyrogue.RemoteVariable`:

* each variable defines offset/bit mapping metadata
* during device attach/build, device logic groups compatible remote variables
  into blocks
* each variable gets ``_block`` pointing to the block that services it
* transaction methods on Device/Root call block transactions, not per-variable
  raw bus operations

For :py:class:`pyrogue.LocalVariable`:

* each variable uses a local software block (:py:class:`pyrogue.LocalBlock`)
  for in-memory set/get behavior

Access Path (RemoteVariable)
============================

Typical read/write path:

* user/API calls ``set`` or ``get`` on a variable
* Device/Root APIs enqueue block transactions
* block reads/writes memory through the device's memory interface
* completion/check updates variable state and notifications

In bulk operations, many variables can share one block transaction, improving
access efficiency versus isolated per-variable transfers.

Transaction flow
================

Typical write path:

1. variable ``set`` updates staged block bytes using model conversion
2. write (and optional verify) transactions are enqueued
3. completion is checked

Typical read path:

1. read transactions are enqueued
2. completion is checked
3. bytes are decoded back into variable values

In PyRogue terminology, waiting for operation responses is called ``check``.

PyRogue block helper functions
==============================

PyRogue exposes helper functions used by variable/device/root flow:

* :py:func:`pyrogue.startTransaction`
* :py:func:`pyrogue.checkTransaction`
* :py:func:`pyrogue.writeBlocks`
* :py:func:`pyrogue.verifyBlocks`
* :py:func:`pyrogue.readBlocks`
* :py:func:`pyrogue.checkBlocks`
* :py:func:`pyrogue.writeAndVerifyBlocks`
* :py:func:`pyrogue.readAndCheckBlocks`

Most users call these indirectly through ``Device``/``Root`` methods. Direct
use is mainly for custom transaction sequencing.

.. code-block:: python

   # Bulk read all blocks attached to a device
   myDevice.readBlocks(recurse=True)
   myDevice.checkBlocks(recurse=True)

   # Write only the block backing one variable
   myDevice.writeBlocks(variable=myDevice.MyReg, checkEach=True)

Implementation Boundary (Python and C++)
========================================

The block API called from PyRogue maps to the ``rogue.interfaces.memory``
runtime layer.

In practice:

* Python code invokes methods on ``pyrogue.Device`` / ``pyrogue.RemoteVariable``
* these route into block/variable objects exposed by
  ``rogue.interfaces.memory``
* underlying C++ block/variable code handles transaction staging,
  read/write/verify behavior, stale tracking, packing/unpacking, and update
  notification triggers

Hub interaction
===============

Blocks are transaction sources; Hubs are transaction routers.

During a transaction, Hub logic:

* offsets addresses by local hub/device base
* forwards transactions to downstream memory slaves
* splits transactions into sub-transactions when request size exceeds
  downstream max-access capability

This is why variable-to-block transactions continue to work cleanly across
multi-level device trees with address translation.

Model-driven block method dispatch
==================================

``Variable`` instances bind to typed ``Block`` conversion methods based on
model and size constraints.

+--------------------+-----------------------------+-------------------------------+----------------------------------------------+
| Model              | C++ path                    | Python path                   | Notes                                        |
+====================+=============================+===============================+==============================================+
| ``Bytes``          | ``set/getByteArray``        | ``set/getByteArrayPy``        | Raw byte semantics.                          |
+--------------------+-----------------------------+-------------------------------+----------------------------------------------+
| ``UInt``           | ``set/getUInt``             | ``set/getUIntPy``             | Fallback for very wide values.               |
+--------------------+-----------------------------+-------------------------------+----------------------------------------------+
| ``Int``            | ``set/getInt``              | ``set/getIntPy``              | Fallback for very wide values.               |
+--------------------+-----------------------------+-------------------------------+----------------------------------------------+
| ``Bool``           | ``set/getBool``             | ``set/getBoolPy``             | Typically 1-bit value semantics.             |
+--------------------+-----------------------------+-------------------------------+----------------------------------------------+
| ``String``         | ``set/getString``           | ``set/getStringPy``           | Byte payload interpreted as text.            |
+--------------------+-----------------------------+-------------------------------+----------------------------------------------+
| ``Float``          | ``set/getFloat``            | ``set/getFloatPy``            | 32-bit float conversion.                     |
+--------------------+-----------------------------+-------------------------------+----------------------------------------------+
| ``Double``         | ``set/getDouble``           | ``set/getDoublePy``           | 64-bit float conversion.                     |
+--------------------+-----------------------------+-------------------------------+----------------------------------------------+
| ``Fixed``          | ``set/getFixed``            | ``set/getFixedPy``            | Uses binary-point metadata.                  |
+--------------------+-----------------------------+-------------------------------+----------------------------------------------+
| ``PyFunc``         | (Python-focused)            | ``set/getPyFunc``             | Delegates conversion to model hooks.         |
+--------------------+-----------------------------+-------------------------------+----------------------------------------------+

Built-in model families
=======================

The following built-in model families are commonly used with blocks:
Canonical model coverage is in :doc:`/pyrogue_tree/model`.

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

Most model conversions run in low-level C++ block paths for performance. An
important exception is very wide integer handling, where Python model logic is
used when values exceed native conversion widths.

Advanced patterns
=================

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

   class GroupedDevice(pr.Device):
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

Where to explore next
=====================

* Model API and utility helpers: :doc:`/pyrogue_tree/model`
* Root bulk write/read/check sequencing: :doc:`/pyrogue_tree/node/root/index`
* C++ block reference: :doc:`/api/cpp/interfaces/memory/block`
* Python LocalBlock reference: :doc:`/api/python/localblock`
