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
import threading
from typing import Any, Callable, Iterable, Optional

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
    groups : object, optional
        Group or list of groups to assign.
    minimum : object, optional
        Minimum allowed value.
    maximum : object, optional
        Maximum allowed value.
    function : callable, optional
        Callback to execute when the command is invoked.
    background : bool, optional (default = False)
        Reserved for background execution.
    guiGroup : str, optional
        GUI grouping label.
    **kwargs : Any
        Additional arguments forwarded to ``BaseVariable``.
    """

    def __init__(
        self,
        *,
        name: Optional[str] = None,
        description: str = "",
        value: Any = 0,
        retValue: Optional[Any] = None,
        enum: Optional[dict[object, str]] = None,
        hidden: bool = False,
        groups: Optional[Any] = None,
        minimum: Optional[Any] = None,
        maximum: Optional[Any] = None,
        function: Optional[Callable[..., Any]] = None,
        background: bool = False,
        guiGroup: Optional[str] = None,
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
        self._lock = threading.Lock()
        self._retDisp = "{}"

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
    def retTypeStr(self) -> Optional[str]:
        """Return the display string for the return type."""
        return self._retTypeStr

    def __call__(self, arg: Any = None) -> Any:
        """Invoke the command.

        Parameters
        ----------
        arg : object, optional
            Command argument. If ``None``, uses the default value.
        """
        return self._doFunc(arg)

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

            return ret

        except Exception as e:
            pr.logException(self._log,e)
            raise e

    @pr.expose
    def call(self, arg: Any = None) -> Any:
        """Invoke the command and return the raw result.

        Parameters
        ----------
        arg : object, optional
            Command argument.
        """
        return self.__call__(arg)

    @pr.expose
    def callDisp(self, arg: Any = None) -> str:
        """Invoke the command and return the display-formatted result.

        Parameters
        ----------
        arg : object, optional
            Command argument.
        """
        return self.genDisp(self.__call__(arg),useDisp=self._retDisp)

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
            New callback to execute for this command.
        """
        self._function = function
        self._functionWrap = pr.functionWrapper(function=self._function, callArgs=['root', 'dev', 'cmd', 'arg'])

    def _setDict(self, d: dict, writeEach: bool, modes: Any, incGroups: Any, excGroups: Any, keys: Any) -> None:
        """Commands do not support dict writes."""
        pass

    def _getDict(self, modes: Any, incGroups: Any, excGroups: Any, properties: Any) -> None:
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
    groups : object, optional
        Group or list of groups to assign.
    minimum : object, optional
        Minimum allowed value.
    maximum : object, optional
        Maximum allowed value.
    function : callable, optional
        Callback to execute when the command is invoked.
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
        enum: Optional[dict[object, str]] = None,
        hidden: bool = False,
        groups: Optional[Any] = None,
        minimum: Optional[Any] = None,
        maximum: Optional[Any] = None,
        function: Optional[Callable[..., Any]] = None,
        base: Any = pr.UInt,
        offset: Optional[int] = None,
        bitSize: int = 32,
        bitOffset: int = 0,
        overlapEn: bool = False,
        guiGroup: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize a remote command."""

        # RemoteVariable constructor will handle assignment of most params
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
        self._log.debug("{}.set({})".format(self, value))
        try:
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
