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

class CommandError(Exception):
    """ Exception for command errors."""
    pass

class BaseCommand(pr.BaseVariable):

    def __init__(self, name=None, description="", hidden=False, function=None,
                 value=0, enum=None, minimum=None, maximum=None, **dump):

        pr.BaseVariable.__init__(self, name=name, description=description, update=False,
                                 mode='WO', value=value, enum=enum, minimum=minimum, maximum=maximum)
        
        self._function = function if function is not None else BaseCommand.nothing

        # args flag
        try:
            self._arg = 'arg' in inspect.getfullargspec(self._function).args

        # C++ functions
        except:
            self._arg = False

    @Pyro4.expose
    @property
    def arg(self):
        return self._arg

    @Pyro4.expose
    def call(self,arg=None):
        """Execute command: TODO: Update comments"""
        try:

            # Convert arg
            arg = self.parseDisp(arg)

            # Possible args
            pargs = {'dev' : self.parent, 'cmd' : self, 'arg' : arg}

            pr.varFuncHelper(self._function,pargs, self._log,self.path)

        except Exception as e:
            self._log.exception(e)

    def __call__(self,arg=None):
        self.call(arg)

    @staticmethod
    def nothing():
        pass

    @staticmethod
    def createToggle(sets):
        def toggle(cmd):
            for s in sets:
                cmd.set(i)
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
    def postedTouch(cmd, arg):
        if arg is not None:
            cmd.post(arg)
        else:
            cmd.post(1)


# LocalCommand is the same as BaseCommand
LocalCommand = BaseCommand


class RemoteCommand(BaseCommand, pr.RemoteVariable):

    def __init__(self, name=None, description="", hidden=False, function=None,
                 base=pr.UInt, value=None, enum=None, minimum=None, maximum=None,
                 offset=None, bitSize=32, bitOffset=0, **dump):
       
        if 'stride' in dump:
            raise VariableError('stride passed for RemoteCommand {}. Use addRemoteCommands() instead.'.format(name))

        BaseCommand.__init__(self,name=name, description=description,
                             hidden=hidden, function=function, value=value,
                             enum=enum, minimum=minimum, maximum=maximum)

        pr.RemoteVariable.__init__(self, name=name, description=description, 
                                   base=base, mode='WO', value=value, 
                                   enum=enum, hidden=hidden, minimum=minimum, maximum=maximum,
                                   offset=offset, bitSize=bitSize, bitOffset=bitOffset, verify=False)


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


