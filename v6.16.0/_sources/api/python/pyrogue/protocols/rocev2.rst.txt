.. _api_python_protocols_rocev2server:

============
RoCEv2Server
============

For conceptual usage, see:

- :doc:`/built_in_modules/protocols/rocev2/index`
- :doc:`/pyrogue_tree/core/device`

Implementation
--------------

This Python API is implemented directly in PyRogue. It is a thin
``pyrogue.Device`` wrapper that owns a Boost.Python-exported
``rogue.protocols.rocev2.Server`` (see
:doc:`/api/python/rogue/protocols/rocev2/server`). The FPGA-side
metadata-bus handshake lives in surf
(``surf.ethernet.roce.RoCEv2Engine``); the application ``Root`` drives
the host↔FPGA bring-up (``getHostParams`` → ``engine.setupConnection``
→ ``completeConnection``) — it is no longer a child device of this
server.

The 15 ``LocalVariable`` status/configuration fields (``FpgaIp``,
``FpgaGid``, ``HostQpn``, ``HostGid``, ``HostIp``, ``MrAddr``,
``MrRkey``, ``RxFrameCount``, ``RxByteCount``, ``MaxPayload``,
``RxQueueDepth``, ``HostRqPsn``, ``HostSqPsn``, ``FpgaQpn``,
``FpgaLkey``) are auto-rendered by ``autoclass`` below from the
docstrings in ``python/pyrogue/protocols/_RoCEv2.py``.

.. autoclass:: pyrogue.protocols.RoCEv2Server
   :members:
   :member-order: bysource
   :inherited-members:

Configuration dataclasses
-------------------------

``RoCEv2Server`` takes its host-NIC bring-up config as a
:class:`~pyrogue.protocols.RoCEv2ServerCfg`. The transport / QP-tuning knobs
shared between the FPGA ``engine.setupConnection()`` and the host
``server.completeConnection()`` calls are bundled in
:class:`~pyrogue.protocols.RoCEv2TransportCfg`. The ``pmtu`` and
``minRnrTimer`` fields take values from the :class:`~pyrogue.protocols.RoCEv2Mtu`
and :class:`~pyrogue.protocols.RoCEv2RnrTimer` enums.

.. autoclass:: pyrogue.protocols.RoCEv2ServerCfg
   :members:

.. autoclass:: pyrogue.protocols.RoCEv2TransportCfg
   :members:

.. autoclass:: pyrogue.protocols.RoCEv2Mtu
   :members:
   :undoc-members:

.. autoclass:: pyrogue.protocols.RoCEv2RnrTimer
   :members:
   :undoc-members:
