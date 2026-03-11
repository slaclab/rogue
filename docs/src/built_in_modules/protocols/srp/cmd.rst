.. _protocols_srp_cmd:

====================
SRP Protocol Command
====================

`Cmd` is a lightweight opcode/context stream command protocol used for
fire-and-forget hardware control operations (for example trigger commands).
It is distinct from SRPv0/SRPv3 register-access transactions.

The class remains under ``rogue.protocols.srp`` for API compatibility.

When to use ``Cmd``
===================

- Use for simple action requests that do not require a register readback path.
- Use when endpoint logic expects opcode/context messages instead of memory
  transactions.
- Avoid for stateful register control where SRPv0/SRPv3 semantics are needed.

Design note
===========

Keep command opcodes stable and documented, since these become part of the
control contract between software and firmware.

Practical note
==============

Unlike ``SrpV0``/``SrpV3``, ``Cmd`` is not a memory-transaction bridge. Use it
only when firmware defines an explicit opcode/context command path.

API reference
=============

- Python: :doc:`/api/python/rogue/protocols/srp_cmd`
- C++: :doc:`/api/cpp/protocols/srp/cmd`
- SRP overview: :doc:`index`
- Register-transaction protocols: :doc:`srpV3`, :doc:`srpV0`
