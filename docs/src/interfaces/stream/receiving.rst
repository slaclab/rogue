.. _interfaces_stream_receiving:

Receiving Frames
================

Frames are received by a subclass of the :ref:`interfaces_stream_slave` class in rogue.
This subclass can be created either in python or in c++. In either case a received frame
results in the execution of the the acceptFrame method in the subclass instance. Python
and C++ subclasses of the Slave class can be used interchagably, allowing c++ subclasses 
to receive frames from python masters and python subclasses to receive frames from c++ masters.

Python Slave Subclass
---------------------

Implementing a Slave subclass in python is easy, but may result in a lower level of performance.

.. code-block:: python

   import rogue.interfaces.stream

   class MyCustomSlave(rogue.interfaces.stream.Slave):

       # Init method must call the parent class init
       def __init__(self):
           super().__init__()

       # Method which is called when a frame is received
       def _acceptFrame(self,frame):

           # First it is good practice to hold a lock on the frame data.
           with frame.lock():

               # Next we can get the size of the frame payload
               size = frame.getPayload()

               # To access the data we need to create a byte array to hold the data
               fullData = bytearray(size)

               # Next we read the frame data into the byte array, from offset 0
               frame.read(fullData,0)

               # Alternatively we can copy a portion of the data from an arbitrary offset
               partialData = bytearray(10)

               # Read 10 bytes starting at offset 100
               frame.read(partialData,5) 

           # Since the data is coped into the passed byte arrays we are free to
           # access the copied data outside of the lock
           print("First byte is {:#}".format(fullData[0]))
           print("Byte 6 is {:#}".format(partialData[1]))


C++ Slave Subclass
------------------


