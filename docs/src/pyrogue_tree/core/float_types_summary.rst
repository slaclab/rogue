.. _pyrogue_tree_float_types_summary:

=============================
Floating Point Types Summary
=============================

This page consolidates all GPU-oriented floating point types supported by Rogue
into a single quick-reference. These types cover the precision formats used by
modern NVIDIA GPU architectures (Ampere, Hopper, Blackwell) and are available as
``Model`` classes for use with ``RemoteVariable``.

For general Model concepts, encoding/decoding behavior, and custom Model
authoring, see :doc:`/pyrogue_tree/core/model`.

Format Details
==============

+----------------+----------------+------+----------+----------+------------+---------+------------------+--------------------+
| Type           | Format         | Sign | Exponent | Mantissa | Total Bits | Storage | Value Range      | Model Class        |
+================+================+======+==========+==========+============+=========+==================+====================+
| Float4         | E2M1           | 1    | 2        | 1        | 4          | 1 byte  | +/-6.0           | ``Float4``         |
+----------------+----------------+------+----------+----------+------------+---------+------------------+--------------------+
| Float6         | E3M2           | 1    | 3        | 2        | 6          | 1 byte  | +/-28.0          | ``Float6``         |
+----------------+----------------+------+----------+----------+------------+---------+------------------+--------------------+
| Float8         | E4M3           | 1    | 4        | 3        | 8          | 1 byte  | +/-448.0         | ``Float8``         |
+----------------+----------------+------+----------+----------+------------+---------+------------------+--------------------+
| Float16        | IEEE 754       | 1    | 5        | 10       | 16         | 2 bytes | +/-65504.0       | ``Float16``        |
+----------------+----------------+------+----------+----------+------------+---------+------------------+--------------------+
| BFloat16       | Brain Float 16 | 1    | 8        | 7        | 16         | 2 bytes | +/-3.39e38       | ``BFloat16``       |
+----------------+----------------+------+----------+----------+------------+---------+------------------+--------------------+
| TensorFloat32  | NVIDIA TF32    | 1    | 8        | 10       | 19         | 4 bytes | +/-3.40e38       | ``TensorFloat32``  |
+----------------+----------------+------+----------+----------+------------+---------+------------------+--------------------+

.. note::

   Each type also has a big-endian variant (e.g., ``Float4BE``, ``Float6BE``,
   ``Float8BE``, ``Float16BE``, ``FloatBE``, ``BFloat16BE``, ``TensorFloat32BE``) for
   registers with big-endian byte order.

Special Value Handling
======================

+-----------------+--------------------------------------------------+-------------------------------------+------------+
| Type            | NaN                                              | Infinity                            | Subnormals |
+=================+==================================================+=====================================+============+
| Float4          | Clamps to max finite                             | No infinity                         | Yes        |
+-----------------+--------------------------------------------------+-------------------------------------+------------+
| Float6          | Clamps to max finite                             | No infinity                         | Yes        |
+-----------------+--------------------------------------------------+-------------------------------------+------------+
| Float8          | 0x7F                                             | No infinity (clamps to max finite)  | Yes        |
+-----------------+--------------------------------------------------+-------------------------------------+------------+
| Float16         | IEEE 754                                         | IEEE 754                            | Yes        |
+-----------------+--------------------------------------------------+-------------------------------------+------------+
| BFloat16        | IEEE 754                                         | IEEE 754                            | Yes        |
+-----------------+--------------------------------------------------+-------------------------------------+------------+
| TensorFloat32   | IEEE 754 (lower 13 mantissa bits zeroed)         | IEEE 754                            | Yes        |
+-----------------+--------------------------------------------------+-------------------------------------+------------+

NVIDIA Architecture Support
===========================

+-----------------+---------------+---------------+------------------+
| Type            | Ampere (A100) | Hopper (H100) | Blackwell (B200) |
+=================+===============+===============+==================+
| Float4 (E2M1)  | --            | --            | Yes              |
+-----------------+---------------+---------------+------------------+
| Float6 (E3M2)  | --            | --            | Yes              |
+-----------------+---------------+---------------+------------------+
| Float8 (E4M3)  | --            | Yes           | Yes              |
+-----------------+---------------+---------------+------------------+
| Float16         | Yes           | Yes           | Yes              |
+-----------------+---------------+---------------+------------------+
| BFloat16        | Yes           | Yes           | Yes              |
+-----------------+---------------+---------------+------------------+
| TensorFloat32   | Yes           | Yes           | Yes              |
+-----------------+---------------+---------------+------------------+

Usage Example
=============

.. code-block:: python

   import pyrogue as pr

   class GpuRegs(pr.Device):
       def __init__(self, **kwargs):
           super().__init__(**kwargs)
           self.add(pr.RemoteVariable(
               name='ActivationWeight',
               offset=0x100,
               bitSize=8,
               mode='RW',
               base=pr.Float8,
           ))

What To Explore Next
====================

* Model conversion behavior and custom Models: :doc:`/pyrogue_tree/core/model`
* Variable behavior and types: :doc:`/pyrogue_tree/core/variable`
