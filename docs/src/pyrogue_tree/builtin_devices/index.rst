.. _pyrogue_tree_builtin_devices:

===============
Built-in Devices
===============

PyRogue includes reusable ``Device`` subclasses for common control, monitoring,
and data-path tasks. These classes reduce boilerplate by packaging widely used
patterns into configurable components that attach directly in your tree.

How these fit in a design
=========================

Built-in Devices are ordinary ``Device`` subclasses, so they participate in the
same tree lifecycle and transaction flow as custom devices:

* add them under a parent ``Device`` or directly under ``Root``
* bind memory/stream interfaces as needed
* operate them through the same Variable and Command APIs as any other node

Use cases commonly include:

* run control sequencing and rate management
* PRBS transmit/receive test pipelines
* stream capture and replay workflows
* process supervision and script orchestration

Relationship to Core and interfaces
===================================

For underlying behavior, see:

* :doc:`/pyrogue_tree/core/device`
* :doc:`/pyrogue_tree/core/variable`
* :doc:`/pyrogue_tree/client_interfaces/index`

Where to explore next
=====================

* Run control orchestration: :doc:`run_control`
* Data capture/write path: :doc:`data_writer` and :doc:`stream_writer`
* Data receive/read path: :doc:`data_receiver` and :doc:`stream_reader`
* PRBS testing devices: :doc:`prbsrx`, :doc:`prbstx`, and :doc:`prbspair`
* External process integration: :doc:`process`

.. toctree::
   :maxdepth: 1
   :caption: Built-in Devices:

   run_control
   data_writer
   data_receiver
   prbsrx
   prbstx
   prbspair
   stream_reader
   stream_writer
   process
