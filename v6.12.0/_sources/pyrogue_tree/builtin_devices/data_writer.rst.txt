.. _pyrogue_tree_node_device_datawriter:

=======================
DataWriter Device Class
=======================

:py:class:`~pyrogue.DataWriter` is a base device for writing received stream
frames to files. It defines the normal tree-facing control surface for a file
writer, but it does not implement the actual file format or stream endpoint by
itself. For application use,
:py:class:`~pyrogue.utilities.fileio.StreamWriter` is the concrete subclass you
should typically instantiate. In the current implementation it provides:

* ``DataFile`` for the selected output path
* ``Open``, ``Close``, and ``AutoName`` commands
* Status variables such as ``IsOpen``, ``CurrentSize``, ``TotalSize``,
  ``Bandwidth``, and ``FrameCount``
* Writer controls such as ``BufferSize`` and ``MaxFileSize``

That makes ``DataWriter`` the reusable base class for file-writer devices that
should look like ordinary PyRogue nodes in the tree.

When To Use DataWriter
======================

Use ``DataWriter`` when you are implementing a custom file-writing device and
want to reuse the standard PyRogue control/status Variables and commands.

If you only want to record stream traffic to file, use
:py:class:`~pyrogue.utilities.fileio.StreamWriter`, documented in
:doc:`/built_in_modules/utilities/fileio/writing`, which is the concrete
built-in subclass most applications actually instantiate.

What You Usually Set
====================

Most ``DataWriter`` subclasses care about only a few constructor parameters:

* ``hidden`` when the writer should stay out of the main user tree
* ``bufferSize`` for filesystem buffering
* ``maxFileSize`` for rolling to a new file after a size limit

How Subclassing Works
=====================

``DataWriter`` is intentionally a base class. The core file operations are
empty or stub implementations until a subclass supplies the real writer
backend.

The main override points are:

* :py:meth:`~pyrogue.DataWriter._open`
* :py:meth:`~pyrogue.DataWriter._close`
* :py:meth:`~pyrogue.DataWriter._isOpen`
* :py:meth:`~pyrogue.DataWriter._setBufferSize`
* :py:meth:`~pyrogue.DataWriter._setMaxFileSize`
* :py:meth:`~pyrogue.DataWriter._getCurrentSize`
* :py:meth:`~pyrogue.DataWriter._getTotalSize`
* :py:meth:`~pyrogue.DataWriter._getBandwidth`
* :py:meth:`~pyrogue.DataWriter._getFrameCount`

That split is what lets ``StreamWriter`` reuse the same tree-facing controls
while delegating the actual writing behavior to the Rogue file-I/O utility.

The base class always creates the same operator-facing controls:

* ``DataFile`` holds the path that ``Open`` will use.
* ``Open`` and ``Close`` control the underlying writer.
* ``AutoName`` creates a timestamped filename using the current ``DataFile``
  directory, if any.
* ``BufferSize`` and ``MaxFileSize`` are writable control points.
* ``IsOpen``, ``CurrentSize``, ``TotalSize``, ``Bandwidth``, and
  ``FrameCount`` are read-only status/monitoring fields.

This common interface is useful because scripts and GUIs can treat custom
writers and built-in writers the same way at the tree level.

Related Topics
==============

* Concrete stream-to-file writer: :doc:`/built_in_modules/utilities/fileio/writing`
* Stream replay from file: :doc:`/built_in_modules/utilities/fileio/reading`
* Rogue file-I/O utilities: :doc:`/built_in_modules/utilities/fileio/index`
* Built-in module catalog beyond top-level ``pyrogue`` Devices: :doc:`/built_in_modules/index`

API Reference
=============

See :doc:`/api/python/pyrogue/datawriter` for generated API details.
