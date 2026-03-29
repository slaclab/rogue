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

Hardware-Read-on-GET
====================

Because softioc processes records on every incoming GET request, the holder's
bound PyRogue variable has its ``get()`` method called on every client read.
Variables that define a ``localGet`` callback see that callback invoked each
time an EPICS client issues a GET, providing true hardware-read-on-GET
semantics without any polling.

This is a key behavioral difference from the EPICS V4 integration, where
values are pushed to clients only when the PyRogue listener fires.

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

See :doc:`/api/python/pyrogue/protocols/epicsv7/epicspvholder` for generated API details.
