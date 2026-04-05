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

Models separate three closely related concerns:

1. Hardware representation such as bit width, endianness, and signedness.
2. Python-facing type behavior such as ``int``, ``bool``, ``float``, or ``str``.
3. Conversion logic used by ``Block`` staging and transaction code.

This keeps Variable definitions clear and lets the same conversion behavior be
reused across many registers.

How Variables Select A Model
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

In the current implementation, ``RemoteVariable`` usually receives a Model
class such as ``pr.UInt`` or ``pr.Float`` rather than a pre-built instance.
The Variable constructor then instantiates the Model using the Variable's
effective bit width.

That is why ``base=pr.UInt`` is the normal form. For custom or parameterized
Models such as fixed-point encodings, the ``base`` you pass must still line up
with the Variable's bit layout.

What A Model Defines
====================

A Model is more than a byte-conversion helper. It also defines metadata that
shapes how the Variable behaves in Python and in the generated tree metadata.

Common Model responsibilities include:

* ``pytype`` for the native Python-facing type.
* ``defaultdisp`` for the default display format when the Variable does not
  override ``disp``.
* ``minValue()`` and ``maxValue()`` for default limit behavior.
* ``toBytes()`` and ``fromBytes()`` for raw conversion.
* ``fromString()`` for display-string parsing.
* ``modelId`` for the lower-level Rogue memory-processing path.

This is why Models belong conceptually between :doc:`/pyrogue_tree/core/variable`
and :doc:`/pyrogue_tree/core/block`: Variables present the value-oriented API,
Models define the encoding, and Blocks move the bytes.

Built-In Model Families
=======================

Common built-in Models include:

* Integer: ``UInt``, ``UIntBE``, ``UIntReversed``, ``Int``, ``IntBE``
* Boolean: ``Bool``
* Text: ``String``
* Floating point: ``Float``, ``FloatBE``, ``Float4``, ``Float4BE``, ``Float6``, ``Float6BE``, ``Float8``, ``Float8BE``, ``BFloat16``, ``BFloat16BE``, ``TensorFloat32``, ``TensorFloat32BE``, ``Double``, ``DoubleBE``
* Fixed point: ``Fixed``, ``UFixed``
* Custom Python conversion path: Models that use ``modelId = rim.PyFunc``

Built-In Model Types
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
| Float8                                      | 8-bit E4M3 float      | float             | 8-bits         | NVIDIA FP8 (Hopper, Blackwell). No infinity.   |
+---------------------------------------------+-----------------------+-------------------+----------------+------------------------------------------------+
| Float8BE                                    | 8-bit E4M3 float      | float             | 8-bits         | Big endian                                     |
+---------------------------------------------+-----------------------+-------------------+----------------+------------------------------------------------+
| BFloat16                                    | Brain Float 16        | float             | 16-bits        | 1s/8e/7m, float32 exponent range (~3.39e38). NVIDIA Ampere/Hopper/Blackwell |
+---------------------------------------------+-----------------------+-------------------+----------------+------------------------------------------------+
| BFloat16BE                                  | Brain Float 16        | float             | 16-bits        | Big-endian BFloat16                            |
+---------------------------------------------+-----------------------+-------------------+----------------+------------------------------------------------+
| TensorFloat32                               | NVIDIA TF32           | float             | 32-bits        | 1s/8e/10m, 19 bits in 4 bytes. NVIDIA Ampere/Hopper/Blackwell |
+---------------------------------------------+-----------------------+-------------------+----------------+------------------------------------------------+
| TensorFloat32BE                             | NVIDIA TF32           | float             | 32-bits        | Big-endian TensorFloat32                       |
+---------------------------------------------+-----------------------+-------------------+----------------+------------------------------------------------+
| Float6                                      | 6-bit E3M2 float      | float             | 8-bits         | 1s/3e/2m, no NaN/Inf, max 28.0. NVIDIA Blackwell |
+---------------------------------------------+-----------------------+-------------------+----------------+------------------------------------------------+
| Float6BE                                    | 6-bit E3M2 float      | float             | 8-bits         | Big-endian Float6                              |
+---------------------------------------------+-----------------------+-------------------+----------------+------------------------------------------------+
| Float4                                      | 4-bit E2M1 float      | float             | 8-bits         | 1s/2e/1m, no NaN/Inf, max 6.0. NVIDIA Blackwell |
+---------------------------------------------+-----------------------+-------------------+----------------+------------------------------------------------+
| Float4BE                                    | 4-bit E2M1 float      | float             | 8-bits         | Big-endian Float4                              |
+---------------------------------------------+-----------------------+-------------------+----------------+------------------------------------------------+
| :ref:`interfaces_memory_model_fixed`        | fixed point           | float             | unconstrained  | Fixed-point conversion                         |
+---------------------------------------------+-----------------------+-------------------+----------------+------------------------------------------------+
| :ref:`interfaces_memory_model_ufixed`       | fixed point           | float             | unconstrained  | Unsigned fixed-point conversion                |
+---------------------------------------------+-----------------------+-------------------+----------------+------------------------------------------------+

For low-level Model class reference and constants, see
:doc:`/api/cpp/interfaces/memory/model`.

Fixed-Point Models
==================

``Fixed`` and ``UFixed`` are important enough, and nuanced enough in
practice, that they now have their own focused page:

* :doc:`/pyrogue_tree/core/fixed_point_models`

That page explains the fixed-point mental model, ``bitSize`` and ``binPoint``,
the conversion formulas, numeric range, and a worked example.

Model Utility Helpers
=====================

The Python Model module also includes a few small helpers that are useful when
you need to reason about raw layouts or write a custom Model:

* :py:func:`~pyrogue.wordCount` computes how many words are needed for a bit width.
* :py:func:`~pyrogue.byteCount` computes how many bytes are needed for a bit width.
* :py:func:`~pyrogue.reverseBits` reverses bit significance across a fixed width.
* :py:func:`~pyrogue.twosComplement` interprets a value with two's-complement sign semantics.

These are especially useful in custom conversion code and in documentation
examples where raw register layout matters.

Model Instances And Caching
===========================

One implementation detail is worth knowing when you use Model classes directly:
the ``Model`` metaclass caches instances by constructor arguments.

In practice, repeated requests for the same Model and parameters, such as
``pr.UInt(16)``, return the same shared Model instance. Most users do not need
to think about this because Variables create Models for them, but it explains
why Models are treated more like reusable type descriptors than like
per-Variable mutable state.

Model Conversion Flow In Block Access
=====================================

When a Variable is read or written:

1. Variable logic resolves its Model and layout metadata.
2. Block conversion methods pack or unpack values for that Model.
3. Block transaction methods move bytes to or from hardware.

Model selection answers "how bytes map to values"; Block transactions answer
"when bytes move."

For transaction flow details, see :doc:`/pyrogue_tree/core/block`.

Custom Model Example
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

This is the same overall pattern used by built-in Models: define the Python
type behavior and the byte conversion behavior in one reusable object, then
attach that Model to one or more Variables.

How ``BitReversedUInt`` Differs From Built-In ``UInt``
======================================================

This example shows a register layout where hardware bit order differs from
normal integer interpretation:

* Built-in ``UInt`` assumes standard bit significance ordering.
* ``BitReversedUInt`` reverses bits on write and read so software uses normal
  integer semantics while memory uses reversed bit positions.
* This is useful for custom register layouts where the hardware view is not a
  normal integer bit ordering.

What To Explore Next
====================

* Variable type and access behavior: :doc:`/pyrogue_tree/core/variable`
* Block packing and transaction flow: :doc:`/pyrogue_tree/core/block`
* Fixed-point usage details: :doc:`/pyrogue_tree/core/fixed_point_models`

API Reference
=============

* Python Model base/reference: :doc:`/api/python/pyrogue/model`
* C++ memory Model reference: :doc:`/api/cpp/interfaces/memory/model`
* Model helpers: :doc:`/api/python/pyrogue/wordcount`, :doc:`/api/python/pyrogue/bytecount`,
  :doc:`/api/python/pyrogue/reversebits`, :doc:`/api/python/pyrogue/twoscomplement`
