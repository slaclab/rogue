.. _protocols_packetizer_core:

========================
Packetizer Protocol Core
========================

Legacy Status
=============

This is a legacy page retained during migration.
Canonical entry point: :doc:`/built_in_modules/index`.

TODO

Status
======

Legacy placeholder content retained.
Detailed protocol narrative and examples are planned in a later expansion pass.

Role
====

``Packetizer Core`` is the primary framing endpoint used by many existing Rogue
systems. It maps stream payloads into packetizer protocol units and supports
application-layer routing patterns.

When to prefer Core
===================

- Existing firmware/software integration expects packetizer v1 behavior.
- You are extending an already-deployed stack using ``Core``.

See also
========

- :doc:`/protocols/packetizer/index`
- :doc:`/protocols/packetizer/coreV2`
