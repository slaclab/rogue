.. _pyrogue_tree_blocks:
.. _pyrogue_tree_node_block:
.. _interfaces_memory_blocks:
.. _interfaces_memory_blocks_advanced:

======
Blocks
======

A Block is the transaction unit used by PyRogue memory access. Variables map
bit fields into Block byte ranges, and hardware reads/writes execute at Block
level.

Why Blocks Exist
================

Blocks separate two concerns:

1. value staging and conversion (pack/unpack Variable values into bytes)
2. transport sequencing (initiate/check read/write/verify operations)

This separation lets Variable APIs stay high-level while transaction handling
stays efficient and ordered.

How Variables Connect to Blocks
===============================

When Devices attach to a Root, compatible ``RemoteVariable`` instances are
grouped into Blocks. Grouping follows address/size compatibility and memory
path constraints (for example minimum access width).

For :py:class:`~pyrogue.RemoteVariable`:

* Each Variable defines offset/bit mapping metadata
* During Device attach/build, Device logic groups compatible remote Variables
  into Blocks
* Each Variable gets ``_block`` pointing to the Block that services it
* Transaction methods on Device/Root call Block transactions, not per-Variable
  raw bus operations

For :py:class:`~pyrogue.LocalVariable`:

* Each Variable uses a local software Block (:py:class:`~pyrogue.LocalBlock`)
  for in-memory set/get behavior

Implications of Block grouping:

* Several Variables can share one Block transaction
* Partial updates can target changed sub-ranges
* Grouped Block operations reduce transaction overhead

Access Path (RemoteVariable)
============================

Typical read/write path:

* User/API calls ``set`` or ``get`` on a Variable
* Device/Root APIs initiate Block transactions
* Block reads/writes memory through the Device's memory interface
* Completion/check updates Variable state and notifications

In bulk operations, many Variables can share one Block transaction, improving
access efficiency versus isolated per-Variable transfers.

Block APIs and Transaction Flow
===============================

Conversion vs Transaction
-------------------------

The Block API has two layers:

* Conversion layer:
  ``set*/get*`` methods convert between native types and staged Block bytes.
* Transaction layer:
  ``write/read/startTransaction/checkTransaction`` moves staged bytes to and
  from hardware.

In the C++ ``Variable`` API, a typed set call performs both steps:

1. conversion into staged bytes via a bound ``Block`` method
2. ``Block::write()`` (write + verify/check sequence)

A typed get call similarly performs:

1. ``Block::read()``
2. conversion from staged bytes via a bound ``Block`` method

Typical write path:

1. Variable ``set`` updates staged Block bytes using Model conversion
2. write (and optional verify) transactions are initiated
3. completion is checked

Typical read path:

1. read transactions are initiated
2. completion is checked
3. bytes are decoded back into Variable values

In PyRogue terminology, waiting for operation responses is called ``check``.

Block helper functions
----------------------

PyRogue exposes helper functions used by Variable/Device/Root flow:

* :py:func:`~pyrogue.startTransaction`
* :py:func:`~pyrogue.checkTransaction`
* :py:func:`~pyrogue.writeBlocks`
* :py:func:`~pyrogue.verifyBlocks`
* :py:func:`~pyrogue.readBlocks`
* :py:func:`~pyrogue.checkBlocks`
* :py:func:`~pyrogue.writeAndVerifyBlocks`
* :py:func:`~pyrogue.readAndCheckBlocks`

Most users call these indirectly through ``Device``/``Root`` methods. Direct
use is mainly for custom transaction sequencing.

.. code-block:: python

   # Bulk read all Blocks attached to a Device
   myDevice.readBlocks(recurse=True)
   myDevice.checkBlocks(recurse=True)

   # Write only the Block backing one Variable
   myDevice.writeBlocks(variable=myDevice.MyReg, checkEach=True)

Logging
-------

Each hardware-backed Block creates its own Rogue C++ logger when Variables are
bound into it.

- Logger pattern: ``pyrogue.memory.block.<path>``
- Example: ``pyrogue.memory.block.Root.MyDevice.MyRegister``
- Unified Logging API:
  ``logging.getLogger('pyrogue.memory.block').setLevel(logging.DEBUG)``
- Legacy Logging API:
  ``rogue.Logging.setFilter('pyrogue.memory.block', rogue.Logging.Debug)``

This logger is useful for low-level register-access debugging because it emits
messages during:

- Variable-to-Block binding
- transaction start/check flow
- retry handling
- verify/readback behavior

The logger name is derived from the first Variable path assigned to the Block,
so filtering by the ``pyrogue.memory.block`` prefix is usually the practical
choice.

Packing Rules and Variable Layout
---------------------------------

The internal ``setBytes``/``getBytes`` helpers are used by all typed methods
and apply Variable layout metadata:

* Bit offsets and bit sizes (including disjoint fields)
* List semantics (``numValues``, ``valueStride``)
* Fast contiguous byte-copy optimization when possible
* Byte reversal and bit-order constraints

Because every typed method funnels through these helpers, custom subclasses can
extend behavior while preserving the same packing model.

Models in Block Conversion
==========================

Blocks use ``Model`` definitions to translate between Python-facing value types
and hardware bit/byte representation.

Canonical Model documentation is in :doc:`/pyrogue_tree/core/model`.

Model-driven Block method dispatch
----------------------------------

``Variable`` instances bind to typed ``Block`` conversion methods based on
Model and size constraints.

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
| ``PyFunc``         | (Python-focused)            | ``set/getPyFunc``             | Delegates conversion to Model hooks.         |
+--------------------+-----------------------------+-------------------------------+----------------------------------------------+

Built-in Model Families
-----------------------

The following built-in Models are commonly used with Blocks:

Canonical Model coverage is in :doc:`/pyrogue_tree/core/model`.

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

Most Model conversions run in low-level C++ Block paths for performance. An
important exception is very wide integer handling, where Python Model logic is
used when values exceed native conversion widths.

Implementation Boundary (Python and C++)
========================================

The Block API called from PyRogue maps to the ``rogue.interfaces.memory``
runtime layer.

In practice:

* Python code invokes methods on ``pyrogue.Device`` / ``pyrogue.RemoteVariable``
* These route into Block/Variable objects exposed by
  ``rogue.interfaces.memory``
* Underlying C++ Block/Variable code handles transaction staging,
  read/write/verify behavior, stale tracking, packing/unpacking, and update
  notification triggers

Hub interaction
===============

Blocks are transaction sources; Hubs are transaction routers.

During a transaction, Hub logic:

* Offsets addresses by local Hub/Device base
* Forwards transactions to downstream memory slaves
* Splits transactions into sub-transactions when request size exceeds
  downstream max-access capability

This is why Variable-to-Block transactions continue to work cleanly across
multi-level Device trees with address translation.

Advanced patterns
=================

Custom Models (Complete Example)
--------------------------------

Custom Models are a good fit when built-in Model classes do not match the
desired encoding/decoding behavior.

The example below defines a complete ``MyUInt`` custom Model and then uses it
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
               description='Register with custom Model',
               offset=0x1000,
               bitSize=32,
               bitOffset=0,
               base=MyUInt,
               mode='RW',
           ))

``RemoteVariable(base=MyUInt, ...)`` binds this Model to Block conversion for
that Variable.

Pre-Allocating Blocks
---------------------

When you need a specific transaction grouping, pre-create a Block and then add
Variables that overlap that address range.

.. code-block:: python

   import pyrogue as pr
   import rogue.interfaces.memory as rim

   class GroupedDevice(pr.Device):
       def __init__(self, **kwargs):
           super().__init__(**kwargs)
           # Pre-allocate a 128-byte Block at offset 0x1000.
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

* Model API and utility helpers: :doc:`/pyrogue_tree/core/model`
* Root bulk write/read/check sequencing: :doc:`/pyrogue_tree/core/root`
* C++ Block reference: :doc:`/api/cpp/interfaces/memory/block`
* Python LocalBlock reference: :doc:`/api/python/localblock`
