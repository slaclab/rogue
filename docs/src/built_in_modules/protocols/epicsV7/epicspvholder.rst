.. _pyrogue_protocol_epicsv7_epicspvholder:
.. _protocols_epicsv7_epicspvholder:

==============================
Epics PV Holder (V7 Protocol)
==============================

``EpicsPvHolder`` is the per-variable bridge object used by the EPICS V7
integration layer. Each holder binds one PyRogue Variable or Command to one
EPICS record and remains owned by ``EpicsPvServer`` for the server lifetime.

The holder infers the record type from Variable metadata, uses the softioc
builder to create the backing record, installs the on-put callback, subscribes
to PyRogue variable updates with ``addListener()``, and forwards alarm state
plus display metadata for numeric types.

Type Mapping and Updates
========================

``EpicsPvHolder`` handles several important translation cases:

- Integer variables (int, uint) are published as longIn/longOut record pairs
  (read and write records respectively).
- Float variables are published as ai/ao record pairs.
- Enum variables are published using softioc enum record support with the
  Variable's display choices.
- NumPy arrays are published as waveform records.
- Numeric scalars carry alarm status and severity when those values are
  present in the tree.
- Strings, lists, dictionaries, and unsupported native types fall back to a
  string-oriented EPICS representation.

PV Name Hashing and PVA Alias
=============================

When the full PV name ``base:path`` exceeds EPICS CA's 60-character limit,
``EpicsPvServer`` assigns the softioc record a hashed short name of the form
``tail_XXXXXXXXXX``. The holder stores this short name and transparently
manages both the CA record and a PVA alias for the full long name.

For hashed PVs, the holder additionally owns a ``p4p.server.SharedPV`` served
under the full long name via a dedicated ``p4p.server.Server``. Variable
updates fan out to both:

1. The softioc CA record (existing behavior — unchanged for all PVs).
2. The ``SharedPV`` via ``post()``, so PVA clients on the long name see the
   new value immediately.

Writes arriving on the PVA long name are routed through the same ``_on_put``
path as CA writes, updating the PyRogue variable exactly once with no feedback
loop.

PVs whose names are 60 characters or fewer have no ``SharedPV`` and behave
identically to before this change.

Command Behavior
================

PyRogue Commands (``LocalCommand`` and ``RemoteCommand``) are exposed as
longOut records. When an EPICS client writes to the record (``caput``), the
holder's on-put callback fires:

- If the written value is zero, the command is invoked with no argument.
- If the written value is non-zero, the value is forwarded to the command
  as the ``arg`` parameter.

This means commands are invoked with a plain ``ctxt.put()`` call from any
EPICS client — no RPC protocol is involved.

Invoking a No-Arg Command
-------------------------

.. code-block:: python

   from p4p.client.thread import Context

   ctxt = Context('pva')
   ctxt.put('MyIoc:MyRoot:MyDevice:ResetCounter', 0)

Invoking a Command With an Argument
------------------------------------

.. code-block:: python

   from p4p.client.thread import Context

   ctxt = Context('pva')
   ctxt.put('MyIoc:MyRoot:MyDevice:SetThreshold', 42)

The value ``42`` is forwarded to the PyRogue command as its argument.

Lifecycle Role in the Server
============================

``EpicsPvHolder`` instances are created and owned by ``EpicsPvServer``. Each
holder binds one tree Variable or Command to one EPICS record and remains
active for the server lifetime.

Logging
=======

``EpicsPvHolder`` reuses the server logger passed in from ``EpicsPvServer``:

- Logger name: ``pyrogue.EpicsPvServer``
- Configuration API:
  ``logging.getLogger('pyrogue.EpicsPvServer').setLevel(logging.DEBUG)``

Put-handling errors reported by a holder appear under the server logger.

What To Explore Next
====================

- Server setup and mapping control: :doc:`epicspvserver`

Related Topics
==============

- EPICS V7 overview: :doc:`index`
- EPICS V4 holder (p4p-based): :doc:`/built_in_modules/protocols/epicsV4/epicspvholder`
- Logging behavior in PyRogue: :doc:`/logging/index`

API Reference
=============

Generated API docs for EPICS V7 are not published on a separate page yet.
Use the class reference ``pyrogue.protocols.epicsV7.EpicsPvHolder`` in the
Python API output when available.
