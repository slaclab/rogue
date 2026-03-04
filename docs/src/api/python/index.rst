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

pyrogue.interfaces
------------------

Client/server and interface wrappers for remote access and integration.

.. toctree::
   :maxdepth: 1

   interfaces_oscommandmemoryslave
   interfaces_simpleclient
   interfaces_virtualclient
   interfaces_zmqserver

pyrogue.interfaces.stream
-------------------------

Stream-facing Python interface bindings.

.. toctree::
   :maxdepth: 1

   interfaces_stream_variable

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
