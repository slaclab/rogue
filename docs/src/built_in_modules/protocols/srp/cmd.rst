.. _protocols_srp_cmd:

====================
SRP Protocol Command
====================

For lightweight fire-and-forget opcode and context messages, Rogue provides
``rogue.protocols.srp.Cmd``. ``Cmd`` is distinct from ``SrpV0`` and ``SrpV3``:
it is a stream command path, not a memory-transaction bridge.

The class remains under ``rogue.protocols.srp`` for API compatibility.

When To Use ``Cmd``
===================

- Use for simple action requests that do not require a register readback path.
- Use when endpoint logic expects opcode/context messages instead of memory
  transactions.
- Avoid for stateful register control where SRPv0/SRPv3 semantics are needed.

Construction And Behavior
=========================

``Cmd`` is a stream ``Master`` only. ``sendCmd(opCode, context)`` emits a small
command frame carrying just those two fields. In normal use there is no
response path and no transaction completion semantics.

Keep command opcodes stable and documented, since they become part of the
control contract between software and firmware.

Unlike ``SrpV0``/``SrpV3``, ``Cmd`` is not a memory-transaction bridge. Use it
only when firmware defines an explicit opcode/context command path.

Python Example
==============

.. code-block:: python

   import rogue.protocols.srp

   cmd = rogue.protocols.srp.Cmd()
   cmd >> command_transport

   # Send opcode 0x1 with context value 0x1234.
   cmd.sendCmd(0x1, 0x1234)

Related Topics
==============

- :doc:`index`
- :doc:`srpV3`
- :doc:`srpV0`

API Reference
=============

- Python: :doc:`/api/python/rogue/protocols/srp/cmd`
- C++: :doc:`/api/cpp/protocols/srp/cmd`
