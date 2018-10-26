#!/bin/bash

# Current directory
LOC_DIR=$(dirname -- "$(readlink -f ${BASH_SOURCE[0]})")

DEST_DIR=${LOC_DIR}/../include/rogue/hardware/drivers/
BASE_URL=https://raw.githubusercontent.com/slaclab/aes-stream-drivers/master/include

for f in DmaDriver.h AxisDriver.h PgpDriver.h; do
   echo "Getting ${BASE_URL}/${f} -> ${DEST_DIR}/$f"
   wget ${BASE_URL}/${f} -O ${DEST_DIR}/$f
done

