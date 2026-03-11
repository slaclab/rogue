.. _pyrogue_tree_node_device_streamwriter:

=========================
StreamWriter Device Class
=========================

:py:class:`~pyrogue.utilities.fileio.StreamWriter` is a concrete
:ref:`DataWriter <pyrogue_tree_node_device_datawriter>` implementation for
recording one or more stream channels to file.

Key points:

* Supports channelized writing via :py:meth:`getChannel`
* Can emit configuration/status frames at open/close
* Supports options such as raw mode and error-frame handling

Logging
=======

The underlying Rogue ``StreamWriter`` instance uses Rogue C++ logging.

- Logger name: ``pyrogue.fileio.StreamWriter``
- Configuration API:
  ``rogue.Logging.setFilter('pyrogue.fileio.StreamWriter', rogue.Logging.Debug)``

The PyRogue Device wrapper itself is mainly a control wrapper, so capture-path
diagnostics usually come from the underlying C++ writer rather than from a
separate Python logger on the wrapper.

Related Topics
==============

- :doc:`/built_in_modules/utilities/fileio/index`
- :doc:`/built_in_modules/utilities/fileio/writing`
- :doc:`data_writer`

API Reference
=============

- Python: :doc:`/api/python/utilities_fileio_streamwriter`
- C++: :doc:`/api/cpp/utilities/fileio/writer`
