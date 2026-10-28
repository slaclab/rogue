.. _pyrogue_tree_builtin_devices:

================
Built-in Devices
================

PyRogue includes reusable ``Device`` subclasses for common control, monitoring,
and data-path tasks. These classes reduce boilerplate by packaging widely used
patterns into configurable components that attach directly in your tree.

This section is intentionally limited to classes exposed in the top-level
``pyrogue`` namespace.

How These Fit In A Design
=========================

Built-in Devices are ordinary ``Device`` subclasses, so they participate in the
same tree lifecycle and transaction flow as custom devices:

* Add them under a parent ``Device`` or directly under ``Root``
* Bind memory/stream interfaces as needed
* Operate them through the same Variable and Command APIs as any other node

Use cases commonly include:

* Run control sequencing and rate management
* Stream capture and receive control surfaces
* Process supervision and script orchestration

Reading Path
============

The built-in devices fall into a few natural groups:

* Start with :doc:`run_control` and :doc:`process` if you are organizing
  software actions, acquisition loops, or operator-visible procedures.
* Use :doc:`data_writer` and :doc:`data_receiver` for tree-facing stream write
  and receive patterns.
* Use :doc:`/built_in_modules/index` for lower-level utilities and wrappers
  such as file I/O and PRBS modules that live outside the top-level
  ``pyrogue`` namespace.

Relationship To Core And Interfaces
===================================

For underlying behavior, see:

* :doc:`/pyrogue_tree/core/device`
* :doc:`/pyrogue_tree/core/variable`
* :doc:`/pyrogue_tree/client_interfaces/index`

Related Topics
==============

* Run control orchestration: :doc:`run_control`
* Data capture/write path: :doc:`data_writer`
* Data receive/read path: :doc:`data_receiver`
* Lower-level modules and wrappers: :doc:`/built_in_modules/index`
* External process integration: :doc:`process`

.. toctree::
   :maxdepth: 1
   :caption: Built-in Devices:

   run_control
   data_writer
   data_receiver
   process
