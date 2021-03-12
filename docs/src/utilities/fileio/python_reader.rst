.. _utilities_fileio_python_reader:

==================
Python File Reader
==================

The Rogue FileReader class is a lightweight python class which can be used on its own
with minimal dependencies. The file reader supports processing store data frame by
frame and supports automatic extraction of configuration and status information which may
exist in a specificed "config channel". The passed file parameter can be a single file or
a list of segemented data files.

The most current file can be downloaded from:

https://github.com/slaclab/rogue/blob/master/python/pyrogue/utilities/fileio/_FileReader.py

Below is an example of using the FileReader in a python script:

.. code-block:: python

   with FileReader(files="mydata.dat",configChan=1) as fd:

      # Loop through the file data
      for header,data in fd.records():

         # Look at record header data
         print(f"Processing record. Total={fd.totCount}, Current={fd.currCount}")
         print(f"Record size    = {header.size}")
         print(f"Record channel = {header.channel}")
         print(f"Record flags   = {header.flags:#x}")
         print(f"Record error   = {header.error:#x}")

         # Do something with the data here:
         for i in range(header.size):
            print(f" Byte {i} = {data[i]:#x}")

         # At any time you can access the current config and status state
         print(f"Data time = {fd.configValue['root.Time']}")

FileReader Description
======================

The class description for the SimpleClient class is included below:

.. autoclass:: pyrogue.utilities.fileio.FileReader
   :members:
   :member-order: bysource


The header data record is described below:

.. autoclass:: pyrogue.utilities.fileio.RogueHeader

