.. _pyrogue_tree_node_device_datawriter:

=======================
DataWriter Device Class
=======================

:py:class:`pyrogue.DataWriter` is a base device for writing received stream
frames to files.

For application use, :py:class:`pyrogue.utilities.fileio.StreamWriter` is the
concrete subclass you should typically instantiate.

It includes built-in variables and commands such as:

* ``DataFile``, ``IsOpen``, ``BufferSize``, ``MaxFileSize``
* ``CurrentSize``, ``TotalSize``, ``Bandwidth``, ``FrameCount``
* ``Open``, ``Close``, ``AutoName``

Custom writer implementations typically subclass ``DataWriter`` and override:

* ``_open`` / ``_close``
* ``_isOpen``
* ``_setBufferSize`` / ``_setMaxFileSize``
* size/frame query methods

DataWriter Class Documentation
==============================

.. autoclass:: pyrogue.DataWriter
   :members:
   :member-order: bysource
   :inherited-members:
