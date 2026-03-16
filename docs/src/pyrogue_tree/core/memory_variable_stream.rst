.. _interfaces_python_memory_variable:

=======================
Variable Update Stream
=======================

:py:class:`~pyrogue.interfaces.stream.Variable` is a stream ``Master`` that
publishes PyRogue variable updates as YAML payload frames.

This is useful when you want to bridge tree updates into an existing stream
pipeline (for logging, forwarding, filtering, or transport) without polling
variables manually.

In the Core model, this adapter sits at the boundary between ``Variable``
update semantics and stream transport plumbing. The ``Root``/``Variable``
lifecycle still governs when values change; the adapter only packages those
changes into frames.

Typical behavior:

- Registers a variable listener on a ``Root``.
- Collects updates during a callback batch.
- Emits a YAML frame when the batch completes.
- Supports include/exclude group filtering.

The class can also emit a full YAML snapshot with ``streamYaml()``.

Data Format
===========

Frames contain UTF-8 YAML text. In batch-update mode, payload content is built
from the listener's accumulated ``{path: value}`` update map. In snapshot mode,
payload content comes from ``Root.getYaml(readFirst=False, ...)``.

The default ``excGroups=['NoStream']`` means Variables in the ``NoStream``
group are not emitted unless you override filtering.

Typical Integration Pattern
===========================

.. code-block:: python

   import pyrogue as pr
   import pyrogue.interfaces.stream as pis
   import pyrogue.utilities.fileio as puf

   class MyRoot(pr.Root):
       def __init__(self, **kwargs):
           super().__init__(**kwargs)

           # Emit variable updates as YAML frames.
           cfg_stream = pis.Variable(root=self, incGroups=None, excGroups=['NoStream'])

           # Record configuration/update frames on channel 1.
           self._writer = puf.StreamWriter(configStream={1: cfg_stream}, rawMode=True)
           self.add(self._writer)

           # Optional one-shot full snapshot frame.
           cfg_stream.streamYaml()

Operational Notes
=================

- Use group filters to limit update volume on large trees.
- Prefer event-driven updates over periodic full snapshots for efficiency.
- Snapshot mode does not force hardware reads before serialization.

Related topics
==============

- Variable behavior and grouping: :doc:`/pyrogue_tree/core/variable`
- Stream topology and transport flow: :doc:`/stream_interface/index`

API reference
=============

See :doc:`/api/python/rogue/interfaces/stream/variable` for generated API details.

Related Topics
==============

- Stream connection patterns: :doc:`/stream_interface/connecting`
- Frame send/receive APIs: :doc:`/stream_interface/sending` and :doc:`/stream_interface/receiving`
- Device and Variable behavior in the tree: :doc:`/pyrogue_tree/core/index`
