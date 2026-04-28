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
:doc:`/api/python/rogue/protocols/rocev2/server`) and adds the
``surf.ethernet.roce._RoceEngine.RoceEngine`` child device for the
FPGA-side metadata-bus handshake.

The 15 ``LocalVariable`` status/configuration fields (``FpgaIp``,
``FpgaGid``, ``HostQpn``, ``HostGid``, ``MrAddr``, ``MrRkey``,
``RxFrameCount``, ``RxByteCount``, ``ConnectionState``, ``MaxPayload``,
``RxQueueDepth``, ``HostRqPsn``, ``HostSqPsn``, ``FpgaQpn``,
``FpgaLkey``) are auto-rendered by ``autoclass`` below from the
docstrings in ``python/pyrogue/protocols/_RoCEv2.py``.

.. autoclass:: pyrogue.protocols.RoCEv2Server
   :members:
   :member-order: bysource
   :inherited-members:
