#-----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
#-----------------------------------------------------------------------------
#  Description:
#       PyRogue base module - Command Class
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

import inspect
import operator
import threading
from typing import Any, Callable, Iterable

import pyrogue as pr
import rogue.interfaces.memory


class CommandError(Exception):
    """Raised when command execution or verification fails."""
    pass


class BaseCommand(pr.BaseVariable):
    """Base class for PyRogue commands.

    Parameters
    ----------
    name : str, optional
        Command name.
    description : str, optional (default = "")
        Human-readable description.
    value : object, optional (default = 0)
        Default command value.
    retValue : object, optional
        Example return value used to infer display type.
    enum : dict, optional
        Mapping from object values to display strings.
    hidden : bool, optional (default = False)
        If True, add the command to the ``Hidden`` group.
    groups : list[str], optional
        Groups to assign.
    minimum : object, optional
        Minimum allowed value.
    maximum : object, optional
        Maximum allowed value.
    function : callable, optional
        Callback executed when the command is invoked. The wrapper provides
        keyword arguments ``root``, ``dev``, ``cmd``, and ``arg``; the
        callback may accept any subset of these names.
        Default to no-op for command if None.
    background : bool, optional (default = False)
        Reserved for future use; not implemented.
    guiGroup : str, optional
        GUI grouping label.
    **kwargs : Any
        Additional arguments forwarded to ``BaseVariable``.
    """

    def __init__(
        self,
        *,
        name: str | None = None,
        description: str = "",
        value: Any = 0,
        retValue: Any | None = None,
        enum: dict[object, str] | None = None,
        hidden: bool = False,
        groups: list[str] | None = None,
        minimum: Any | None = None,
        maximum: Any | None = None,
        function: Callable[..., Any] | None = None,
        background: bool = False,
        guiGroup: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize a command variable."""
        pr.BaseVariable.__init__(
            self,
            name=name,
            description=description,
            mode='WO',
            value=value,
            enum=enum,
            hidden=hidden,
            groups=groups,
            minimum=minimum,
            maximum=maximum,
            bulkOpEn=False,
            guiGroup=guiGroup,
            **kwargs)

        self._function = function
        self._functionWrap = pr.functionWrapper(function=self._function, callArgs=['root', 'dev', 'cmd', 'arg'])

        self._thread = None
        self._lock   = threading.Lock()
        self._runEn  = False
        self._retDisp = "{}"

        self._workerResult = None
        self._workerError  = ''

        if retValue is None:
            self._retTypeStr = None
        elif isinstance(retValue, list):
            self._retTypeStr = f'List[{retValue[0].__class__.__name__}]'
        else:
            self._retTypeStr = retValue.__class__.__name__

        # args flag
        try:
            self._arg = 'arg' in inspect.getfullargspec(self._function).args

        # C++ functions
        except Exception:
            self._arg = False

    @pr.expose
    @property
    def arg(self) -> bool:
        """Return True if the command accepts an argument."""
        return self._arg

    @pr.expose
    @property
    def retTypeStr(self) -> str | None:
        """Return the display string for the return type."""
        return self._retTypeStr

    @pr.expose
    @property
    def running(self) -> bool:
        """Return True if a non-blocking worker thread is in flight."""
        with self._lock:
            thr = self._thread
        return thr is not None and thr.is_alive()

    @pr.expose
    @property
    def result(self) -> Any:
        """Return the last successful return value from a non-blocking call."""
        with self._lock:
            return self._workerResult

    @pr.expose
    @property
    def error(self) -> str:
        """Return the last error string from a non-blocking call, or ''."""
        with self._lock:
            return self._workerError

    def _resolveArg(self, arg: Any) -> Any:
        """Parse raw call argument into the canonical command value.

        Parameters
        ----------
        arg : object
            Raw argument as received by ``__call__``; ``None`` selects the
            default value.
        """
        if arg is None:
            return self._default
        return self.parseDisp(arg)

    def __call__(self, arg: Any = None, *, blocking: bool = True) -> Any:
        """Invoke the command.

        Parameters
        ----------
        arg : object, optional
            Command argument. If ``None``, uses the default value.
        blocking : bool, optional (default = True)
            When ``True`` (the default), execute the command synchronously and
            return the result.  When ``False``, dispatch the command on a
            worker thread and return ``None`` immediately.  Use the
            :attr:`running`, :attr:`result`, and :attr:`error` properties to
            monitor progress and retrieve the outcome.

            .. versionadded:: 6.14.0
        """
        if blocking:
            return self._doFunc(arg)

        # Non-blocking path: dispatch worker thread and return immediately.
        if self.parent.enable.value() is not True:
            return None

        resolvedArg = self._resolveArg(arg)

        with self._lock:
            if self._thread is None or not self._thread.is_alive():
                if self._arg and not isinstance(self, RemoteCommand):
                    self._default = resolvedArg
                    self._queueUpdate()

                self._runEn  = True
                self._thread = threading.Thread(
                    target=self._runWorker,
                    args=(resolvedArg,),
                    daemon=False,
                    name=f'{self.path}.worker',
                )
                self._thread.start()
            else:
                self._log.warning("Command already running!")

        return None

    def _doFunc(self, arg: Any) -> Any:
        """Execute command callback.

        Execute command: TODO: Update comments.

        Parameters
        ----------
        arg : object
            Command argument.
        """
        if (self.parent.enable.value() is not True):
            return

        try:

            # Convert arg
            if arg is None:
                arg = self._default
            else:
                arg = self.parseDisp(arg)

            ret = self._functionWrap(function=self._function, root=self.root, dev=self.parent, cmd=self, arg=arg)

            # Set arg to local variable if not a remote variable
            if self._arg and not isinstance(self,RemoteCommand):
                self._default = arg
                self._queueUpdate()

            with self._lock:
                self._workerResult = ret
                self._workerError  = ''

            return ret

        except Exception as e:
            pr.logException(self._log,e)
            with self._lock:
                self._workerError = str(e)
            raise e

    @pr.expose
    def call(self, arg: Any = None, *, blocking: bool = True) -> Any:
        """Invoke the command and return the raw result.

        Parameters
        ----------
        arg : object, optional
            Command argument.
        blocking : bool, optional (default = True)
            When ``False``, dispatch on a worker thread and return ``None``.
        """
        return self.__call__(arg, blocking=blocking)

    @pr.expose
    def callDisp(self, arg: Any = None, *, blocking: bool = True) -> str:
        """Invoke the command and return the display-formatted result.

        Parameters
        ----------
        arg : object, optional
            Command argument.
        blocking : bool, optional (default = True)
            When ``False``, dispatch on a worker thread and return ``""``.
        """
        if not blocking:
            self.__call__(arg, blocking=False)
            return ""
        return self.genDisp(self.__call__(arg), useDisp=self._retDisp)

    def _runWorker(self, arg: Any) -> None:
        """Execute the command function on a worker thread.

        Mirrors ``pr.Process._run``.  Exceptions are logged server-side;
        only ``str(exc)`` is surfaced to clients via the :attr:`error`
        property.
        """
        with self._lock:
            self._workerError = ''

        try:
            with self.root.updateGroup(period=1.0):
                ret = self._functionWrap(
                    function=self._function,
                    root=self.root,
                    dev=self.parent,
                    cmd=self,
                    arg=arg,
                )
        except Exception as e:
            pr.logException(self._log, e)
            with self._lock:
                self._workerError = str(e)
        else:
            with self._lock:
                self._workerResult = ret

        with self._lock:
            self._runEn  = False

    def _stopWorker(self) -> None:
        """Signal the worker to stop and wait for it to exit.

        Mirrors ``pr.Process._stopProcess`` including the self-thread guard
        that prevents deadlock when the user function triggers ``Root.stop()``.
        """
        with self._lock:
            self._runEn = False
            thr = self._thread

        # Self-thread guard: prevents deadlock if the user function calls
        # Root.stop() from within the worker (mirrors _Process._stopProcess).
        if (thr is not None
                and hasattr(thr, 'is_alive') and thr.is_alive()
                and hasattr(thr, 'join')
                and threading.current_thread() is not thr):
            thr.join()

    def _stop(self) -> None:
        """Join any in-flight worker thread.

        Called by ``Device._stop`` during ``Root.stop()``.
        """
        self._stopWorker()

    @staticmethod
    def nothing() -> None:
        """No-op command handler."""
        pass

    @staticmethod
    def read(cmd: BaseCommand) -> None:
        """Read the command variable.

        Parameters
        ----------
        cmd : BaseCommand
            Command to read.
        """
        cmd.get(read=True)

    @staticmethod
    def setArg(cmd: BaseCommand, arg: Any) -> None:
        """Set the command argument.

        Parameters
        ----------
        cmd : BaseCommand
            Command to write.
        arg : object
            Value to write.
        """
        cmd.set(arg)

    @staticmethod
    def setAndVerifyArg(cmd: BaseCommand, arg: Any) -> None:
        """Set the argument and verify by reading it back.

        Parameters
        ----------
        cmd : BaseCommand
            Command to write.
        arg : object
            Value to write and verify.
        """
        cmd.set(arg)
        ret = cmd.get()
        if ret != arg:
            raise CommandError(f'Verification failed for {cmd.path}. \nSet to {arg} but read back {ret}')

    @staticmethod
    def createToggle(sets: Iterable[Any]) -> Callable[[BaseCommand], None]:
        """Create a toggle function that iterates over provided values.

        Parameters
        ----------
        sets : iterable
            Values to write sequentially.
        """
        def toggle(cmd: BaseCommand) -> None:
            """Write each configured toggle value to ``cmd``."""
            for s in sets:
                cmd.set(s)
        return toggle

    @staticmethod
    def toggle(cmd: BaseCommand) -> None:
        """Toggle a command by writing 1 then 0.

        Parameters
        ----------
        cmd : BaseCommand
            Command to toggle.
        """
        cmd.set(1)
        cmd.set(0)

    @staticmethod
    def createTouch(value: Any) -> Callable[[BaseCommand], None]:
        """Create a touch function that writes a fixed value.

        Parameters
        ----------
        value : object
            Value to write when the touch function is called.
        """
        def touch(cmd: BaseCommand) -> None:
            """Write the captured fixed value to ``cmd``."""
            cmd.set(value)
        return touch

    @staticmethod
    def touch(cmd: BaseCommand, arg: Any) -> None:
        """Touch the command with a provided argument or 1.

        Parameters
        ----------
        cmd : BaseCommand
            Command to touch.
        arg : object
            Value to write. If ``None``, writes ``1``.
        """
        if arg is not None:
            cmd.set(arg)
        else:
            cmd.set(1)

    @staticmethod
    def touchZero(cmd: BaseCommand) -> None:
        """Touch the command with 0.

        Parameters
        ----------
        cmd : BaseCommand
            Command to touch.
        """
        cmd.set(0)

    @staticmethod
    def touchOne(cmd: BaseCommand) -> None:
        """Touch the command with 1.

        Parameters
        ----------
        cmd : BaseCommand
            Command to touch.
        """
        cmd.set(1)

    @staticmethod
    def createPostedTouch(value: Any) -> Callable[[BaseCommand], None]:
        """Create a posted touch function for asynchronous writes.

        Parameters
        ----------
        value : object
            Value to post.
        """
        def postedTouch(cmd: BaseCommand) -> None:
            """Post the captured fixed value to ``cmd`` asynchronously."""
            cmd.post(value)
        return postedTouch

    @staticmethod
    def postedTouch(cmd: BaseCommand, arg: Any) -> None:
        """Post a command value without waiting for completion.

        Parameters
        ----------
        cmd : BaseCommand
            Command to post.
        arg : object
            Value to post.
        """
        cmd.post(arg)

    @staticmethod
    def postedTouchOne(cmd: BaseCommand) -> None:
        """Post a value of 1.

        Parameters
        ----------
        cmd : BaseCommand
            Command to post.
        """
        cmd.post(1)

    @staticmethod
    def postedTouchZero(cmd: BaseCommand) -> None:
        """Post a value of 0.

        Parameters
        ----------
        cmd : BaseCommand
            Command to post.
        """
        cmd.post(0)

    def replaceFunction(self, function: Callable[..., Any]) -> None:
        """Replace the command callback function.

        Parameters
        ----------
        function : callable
            New callback for this command. The wrapper provides keyword
            arguments ``root``, ``dev``, ``cmd``, and ``arg``; the callback
            may accept any subset of these names.
        """
        self._function = function
        self._functionWrap = pr.functionWrapper(function=self._function, callArgs=['root', 'dev', 'cmd', 'arg'])

    def _setDict(
        self,
        d: dict[Any, Any],
        writeEach: bool,
        modes: list[str],
        incGroups: str | list[str] | None = None,
        excGroups: str | list[str] | None = None,
        keys: Any = None,
    ) -> None:
        """Commands do not support dict writes."""
        pass

    def _getDict(
        self,
        modes: list[str],
        incGroups: str | list[str] | None = None,
        excGroups: str | list[str] | None = None,
        properties: Any = None,
    ) -> None:
        """Commands do not support dict reads."""
        return None

    def get(self, read: bool = True, index: int = -1) -> Any:
        """Return the cached command argument value.

        Parameters
        ----------
        read : bool, optional (default = True)
            Unused for commands.
        index : int, optional (default = -1)
            Unused for commands.
        """
        return self._default

    def _genDocs(self, file: Any) -> None:
        """Emit Sphinx documentation for this command."""
        print(f".. topic:: {self.path}",file=file)

        print('',file=file)
        print(pr.genDocDesc(self.description,4),file=file)
        print('',file=file)

        print(pr.genDocTableHeader(['Field','Value'],4,100),file=file)

        for a in ['name', 'path', 'enum', 'typeStr', 'disp']:
            astr = str(getattr(self,a))

            if astr != 'None':
                print(pr.genDocTableRow([a,astr],4,100),file=file)


# LocalCommand is the same as BaseCommand
LocalCommand = BaseCommand


class RemoteCommand(BaseCommand, pr.RemoteVariable):
    """Remote command backed by a memory-mapped variable.

    Parameters
    ----------
    name : str
        Command name.
    description : str, optional (default = "")
        Human-readable description.
    value : object, optional
        Default value.
    retValue : object, optional
        Example return value used to infer display type.
    enum : dict, optional
        Mapping from object values to display strings.
    hidden : bool, optional (default = False)
        If True, add the command to the ``Hidden`` group.
    groups : list[str], optional
        Groups to assign.
    minimum : object, optional
        Minimum allowed value.
    maximum : object, optional
        Maximum allowed value.
    function : callable, optional
        Callback executed when the command is invoked. The wrapper provides
        keyword arguments ``root``, ``dev``, ``cmd``, and ``arg``; the
        callback may accept any subset of these names.
        Default to no-op for command if None.
    base : object, optional (default = ``pr.UInt``)
        Base data type for the underlying remote variable.
    offset : int, optional
        Memory offset.
    bitSize : int, optional (default = 32)
        Bit width of the value.
    bitOffset : int, optional (default = 0)
        Bit offset of the value.
    overlapEn : bool, optional (default = False)
        Allow overlapping remote variables.
    guiGroup : str, optional
        GUI grouping label.
    **kwargs : Any
        Additional arguments forwarded to ``RemoteVariable``.
    """

    def __init__(
        self,
        *,
        name: str,
        description: str = '',
        value: Any = None,
        retValue: Any = None,
        enum: dict[object, str] | None = None,
        hidden: bool = False,
        groups: list[str] | None = None,
        minimum: Any | None = None,
        maximum: Any | None = None,
        function: Callable[..., Any] | None = None,
        base: Any = pr.UInt,
        offset: int | None = None,
        bitSize: int = 32,
        bitOffset: int = 0,
        overlapEn: bool = False,
        guiGroup: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize a remote command."""
        BaseCommand.__init__(
            self,
            name=name,
            retValue=retValue,
            function=function,
            guiGroup=guiGroup,
            **kwargs)

        pr.RemoteVariable.__init__(
            self,
            name=name,
            description=description,
            mode='WO',
            value=value,
            enum=enum,
            hidden=hidden,
            groups=groups,
            minimum=minimum,
            maximum=maximum,
            base=base,
            offset=offset,
            bitSize=bitSize,
            bitOffset=bitOffset,
            overlapEn=overlapEn,
            bulkOpEn=False,
            verify=False,
            guiGroup=guiGroup,
            **kwargs)

    def set(self, value: Any, *,  index: int = -1, write: bool = True) -> None:
        """Write a value to the remote command variable.

        Parameters
        ----------
        value : object
            Value to write.
        index : int, optional (default = -1)
            Optional index for array variables.
        write : bool, optional (default = True)
            If True, perform a hardware write transaction.
        """
        self._log.debug("%s.set(%r)", self, value)
        try:
            index = operator.index(index)

            self._set(value,index)

            if write:
                pr.startTransaction(self._block, type=rogue.interfaces.memory.Write, forceWr=True, checkEach=True, variable=self, index=index)

        except Exception as e:
            pr.logException(self._log,e)
            raise e


    def get(self, *, index: int = -1, read: bool = True) -> Any:
        """Read a value from the remote command variable.

        Parameters
        ----------
        index : int, optional (default = -1)
            Optional index for array variables.
        read : bool, optional (default = True)
            If True, perform a hardware read transaction.

        Returns
        -------
        object
            Retrieved value.
        """
        try:
            index = operator.index(index)

            if read:
                pr.startTransaction(self._block, type=rogue.interfaces.memory.Read, forceWr=False, checkEach=True, variable=self, index=index)

            return self._get(index)

        except Exception as e:
            pr.logException(self._log,e)
            raise e

    def _genDocs(self, file: Any) -> None:
        """Emit Sphinx documentation for this remote command."""
        BaseCommand._genDocs(self,file)

        for a in ['offset', 'bitSize', 'bitOffset', 'varBytes']:
            astr = str(getattr(self,a))

            if astr != 'None':
                print(pr.genDocTableRow([a,astr],4,100),file=file)



# Alias, this should go away
Command = BaseCommand
