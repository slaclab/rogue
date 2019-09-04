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
import time
import jsonpickle

# Class for system log monitoring
class SystemLogMonitor(object):

    def __init__(self,details):
        self._details  = details
        self._logCount = 0

    def processLogString(self, logstr):
        lst = jsonpickle.decode(logstr)

        if len(lst) > self._logCount:
            for i in range(self._logCount,len(lst)):
                vv = lst[i]['message'].replace('\n', "\n                         ")
                print("{}: {}".format(time.strftime("%Y-%m-%d %H:%M:%S %Z", time.localtime(lst[i]['created'])),vv))

                if self._details:
                    print("                   Name: {}".format(lst[i]['name']))
                    print("                  Level: {} ({})".format(lst[i]['levelName'],lst[i]['levelNumber']))

                    if lst[i]['exception'] is not None:
                        print("              Exception: {}".format(lst[i]['exception']))

                        for v in lst[i]['traceBack']:
                            vv = v.replace('\n', "\n                         ")
                            print("                         {}".format(vv))
                    print("")

        self._logCount = len(lst)

    def varUpdated(self, key, varVal):
        if 'SystemLog' in key:
            self.processLogString(varVal.value)

class VariableMonitor(object):
    def __init__(self,path):
        self._path = path

    def varUpdated(self, key, varVal):
        if self._path == key:
            print("{}: {} = {}".format(time.strftime("%Y-%m-%d %H:%M:%S %Z", time.localtime(time.time())), key, varVal.valueDisp))


parser = argparse.ArgumentParser('Pyrogue Client')

parser.add_argument('--host', 
                    type=str, 
                    help='Server host name or address',
                    default='localhost')

parser.add_argument('--port', 
                    type=int, 
                    help='Server port number',
                    default=9099)

parser.add_argument('--details',
                    help='Show log details with stacktrace (cmd=syslog)',
                    action='store_true')

parser.add_argument('cmd',    
                    type=str, 
                    choices=['gui','syslog','monitor','get','value','set','exec'], 
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

# System log
elif args.cmd == 'syslog':
    sl = SystemLogMonitor(args.details)
    client = pyrogue.interfaces.SimpleClient(args.host,args.port,cb=sl.varUpdated)

    print("Listening for system log message:")
    print("")

    sl.processLogString(client.value('root.SystemLog'))

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        client.stop()
        exit()

# Variable Monitor
elif args.cmd == 'monitor':
    if args.path is None:
        print("Error: A path must be provided")
        exit()

    vm = VariableMonitor(args.path)
    client = pyrogue.interfaces.SimpleClient(args.host,args.port,cb=vm.varUpdated)

    ret = client.valueDisp(args.path)
    print("")
    print("{}: {} = {}".format(time.strftime("%Y-%m-%d %H:%M:%S %Z", time.localtime(time.time())), args.path, ret))

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        client.stop()
        exit()

# All Other Commands
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

