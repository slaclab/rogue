.. _interfaces_python_memory_variable:

=======================
Variable Update Stream
=======================

:py:class:`~pyrogue.interfaces.stream.Variable` is a stream ``Master`` that
publishes PyRogue Variable updates as YAML payload frames.

This is useful when you want to bridge tree updates into an existing stream
pipeline (for logging, forwarding, filtering, or transport) without polling
variables manually.

In the Core model, this adapter sits at the boundary between tree-update
semantics and stream transport plumbing. ``Root`` and ``Variable`` still
govern when values change. The stream adapter only listens for those updates,
packages them into YAML, and sends them as stream Frames.

How It Works
============

When the stream object is constructed, it registers a Root variable listener
with ``root.addVarListener(func=..., done=...)``.

At runtime:

* Each Variable update callback contributes one entry to an internal
  path-keyed update map.
* The callback receives a :py:class:`pyrogue.VariableValue` snapshot, not just
  a raw Python value.
* When the Root finishes the current update batch and calls the listener's
  ``done`` hook, the stream emits one YAML Frame containing the accumulated
  updates.

This batching matters. A multi-Variable operation wrapped in
``Root.updateGroup()`` is normally emitted as one stream Frame rather than a
burst of one-frame-per-variable traffic.

The class can also emit a full YAML snapshot on demand with ``streamYaml()``.

Data Format
===========

Frames contain UTF-8 YAML text. In batch-update mode, payload content is built
from the listener's accumulated ``{path: VariableValue}`` update map. The YAML
representer serializes each ``VariableValue`` to its current value, so the
result is effectively a flat map of full Variable paths to values.

In snapshot mode, payload content comes from
``Root.getYaml(readFirst=False, ...)``. That means snapshot frames use the
normal tree-shaped YAML structure rooted at the ``Root`` name.

In other words:

* Update frames are delta-style and path-keyed.
* ``streamYaml()`` emits a full subtree snapshot.

Neither mode forces a hardware read by itself. ``streamYaml()`` explicitly uses
``readFirst=False``, so it serializes the currently cached tree state.

Group Filtering
===============

The constructor accepts the same include/exclude filtering model used by Root
variable listeners:

* ``incGroups`` limits updates to Variables in selected groups.
* ``excGroups`` suppresses Variables in selected groups.

The default ``excGroups=['NoStream']`` means Variables in the built-in
``NoStream`` group are omitted unless you override that policy. This is the
standard way to keep noisy, internal, or operator-irrelevant Variables out of
configuration/status streams.

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

This pattern is common when a design already has a Rogue stream pipeline and
you want configuration or status updates to flow through the same transport.

When To Use It
==============

Use the stream adapter when the important problem is transport integration:

* Forwarding tree updates into an existing stream path.
* Recording configuration or state changes alongside other stream data.
* Feeding a downstream logging, bridging, or filtering stage that already
  speaks Rogue stream Frames.

Prefer event-driven updates over periodic full snapshots when you want lower
traffic and better temporal correlation to actual tree changes. Use
``streamYaml()`` when a consumer needs a complete baseline frame, such as at
file open or stream startup.

What To Explore Next
====================

* Variable behavior and grouping policy: :doc:`/pyrogue_tree/core/variable`
* Group filters such as ``NoStream``: :doc:`/pyrogue_tree/core/groups`

Related Topics
==============

* Stream topology and transport flow: :doc:`/stream_interface/index`
* Stream connection patterns: :doc:`/stream_interface/connecting`
* Frame send/receive APIs: :doc:`/stream_interface/sending` and :doc:`/stream_interface/receiving`

API Reference
=============

See :doc:`/api/python/rogue/interfaces/stream/variable` for generated API details.
