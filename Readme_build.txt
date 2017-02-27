To build the rogue base package you need the following. Some of these packages
may be available in a modern linux distribution. (see below).

See Readme_zeromq.txt  for ZEROMQ  package requirements and installation
See Readme_python2.txt for python2 package requirements and installation
See Readme_python3.txt for python3 package requirements and installation
See Readme_boost.txt   for boost   package requirements and installation
See Readme_epics.txt   for epics   package requirements and installation

To build this package you must first setup the environment. A
template file setup_template.csh is provided as an example. To 
use this file execute the following in your tcsh:

> source setup_template.csh

If using a different shell the equivelent setup file for that shell 
must be created.

--------------------------------------
Modern linux (archlinux RCE example)
--------------------------------------
In some cases on modern distributons the above packages can be 
available through the package manager:

> pacman -S python3
> pacman -S python-pip
> pacman -S boost
> pacman -S zeromq
> pacman -S pyqt4
> pacman -S python-pyqt4

> pip3 install pyzmq
> pip3 install https://github.com/zeromq/pyre/archive/master.zip
> pip3 install ipython
> pip3 install PyYAML
> pip3 install pcaspy

Epics will always need to be installed manually.

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

