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

.. note::

   Passing ``root=self`` to the constructor automatically registers the server
   with the Root lifecycle via ``addProtocol``. Do **not** call
   ``self.addProtocol(self.epics)`` afterwards — doing so registers the server
   twice and raises ``Exception: epicsV7: Duplicate _start() call`` at startup.

   This differs from the EPICS V4 integration, where ``addProtocol`` must be
   called explicitly. If you are migrating from V4, remove the
   ``self.addProtocol(...)`` call.

Setup Example
=============

.. code-block:: python

   import pyrogue as pr
   import pyrogue.protocols.epicsV7 as pep7

   class MyRoot(pr.Root):
       def __init__(self):
           super().__init__(name='MyRoot')
           # Add variables/devices here as usual.

           # Passing root=self auto-registers with the Root lifecycle.
           # Do NOT also call self.addProtocol(self.epics).
           self.epics = pep7.EpicsPvServer(
               base='MyIoc',
               root=self,
               incGroups=None,
               excGroups=['NoServe'],
               pvMap=None,
           )

   with MyRoot() as root:
       # Inspect active mapping.
       root.epics.dump()
       # Optionally write mapping to file for IOC/client integration.
       root.epics.dump('epics_map.txt')

Typical Usage Pattern
=====================

The common setup follows this pattern:

1. Create and start a ``Root`` with Local and Remote variables.
2. Construct ``EpicsPvServer(base=..., root=..., pvMap=...)`` — this
   automatically registers the server with the Root lifecycle.
3. Do **not** call ``root.addProtocol(...)`` — it is handled internally.
4. Use any EPICS client (CA or PVA) to put and get values.
5. Invoke PyRogue Commands using a plain put to the command's PV.

PV Name Length Handling
=======================

EPICS CA enforces a 60-character limit on PV names (``PVNAME_STRINGSZ = 61``
in EPICS Base). When the full name ``base:path`` would exceed 60 characters,
``EpicsPvServer`` automatically shortens the softioc record name to a
deterministic hash of the form ``tail_XXXXXXXXXX`` (10 lowercase hex digits
derived from SHA-1 of the full name). CA clients use this hashed short name;
PVA clients can use the full human-readable name via a PVA alias — they never
need to know about the hash.

- Names at or below 60 characters are published unchanged. Existing deployments
  are completely unaffected.
- Two distinct variable paths that hash to the same short name cause
  ``_start()`` to raise ``RuntimeError`` immediately before any record is
  created.
- ``list()`` always returns full long names regardless of whether a PV was
  hashed.
- ``dump()`` annotates each hashed PV with its CA short name in the form
  ``(CA: base:tail_XXXXXXXXXX)``.

Example output from ``dump()`` for a hashed PV::

   MyIoc:LocalRoot:MyDevice:ThisIsAVeryLongVariableNameThatExceedsSixtyCharacterLimit  (CA: MyIoc:tail_3f9a1b2c4d)

PVA Transparency for Long Names
---------------------------------

For every PV whose CA record name was hashed, ``EpicsPvServer`` additionally
registers the full long name as a PVA-only channel backed by a
``p4p.server.SharedPV``. This means:

- PVA clients connect using the full, human-readable name.
- Reads on the long PVA name return the current PyRogue variable value.
- Writes on the long PVA name update the same PyRogue variable as a CA write
  via the short name.
- A CA write via the short name is immediately visible to PVA clients on the
  long name, and vice versa — with no feedback loops.

.. code-block:: python

   from p4p.client.thread import Context

   ctxt = Context('pva')

   # PVA clients always use the full name — no knowledge of the hash required.
   full_name = 'MyIoc:LocalRoot:MyDevice:ThisIsAVeryLongVariableNameThatExceedsSixtyCharacterLimit'
   value = ctxt.get(full_name)
   ctxt.put(full_name, 42)

Live Hardware Values
====================

softioc does not expose a Python callback that fires when a CA or PVA client
issues a ``caget`` / ``ctxt.get()``. Both EPICS V4 and V7 integrations serve
the most recently pushed value from the EPICS record buffer. To ensure clients
receive up-to-date hardware values, the Rogue server process must execute
hardware reads itself — either via PyRogue auto-polling (``pollInterval`` on
variables or ``pollEn=True`` on the Root) or by calling device-level read
commands explicitly.

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
4. **Remove any** ``self.addProtocol(self.epics)`` **call.** In V4 this was
   required; in V7 the constructor calls ``addProtocol`` automatically when
   ``root=self`` is passed. Keeping the explicit call registers the server
   twice and raises ``Exception: epicsV7: Duplicate _start() call`` at startup.

When To Use It
==============

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

Generated API docs for EPICS V7 are not published on a separate page yet.
Use the class reference ``pyrogue.protocols.epicsV7.EpicsPvServer`` in the
Python API output when available.
