#!/bin/bash

mkdir build
cd build
cmake .. -DROGUE_INSTALL=conda -DROGUE_DIR=${PREFIX} -DCMAKE_BUILD_TYPE=RelWithDebInfo
make -j ${CPU_COUNT} install

mkdir -p $PREFIX/etc/conda/activate.d
cat <<EOF > $PREFIX/etc/conda/activate.d/rogue_activate.sh
export EPICS_BASE_LIB="\${CONDA_PREFIX}/epics/lib/${EPICS_HOST_ARCH}"
export EPICS_PCAS_LIB="\${CONDA_PREFIX}/pcas/lib/${EPICS_HOST_ARCH}"
export LD_LIBRARY_PATH=\${EPICS_BASE_LIB}:\${EPICS_PCAS_LIB}\${LD_LIBRARY_PATH:+:\$LD_LIBRARY_PATH}
EOF

mkdir -p $PREFIX/etc/conda/deactivate.d
cat <<EOF > $PREFIX/etc/conda/deactivate.d/rogue_deactivate.sh
unset EPICS_BASE_LIB
unset EPICS_PCAS_LIB
EOF

