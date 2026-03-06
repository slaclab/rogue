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

When to use it
==============

- You need EPICS-facing value exposure aligned with tree variable semantics.
- You are composing higher-level EPICS publication or subscription workflows.
- You want protocol-specific behavior isolated from core device modeling.

Related pages
=============

- EPICS server integration: :doc:`epicspvserver`
- General protocol organization: :doc:`/protocols/index`
- Usage validation: ``tests/test_epics.py``

EPICS PvHolder API Reference
==================================

See :doc:`/api/python/protocols_epicsv4_epicspvholder` for generated API details.
