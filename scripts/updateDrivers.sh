#!/bin/bash
# ----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
# ----------------------------------------------------------------------------

# Current directory
LOC_DIR=$(dirname -- "$(readlink -f ${BASH_SOURCE[0]})")

DEST_DIR=${LOC_DIR}/../include/rogue/hardware/drivers/
BASE_URL=https://raw.githubusercontent.com/slaclab/aes-stream-drivers/master/include

for f in DmaDriver.h AxisDriver.h PgpDriver.h; do
   echo "Getting ${BASE_URL}/${f} -> ${DEST_DIR}/$f"
   wget ${BASE_URL}/${f} -O ${DEST_DIR}/$f
done

