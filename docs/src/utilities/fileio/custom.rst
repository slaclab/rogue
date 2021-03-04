.. _utilities_fileio_custom:

==============
Custom Writers
==============

Rogue provides a standard class :ref:`utilities_fileio_writer` for storing stream data
in Rogue. In some cases the user may want to implement a custom file format or may need to record
data in a pre-defined for certain DAQ systems. Rogue provides the ability to sub-class the StreamWriter
class, while keeping its core features including multiple segmented files and data buffering for burst
writing. To write a custom data format the user simply needs to sub-class the StreamWriter and override
the writeFile virtual method.

See :ref:`custom_module` for more information about using this custom class in a Rogue library.

Custom Writer Subclass
======================

The example below shows an example sub-class for writing Frame data to a text file.

.. code-block:: c

   #include <rogue/utilities/fileio/StreamWriter.h>
   #include <rogue/interfaces/stream/Frame.h>

   class MyDataWriter : public rogue::utilities::fileio::StreamWriter {

      protected:

         virtual void writeFile ( uint8_t channel, std::shared_ptr<rogue::interfaces::stream::Frame> frame) {

            // Variables
            uint32_t value;
            uint32_t size;
            char buffer[100];

            // Release the python GIL to avoid deadlocks
            rogue::GilRelease noGil;

            // Lock the access to the local file
            // When the writeFile method is called, a lock is already held on the Frame instance
            std::unique_lock<std::mutex> lock(mtx_);

            // Get the payload size from the frame
            size = frame->getPayload();

            // Call a helper function to check the file size and do housekeeping on the
            // memory resident buffer. This will close and open a new file if we have
            // reached the max size and will flush the memory buffer to a file if we
            // have reached the requested burst size.
            checkSize(size);

            // Get an iterator to the frame data
            it = frame->begin();

            // First line is the size in 32-bit values
            sprintf(buffer,"0x%x\n",size/4);

            // Call the underlying write functions
            intWrite(buffer,strlen(buffer));

            // Loop through the rest of the file
            do {
               fromFrame(it,4,&value):
               sprintf(buffer,"0x%x\n",value);
               intWrite(buffer,strlen(buffer));
            } while ( ++it != frame->end() );

            // Update the frame count
            frameCount_ ++;

            // This helps update the class state
            cond_.notify_all();
         }
   }

   // Smart pointer alias for our custom class
   typedef std::shared_ptr<MyDataWriter> MyDataWriterPtr;


Once your custom writer is created you may want to use it in the Rogue tree, allowing you to open and write
files using the Rogue PyDM GUI. You can sub-class the rogue StreamWriter class for use with your custom
module.

.. code-block:: python

   import pyrogue
   import pyrogue.utilities.fileio

   # Assume we have to incoming data streams, streamA and streamB coming from a pair
   # of stream Masters
   # streamA
   # streamB

   # Instantiate your custom writer
   mywrite = MyWriter()

   # Pass the custom writer to the Rogue wrapper
   fwrite = pyrogue.utilities.fileio.StreamWriter(writer=myWrite)

   # Add the file writer to the Rogue tree.
   root.add(fwrite)

   # Don't set any other parameters as you will use the Rogue tree to set the
   # file parameters and open/close files

   # Connect stream A to the file writer channel 0
   streamA >> fwrite.getChannel(0)

   # Connect stream B to the file writer channel 1
   streamB >> fwrite.getChannel(1)

