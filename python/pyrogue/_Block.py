#-----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
#-----------------------------------------------------------------------------
#  Description:
#       PyRogue base module - Block Class
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
from __future__ import annotations

import threading
from typing import Any, Callable, Iterable, Optional

import numpy as np
import pyrogue as pr
import rogue.interfaces.memory as rim



def startTransaction(
    block: rim.Block,
    *,
    type: int,
    forceWr: bool = False,
    check: bool = False,
    variable: pr.BaseVariable = None,
    index: int = -1,
    **kwargs: Any,
) -> None:
    """Helper function for starting a transaction on a block.

    This helper function ensures future changes to the API do not break custom
    code in a Device's writeBlocks, readBlocks and checkBlocks functions.

    Parameters
    ----------
    block : rim.Block
        Block instance to start a transaction on.
    type : {rim.Read, rim.Write, rim.Post, rim.Verify}
        Transaction type
    forceWr : bool, optional (default = False)
        Force the write even if block values are unchanged.
    check : bool, optional (default = False)
        Wait for transaction to complete before returning
    variable : pr.BaseVariable, optional
        Variable associated with the transaction, None for pure Block transactions.
    index : int, optional (default = -1)
        Optional index for array variables.
    **kwargs : Any, optional
        Unused, provided for future compatibility.
    """
    block._startTransaction(type, forceWr, check, variable, index)


def checkTransaction(block: rim.Block, **kwargs: Any) -> None:
    """Wait for completion of transaction on a block.

    Helper function for calling the checkTransaction function in a block. This helper
    function ensures future changes to the API do not break custom code in a Device's
    writeBlocks, readBlocks and checkBlocks functions.

    Parameters
    ----------
    block : rim.Block
        Block instance to operate on.
    **kwargs : Any, optional
       Unused, provided for future compatibility.
    """
    block._checkTransaction()

def writeBlocks(
    blocks: Iterable[rim.Block],
    force: bool = False,
    checkEach: bool = False,
    index: int = -1,
    **kwargs: Any,
) -> None:
    """Write a list of blocks efficiently.

    Helper function for writing and verifying a list of blocks. Allows a custom list
    of blocks to be efficiently written, similar to ``Device.writeBlocks()``.

    Parameters
    ----------
    blocks : iterable[rim.Block]
        Blocks to write.
    force : bool, optional (default = False)
        Force the write even if values are unchanged.
    checkEach : bool, optional (default = False)
        Wait for completion of each block transaction before initiating the next one
    index : int, optional (default = -1)
        Optional index for array variables.
    **kwargs : Any
        Additional arguments passed through to startTransaction().
    """
    for b in blocks:
        startTransaction(b, type=rim.Write, forceWr=force, check=checkEach, index=index, **kwargs)

def verifyBlocks(blocks: Iterable[rim.Block], checkEach: bool = False, **kwargs: Any) -> None:
    """Verify a list of blocks efficiently.

    Helper function for verifying a list of blocks. Allows a custom list of blocks
    to be efficiently verified without blocking between each read, similar to
    ``Device.verifyBlocks()``.

    Parameters
    ----------
    blocks : iterable[rim.Block]
        Blocks to verify.
    checkEach : bool, optional (default = False)
        Wait for completion of each block transation before initiating the next one
    **kwargs : Any
        Additional arguments passed through to startTransaction().
    """
    for b in blocks:
        startTransaction(b, type=rim.Verify, check=checkEach, **kwargs)

def readBlocks(blocks: Iterable[rim.Block], checkEach: bool = False, **kwargs: Any) -> None:
    """Read a list of blocks efficiently.

    Helper function for reading a list of blocks. Allows a custom list of blocks
    to be efficiently read without blocking between each read, similar to
    ``Device.readBlocks()``.

    Parameters
    ----------
    blocks : iterable[rim.Block]
        Blocks to read.
    checkEach : bool, optional (default = False)
        Wait for completion of each block transation before initiating the next one
    **kwargs : Any
        Additional arguments passed through to startTransaction()
    """
    for b in blocks:
        startTransaction(b, type=rim.Read, check=checkEach, **kwargs)

def checkBlocks(blocks: Iterable[rim.Block], **kwargs: Any) -> None:
    """Wait on block transactions for a list of blocks.

    Helper function for waiting on block transactions to complete.
    Allows a custom list of blocks to be efficiently operated on
    without blocking between each transaction, similar to ``Device.checkBlocks()``.

    Parameters
    ----------
    blocks : iterable[rim.Block]
        Blocks to check.
    **kwargs : Any
        Unused
    """
    for b in blocks:
        checkTransaction(b)

def writeAndVerifyBlocks(
    blocks: Iterable[rim.Block],
    force: bool = False,
    checkEach: bool = False,
    index: int = -1,
    **kwargs: Any,
) -> None:
    """Write and verify a list of blocks efficiently.

    Helper function for writing and verifying a list of blocks. Allows a custom
    list of blocks to be efficiently written and verified similar to
    ``Device.writeAndVerifyBlocks()``.

    Parameters
    ----------
    blocks : iterable[rim.Block]
        Blocks to write and verify.
    force : bool, optional (default = False)
        Force the write even if values are unchanged.
    checkEach : bool, optional (default = False)
        Wait for each block transaction to complete before starting the next one
    index : int, optional (default = -1)
        Optional index for array variables.
    **kwargs : Any
        Additional arguments passed through to the block transaction.
    """
    writeBlocks(blocks, force=force, checkEach=checkEach, index=index, **kwargs)
    verifyBlocks(blocks, checkEach=checkEach, **kwargs)
    checkBlocks(blocks)

def readAndCheckBlocks(blocks: Iterable[rim.Block], checkEach: bool = False, **kwargs: Any) -> None:
    """Read blocks and wait for completion.

    Helper function for reading a list of blocks. Allows a custom list of blocks
    to be efficiently read without blocking between each read, similar to
    ``Device.readAndCheckBlocks()``.

    Parameters
    ----------
    blocks : iterable[rim.Block]
        Blocks to read.
    checkEach : bool, optional (default = False)
        Wait for each block transaction to complete before starting the next one
    **kwargs : Any
        Additional arguments passed through to the block transaction.
    """
    readBlocks(blocks, checkEach, **kwargs)
    checkBlocks(blocks)




class MemoryError(Exception):
    """Raised when a memory access fails.

    Parameters
    ----------
    name : str
        Name of the device or memory target.
    address : int
        Address where the error occurred.
    msg : str, optional
        Additional error message.
    size : int, optional (default = 0)
        Size of the attempted access.
    """

    def __init__(self, *, name: str, address: int, msg: Optional[str] = None, size: int = 0) -> None:

        self._value = f'Memory Error for {name} at address {address:#08x}'

        if msg is not None:
            self._value += " " + msg

    def __str__(self) -> str:
        return repr(self._value)


class LocalBlock(object):
    """Back-end Block class used by LocalVariable.

    Stores value in local memory.

    Parameters
    ----------
    variable : pr.LocalVariable
        Variable associated with this block.
    localSet : callable
        Setter callback. Expected signature:
        ``localSet(value, dev=None, var=None, changed=None)``.
    localGet : callable
        Getter callback. Expected signature:
        ``localGet(dev=None, var=None)``.
    minimum : object
        Minimum allowed value (may be ``None``).
    maximum : object
        Maximum allowed value (may be ``None``).
    value : object
        Initial value stored in the block.
    """
    def __init__(
        self,
        *,
        variable: pr.LocalVariable,
        localSet: Optional[Callable[..., Any]],
        localGet: Optional[Callable[..., Any]],
        minimum: Optional[Any],
        maximum: Optional[Any],
        value: Any,
    ) -> None:
        self._path      = variable.path
        self._mode      = variable.mode
        self._device    = variable.parent
        self._localSet  = localSet
        self._localGet  = localGet
        self._minimum   = minimum
        self._maximum   = maximum
        self._variable  = variable
        self._variables = [variable] # Used by poller
        self._value     = value
        self._lock      = threading.RLock()
        self._enable    = True

        # Setup logging
        self._log = pr.logInit(cls=self,name=self._path)

        # Wrap local functions
        self._localSetWrap = pr.functionWrapper(function=self._localSet, callArgs=['dev', 'var', 'value', 'changed'])
        self._localGetWrap = pr.functionWrapper(function=self._localGet, callArgs=['dev', 'var'])

    def __repr__(self) -> str:
        return repr(self._path)

    @property
    def path(self) -> str:
        """Return the block path."""
        return self._path

    @property
    def mode(self) -> str:
        """Return the variable access mode. ('RW', 'RO', etc)."""
        return self._mode

    @property
    def bulkOpEn(self) -> bool:
        """Return True to enable bulk operations."""
        return True

    def forceStale(self) -> None:
        """Mark the block as stale (no-op for local blocks)."""
        pass

    def setEnable(self, value: bool) -> None:
        """Enable or disable local access.

        Parameters
        ----------
        value : bool
            True to enable local access, False to disable.
        """
        with self._lock:
            self._enable = value

    def _setTimeout(self, value: Any) -> None:
        """Set the timeout (not used for local blocks).

        Parameters
        ----------
        value : object
            Timeout value, currently ignored for local blocks.
        """
        pass

    @property
    def variables(self) -> list:
        """Return the list of variables in this block."""
        return self._variables

    def set(self, var: pr.LocalVariable, value: Any, index: int = -1) -> None:
        """Set the block value, optionally for an index.

        Parameters
        ----------
        var : pr.LocalVariable
            Variable associated with this block.
        value : object
            Value to write.
        index : int, optional (default = -1)
            Index for array variables.
        """
        with self._lock:

            if index < 0 and (isinstance(value, list) or isinstance(value, dict)):
                changed = True
            elif index >= 0:
                changed = self._value[index] != value
            elif isinstance(value, np.ndarray):
                changed = np.array_equal(self._value, value)
            else:

                if (self._minimum is not None and value < self._minimum) or \
                   (self._maximum is not None and value > self._maximum):

                    raise pr.VariableError(f'Value range error for {self._path}. Value={value}, Min={self._minimum}, Max={self._maximum}')

                changed = self._value != value

            # Ignore type check if value is accessed with an index
            if index >= 0:
                self._value[index] = value
            else:
                if not isinstance(value, var._nativeType):
                    self._log.warning( f'{var.path}: Expecting {var._nativeType}: Currently a warning but in the future this will be an error' )
                    #raise TypeError(f"Error - {var.path}: Expecting {var._nativeType} but got {type(value)}")

                self._value = value

            # If a setFunction exists, call it (Used by local variables)
            if self._enable and self._localSet is not None:
                self._localSetWrap(function=self._localSet, dev=self._device, var=self._variable, value=self._value, changed=changed)

    def get(self, var: pr.LocalVariable, index: int = -1) -> Any:
        """Get the block value, optionally for an index.

        Parameters
        ----------
        var : pr.LocalVariable
            Variable associated with this block.
        index : int, optional (default = -1)
            Index for array variables.

        Returns
        -------
        object
            Current value.
        """
        if self._enable and self._localGet is not None:
            with self._lock:
                self._value = self._localGetWrap(function=self._localGet, dev=self._device, var=self._variable)
        if index >= 0:
            return self._value[index]
        else:
            return self._value

    def _startTransaction(self, type: Any, forceWr: bool, check: bool, variable: pr.LocalVariable, index: int) -> None:
        """Start a transaction (local blocks perform no hardware IO)."""
        pass

    def _checkTransaction(self) -> None:
        """Notify listeners of transaction completion"""
        if self._enable and self._variable._updateNotify:
            self._variable._queueUpdate()

    def _iadd(self, other: Any) -> None:
        """In-place add helper for local blocks."""
        with self._lock:
            self.set(None, self.get(None) + other)
            if self._enable:
                self._variable._queueUpdate()

    def _isub(self, other: Any) -> None:
        """In-place subtract helper for local blocks."""
        with self._lock:
            self.set(None, self.get(None) - other)
            if self._enable:
                self._variable._queueUpdate()

    def _imul(self, other: Any) -> None:
        """In-place multiply helper for local blocks."""
        with self._lock:
            self.set(None, self.get(None) * other)
            if self._enable:
                self._variable._queueUpdate()

    def _imatmul(self, other: Any) -> None:
        """In-place matrix multiply helper for local blocks."""
        with self._lock:
            self.set(None, self.get(None) @ other)
            self._variable._queueUpdate()

    def _itruediv(self, other: Any) -> None:
        """In-place true division helper for local blocks."""
        with self._lock:
            self.set(None, self.get(None) / other)
            if self._enable:
                self._variable._queueUpdate()

    def _ifloordiv(self, other: Any) -> None:
        """In-place floor division helper for local blocks."""
        with self._lock:
            self.set(None, self.get(None) // other)
            if self._enable:
                self._variable._queueUpdate()

    def _imod(self, other: Any) -> None:
        """In-place modulo helper for local blocks."""
        with self._lock:
            self.set(None, self.get(None) % other)
            if self._enable:
                self._variable._queueUpdate()

    def _ipow(self, other: Any) -> None:
        """In-place power helper for local blocks."""
        with self._lock:
            self.set(None, self.get(None) ** other)
            if self._enable:
                self._variable._queueUpdate()

    def _ilshift(self, other: Any) -> None:
        """In-place left shift helper for local blocks."""
        with self._lock:
            self.set(None, self.get(None) << other)
            if self._enable:
                self._variable._queueUpdate()

    def _irshift(self, other: Any) -> None:
        """In-place right shift helper for local blocks."""
        with self._lock:
            self.set(None, self.get(None) >> other)
            if self._enable:
                self._variable._queueUpdate()

    def _iand(self, other: Any) -> None:
        """In-place bitwise-and helper for local blocks."""
        with self._lock:
            self.set(None, self.get(None) & other)
            if self._enable:
                self._variable._queueUpdate()

    def _ixor(self, other: Any) -> None:
        """In-place bitwise-xor helper for local blocks."""

        with self._lock:
            self.set(None, self.get(None) ^ other)
            if self._enable:
                self._variable._queueUpdate()

    def _ior(self, other):
        """In-place bitwise-or helper for local blocks."""
        with self._lock:
            self.set(None, self.get(None) | other)
            if self._enable:
                self._variable._queueUpdate()
