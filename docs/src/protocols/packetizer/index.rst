.. _protocols_packetizer:

===================
Packetizer Protocol
===================

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

Packetizer provides frame-level protocol formatting used above transport and
reliability layers. It allows Rogue applications to exchange typed/channeled
payloads on top of lower-level links.

Typical role in protocol stack:

.. code-block:: text

   UDP <-> RSSI <-> Packetizer <-> Application logic

Core variants
=============

- ``Core``: baseline packetizer implementation for standard deployments.
- ``CoreV2``: newer packetizer variant with updated protocol behavior and
  compatibility needs.

When to use
===========

- You need explicit packet framing at the protocol layer.
- You need destination/application channel routing semantics.
- You are integrating with systems that already use Rogue packetizer endpoints.

Related docs
============

- :doc:`/protocols/network`
- :doc:`/protocols/rssi/index`
- :doc:`/protocols/udp/index`

C++ API details for packetizer protocol classes are documented in
:doc:`/api/cpp/protocols/packetizer/index`.

.. toctree::
   :maxdepth: 1
   :caption: Packetizer Protocol

   core
   coreV2
