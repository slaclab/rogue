#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

from pyrogue.interfaces._ZmqServer import *
from pyrogue.interfaces._Virtual   import *
from pyrogue.interfaces._SimpleClient import *
from pyrogue.interfaces._SqlLogging   import *

import time
import json

# Common class for system log display
class SystemLogMonitor(object):

    def __init__(self,details):
        self._details  = details
        self._logCount = 0

    def processLogString(self, logstr):
        lst = json.loads(logstr)

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


# Common class for variable filtering and display
class VariableMonitor(object):
    def __init__(self,path):
        self._path = path

    def display(self,value):
        print("{}: {} = {}".format(time.strftime("%Y-%m-%d %H:%M:%S %Z", time.localtime(time.time())), self._path, value))

    def varUpdated(self, key, varVal):
        if self._path == key:
            self.display(varVal.valueDisp)


