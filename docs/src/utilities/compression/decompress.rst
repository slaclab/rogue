.. _utilities_compression_decompression:

====================
Decompressing Frames
====================

The following code block describes how to read data from a file, pass it through a decompress block and then on to a PRBS receiver.

.. code-block:: python

   import pyrogue
   import rogue.utilities.fileio

   # First we create a file reader instance
   fread = rogue.utilities.fileio.StreamReader()

   # Create a PRBS instance to be used as a receiver
   prbs = rogue.utilities.Prbs()

   # Create a decompression instance
   decomp = rogue.utilities.StreamUnZip()

   # Connect the decompression engine to the file writer
   decomp << fread

   # Connect the two together
   prbs << decomp

   # Open the file and push data to the prbs receiver
   fread.open("myFile.dat.1")

   # Wait until reader is done
   fread.closeWait();

   # Display the results
   print(f"Got {prbs.getRxCount()} frames")
   print(f"Got {prbs.getRxErrors()} errors")

Below is the same code in c++.

.. code-block:: c

   #include <rogue/utilities/fileio/StreamReader.h>
   #include <rogue/utilities/Prbs.h>

   // First we create a file reader instance
   rogue::utilities::fileio::StreamReaderPtr fwrite = rogue::utilities::fileio::StreamReaderPtr::create();

   // Create a PRBS receiver
   rogue::utilities::PrbsPtr prbs = rogue::utilities::Prbs::create();

   // Create a decompression block
   rogue::utilities::StreamUnZipPtr comp = rogue::utilities::StreamUnZip::create();

   // Connect the decompression engine to the file reader
   decomp << fread;

   // Connect prbs to file reader
   prbs << decomp;

   // Open the data file
   fread->open("myFile.dat.1");

   // Close the data file after all frames are read
   fread->closeWait();

   // Display the results
   printf("Got %i frames\n",prbs.getRxCount());
   printf("Got %i errors\n",prbs.getRxErrors());

