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
import rogue.interfaces.memory
import pyrogue as pr
import inspect
import threading

from _collections_abc import Callable
from typing import Union, Type, List, Dict, Any, Optional


class CommandError(Exception):
    """
    Exception for command errors.
    """
    pass


class BaseCommand(pr.BaseVariable):
    """

    Abstract base class for all other Command Classses.
    All Commands are sub-classes of BaseVariable and support all Variable attributes.

    Commands are tasks applied to devices. Includes a number of commonly used commands
    and sequence generators.

    Args:
        name (str) : The name of the variable
        description (str) : A brief description of the variable
        value (int) : An optional value to determine the arg type
        retValue (str) :
        enum (dict) : A dictionary of key,value pairs for args which have a set of selections
        hidden (bool) : Whether the variable is visible to external classes
        groups (str) : Groups
        minimum (int) : Optional minimum value for a arg with a set range
        maximum (int) : Optional maximum value for a arg with a set range
        function (function) : Function which is called when the command is executed. Must follow template -
            function(device containing the variable, command generating the call, arg passed by command executrion).
        background (str) : Background
        guiGroup (str) : The GUI group

    Attributes:
        _functionWrap (object) : A wrapper for the functino variable. Includes 'root', 'dev', 'cmd', 'arg'.
        _thread (object) : The thread
        _lock (object) : The lock for the thread
        _retDisp (object) : Ret Disp
        _retTypeStr (str) :Ret type string
        _arg (bool) : Args flag
    """

    def __init__(
                self, *,
                name: Optional[str] = None,
                description: str = "",
                value: int = 0,
                retValue: Union[None, List, Any] = None,
                enum: Optional[Dict] = None,
                hidden: bool = False,
                groups: Union[List[str], str, None] = None,
                minimum: Optional[int] = None,
                maximum: Optional[int] = None,
                function: Optional[Callable] = None,
                background: bool = False,
                guiGroup: Optional[str] = None,
                **kwargs):

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
    def arg(self):
        """ """
        return self._arg

    @pr.expose
    @property
    def retTypeStr(self):
        """ """
        return self._retTypeStr

    def __call__(self,arg=None):
        return self._doFunc(arg)

    def _doFunc(self,arg):
        """
        Execute command: TODO: Update comments

        Args:
            arg :


        Returns:

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
    def call(self,arg=None):
        """

        Args:
            arg (str) :     (Default value = None)

        Returns:

        """
        return self.__call__(arg)

    @pr.expose
    def callDisp(self,arg=None):
        """
        Args:
            arg (str) :     (Default value = None)

        Returns:

        """
        return self.genDisp(self.__call__(arg),useDisp=self._retDisp)

    @staticmethod
    def nothing():
        """ """
        pass

    @staticmethod
    def read(cmd):
        """
        Args:
            cmd :
        Returns:

        """
        cmd.get(read=True)

    @staticmethod
    def setArg(cmd, arg):
        """
        Args:
            cmd :
            arg :

        Returns:

        """
        cmd.set(arg)

    @staticmethod
    def setAndVerifyArg(cmd, arg):
        """
        Args:
            cmd :
            arg :

        Returns:

        """
        cmd.set(arg)
        ret = cmd.get()
        if ret != arg:
            raise CommandError(f'Verification failed for {cmd.path}. \nSet to {arg} but read back {ret}')

    @staticmethod
    def createToggle(sets):
        """
        Args:
            sets :

        Returns:

        """
        def toggle(cmd):
            """


            Args:
            cmd :


            Returns:

            """
            for s in sets:
                cmd.set(s)
        return toggle

    @staticmethod
    def toggle(cmd):
        """
        Args:
            cmd :


        Returns:

        """
        cmd.set(1)
        cmd.set(0)

    @staticmethod
    def createTouch(value):
        """
        Args:
            value :


        Returns:

        """
        def touch(cmd):
            """


            Args:
                cmd :


            Returns:

            """
            cmd.set(value)
        return touch

    @staticmethod
    def touch(cmd, arg):
        """
        Args:
            cmd :
            arg :

        Returns:

        """
        if arg is not None:
            cmd.set(arg)
        else:
            cmd.set(1)

    @staticmethod
    def touchZero(cmd):
        """
        Args:
            cmd :


        Returns:

        """
        cmd.set(0)

    @staticmethod
    def touchOne(cmd):
        """
        Args:
            cmd :


        Returns:

        """
        cmd.set(1)

    @staticmethod
    def createPostedTouch(value):
        """
        Args:
            value :


        Returns:

        """
        def postedTouch(cmd):
            """


            Args:
                cmd :


            Returns:

            """
            cmd.post(value)
        return postedTouch

    @staticmethod
    def postedTouch(cmd, arg):
        """
        Args:
            cmd :
            arg :

        Returns:

        """
        cmd.post(arg)

    @staticmethod
    def postedTouchOne(cmd):
        """
        Args:
            cmd :

        Returns:

        """
        cmd.post(1)

    @staticmethod
    def postedTouchZero(cmd):
        """
        Args:
            cmd :

        Returns:

        """
        cmd.post(0)

    def replaceFunction(self, function):
        """
        Args:
            function :

        Returns:

        """
        self._function = function
        self._functionWrap = pr.functionWrapper(function=self._function, callArgs=['root', 'dev', 'cmd', 'arg'])

    def _setDict(self,d,writeEach,modes,incGroups,excGroups,keys):
        """
        Args:
            d :
            writeEach :
            modes :
            incGroups :
            excGroups :
            keys :

        Returns:

        """
        pass

    def _getDict(self,modes,incGroups,excGroups,properties):
        """
        Args:
            modes :
            incGroups :
            excGroups :

        Returns:

        """
        return None

    def get(self,read=True, index=-1):
        """
        Args:
            read (bool) : (Default value = True)
            index (int) : (Default value = -1)

        Returns:

        """
        return self._default

    def _genDocs(self,file):
        """
        Args:
            file :

        Returns:

        """
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
    """ A Command which has a 1:1 associated with a hardware element.
    Subclass of RemoteVariable. Passed attributes are the same as BaseCommand and RemoteVariable.

    Used to generate a set of writes to the associated hardware element.
    Add additional functions to Command objects.

    """

    def __init__(
                self, *,
                name: str,
                description: str = "",
                value: Optional[Any] = None,
                retValue: Union[None, List, Any] = None,
                enum: Optional[Dict] = None,
                hidden: bool = False,
                groups: Union[List[str], str, None] = None,
                minimum: Optional[int] = None,
                maximum: Optional[int] = None,
                function: Optional[Callable] = None,
                base: Type[pr.Model] = pr.UInt,
                offset: Union[int, List, None] = None,
                bitSize: int = 32,
                bitOffset: int = 0,
                overlapEn: bool = False,
                guiGroup: Optional[str] = None,
                **kwargs):

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

    def set(self, value, *,  index=-1, write=True):
        """
        Args:
            value :
            * :
            index (int) : (Default value = -1)
            write (bool) : (Default value = True)

        Returns:

        """
        self._log.debug("{}.set({})".format(self, value))
        try:
            self._set(value,index)

            if write:
                pr.startTransaction(self._block, type=rogue.interfaces.memory.Write, forceWr=True, checkEach=True, variable=self, index=index)

        except Exception as e:
            pr.logException(self._log,e)
            raise e


    def get(self, *, index=-1, read=True):
        """
        Args:
            * :

            index (int) : (Default value = -1)
            read (bool) : (Default value = True)

        Returns:

        """
        try:
            if read:
                pr.startTransaction(self._block, type=rogue.interfaces.memory.Read, forceWr=False, checkEach=True, variable=self, index=index)

            return self._get(index)

        except Exception as e:
            pr.logException(self._log,e)
            raise e

    def _genDocs(self,file):
        """
        Args:
            file :

        Returns:

        """
        BaseCommand._genDocs(self,file)

        for a in ['offset', 'bitSize', 'bitOffset', 'varBytes']:
            astr = str(getattr(self,a))

            if astr != 'None':
                print(pr.genDocTableRow([a,astr],4,100),file=file)



# Alias, this should go away
Command = BaseCommand
