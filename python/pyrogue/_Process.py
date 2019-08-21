#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Title      : PyRogue base module - Process Device Class
#-----------------------------------------------------------------------------
# File       : pyrogue/_Process.py
# Created    : 2019-08-06
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to 
# the license terms in the LICENSE.txt file found in the top-level directory 
# of this distribution and at: 
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html. 
# No part of the rogue software platform, including this file, may be 
# copied, modified, propagated, or distributed except according to the terms 
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
import rogue.interfaces.memory as rim
import collections
import datetime
import functools as ft
import pyrogue as pr
import inspect
import threading
import math
import time

class Process(pr.Device):
    """Special base class to execute processes."""

    def __init__(self, **kwargs):

        pr.Device.__init__(self, **kwargs)

        self._lock   = threading.Lock()
        self._thread = None
        self._runEn  = False

        self.add(pr.LocalCommand(
            name='Start',
            function=self._start,
            description='Start process.'))

        self.add(pr.LocalCommand(
            name='Stop',
            function=self._stop,
            description='Stop process.'))

        self.add(pr.LocalVariable(
            name='Running',
            mode='RO',
            value=False,
            description='Operation is running.'))

        self.add(pr.LocalVariable(
            name='Progress',
            mode='RO',
            units='Pct',
            value=0.0,
            description='Percent complete.'))

    def _start(self):
        with self._lock:
            if self.Running.value() is False:
                self._runEn  = True
                self._thread = threading.Thread(target=self._run)
                self._thread.start()
            else:
                self._log.warning("Process already running!")

    def _stop(self):
        with self._lock:
            self._runEn  = False

    def _run(self):
        self.Running.set(True)

        try:
            self._process()
        except Exception as e:
            self._log.exception(e)

        self.Running.set(False)

    def _process(self):
        for i in range(101):
            if self._runEn is False:
                break
            time.sleep(1)
            self.Progress.set(i)


