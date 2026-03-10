.. _custom_module:

=======================
Creating Custom Modules
=======================

Rogue can be extended with custom C++ modules when the built-in stream,
protocol, or hardware helpers are not enough for an application. The usual
workflow is:

- Implement the C++ class that provides the needed Rogue interface behavior.
- Build it as a Python-loadable shared library against an existing Rogue
  installation.
- Wrap the exported class in a PyRogue ``Device`` so it fits naturally into a
  larger tree.
- Test the module first in a minimal local setup, then in a larger control
  application.

The example in this section follows that path for a custom stream transmitter
and receiver. It is still part of the broader
:doc:`/stream_interface/index` story, but the same pattern also applies to
other custom Rogue extensions.

Recommended Reading Order
=========================

1. Start with :doc:`sourcefile` to see the underlying C++ classes.
2. Continue with :doc:`makefile` to build the shared library.
3. Then read :doc:`wrapper` to expose the module through PyRogue ``Device``
   wrappers.
4. Finish with :doc:`testing` to validate the module in a small working setup.

.. toctree::
   :maxdepth: 1
   :caption: Example:

   sourcefile
   makefile
   wrapper
   testing

What To Explore Next
====================

- Stream interface patterns and connection semantics: :doc:`/stream_interface/index`
- PyRogue tree integration and Device structure: :doc:`/pyrogue_tree/index`
- Python and C++ API reference entry point: :doc:`/api/index`
