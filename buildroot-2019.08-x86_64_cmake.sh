#!/usr/bin/bash
# Run this to do a custom local NO_PYTHON linuxRT-x86_64 build.
# Example:
# ./target_arch_cmake.sh
TOOLCHAIN=buildroot-2019.08-x86_64
mkdir $TOOLCHAIN
ln -s $TOOLCHAIN linuxRT-x86_64
cd $TOOLCHAIN
source $PSPKG_ROOT/etc/env_add_pkg.sh cmake/3.15.0
cmake .. -DROGUE_INSTALL=target_arch -DNO_PYTHON=TRUE -DSTATIC_LIB=TRUE -DCMAKE_TOOLCHAIN_FILE=../$TOOLCHAIN.cmake
make install
