.. _memory_interface_model_types:

==================
Memory Model Types
==================

Rogue model types define how bits and bytes in a block map to Python-facing
values.

Most PyRogue users select a model via ``base=...`` in ``RemoteVariable`` and do
not directly interact with low-level memory model internals.

For broader context, see:

- :doc:`/memory_interface/overview`
- :doc:`/pyrogue_tree/blocks`

Common model families
=====================

- Integer: ``UInt``, ``UIntBE``, ``UIntReversed``, ``Int``, ``IntBE``
- Boolean: ``Bool``
- Text: ``String``
- Floating point: ``Float``, ``FloatBE``, ``Double``, ``DoubleBE``
- Fixed point: ``Fixed``, ``UFixed``

API reference entry points
==========================

- :doc:`/api/python/model`
- :doc:`/api/python/uint`
- :doc:`/api/python/int`
- :doc:`/api/python/bool`
- :doc:`/api/python/string`
- :doc:`/api/python/float`
- :doc:`/api/python/double`
- :doc:`/api/python/fixed`
- :doc:`/api/python/ufixed`
