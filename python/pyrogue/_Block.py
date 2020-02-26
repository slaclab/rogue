#-----------------------------------------------------------------------------
# Title      : PyRogue base module - Block Class
#-----------------------------------------------------------------------------
# File       : pyrogue/_Block.py
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
import pyrogue as pr


class MemoryError(Exception):
    """ Exception for memory access errors."""

    def __init__(self, *, name, address, msg=None, size=0):

        self._value = f'Memory Error for {name} at address {address:#08x}'

        if msg is not None:
            self._value += " " + msg

    def __str__(self):
        return repr(self._value)


class LocalBlock(object):
    def __init__(self, *, variable, localSet, localGet, value):
        self._path      = variable.path
        self._mode      = variable.mode
        self._device    = variable.parent
        self._localSet  = localSet
        self._localGet  = localGet
        self._variable  = variable
        self._variables = [variable] # Used by poller
        self._value     = value
        self._lock      = threading.RLock()
        self._doUpdate  = False
        self._enable    = True

        # Setup logging
        self._log = pr.logInit(cls=self,name=self._path)

    def __repr__(self):
        return repr(self._path)

    @property
    def path(self):
        return self._path

    @property
    def mode(self):
        return self._mode

    @property
    def bulkEn(self):
        return True

    def forceStale(self):
        pass

    def setEnable(self,value):
        with self._lock:
            self._enable = value

    def _setTimeout(self,value):
        pass

    @property
    def variables(self):
        return self._variables

    def set(self, var, value):
        with self._lock:

            if isinstance(value, list) or isinstance(value,dict):
                changed = True
            else:
                changed = self._value != value
            self._value = value

            # If a setFunction exists, call it (Used by local variables)
            if self._enable and self._localSet is not None:

                # Possible args
                pargs = {'dev' : self._device, 'var' : self._variable, 'value' : self._value, 'changed' : changed}

                pr.varFuncHelper(self._localSet, pargs, self._log, self._variable.path)

    def get(self, var):
        if self._enable and self._localGet is not None:
            with self._lock:

                # Possible args
                pargs = {'dev' : self._device, 'var' : self._variable}

                self._value = pr.varFuncHelper(self._localGet,pargs, self._log, self._variable.path)

        return self._value

    def startTransaction(self, type, forceWr, check, var):
        """
        Start a transaction.
        """
        if self._enable:
            with self._lock:
                self._doUpdate = self._variable._updateNotify

    def checkTransaction(self):
        """
        Check status of block.
        If update=True notify variables if read
        """
        if self._enable:
            with self._lock:
                doUpdate = self._doUpdate
                self._doUpdate = False

            # Update variables outside of lock
            if doUpdate:
                self._variable._queueUpdate()

    def _iadd(self, other):
        with self._lock:
            self.set(None, self.get(None) + other)
            if self._enable:
                self._variable._queueUpdate()

    def _isub(self, other):
        with self._lock:
            self.set(None, self.get(None) - other)
            if self._enable:
                self._variable._queueUpdate()

    def _imul(self, other):
        with self._lock:
            self.set(None, self.get(None) * other)
            if self._enable:
                self._variable._queueUpdate()

    def _imatmul(self, other):
        with self._lock:
            self.set(None, self.get(None) @ other)
            self._variable._queueUpdate()

    def _itruediv(self, other):
        with self._lock:
            self.set(None, self.get(None) / other)
            if self._enable:
                self._variable._queueUpdate()

    def _ifloordiv(self, other):
        with self._lock:
            self.set(None, self.get(None) // other)
            if self._enable:
                self._variable._queueUpdate()

    def _imod(self, other):
        with self._lock:
            self.set(None, self.get(None) % other)
            if self._enable:
                self._variable._queueUpdate()

    def _ipow(self, other):
        with self._lock:
            self.set(None, self.get(None) ** other)
            if self._enable:
                self._variable._queueUpdate()

    def _ilshift(self, other):
        with self._lock:
            self.set(None, self.get(None) << other)
            if self._enable:
                self._variable._queueUpdate()

    def _irshift(self, other):
        with self._lock:
            self.set(None, self.get(None) >> other)
            if self._enable:
                self._variable._queueUpdate()

    def _iand(self, other):
        with self._lock:
            self.set(None, self.get(None) & other)
            if self._enable:
                self._variable._queueUpdate()

    def _ixor(self, other):
        with self._lock:
            self.set(None, self.get(None) ^ other)
            if self._enable:
                self._variable._queueUpdate()

    def _ior(self, other):
        with self._lock:
            self.set(None, self.get(None) | other)
            if self._enable:
                self._variable._queueUpdate()
