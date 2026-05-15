.. _installing_full_build:

==========================
Building Rogue From Source
==========================

Native source builds outside Miniforge are mainly for Linux environments that
already manage their own system packages, deployment paths, or compiler
toolchains.

Most users should prefer the Miniforge workflows in
:ref:`installing_miniforge` or :ref:`installing_miniforge_build`. Use this path
when you specifically want Rogue integrated into an existing native build
environment.

These instructions are only relevant for Linux. For Windows and macOS, use the
Miniforge or Docker paths instead.

Installing Packages Required For Rogue
======================================

The following packages are required to build the Rogue library:

* CMake >= 3.19
* Boost >= 1.58
* Python3 >= 3.10
* Bz2

Package Manager Install
-----------------------

Debian-based systems (Ubuntu 22.04 or later)
############################################

.. code::

   $ sudo apt install cmake
   $ sudo apt install python3
   $ sudo apt install libboost-all-dev
   $ sudo apt install libbz2-dev
   $ sudo apt install python3-pip
   $ sudo apt install git
   $ sudo apt install libzmq3-dev
   $ sudo apt install python3-pyqt5
   $ sudo apt install python3-pyqt5.qtsvg

RHEL-based systems (E.g. Rocky 9)
#################################

.. code::

   $ sudo dnf install -y cmake
   $ sudo dnf install -y python3
   $ sudo dnf install -y boost-devel
   $ sudo dnf install -y boost-python3-devel
   $ sudo dnf install -y bzip2-devel
   $ sudo dnf install -y python3-pip
   $ sudo dnf install -y git
   $ sudo dnf install -y zeromq-devel
   $ sudo dnf install -y python3-qt5
   $ sudo dnf install -y python3-pyqt5-sip
   $ sudo dnf install -y qt5-qtsvg-devel

Arch Linux
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

Building & Installing Rogue
===========================

There are three supported installation modes:

- Local:
  Rogue stays associated with the local checkout. A setup script is generated
  to place that build on the shell environment.
- Custom:
  Rogue is installed into a custom non-system directory. A setup script is
  generated for that install location.
- System:
  Rogue is installed into standard system locations and the Python pieces are
  installed through the system Python environment.

Local Install
-------------

.. code::

   $ git clone https://github.com/slaclab/rogue.git
   $ cd rogue
   $ pip3 install -r pip_requirements.txt
   $ mkdir build
   $ cd build
   $ cmake .. -DROGUE_INSTALL=local
   $ make -j$(nproc)
   $ make install
   $ source ../setup_rogue.sh (or .csh, or .fish)

Custom Install
--------------

Make sure you have permission to install into the target directory. If not, use
``sudo``.

.. code::

   $ git clone https://github.com/slaclab/rogue.git
   $ cd rogue
   $ pip3 install -r pip_requirements.txt
   $ mkdir build
   $ cd build
   $ cmake .. -DROGUE_INSTALL=custom -DROGUE_DIR=/path/to/custom/dir
   $ make -j$(nproc)
   $ make install
   $ source /path/to/custom/dir/setup_rogue.sh (or .csh, or .fish)


System Install
--------------

Make sure you have permission to install into ``/usr/local``. If not, use
``sudo``.

.. code::

   $ git clone https://github.com/slaclab/rogue.git
   $ cd rogue
   $ pip3 install -r pip_requirements.txt
   $ mkdir build
   $ cd build
   $ cmake .. -DROGUE_INSTALL=system
   $ make -j$(nproc)
   $ make install

Updating Rogue
--------------

To update from Git and rebuild:

.. code::

   $ git pull
   $ cd build
   $ make rebuild_cache
   $ make clean
   $ make install

Cross-Compiling Rogue
=====================

If you want to cross-compile Rogue, first you need a working cross-compilation
toolchain and cross-compiled versions of all required dependencies.

Then create a CMake toolchain file that points the compiler variables at the
cross-toolchain binaries. The required variables are:

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

In the same file you also need to point to the cross-compiled dependency
locations using these variables:

.. code::

   BZIP2_LIBRARIES
   BZIP2_INCLUDE_DIR
   ZeroMQ_LIBRARY
   ZeroMQ_INCLUDE_DIR
   PYTHON_LIBRARY
   PYTHON_INCLUDE_DIR
   BOOST_ROOT

**Note:** For Python you also need cross-compiled versions of the required
Python packages, such as NumPy.

Once that file is defined, pass it to CMake with
``-DCMAKE_TOOLCHAIN_FILE=<file_name>``.

Example
-------

To cross-compile Rogue at SLAC using the internal ``buildroot`` toolchain, the
following toolchain file was used as an example:

.. code::

   set(CMAKE_SYSTEM_NAME               Generic)
   set(CMAKE_SYSTEM_PROCESSOR          x86_64)

   set(CMAKE_C_COMPILER_AR     /sdf/sw/epics/package/linuxRT/buildroot-2025.02/host/linux-x86_64/x86_64/bin/x86_64-linux-ar)
   set(CMAKE_ASM_COMPILER      /sdf/sw/epics/package/linuxRT/buildroot-2025.02/host/linux-x86_64/x86_64/bin/x86_64-linux-gcc)
   set(CMAKE_C_COMPILER        /sdf/sw/epics/package/linuxRT/buildroot-2025.02/host/linux-x86_64/x86_64/bin/x86_64-linux-gcc)
   set(CMAKE_CXX_COMPILER      /sdf/sw/epics/package/linuxRT/buildroot-2025.02/host/linux-x86_64/x86_64/bin/x86_64-linux-g++)
   set(CMAKE_LINKER            /sdf/sw/epics/package/linuxRT/buildroot-2025.02/host/linux-x86_64/x86_64/bin/x86_64-linux-ld)
   set(CMAKE_OBJCOPY           /sdf/sw/epics/package/linuxRT/buildroot-2025.02/host/linux-x86_64/x86_64/bin/x86_64-linux-objcopy)
   set(CMAKE_C_COMPILER_RANLIB /sdf/sw/epics/package/linuxRT/buildroot-2025.02/host/linux-x86_64/x86_64/bin/x86_64-linux-ranlib)
   set(CMAKE_SIZE              /sdf/sw/epics/package/linuxRT/buildroot-2025.02/host/linux-x86_64/x86_64/bin/x86_64-linux-size)
   set(CMAKE_STRIP             /sdf/sw/epics/package/linuxRT/buildroot-2025.02/host/linux-x86_64/x86_64/bin/x86_64-linux-strip)

   set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
   set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
   set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)

   # Define location of BZIP2 (cross-compiled)
   set(BZIP2_LIBRARIES   /sdf/sw/epics/package/bzip2/1.0.8/buildroot-2025.02-x86_64/lib/libbz2.a)
   set(BZIP2_INCLUDE_DIR /sdf/sw/epics/package/bzip2/1.0.8/buildroot-2025.02-x86_64/include)

   # Define the location of ZMQ (cross-compiled).
   # ZMQ must be cross-compiled locally; no pre-built package exists on SDF.
   set(ZeroMQ_LIBRARY     /path/to/cross-compiled/libzmq.a)
   set(ZeroMQ_INCLUDE_DIR /path/to/cross-compiled/include)

   # Define the location of python3 (cross-compiled).
   # The buildroot-2025.02 toolchain bundles Python 3.12 in its host directory.
   set(PYTHON_LIBRARY     /sdf/sw/epics/package/linuxRT/buildroot-2025.02/host/linux-x86_64/x86_64/lib/libpython3.12.so)
   set(PYTHON_INCLUDE_DIR /sdf/sw/epics/package/linuxRT/buildroot-2025.02/host/linux-x86_64/x86_64/include/python3.12)

   # Define the location of boost (cross-compiled)
   set(BOOST_ROOT /sdf/sw/epics/package/boost/1.64.0/buildroot-2025.02-x86_64)

Then build Rogue as described above, but add the
``CMAKE_TOOLCHAIN_FILE`` variable when calling CMake:

.. code::

   cmake .. -DCMAKE_TOOLCHAIN_FILE=buildroot-2025.02-x86_64.cmake

**Note:** Pass the correct absolute or relative path to the toolchain file.
