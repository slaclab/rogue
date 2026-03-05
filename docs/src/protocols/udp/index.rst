.. _protocols_udp:

============
UDP Protocol
============

Legacy Status
=============

This is a legacy page retained during migration.
Canonical entry point: :doc:`/built_in_modules/index`.

TODO

Status
======

Legacy placeholder content retained.
Detailed protocol narrative and examples are planned in a later expansion pass.

Overview
========

The UDP protocol layer provides datagram transport for stream traffic. In
Rogue systems, UDP is commonly used as a low-level transport under RSSI and
packetizer protocol layers.

Typical role in protocol stack:

.. code-block:: text

   UDP <-> RSSI <-> Packetizer

When to use
===========

- You need lightweight datagram transport over IP networks.
- Your reliability and framing requirements are handled by upper layers.
- You are integrating with existing UDP-based firmware endpoints.

When not to use directly
========================

- If you need ordered/reliable delivery semantics by default, use RSSI over
  UDP instead of raw UDP-only application flows.

Related docs
============

- :doc:`/protocols/network`
- :doc:`/protocols/rssi/index`
- :doc:`/protocols/packetizer/index`

C++ API details for UDP protocol classes are documented in
:doc:`/api/cpp/protocols/udp/index`.

.. toctree::
   :maxdepth: 1
   :caption: UDP Protocol

   client
   server
