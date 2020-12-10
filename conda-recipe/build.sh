#!/bin/bash

mkdir build
cd build
cmake .. -DROGUE_INSTALL=conda -DROGUE_DIR=${PREFIX} -DCMAKE_BUILD_TYPE=RelWithDebInfo
ls -lR $PREFIX/epics/include/compiler/
make -j ${CPU_COUNT} install

