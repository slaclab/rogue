Compile and install boost

> mkdir /path/to/boost/1.64.0/
> mkdir /path/to/boost/1.64.0/src
> cd /path/to/boost/1.64.0/src

> wget https://sourceforge.net/projects/boost/files/boost/1.64.0/boost_1.64_0.tar.gz
> tar -xvvzpf boost_1.64_0.tar.gz
> cd boost_1.64_0
> source /path/to/python3/settings.csh (or settings.sh)

Edit vi tools/build/src/tools/python.jam
Change line 547 to:

includes ?= $(prefix)/include/python$(version)m ;
(adding m after version)

> ./bootstrap --prefix=/path/to/boost/1.64.0/ --with-python=python3
> ./b2 
> ./b2 install

Create a set of setup files: settings.csh and settings.sh in /path/to/boost/1.64.0
which setup the environment, adding /path/to/boost/1.64.0/lib to $LD_LIBRARY_PATH. 
Set $BOOST_PATH to /path/to/boost/1.64.0/ so that makefiles can find the proper path 
for include and linked libraries.

