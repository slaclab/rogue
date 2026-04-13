.. _pyrogue_tree_node_command_remote_command:

=============
RemoteCommand
=============

:py:class:`~pyrogue.RemoteCommand` is the right choice when a tree action is
really a hardware-backed write, but should read like a command rather than like
persistent state. It combines ``Command`` invocation behavior with
``RemoteVariable`` register mapping.

Typical use cases include:

* Triggering a hardware reset register
* Pulsing a self-clearing strobe bit
* Touching a command register with a fixed value
* Issuing a posted write when the command bit should not be read back

When To Use RemoteCommand
=========================

Use ``RemoteCommand`` when the tree should expose "do this now", but the
implementation still lives in a memory-mapped field.

This is often a better fit than a writable ``RemoteVariable`` for reset pulses,
update strobes, trigger bits, apply bits, and other actions that are not meant
to represent persistent operator-managed state.

What You Usually Set
====================

Most ``RemoteCommand`` definitions use the shared command behavior from
:doc:`/pyrogue_tree/core/command` together with the remote mapping parameters
that describe the hardware field:

* ``offset`` for the register address
* ``bitSize`` and ``bitOffset`` for the command field
* ``base`` for the underlying data model
* ``function`` for the command action policy
* ``value`` when the command has a meaningful default argument

In practice, ``function`` is the parameter that most strongly determines what
invoking the command actually does.

How RemoteCommand Works
=======================

``RemoteCommand`` is still a ``Command`` node, so users invoke it as
``cmd()`` or ``cmd(arg)``. Under the hood, the command callback receives the
normal command wrapper keywords:

* ``root``
* ``dev``
* ``cmd``
* ``arg``

For ``RemoteCommand``, the callback usually operates by calling methods on
``cmd`` such as:

* ``cmd.set(value)``
* ``cmd.get(read=True)``
* ``cmd.post(value)``

That is why the built-in helper functions work so well here: they are small
command policies layered on top of the mapped register field.

Built-In Command Functions
==========================

PyRogue includes several built-in helper functions on
:py:class:`~pyrogue.BaseCommand` that are commonly passed as the ``function``
for a ``RemoteCommand``.

In code, these are often referenced as either ``pr.BaseCommand.touchOne`` or
``pr.RemoteCommand.touchOne`` because ``RemoteCommand`` inherits from
``BaseCommand``.

The most important ones are:

* ``toggle`` writes ``1`` and then ``0``
* ``touchOne`` writes ``1``
* ``touchZero`` writes ``0``
* ``touch`` writes the supplied argument, or ``1`` when no argument is given
* ``postedTouchOne`` posts ``1`` without the normal blocking write path
* ``postedTouchZero`` posts ``0`` without the normal blocking write path
* ``postedTouch`` posts the supplied argument
* ``createTouch(value)`` creates a helper that always writes one fixed value
* ``createPostedTouch(value)`` creates a posted helper for one fixed value
* ``createToggle(values)`` creates a helper that writes a configured sequence
  of values
* ``setArg`` writes the supplied argument
* ``setAndVerifyArg`` writes the supplied argument and checks that it reads
  back correctly
* ``read`` performs a read of the mapped command field

The right helper depends on the hardware semantics.

``toggle`` For Pulse-Style Commands
-----------------------------------

Use ``toggle`` when the action is represented by a ``1 -> 0`` pulse.

.. code-block:: python

   import pyrogue as pr

   class MyDevice(pr.Device):
       def __init__(self, **kwargs):
           super().__init__(**kwargs)

           self.add(pr.RemoteCommand(
               name='CountReset',
               description='Pulse the hardware counter reset bit',
               offset=0x00,
               bitSize=1,
               bitOffset=0,
               base=pr.UInt,
               function=pr.BaseCommand.toggle,
           ))

This is one of the most common ``RemoteCommand`` patterns in real hardware
trees.

``touchOne`` And ``touchZero`` For Fixed-Value Writes
-----------------------------------------------------

Use these when the hardware action is a single fixed write rather than a pulse
sequence.

.. code-block:: python

   import pyrogue as pr

   class MyDevice(pr.Device):
       def __init__(self, **kwargs):
           super().__init__(**kwargs)

           self.add(pr.RemoteCommand(
               name='DeviceUpdate',
               description='Latch recently written configuration values',
               offset=0x3FC,
               bitSize=1,
               base=pr.UInt,
               function=pr.BaseCommand.touchZero,
           ))

``touchOne`` is similarly common for self-clearing strobe bits that trigger on
the write of ``1``.

``touch`` For Argument-Driven Writes
------------------------------------

Use ``touch`` when the command should write the caller-provided argument.

.. code-block:: python

   import pyrogue as pr

   class MyDevice(pr.Device):
       def __init__(self, **kwargs):
           super().__init__(**kwargs)

           self.add(pr.RemoteCommand(
               name='FreezeDebug',
               description='Write the debug freeze control field',
               offset=0xA0,
               bitSize=1,
               base=pr.UInt,
               value=1,
               function=pr.BaseCommand.touch,
           ))

Calling ``FreezeDebug(1)`` writes ``1``. Calling ``FreezeDebug(0)`` writes
``0``. If the caller omits the argument, ``touch`` falls back to ``1``.

``postedTouch...`` For Posted Writes
------------------------------------

Use the posted variants when the hardware command should be issued through
``post()`` rather than the normal blocking write path.

.. code-block:: python

   import pyrogue as pr

   class MyDevice(pr.Device):
       def __init__(self, **kwargs):
           super().__init__(**kwargs)

           self.add(pr.RemoteCommand(
               name='FpgaReload',
               description='Request FPGA reload through a posted write',
               offset=0x104,
               bitSize=1,
               bitOffset=0,
               base=pr.UInt,
               function=pr.BaseCommand.postedTouchOne,
           ))

This pattern is useful when the command bit is self-clearing, has unusual
readback behavior, or should not participate in the normal write/verify path.

``createTouch`` And ``createToggle`` For Captured Policies
----------------------------------------------------------

The ``create...`` helpers are factories that return command functions with a
captured fixed value or sequence. They are useful when the hardware protocol
does not match one of the standard one-line helpers directly.

.. code-block:: python

   import pyrogue as pr

   class MyDevice(pr.Device):
       def __init__(self, **kwargs):
           super().__init__(**kwargs)

           self.add(pr.RemoteCommand(
               name='SpecialKick',
               description='Write the required three-step kick sequence',
               offset=0x20,
               bitSize=8,
               base=pr.UInt,
               function=pr.BaseCommand.createToggle([0x5A, 0xA5, 0x00]),
           ))

Likewise, ``createTouch(0x81)`` is a compact way to define a command that
always writes ``0x81``. ``createPostedTouch(0x81)`` does the same thing
through ``post()`` instead of ``set()``.

``setArg`` And ``setAndVerifyArg`` For Argument-Carrying Commands
-----------------------------------------------------------------

These helpers are useful when the command node should behave like an explicit
command wrapper around a writable field.

.. code-block:: python

   import pyrogue as pr

   class MyDevice(pr.Device):
       def __init__(self, **kwargs):
           super().__init__(**kwargs)

           self.add(pr.RemoteCommand(
               name='StartAddress',
               description='Write the capture start address through a command node',
               offset=0x40,
               bitSize=32,
               base=pr.UInt,
               value=0,
               function=pr.BaseCommand.setAndVerifyArg,
           ))

This is less common than the strobe-style helpers, but it can be useful when
you want the tree surface to read like an action rather than like persistent
register state.

The ``read`` helper is also available, though it is more specialized. It is
mainly useful for diagnostic or synchronization cases where invoking the
command should explicitly perform a read of the mapped command field.

Custom Command Functions
========================

You are not limited to the built-in helpers. A custom callback is appropriate
when the hardware action needs a small amount of extra policy.

.. code-block:: python

   import pyrogue as pr

   class MyDevice(pr.Device):
       def __init__(self, **kwargs):
           super().__init__(**kwargs)

           self.add(pr.RemoteCommand(
               name='ReloadAtAddress',
               description='Write a reload request using the current address field',
               offset=0x104,
               bitSize=1,
               base=pr.UInt,
               function=lambda cmd: cmd.post(1),
           ))

Use a custom function when the command behavior is still simple but does not
fit one of the built-in helpers cleanly.

What To Explore Next
====================

* Software-defined commands: :doc:`/pyrogue_tree/core/local_command`
* Shared command behavior: :doc:`/pyrogue_tree/core/command`
* Hardware-backed Variables: :doc:`/pyrogue_tree/core/remote_variable`

API Reference
=============

See :doc:`/api/python/pyrogue/remotecommand` for generated API details.
