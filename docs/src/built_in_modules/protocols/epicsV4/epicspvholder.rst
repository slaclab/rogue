.. _pyrogue_protocol_epicspvholder:
.. _protocols_epics_epicspvholder:
.. _protocols_epicsv4_epicspvholder:

========================
Epics PV Holder Protocol
========================

``EpicsPvHolder`` is the per-variable bridge object used by the EPICS V4
integration layer.

What it does
============

``EpicsPvHolder`` provides a container/bridge object used when integrating
EPICS PV interactions into a PyRogue-based control application.

Behavior from implementation
============================

Based on ``python/pyrogue/protocols/epicsV4.py``, each holder:

- Infers EPICS value type from variable metadata (including enum and ndarray);
- Creates a P4P ``SharedPV`` with a handler for put/get/rpc behavior;
- Subscribes to PyRogue variable updates via ``addListener``;
- Forwards alarm status/severity and display metadata (units/limits) for
  numeric types.

Lifecycle role in the server
============================

``EpicsPvHolder`` instances are created and owned by ``EpicsPvServer``.
Each holder binds one tree variable/command to one EPICS PV and remains active
for the server lifetime.

Per-holder responsibilities:

- Determine EPICS-facing value type from PyRogue metadata.
- Create backing ``SharedPV`` and handler for put/get/rpc operations.
- Subscribe to variable updates and post translated values/alarms.

When to use it
==============

- You need EPICS-facing value exposure aligned with tree variable semantics.
- You are composing higher-level EPICS publication or subscription workflows.
- You want protocol-specific behavior isolated from core device modeling.

Related Topics
==============

- EPICS server integration: :doc:`epicspvserver`
- General protocol organization: :doc:`/built_in_modules/protocols/index`
- Usage validation: ``tests/test_epics.py``

Logging
=======

``EpicsPvHolder`` does not create a separate logger. Each holder reuses the
server logger passed in from ``EpicsPvServer``:

- Logger name: ``pyrogue.EpicsPvServer``
- Configuration API:
  ``logging.getLogger('pyrogue.EpicsPvServer').setLevel(logging.DEBUG)``

That means put/get/rpc handling errors reported by a holder appear under the
server logger rather than a per-PV logger.

API Reference
=============

See :doc:`/api/python/pyrogue/protocols/epicsv4_epicspvholder` for generated API details.
