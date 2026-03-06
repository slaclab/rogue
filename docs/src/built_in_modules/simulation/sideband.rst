.. _interfaces_simulation_sideband:

===========
SideBandSim
===========

``SideBandSim`` provides a simple sideband path over paired ZMQ sockets.

It moves optional ``opCode`` and ``remData`` byte fields between endpoints and
runs a background receive thread that invokes a user callback.

Constructor
===========

.. code-block:: python

   sb = pyrogue.interfaces.simulation.SideBandSim(host='127.0.0.1', port=9008)

Port behavior:

- PULL socket connects to ``port``
- PUSH socket connects to ``port+1``

Sending and receiving
=====================

.. code-block:: python

   import pyrogue.interfaces.simulation as pis

   def on_sideband(op_code, rem_data):
       print('rx', op_code, rem_data)

   with pis.SideBandSim('127.0.0.1', 9008) as sb:
       sb.setRecvCb(on_sideband)
       sb.send(opCode=0x3A)
       sb.send(remData=0x55)

Notes:

- Callback receives ``None`` for fields not present in a message
- Malformed frame lengths are logged as errors
- Context-manager exit stops the receive worker

Where to explore next
=====================

- Combined VC + sideband simulation: :doc:`/built_in_modules/simulation/pgp2b`
