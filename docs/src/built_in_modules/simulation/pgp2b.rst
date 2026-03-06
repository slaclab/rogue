.. _interfaces_simulation_pgp2b:

========
Pgp2bSim
========

``Pgp2bSim`` builds a simulated PGP2B endpoint from stream TCP clients plus a
sideband channel.

Constructor
===========

.. code-block:: python

   pgp = pyrogue.interfaces.simulation.Pgp2bSim(
       vcCount=4,
       host='127.0.0.1',
       port=9000,
   )

Behavior:

- Creates ``vcCount`` stream endpoints as ``rogue.interfaces.stream.TcpClient``
- Virtual-channel ports are ``port, port+2, ..., port+2*(vcCount-1)``
- Sideband uses a paired channel at ``port+8`` via ``SideBandSim``

Connecting two simulated endpoints
==================================

.. code-block:: python

   import pyrogue.interfaces.simulation as pis

   with pis.Pgp2bSim(vcCount=4, host='127.0.0.1', port=9000) as a, \
        pis.Pgp2bSim(vcCount=4, host='127.0.0.1', port=9100) as b:

       pis.connectPgp2bSim(a, b)

``connectPgp2bSim(a, b)`` links each VC pair bidirectionally and cross-connects
sideband callbacks.

Where to explore next
=====================

- Sideband channel details: :doc:`/built_in_modules/simulation/sideband`
- Stream topologies and connection operators: :doc:`/stream_interface/connecting`
- TCP stream transport behavior: :doc:`/stream_interface/tcp_bridge`
