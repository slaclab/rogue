.. _pyrogue_protocol_epicsv7_epicspvserver:
.. _protocols_epicsv7_epicspvserver:

================================
Epics PV Server (V7 Protocol)
================================

``EpicsPvServer`` is the EPICS V7 server-side bridge for exposing PyRogue tree
variables as EPICS records using softIocPVA (pythonSoftIOC).

What It Does
============

``EpicsPvServer`` builds and runs a softIocPVA instance in a background thread,
creating real EPICS records for each served PyRogue Variable or Command.

Server Behavior
===============

``EpicsPvServer``:

- Requires a running ``Root`` before startup.
- Builds PV mappings either automatically (``base:path``) or from ``pvMap``.
- Supports include and exclude group filtering (default excludes ``NoServe``).
- Creates one ``EpicsPvHolder`` per served variable and exposes ``list()`` and
  ``dump()`` helpers for mapping inspection.
- Starts softIocPVA once via ``iocInit()`` — the IOC is a process-wide
  singleton; multiple ``EpicsPvServer`` instances share the same running IOC.
- Serves both CA and PVA protocols; any standard EPICS client can access
  the published records.

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
   import pyrogue.protocols.epicsV7 as pep7

   class MyRoot(pr.Root):
       def __init__(self):
           super().__init__(name='MyRoot')
           # Add variables/devices here as usual.

           # Build EPICS V7 server with automatic path-based naming.
           self.epics = pep7.EpicsPvServer(
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
4. Use any EPICS client (CA or PVA) to put and get values.
5. Invoke PyRogue Commands using a plain put to the command's PV.

Hardware-Read-on-GET
=====================

A key feature of the V7 integration is hardware-read-on-GET semantics.
Because softIocPVA processes a record on every incoming GET request, the
bound PyRogue variable's ``get()`` method is called each time a client reads
the value. For variables with a ``localGet`` callback, this means the callback
fires on every client read rather than only when the Rogue tree fires a change
notification.

This makes the V7 server suitable for hardware polling use cases where the
latest value must be fetched from hardware on every read.

Commands via caput
==================

PyRogue Commands (``LocalCommand`` and ``RemoteCommand``) are exposed as
longOut EPICS records. Clients invoke them with a plain put:

Invoking a No-Arg Command
--------------------------

.. code-block:: python

   from p4p.client.thread import Context

   ctxt = Context('pva')

   pv_name = 'MyIoc:MyRoot:MyDevice:ResetCounter'
   ctxt.put(pv_name, 0)   # value=0 triggers no-arg command call

Invoking a Command With an Argument
-------------------------------------

.. code-block:: python

   from p4p.client.thread import Context

   ctxt = Context('pva')

   pv_name = 'MyIoc:MyRoot:MyDevice:SetThreshold'
   ctxt.put(pv_name, 42)   # value is forwarded to command as arg

The put value is forwarded directly to the PyRogue command as its argument.
This is different from the V4 integration, which uses ``ctxt.rpc()`` with
an NTURI wrapper.

Migration from EPICS V4
=======================

The ``EpicsPvServer`` constructor signature is identical in V4 and V7.
The key differences when migrating:

1. Replace ``import pyrogue.protocols.epicsV4 as pep`` with
   ``import pyrogue.protocols.epicsV7 as pep7`` and update the class reference.
2. Replace ``ctxt.rpc()`` command invocations with ``ctxt.put(pv_name, value)``.
3. Install ``softioc`` (``pip install softioc``) instead of or alongside ``p4p``.
   If you use ``p4p`` as a PVA client (for ``ctxt.get()`` / ``ctxt.put()``),
   keep it — only the server-side dependency changes.

When To Use It
==============

- You need hardware-read-on-GET semantics for ``localGet`` variables.
- Your deployment requires CA compatibility alongside PVA.
- You want to avoid the p4p SharedPV server in favor of standard softIocPVA.

Logging
=======

``EpicsPvServer`` uses Python logging.

- Logger name: ``pyrogue.EpicsPvServer``
- Configuration API:
  ``logging.getLogger('pyrogue.EpicsPvServer').setLevel(logging.DEBUG)``

What To Explore Next
====================

- Per-variable EPICS record behavior: :doc:`epicspvholder`

Related Topics
==============

- EPICS V7 overview: :doc:`index`
- EPICS V4 server (p4p-based): :doc:`/built_in_modules/protocols/epicsV4/epicspvserver`
- Tree group filtering: :doc:`/pyrogue_tree/core/groups`
- Logging behavior in PyRogue: :doc:`/logging/index`

API Reference
=============

See :doc:`/api/python/pyrogue/protocols/epicsv7/epicspvserver` for generated API details.
