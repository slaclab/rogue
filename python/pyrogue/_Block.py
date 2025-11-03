# -----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
# -----------------------------------------------------------------------------
#  Description:
#       PyRogue base module - Block Class
# -----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
# -----------------------------------------------------------------------------
import threading
from collections.abc import Callable
from typing import Any, Optional, Union

import numpy as np

import pyrogue as pr
import rogue.interfaces.memory as rim


def startTransaction(
    block: "pr.LocalBlock",
    *,
    type,
    forceWr: bool = False,
    checkEach: bool = False,
    variable: Any | None = None,
    index: int = -1,
    **kwargs,
):
    """
    Helper function for calling the startTransaction function in a block. This helper
        function ensures future changes to the API do not break custom code in a Device's
        writeBlocks, readBlocks and checkBlocks functions.

    Args:
        block :
        type :
        forceWr :
        checkEach :
        variable :
        index :
        **kwargs :

    """
    block._startTransaction(type, forceWr, checkEach, variable, index)


def checkTransaction(block, **kwargs):
    """Helper function for calling the checkTransaction function in a block. This helper
        function ensures future changes to the API do not break custom code in a Device's
        writeBlocks, readBlocks and checkBlocks functions.

    Args:
        block :

    **kwargs :


    Returns:

    """
    block._checkTransaction()


def writeBlocks(blocks, force=False, checkEach=False, index=-1, **kwargs):
    """Helper function for writing and verifying a list of blocks.
    Allows a custom list of blocks to be efficiently written,
    similar to Device.writeBlocks()."""
    for b in blocks:
        startTransaction(
            b, type=rim.Write, forceWr=force, checkEach=checkEach, index=index, **kwargs
        )


def verifyBlocks(blocks, checkEach=False, **kwargs):
    """Helper function for verifying a list of blocks.
    Allows a custom list of blocks to be efficiently verified without blocking
    between each read, similar to Device.verifyBlocks()."""
    for b in blocks:
        startTransaction(b, type=rim.Verify, checkEach=checkEach, **kwargs)


def readBlocks(blocks, checkEach=False, **kwargs):
    """Helper function for reading a list of blocks.
    Allows a custom list of blocks to be efficiently read without blocking
    between each read, similar to Device.readBlocks()."""
    for b in blocks:
        startTransaction(b, type=rim.Read, checkEach=checkEach, **kwargs)


def checkBlocks(blocks, **kwargs):
    """Helper function for waiting on block transactions for a list of blocks
    Allows a custom list of blocks to be efficiently operated on without blocking
    between each transaction, similar to  Device.checkBlocks()."""
    for b in blocks:
        checkTransaction(b)


def writeAndVerifyBlocks(blocks, force=False, checkEach=False, index=-1, **kwargs):
    """Helper function for writing and verifying a list of blocks.
    Allows a custom list of blocks to be efficiently written and verified
    similar to Device.writeAndVerifyBlocks()."""
    writeBlocks(blocks, force=force, checkEach=checkEach, index=index, **kwargs)
    verifyBlocks(blocks, checkEach=checkEach, **kwargs)
    checkBlocks(blocks)


def readAndCheckBlocks(blocks, checkEach=False, **kwargs):
    """Helper function for reading a list of blocks.
     Allows a custom list of blocks to be efficiently written and verified
    without blocking between each read, similar to Device.readAndCheckBlocks()."""
    readBlocks(blocks, checkEach, **kwargs)
    checkBlocks(blocks)


class MemoryError(Exception):
    """Exception for memory access errors."""

    def __init__(self, *, name, address, msg=None, size=0):
        self._value = f"Memory Error for {name} at address {address:#08x}"

        if msg is not None:
            self._value += " " + msg

    def __str__(self):
        return repr(self._value)


class LocalBlock(object):
    """LocalBlock Class definition.

    Args:
        variable:
        localSet:
        localGet:
        minimum:
        maximum:
        value:

    Attributes:
        _path (str): Variables path
        _mode (str): Variables mode
        _device (pr.Device): Variables parent device
        _lock (thread): threading.RLock()
        _enable (bool): If the block is enabled.
        _variables (list): List of variables, Used by poller
        _log (Logger): Logger
        _localSetWrap (Callable):  functionWrapper for localSet with callArgs=['dev', 'var', 'value', 'changed'])
        _localGetWrap (Callable): functionWrapper for localGet with callArgs=['dev', 'var']
    """

    def __init__(
        self,
        *,
        variable: "pr.LocalVariable",
        localSet: Optional[Callable],
        localGet: Optional[Callable],
        minimum: Optional[int],
        maximum: Optional[int],
        value: Any,
    ):
        self._path = variable.path
        self._mode = variable.mode
        self._device = variable.parent
        self._localSet = localSet
        self._localGet = localGet
        self._minimum = minimum
        self._maximum = maximum
        self._variable = variable
        self._variables = [variable]  # Used by poller
        self._value = value
        self._lock = threading.RLock()
        self._enable = True

        # Setup logging
        self._log = pr.logInit(cls=self, name=self._path)

        # Wrap local functions
        self._localSetWrap = pr.functionWrapper(
            function=self._localSet, callArgs=["dev", "var", "value", "changed"]
        )
        self._localGetWrap = pr.functionWrapper(
            function=self._localGet, callArgs=["dev", "var"]
        )

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

    def setEnable(self, value: bool):
        """

        Args:
            value :

        """
        with self._lock:
            self._enable = value

    def _setTimeout(self, value):
        """

        Args:
            value :

        """
        pass

    @property
    def variables(self):
        """ """
        return self._variables

    def set(self, var: Any, value: Union[int, list, dict], index: int = -1):
        """

        Args:
            var :
            value :
            index :

        """
        with self._lock:
            if index < 0 and (isinstance(value, list) or isinstance(value, dict)):
                changed = True
            elif index >= 0:
                changed = self._value[index] != value
            elif isinstance(value, np.ndarray):
                changed = np.array_equal(self._value, value)
            else:
                if (self._minimum is not None and value < self._minimum) or (
                    self._maximum is not None and value > self._maximum
                ):
                    raise pr.VariableError(
                        f"Value range error for {self._path}. Value={value}, Min={self._minimum}, Max={self._maximum}"
                    )

                changed = self._value != value

            if index >= 0:
                self._value[index] = value
            else:
                self._value = value

            # If a setFunction exists, call it (Used by local variables)
            if self._enable and self._localSet is not None:
                self._localSetWrap(
                    function=self._localSet,
                    dev=self._device,
                    var=self._variable,
                    value=self._value,
                    changed=changed,
                )

    def get(self, var: Any, index: int = -1):
        """

        Args:
            var :
            index :

        Returns:

        """
        if self._enable and self._localGet is not None:
            with self._lock:
                self._value = self._localGetWrap(
                    function=self._localGet, dev=self._device, var=self._variable
                )
        if index >= 0:
            return self._value[index]
        else:
            return self._value

    def _startTransaction(self, type, forceWr, checkEach, variable, index):
        """Start a transaction.

        Args:
            type :
            forceWr :
            checkEach :
            variable :
            index :

        """
        pass

    def _checkTransaction(self):
        """Check status of block. If update=True notify variables if read."""
        if self._enable and self._variable._updateNotify:
            self._variable._queueUpdate()

    def _iadd(self, other):
        """

        Args:
            other :

        """
        with self._lock:
            self.set(None, self.get(None) + other)
            if self._enable:
                self._variable._queueUpdate()

    def _isub(self, other):
        """

        Args:
            other :

        """
        with self._lock:
            self.set(None, self.get(None) - other)
            if self._enable:
                self._variable._queueUpdate()

    def _imul(self, other):
        """

        Args:
            other :

        """
        with self._lock:
            self.set(None, self.get(None) * other)
            if self._enable:
                self._variable._queueUpdate()

    def _imatmul(self, other):
        """

        Args:
            other :

        """
        with self._lock:
            self.set(None, self.get(None) @ other)
            self._variable._queueUpdate()

    def _itruediv(self, other):
        """

        Args:
            other :

        """
        with self._lock:
            self.set(None, self.get(None) / other)
            if self._enable:
                self._variable._queueUpdate()

    def _ifloordiv(self, other):
        """

        Args:
            other :

        """
        with self._lock:
            self.set(None, self.get(None) // other)
            if self._enable:
                self._variable._queueUpdate()

    def _imod(self, other):
        """

        Args:
            other :

        """
        with self._lock:
            self.set(None, self.get(None) % other)
            if self._enable:
                self._variable._queueUpdate()

    def _ipow(self, other):
        """

        Args:
            other :

        """
        with self._lock:
            self.set(None, self.get(None) ** other)
            if self._enable:
                self._variable._queueUpdate()

    def _ilshift(self, other):
        """

        Args:
            other :

        """
        with self._lock:
            self.set(None, self.get(None) << other)
            if self._enable:
                self._variable._queueUpdate()

    def _irshift(self, other):
        """

        Args:
            other :

        """
        with self._lock:
            self.set(None, self.get(None) >> other)
            if self._enable:
                self._variable._queueUpdate()

    def _iand(self, other):
        """

        Args:
            other :

        """
        with self._lock:
            self.set(None, self.get(None) & other)
            if self._enable:
                self._variable._queueUpdate()

    def _ixor(self, other):
        """

        Args:
            other :

        """
        with self._lock:
            self.set(None, self.get(None) ^ other)
            if self._enable:
                self._variable._queueUpdate()

    def _ior(self, other):
        """

        Args:
            other :

        """
        with self._lock:
            self.set(None, self.get(None) | other)
            if self._enable:
                self._variable._queueUpdate()
