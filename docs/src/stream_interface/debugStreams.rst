.. _interfaces_stream_debug_streams:
.. _stream_interface_debug_streams:

=================
Debugging Streams
=================

The base :ref:`interfaces_stream_slave` class can serve as a passive debug
receiver for stream traffic. This is often the simplest way to inspect a stream
without writing a custom ``Slave`` implementation.

You typically use a debug ``Slave`` during bring-up, when verifying a new
connection path, when checking that channel and error fields look correct, or
when you need to see the first few payload bytes of each incoming ``Frame``.
Most of the time the debug ``Slave`` is attached as a secondary ``Slave`` so it
observes traffic without disturbing the primary processing path.

Debug Behavior
==============

Enable debug printing with ``setDebug(maxBytes, name)`` on a base ``Slave``.

- ``maxBytes`` controls how many payload bytes are shown for each received
  ``Frame``
- ``name`` controls the logger name suffix used for emitted messages

Python Example
==============

.. code-block:: python

   import rogue.interfaces.stream as ris

   # Data source
   src = MyCustomMaster()

   # Data destination
   dst = MyCustomSlave()

   # Debug Slave
   dbg = ris.Slave()

   # Print up to the first 100 bytes of each received Frame
   dbg.setDebug(100, 'myDebug')

   # Primary path
   src >> dst

   # Add the debug Slave as a second receiver
   src >> dbg

C++ Example
===========

.. code-block:: cpp

   #include "rogue/Helpers.h"
   #include "rogue/interfaces/stream/Slave.h"
   #include "MyCustomMaster.h"
   #include "MyCustomSlave.h"

   int main() {
      // Data source
      auto src = MyCustomMaster::create();

      // Data destination
      auto dst = MyCustomSlave::create();

      // Debug Slave
      auto dbg = rogue::interfaces::stream::Slave::create();

      // Print up to the first 100 bytes of each received Frame
      dbg->setDebug(100, "myDebug");

      // Primary path
      rogueStreamConnect(src, dst);

      // Add the debug Slave as a second receiver
      rogueStreamConnect(src, dbg);
      return 0;
   }

Logging
=======

``setDebug(maxBytes, name)`` uses Rogue C++ logging, not Python ``logging``.
The emitted logger name is ``pyrogue.<name>``.

For example, ``dbg.setDebug(100, 'stream.debug')`` emits through
``pyrogue.stream.debug``. Enable that logger before using the debug ``Slave``:

- Dynamic logger pattern: ``pyrogue.<name>``
- Unified Logging API:
  ``logging.getLogger('pyrogue.stream.debug').setLevel(logging.DEBUG)``
- Legacy Logging API:
  ``rogue.Logging.setFilter('pyrogue.stream.debug', rogue.Logging.Debug)``

.. code-block:: python

   import rogue
   import rogue.interfaces.stream as ris

   rogue.Logging.setFilter('pyrogue.stream.debug', rogue.Logging.Debug)

   dbg = ris.Slave()
   dbg.setDebug(100, 'stream.debug')

The helper creates the logger when debug mode is enabled, so it is best to set
the filter first.

Debugging Notes
===============

- The base ``Slave`` debug path increments internal frame and byte counters.
- The logger name is determined entirely by the ``name`` argument passed to
  ``setDebug(...)``.
- If a custom C++ ``Slave`` overrides ``acceptFrame`` and still wants the base
  debug and counter behavior, it should call ``Slave::acceptFrame(frame)`` or
  implement equivalent logic explicitly.

What To Explore Next
====================

- Connection placement rules: :doc:`/stream_interface/connecting`
- Receive-side handling: :doc:`/stream_interface/receiving`
- ``Fifo`` tap patterns: :doc:`/stream_interface/fifo`
- ``RateDrop`` sampling patterns: :doc:`/stream_interface/rate_drop`

Related Topics
==============

- Rogue logging overview: :doc:`/logging/index`

API Reference
=============

- Python:

  - :doc:`/api/python/rogue/interfaces/stream/slave`

- C++:

  - :doc:`/api/cpp/interfaces/stream/slave`
