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

parser = argparse.ArgumentParser('Pyrogue Client')

parser.add_argument('--host', 
                    type=str, 
                    help='Server host name or address',
                    default='localhost')

parser.add_argument('--port', 
                    type=int, 
                    help='Server port number',
                    default=9099)

parser.add_argument('cmd',    
                    type=str, 
                    choices=['gui','get','value','set','exec'], 
                    help='Client command to issue')

parser.add_argument('path',
                    type=str,
                    nargs='?',
                    help='Path to access')

parser.add_argument('value',
                    type=str, 
                    nargs='?',
                    help='Value to set')

args = parser.parse_args()

print("Connecting to host {} port {}".format(args.host,args.port))

# Connect to the gui server
if args.cmd == 'gui':
    client = pyrogue.interfaces.VirtualClient(args.host,args.port)

    # Create GUI
    appTop = pyrogue.gui.application(sys.argv)
    guiTop = pyrogue.gui.GuiTop(excGroups='Hidden')
    guiTop.setWindowTitle("Rogue Client {}:{}".format(args.host,args.port))
    guiTop.addTree(client.root)

    # Run gui
    appTop.exec_()

# Connect to the simple server
else:

    client = pyrogue.interfaces.SimpleClient(args.host,args.port)

    if args.path is None:
        print("Error: A path must be provided")
        exit()

    elif args.cmd == 'get':
        ret = client.getDisp(args.path)

    elif args.cmd == 'value':
        ret = client.valueDisp(args.path)

    elif args.cmd == 'set':
        if args.value is None:
            print("Error: A value must be provided")
            exit()
        else:
            client.setDisp(args.path,args.value)
            ret = None

    elif args.cmd == 'exec':
        ret = client.exec(args.path,args.value)

    if ret is not None:
        print(f"\nRet = {ret}")

