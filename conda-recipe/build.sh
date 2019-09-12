#!/bin/bash

mkdir build
cd build
cmake .. -DROGUE_INSTALL=conda -DROGUE_DIR=${PREFIX}
make -j ${CPU_COUNT} install

mkdir -p $PREFIX/etc/conda/activate.d
mkdir -p $PREFIX/etc/conda/deactivate.d
scp $RECIPE_DIR/rogue_activate.sh   $PREFIX/etc/conda/activate.d/rogue.sh
scp $RECIPE_DIR/rogue_deactivate.sh $PREFIX/etc/conda/deactivate.d/rogue.sh

