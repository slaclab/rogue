.. _protocols_srp_classes_cmd:

===
Cmd
===

`rogue::protocols::srp::Cmd` transmits lightweight opcode/context stream
commands for fire-and-forget control paths. It is not an SRP register protocol,
but remains in the ``srp`` namespace for API compatibility.

Cmd objects in C++ are referenced by the following shared pointer typedef:

.. doxygentypedef:: rogue::protocols::srp::CmdPtr

The class description is shown below:

.. doxygenclass:: rogue::protocols::srp::Cmd
   :members:
