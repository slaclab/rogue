.. _pyrogue_tree_node_command_local_command:

============
LocalCommand
============

:py:class:`~pyrogue.LocalCommand` is the right choice when a tree action should
run Python logic rather than write a hardware command register. It gives the
tree a normal ``Command`` node, but the implementation stays in software.

Typical use cases:

* Orchestration steps such as initialization or reset sequences
* File and configuration workflows
* Helper actions that combine multiple Variable or Device operations
* Operator-visible procedures that do not map to one hardware strobe bit

When To Use LocalCommand
========================

Use ``LocalCommand`` when the important interaction is a procedure rather than
state.

That makes it the software-defined counterpart to ``RemoteCommand``:

* ``LocalCommand`` runs Python-defined behavior
* ``RemoteCommand`` performs an action through a hardware-backed write path

If the action really lives in a memory-mapped register field, especially a
reset pulse or trigger bit, ``RemoteCommand`` is usually the better fit. If
the action is "run this workflow", ``LocalCommand`` usually reads better in
the tree.

What You Usually Set
====================

Most ``LocalCommand`` definitions use the shared command behavior from
:doc:`/pyrogue_tree/core/command`, plus a small set of parameters that shape
the local action itself:

* ``function`` for the Python callback to execute
* ``value`` for the default command argument, when the command takes one
* ``retValue`` when the command returns a value and you want the return type to
  be described clearly
* ``description`` for operator-facing help text
* ``hidden`` and ``groups`` for presentation and workflow policy

How Invocation Works
====================

``LocalCommand`` is an alias-style specialization of
:py:class:`~pyrogue.BaseCommand`. The callback wrapper can supply any subset of
these keyword arguments:

* ``root``
* ``dev``
* ``cmd``
* ``arg``

That means the callback can be as small or as explicit as the job requires. A
simple no-argument helper works fine, but so does a callback that needs access
to the surrounding ``Device``, the ``Root``, the command node itself, or a
user-supplied argument.

The common invocation forms are:

* ``cmd()``
* ``cmd(arg)``
* ``cmd.call(arg)``

If the callback accepts ``arg``, then ``value=...`` becomes the command's
default argument. Calling the command without an explicit argument uses that
stored default.

Example: device-local procedure
===============================

.. code-block:: python

   import pyrogue as pr

   class MyDevice(pr.Device):
       def __init__(self, **kwargs):
           super().__init__(**kwargs)

           self.add(pr.LocalCommand(
               name='SoftReset',
               description='Run the device software reset sequence',
               function=self._soft_reset,
           ))

       def _soft_reset(self):
           # Device-specific software sequence
           self.countReset()
           self.initialize()

This is the simplest ``LocalCommand`` pattern: expose a named tree action and
back it with ordinary Python logic.

Example: command with an argument
=================================

Many ``LocalCommand`` nodes are thin wrappers around a higher-level software
workflow that needs one input value, such as a file path, a numeric count, or
an option string.

.. code-block:: python

   import pyrogue as pr

   class ConfigRoot(pr.Root):
       def __init__(self, **kwargs):
           super().__init__(**kwargs)

           self.add(pr.LocalCommand(
               name='LoadConfig',
               description='Load configuration from a YAML file',
               value='',
               function=self._load_config,
           ))

       def _load_config(self, arg):
           self.loadYaml(name=arg, writeEach=False, modes=['RW', 'WO'])

Here, ``value=''`` establishes the default argument shape and lets the command
be called either as ``LoadConfig('/path/file.yml')`` or by reusing the stored
default argument.

Using The ``@self.command`` Decorator
=====================================

``Device.command()`` provides a compact way to define a ``LocalCommand`` inline
next to the logic it wraps.

In the current implementation:

* The decorator creates ``LocalCommand(function=...)`` under the hood.
* If you do not pass ``name=...``, the function name becomes the command name.
* The decorated function may accept any subset of ``root``, ``dev``, ``cmd``,
  and ``arg``.

This is often the cleanest form for small device-local procedures because the
tree-facing command and the Python logic are defined together.

.. code-block:: python

   import pyrogue as pr

   class MyDevice(pr.Device):
       def __init__(self, **kwargs):
           super().__init__(**kwargs)

           @self.command(description='Capture the current state to disk', value='')
           def SaveSnapshot(arg):
               self.saveYaml(name=arg, modes=['RW', 'RO', 'WO'])

The decorator form still creates a ``LocalCommand(function=...)`` under the
hood. Use whichever form reads more clearly in the surrounding code.

It is also a good fit for callbacks that want explicit access to the command
context:

.. code-block:: python

   import pyrogue as pr

   class MyDevice(pr.Device):
       def __init__(self, **kwargs):
           super().__init__(**kwargs)

           @self.command(description='Report the current device path')
           def ReportPath(cmd):
               print(f'Command path: {cmd.path}')

           @self.command(value=1, description='Generate a requested number of frames')
           def GenerateFrames(arg, dev):
               for _ in range(arg):
                   dev._gen_frame()

These examples show the main decorator patterns: a default-name command, a
callback that uses the command object itself, and a callback that uses both an
argument and the surrounding ``Device``.

Built-In Command Functions
==========================

PyRogue includes a small set of built-in command helper functions on
:py:class:`~pyrogue.BaseCommand`, but those helpers are mainly useful for
commands that have a meaningful backing value or write path.

In practice:

* ``LocalCommand`` usually uses a custom Python callback.
* ``BaseCommand.nothing`` is the main built-in helper that is naturally useful
  for ``LocalCommand`` itself.
* The write-oriented helpers such as ``touchOne`` and ``toggle`` are discussed
  in :doc:`/pyrogue_tree/core/remote_command`, where they are used most often.

``nothing`` is a no-op handler. It is occasionally useful as a placeholder
while bringing up a tree shape or when a command node should exist before its
real implementation is attached.

.. code-block:: python

   import pyrogue as pr

   class MyDevice(pr.Device):
       def __init__(self, **kwargs):
           super().__init__(**kwargs)

           self.add(pr.LocalCommand(
               name='ReservedAction',
               description='Placeholder command for a future software action',
               function=pr.BaseCommand.nothing,
           ))

What To Explore Next
====================

* Hardware-backed commands: :doc:`/pyrogue_tree/core/remote_command`
* Shared command behavior: :doc:`/pyrogue_tree/core/command`
* Tree-level placement and decorators: :doc:`/pyrogue_tree/core/device`

API Reference
=============

``LocalCommand`` is an alias-style specialization of
:py:class:`~pyrogue.BaseCommand`.

For full API documentation, see:

* :doc:`/api/python/pyrogue/basecommand`
* :doc:`/pyrogue_tree/core/command`
