.. _pyrogue_tree_fixed_point_models:

==================
Fixed-Point Models
==================

``Fixed`` and ``UFixed`` are the PyRogue ``Model`` types for fixed-point
values. They are one of the most common sources of confusion because they are
easy to read as "floating-point values stored in hardware." That is not what
they are doing.

The right mental model is:

* Hardware stores an integer bit pattern.
* ``binPoint`` says how many fractional bits that integer represents.
* PyRogue converts between the stored integer and the Python ``float`` you see
  in the Variable API.

So a fixed-point value is really a scaled integer.

What ``bitSize`` And ``binPoint`` Mean
======================================

For ``pr.Fixed(bitSize, binPoint)`` and ``pr.UFixed(bitSize, binPoint)``:

* ``bitSize`` is the total stored width.
* ``binPoint`` is the number of fractional bits.
* The value resolution is ``2^-binPoint``.

If ``binPoint`` is 8, then one integer count in hardware corresponds to
``1 / 256`` in the Python-facing value.

Examples:

* ``pr.Fixed(16, 8)`` means a signed 16-bit integer interpreted with 8
  fractional bits.
* ``pr.UFixed(12, 4)`` means an unsigned 12-bit integer interpreted with 4
  fractional bits.

In both cases, the binary point is not an extra stored bit. It is just the
scaling rule used for conversion.

How Conversion Works
====================

In the current implementation, fixed-point conversion is handled by the lower
level Rogue memory path using ``modelId = rim.Fixed`` together with the
Model's ``bitSize``, ``binPoint``, and signedness. The Python ``Fixed`` and
``UFixed`` classes mainly supply that metadata.

The conversion rule is:

* On write: store ``round(value * 2^binPoint)`` as the underlying integer.
* On read: return ``stored_integer / 2^binPoint``.

For signed ``Fixed``, the stored integer uses two's-complement interpretation.
For ``UFixed``, it is treated as unsigned.

This leads to two practical consequences:

* Values are quantized to steps of ``2^-binPoint``.
* A value that is not exactly representable is rounded to the nearest
  representable fixed-point step on write.

Numeric Range
=============

For a signed ``Fixed(bitSize, binPoint)`` value:

* Minimum representable value:
  ``-2^(bitSize - 1) / 2^binPoint``
* Maximum representable value:
  ``(2^(bitSize - 1) - 1) / 2^binPoint``

For an unsigned ``UFixed(bitSize, binPoint)`` value:

* Minimum representable value:
  ``0``
* Maximum representable value:
  ``(2^bitSize - 1) / 2^binPoint``

Examples:

* ``pr.Fixed(16, 8)`` has resolution ``1/256`` and range
  ``-128.0`` to ``127.99609375``.
* ``pr.UFixed(12, 4)`` has resolution ``1/16`` and range
  ``0.0`` to ``255.9375``.

One detail that often surprises users is that the positive maximum is usually
slightly smaller in magnitude than the negative minimum for signed fixed-point
types. That is normal two's-complement behavior.

Worked Example
==============

.. code-block:: python

   import pyrogue as pr

   class DspRegs(pr.Device):
       def __init__(self, **kwargs):
           super().__init__(**kwargs)

           self.add(pr.RemoteVariable(
               name='Gain',
               description='Signed gain coefficient in Q1.15 format',
               offset=0x00,
               bitSize=16,
               bitOffset=0,
               mode='RW',
               base=pr.Fixed(16, 15),
               disp='{:.6f}',
           ))

Here ``Gain`` is a signed 16-bit fixed-point value with 15 fractional bits.
That format is often called ``Q1.15``.

Interpretation examples:

* Python value ``0.5`` writes the integer ``16384`` because
  ``0.5 * 2^15 = 16384``.
* Python value ``-0.25`` writes the two's-complement integer representing
  ``-8192``.
* A raw stored integer value of ``24576`` reads back as ``0.75`` because
  ``24576 / 2^15 = 0.75``.

For coefficient-style registers, this is usually the easiest way to reason
about the model: first think about the scaled integer in hardware, then divide
or multiply by ``2^binPoint``.

Common Mistakes
===============

The mistakes users make most often are:

* Treating ``bitSize`` as "integer bits" instead of total bits.
* Treating ``binPoint`` as an extra stored field rather than a scaling rule.
* Expecting arbitrary decimal values to round-trip exactly.
* Forgetting that signed ``Fixed`` uses two's-complement range and therefore
  has an asymmetric positive and negative limit.
* Forgetting to set an explicit ``disp`` when operator-facing decimal
  formatting matters.

In practice, if you know the hardware format name, such as ``Q1.15`` or
``Q5.11``, convert it like this:

* Total width is ``bitSize``.
* Fractional width is ``binPoint``.
* Use ``Fixed`` for signed formats and ``UFixed`` for unsigned formats.

If the register documentation instead gives a scale factor directly, choose
``binPoint`` so that the scale factor is ``1 / 2^binPoint``.

What To Explore Next
====================

* General Model behavior: :doc:`/pyrogue_tree/core/model`
* Variable definitions that use Models: :doc:`/pyrogue_tree/core/remote_variable`

API Reference
=============

* Python Model base/reference: :doc:`/api/python/pyrogue/model`
* C++ memory Model reference: :doc:`/api/cpp/interfaces/memory/model`
