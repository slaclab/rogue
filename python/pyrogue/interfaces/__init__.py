#-----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
import pyrogue
from pyrogue.interfaces._ZmqServer import *
from pyrogue.interfaces._Virtual   import *
from pyrogue.interfaces._SimpleClient import *
from pyrogue.interfaces._SqlLogging   import *
from pyrogue.interfaces._OsCommandMemorySlave import *

import time
import json
from typing import Any


# Common class for system log display
class SystemLogMonitor(object):
    """Monitor and display system log entries from variable updates.

    Parameters
    ----------
    details : bool
        If ``True``, print detailed log metadata and traceback entries.
    """

    def __init__(self, details: bool) -> None:
        self._details  = details
        self._logCount = 0

    def processLogString(self, logstr: str) -> None:
        """
        Parse and print new log entries from a JSON log string.

        Parameters
        ----------
        logstr : str
            JSON-encoded list of log entries.
        """
        lst = json.loads(logstr)

        if len(lst) > self._logCount:
            for i in range(self._logCount,len(lst)):
                vv = lst[i]['message'].replace('\n', "\n                         ")
                tags = []
                if lst[i].get('rogueCpp'):
                    tags.append('C++')
                if lst[i].get('rogueComponent') is not None:
                    tags.append(lst[i]['rogueComponent'])
                prefix = f" [{' '.join(tags)}]" if len(tags) > 0 else ''
                print("{}{}: {}".format(time.strftime("%Y-%m-%d %H:%M:%S %Z", time.localtime(lst[i]['created'])), prefix, vv))

                if self._details:
                    print("                   Name: {}".format(lst[i]['name']))
                    print("                  Level: {} ({})".format(lst[i]['levelName'],lst[i]['levelNumber']))
                    if lst[i].get('rogueCpp'):
                        print("                 Source: Rogue C++")
                    if lst[i].get('rogueComponent') is not None:
                        print("              Component: {}".format(lst[i]['rogueComponent']))
                    if lst[i].get('rogueLogger') is not None:
                        print("           Rogue Logger: {}".format(lst[i]['rogueLogger']))
                    if lst[i].get('rogueTid') is not None:
                        print("             Rogue TID: {}".format(lst[i]['rogueTid']))
                    if lst[i].get('roguePid') is not None:
                        print("             Rogue PID: {}".format(lst[i]['roguePid']))

                    if lst[i]['exception'] is not None:
                        print("              Exception: {}".format(lst[i]['exception']))

                        for v in lst[i]['traceBack']:
                            vv = v.replace('\n', "\n                         ")
                            print("                         {}".format(vv))
                    print("")

        self._logCount = len(lst)

    def varUpdated(self, key: str, varVal: pyrogue.VariableValue) -> None:
        """
        Variable listener callback. Processes SystemLog variable updates.

        Parameters
        ----------
        key : str
            Variable path.
        varVal : pr.VariableValue
            Variable value containing log data.
        """
        if 'SystemLog' in key:
            self.processLogString(varVal.value)


# Common class for variable filtering and display
class VariableMonitor(object):
    """Monitor a specific variable and display its updates.

    Parameters
    ----------
    path : str
        Full path of the variable to monitor.
    """

    def __init__(self, path: str) -> None:
        self._path = path

    def display(self, value: pyrogue.VariableValue) -> None:
        """
        Print the current variable value with timestamp.

        Parameters
        ----------
        value : object
            Variable value to display.
        """
        print("{}: {} = {}".format(time.strftime("%Y-%m-%d %H:%M:%S %Z", time.localtime(time.time())), self._path, value))

    def varUpdated(self, key: str, varVal: pyrogue.VariableValue) -> None:
        """
        Variable listener callback. Displays updates when the path matches.

        Parameters
        ----------
        key : str
            Variable path.
        varVal : object
            Variable value.
        """
        if self._path == key:
            self.display(varVal.valueDisp)
