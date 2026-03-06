.. _pyrogue_tree_node_device_datawriter:

=======================
DataWriter Device Class
=======================

:py:class:`~pyrogue.DataWriter` is a base device for writing received stream
frames to files.

For application use, :py:class:`~pyrogue.utilities.fileio.StreamWriter` is the
concrete subclass you should typically instantiate.

Custom data writers can be created by subclassing ``DataWriter``.

Key Methods
-----------
The following methods control the operation of the file writer and are typical
override points in a custom writer:

* :py:meth:`~pyrogue.DataWriter._setBufferSize`
* :py:meth:`~pyrogue.DataWriter._setMaxFileSize`
* :py:meth:`~pyrogue.DataWriter._getFrameCount`

Included Command Objects
------------------------
The following :py:class:`~pyrogue.LocalCommand` objects are created when
``DataWriter`` is instantiated.

* **Open**: Open data file. The new file name will be the contents of
  ``DataFile``.
* **Close**: Close data file.
* **AutoName**: Auto create data file name using date and time.

Included Variable Objects
-------------------------
The following :py:class:`~pyrogue.LocalVariable` objects are created when
``DataWriter`` is instantiated.

* **DataFile**: Data file for storing frames for connected streams. This is the
  file opened when the ``Open`` command is executed.
* **IsOpen**: Status field which is ``True`` when the data file is open.
* **BufferSize**: File buffering size. Enables caching of data before calls to
  the file system.
* **MaxFileSize**: Maximum size for an individual file. Setting to a non-zero
  value splits run data into multiple files.
* **CurrentSize**: Size of current data file in bytes.
* **TotalSize**: Total bytes written.
* **FrameCount**: Total frames received and written.

DataWriter API Reference
==============================

See :doc:`/api/python/datawriter` for generated API details.
