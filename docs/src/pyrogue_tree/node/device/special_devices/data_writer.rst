.. _pyrogue_tree_node_device_datawriter:

=======================
DataWriter Device Class
=======================

Similiar to RunControl, DataWriter is a special class which serves at the interface for a file writer in
the system

* pyrogue.utilities.fileio.StreamWriter is the default generic write contained in YAML

    * Custom data writers can be created

Key Methods
-----------
The following methods control the operation of the file writer, and should be overridden in a custom writer.

* :py:meth:`pyrogue.DataWriter._setBufferSize`
* :py:meth:`pyrogue.DataWriter._setMaxFileSize`
* :py:meth:`pyrogue.DataWriter._getFrameCount`

Included Command Objects
------------------------
The following :py:class:`pyrogue.LocalCommand` objects are all created when the DataWriter is created.

* **Open**: Open data file. The new file name will be the contents of the DataFile variable.
* **Close**: Close data file.
* **AutoName**: Auto create data file name using data and time.

Included Variable Objects
-------------------------
The following :py:class:`pyrogue.LocalVariable` objects are all created when the Datawriter is created.

* **DataFile**: Data file for storing frames for connected streams. This is the file opened when the Open command is executed.
* **IsOpen**: Status field which is True when the Data file is open.
* **BufferSize**: File buffering size. Enables caching of data before call to file system.
* **MaxFileSize**: Maximum size for an individual file. Setting to a non zero splits the run data into multiple files.
* **CurrentSize**: Size of current data files in bytes.
* **TotalSize**: Total bytes written.
* **FrameCount**: Total frames received and written.


DataWriter Class Documentation
==============================

.. autoclass:: pyrogue.DataWriter
   :members:
   :member-order: bysource
   :inherited-members: