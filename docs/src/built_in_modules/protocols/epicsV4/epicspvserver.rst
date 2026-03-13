.. _pyrogue_protocol_epicspvserver:
.. _protocols_epics_epicspvserver:
.. _protocols_epicsv4_epicspvserver:

========================
Epics PV Server Protocol
========================

``EpicsPvServer`` is the EPICS V4 server-side bridge for exposing PyRogue tree
variables as PVs.

What It Does
============

``EpicsPvServer`` publishes and serves EPICS-facing process variables using
the PyRogue integration layer.

Behavior from implementation
============================

Based on ``python/pyrogue/protocols/epicsV4.py``, the server:

- Requires a running ``Root`` before startup.
- Builds PV mappings either automatically (``base:path``) or from ``pvMap``.
- Supports include and exclude group filtering (default excludes ``NoServe``).
- Creates one ``EpicsPvHolder`` per served variable and exposes ``list()`` and
  ``dump()`` helpers for mapping inspection.

Constructor and Mapping Overview
================================

``EpicsPvServer(base=..., root=..., incGroups=..., excGroups=..., pvMap=...)``
uses two mapping modes:

- Automatic mode (``pvMap=None``): serves variables that pass group filters
  using ``<base>:<path.with.colons>`` naming.
- Explicit mode (``pvMap`` dict): serves only mapped variable paths with
  user-defined PV names.

Default exclusion is ``['NoServe']`` when ``excGroups`` is not provided.

Code-Backed Setup Example
=========================

.. code-block:: python

   import pyrogue as pr
   import pyrogue.protocols.epicsV4 as pep

   class MyRoot(pr.Root):
       def __init__(self):
           super().__init__(name='MyRoot')
           # Add variables/devices here as usual.

           # Build EPICS server with automatic path-based naming.
           self.epics = pep.EpicsPvServer(
               base='MyIoc',
               root=self,
               incGroups=None,
               excGroups=['NoServe'],
               pvMap=None,
           )

           # Register as protocol so Root lifecycle starts/stops it.
           self.addProtocol(self.epics)

   with MyRoot() as root:
       # Inspect active mapping.
       root.epics.dump()
       # Optionally write mapping to file for IOC/client integration.
       root.epics.dump('epics_map.txt')

Usage Pattern from Tests
========================

``tests/test_epics.py`` validates the common setup:

1. Create and start a ``Root`` with Local and Remote variables.
2. Construct ``EpicsPvServer(base=..., root=..., pvMap=...)``.
3. Register it with ``root.addProtocol(...)``.
4. Use a P4P client to put and get values and confirm round-trip behavior.

When To Use It
==============

- You need external EPICS clients to consume or control values exposed by
  Rogue.
- Your deployment requires EPICS compatibility alongside existing PyRogue
  tooling.
- You want an explicit server boundary for EPICS protocol behavior.

Integration Guidance
====================

- Keep naming and unit conventions aligned between tree variables and EPICS
  PVs.
- Document which PVs are authoritative control points versus status mirrors.
- Pair this page with tree-side validation and polling strategy docs when the
  deployment depends on them.

Logging
=======

``EpicsPvServer`` uses Python logging.

- Logger name: ``pyrogue.EpicsPvServer``
- Configuration API:
  ``logging.getLogger('pyrogue.EpicsPvServer').setLevel(logging.DEBUG)``

This logger is used for PV mapping errors and other server-side operational
messages emitted by the Python implementation.

What To Explore Next
====================

- Per-variable EPICS publication behavior: :doc:`epicspvholder`

Related Topics
==============

- EPICS V4 overview: :doc:`index`
- Tree group filtering: :doc:`/pyrogue_tree/core/groups`
- Logging behavior in PyRogue: :doc:`/logging/index`

API Reference
=============

See :doc:`/api/python/pyrogue/protocols/epicsv4/epicspvserver` for generated API details.
