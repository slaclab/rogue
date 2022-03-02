#-----------------------------------------------------------------------------
# Title      : PyRogue base module - Process Device Class
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
import threading
import time
import pyrogue as pr

class Process(pr.Device):
    """Special base class to execute processes."""

    def __init__(self, *, argVariable=None, returnVariable=None, function=None, **kwargs):

        pr.Device.__init__(self, **kwargs)

        self._lock   = threading.Lock()
        self._thread = None
        self._runEn  = False
        self._argVar = argVariable
        self._retVar = returnVariable
        self._function = function

        self._functionWrap = pr.functionWrapper(function=self._function, callArgs=['root', 'dev', 'arg'])

        self.add(pr.LocalCommand(
            name='Start',
            function=self._startProcess,
            description='Start process. No Args.'))

        self.add(pr.LocalCommand(
            name='Stop',
            function=self._stopProcess,
            description='Stop process. No Args.'))

        self.add(pr.LocalVariable(
            name='Running',
            mode='RO',
            value=False,
            pollInterval=1.0,
            description='Status values indicating if operation is running.'))

        self.add(pr.LocalVariable(
            name='Progress',
            mode='RO',
            units='Pct',
            value=0.0,
            disp = '{:1.2f}',
            minimum=0.0,
            maximum=1.0,
            pollInterval=1.0,
            description='Percent complete: 0 - 100 %.'))

        self.add(pr.LocalVariable(
            name='Message',
            mode='RO',
            value='',
            pollInterval=1.0,
            description="Process status message. Prefixed with 'Error:' if an error occurred."))

        # Add arg variable if not already added
        if self._argVar is not None and self._argVar not in self:
            self.add(self._argVar)

        # Add return variable if not already added
        if self._retVar is not None and self._retVar not in self:
            self.add(self._retVar)


    def _startProcess(self):
        """ """
        with self._lock:
            if self.Running.value() is False:
                self._runEn  = True
                self._thread = threading.Thread(target=self._run)
                self._thread.start()
            else:
                self._log.warning("Process already running!")

    def _stopProcess(self):
        """ """
        with self._lock:
            self._runEn  = False

    def _stop(self):
        """ """
        self._stopProcess()
        pr.Device._stop(self)

    def __call__(self,arg=None):
        with self._lock:
            if self.Running.value() is False:
                if arg is not None and self._argVar is not None:
                    self.nodes[self._argVar].setDisp(arg)

                self._runEn  = True
                self._thread = threading.Thread(target=self._run)
                self._thread.start()
            else:
                self._log.warning("Process already running!")

        return None

    def _run(self):
        """ """
        self.Running.set(True)

        try:
            self._process()
        except Exception as e:
            pr.logException(self._log,e)
            self.Message.setDisp("Stopped after error!")

        self.Running.set(False)

    def _process(self):
        """ """

        # User has provided a function Update status at start and end and call their function
        if self._function is not None:
            self.Message.setDisp("Running")
            self.Progress.set(0.0)

            if self._argVar is not None:
                arg = self._argVar.get()
            else:
                arg = None

            ret = self._functionWrap(function=self._function, root=self.root, dev=self, arg=arg)

            if self._retVar is not None:
                self._retVar.set(ret)

            self.Message.setDisp("Done")
            self.Progress.set(1.0)

        # No function run example process
        else:
            self.Message.setDisp("Started")
            for i in range(101):
                if self._runEn is False:
                    break
                time.sleep(1)
                self.Progress.set(i/100)
                self.Message.setDisp(f"Running for {i} seconds.")
            self.Message.setDisp("Done")
