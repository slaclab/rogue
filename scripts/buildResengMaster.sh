#!/bin/bash

BASE=/afs/slac.stanford.edu/g/reseng/rogue
BUILD=/tmp

# Setup environment
export MODULEPATH=/usr/share/Modules/modulefiles:/etc/modulefiles:/afs/slac.stanford.edu/package/spack/share/spack/modules/linux-rhel6-x86_64
module load cmake-3.9.4-gcc-4.9.4-ofjqova
source /afs/slac.stanford.edu/g/reseng/python/3.6.1/settings.sh
source /afs/slac.stanford.edu/g/reseng/boost/1.64.0/settings.sh
source /afs/slac.stanford.edu/g/reseng/zeromq/4.2.0/settings.sh
source /afs/slac.stanford.edu/g/reseng/epics/base-R3-15-5-1-0/settings.sh

# Remove old build
rm -rf ${DEST}

# Download Rogue
cd ${BUILD}
git clone -b master https://github.com/slaclab/rogue.git 
cd rogue

# Branch and destination
TAG=`git describe --tags`
DEST=${BASE}/${TAG}
rm -rf ${DEST}

# Build
mkdir build
cd build
cmake .. -DROGUE_INSTALL=custom -DROGUE_DIR=${DEST}
make -j 6 install

# Update config files
sed -i.bak s/#source/source/g ${DEST}/setup_rogue.sh
sed -i.bak s/#source/source/g ${DEST}/setup_rogue.csh
rm -rf ${BASE}/master
ln -sf ${DEST} ${BASE}/master

# Cleanup
cd ${BUILD}
rm -rf rogue
rm -f ${DEST}/*.bak

