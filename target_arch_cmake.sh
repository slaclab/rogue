#!/usr/bin/bash
# Run this from a subdirectory to do a custom local NO_PYTHON build.
# Example:
# ./target_arch_cmake.sh
mkdir -p $EPICS_HOST_ARCH
cd $EPICS_HOST_ARCH
source $PSPKG_ROOT/etc/env_add_pkg.sh cmake/3.15.0
source $PSPKG_ROOT/etc/env_add_pkg.sh zeromq/4.1.5
#cmake .. -DROGUE_INSTALL=local -DROGUE_DIR=. -DNO_PYTHON=TRUE -DSTATIC_LIB=TRUE
cmake .. -DROGUE_INSTALL=target_arch -DNO_PYTHON=TRUE -DSTATIC_LIB=TRUE
make install
