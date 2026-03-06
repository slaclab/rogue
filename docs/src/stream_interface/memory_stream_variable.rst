.. _interfaces_python_memory_variable:

=======================
Variable Update Stream
=======================

:py:class:`~pyrogue.interfaces.stream.Variable` is a stream ``Master`` that
publishes PyRogue variable updates as YAML payload frames.

This is useful when you want to bridge tree updates into an existing stream
pipeline (for logging, forwarding, filtering, or transport) without polling
variables manually.

Typical behavior:

- Registers a variable listener on a ``Root``.
- Collects updates during a callback batch.
- Emits a YAML frame when the batch completes.
- Supports include/exclude group filtering.

The class can also emit a full YAML snapshot with ``streamYaml()``.

API reference
=============

See :doc:`/api/python/interfaces_stream_variable` for generated API details.
