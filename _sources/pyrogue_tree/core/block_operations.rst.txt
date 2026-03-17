.. _pyrogue_tree_block_operations:

=======================
Device Block Operations
=======================

``Device`` provides a family of methods that traverse a tree and initiate or
check ``Block`` transactions:

* :py:meth:`~pyrogue.Device.writeBlocks`
* :py:meth:`~pyrogue.Device.verifyBlocks`
* :py:meth:`~pyrogue.Device.readBlocks`
* :py:meth:`~pyrogue.Device.checkBlocks`
* :py:meth:`~pyrogue.Device.writeAndVerifyBlocks`
* :py:meth:`~pyrogue.Device.readAndCheckBlocks`

These methods sit between the tree model and the lower-level ``Block``
transaction layer. They are used in three main ways:

* As the default path for bulk reads and writes across a subtree.
* As the per-Variable path used by many hardware-backed reads and writes.
* As the main override points when hardware needs custom sequencing.

Why These Methods Exist
=======================

PyRogue separates transaction initiation from transaction completion. That is
why these methods come in pairs and helper sequences rather than as one large
"do everything" call.

At a high level:

* ``writeBlocks`` initiates write transactions.
* ``verifyBlocks`` initiates verify transactions.
* ``readBlocks`` initiates read transactions.
* ``checkBlocks`` waits for initiated transactions to complete.

That split lets a ``Device`` issue many transactions first and then wait for
completion afterward. The composed helpers:

* ``writeAndVerifyBlocks``
* ``readAndCheckBlocks``

simply bundle the most common full flows on top of those same methods. In
practice, most readers only need two ideas first:

* The default bulk path is "issue transactions across this ``Device`` or
  subtree, then check them."
* These same methods are also the normal place to override sequencing when the
  hardware needs something more specific.

Default Full-Device Behavior
============================

When called without ``variable=...``, these methods operate on the current
``Device`` and, optionally, its child Devices.

The default traversal is simple:

1. Process the ``Block`` objects attached directly to the current ``Device``.
2. Recurse into child Devices if ``recurse=True``.

So the current ``Device`` goes first, and child Devices follow after that.
That is the baseline behavior that custom overrides either preserve or replace.

Ordering Rules
==============

Within that default traversal, the ordering is also defined.

Inside one ``Device``:

* Automatically built hardware-backed Blocks are created from Variables sorted
  by ``(offset, varBytes)``, so those Blocks are normally issued in
  address-oriented order.
* ``LocalVariable`` Blocks are appended as the Device walks its child Nodes, so
  they follow Node insertion order rather than address sorting.

For the Block-building process that creates that ordering, see
:doc:`/pyrogue_tree/core/block`.

For child Devices, the traversal follows add order. ``Node`` stores children
in an ``OrderedDict``, and ``Device`` recurses through
``self.devices.values()``.

So the default recursive flow is:

* This Device's Blocks first.
* Then child Devices in add order.

Single-Variable Behavior
========================

The same methods can also target one specific Variable by passing
``variable=...``.

That path does not perform full subtree traversal. Instead, it operates only on
the ``Block`` associated with that Variable. This is how many hardware-backed
per-Variable ``get`` and ``set`` paths reuse the same ``Device`` block methods
without turning into full-tree operations.

Common Usage Patterns
=====================

Most manual use of these APIs falls into one of three patterns: operate on a
subtree, operate on one Variable's backing ``Block``, or call a composed
helper when the full flow is what you actually want.

Read One Subtree
----------------

.. code-block:: python

   # Initiate reads across this Device subtree, then wait for completion.
   my_dev.readAndCheckBlocks(recurse=True)

This is the normal manual pattern when you want a current hardware snapshot of
one part of the tree.

Write And Verify One Subtree
----------------------------

.. code-block:: python

   # Force a full write/verify/check pass across this Device subtree.
   my_dev.writeAndVerifyBlocks(force=True, recurse=True)

This pattern is often useful for ADC and mixed-signal configuration, where a
command needs to push a complete known-good register set into hardware in one
step.

Target One Variable's ``Block``
-------------------------------

.. code-block:: python

   # Only issue a write for the Block backing one Variable.
   my_dev.writeBlocks(variable=my_dev.MyRegister, checkEach=True)
   my_dev.checkBlocks(variable=my_dev.MyRegister)

This is the manual form of the narrower path that hardware-backed per-Variable
operations use internally.

Composed Helpers
================

Two helpers cover the most common complete flows:

* ``writeAndVerifyBlocks(...)`` runs
  ``writeBlocks`` -> ``verifyBlocks`` -> ``checkBlocks``.
* ``readAndCheckBlocks(...)`` runs
  ``readBlocks`` -> ``checkBlocks``.

These helpers are often the clearest way to trigger a full operation from a
script, a command callback, or a one-shot configuration step. They are also a
good way to avoid open-coding the same multi-step sequence in many places.

How YAML Configuration Uses These Methods
=========================================

YAML configuration loading is one of the main places where users encounter
bulk block operations indirectly.

For ``Root.loadYaml(..., writeEach=False)`` and ``Root.setYaml(..., writeEach=False)``,
PyRogue first stages values into Variables with ``setDisp(..., write=False)``.
Only after that full YAML payload has been applied to the tree does Root
commit the configuration through its normal bulk write path.

In practice, that means YAML configuration uses the same transaction model
described on this page:

* Values are staged first.
* The resulting Block writes are issued across the tree.
* Verification and completion checks run through the normal bulk helpers.

So the YAML page should be read as "how the tree is described and matched,"
while this page remains the right place for "how the resulting hardware
transactions are issued and checked."

Two Root settings are especially relevant in that YAML-driven path:

* ``ForceWrite`` can force writes of non-stale Blocks during config apply.
* ``InitAfterConfig`` can trigger ``initialize()`` after the configuration has
  been committed.

Method Parameters
=================

The methods share a common shape, but the meaning of the parameters is easiest
to understand after the default traversal and common usage patterns are clear.
The most important controls are ``recurse``, ``variable``, ``checkEach``, and
for writes, ``force``.

``writeBlocks``
---------------

Signature:

.. code-block:: python

   writeBlocks(*, force=False, recurse=True, variable=None, checkEach=False, index=-1, **kwargs)

Important parameters:

* ``force``:
  Write even when the value is not marked stale.
* ``recurse``:
  Include child Devices when ``True``.
* ``variable``:
  Operate on one Variable's Block instead of the full Device subtree.
* ``checkEach``:
  Request per-transaction checking behavior instead of deferring checks.
* ``index``:
  Array index used for targeted Variable operations.
* ``**kwargs``:
  Passed through to the underlying transaction helpers.

``verifyBlocks``
----------------

Signature:

.. code-block:: python

   verifyBlocks(*, recurse=True, variable=None, checkEach=False, **kwargs)

Important parameters:

* ``recurse``:
  Include child Devices when ``True``.
* ``variable``:
  Verify only one Variable's Block.
* ``checkEach``:
  Request per-transaction checking behavior.
* ``**kwargs``:
  Passed through to the transaction helper.

``readBlocks``
--------------

Signature:

.. code-block:: python

   readBlocks(*, recurse=True, variable=None, checkEach=False, index=-1, **kwargs)

Important parameters:

* ``recurse``:
  Include child Devices when ``True``.
* ``variable``:
  Read only one Variable's Block.
* ``checkEach``:
  Request per-transaction checking behavior.
* ``index``:
  Array index used for targeted Variable reads.
* ``**kwargs``:
  Passed through to the transaction helper.

``checkBlocks``
---------------

Signature:

.. code-block:: python

   checkBlocks(*, recurse=True, variable=None, **kwargs)

Important parameters:

* ``recurse``:
  Include child Devices when ``True``.
* ``variable``:
  Check only one Variable's Block.
* ``**kwargs``:
  Passed through to the transaction helper.

Device-Wide ``checkEach`` Behavior
----------------------------------

The ``checkEach`` control exists at two levels.

At call time, ``writeBlocks``, ``verifyBlocks``, ``readBlocks``,
``writeAndVerifyBlocks``, and ``readAndCheckBlocks`` all accept a
``checkEach=...`` argument. That requests transaction-by-transaction checking
for that one operation.

At Device scope, the persistent control is ``forceCheckEach``. Each block
method combines the caller's argument with the Device setting:

.. code-block:: python

   checkEach = checkEach or self.forceCheckEach

So a Device can force per-transaction checking for all reads, writes, and
verifies by setting:

.. code-block:: python

   self.forceCheckEach = True

There is not a separate ``Device(..., checkEach=...)`` constructor argument in
this implementation. If a Device should always use this stricter behavior, set
``forceCheckEach`` in the subclass:

.. code-block:: python

   class MyDevice(pyrogue.Device):
       def __init__(self, **kwargs):
           super().__init__(**kwargs)
           self.forceCheckEach = True

This is useful when the hardware benefits from immediate acknowledgement of
each transaction instead of the default "issue many operations, then check
them" flow. One example is a board or front-end path where tight sequencing or
hardware-side backpressure makes deferred checking less desirable.

How To Override Properly
========================

The normal reason to override these methods is that the hardware needs extra
ordering around the default traversal. Before overriding, it helps to separate
two questions:

* Are you keeping the inherited traversal and just adding steps around it?
* Or are you intentionally replacing part of the inherited traversal order?

Common cases:

* A commit or apply strobe must be written after configuration registers.
* A page or bank select register must be set before reads or writes.
* A debug-freeze or capture gate must wrap a read sequence.
* Child Devices must be traversed in a hardware-specific order rather than the
  default add order.
* A subsystem needs to change the order in which some operations happen.

The general rule is:

* Keep the default traversal unless you intentionally need to replace it.
* Preserve the relevant keyword parameters.
* Add only the extra pre- or post-sequencing behavior you need.

The following examples move from the smallest override to the most structural
one.

Example: Post-Write Update Strobe
---------------------------------

This pattern is often needed for ADC and similar devices whose configuration
registers are shadowed internally and do not take effect until a separate
update strobe is written:

.. code-block:: python

   class MyDevice(pyrogue.Device):
       def __init__(self, **kwargs):
           super().__init__(**kwargs)
           self.add(pyrogue.RemoteCommand(
               name='DeviceUpdate',
               offset=0x3FC,
               function=pyrogue.BaseCommand.touchZero,
           ))

       def writeBlocks(self, force=False, recurse=True, variable=None, checkEach=False, index=-1, **kwargs):
           super().writeBlocks(
               force=force,
               recurse=recurse,
               variable=variable,
               checkEach=checkEach,
               index=index,
               **kwargs,
           )
           self.DeviceUpdate()

Here, ``DeviceUpdate`` is a real hardware command register. The write to
``0x3FC`` tells the ADC to latch the configuration values that were just
written through the normal block path. A closely related pattern is an
``ApplyConfig`` bit or pulse in clocking and timing devices.

Example: Wrap Reads With A Control Register
-------------------------------------------

Another common pattern is to bracket reads with a hardware control action when
the live status registers would otherwise change while the read sequence is in
progress:

.. code-block:: python

   class MyReader(pyrogue.Device):
       def __init__(self, **kwargs):
           super().__init__(**kwargs)
           self.add(pyrogue.RemoteCommand(
               name='FreezeDebug',
               description='Freeze debug snapshot registers during readout',
               offset=0xA0,
               bitSize=1,
               bitOffset=0,
               base=pyrogue.UInt,
               function=pyrogue.RemoteCommand.touch,
           ))

       def readBlocks(self, *, recurse=True, variable=None, checkEach=False, index=-1, **kwargs):
           self.FreezeDebug(1)
           try:
               super().readBlocks(
                   recurse=recurse,
                   variable=variable,
                   checkEach=checkEach,
                   index=index,
                   **kwargs,
               )
           finally:
               self.FreezeDebug(0)

In this pattern, ``FreezeDebug`` controls a hardware snapshot or hold function.
The assertion at the start of ``readBlocks`` freezes a bank of debug registers
so the read transactions see one consistent sample of the hardware state. The
final write releases the freeze after the read requests have been issued.

Example: Custom Child-Device Ordering
-------------------------------------

Sometimes the reason to override a block method is not a local register strobe,
but the ordering of child-Device configuration. The default recursive behavior
visits child Devices in add order. That is often correct, but some hardware
trees need a stricter sequence.

One real pattern is a mixed-clocking and data-converter system where the clock
generator must be configured first, some DAC setup must complete before a JESD
initialization step runs, and the ADC devices should only be configured after
that intermediate hardware procedure:

.. code-block:: python

   class MyCarrier(pyrogue.Device):
       def writeBlocks(self, force=False, recurse=True, variable=None, checkEach=False, index=-1, **kwargs):
           super().writeBlocks(
               force=force,
               recurse=False,
               variable=variable,
               checkEach=checkEach,
               index=index,
               **kwargs,
           )

           self.Clock.writeBlocks(force=force, recurse=True, variable=variable, checkEach=checkEach, index=index, **kwargs)
           self.DacA.writeBlocks(force=force, recurse=True, variable=variable, checkEach=checkEach, index=index, **kwargs)
           self.DacB.writeBlocks(force=force, recurse=True, variable=variable, checkEach=checkEach, index=index, **kwargs)

           self.InitJesdLinks()

           self.AdcA.writeBlocks(force=force, recurse=True, variable=variable, checkEach=checkEach, index=index, **kwargs)
           self.AdcB.writeBlocks(force=force, recurse=True, variable=variable, checkEach=checkEach, index=index, **kwargs)
           self.checkBlocks(recurse=True)

In that pattern, the override is intentionally replacing the default child
recursion order. The important part is to make that decision explicit:
preserve the normal parameter behavior, disable the inherited recursion where
needed, and then issue child-Device operations in the hardware order that the
system requires.

Example: One-Shot Configure Command
-----------------------------------

Sometimes the cleanest solution is not to override the block methods at all,
but instead to call a composed helper from a ``Command``:

.. code-block:: python

   @self.command()
   def Configure():
       self.writeAndVerifyBlocks(force=True, recurse=True, checkEach=True)

This is a good fit when the special behavior is a named procedure rather than a
global change to all future block writes.

Relationship To ``Blocks``
==========================

This page is about the Device-level traversal methods. The companion
``Blocks`` page is about what a ``Block`` is, how Variables map into Blocks,
and how conversion and transaction layers are separated.

Use the two pages together:

* :doc:`/pyrogue_tree/core/block` for what Blocks are.
* This page for how Devices traverse and sequence Block operations.

What To Explore Next
====================

* What Blocks are and how Variables map into them: :doc:`/pyrogue_tree/core/block`
* Device structure and lifecycle hooks: :doc:`/pyrogue_tree/core/device`
* Variable behavior and hardware-backed access paths: :doc:`/pyrogue_tree/core/variable`
