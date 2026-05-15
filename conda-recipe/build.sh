#!/bin/bash
set -ex

CPU_COUNT="${CPU_COUNT:-$(nproc)}"

rm -rf build
mkdir build
cd build

# Version.cpp::init() requires ROGUE_VERSION to start with 'v'/'V'.
# PKG_VERSION may or may not already include the leading 'v' depending on whether
# this recipe is built from tidair-tag (with 'v') or a conda-forge feedstock (no 'v').
case "${PKG_VERSION}" in
    v*|V*) ROGUE_VERSION_STR="${PKG_VERSION}" ;;
    *)     ROGUE_VERSION_STR="v${PKG_VERSION}" ;;
esac

cmake ${CMAKE_ARGS} .. \
    -DROGUE_INSTALL=conda \
    -DROGUE_DIR=${PREFIX} \
    -DROGUE_VERSION=${ROGUE_VERSION_STR} \
    -DCMAKE_BUILD_TYPE=Release \
    -DPython3_EXECUTABLE="$PYTHON"

cmake --build . -j ${CPU_COUNT}
cmake --install .
