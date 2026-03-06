.. _protocols_network:

===============
Network Wrapper
===============

This page documents the PyRogue network helper classes implemented in
``python/pyrogue/protocols/_Network.py``. For RSSI protocol behavior and stack
internals, see :ref:`protocols_rssi`.

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
  choose server mode (``True``) or client mode (``False``). Typical FPGA
  register/data links use ``False``.
* ``host``/``port``:
  remote endpoint for client mode, or bind port for server mode.
* ``jumbo``:
  enable jumbo-MTU path assumptions in UDP setup.
* ``packVer``:
  packetizer version, ``1`` or ``2``.
* ``enSsi``:
  enable SSI handling in packetizer.
* ``wait``:
  in client mode, wait for RSSI link-up during startup.
* ``defaults`` (via ``kwargs``):
  optional RSSI parameter overrides such as ``locMaxBuffers``,
  ``locCumAckTout``, ``locRetranTout``, ``locNullTout``,
  ``locMaxRetran``, ``locMaxCumAck``.

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

           self.add(pyrogue.protocols.UdpRssiPack(
               name='Net',
               server=False,
               host='10.0.0.5',
               port=8192,
               jumbo=True,
               packVer=2,
               enSsi=True,
           ))
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
  local commands exported by the wrapper device.

See also
========

* :ref:`protocols_rssi`
* :ref:`protocols_udp`
* :ref:`protocols_packetizer`
