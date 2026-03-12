.. _interfaces_stream_using_rate_drop:
.. _stream_interface_using_rate_drop:

===========================
Rate Limiting With RateDrop
===========================

A :ref:`interfaces_stream_rate_drop` object limits how often ``Frame`` objects
are forwarded to downstream consumers.

You typically add a ``RateDrop`` when a downstream ``Slave`` cannot keep up with
the full incoming rate but still benefits from seeing a representative subset of
traffic. Common examples include live monitoring, file capture of diagnostic
samples, or GUI update paths that should not consume every ``Frame`` produced by
the main stream.

At a high level, ``RateDrop`` supports two operating modes:

- time mode, where forwarded ``Frame`` objects are separated by at least a
  configured time interval
- count mode, where roughly one ``Frame`` is kept and then a configured number
  of following ``Frame`` objects are dropped

Constructor
===========

- Python: ``ris.RateDrop(period, value)``
- C++: ``ris::RateDrop::create(period, value)``

Rate Drop Behavior
==================

The meaning of ``value`` depends on the ``period`` flag:

- ``period=True``:
  ``value`` is interpreted as seconds between forwarded ``Frame`` objects.
  For example, ``value=0.1`` forwards at about 10 Hz.
- ``period=False``:
  ``value`` is interpreted as a drop-count setting. One ``Frame`` is forwarded,
  then roughly ``value`` ``Frame`` objects are suppressed before forwarding the
  next one.
- ``value=0`` in count mode effectively disables dropping.

Time mode is usually the better choice for live displays and diagnostics,
because it produces a more predictable output rate. Count mode is useful when
the source rate is already stable and the goal is simply to thin the stream.

Python Time Mode Example
========================

The most common use is to limit a monitoring or logging path to a fixed
approximate rate.

.. code-block:: python

   import rogue.interfaces.stream as ris

   # Data source
   src = MyCustomMaster()

   # Data destination
   dst = MyCustomSlave()

   # Keep at most one Frame every 0.01 seconds, about 100 Hz
   rate = ris.RateDrop(True, 0.01)

   # Connect the RateDrop object between the source and the destination
   src >> rate >> dst

C++ Time Mode Example
=====================

.. code-block:: cpp

   #include "rogue/Helpers.h"
   #include "rogue/interfaces/stream/RateDrop.h"
   #include "MyCustomMaster.h"
   #include "MyCustomSlave.h"

   int main() {
      // Data source
      auto src = MyCustomMaster::create();

      // Data destination
      auto dst = MyCustomSlave::create();

      // Keep at most one Frame every 0.01 seconds, about 100 Hz
      auto rate = rogue::interfaces::stream::RateDrop::create(true, 0.01);

      // Connect the RateDrop object between the source and the destination
      rogueStreamConnect(src, rate);
      rogueStreamConnect(rate, dst);
      return 0;
   }

Python Count Mode Example
=========================

Count mode is useful when the source rate is steady and you want to keep only a
sparse subset of the traffic.

.. code-block:: python

   import rogue.interfaces.stream as ris

   # Data source
   src = MyCustomMaster()

   # Data destination
   dst = MyCustomSlave()

   # Forward one Frame, then drop about ten
   sparse = ris.RateDrop(False, 10)

   src >> sparse >> dst

Logging
=======

``RateDrop`` uses Rogue C++ logging with the static logger name
``pyrogue.stream.RateDrop``.

If you want implementation messages from the object itself, enable that logger
before constructing the ``RateDrop``:

.. code-block:: python

   import rogue
   import rogue.interfaces.stream as ris

   rogue.Logging.setFilter('pyrogue.stream.RateDrop', rogue.Logging.Debug)
   rate = ris.RateDrop(True, 0.1)

``RateDrop`` does not expose a separate runtime ``setDebug(...)`` helper. If
you want to inspect the thinned stream payload, attach a debug ``Slave``
downstream and enable ``setDebug(maxBytes, name)`` there.

What To Explore Next
====================

- Connection topology rules: :doc:`/stream_interface/connecting`
- ``Fifo`` usage: :doc:`/stream_interface/fifo`
- ``Filter`` usage: :doc:`/stream_interface/filter`
- Receive-side monitoring patterns: :doc:`/stream_interface/receiving`

Related Topics
==============

- File writer integration: :doc:`/built_in_modules/utilities/fileio/writing`

API Reference
=============

- Python:

  - :doc:`/api/python/rogue/interfaces/stream/ratedrop`

- C++:

  - :doc:`/api/cpp/interfaces/stream/rateDrop`
