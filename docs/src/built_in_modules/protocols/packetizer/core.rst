.. _protocols_packetizer_core:

========================
Packetizer Protocol Core
========================

``Core`` is the packetizer v1 wiring class. It creates a ``Transport`` endpoint
and a v1 controller, then exposes ``application(dest)`` endpoints for channel-
based application routing.

Behavior summary
================

- Constructor argument ``enSsi`` controls SSI framing behavior.
- ``transport()`` returns the stream edge for lower-layer connection.
- ``application(dest)`` lazily allocates per-destination application endpoints.
- ``getDropCount()`` exposes controller-reported dropped-frame count.
- ``setTimeout()`` forwards timeout tuning into controller behavior.

When to prefer Core
===================

- Existing firmware/software integration expects packetizer v1 behavior.
- You are extending an already-deployed stack already based on ``Core``.

Code-backed example
===================

.. code-block:: python

   import rogue.protocols.packetizer

   pkt = rogue.protocols.packetizer.Core(True)
   pkt.application(0) >> reg_sink
   data_source >> pkt.application(1)

   # Attach transport side to lower protocol layer
   # lower_layer == pkt.transport()

See also
========

- :doc:`/built_in_modules/protocols/packetizer/index`
- :doc:`/built_in_modules/protocols/packetizer/coreV2`
- :doc:`/api/cpp/protocols/packetizer/core`
