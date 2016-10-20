# rogue
SLAC Python Based Hardware Abstraction &amp; Data Acquisition System

Introduction presentation: 
https://docs.google.com/presentation/d/1m2nqGzCZXsQV8ul4d0Gk7xmwn-OLW1iucTLm7LLp9eg/edit?usp=sharing

JIRA:
https://jira.slac.stanford.edu/plugins/servlet/project-config/ESROGUE

To build this package you must first setup the environment. A
template file setup_template.csh is provided as an example. To 
use this file execute the following in your tcsh:

source setup_template.csh

If using a different shell the equivelent setup file for that shell 
must be created.

This file does the following:

set PYTHONPATH environment variable to point to build directory so python
can find needed libraries on execution.

set PYTHON_CFG to the appropriate python-config executable for the local
machine. i.e. python2.6-config or python2.7-config.

Add the local build directory to the LD_LIBRARY_PATH environment variable
so that python and applications can find the shared libraries.

------------------
TODO
------------------

Proper memory allocation in Slave for Frame and Buffers. This includes allocating
space for payload as well as the variables within the clases.

Add the following:

protocols/rssi
protocols/packetizer
protocols/udp

stream Master should access primary slave last. Update code to remove primary from slave list and call it only after other slaves have been completed. This is important for zero copy.

-------------------------------------
-- NOTES
-------------------------------------

Look into adding timeout retries in the block. A block write or read request with a specific flag would spawn a thread to wait for the reply. Thsi thread would interrupt the doneTransaction call and retry if there is a timeout or error. Maybe this just get enabled per block? Timeout and retry enable should be block creation attributes.

