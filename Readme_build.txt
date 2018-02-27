To build the rogue base package you need the following. Some of these packages
may be available in a modern linux distribution. (see below).

See Readme_python3.txt for python3 package requirements and installation (preferred)
See Readme_boost.txt   for boost   package requirements and installation

Optional packages for mesh networking and epics support:

See Readme_zeromq.txt  for ZEROMQ  package requirements and installation (optional)
See Readme_epics.txt   for epics   package requirements and installation

--------------------------------------
Modern linux (archlinux RCE example)
--------------------------------------
In some cases on modern distributons the above packages can be 
available through the package manager:

> pacman -S python3
> pacman -S python3-pip
> pacman -S boost
> pacman -S zeromq (opional for mesh networking)
> pacman -S pyqt4 (optional for GUI)
> pacman -S python-pyqt4 (optional for gui)

> pip3 install ipython
> pip3 install PyYAML
> pip3 install pyzmq (optional for mesh networking)
> pip3 install pcaspy (optional for epics)

Epics will always need to be installed manually.

--------------------------------------
Building Rogue
--------------------------------------
To build this package you must first setup the environment. A
template file setup_template.csh is provided as an example. To 
use this file execute the following in your tcsh:

> source setup_template.csh

If using a different shell the equivelent setup file for that shell 
must be created.

Download the rogue package

> git clone https://github.com/slaclab/rogue.git
> cd rogue
> git submodule init
> git submodule update
> source setup_template.csh (or your custom version)
> make

