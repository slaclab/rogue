.. _interfaces_simulation_pgp2b:

========
Pgp2bSim
========

``Pgp2bSim`` builds a simulated PGP2B endpoint from stream TCP clients plus a
sideband channel.

Co-Simulation Context
=====================

In many development flows, VHDL is run in a simulator (commonly VCS) while
Rogue software drives and observes the design through Rogue stream interfaces
(with VHPI on the firmware side). This is often referred to as software
co-simulation.

In deployed firmware, PGP2b links are commonly used between FPGA endpoints.
For simulation, SURF provides ``RoguePgp2bSim`` firmware modules that emulate
PGP link endpoints and expose TCP-backed stream interfaces.

``Pgp2bSim`` exists to connect two of those simulated endpoints through
software. This avoids simulating full high-speed serial transceiver behavior in
VHDL, which is typically much slower, while still exercising the intended data
movement between link endpoints.

In short, this module focuses on emulating the functional purpose of the link
(frame movement and sideband exchange) rather than electrical-link behavior.
Although this utility may ultimately belong in SURF, it is currently part of
Rogue and documented here.

Method overview
===============

Key pieces used in the examples below:

- ``Pgp2bSim(vcCount, host, port)``: constructs one simulated endpoint.
- ``connectPgp2bSim(a, b)``: links all virtual channels and sideband between
  two endpoints.
- ``setRecvCb(fn)`` on each endpoint sideband object: registers callback for
  sideband ``opCode``/``remData`` events.
- Context-manager usage (``with``): ensures sockets/threads are cleaned up.

Constructor
===========

.. code-block:: python

   import pyrogue.interfaces.simulation as pis

   # Create one simulated endpoint with 4 virtual channels.
   pgp = pis.Pgp2bSim(
       vcCount=4,
       host='127.0.0.1',
       port=9000,
   )

Behavior:

- Creates ``vcCount`` stream endpoints as ``rogue.interfaces.stream.TcpClient``
- Virtual-channel ports are ``port, port+2, ..., port+2*(vcCount-1)``
- Sideband uses a paired channel at ``port+8`` via ``SideBandSim``
- In the current implementation, sideband offset is fixed (not derived from
  ``vcCount``), so ``vcCount`` should be kept at ``<= 4`` to avoid port
  overlap with sideband.

Integrated Sideband Channel
===========================

In ``Pgp2bSim``, sideband is not a separate topology concept; it is part of the
simulated PGP endpoint. Internally it uses ``SideBandSim`` to exchange optional
``opCode`` and ``remData`` fields.

Sideband port behavior (per endpoint):

- PULL socket connects to ``port+8``
- PUSH socket connects to ``port+9``
- These offsets are fixed in current code, independent of ``vcCount``.

Typical sideband callback pattern:

.. code-block:: python

   import pyrogue.interfaces.simulation as pis

   def on_a_sideband(op_code, rem_data):
       # Called when endpoint A receives sideband data.
       print("A sideband:", op_code, rem_data)

   def on_b_sideband(op_code, rem_data):
       # Called when endpoint B receives sideband data.
       print("B sideband:", op_code, rem_data)

   with pis.Pgp2bSim(vcCount=4, host='127.0.0.1', port=9000) as a, \
        pis.Pgp2bSim(vcCount=4, host='127.0.0.1', port=9100) as b:

       pis.connectPgp2bSim(a, b)

       # Register sideband callbacks on each endpoint.
       a.setRecvCb(on_a_sideband)
       b.setRecvCb(on_b_sideband)

       # Inject sideband data from either endpoint.
       a.sendOpCode(0x3A)
       b.sendRemData(0x55)

Standalone SideBandSim Usage
============================

While sideband is integrated into ``Pgp2bSim``, ``SideBandSim`` is also useful
on its own to emulate PGP2b opcode/remData behavior in software/firmware
co-simulation.

.. code-block:: python

   import pyrogue.interfaces.simulation as pis

   def on_sideband(op_code, rem_data):
       # Receive emulated opcode/remData notifications.
       print("sideband rx:", op_code, rem_data)

   with pis.SideBandSim('127.0.0.1', 9008) as sb:
       # Register receive callback.
       sb.setRecvCb(on_sideband)

       # Send opcode-only and remData-only examples.
       sb.send(opCode=0x12)
       sb.send(remData=0x34)

Connecting two simulated endpoints
==================================

.. code-block:: python

   import pyrogue.interfaces.simulation as pis

   # Build two simulated endpoints using different base-port ranges.
   with pis.Pgp2bSim(vcCount=4, host='127.0.0.1', port=9000) as a, \
        pis.Pgp2bSim(vcCount=4, host='127.0.0.1', port=9100) as b:

       # Connect all VCs bidirectionally and link sideband callbacks.
       pis.connectPgp2bSim(a, b)

``connectPgp2bSim(a, b)`` links each VC pair bidirectionally and cross-connects
sideband callbacks.

Operational Notes
=================

- Use distinct base-port ranges per endpoint to avoid overlap.
- Keep ``vcCount`` matched between both endpoints when linking.
- Use ``with`` context management so background resources are cleaned up
  automatically.

Logging
=======

``Pgp2bSim`` itself is a composition wrapper and does not create a dedicated
logger of its own.

The useful logging comes from two lower layers:

- ``SideBandSim`` uses Python logging with names of the form
  ``pyrogue.SideBandSim.<host>.<port>``
- The underlying TCP stream endpoints can be debugged through the normal
  TCP bridge logger family documented in :doc:`/stream_interface/tcp_bridge`

Example:

.. code-block:: python

   import logging
   import rogue

   logging.getLogger('pyrogue.SideBandSim').setLevel(logging.DEBUG)
   rogue.Logging.setFilter('pyrogue.stream.TcpCore', rogue.Logging.Debug)

What To Explore Next
====================

- Stream topologies and connection operators: :doc:`/stream_interface/connecting`
- TCP stream transport behavior: :doc:`/stream_interface/tcp_bridge`
