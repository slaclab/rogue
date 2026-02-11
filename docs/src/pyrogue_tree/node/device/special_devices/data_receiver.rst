.. _pyrogue_tree_node_device_datareceiver:

=========================
DataReceiver Device Class
=========================

:py:class:`pyrogue.DataReceiver` is a device/stream-slave hybrid used to accept
incoming frames and expose them through PyRogue variables.

Core behavior:

* counts frames, bytes, and frame errors
* stores latest payload in ``Data``
* toggles ``Updated`` when new data arrives
* supports ``RxEnable`` gating

Override :py:meth:`pyrogue.DataReceiver.process` to customize payload parsing.

DataReceiver Class Documentation
================================

.. autoclass:: pyrogue.DataReceiver
   :members:
   :member-order: bysource
   :inherited-members:
