.. _tutorial_commands_and_groups:

===============================
Commands, Blocks, And Groups
===============================

:doc:`/getting_started/index` used variables to read and write registers. That
covers state, but not actions — and it says nothing about how Rogue batches
register access or how bulk operations decide what to include.

This tutorial covers three mechanisms that work together in every real
application:

* **Commands** perform actions rather than holding values.
* **Blocks** decide how many memory transactions your variables actually cost.
* **Groups** label nodes so bulk operations can skip them.

.. note::

   **No hardware required.** Everything here runs against
   ``rogue.interfaces.memory.Emulate``, the same software memory space used in
   :doc:`/getting_started/index`.

Prerequisites
=============

Finish :doc:`/getting_started/index`. All examples below attach to one emulated
memory space:

.. literalinclude:: examples/commands_and_groups.py
   :language: python
   :pyobject: TutorialRoot

Part 1: Commands
================

A :ref:`Command <pyrogue_tree_node_command>` is a node you invoke. Rogue offers
three kinds, and picking the wrong one is a common source of awkward code:

.. literalinclude:: examples/commands_and_groups.py
   :language: python
   :pyobject: CommandDevice

``RemoteCommand`` writes a value to an address. The ``function`` argument says
what writing means: ``cmd.post(1)`` fires a write without waiting for a
response, which is right for a self-clearing trigger bit where the hardware
resets the bit itself and reading it back is pointless.

The ``@self.command`` decorator is the shortest form when the action is Python
rather than a single register write — sequencing several variables, validating
an argument, computing a value. The ``arg`` parameter carries whatever the
caller passed.

``LocalCommand`` touches no registers. Use it for host-side helpers, and set
``retValue`` when the caller should get something back.

Invoke all three the same way:

.. code-block:: python

   root.Cmds.Pulse()                 # RemoteCommand
   root.Cmds.SetControl(0x55)        # decorator form, takes an argument
   print(root.Cmds.Describe())       # LocalCommand, returns a value

.. code-block:: text

   Control after SetControl : 0x00000055
   Describe returned        : CommandDevice ready

Part 2: Blocks
==============

This is the part that surprises people. A :ref:`Block <pyrogue_tree_node_block>` is
the unit Rogue actually reads and writes. Variables do not map one-to-one onto
transactions — Rogue coalesces variables that share a register into a single
Block, so one transaction serves all of them.

Three fields packed into one 32-bit register at the same ``offset``, differing
only in ``bitOffset``:

.. literalinclude:: examples/commands_and_groups.py
   :language: python
   :pyobject: PackedDevice

The same three fields given addresses of their own:

.. literalinclude:: examples/commands_and_groups.py
   :language: python
   :pyobject: SpreadDevice

Identical API from the caller's side, but the cost differs:

.. code-block:: text

   Blocks used by Packed (offset 0x00 x3) : 1
   Blocks used by Spread (0x00/0x04/0x08) : 3

Writing all three packed fields is **one** transaction; writing the spread
fields is **three**. Over a high-latency link, or across a register map with
hundreds of fields, that ratio decides whether a tree scan takes milliseconds or
seconds.

The fields remain independent — setting one does not disturb its neighbours,
because Rogue performs a read-modify-write on the shared Block:

.. code-block:: python

   root.Packed.Middle.set(0x00)
   assert root.Packed.Low.get() == 0xAA    # untouched
   assert root.Packed.High.get() == 0xCC   # untouched

You rarely construct Blocks yourself. What matters is knowing they exist, since
they explain why bit-packed register maps are worth the effort. See
:doc:`/pyrogue_tree/core/block` and
:doc:`/pyrogue_tree/core/block_operations` for the full model.

Part 3: Groups
==============

A large tree contains values that should not be treated uniformly. Counters
should not be written back from a saved configuration. Diagnostics need not be
served to EPICS. :ref:`Groups <pyrogue_tree_node_groups>` are labels that let bulk
operations make those distinctions:

.. literalinclude:: examples/commands_and_groups.py
   :language: python
   :pyobject: GroupDevice

Two conventional names appear here. ``NoConfig`` marks values that should not be
captured in a saved configuration; ``NoServe`` keeps a value out of EPICS and
similar servers by default.

Groups take effect when a bulk operation filters on them:

.. code-block:: python

   everything = root.getYaml(readFirst=False, modes=['RW'],
                             incGroups=None, excGroups=None)
   config     = root.getYaml(readFirst=False, modes=['RW'],
                             incGroups=None, excGroups=['NoConfig'])

.. code-block:: text

   Volatile in full dump   : True
   Volatile in saved config: False
   Volatile groups         : ['NoConfig']

.. important::

   Groups are labels, not access control. A variable tagged ``NoServe`` is still
   fully readable and writable through ``.get()`` and ``.set()`` — the tag only
   affects operations that choose to honour it. Do not use Groups to protect
   dangerous registers.

Running It
==========

.. code-block:: bash

   python3 commands_and_groups.py

.. code-block:: text

   --- Commands
      Control after SetControl : 0x00000055
      Describe returned        : CommandDevice ready
   --- Blocks
      packed values  : 0xaa 0xbb 0xcc
      Blocks used by Packed (offset 0x00 x3) : 1
      Blocks used by Spread (0x00/0x04/0x08) : 3
   --- Groups
      Saved in full dump      : True
      Volatile in full dump   : True
      Volatile in saved config: False
      Volatile groups         : ['NoConfig']

Where To Go Next
================

* :doc:`/pyrogue_tree/core/command` — command reference, including argument
  and return-value handling.
* :doc:`/pyrogue_tree/core/block` — the Block model in detail.
* :doc:`/pyrogue_tree/core/groups` — group semantics and framework conventions.
* :doc:`/pyrogue_tree/core/yaml_configuration` — saving and loading
  configuration, where ``NoConfig`` earns its place.
* :doc:`/tutorials/file_capture` — continue with capturing data to disk.
