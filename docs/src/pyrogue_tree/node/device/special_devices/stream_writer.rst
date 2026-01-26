.. _pyrogue_tree_node_device_streamwriter:

=========================
StreamWriter Device Class
=========================

StreamWriter is a subclass of :ref:`Data Writer <pyrogue_tree_node_device_datawriter>`.

* Pyrogue Device wrapper around rogue::utilities::fileio::StreamWriter
* Exposes StreamWriter methods as Variables and Commands
* Streamwriter allows multiple streams to be written to a single data file

   * A header identifies each file record, its channel # and Frame flags

* :code:`getChannel(id)`

   * Function to expose a slave interface which can be connected to a stream Master
   * Id value is placed in file record header to identify stream

StreamWriter Class Documentation
================================

.. autoclass:: pyrogue.utilities.fileio.StreamWriter
   :members:
   :member-order: bysource
   :inherited-members: