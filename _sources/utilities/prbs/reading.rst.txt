.. _utilities_prbs_writing:

=====================
Receiving PRBS Frames
=====================

The PRBS object can either be used in its raw form or with either the PrbsTx or PrbsRx
Rogue Device wrappers. Using the Rogue Device wrapper allows the PRBS transmitter and receiver to
be controlled and monitor in the Rogue PyDM GUI.

The following code block describes how to create and connect a PRBS receiver to a file writer in python:

.. code-block:: python

   import pyrogue
   import rogue.utilities.fileio

   # First we create a file reader instance
   fread = rogue.utilities.fileio.StreamReader()

   # Create a PRBS instance to be used as a receiver
   prbs = rogue.utilities.Prbs()

   # Connect the two together
   prbs << fread

   # Open the file and push data to the prbs receiver
   fread.open("myFile.dat.1")

   # Wait until reader is done
   fread.closeWait();

   # Display the results
   print(f"Got {prbs.getRxCount()} frames")
   print(f"Got {prbs.getRxErrors()} errors")


The following code is an example of connecting a PRBS receiver to a file reader for control under
a Rogue tree.

TODO python class reference

.. code-block:: python

   import pyrogue
   import pyrogue.utilities
   import pyrogue.utilities.fileio

   # First we create a file reader instance, use the python wrapper
   fread = pyrogue.utilities.fileio.StreamReader()

   # Add the file reader to the Rogue tree.
   root.add(fread)

   # Create a PRBS receiver
   prbs = pyrogue.utilities.PrbsRx()

   # Add the prbs receiver to the Rogue tree.
   self.add(prbs)

   # Connect the receiver to the file reader
   fread >> prbs

The following code shows how to connect a PRBS receiver to a StreamReader in c++.

.. code-block:: c

   #include <rogue/utilities/fileio/StreamReader.h>
   #include <rogue/utilities/Prbs.h>

   // First we create a file reader instance
   rogue::utilities::fileio::StreamReaderPtr fwrite = rogue::utilities::fileio::StreamReaderPtr::create();

   // Create a PRBS receiver
   rogue::utilities::PrbsPtr prbs = rogue::utilities::Prbs::create();

   // Connect prbs to file reader
   prbs << fread;

   // Open the data file
   fread->open("myFile.dat.1");

   // Close the data file after all frames are read
   fread->closeWait();

   // Display the results
   printf("Got %i frames\n",prbs.getRxCount());
   printf("Got %i errors\n",prbs.getRxErrors());

