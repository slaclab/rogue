#!/usr/bin/env python3
#-----------------------------------------------------------------------------
# Title      : Example server test script
#-----------------------------------------------------------------------------
# This file is part of the rogue_example software. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue_example software, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
import pyrogue.examples
import logging
import argparse

# Set the argument parser
parser = argparse.ArgumentParser('Example Server')

parser.add_argument(
    "--gui",
    action   = 'store_true',
    required = False,
    default  = False,
    help     = "Use gui",
)

parser.add_argument(
    "--epics3",
    action   = 'store_true',
    required = False,
    default  = False,
    help     = "Enable EPICS 3",
)

parser.add_argument(
    "--epics4",
    action   = 'store_true',
    required = False,
    default  = False,
    help     = "Enable EPICS 4",
)

# Get the arguments
args = parser.parse_args()

#rogue.Logging.setFilter('pyrogue.epicsV3.Value',rogue.Logging.Debug)
#rogue.Logging.setLevel(rogue.Logging.Debug)

#logger = logging.getLogger('pyrogue')
#logger.setLevel(logging.DEBUG)

with pyrogue.examples.ExampleRoot() as root:
    root.saveAddressMap('addr_map.csv')
    root.saveAddressMap('addr_map.h',headerEn=True)

    if args.oldGui:
        import pyrogue.gui
        pyrogue.gui.runGui(root=root)

    elif args.gui:
        import pyrogue.pydm
        pyrogue.pydm.runPyDM(root=dummyTree,title='test123',sizeX=1000,sizeY=500)

    else:
        pyrogue.waitCntrlC()
