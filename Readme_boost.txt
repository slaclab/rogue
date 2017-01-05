Compile and install boost

The boost python libraries are specific to either python version.
As far as I can tell you can't have a boost install which supports
both at the same time.

Boost with python2 support:

> mkdir /path/to/boost/1.62.0_p2/
> mkdir /path/to/boost/1.62.0_p2/src
> cd /path/to/boost/1.62.0_p2/src

> wget https://sourceforge.net/projects/boost/files/boost/1.62.0/boost_1_62_0.tar.gz
> tar -xvvzpf boost_1_62_0.tar.gz
> cd boost_1_62_0
> source /path/to/python2/settings.csh (or settings.sh)
> ./bootstrap --prefix=/path/to/boost/1.62.0_p2/ --with-python=python2
> ./b2 
> ./b2 install

Create a set of setup files: settings.csh and settings.sh in /path/to/boost/1.62.0_p2
which setup the environment, adding /path/to/boost/1.62.0_p2/lib to $LD_LIBRARY_PATH. 
Set $BOOST_PATH to /path/to/boost/1.62.0_p2/ so that makefiles can find the proper path 
for include and linked libraries.

Boost with python3 support:

> mkdir /path/to/boost/1.62.0_p3/
> mkdir /path/to/boost/1.62.0_p3/src
> cd /path/to/boost/1.62.0_p3/src

> wget https://sourceforge.net/projects/boost/files/boost/1.62.0/boost_1_62_0.tar.gz
> tar -xvvzpf boost_1_62_0.tar.gz
> cd boost_1_62_0
> source /path/to/python3/settings.csh (or settings.sh)

Edit vi tools/build/src/tools/python.jam
Change line 542 to:

includes ?= $(prefix)/include/python$(version)m ;
(adding m after version)

> ./bootstrap --prefix=/path/to/boost/1.62.0_p3/ --with-python=python3
> ./b2 
> ./b2 install

Create a set of setup files: settings.csh and settings.sh in /path/to/boost/1.62.0_p3
which setup the environment, adding /path/to/boost/1.62.0_p3/lib to $LD_LIBRARY_PATH. 
Set $BOOST_PATH to /path/to/boost/1.62.0_p3/ so that makefiles can find the proper path 
for include and linked libraries.

