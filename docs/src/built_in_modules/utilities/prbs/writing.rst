.. _utilities_prbs_writing:

======================
Generating PRBS Frames
======================

Use ``rogue.utilities.Prbs`` when a lightweight generator/checker endpoint is
needed directly in a stream topology.

Use ``pyrogue.utilities.prbs.PrbsTx`` when you want generator control and
counters as part of a ``Root`` tree.

This transmit path is commonly used to drive PRBS into FPGA firmware/VHDL
checkers during link bring-up and integration testing.

Method Overview
===============

Common PRBS generator calls shown below:

- ``genFrame(size)``: Generates and transmits one PRBS frame of ``size`` bytes.
- ``PrbsTx`` wrapper: Exposes generator controls and counters as ``Variables``
  and ``Commands`` in a tree.

Python PRBS Generator Example
=============================

.. code-block:: python

   import rogue.utilities as ru
   import rogue.utilities.fileio as ruf

   # Capture generated test traffic to file.
   fwrite = ruf.StreamWriter()
   fwrite.setBufferSize(1000)
   fwrite.setMaxSize(1_000_000)

   # Create PRBS source endpoint.
   prbs = ru.Prbs()

   # Route generated frames into writer channel 0.
   prbs >> fwrite.getChannel(0)

   # Capture 1000 test frames of 1000 bytes each.
   fwrite.open("test.dat")
   for _ in range(1000):
      prbs.genFrame(1000)
   fwrite.close()

PyRogue PRBS Transmitter Wrapper
================================

.. code-block:: python

   import pyrogue.utilities.fileio as puf
   import pyrogue.utilities.prbs as pup

   # Add tree-managed file writer and PRBS transmitter.
   fwrite = puf.StreamWriter()
   root.add(fwrite)

   prbs = pup.PrbsTx()
   root.add(prbs)

   # Transmit PRBS stream into writer channel 0.
   prbs >> fwrite.getChannel(0)

C++ PRBS Generator Example
==========================

.. code-block:: cpp

   #include <rogue/utilities/Prbs.h>
   #include <rogue/utilities/fileio/StreamWriter.h>
   #include <rogue/utilities/fileio/StreamWriterChannel.h>

   namespace ru  = rogue::utilities;
   namespace ruf = rogue::utilities::fileio;

   // Capture generated test traffic to file.
   auto fwrite = ruf::StreamWriter::create();
   fwrite->setBufferSize(10000);
   fwrite->setMaxSize(100000000);
   fwrite->setDropErrors(true);

   // Create PRBS source endpoint.
   auto prbs = ru::Prbs::create();

   // Route PRBS output to writer channel 0.
   prbs >> fwrite->getChannel(0);

   // Capture 1000 test frames of 1000 bytes each.
   fwrite->open("test.dat");
   for (int i = 0; i < 1000; ++i) prbs->genFrame(1000);
   fwrite->close();

Related Topics
==============

- :doc:`/pyrogue_tree/builtin_devices/prbstx`
- :doc:`/pyrogue_tree/builtin_devices/prbspair`

API Reference
=============

- Python:

  - :doc:`/api/python/rogue/utilities/prbs/prbs`
  - :doc:`/api/python/pyrogue/utilities/prbs/prbstx`
  - :doc:`/api/python/pyrogue/utilities/prbs/prbspair`

- C++:

  - :doc:`/api/cpp/utilities/prbs/prbs`
