.. _pyrogue_tree_node_variable_local_variable:

=============
LocalVariable
=============

:py:class:`~pyrogue.LocalVariable` is the right choice when the value belongs
to Python logic rather than to a hardware register. It is still a normal
``Variable`` in the tree, so it can participate in GUIs, polling, formatting,
limits, and remote access, but its storage and behavior stay local to the
application.

Typical use cases:

* Software state or configuration values
* Values produced by helper libraries or external APIs
* GUI-facing controls that should update Python-owned state
* Operator-visible status derived from software components rather than from
  memory-mapped hardware

When To Use LocalVariable
=========================

Use ``LocalVariable`` when the tree should expose a value, but there is no
hardware address that should be read or written for that value.

That makes it the natural companion to ``RemoteVariable``:

* ``RemoteVariable`` exposes memory-mapped hardware state
* ``LocalVariable`` exposes software-owned state
* ``LinkVariable`` exposes a derived view layered on top of other Variables

Examples of good ``LocalVariable`` candidates include run-state flags, file
paths, software counters, cached measurements from another library, and tuning
values that are meaningful to the application even though they are not direct
register fields.

What You Usually Set
====================

Most ``LocalVariable`` definitions use the shared Variable parameters from
:doc:`/pyrogue_tree/core/variable`, plus a small set of local-specific ones:

* ``value`` for a directly stored Python-owned value.
* ``localGet`` to fetch the current value from application state.
* ``localSet`` to push a new value into application state.
* ``pollInterval`` when the local value should be refreshed periodically.

For simple access, ``localGet`` and ``localSet`` are not required. If the
Variable should just store a Python-owned value directly, ``value=...`` is
enough on its own.

How Typing Works
================

For ``LocalVariable``, the ``value=`` argument does two jobs:

* It provides the initial stored value.
* It establishes the Variable's native Python type.

In the current implementation, ``BaseVariable`` records ``type(value)`` as the
native type when ``value`` is provided. That means the seed value is the main
type anchor for normal ``LocalVariable`` usage.

Examples:

* ``value=False`` makes the Variable behave like a boolean-backed value.
* ``value=0`` makes it integer-backed.
* ``value=''`` makes it string-backed.
* ``value=np.array([...])`` makes it array-backed and also captures the array
  dtype and shape for ``typeStr``.

Important implications:

* ``LocalVariable`` does not automatically coerce later writes to match the
  seed type.
* A type mismatch currently produces a warning during ``set()``, not an
  exception.
* ``typeStr`` is display metadata; it does not enforce conversion by itself.

If you define a callback-only ``LocalVariable`` with ``localGet`` and no
``value``, the Variable can still work, but PyRogue does not have a seed value
to infer the native type from up front. In that case, providing a sensible
``value=`` is usually the clearest choice unless you intentionally want the
type to be discovered lazily.

For boolean values, there is one extra convenience: when ``value`` is a
``bool`` and no explicit ``enum`` is supplied, PyRogue automatically creates a
``{False: 'False', True: 'True'}`` enum for display.

Callbacks And Value Ownership
=============================

``LocalVariable`` can either hold a value directly or act as a live view over
some other Python object through callbacks.

If you only need direct stored access, skip the callbacks and provide
``value=...``. Add ``localGet`` and ``localSet`` only when the Variable should
proxy some other application state or behavior.

The optional callbacks are:

* ``localGet`` to produce the current value when the Variable is read
* ``localSet`` to apply a new value when the Variable is written

In the current implementation, the callback wrappers support keyword arguments
matching:

* ``localGet(dev=None, var=None)``
* ``localSet(value, dev=None, var=None, changed=None)``

The callback may accept any subset of those names. In practice, many
``LocalVariable`` instances use simple callables that only take ``value`` or
no explicit arguments at all.

This makes ``LocalVariable`` useful for two common patterns:

* A stored software value that PyRogue owns directly
* A thin tree-facing wrapper around application state owned elsewhere

Design guidance:

* Keep callbacks deterministic and low-latency
* Avoid long blocking operations in ``localGet`` when the Variable is polled
* Make side effects in ``localSet`` explicit and idempotent when possible
* Use ``LocalCommand`` instead when the interaction is really an action rather
  than a persistent value

Example: software-owned state
=============================

.. code-block:: python

   import pyrogue as pr

   class MyDevice(pr.Device):
       def __init__(self, **kwargs):
           super().__init__(**kwargs)
           self._is_running = False

           self.add(pr.LocalVariable(
               name='IsRunning',
               mode='RW',
               value=self._is_running,
               localGet=lambda: self._is_running,
               localSet=self._set_is_running,
           ))

       def _set_is_running(self, value):
           self._is_running = bool(value)

In this pattern, the tree shows one stable ``Variable`` interface while the
actual value is still owned by Python application state.

More Example Patterns
=====================

String-backed application setting
---------------------------------

This is a common pattern for software configuration such as file paths,
hostnames, or operator-entered labels.

.. code-block:: python

   import pyrogue as pr

   class FileWriter(pr.Device):
       def __init__(self, **kwargs):
           super().__init__(**kwargs)

           self.add(pr.LocalVariable(
               name='OutputPath',
               mode='RW',
               value='',
               description='Destination path for captured data',
           ))

Here, ``value=''`` makes the Variable string-backed from the start.

Polled status from a helper library
-----------------------------------

This pattern is common in GitHub projects built on PyRogue: a local counter or
status value is exposed read-only, refreshed by ``localGet``, and polled on an
interval. One concrete example is the ``FrameCnt``-style counters used in the
PySMuRF ``FrameStatistics`` device.

.. code-block:: python

   import pyrogue as pr

   class Stats(pr.Device):
       def __init__(self, helper, **kwargs):
           super().__init__(**kwargs)
           self._helper = helper

           self.add(pr.LocalVariable(
               name='FrameCount',
               mode='RO',
               value=0,
               typeStr='UInt64',
               pollInterval=1,
               localGet=self._helper.get_frame_count,
           ))

The ``value=0`` seed makes the Variable integer-backed, while ``typeStr`` lets
the tree present a more specific label to users.

Read-write wrapper over external application state
--------------------------------------------------

This is the pattern to use when the tree should expose a live control surface
for an object owned by another Python library.

.. code-block:: python

   import pyrogue as pr

   class Processor(pr.Device):
       def __init__(self, engine, **kwargs):
           super().__init__(**kwargs)
           self._engine = engine

           self.add(pr.LocalVariable(
               name='Disable',
               mode='RW',
               value=False,
               localSet=lambda value: self._engine.set_disable(value),
               localGet=self._engine.get_disable,
           ))

This is also a common real-world GitHub pattern: the Variable gives GUIs and
scripts a normal tree-facing boolean while the actual state lives in another
software object.

What To Explore Next
====================

* Hardware-backed Variables: :doc:`/pyrogue_tree/core/remote_variable`
* Linked Variables: :doc:`/pyrogue_tree/core/link_variable`
* General Variable behavior: :doc:`/pyrogue_tree/core/variable`

API Reference
=============

See :doc:`/api/python/pyrogue/localvariable` for generated API details.
