.. _pyrogue_tree_node_device_streamwriter:

=========================
StreamWriter Device Class
=========================

:py:class:`pyrogue.utilities.fileio.StreamWriter` is a concrete
:ref:`DataWriter <pyrogue_tree_node_device_datawriter>` implementation for
recording one or more stream channels to file.

Key points:

* supports channelized writing via :py:meth:`getChannel`
* can emit configuration/status frames at open/close
* supports options such as raw mode and error-frame handling

StreamWriter Class Documentation
================================

.. autoclass:: pyrogue.utilities.fileio.StreamWriter
   :members:
   :member-order: bysource
   :inherited-members:
