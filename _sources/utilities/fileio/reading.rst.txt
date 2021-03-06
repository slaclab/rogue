.. _utilities_fileio_reading:

==========================
Reading Frames From A File
==========================

Frames can be read in a streaming fashion using the :ref:`utilities_fileio_reader` class. This
class will output frames using the standard stream interface, with a Frame object created for
each data blob in the Frame, with the same format and with the same flags when it was originally
written. Since multiple "channels" may have been used when writing the file, generated frames will
be tagged with a channel ID to match the channel value when written. A :ref:`interfaces_stream_filter`
object can be used to direct the Frames based upon their channel IDs.

There is also a python utilitiy for reading frames in python using a non-streaming method.

The following code block describes how to create and connect a file reader in python:

.. code-block:: python

   import pyrogue
   import rogue.utilities.fileio

   # First we create a file reader instance
   fread = rogue.utilities.fileio.StreamReader()

   # Assuming we already have a frame receiver, we can connect the reader
   # instance to the receiver
   receiver << fread

   # We can then open the file. As soon as the file is opened the read frames
   # will be streamed to the receiver until all frames are read. If the file
   # was written using the maxSize attribute, you can include the index of the
   # first file, and all of the seperate files in the split sequence will be written
   # in order:
   fread.open("myFile.dat.1")

   # After all of the files are read, you can then close the file. The closeWait() command
   # is a blocking command that will wait until all the frames are read, and then close() the
   # file
   fread.closeWait()


A Rogue Device wrapper is provided for including the StreamReader class as part of the Rogue tree. This allows the StreamReader to be
present in the Rogue PyDM GUI, providing an interface for opening and closing files.

The following code is an example of using the Rogue StreamReader wrapper in the Rogue tree.

TODO python class reference

.. code-block:: python

   import pyrogue
   import pyrogue.utilities.fileio

   # First we create a file reader instance, use the python wrapper
   fread = pyrogue.utilities.fileio.StreamReader()

   # Add the file reader to the Rogue tree.
   root.add(fread)

   # Assuming we already have a frame receiver, we can connect the reader
   # instance to the receiver
   receiver << fread


The following code shows how to use a StreamReader in c++.

.. code-block:: c

   #include <rogue/utilities/fileio/StreamReader.h>

   // First we create a file reader instance
   rogue::utilities::fileio::StreamReaderPtr fwrite = rogue::utilities::fileio::StreamReaderPtr::create();

   // Connect the reader to an existing receiver
   receiver << fread;

   // Open the data file
   fread->open("myFile.dat.1");

   // Close the data file after all frames are read
   fread->closeWait();

