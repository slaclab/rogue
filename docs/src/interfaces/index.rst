.. _interfaces:

==========
Interfaces
==========

This section is now primarily a transitional and integration-focused index.

Canonical homes for core interface documentation:

- Stream interface: :doc:`/stream_interface/index`
- Memory interface: :doc:`/memory_interface/index`
- PyRogue client and server connectivity: :doc:`/pyrogue_core/client_access`

Use this section for remaining integration references that are not yet migrated.

Narrative Fit Note (M3)
=======================

The broad conceptual narrative below overlaps with canonical content now owned
by :doc:`/pyrogue_core/index`, :doc:`/stream_interface/index`, and
:doc:`/memory_interface/index`. Keep it as legacy source text for now, then
either redistribute or trim during M4 harmonization.

Legacy Notes (Old Content)
==========================

The following content is preserved from the prior structure for possible reuse.

Rogue is defined by a set of interfaces, both external and internal. External
interfaces include methods to access the Rogue tree from outside elements
including client scripts, GUIs and higher level DAQ systems.

The internal Rogue interfaces serve as the glue between many modules within
Rogue. These internal interfaces are designed so that once they are connected
together, they interact directly without requiring interaction with the Python
layer.

For example two C++ based stream modules can be "glued" together with a Python
script and then move data at high rates using only low level C++ threads.

The flexibility of this interface allows Stream and Memory modules to be first
prototyped in Python and then re-implemented in C++ for performance.

.. toctree::
   :maxdepth: 1
   :caption: Interfaces:

   simulation/index
   sql.rst
   cpp_api.rst
   version.rst
