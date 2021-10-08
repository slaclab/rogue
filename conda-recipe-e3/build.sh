#!/bin/bash

mkdir build
cd build
cmake .. -DROGUE_INSTALL=conda -DROGUE_DIR=${PREFIX} -DCMAKE_BUILD_TYPE=RelWithDebInfo -DDO_EPICS=1
make -j ${CPU_COUNT} install

