.. _protocols_network:

===============
Network Wrapper
===============

``pyrogue.protocols.UdpRssiPack`` is implemented in
``python/pyrogue/protocols/_Network.py`` and provides a compact way to build
the standard Rogue UDP/RSSI/packetizer stack. For RSSI protocol behavior and
stack internals, see :ref:`protocols_rssi`.

Overview
========

``pyrogue.protocols.UdpRssiPack`` is a convenience ``pyrogue.Device`` that
bundles the common network stack used by many Rogue/PyRogue systems:

* UDP transport (``rogue.protocols.udp.Client`` or ``Server``)
* RSSI reliability layer (``rogue.protocols.rssi.Client`` or ``Server``)
* Packetizer framing (``rogue.protocols.packetizer.Core`` or ``CoreV2``)

Internally, it wires the stream graph as:

.. code-block:: text

   UDP <-> RSSI Transport <-> RSSI Application <-> Packetizer

Because it is a ``pyrogue.Device``, RSSI status and configuration variables are
exposed directly in the PyRogue tree.

Implementation details from ``_Network.py``
===========================================

- ``server=False``:
  Creates ``udp.Client(host, port, jumbo)`` and ``rssi.Client(...)``.
- ``server=True``:
  Creates ``udp.Server(port, jumbo)`` and ``rssi.Server(...)``.
- Packetizer selection by ``packVer``:
  ``packVer=1`` uses ``packetizer.Core(enSsi)``;
  ``packVer=2`` uses ``packetizer.CoreV2(False, True, enSsi)``.
- RSSI segment size is derived from transport payload budget:
  ``udp.maxPayload() - 8``.

When to use
===========

Use ``UdpRssiPack`` when you want:

* A standard UDP + RSSI + packetizer stack with minimal setup code
* Link status/counters in the PyRogue variable tree
* Start/stop lifecycle managed through the Root interface mechanism

For most hardware systems (software talking to an FPGA RSSI endpoint), use
``server=False`` so Rogue acts as the RSSI/UDP client and connects outbound to
the FPGA target.

Key constructor arguments
=========================

* ``server``:
  Choose server mode (``True``) or client mode (``False``). Typical FPGA
  register/data links use ``False``.
* ``host``/``port``:
  Remote endpoint for client mode, or bind port for server mode.
* ``jumbo``:
  Enable jumbo-MTU path assumptions in UDP setup.
* ``packVer``:
  Packetizer version, ``1`` or ``2``.
* ``enSsi``:
  Enable SSI handling in packetizer.
* ``wait``:
  In client mode, wait for RSSI link-up during startup.
* ``defaults`` (via ``kwargs``):
  Optional RSSI parameter overrides such as ``locMaxBuffers``,
  ``locCumAckTout``, ``locRetranTout``, ``locNullTout``,
  ``locMaxRetran``, ``locMaxCumAck``.

Startup behavior
================

During ``UdpRssiPack._start()``:

- RSSI is started first.
- In client mode with ``wait=True``, startup waits for link-open.
- After link bring-up, UDP RX buffer count is tuned from negotiated RSSI
  buffer depth (``udp.setRxBufferCount(rssi.curMaxBuffers())``).

This startup behavior is why using the wrapper through Root-managed lifecycle
is preferred for full applications.

Typical Root integration
========================

Use ``add()`` to place the wrapper in the tree, then ``addInterface()`` so
Root start/stop sequencing manages the transport lifecycle.

.. code-block:: python

   import pyrogue as pr
   import pyrogue.protocols
   import pyrogue.utilities.fileio
   import rogue.protocols.srp

   class MyRoot(pr.Root):
       def __init__(self):
           super().__init__(name='MyRoot')

           # Add bundled UDP + RSSI + packetizer stack.
           self.add(pyrogue.protocols.UdpRssiPack(
               name='Net',
               server=False,
               host='10.0.0.5',
               port=8192,
               jumbo=True,
               packVer=2,
               enSsi=True,
           ))
           # Register managed interface lifecycle with Root.
           self.addInterface(self.Net)

           # VC 0: register/memory path (for Device memBase)
           srp = rogue.protocols.srp.SrpV3()
           self.Net.application(dest=0) == srp

           # VC 1: data path to file writer
           self.add(pyrogue.utilities.fileio.StreamWriter(
               name='DataWriter'
           ))
           self.Net.application(dest=1) >> self.DataWriter.getChannel(1)

           # Example memory-mapped device:
           self.add(MyDevice(name='Dev', memBase=srp, offset=0x0))

Lifecycle notes
===============

- Root-managed mode:
  add ``UdpRssiPack`` to the tree and register it via ``Root.addInterface(...)``.
- Standalone mode:
  direct scripts can call wrapper ``start``/``stop`` commands (or ``_start`` /
  ``_stop``) when no Root lifecycle manager is present.
- Managed Interface Lifecycle reference:
  :ref:`pyrogue_tree_node_device_managed_interfaces`

Server mode (less common)
=========================

``server=True`` is typically used for software peer links, integration tests,
or cases where the remote endpoint must initiate the connection to Rogue.
This is not the common deployment for FPGA RSSI endpoints.

.. code-block:: python

   self.add(pyrogue.protocols.UdpRssiPack(
       name='Net',
       server=True,
       port=8192,
       jumbo=True,
       packVer=2,
       enSsi=True,
   ))
   self.addInterface(self.Net)

Available helper methods/commands
=================================

* ``application(dest)``:
  return packetizer application endpoint for a destination VC.
* ``countReset()``:
  reset RSSI counters.
* ``start`` / ``stop``:
  local commands exported by the wrapper device for link control.

Logging
=======

``UdpRssiPack`` itself is a PyRogue ``Device``, so any wrapper-level Python log
messages follow normal PyRogue logger naming. Most transport/protocol debug
output, however, comes from the underlying Rogue C++ modules:

- ``pyrogue.udp.Client`` / ``pyrogue.udp.Server``
- ``pyrogue.rssi.controller``
- ``pyrogue.packetizer.Controller``

Configuration example:

.. code-block:: python

   import rogue

   rogue.Logging.setFilter('pyrogue.udp', rogue.Logging.Debug)
   rogue.Logging.setFilter('pyrogue.rssi', rogue.Logging.Debug)
   rogue.Logging.setFilter('pyrogue.packetizer', rogue.Logging.Debug)

In practice, enable the underlying protocol loggers rather than relying on any
wrapper-level Python logging when debugging link behavior.

See also
========

* :ref:`protocols_rssi`
* :ref:`protocols_udp`
* :ref:`protocols_packetizer`
