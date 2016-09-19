# rogue
SLAC Python Based Hardware Abstraction &amp; Data Acquisition System

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

