.. _protocols_packetizer_coreV2:

==========================
Packetizer Protocol CoreV2
==========================

``CoreV2`` is the packetizer v2 wiring class. It creates a ``Transport``
endpoint and a v2 controller, then exposes ``application(dest)`` endpoints for
channel-based application routing.

Behavior summary
================

- Constructor arguments:
  ``enIbCrc`` enables inbound CRC checking,
  ``enObCrc`` enables outbound CRC generation,
  ``enSsi`` controls SSI behavior.
- ``transport()`` returns the stream edge for lower-layer connection.
- ``application(dest)`` lazily allocates per-destination application endpoints.
- ``getDropCount()`` exposes controller-reported dropped-frame count.
- ``setTimeout()`` forwards timeout tuning into controller behavior.

When to prefer CoreV2
=====================

- New designs where packetizer version selection is open.
- Integrations requiring packetizer v2 behavior or CRC configuration control.

Code-backed example
===================

.. code-block:: python

   import rogue.protocols.packetizer

   pkt = rogue.protocols.packetizer.CoreV2(True, True, True)
   pkt.application(0) >> reg_sink
   data_source >> pkt.application(1)

   # Attach transport side to lower protocol layer
   # lower_layer == pkt.transport()

Compatibility note
==================

Core/CoreV2 selection must match peer endpoint expectations. Confirm protocol
version alignment across firmware and software.

See also
========

- :doc:`/protocols/packetizer/index`
- :doc:`/protocols/packetizer/core`
- :doc:`/api/cpp/protocols/packetizer/coreV2`
