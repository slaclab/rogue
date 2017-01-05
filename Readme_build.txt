To build the rogue base package you need the following:

See Readme_zeromq.txt  for ZEROMQ  package requirements and installation
See Readme_python2.txt for python2 package requirements and installation
See Readme_python3.txt for python3 package requirements and installation
See Readme_boost.txt   for boost   package requirements and installation
See Readme_epics.txt   for epics   package requirements and installation

To build this package you must first setup the environment. A
template file setup_template.csh is provided as an example. To 
use this file execute the following in your tcsh:

> source setup_template.csh

An RCE version is available as well

> source setup_rce.csh

If using a different shell the equivelent setup file for that shell 
must be created.

--------------------------------------
Building Rogue
--------------------------------------

Download the rogue package

> git clone https://github.com/slaclab/rogue.git
> cd rogue
> git submodule init
> git submodule update
> source setup_template.csh (or your custom version)
> make

