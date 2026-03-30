.. _pyrogue_protocol_epicspvholder:
.. _protocols_epics_epicspvholder:
.. _protocols_epicsv4_epicspvholder:

========================
Epics PV Holder Protocol
========================

``EpicsPvHolder`` is the per-variable bridge object used by the EPICS V4
integration layer. Each holder binds one PyRogue Variable or Command to one
EPICS PV and remains owned by ``EpicsPvServer`` for the server lifetime.

The holder is where PyRogue metadata becomes EPICS-facing behavior. It infers
the published value type from the Variable metadata, creates the backing P4P
``SharedPV``, installs the put/get/rpc handler, subscribes to PyRogue variable
updates with ``addListener()``, and forwards alarm state plus display metadata
for numeric types.

Type Mapping and Updates
========================

``EpicsPvHolder`` handles several important translation cases:

- Enum variables are published through EPICS enum support using the Variable's
  display choices.
- NumPy arrays are published as array-oriented EPICS types.
- Numeric scalars carry alarm status, severity, description, units, and limit
  metadata when those values are present in the tree.
- Strings, lists, dictionaries, and unsupported native types fall back to a
  string-oriented EPICS representation.

Command and Variable Behavior
=============================

Writable Variables accept EPICS puts and translate them through the normal
PyRogue set and display paths. Commands are exposed through EPICS RPC behavior,
with the holder forwarding the EPICS request payload into the bound PyRogue
command and packaging the return value back into the EPICS response.

RPC Dispatch
------------

When an EPICS client calls ``ctxt.rpc()`` on a command-backed PV, the
``EpicsPvHandler.rpc()`` method extracts the query from the incoming request.
If the query contains an ``arg`` field, the value is forwarded to the PyRogue
command; otherwise the command is called with no argument. The return value is
wrapped in a P4P ``Value`` and sent back to the client.

For usage examples and client-side patterns, see
:ref:`protocols_epicsv4_epicspvserver`.

Lifecycle Role in the Server
============================

``EpicsPvHolder`` instances are created and owned by ``EpicsPvServer``. Each
holder binds one tree Variable or Command to one EPICS PV and remains active
for the server lifetime.

Logging
=======

``EpicsPvHolder`` does not create a separate logger. Each holder reuses the
server logger passed in from ``EpicsPvServer``:

- Logger name: ``pyrogue.EpicsPvServer``
- Logging API:
  ``pyrogue.setLogLevel('pyrogue.EpicsPvServer', 'DEBUG')``

That means put/get/rpc handling errors reported by a holder appear under the
server logger rather than a per-PV logger.

What To Explore Next
====================

- Server setup and mapping control: :doc:`epicspvserver`

Related Topics
==============

- EPICS V4 overview: :doc:`index`
- Logging behavior in PyRogue: :doc:`/logging/index`

API Reference
=============

See :doc:`/api/python/pyrogue/protocols/epicsv4/epicspvholder` for generated API details.
