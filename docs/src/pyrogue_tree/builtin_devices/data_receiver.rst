.. _pyrogue_tree_node_device_datareceiver:

=========================
DataReceiver Device Class
=========================

:py:class:`~pyrogue.DataReceiver` is a device/stream-slave hybrid used to
accept incoming frames and expose them through PyRogue variables. It combines
a normal tree-facing ``Device`` with a Rogue stream ``Slave`` endpoint. In the
current implementation it:

* Counts frames, bytes, and frame errors
* Stores latest payload in ``Data``
* Toggles ``Updated`` when new data arrives
* Supports ``RxEnable`` gating

That makes it a useful bridge when stream traffic should update Variables,
status fields, or application-specific decoded results in the tree.

When To Use DataReceiver
========================

Use ``DataReceiver`` when incoming stream frames should be decoded or reflected
into PyRogue Variables.

Common fits include:

* Debug or monitoring receivers that expose the latest payload
* Protocol-specific decoder devices that unpack frame contents into multiple
  Variables
* Small live-analysis nodes that update status or derived values as frames
  arrive

What You Usually Set
====================

Most ``DataReceiver`` definitions revolve around:

* ``typeStr`` for the exposed ``Data`` Variable type
* ``hideData`` when the raw payload Variable should stay hidden
* ``value`` for the initial payload container
* ``enableOnStart`` for whether ``RxEnable`` should come up enabled at start

The built-in ``Data`` ``LocalVariable`` is created with ``typeCheck=False`` so
subclasses can publish decoded objects without triggering ``LocalVariable``
type errors.

In many practical subclasses, the main customization is not the constructor
arguments but the ``process(frame)`` override.

Subclassing And Override Points
===============================

In practice, subclassing is the normal way to use ``DataReceiver``.

The default ``process(frame)`` implementation copies the payload into the
``Data`` Variable and sets ``Updated=True``. Real applications often override
that method to parse the payload into more meaningful Variables.

Important behaviors to keep in mind:

* ``_acceptFrame()`` ignores frames when the device is not running or when
  ``RxEnable`` is false.
* Frame, byte, and error counters are maintained before ``process(frame)`` is
  called.
* ``process(frame)`` runs while the frame lock is held.
* The default class also supports ``source >> receiver`` and
  ``receiver << source`` stream connection syntax.

Concrete Example
================

One common pattern is to subclass ``DataReceiver``, add decoded result
Variables, and unpack specific fields from the incoming payload.

.. code-block:: python

   import numpy as np
   import pyrogue as pr

   class HeaderPayloadRx(pr.DataReceiver):
       def __init__(self, **kwargs):
           super().__init__(hideData=True, **kwargs)

           self.add(pr.LocalVariable(
               name='Header',
               mode='RO',
               value=0,
               description='Decoded 32-bit header word',
           ))

       def process(self, frame):
           # DataReceiver calls this with the frame lock already held.
           data = frame.getNumpy()

           # Example protocol: first 4 bytes are a header, rest is payload.
           header = int.from_bytes(bytearray(data[:4]), byteorder='little', signed=False)
           payload = np.array(data[4:], dtype=np.uint8)

           # Publish both the decoded header and the latest payload view.
           self.Header.set(header, write=True)
           self.Data.set(payload, write=True)
           self.Updated.set(True, write=True)

This matches the way many real ``DataReceiver`` subclasses are used: the raw
frame arrives on the stream side, but the tree exposes a more structured view
for GUIs, scripts, or live monitoring tools.

The base class creates these built-in Variables:

* ``RxEnable`` for gating frame acceptance
* ``FrameCount``, ``ErrorCount``, and ``ByteCount`` for stream statistics
* ``Updated`` as a tree-visible "new data arrived" flag
* ``Data`` as the latest payload container

The ``Data`` Variable is excluded from ``NoState``, ``NoStream``, and
``NoConfig`` by default, which is usually what you want for rapidly changing
payload data that should not behave like configuration or normal state export.

Related Topics
==============

* Stream replay source: :doc:`/built_in_modules/utilities/fileio/reading`
* Stream capture to file: :doc:`/built_in_modules/utilities/fileio/writing`
* Stream receiving model: :doc:`/stream_interface/receiving`
* Built-in module catalog beyond top-level ``pyrogue`` Devices: :doc:`/built_in_modules/index`

API Reference
=============

See :doc:`/api/python/pyrogue/datareceiver` for generated API details.
