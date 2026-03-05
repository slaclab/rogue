.. _pyrogue_tree_blocks:
.. _interfaces_memory_blocks:

===============
Blocks & Models
===============

In Rogue, a block represents a hardware-accessible byte region and hosts one or
more variables that map into that region. It is the level where Python-facing
values are converted into bytes and where read/write transactions are issued to
hardware.

When variables are added to a device, PyRogue groups compatible variables into
blocks. Grouping is constrained by the minimum access size of the underlying
memory path. For example, if hardware requires 32-bit accesses, variables that
share one 32-bit register are typically placed into the same block.

Blocks also track shadow state (including stale bytes). This allows multiple
variable updates to be staged first, then committed with block transactions.
For larger blocks, sub-range transactions can update only the changed portion
while still allowing full-block bursts when needed.

Most users can rely on automatic block creation. For performance-sensitive
cases, you can pre-allocate blocks or customize block behavior.

See :doc:`/pyrogue_tree/blocks_advanced` for more information about advanced
Block features.

The translation from Python values to packed bytes is controlled by ``Model``
classes. Blocks apply those models during conversion and transaction flow.

How Variables, Models, and Block Methods Tie Together
-----------------------------------------------------

Each ``Variable`` stores model metadata (for example ``UInt``, ``Int``, ``Bool``, ``String``, ``Float``,
``Double``, ``Fixed``, ``Bytes``, ``PyFunc``) and binds to matching conversion methods in ``Block``.
This binding is configured once when the variable is constructed.

At runtime the flow is:

1. A variable API is called (for example ``setUInt()``, ``getString()``, or Python ``_set()``/``_get()``).
2. The variable calls its bound ``Block`` conversion method pair.
3. The conversion method packs/unpacks bits using the variable layout (bit offsets, widths, stride, endianness).
4. A block transaction is executed to write/read hardware (including verify/retry behavior).

Conceptually:

- Conversion methods in ``Block``:
  ``setPyFunc/getPyFunc``, ``setByteArray/getByteArray``, ``setUInt/getUInt``,
  ``setInt/getInt``, ``setBool/getBool``, ``setString/getString``,
  ``setFloat/getFloat``, ``setDouble/getDouble``, ``setFixed/getFixed``.
- Transport methods in ``Block``:
  ``write/read``, ``startTransaction/checkTransaction``.

This separation is important: conversion selects how bytes are interpreted, while transport selects when bytes move
to/from hardware.

PyRogue Block Helper Functions
------------------------------

PyRogue exposes block helper functions that operate on one block or a list of
blocks:

- ``pyrogue.startTransaction(...)``
- ``pyrogue.checkTransaction(...)``
- ``pyrogue.writeBlocks(...)``
- ``pyrogue.verifyBlocks(...)``
- ``pyrogue.readBlocks(...)``
- ``pyrogue.checkBlocks(...)``
- ``pyrogue.writeAndVerifyBlocks(...)``
- ``pyrogue.readAndCheckBlocks(...)``

These helpers are primarily used by variable/device classes to control hardware
IO paths:

- variable ``get``/``set`` operations drive parent device block operations
- device bulk methods enqueue block transactions and later check completion

Most users do not call these helpers directly except when implementing custom
device sequencing or specialized transaction workflows.

The following Models are currently supported in Rogue:

+---------------------------------------------+-----------------------+-------------------+----------------+------------------------------------------------+
| Model                                       | Hardware Type         | Python Type       | Bit Size       | Notes                                          |
+=============================================+=======================+===================+================+================================================+
| :ref:`interfaces_memory_model_uint`         | unsigned integer      | int               | unconstrained  | Little endian                                  |
+---------------------------------------------+-----------------------+-------------------+----------------+------------------------------------------------+
| :ref:`interfaces_memory_model_uintbe`       | unsigned integer      | int               | unconstrained  | Same as UInt but big endian                    |
+---------------------------------------------+-----------------------+-------------------+----------------+------------------------------------------------+
| :ref:`interfaces_memory_model_uintreversed` | unsigned integer      | int               | unconstrained  | Same as UInt but with a reversed bit order.    |
+---------------------------------------------+-----------------------+-------------------+----------------+------------------------------------------------+
| :ref:`interfaces_memory_model_int`          | signed integer        | int               | unconstrained  | Little endian                                  |
+---------------------------------------------+-----------------------+-------------------+----------------+------------------------------------------------+
| :ref:`interfaces_memory_model_intbe`        | signed integer        | int               | unconstrained  | Same as Int but big endian                     |
+---------------------------------------------+-----------------------+-------------------+----------------+------------------------------------------------+
| :ref:`interfaces_memory_model_bool`         | bit                   | bool              | 1-bit          |                                                |
+---------------------------------------------+-----------------------+-------------------+----------------+------------------------------------------------+
| :ref:`interfaces_memory_model_string`       | bytes                 | string            | unconstrained  |                                                |
+---------------------------------------------+-----------------------+-------------------+----------------+------------------------------------------------+
| :ref:`interfaces_memory_model_float`        | 32-bit float          | float             | 32-bits        |                                                |
+---------------------------------------------+-----------------------+-------------------+----------------+------------------------------------------------+
| :ref:`interfaces_memory_model_floatbe`      | 32-bit float          | float             | 32-bits        | Same as float but big endian                   |
+---------------------------------------------+-----------------------+-------------------+----------------+------------------------------------------------+
| :ref:`interfaces_memory_model_double`       | 64-bit float          | float             | 64-bits        |                                                |
+---------------------------------------------+-----------------------+-------------------+----------------+------------------------------------------------+
| :ref:`interfaces_memory_model_doublebe`     | 64-bit float          | float             | 64-bits        | Same as float but big endian                   |
+---------------------------------------------+-----------------------+-------------------+----------------+------------------------------------------------+
| :ref:`interfaces_memory_model_fixed`        | fixed point           | float             | unconstrained  | Not fully functional yet                       |
+---------------------------------------------+-----------------------+-------------------+----------------+------------------------------------------------+

Most of the above types perform Python-to-byte conversions in low-level C++
Block paths for performance. An exception is very wide integer handling
(``UInt``/``Int`` beyond native C++ conversion widths), where Python model
logic is used.

For custom model definitions, model-driven conversion behavior, and block
pre-allocation patterns, see :doc:`/pyrogue_tree/blocks_advanced`.

For model family reference and API entry points, see
:doc:`/pyrogue_tree/model/index` and :doc:`/pyrogue_core/model_types`.
