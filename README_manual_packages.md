# Manual Package Installation

This readme file is only neccessary if you need to install your own
copy of the python3, boost, zeromq or epics packages. These
packages already exist on most modern Linux distributions (except epics).
These packages are also already available on AFS at SLAC.

## autoconf

A recent version of autoconf is required for some of the packages needed
by rogue. At SLAC a proper version can be found at: 

````
$ source /afs/slac.stanford.edu/g/reseng/vol11/autoconf/2.69/settings.csh
````
or
````
$ source /afs/slac.stanford.edu/g/reseng/vol11/autoconf/2.69/settings.sh
````

You need to either use the the above version or download it and compile 
it on your own. Most modern versions of linux have the appropriate version.

## Python3

Choose an install location:

````
$ mkdir /path/to/python/3.6.1
$ mkdir /path/to/python/3.6.1/src/
````

### Download and install python3

````
$ cd /path/to/python/3.6.1/src
$ wget https://www.python.org/ftp/python/3.6.1/Python-3.6.1.tgz
$ tar -xvvzpf Python-3.6.1.tar.xz
$ cd Python-3.6.1
$ ./configure --prefix=/path/to/python/3.6.1 --enable-shared
$ make 
$ make install
````

### Setup environment

- Add /path/to/python/3.6.1/bin to your $PATH
- Add /path/to/python/3.6.1/lib to your $LD_LIBRARY_PATH

It is recommended to create a settings.csh and settings.sh file in
/path/to/python/3.6.1 to allow users to add this specific python
install to their environment when needed.

### Install sip

````
$ cd /path/to/python/3.6.1/src/
$ wget https://sourceforge.net/projects/pyqt/files/sip/sip-4.19.2/sip-4.19.2.tar.gz
$ tar -xvvzpf sip-4.19.2.tar.gz
$ cd sip-4.19.2
$ python3 configure.py 
$ make 
$ make install
````

### Install pyqt4 (if you want a local GUI)

````
$ cd /path/to/python/3.6.1/src/
$ wget https://downloads.sourceforge.net/project/pyqt/PyQt4/PyQt-4.12/PyQt4_gpl_x11-4.12.tar.gz
$ tar -xvvzpf PyQt4_gpl_x11-4.12.tar.gz
$ cd PyQt4_gpl_x11-4.12
$ python3 configure-ng.py --qmake=/usr/bin/qmake-qt4 --assume-shared
$ make 
$ make install
````

### Install swig

````
$ yum install pcre-devel (or equivelent)
$ cd /path/to/python/3.6.1/src/
$ wget http://downloads.sourceforge.net/project/swig/swig/swig-3.0.12/swig-3.0.12.tar.gz
$ tar -xvvzpf swig-3.0.12.tar.gz
$ cd swig-3.0.12
$ ./configure --prefix=/path/to/python/3.6.1/ 
$ make
$ make install
````

## Boost

### Compile and install boost

````
$ mkdir /path/to/boost/1.64.0/
$ mkdir /path/to/boost/1.64.0/src
$ cd /path/to/boost/1.64.0/src
$ wget https://sourceforge.net/projects/boost/files/boost/1.64.0/boost_1_64_0.tar.gz
$ tar -xvvzpf boost_1.64_0.tar.gz
$ cd boost_1.64_0
$ source /path/to/python3/settings.csh (or settings.sh)
````

### Fix error in source file

Edit vi tools/build/src/tools/python.jam
Change line 547 to:

````
includes ?= $(prefix)/include/python$(version)m ;
(adding m after version)
````

### Build

````
$ ./bootstrap --prefix=/path/to/boost/1.64.0/ --with-python=python3
$ ./b2 
$ ./b2 install
````

Create a set of setup files: settings.csh and settings.sh in /path/to/boost/1.64.0
which setup the environment, adding /path/to/boost/1.64.0/lib to $LD_LIBRARY_PATH. 
Set $BOOST_PATH to /path/to/boost/1.64.0/ so that makefiles can find the proper path 
for include and linked libraries.

## ZeroMq

### Choose an install location:

````
$ mkdir /path/to/zeromq/4.2.1
$ mkdir /path/to/zeromq/4.2.1/src/
````

### Zeromq libraries

````
$ cd /path/to/zeromq/4.2.1/src/
$ wget https://github.com/zeromq/libzmq/releases/download/v4.2.0/zeromq-4.2.1.tar.gz
$ tar -xvvzpf zeromq-4.2.1.tar.gz
$ cd zeromq-4.2.1
$ ./autogen.sh
$ ./configure --prefix=/path/to/zeromq/4.2.1/
$ make 
$ make install
````

### Setup environment

- Add /path/to/zeromq/4.2.1/bin to your $PATH
- Add /path/to/zeromq/4.2.1/lib to your $LD_LIBRARY_PATH

It is recommended to create a settings.csh and settings.sh file in
/path/to/zeromq/4.2.1 to allow users to add this specific python
install to their environment when needed. ZEROMQ_PATH should be set
to allow makefiles to include the proper include files and libraries.

# EPICS Base

Epics install is optional. It is only required if you want to
use the epics server feature of rogue.

Choose a directory for epics. The epics install is in the 
same directory it is compiled in. 

````
$ mkdir /path/to/epics/
````

You need to set an environment variable for the host your 
are compiling on. For the RCE:

````
$ export EPICS_HOST_ARCH linux-arm
````

For one of the linux workstartions:

````
$ export EPICS_HOST_ARCH linux-x86_64
````

Get and compile epics:

````
$ cd /path/to/epics
$ wget https://www.aps.anl.gov/epics/download/base/base-3.15.1.tar.gz
$ tar -xvvzpf base-3.15.1.tar.gz
$ cd base-3.15.1
$ make
````

Once the compile is complete you will need to set the EPICS_BASE
environment variable:

````
$ export EPICS_BASE=/mnt/host/epics/base-3.15.1/
````

One complete create settings.csh and settings.sh source file in
/path/to/epics/base-3.15.1 which sets the EPICS_BASE and EPICS_HOST_ARCH
environment variables. Also add {EPICS_BASE}/bin/linux-x86_64/ to $PATH
and ${EPICS_BASE}/lib/linux-x86_64/ to $LD_LIBRARY_PATH

