.. _stream_interface_built_in_modules:

=======================
Built-in Stream Modules
=======================

Rogue includes reusable stream modules for buffering, channel/error filtering,
rate limiting, inspection, and network bridging.

Module roles
============

- ``Fifo``: queue-based buffering with optional copy/trim behavior.
- ``Filter``: pass only selected frame channel values, with optional error-drop.
- ``RateDrop``: reduce downstream rate using count-based or time-based policy.
- ``Slave`` debug mode: inspect frames without writing a custom receiver.
- ``TcpServer``/``TcpClient``: full-duplex stream bridge over two TCP ports.

Constructor quick reference
===========================

- ``ris.Fifo(maxDepth, trimSize, noCopy)``
  maxDepth controls queue drop threshold, trimSize limits copied bytes,
  noCopy selects pass-by-reference vs copy.
- ``ris.Filter(dropErrors, channel)``
  forwards only matching-channel frames; optional drop of errored frames.
- ``ris.RateDrop(period, value)``
  period mode uses seconds between forwarded frames; count mode forwards one
  frame then suppresses ``value`` frames.
- ``ris.TcpServer(addr, port)`` / ``ris.TcpClient(addr, port)``
  bridge stream traffic over two consecutive TCP ports.

Detailed usage pages
====================

- :doc:`/stream_interface/fifo`
- :doc:`/stream_interface/filter`
- :doc:`/stream_interface/rate_drop`
- :doc:`/stream_interface/debugStreams`
- :doc:`/stream_interface/tcp_bridge`

API reference
=============

- :doc:`/api/cpp/interfaces/stream/fifo`
- :doc:`/api/cpp/interfaces/stream/filter`
- :doc:`/api/cpp/interfaces/stream/rateDrop`
- :doc:`/api/cpp/interfaces/stream/tcpCore`
- :doc:`/api/cpp/interfaces/stream/tcpClient`
- :doc:`/api/cpp/interfaces/stream/tcpServer`

What to explore next
====================

- Connection patterns: :doc:`/stream_interface/connecting`
- Send/receive frame patterns: :doc:`/stream_interface/sending`,
  :doc:`/stream_interface/receiving`
- Frame semantics and metadata: :doc:`/stream_interface/frame_model`
