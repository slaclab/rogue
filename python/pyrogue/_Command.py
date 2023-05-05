#-----------------------------------------------------------------------------
# Title      : PyRogue base module - Command Class
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


class CommandError(Exception):
    """
    Exception for command errors.
    """
    pass


class BaseCommand(pr.BaseVariable):
    """ """

    def __init__(self, *,
                 name=None,
                 description="",
                 value=0,
                 retValue=None,
                 enum=None,
                 hidden=False,
                 groups=None,
                 minimum=None,
                 maximum=None,
                 function=None,
                 background=False,
                 guiGroup=None,
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
        self._background = background
        self._retDisp = "{}"

        if self._background:
            self._log.error('Background commands are deprecated. Please use a Process device instead.')

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
        if self._background:
            with self._lock:
                if self._thread is not None and self._thread.isAlive():
                    self._log.warning('Command execution is already in progress!')
                    return None
                else:
                    self._thread = threading.Thread(target=self._doFunc, args=(arg,))
                    self._thread.start()

            return None
        else:
            return self._doFunc(arg)

    def _doFunc(self,arg):
        """
        Execute command: TODO: Update comments

        Parameters
        ----------
        arg :


        Returns
        -------

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


        Parameters
        ----------
        arg : str
             (Default value = None)

        Returns
        -------

        """
        return self.__call__(arg)

    @pr.expose
    def callDisp(self,arg=None):
        """


        Parameters
        ----------
        arg : str
             (Default value = None)

        Returns
        -------

        """
        return self.genDisp(self.__call__(arg),useDisp=self._retDisp)

    @staticmethod
    def nothing():
        """ """
        pass

    @staticmethod
    def read(cmd):
        """


        Parameters
        ----------
        cmd :


        Returns
        -------

        """
        cmd.get(read=True)

    @staticmethod
    def setArg(cmd, arg):
        """


        Parameters
        ----------
        cmd :

        arg :


        Returns
        -------

        """
        cmd.set(arg)

    @staticmethod
    def setAndVerifyArg(cmd, arg):
        """


        Parameters
        ----------
        cmd :

        arg :


        Returns
        -------

        """
        cmd.set(arg)
        ret = cmd.get()
        if ret != arg:
            raise CommandError(f'Verification failed for {cmd.path}. \nSet to {arg} but read back {ret}')

    @staticmethod
    def createToggle(sets):
        """


        Parameters
        ----------
        sets :


        Returns
        -------

        """
        def toggle(cmd):
            """


            Parameters
            ----------
            cmd :


            Returns
            -------

            """
            for s in sets:
                cmd.set(s)
        return toggle

    @staticmethod
    def toggle(cmd):
        """


        Parameters
        ----------
        cmd :


        Returns
        -------

        """
        cmd.set(1)
        cmd.set(0)

    @staticmethod
    def createTouch(value):
        """


        Parameters
        ----------
        value :


        Returns
        -------

        """
        def touch(cmd):
            """


            Parameters
            ----------
            cmd :


            Returns
            -------

            """
            cmd.set(value)
        return touch

    @staticmethod
    def touch(cmd, arg):
        """


        Parameters
        ----------
        cmd :

        arg :


        Returns
        -------

        """
        if arg is not None:
            cmd.set(arg)
        else:
            cmd.set(1)

    @staticmethod
    def touchZero(cmd):
        """


        Parameters
        ----------
        cmd :


        Returns
        -------

        """
        cmd.set(0)

    @staticmethod
    def touchOne(cmd):
        """


        Parameters
        ----------
        cmd :


        Returns
        -------

        """
        cmd.set(1)

    @staticmethod
    def createPostedTouch(value):
        """


        Parameters
        ----------
        value :


        Returns
        -------

        """
        def postedTouch(cmd):
            """


            Parameters
            ----------
            cmd :


            Returns
            -------

            """
            cmd.post(value)
        return postedTouch

    @staticmethod
    def postedTouch(cmd, arg):
        """


        Parameters
        ----------
        cmd :

        arg :


        Returns
        -------

        """
        cmd.post(arg)

    @staticmethod
    def postedTouchOne(cmd):
        """


        Parameters
        ----------
        cmd :


        Returns
        -------

        """
        cmd.post(1)

    @staticmethod
    def postedTouchZero(cmd):
        """


        Parameters
        ----------
        cmd :


        Returns
        -------

        """
        cmd.post(0)

    def replaceFunction(self, function):
        """


        Parameters
        ----------
        function :


        Returns
        -------

        """
        self._function = function
        self._functionWrap = pr.functionWrapper(function=self._function, callArgs=['root', 'dev', 'cmd', 'arg'])

    def _setDict(self,d,writeEach,modes,incGroups,excGroups,keys):
        """


        Parameters
        ----------
        d :

        writeEach :

        modes :

        incGroups :

        excGroups :

        keys :


        Returns
        -------

        """
        pass

    def _getDict(self,modes,incGroups,excGroups,properties):
        """


        Parameters
        ----------
        modes :

        incGroups :

        excGroups :


        Returns
        -------

        """
        return None

    def get(self,read=True, index=-1):
        """


        Parameters
        ----------
        read : bool
             (Default value = True)
        index : int
             (Default value = -1)

        Returns
        -------

        """
        return self._default

    def _genDocs(self,file):
        """


        Parameters
        ----------
        file :


        Returns
        -------

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
    """ """

    def __init__(self, *,
                 name,
                 description='',
                 value=None,
                 retValue=None,
                 enum=None,
                 hidden=False,
                 groups=None,
                 minimum=None,
                 maximum=None,
                 function=None,
                 base=pr.UInt,
                 offset=None,
                 bitSize=32,
                 bitOffset=0,
                 overlapEn=False,
                 guiGroup=None,
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


        Parameters
        ----------
        value :

        * :

        index : int
             (Default value = -1)
        write : bool
             (Default value = True)

        Returns
        -------

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


        Parameters
        ----------
        * :

        index : int
             (Default value = -1)
        read : bool
             (Default value = True)

        Returns
        -------

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


        Parameters
        ----------
        file :


        Returns
        -------

        """
        BaseCommand._genDocs(self,file)

        for a in ['offset', 'bitSize', 'bitOffset', 'varBytes']:
            astr = str(getattr(self,a))

            if astr != 'None':
                print(pr.genDocTableRow([a,astr],4,100),file=file)



# Alias, this should go away
Command = BaseCommand
