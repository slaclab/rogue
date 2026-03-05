.. _stream_interface_built_in_modules:

=======================
Built-in Stream Modules
=======================

Common built-in modules include FIFO, Filter, RateDrop, Debug, and TCP bridge
components.

Module roles at a glance
========================

- FIFO: absorb burstiness and decouple producer/consumer timing.
- Filter: transform or select frame content.
- RateDrop: bound downstream processing by dropping at policy-defined rates.
- Debug: inspect frame flow and metadata during bring-up.
- TCP bridge: connect stream paths across processes or hosts.

Selection and ordering guidance
===============================

- Put flow-control modules (FIFO/RateDrop) near rate boundaries.
- Put transformation modules (Filter) before expensive consumers.
- Keep debug modules easy to enable/disable for operations.

Usage docs:

- :doc:`/interfaces/stream/usingFifo`
- :doc:`/interfaces/stream/usingFilter`
- :doc:`/interfaces/stream/usingRateDrop`
- :doc:`/interfaces/stream/debugStreams`
- :doc:`/interfaces/stream/usingTcp`

API reference:

- :doc:`/api/cpp/interfaces/stream/fifo`
- :doc:`/api/cpp/interfaces/stream/filter`
- :doc:`/api/cpp/interfaces/stream/rateDrop`
- :doc:`/api/cpp/interfaces/stream/tcpCore`
- :doc:`/api/cpp/interfaces/stream/tcpClient`
- :doc:`/api/cpp/interfaces/stream/tcpServer`
