.. _installing_full_build:

==========================
Building Rogue From Source
==========================

The following instructions demonstrate how to build rogue outside of the anaconda environment. These
instructions are only relevant for the Linux and MacOS operating systems. See :ref:`installing_anaconda` or
:ref:`installing_docker` for Windows and MacOS.

Installing Packages Required For Rogue
======================================

The following packages are required to build the rogue library:

* cmake   >= 3.5
* Boost   >= 1.58
* python3 >= 3.6
* bz2

Package Manager Install
-----------------------

Ubuntu 18.04 (or later)
########################

.. code::

   $ apt-get install cmake
   $ apt-get install python3
   $ apt-get install libboost-all-dev
   $ apt-get install libbz2-dev
   $ apt-get install python3-pip
   $ apt-get install git
   $ apt-get install libzmq3-dev
   $ apt-get install python3-pyqt5
   $ apt-get install python3-pyqt5.qtsvg

archlinux:
##########

.. code::

   $ pacman -S cmake
   $ pacman -S python3
   $ pacman -S boost
   $ pacman -S bzip2
   $ pacman -S python-pip
   $ pacman -S git
   $ pacman -S zeromq
   $ pacman -S python-pyqt5

MacOs:
#######

Information on the homebrew package manager can be found at: `<https://brew.sh/>`_

.. code::

   $ brew install cmake
   $ brew install python3
   $ brew install boost
   $ brew install bzip2
   $ brew install python-pip
   $ brew install git
   $ brew install zeromq
   $ brew install pyqt5

Epics V3 support is and optional module that will be included in the rogue build
if the EPICS_BASE directory is set in the user's environment.

Building & Installing Rogue
===========================

There are three possible modes for building/installing rogue:

* Local:
   Rogue is going to be used in the local checkout directory. A setup script is generated to add rogue to the system environment.

* Custom:
   Rogue is going to be installed in a custom non-system directory. A setup script is generated to add rogue to the system environment.

* System:
   The rogue headers and libraries will be installed to a standard system directory and the python filed will be installed using the system python package installed.

Local Install
-------------

.. code::

   $ git clone https://github.com/slaclab/rogue.git
   $ cd rogue
   $ pip3 install -r pip_requirements.txt
   $ mkdir build
   $ cd build
   $ cmake .. -DROGUE_INSTALL=local
   $ make
   $ make install
   $ source ../setup_rogue.csh (or .sh)

Custom Install
--------------

Make sure you have permission to install into the passed install directory, if not use sudo.

.. code::

   $ git clone https://github.com/slaclab/rogue.git
   $ cd rogue
   $ pip3 install -r pip_requirements.txt
   $ mkdir build
   $ cd build
   $ cmake .. -DROGUE_INSTALL=custom -DROGUE_DIR=/path/to/custom/dir
   $ make
   $ make install
   $ source /path/to/custom/dir/setup_rogue.csh (or .sh)


System Install
--------------

Make sure you have permission to install into the /usr/local/ directory, if not use sudo.

.. code::

   $ git clone https://github.com/slaclab/rogue.git
   $ cd rogue
   $ pip3 install -r pip_requirements.txt
   $ mkdir build
   $ cd build
   $ cmake .. -DROGUE_INSTALL=system
   $ make
   $ make install

Updating Rogue
--------------

to update from git and rebuild:

.. code::

   $ git pull
   $ cd build
   $ make rebuild_cache
   $ make clean
   $ make install

Cross-compiling Rogue
=====================

If you want to cross-compile rogue, first you need to have your cross-compilation toolchain setup. You also need to have cross-compiled version of all the dependencies with that toolchain.

Then, you need to create a CMake toolchain file, where you have to manually point the CMake compiler variables to the path of your cross-compiler. Those variables are:

.. code::

   CMAKE_SYSTEM_NAME
   CMAKE_SYSTEM_PROCESSOR
   CMAKE_C_COMPILER_AR
   CMAKE_ASM_COMPILER
   CMAKE_C_COMPILER
   CMAKE_CXX_COMPILER
   CMAKE_LINKER
   CMAKE_OBJCOPY
   CMAKE_C_COMPILER_RANLIB
   CMAKE_SIZE
   CMAKE_STRIP

In this file you also need to point to the location of the cross-compile version of the dependencies by using these variables:

.. code::

   BZIP2_LIBRARIES
   BZIP2_INCLUDE_DIR
   ZeroMQ_LIBRARY
   ZeroMQ_INCLUDE_DIR
   PYTHON_LIBRARY
   PYTHON_INCLUDE_DIR
   BOOST_ROOT

**Note:** for python you also need cross-compile version of its packages, like for example numpy.

Once you have that file define, you pas that file to CMake with the option ``-CMAKE_TOOLCHAIN_FILE=<file_name>``.

Example
-------

To cross-compile rogue at SLAC using our internal ``buildroot`` toolchain, we defined the following toolchain file, called ``buildroot-2019.08-x86_64.cmake``

.. code::

   set(CMAKE_SYSTEM_NAME               Generic)
   set(CMAKE_SYSTEM_PROCESSOR          x86_64)

   set(CMAKE_C_COMPILER_AR     /afs/slac/package/linuxRT/buildroot-2019.08/host/linux-x86_64/x86_64/usr/bin/x86_64-linux-ar)
   set(CMAKE_ASM_COMPILER      /afs/slac/package/linuxRT/buildroot-2019.08/host/linux-x86_64/x86_64/usr/bin/x86_64-linux-gcc)
   set(CMAKE_C_COMPILER        /afs/slac/package/linuxRT/buildroot-2019.08/host/linux-x86_64/x86_64/usr/bin/x86_64-linux-gcc)
   set(CMAKE_CXX_COMPILER      /afs/slac/package/linuxRT/buildroot-2019.08/host/linux-x86_64/x86_64/usr/bin/x86_64-linux-g++)
   set(CMAKE_LINKER            /afs/slac/package/linuxRT/buildroot-2019.08/host/linux-x86_64/x86_64/usr/bin/x86_64-linux-ld)
   set(CMAKE_OBJCOPY           /afs/slac/package/linuxRT/buildroot-2019.08/host/linux-x86_64/x86_64/usr/bin/x86_64-linux-objcopy)
   set(CMAKE_C_COMPILER_RANLIB /afs/slac/package/linuxRT/buildroot-2019.08/host/linux-x86_64/x86_64/usr/bin/x86_64-linux-ranlib)
   set(CMAKE_SIZE              /afs/slac/package/linuxRT/buildroot-2019.08/host/linux-x86_64/x86_64/usr/bin/x86_64-linux-size)
   set(CMAKE_STRIP             /afs/slac/package/linuxRT/buildroot-2019.08/host/linux-x86_64/x86_64/usr/bin/x86_64-linux-strip)

   set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
   set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
   set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)

   # Define location of BZIP2 (cross-compiled)
   set(BZIP2_LIBRARIES   /afs/slac/g/lcls/package/bzip2/1.0.6/buildroot-2019.08-x86_64/lib/libbz2.a)
   set(BZIP2_INCLUDE_DIR /afs/slac/g/lcls/package/bzip2/1.0.6/buildroot-2019.08-x86_64/include)

   # Define  the location of ZMQ (cross-compiled)
   set(ZeroMQ_LIBRARY     /afs/slac/g/lcls/package/libzmq/zeromq-4.3.4/buildroot-2019.08-x86_64/lib/libzmq.a)
   set(ZeroMQ_INCLUDE_DIR /afs/slac/g/lcls/package/libzmq/zeromq-4.3.4/buildroot-2019.08-x86_64/include)

   # Define the location of python3 (cross-compiled)
   set(PYTHON_LIBRARY     /afs/slac/g/lcls/package/python/3.6.1/buildroot-2019.08-x86_64/lib/libpython3.6m.so)
   set(PYTHON_INCLUDE_DIR /afs/slac/g/lcls/package/python/3.6.1/buildroot-2019.08-x86_64/include/python3.6m)

   # Define the location of boost (cross-compiled)
   set(BOOST_ROOT /afs/slac/g/lcls/package/boost/1.64.0/buildroot-2019.08-x86_64)

Then we build rogue as described in the previous section, but adding the ``CMAKE_TOOLCHAIN_FILE`` variable when calling CMake:

.. code::

   cmake .. -DCMAKE_TOOLCHAIN_FILE=buildroot-2019.08-x86_64.cmake

**Note:** you need to pass the correct path, either absolute or relative, of you toolchain file  to the ``CMAKE_TOOLCHAIN_FILE`` variable.
