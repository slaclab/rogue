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


def startTransaction(block, *, type, forceWr=False, checkEach=False, variable=None, index=-1, **kwargs):
    """
    Helper function for calling the startTransaction function in a block. This helper
        function ensures future changes to the API do not break custom code in a Device's
        writeBlocks, readBlocks and checkBlocks functions.

    Parameters2
    ----------
    block :
        
    * :
        
    type :
        
    forceWr :
         (Default value = False)
    checkEach :
         (Default value = False)
    variable :
         (Default value = None)
    index :
         (Default value = -1)
    **kwargs :
        

    Returns
    -------

    """
    block._startTransaction(type, forceWr, checkEach, variable, index)


def checkTransaction(block, **kwargs):
    """
    Helper function for calling the checkTransaction function in a block. This helper
        function ensures future changes to the API do not break custom code in a Device's
        writeBlocks, readBlocks and checkBlocks functions.

    Parameters
    ----------
    block :
        
    **kwargs :
        

    Returns
    -------

    """
    block._checkTransaction()


class MemoryError(Exception):
    """ 
    Exception for memory access errors.
    """

    def __init__(self, *, name, address, msg=None, size=0):

        self._value = f'Memory Error for {name} at address {address:#08x}'

        if msg is not None:
            self._value += " " + msg

    def __str__(self):
        return repr(self._value)


class LocalBlock(object):
    """ """
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

        # Wrap local functions
        self._localSetWrap = pr.functionWrapper(function=self._localSet, callArgs=['dev', 'var', 'value', 'changed'])
        self._localGetWrap = pr.functionWrapper(function=self._localGet, callArgs=['dev', 'var'])

    def __repr__(self):
        return repr(self._path)

    @property
    def path(self):
        """ """
        return self._path

    @property
    def mode(self):
        """ """
        return self._mode

    @property
    def bulkOpEn(self):
        """ """
        return True

    def forceStale(self):
        """ """
        pass

    def setEnable(self,value):
        """
        

        Parameters
        ----------
        value :
            

        Returns
        -------

        """
        with self._lock:
            self._enable = value

    def _setTimeout(self,value):
        """
        

        Parameters
        ----------
        value :
            

        Returns
        -------

        """
        pass

    @property
    def variables(self):
        """ """
        return self._variables

    def set(self, var, value, index=-1):
        """
        

        Parameters
        ----------
        var :
            
        value :
            
        index : int
             (Default value = -1)

        Returns
        -------

        """
        with self._lock:

            if index < 0 and (isinstance(value, list) or isinstance(value,dict)):
                changed = True
            elif index >= 0:
                changed = self._value[index] != value
            else:
                changed = self._value != value

            if index >= 0:
                self._value[index] = value
            else:
                self._value = value

            # If a setFunction exists, call it (Used by local variables)
            if self._enable and self._localSet is not None:
                self._localSetWrap(function=self._localSet, dev=self._device, var=self._variable, value=self._value, changed=changed)

    def get(self, var, index=-1):
        """
        

        Parameters
        ----------
        var :
            
        index : int
             (Default value = -1)

        Returns
        -------

        """
        if self._enable and self._localGet is not None:
            with self._lock:
                self._value = self._localGetWrap(function=self._localGet, dev=self._device, var=self._variable)
        if index >= 0:
            return self._value[index]
        else:
            return self._value

    def _startTransaction(self, type, forceWr, checkEach, variable, index):
        """
        Start a transaction.

        Parameters
        ----------
        type :
            
        forceWr :
            
        checkEach :
            
        variable :
            
        index :
            

        Returns
        -------

        """
        if self._enable:
            with self._lock:
                self._doUpdate = self._variable._updateNotify

    def _checkTransaction(self):
        """
        Check status of block.
        If update=True notify variables if read

        Parameters
        ----------

        Returns
        -------

        """
        if self._enable:
            with self._lock:
                doUpdate = self._doUpdate
                self._doUpdate = False

            # Update variables outside of lock
            if doUpdate:
                self._variable._queueUpdate()

    def _iadd(self, other):
        """
        

        Parameters
        ----------
        other :
            

        Returns
        -------

        """
        with self._lock:
            self.set(None, self.get(None) + other)
            if self._enable:
                self._variable._queueUpdate()

    def _isub(self, other):
        """
        

        Parameters
        ----------
        other :
            

        Returns
        -------

        """
        with self._lock:
            self.set(None, self.get(None) - other)
            if self._enable:
                self._variable._queueUpdate()

    def _imul(self, other):
        """
        

        Parameters
        ----------
        other :
            

        Returns
        -------

        """
        with self._lock:
            self.set(None, self.get(None) * other)
            if self._enable:
                self._variable._queueUpdate()

    def _imatmul(self, other):
        """
        

        Parameters
        ----------
        other :
            

        Returns
        -------

        """
        with self._lock:
            self.set(None, self.get(None) @ other)
            self._variable._queueUpdate()

    def _itruediv(self, other):
        """
        

        Parameters
        ----------
        other :
            

        Returns
        -------

        """
        with self._lock:
            self.set(None, self.get(None) / other)
            if self._enable:
                self._variable._queueUpdate()

    def _ifloordiv(self, other):
        """
        

        Parameters
        ----------
        other :
            

        Returns
        -------

        """
        with self._lock:
            self.set(None, self.get(None) // other)
            if self._enable:
                self._variable._queueUpdate()

    def _imod(self, other):
        """
        

        Parameters
        ----------
        other :
            

        Returns
        -------

        """
        with self._lock:
            self.set(None, self.get(None) % other)
            if self._enable:
                self._variable._queueUpdate()

    def _ipow(self, other):
        """
        

        Parameters
        ----------
        other :
            

        Returns
        -------

        """
        with self._lock:
            self.set(None, self.get(None) ** other)
            if self._enable:
                self._variable._queueUpdate()

    def _ilshift(self, other):
        """
        

        Parameters
        ----------
        other :
            

        Returns
        -------

        """
        with self._lock:
            self.set(None, self.get(None) << other)
            if self._enable:
                self._variable._queueUpdate()

    def _irshift(self, other):
        """
        

        Parameters
        ----------
        other :
            

        Returns
        -------

        """
        with self._lock:
            self.set(None, self.get(None) >> other)
            if self._enable:
                self._variable._queueUpdate()

    def _iand(self, other):
        """
        

        Parameters
        ----------
        other :
            

        Returns
        -------

        """
        with self._lock:
            self.set(None, self.get(None) & other)
            if self._enable:
                self._variable._queueUpdate()

    def _ixor(self, other):
        """
        

        Parameters
        ----------
        other :
            

        Returns
        -------

        """
        with self._lock:
            self.set(None, self.get(None) ^ other)
            if self._enable:
                self._variable._queueUpdate()

    def _ior(self, other):
        """
        

        Parameters
        ----------
        other :
            

        Returns
        -------

        """
        with self._lock:
            self.set(None, self.get(None) | other)
            if self._enable:
                self._variable._queueUpdate()
