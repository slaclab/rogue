.. _utilities_prbs_writing:

======================
Generating PRBS Frames
======================

The PRBS object can either be used in its raw form or with either the PrbsTx or PrbsRx
Rogue Device wrappers. Using the Rogue Device wrapper allows the PRBS transmitter and receiver to
be controlled and monitor in the Rogue PyDM GUI.

The following code block describes how to create and connect a PRBS generator to a file writer in python:

.. code-block:: python

   import pyrogue
   import rogue.utilities.fileio

   # Create a file writer, buffer size = 1000, max file size = 1MB
   fwrite = rogue.utilities.fileio.StreamWriter()
   fwrite.setBufferSize(1000)
   fwrite.setMaxSize(1000000)

   # Create a PRBS instance to be used as a generator
   prbs = rogue.utilities.Prbs()

   # Connect the generator to the file writer
   prbs >> fwrite.getChannel(0)

   # Open the data file
   fwrite.open("test.dat")

   # Generate 1000 frames of PRBS data, 1000 bytes each
   for _ in range(1000):
      prbs.genFrame(1000)

   # Close the data file
   fwrite.close()


The following code is an example of connecting a PRBS generator to a file writer for control under
a Rogue tree.

TODO python class reference

.. code-block:: python

   import pyrogue
   import pyrogue.utilities
   import pyrogue.utilities.fileio

   # First we create a file writer instance, use the python wrapper
   fwrite = pyrogue.utilities.fileio.StreamWriter()

   # Add the file writer to the Rogue tree.
   root.add(fwrite)

   # Create a PRBS generator
   prbs = pyrogue.utilities.PrbsTx()

   # Add the prbs generator to the Rogue tree.
   self.add(prbs)

   # Connect the generator to the file writer
   prbs >> fwrite.getChannel(0)


The following code shows how to connect a PRBS generator to a StreamWriter in c++.

.. code-block:: c

   #include <rogue/utilities/Prbs.h>
   #include <rogue/utilities/fileio/StreamWriter.h>
   #include <rogue/utilities/fileio/StreamWriterChannel.h>

   // First we create a file writer instance
   rogue::utilities::fileio::StreamWriterPtr fwrite = rogue::utilities::fileio::StreamWriterPtr::create():

   // Next we set the buffer size which controls how much data to cache in memory
   // before forming a burst write to the operating system. Larger writes help
   // in file operation performance
   fwrite->setBufferSize(10000);

   // We can also set a maximum file size for each file. If this value is non-zero
   // the passed file name will be appended with a numeric value starting from 1.
   // As the max size is reached a new file will be opened with the next index value 100MBytes
   fwrite->setMaxSize(100000000);

   // By default all frames are written, even if the incoming error field is set. You
   // can choose to ignore errored frames using the following call:
   fwrite->setDropErrors(true);

   // Create a PRBS generator
   rogue::utilities::PrbsPtr prbs = rogue::utilities::Prbs::create();

   // Connect prbs to file writer
   prbs >> fwrite->getChannel(0);

   // Open the data file
   fwrite->open("test.dat"):

   # Generate 1000 frames of PRBS data, 1000 bytes each
   for (i=0; i < 1000; i++ ) prbs->genFrame(1000):

   // Close the data file
   fwrite->close():

