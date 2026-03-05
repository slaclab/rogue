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

Example
=======

.. code-block:: python

   import numpy as np
   import pyrogue as pr

   class HeaderPayloadRx(pr.DataReceiver):
       def process(self, frame):
           # Example: first 4 bytes header, remaining payload
           data = frame.getNumpy()

           header = int.from_bytes(bytearray(data[:4]), byteorder='little', signed=False)
           payload = np.array(data[4:], dtype=np.uint8)

           # Store payload in Data and mark update
           self.Data.set(payload, write=True)
           self.Updated.set(True, write=True)

           # Optional: project-specific handling using parsed header
           _ = header

DataReceiver Class Documentation
================================

See :doc:`/api/python/datareceiver` for generated API details.
