.. _utilities_filio_writing:

========================
Writing Frames To A File
========================

Frames can be written to a data file using the :ref:`utilities_fileio_writer` class. This
file writer supports multiple incoming streams, which are then deliniated in the written
data file. The Channel 0 interface can be used to write frames which may have a non-zero
channel ID field value set. If this value is non-zero the Frame's channel ID will be used
when writing the file.

The following code block describes how to create and connect a file writer in python:

.. code-block:: python

   import pyrogue
   import rogue.utilities.fileio

   # Assume we have to incoming data streams, streamA and streamB coming from a pair
   # of stream Masters
   # streamA
   # streamB

   # First we create a file writer instance
   fwrite = rogue.utilities.fileio.StreamWriter()

   # Next we set the buffer size which controls how much data to cache in memory
   # before forming a burst write to the operating system. Larger writes help
   # in file operation performance
   fwrite.setBufferSize(10000)

   # We can also set a maximum file size for each file. If this value is non-zero
   # the passed file name will be appended with a numeric value starting from 1.
   # As the max size is reached a new file will be opened with the next index value
   # 100MBytes
   fwrite.setMaxSize(100000000)

   # By default all frames are written, even if the incoming error field is set. You
   # can choose to ignore errored frames using the following call:
   fwrite.setDropErrors(True)

   # Connect stream A to the file writer channel 0
   streamA >> fwrite.getChannel(0)

   # Connect stream B to the file writer channel 1
   streamB >> fwrite.getChannel(1)

   # Open the data file
   fwrite.open("myFile.dat")

   # Close the data file
   fwrite.close()


Most uses of the StreamWriter class will be used in the larger Rogue tree. Using the StreamWriter as
a Device in the Rogue tree will provide a Variable and Command interface, including PyDM GUI supports
for opening and closing files.

The following code shows how to use a StreamWriter in c++.

.. code-block:: c

   #include <rogue/utilities/fileio/StreamWriter.h>
   #include <rogue/utilities/fileio/StreamWriterChannel.h>

   // Assume we have to incoming data streams, streamA and streamB coming from a pair
   // of stream Masters
   // streamA
   // streamB

   // First we create a file writer instance
   rogue::utilities::fileio::StreamWriterPtr fwrite = rogue::utilities::fileio::StreamWriterPtr::create()

   // Next we set the buffer size which controls how much data to cache in memory
   // before forming a burst write to the operating system. Larger writes help
   // in file operation performance
   fwrite->setBufferSize(10000);

   // We can also set a maximum file size for each file. If this value is non-zero
   // the passed file name will be appended with a numeric value starting from 1.
   // As the max size is reached a new file will be opened with the next index value
   // 100MBytes
   fwrite->setMaxSize(100000000);

   // By default all frames are written, even if the incoming error field is set. You
   // can choose to ignore errored frames using the following call:
   fwrite->setDropErrors(true);

   // Connect stream A to the file writer channel 0
   streamA >> fwrite->getChannel(0);

   // Connect stream B to the file writer channel 1
   streamB >> fwrite->getChannel(1);

   // Open the data file
   fwrite->open("myFile.dat")

   // Close the data file
   fwrite->close()

