#!/bin/bash

mkdir build
cd build; cmake .. -DROGUE_INSTALL=system -DROGUE_DIR=${PREFIX}
cd build; make -j ${CPU_COUNT} install

