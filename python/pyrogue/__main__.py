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
import pyrogue.pydm
import time
import os

parser = argparse.ArgumentParser('Pyrogue Client')

parser.add_argument('--server',
                    type=str,
                    help="Server address: 'host:port' or list of addresses: 'host1:port1,host2:port2'",
                    default='localhost:9099')

parser.add_argument('--ui',
                    type=str,
                    help='UI File for gui (cmd=gui)',
                    default=None)

parser.add_argument('--details',
                    help='Show log details with stacktrace (cmd=syslog)',
                    action='store_true')

parser.add_argument('cmd',
                    type=str,
                    choices=['gui','syslog','monitor','get','value','set','exec','path'],
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

# Print library path
if args.cmd == 'path':
    print(os.path.dirname(__file__))
    exit()

# Common extraction for single server address
try:
    host = args.server.split(',')[0].split(':')[0]
    port = int(args.server.split(',')[0].split(':')[1])
except Exception:
    raise Exception("Failed to extract server host & port")

print("Connecting to {}".format(args.server))

# GUI Client
if args.cmd == 'gui':
    pyrogue.pydm.runPyDM(serverList=args.server,ui=args.ui)

# System log
elif args.cmd == 'syslog':
    sl = pyrogue.interfaces.SystemLogMonitor(args.details)
    client = pyrogue.interfaces.SimpleClient(host,port,cb=sl.varUpdated)

    print("Listening for system log message:")
    print("")

    sl.processLogString(client.value('root.SystemLog'))

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        client._stop()
        exit()

# Variable Monitor
elif args.cmd == 'monitor':
    if args.path is None:
        print("Error: A path must be provided")
        exit()

    vm = pyrogue.interfaces.VariableMonitor(args.path)
    client = pyrogue.interfaces.SimpleClient(host,port,cb=vm.varUpdated)

    ret = client.valueDisp(args.path)
    print("")
    vm.display(client.valueDisp(args.path))

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        client._stop()
        exit()

# All Other Commands
else:

    client = pyrogue.interfaces.SimpleClient(host,port)

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
        print(f'\nRet = {ret}')
