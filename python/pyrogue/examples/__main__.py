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
    "--epics4",
    action   = 'store_true',
    required = False,
    default  = False,
    help     = "Enable EPICS 4",
)

parser.add_argument(
    "--map",
    action   = 'store_true',
    required = False,
    default  = False,
    help     = "Store address map",
)

# Get the arguments
args = parser.parse_args()

#import logging
#rogue.Logging.setLevel(rogue.Logging.Debug)

#logger = logging.getLogger('pyrogue')
#logger.setLevel(logging.DEBUG)

with pyrogue.examples.ExampleRoot(epics4En=args.epics4) as root:
    if args.map:
        root.saveAddressMap('addr_map.csv')
        root.saveAddressMap('addr_map.h',headerEn=True)

    if args.gui:
        import pyrogue.pydm
        ui = pyrogue.pydm.__path__[0] + '/examples/rogue_plugin_test.ui'
        pyrogue.pydm.runPyDM(root=root,ui=ui,title='Test UI',sizeX=1000,sizeY=500)

    else:
        pyrogue.waitCntrlC()
