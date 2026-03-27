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

Server Behavior
===============

``EpicsPvServer``:

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

Setup Example
=============

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

Typical Usage Pattern
=====================

The common setup follows this pattern:

1. Create and start a ``Root`` with Local and Remote variables.
2. Construct ``EpicsPvServer(base=..., root=..., pvMap=...)``.
3. Register it with ``root.addProtocol(...)``.
4. Use a P4P client to put and get values and confirm round-trip behavior.
5. Use ``ctxt.rpc()`` to invoke PyRogue Commands through EPICS.

RPC for Commands
================

PyRogue Commands (``LocalCommand`` and ``RemoteCommand``) are automatically
exposed through EPICS RPC when served by ``EpicsPvServer``. The server-side
``EpicsPvHandler.rpc()`` method dispatches incoming RPC requests to the bound
PyRogue Command.

Commands appear in the PV namespace alongside variables and can be invoked from
any P4P client using ``ctxt.rpc()``.

Invoking a Command Without Arguments
-------------------------------------

Use an ``NTURI`` with an empty query to call a no-argument command:

.. code-block:: python

   from p4p.client.thread import Context
   from p4p.nt import NTURI

   ctxt = Context('pva')

   pv_name = 'MyIoc:MyRoot:MyDevice:ResetCounter'
   uri = NTURI([])
   ctxt.rpc(pv_name, uri.wrap(pv_name))

On the server side, the handler sees no ``arg`` field in the query and calls
the command with no argument.

Invoking a Command With an Argument
------------------------------------

To pass a value into a command, declare a query field named ``arg`` in the
``NTURI``. The handler extracts ``val.arg`` from the query and forwards it
to the PyRogue command:

.. code-block:: python

   from p4p.client.thread import Context
   from p4p.nt import NTURI

   ctxt = Context('pva')

   pv_name = 'MyIoc:MyRoot:MyDevice:SetThreshold'
   uri = NTURI([('arg', 'i')])   # 'i' = int32; use 'd' for float64, 's' for string
   ctxt.rpc(pv_name, uri.wrap(pv_name, kws={'arg': 42}))

The NTURI type code for the ``arg`` field should match the expected value type.
Common type codes are ``'i'`` (int32), ``'l'`` (int64), ``'d'`` (float64), and
``'s'`` (string).

P4P Context Behavior After RPC
-------------------------------

.. note::

   Calling ``ctxt.rpc()`` on a P4P ``Context`` may cause subsequent
   ``ctxt.get()`` calls to return raw ``p4p.wrapper.Value`` structs instead of
   auto-unwrapped scalars. If you need to continue using ``ctxt.get()`` after
   an RPC call, use a separate ``Context`` for the RPC operation:

   .. code-block:: python

      rpc_ctxt = Context('pva')
      rpc_ctxt.rpc(pv_name, uri.wrap(pv_name))
      rpc_ctxt.close()

      # The original context continues to return unwrapped scalars.
      value = ctxt.get(other_pv)

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
- Logging API:
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
