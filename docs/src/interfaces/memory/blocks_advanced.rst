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
