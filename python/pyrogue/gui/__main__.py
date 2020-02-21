#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

import argparse
import pyrogue
import pyrogue.interfaces
import pyrogue.gui
import sys

parser = argparse.ArgumentParser('Pyrogue GUI Client')
parser.add_argument('--host', type=str, help='Server host name or address',default='localhost')
parser.add_argument('--port', type=int, help='Server port number',default=9099)
args = parser.parse_args()

print("Connecting to host {} port {}".format(args.host,args.port))

# Connect to the server
client = pyrogue.interfaces.VirtualClient(args.host,args.port)

# Create GUI
appTop = pyrogue.gui.application(sys.argv)
guiTop = pyrogue.gui.GuiTop(excGroups='Hidden')
guiTop.setWindowTitle("Rogue Client {}:{}".format(args.host,args.port))
guiTop.addTree(client.root)

# Run gui
appTop.exec_()
