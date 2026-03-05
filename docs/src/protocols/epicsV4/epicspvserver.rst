.. _pyrogue_protocol_epicspvserver:
.. _protocols_epics_epicspvserver:
.. _protocols_epicsv4_epicspvserver:

========================
Epics PV Server Protocol
========================

``EpicsPvServer`` is the EPICS V4 server-side bridge for exposing PyRogue tree
variables as PVs.

What it does
============

``EpicsPvServer`` publishes and serves EPICS-facing process variables using
the PyRogue integration layer.

Behavior from implementation
============================

Based on ``python/pyrogue/protocols/epicsV4.py``, the server:

- requires a running root before startup;
- builds PV mappings either automatically (``base:path``) or from ``pvMap``;
- supports include/exclude group filtering (default excludes ``NoServe``);
- creates one ``EpicsPvHolder`` per served variable and exposes list/dump
  helpers for mapping inspection.

Usage pattern from tests
========================

``tests/test_epics.py`` validates the common setup:

1. Create/start a root with Local and Remote variables.
2. Construct ``EpicsPvServer(base=..., root=..., pvMap=...)``.
3. Register it with ``root.addProtocol(...)``.
4. Use a P4P client to put/get values and confirm round-trip behavior.

When to use it
==============

- You need external EPICS clients to consume/control values exposed by Rogue.
- Your deployment requires EPICS compatibility alongside existing PyRogue
  tooling.
- You want an explicit server boundary for EPICS protocol behavior.

Integration guidance
====================

- Keep naming/unit conventions aligned between tree variables and EPICS PVs.
- Document which PVs are authoritative control points versus status mirrors.
- Pair with tree-side validation and polling strategy docs as needed.

EpicsPvServer API Reference
=================================

See :doc:`/api/python/protocols_epicsv4_epicspvserver` for generated API details.
