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
import Pyro4

class BaseCommand(pr.Node):

    def __init__(self, name=None, arg=False, description="", hidden=False, function=None):
        pr.Node.__init__(self, name=name, description=description, hidden=hidden)
        self._function = function if function is not None else BaseCommand.nothing

        if not callable(self._function):
            self._arg = True
        elif len(inspect.signature(self._function).parameters) == 3:
            self._arg = True
        else:
            self._arg = False

    @Pyro4.expose
    @property
    def arg(self):
        return self._arg

    @Pyro4.expose
    def call(self,arg=None):
        """Execute command: TODO: Update comments"""
        try:
            if self._function is not None:

                # Function is really a function
                if callable(self._function):
                    self._log.debug('Calling Command: {}'.format(self.name))

                    if len(inspect.signature(self._function).parameters) == 3:
                        self._function(self._parent, self, arg)
                    else:
                        self._function(self._parent, self)

                # Attempt to execute string as a python script
                else:
                    dev = self._parent
                    cmd = self
                    exec(textwrap.dedent(self._function))

        except Exception as e:
            self._log.exception(e)

    def __call__(self,arg=None):
        self.call(arg)

    @staticmethod
    def nothing(dev, cmd):
        pass

    @staticmethod
    def createToggle(sets):
        def toggle(dev, cmd):
            for s in sets:
                cmd.set(i)
        return toggle

    @staticmethod
    def toggle(dev, cmd):
        cmd.set(1)
        cmd.set(0)

    @staticmethod
    def createTouch(value):
        def touch(dev, cmd):
            cmd.set(value)
        return touch

    @staticmethod
    def touch(dev, cmd, arg):
        if arg is not None:
            cmd.set(arg)
        else:
            cmd.set(1)

    @staticmethod
    def touchZero(dev, cmd):
        cmd.set(0)

    @staticmethod
    def touchOne(dev, cmd):
        cmd.set(1)

    @staticmethod
    def postedTouch(dev, cmd, arg):
        if arg is not None:
            cmd.post(arg)
        else:
            cmd.post(1)


class LocalCommand(BaseCommand,pr.BaseVariable):
    def __init__(self, name=None, mode='RW', description="", hidden=False, function=None, update=False, **kwargs):
        BaseCommand.__init__(self,name=name, description=description, hidden=hidden, function=function)
        pr.BaseVariable.__init__(self, name=name, description=description, hidden=hidden, mode=mode, update=update, **kwargs)


class RemoteCommand(BaseCommand, pr.RemoteVariable):
    def __init__(self, name=None, mode='RW', description="", hidden=False, function=None, update=False, **kwargs):
        BaseCommand.__init__(self,name=name, description=description, hidden=hidden, function=function)
        pr.RemoteVariable.__init__(self, name=name, description=description, hidden=hidden, mode=mode, update=update, **kwargs)

    def set(self, value, write=True):
        self._log.debug("{}.set({})".format(self, value))
        try:
            self._block.set(self, value)

            if write:
                self._block.blockingTransaction(rogue.interfaces.memory.Write)

        except Exception as e:
            self._log.exception(e)

 
    def get(self, read=True):
        try:
            if read:
                self._block.blockingTransaction(rogue.interfaces.memory.Read)
                
            ret = self._block.get(self)

        except Exception as e:
            self._log.exception(e)
            return None

        return ret
            


# Legacy Support
def Command(offset=None, **kwargs):
    if offset is None:
        ret = LocalCommand(**kwargs)
        ret._depWarn = True
        return(ret)
    else:
        ret = RemoteCommand(offset=offset,**kwargs)
        ret._depWarn = True
        return(ret)

Command.nothing = BaseCommand.nothing
Command.toggle = BaseCommand.toggle
Command.touch = BaseCommand.touch
Command.touchZero = BaseCommand.touchZero
Command.touchOne = BaseCommand.touchOne
Command.postedTouch = BaseCommand.postedTouch


###################################
# (Hopefully) useful Command stuff
##################################
BLANK_COMMAND = Command(name='Blank', description='A singleton command that does nothing')

def command(order=0, **cmdArgs):
    def wrapper(func):
        func.PyrogueCommandOrder = order
        func.PyrogueCommandArgs = cmdArgs
        return func
    return wrapper
################################


