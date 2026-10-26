#!/bin/bash
set -ex

# Version.cpp::init() requires ROGUE_VERSION to start with 'v'/'V'.
# PKG_VERSION may or may not already include the leading 'v' depending on whether
# this recipe is built from tidair-tag (with 'v') or a conda-forge feedstock (no 'v').
case "${PKG_VERSION}" in
    v*|V*) ROGUE_VERSION_STR="${PKG_VERSION}" ;;
    *)     ROGUE_VERSION_STR="v${PKG_VERSION}" ;;
esac

# source.path copies the whole clone, so drop any stale in-tree build/ first
rm -rf build

cmake ${CMAKE_ARGS} \
    -DROGUE_INSTALL=conda \
    -DROGUE_DIR=${PREFIX} \
    -DROGUE_VERSION=${ROGUE_VERSION_STR} \
    -DCMAKE_BUILD_TYPE=Release \
    -DPython3_EXECUTABLE="$PYTHON" \
    -S "${SRC_DIR}" \
    -B build

cmake --build build --parallel ${CPU_COUNT}
cmake --install build
