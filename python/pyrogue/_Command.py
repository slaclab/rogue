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
import textwrap
import time
from collections import OrderedDict as odict
import pyrogue


class Command(pyrogue.Variable):
    """Command holder: Subclass of variable with callable interface"""

    def __init__(self, parent=None, base='None', mode='CMD', function=None, **kwargs):

        pyrogue.Variable.__init__(self, base=base, mode=mode, parent=parent, **kwargs)

        self.classType = 'command'
        self._function = function if function is not None else Command.nothing

    def __call__(self,arg=None):
        """Execute command: TODO: Update comments"""
        try:
            if self._function is not None:

                # Function is really a function
                if callable(self._function):
                    self._log.debug('Calling CMD: {}'.format(self.name))
                    self._function(self._parent, self, arg)

                # Function is a CPSW sequence
                elif type(self._function) is odict:
                    for key,value in self._function.items():

                        # Built in
                        if key == 'usleep':
                            time.sleep(value/1e6)

                        # Determine if it is a command or variable
                        else:
                            n = self._parent._nodes[key]

                            if callable(n): 
                                n(value)
                            else: 
                                n.set(value)

                # Attempt to execute string as a python script
                else:
                    dev = self._parent
                    exec(textwrap.dedent(self._function))

        except Exception as e:
            self._log.error(e)

    @staticmethod
    def nothing(dev, cmd, arg):
        pass

    @staticmethod
    def toggle(dev, cmd, arg):
        cmd.set(1)
        cmd.set(0)

    @staticmethod
    def touch(dev, cmd, arg):
        if arg is not None:
            cmd.set(arg)
        else:
            cmd.set(1)

    @staticmethod
    def touchZero(dev, cmd, arg):
        cmd.set(0)

    @staticmethod
    def touchOne(dev, cmd, arg):
        cmd.set(1)

    @staticmethod
    def postedTouch(dev, cmd, arg):
        if arg is not None:
            cmd.post(arg)
        else:
            cmd.post(1)

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


