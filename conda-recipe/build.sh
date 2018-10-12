#!/bin/bash

mkdir build
cd build
cmake .. -DROGUE_INSTALL=conda -DROGUE_DIR=${PREFIX}
make -j ${CPU_COUNT} install

#$PYTHON setup.py install --single-version-externally-managed

$PYTHON setup.py install

