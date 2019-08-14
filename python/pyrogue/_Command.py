#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Title      : PyRogue base module - Command Class
#-----------------------------------------------------------------------------
# File       : pyrogue/_Command.py
# Created    : 2017-05-16
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
import textwrap
import time
from collections import OrderedDict as odict
import pyrogue as pr
import inspect
import threading

class CommandError(Exception):
    """ Exception for command errors."""
    pass

class BaseCommand(pr.BaseVariable):

    def __init__(self, *,
                 name=None,
                 description="",
                 value=0,
                 retValue=None,
                 enum=None,
                 hidden=False,                 
                 minimum=None,
                 maximum=None,
                 function=None,
                 background=False):

        pr.BaseVariable.__init__(
            self,
            name=name,
            description=description,
            mode='WO',
            value=value,
            enum=enum,
            hidden=hidden,
            minimum=minimum,
            maximum=maximum)
        
        self._function = function if function is not None else BaseCommand.nothing
        self._thread = None
        self._lock = threading.Lock()
        self._background = background

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
        except:
            self._arg = False

    @pr.expose
    @property
    def arg(self):
        return self._arg

    @pr.expose
    @property
    def retTypeStr(self):
        return self._retTypeStr

    @pr.expose
    def call(self,arg=None):
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
        """Execute command: TODO: Update comments"""
        if (self.parent.enable.value() is not True):
            return

        try:

            # Convert arg
            if arg is None:
                arg = self._default
            else:
                arg = self.parseDisp(arg)

            # Possible args
            pargs = {'dev' : self.parent, 'cmd' : self, 'arg' : arg}

            return pr.varFuncHelper(self._function,pargs, self._log,self.path)

        except Exception as e:
            self._log.exception(e)

    def __call__(self,arg=None):
        return self.call(arg)

    @staticmethod
    def nothing():
        pass

    @staticmethod
    def read(cmd):
        cmd.get(read=True)

    @staticmethod
    def setArg(cmd, arg):
        cmd.set(arg)

    @staticmethod
    def setAndVerifyArg(cmd, arg):
        cmd.set(arg)
        ret = cmd.get()
        if ret != arg:
            raise CommandError(
                f'Verification failed for {cmd.path}. \n'+
                f'Set to {arg} but read back {ret}')
        

    @staticmethod
    def createToggle(sets):
        def toggle(cmd):
            for s in sets:
                cmd.set(s)
        return toggle

    @staticmethod
    def toggle(cmd):
        cmd.set(1)
        cmd.set(0)

    @staticmethod
    def createTouch(value):
        def touch(cmd):
            cmd.set(value)
        return touch

    @staticmethod
    def touch(cmd, arg):
        if arg is not None:
            cmd.set(arg)
        else:
            cmd.set(1)

    @staticmethod
    def touchZero(cmd):
        cmd.set(0)

    @staticmethod
    def touchOne(cmd):
        cmd.set(1)

    @staticmethod
    def createPostedTouch(value):
        def postedTouch(cmd):
            cmd.post(value)
        return postedTouch

    @staticmethod
    def postedTouch(cmd, arg):
        cmd.post(arg)

    @staticmethod
    def postedTouchOne(cmd):
        cmd.post(1)

    @staticmethod
    def postedTouchZero(cmd):
        cmd.post(0)
        
    def _setDict(self,d,writeEach,modes):
        pass

    def _getDict(self,modes):
        return None

    def get(self,read=True):
        return self._default

# LocalCommand is the same as BaseCommand
LocalCommand = BaseCommand


class RemoteCommand(BaseCommand, pr.RemoteVariable):

    def __init__(self, *,
                 name,
                 description='',
                 value=None,
                 retValue=None,
                 enum=None,
                 hidden=False,
                 minimum=None,
                 maximum=None,
                 function=None,
                 base=pr.UInt,
                 offset=None,
                 bitSize=32,
                 bitOffset=0,
                 overlapEn=False):

        # RemoteVariable constructor will handle assignment of most params
        BaseCommand.__init__(
            self,
            name=name,
            retValue=retValue,
            function=function)

        pr.RemoteVariable.__init__(
            self,
            name=name,
            description=description,
            mode='WO',
            value=value,
            enum=enum,
            hidden=hidden,
            minimum=minimum,
            maximum=maximum,
            base=base,
            offset=offset,
            bitSize=bitSize,
            bitOffset=bitOffset,
            overlapEn=overlapEn,
            verify=False)


    def set(self, value, write=True):
        self._log.debug("{}.set({})".format(self, value))
        try:
            self._block.set(self, value)

            if write:
                self._block.startTransaction(rogue.interfaces.memory.Write, check=True)

        except Exception as e:
            self._log.exception(e)

 
    def get(self, read=True):
        try:
            if read:
                self._block.startTransaction(rogue.interfaces.memory.Read, check=True)
                
            ret = self._block.get(self)

        except Exception as e:
            self._log.exception(e)
            return None

        return ret

# Alias
Command = BaseCommand

