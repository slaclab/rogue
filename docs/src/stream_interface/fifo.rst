.. _interfaces_stream_using_fifo:
.. _stream_interface_using_fifo:

==============
FIFO Buffering
==============

A :ref:`interfaces_stream_fifo` object inserts an elastic buffer between an
upstream stream stage and a downstream stream stage. In Rogue terms, it sits
between a ``Master`` and one or more downstream ``Slave`` objects and decouples
their timing.

You typically add a ``Fifo`` for one of three reasons. The first is to absorb
bursts or flow-control events so a fast producer does not immediately stall a
slower consumer. The second is to create a deliberate drop point when the
downstream path cannot keep up indefinitely. The third is to add a tap path for
monitoring or logging, where the monitoring branch should not interfere with the
primary processing path.

At a high level, ``Fifo`` behavior is controlled by three constructor
parameters:

- ``maxDepth`` controls how many ``Frame`` objects may be queued before new
  arrivals are dropped.
- ``trimSize`` controls how much payload is copied when copy mode is enabled.
- ``noCopy`` selects whether the original ``Frame`` is queued or whether a new
  copied ``Frame`` is created.

Constructor
===========

- Python: ``ris.Fifo(maxDepth, trimSize, noCopy)``
- C++: ``ris::Fifo::create(maxDepth, trimSize, noCopy)``

Copy And Queue Behavior
=======================

The interaction between ``trimSize`` and ``noCopy`` determines what the ``Fifo``
actually stores.

- ``noCopy=True`` and ``trimSize=0``:
  the original incoming ``Frame`` is queued.
- ``noCopy=False`` and ``trimSize=0``:
  a full copy of the incoming ``Frame`` is queued.
- ``noCopy=False`` and ``trimSize!=0``:
  a copied ``Frame`` containing only up to ``trimSize`` bytes of payload is
  queued.

``maxDepth`` determines whether the queue is bounded. When ``maxDepth=0``, the
queue depth is effectively unlimited and frames are never dropped due to queue
depth. When ``maxDepth!=0``, incoming ``Frame`` objects are dropped once the
queue reaches that depth. Use ``dropCnt()`` to inspect the number of dropped
``Frame`` objects and ``clearCnt()`` to reset the counter.

Python In-Line Example
======================

The simplest use of a ``Fifo`` is to place it directly in-line between a source
and a destination. This is the normal choice when the goal is to absorb bursts
without changing the payload.

.. code-block:: python

   import rogue.interfaces.stream as ris

   # Data source
   src = MyCustomMaster()

   # Data destination
   dst = MyCustomSlave()

   # Create a Fifo with maxDepth=100, trimSize=0, noCopy=True
   fifo = ris.Fifo(100, 0, True)

   # Connect the Fifo between the source and the destination
   src >> fifo >> dst

In this configuration the ``Fifo`` queues the original incoming ``Frame``
objects, up to a depth of 100, and begins dropping newly arrived ``Frame``
objects once that depth is reached.

C++ In-Line Example
===================

.. code-block:: cpp

   #include "rogue/Helpers.h"
   #include "rogue/interfaces/stream/Fifo.h"
   #include "MyCustomMaster.h"
   #include "MyCustomSlave.h"

   int main() {
      // Data source
      auto src = MyCustomMaster::create();

      // Data destination
      auto dst = MyCustomSlave::create();

      // Create a Fifo with maxDepth=100, trimSize=0, noCopy=true
      auto fifo = rogue::interfaces::stream::Fifo::create(100, 0, true);

      // Connect the Fifo between the source and the destination
      rogueStreamConnect(src, fifo);
      rogueStreamConnect(fifo, dst);
      return 0;
   }

Python Tap Example
==================

Another common pattern is to use a copied ``Fifo`` as a secondary monitoring
branch. In that case the primary path continues unchanged, while the tap path
receives copied and optionally trimmed ``Frame`` objects.

.. code-block:: python

   import rogue.interfaces.stream as ris

   # Data source
   src = MyCustomMaster()

   # Main data destination
   dst = MyCustomSlave()

   # Additional monitor
   mon = MyCustomMonitor()

   # Primary path
   src >> dst

   # Tap path: copy at most 20 bytes from each Frame and queue up to 150 Frames
   fifo = ris.Fifo(150, 20, False)
   src >> fifo >> mon

This is useful when the monitor is slower than the main path or only needs a
small prefix of each payload. Because the monitor branch gets copies rather than
the original ``Frame`` objects, it does not interfere with the primary path's
ownership or zero-copy behavior.

C++ Tap Example
===============

.. code-block:: cpp

   #include "rogue/Helpers.h"
   #include "rogue/interfaces/stream/Fifo.h"
   #include "MyCustomMaster.h"
   #include "MyCustomSlave.h"
   #include "MyCustomMonitor.h"

   int main() {
      // Data source
      auto src = MyCustomMaster::create();

      // Main data destination
      auto dst = MyCustomSlave::create();

      // Additional monitor
      auto mon = MyCustomMonitor::create();

      // Primary path
      rogueStreamConnect(src, dst);

      // Tap path: copy at most 20 bytes from each Frame and queue up to 150 Frames
      auto fifo = rogue::interfaces::stream::Fifo::create(150, 20, false);
      rogueStreamConnect(src, fifo);
      rogueStreamConnect(fifo, mon);
      return 0;
   }

Logging
=======

``Fifo`` uses Rogue C++ logging with the static logger name
``pyrogue.stream.Fifo``.

Enable that logger before constructing the object if you want constructor-time
and runtime messages from the ``Fifo`` implementation:

.. code-block:: python

   import rogue
   import rogue.interfaces.stream as ris

   rogue.Logging.setFilter('pyrogue.stream.Fifo', rogue.Logging.Debug)
   fifo = ris.Fifo(256, 0, True)

``Fifo`` does not expose a separate runtime ``setDebug(...)`` helper. If you
need byte-dump inspection, attach a debug ``Slave`` before or after the
``Fifo`` and use ``setDebug(maxBytes, name)`` on that monitor.

What To Explore Next
====================

- Connection topology rules: :doc:`/stream_interface/connecting`
- ``Filter`` usage: :doc:`/stream_interface/filter`
- ``RateDrop`` usage: :doc:`/stream_interface/rate_drop`
- Receive-side monitoring patterns: :doc:`/stream_interface/receiving`

API Reference
=============

- Python:

  - :doc:`/api/python/rogue/interfaces/stream/fifo`

- C++:

  - :doc:`/api/cpp/interfaces/stream/fifo`
