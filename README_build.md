# Building Rogue

This README provides instructions for building rogue outside of the anaconda environment.

## Installing Packages Required For Rogue

The following packages are required to build the rogue library:

- cmake   >= 3.5
- Boost   >= 1.58
- python3 >= 3.6
- bz2

To add these packages on Ubuntu 17.04 (or later):

````
$ apt-get install cmake (or cmake3)
$ apt-get install python3
$ apt-get install libboost-all-dev
$ apt-get install libbz2-dev
$ apt-get install python3-pip
$ apt-get install git
$ apt-get install libzmq3-dev
$ apt-get install python3-pyqt5 (or python3-pyqt4)
````

To add these packages on archlinux:

````
$ pacman -S cmake
$ pacman -S python3
$ pacman -S boost
$ pacman -S bzip2
$ pacman -S python-pip
$ pacman -S git
$ pacman -S zeromq
$ pacman -S python-pyqt5 (or python-pyqt4)
````

Epics V3 support is and optional module that will be included in the rogue build
if the EPICS_BASE directory is set in the user's environment.

### Python packages required

The following python packages are required to use rogue in the python3
environment. Currently I am using PIP to install these, but you are free 
to use your favorite python tool.

````
$ pip3 install PyYAML
$ pip3 install Pyro4 
$ pip3 install parse
$ pip3 install click
$ pip3 install pyzmq
$ pip3 install mysqlclient
````

## Building & Installing Rogue

There are three possible modes for building/installing rogue:

- Local:
   Rogue is going to be used in the local checkout directory. A setup script is generated to add rogue to the system environment.

- Custom:
   Rogue is going to be installed in a custom non-system directory. A setup script is generated to add rogue to the system environment.

- System:
   The rogue headers and libraries will be installed to a standard system directory and the python filed will be installed using the system python package installed.

### Local Install

````
$ git clone https://github.com/slaclab/rogue.git
$ cd rogue
$ mkdir build
$ cd build
$ cmake .. -DROGUE_INSTALL=local
$ make
$ make install
$ source ../setup_rogue.csh (or .sh)
````

### Custom Install

````
$ git clone https://github.com/slaclab/rogue.git
$ cd rogue
$ mkdir build
$ cd build
$ cmake .. -DROGUE_INSTALL=custom -DROGUE_DIR=/path/to/custom/dir
$ make
$ make install
$ source /path/to/custom/dir/setup_rogue.csh (or .sh)
````

### System Install

````
$ git clone https://github.com/slaclab/rogue.git
$ cd rogue
$ mkdir build
$ cd build
$ cmake .. -DROGUE_INSTALL=system
$ make
$ make install
````

### Updating rogue

to update from git and rebuild:
````
$ git pull
$ cd build
$ make rebuild_cache
$ make clean
$ make install
````

