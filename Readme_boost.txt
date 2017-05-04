Compile and install boost

Linux distributions with a modern version of boost can skip this step. Arch-linux 
installations, for example, can use the standard boost package that is included.

Boost is available on slac afs at:

/afs/slac.stanford.edu/g/reseng/boost/1.62.0_p3/

If you need to install boost on your local machine see the following steps:

> mkdir /path/to/boost/1.62.0/
> mkdir /path/to/boost/1.62.0/src
> cd /path/to/boost/1.62.0/src

> wget https://sourceforge.net/projects/boost/files/boost/1.62.0/boost_1_62_0.tar.gz
> tar -xvvzpf boost_1_62_0.tar.gz
> cd boost_1_62_0
> source /path/to/python3/settings.csh (or settings.sh)

In some cases you will need to edit: tools/build/src/tools/python.jam to fix
a compile error. I have seen this on redhat machines:
Change line 542 to:

includes ?= $(prefix)/include/python$(version)m ;
(adding m after version)

Make sure before running this step you have your path setup with the python3 bin and lib directory.

> ./bootstrap --prefix=/path/to/boost/1.62.0/ --with-python=python3
> ./b2 
> ./b2 install

Create a set of setup files: settings.csh and settings.sh in /path/to/boost/1.62.0
which setup the environment, adding /path/to/boost/1.62.0/lib to $LD_LIBRARY_PATH. 
Set $BOOST_PATH to /path/to/boost/1.62.0/ so that makefiles can find the proper path 
for include and linked libraries.

