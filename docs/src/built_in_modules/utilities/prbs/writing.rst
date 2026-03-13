.. _utilities_prbs_writing:

======================
Generating PRBS Frames
======================

``rogue.utilities.Prbs`` generates PRBS traffic directly into a stream graph.
That form is a good fit for scripts, standalone tests, and small validation
setups.

``pyrogue.utilities.prbs.PrbsTx`` wraps the same generator behavior in a
tree-managed ``Device``. That form is a better fit when transmit control and
counters should be visible through a ``Root`` tree.

PRBS transmit paths commonly drive traffic into FPGA firmware/VHDL checkers
during link bring-up and integration testing.

Method Overview
===============

Common generator calls are:

- ``genFrame(size)``: Generates and transmits one PRBS frame of ``size`` bytes.
- ``PrbsTx`` wrapper: Exposes generator controls and counters as ``Variables``
  and ``Commands`` in a tree.

Using ``PrbsTx`` In A Tree
==========================

``pyrogue.utilities.prbs.PrbsTx`` is the tree-managed form of the PRBS
generator.

It is the right choice when operators or client code should be able to inspect
or control transmit settings such as enable state, frame size, frame period,
and generator counters through the PyRogue tree.

Python Direct-Utility Example
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

Python Tree-Managed Example
===========================

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

- :doc:`index`
- :doc:`reading`

API Reference
=============

- Python:

  - :doc:`/api/python/rogue/utilities/prbs/prbs`
  - :doc:`/api/python/pyrogue/utilities/prbs/prbstx`
  - :doc:`/api/python/pyrogue/utilities/prbs/prbspair`

- C++:

  - :doc:`/api/cpp/utilities/prbs/prbs`
