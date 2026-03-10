.. _api_python:

Python API
==========

Canonical generated Python API reference pages, grouped by package and role.

pyrogue
-------

Core Objects
~~~~~~~~~~~~

.. toctree::
   :maxdepth: 1

   node
   root
   pollqueue
   device
   localblock
   process
   runcontrol
   datareceiver
   datawriter

Commands
~~~~~~~~

.. toctree::
   :maxdepth: 1

   basecommand
   remotecommand

Variables
~~~~~~~~~

.. toctree::
   :maxdepth: 1

   basevariable
   remotevariable
   localvariable
   linkvariable

Models
~~~~~~

.. toctree::
   :maxdepth: 1

   model
   uint
   int
   bool
   string
   float
   double
   fixed
   ufixed

Helpers
~~~~~~~

.. toctree::
   :maxdepth: 1

   wordcount
   bytecount
   reversebits
   twoscomplement
   version

pyrogue.interfaces
------------------

Client/server and interface wrappers for remote access and integration.

.. toctree::
   :maxdepth: 1

   interfaces_oscommandmemoryslave
   interfaces_sqllogger
   interfaces_sqlreader
   interfaces_simpleclient
   interfaces_virtualclient
   interfaces_zmqserver

pyrogue.interfaces.stream
-------------------------

Stream-facing Python interface bindings.

.. toctree::
   :maxdepth: 1

   interfaces_stream_master
   interfaces_stream_slave
   interfaces_stream_frame
   interfaces_stream_fifo
   interfaces_stream_filter
   interfaces_stream_ratedrop
   interfaces_stream_tcpcore
   interfaces_stream_tcpclient
   interfaces_stream_tcpserver
   interfaces_stream_variable

pyrogue.interfaces.memory
-------------------------

Memory-facing Python interface bindings.

.. toctree::
   :maxdepth: 1

   interfaces_memory_master
   interfaces_memory_slave
   interfaces_memory_hub
   interfaces_memory_transaction
   interfaces_memory_block
   interfaces_memory_emulate
   interfaces_memory_tcpclient
   interfaces_memory_tcpserver

pyrogue.protocols.epicsV4
-------------------------

EPICS PV integration classes.

.. toctree::
   :maxdepth: 1

   protocols_epicsv4_epicspvholder
   protocols_epicsv4_epicspvserver

pyrogue.utilities.fileio
------------------------

File I/O utility classes and readers/writers.

.. toctree::
   :maxdepth: 1

   utilities_fileio_filereader
   utilities_fileio_rogueheader
   utilities_fileio_streamreader
   utilities_fileio_streamwriter

pyrogue.utilities.prbs
----------------------

PRBS test and diagnostics utility classes.

.. toctree::
   :maxdepth: 1

   utilities_prbs_prbspair
   utilities_prbs_prbsrx
   utilities_prbs_prbstx

rogue.hardware
--------------

Python-visible hardware interface classes exported from Rogue C++.

.. toctree::
   :maxdepth: 1

   hardware_memmap
   hardware_axi_axistreamdma
   hardware_axi_aximemmap
