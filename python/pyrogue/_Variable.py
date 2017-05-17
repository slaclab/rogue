#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Title      : PyRogue base module - Variable Class
#-----------------------------------------------------------------------------
# File       : pyrogue/_Variable.py
# Created    : 2016-09-29
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to 
# the license terms in the LICENSE.txt file found in the top-level directory 
# of this distribution and at: 
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html. 
# No part of the rogue software platform, including this file, may be 
# copied, modified, propagated, or distributed except according to the terms 
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
import pyrogue as pr
import textwrap


class VariableError(Exception):
    """ Exception for variable access errors."""
    pass


class BaseVariable(pr.Node):

    def __init__(self, name=None, description="", parent=None, 
                 mode='RW', value=None, base='hex', disp=None,
                 enum=None, units=None, hidden=False, minimum=None, maximum=None, **dump):

        # Public Attributes
        self.mode           = mode
        self.enum           = enum
        self.units          = units
        self.minimum        = minimum # For base='range'
        self.maximum        = maximum # For base='range'

        self._default       = value
        self.__listeners    = []
        self._pollInterval  = 0
        self._beforeReadCmd = None
        self._afterWriteCmd = None
        self.__dependencies = []

        self._base = base

        # Handle legacy model declarations
        if base == 'hex' or base == 'uint' or base == 'bin' or base == 'enum' or base == 'range':
            self._base = pr.IntModel(signed=False, endianness='little')
        elif base == 'int':
            self._base = pr.IntModel(signed=True, endianness='little')
        elif base == 'bool':
            self._base = pr.BoolModel()
        elif base == 'string':
            self._base = pr.StringModel()
        elif base == 'float':
            self._base = pr.FloatModel()

        # disp follows base if not specified
        if disp is None and isinstance(base, str):
            disp = base
        elif disp is None:
            disp = self._base.defaultdisp

        if isinstance(disp, dict):
            self.disp = 'enum'
            self.enum = disp
        elif isinstance(disp, list):
            self.disp = 'enum'
            self.enum = {k:str(k) for k in disp}
        elif isinstance(disp, str):
            if disp == 'range':
                self.disp = 'range'
            elif disp == 'hex':
                self.disp = '{:x}'
            elif disp == 'uint':
                self.disp = '{:d}'
            elif disp == 'bin':
                self.disp = '{:b}'
            elif disp == 'string':
                self.disp = '{}'
            elif disp == 'bool':
                self.disp = 'enum'
                self.enum = {False: 'False', True: 'True'}
            else:
                self.disp = disp

        self.revEnum = None
        self.valEnum = None
        if self.enum is not None:
            self.revEnum = {v:k for k,v in self.enum.items()}
            self.valEnum = [v for k,v in self.enum.items()]

        # Check modes
        if (self.mode != 'RW') and (self.mode != 'RO') and \
           (self.mode != 'WO') and (self.mode != 'SL') and \
           (self.mode != 'CMD'):
            raise VariableError('Invalid variable mode %s. Supported: RW, RO, WO, SL, CMD' % (self.mode))

        # Call super constructor
        pr.Node.__init__(self, name=name, description=description, hidden=hidden, parent=parent)

    def addDependency(self, dep):
        self.__dependencies.append(dep)
        dep.addListener(self)

    @property
    def pollInterval(self):
        return self._pollInterval

    @pollInterval.setter
    def pollInterval(self, interval):
        self._pollInterval = interval
        if isinstance(self._root, pr.Root) and self._root._pollQueue:
            self._root._pollQueue.updatePollInterval(self)

    @property
    def dependencies(self):
        return self.__dependencies

    def addListener(self, listener):
        """
        Add a listener Variable or function to call when variable changes. 
        If listener is a Variable then Variable.linkUpdated() will be used as the function
        This is usefull when chaining variables together. (adc conversions, etc)
        The variable and value will be passed as an arg: func(var,value)
        """
        if isinstance(listener, BaseVariable):
            self.__listeners.append(listener.linkUpdated)
        else:
            self.__listeners.append(listener)

    def set(self, value, write=True):
        pass

    def post(self,value):
        pass

    def get(self,read=True):
        return None

    def linkUpdated(self, var, value):
        self._updated()

    def getDisp(self, read=True):
        #print('{}.getDisp(read={}) disp={} value={}'.format(self.path, read, self.disp, self.get(read=False)))
        if self.disp == 'enum':
            print('enum: {}'.format(self.enum))
            print('get: {}'.format(self.get(read)))
            return self.enum[self.get(read)]
        else:
            return self.disp.format(self.get(read))

    def parseDisp(self, sValue):
        if self.disp == 'enum':
            return self.revEnum[sValue]
        else:
             return (parse.parse(self.disp, sValue)[0])

    def setDisp(self, sValue, write=True):
        self.set(self.parseDisp(sValue), write)

    def _rootAttached(self):
        # Variables are always leaf nodes so no need to recurse
        if self._default is not None:
            self.set(self._default, write=False)

        if self._pollInterval > 0 and self._root._pollQueue is not None:
            self._root._pollQueue.updatePollInterval(self)

    def _updated(self):
        """Variable has been updated. Inform listeners."""
        value = self.get(read=False)

        for func in self.__listeners:
            func(self, value)

        # Root variable update log
        self._root._varUpdated(self,value)

    def __set__(self, value):
        self.set(value, write=True)

    def __get__(self):
        self.get(read=True)


class RemoteVariable(BaseVariable):

    def __init__(self, name=None, description="", parent=None, 
                 mode='RW', value=None, base='hex', disp=None,
                 enum=None, units=None, hidden=False, minimum=None, maximum=None,
                 offset=None, bitSize=32, bitOffset=0, pollInterval=0, 
                 verify=True, beforeReadCmd=lambda: None, afterWriteCmd=lambda: None, **dump):

        BaseVariable.__init__(self, name=name, description=description, parent=parent, 
                     mode=mode, value=value, base=base, disp=disp,
                     enum=enum, units=units, hidden=hidden, minimum=minimum, maximum=maximum);

        self._pollInterval  = pollInterval
        self._beforeReadCmd = beforeReadCmd
        self._afterWriteCmd = afterWriteCmd

        self._block    = None

        self.offset    = offset
        self.bitSize   = bitSize
        self.bitOffset = bitOffset
        self.verify    = verify

    def set(self, value, write=True):
        """
        Set the value and write to hardware if applicable
        Writes to hardware are blocking. An error will result in a logged exception.
        """

        self._log.debug("{}.set({})".format(self, value))
        try:
            self._block.set(self, value)
            self._updated()

            if write and self._block.mode != 'RO':
                self._block.blockingTransaction(rogue.interfaces.memory.Write)
                self._afterWriteCmd()

                if self._block.mode == 'RW':
                    self._beforeReadCmd()
                    self._block.blockingTransaction(rogue.interfaces.memory.Verify)

        except Exception as e:
            self._log.error(e)

    def post(self,value):
        """
        Set the value and write to hardware if applicable using a posted write.
        Writes to hardware are posted.
        """
        try:
            self._block.set(self, value)
            self._updated()

            if self._block.mode != 'RO':
                self._block.backgroundTransaction(rogue.interfaces.memory.Post)

        except Exception as e:
            self._log.error(e)

    def get(self,read=True):
        """ 
        Return the value after performing a read from hardware if applicable.
        Hardware read is blocking. An error will result in a logged exception.
        Listeners will be informed of the update.
        """
        try:
            if read and self._block.mode != 'WO':
                self._beforeReadCmd()
                self._block.blockingTransaction(rogue.interfaces.memory.Read)

            ret = self._block.get(self)

        except Exception as e:
            self._log.error(e)
            return None

        # Update listeners for all variables in the block
        if read:
            self._block._updated()

        return ret


class LocalVariable(BaseVariable):

    def __init__(self, name=None, description="", parent=None, 
                 mode='RW', value=None, base='hex', disp=None,
                 enum=None, units=None, hidden=False, minimum=None, maximum=None,
                 localSet=None, localGet=None, pollInterval=0, **dump):

        BaseVariable.__init__(self, name=name, description=description, parent=parent, 
                     mode=mode, value=value, base=base, disp=disp,
                     enum=enum, units=units, hidden=hidden, minimum=minimum, maximum=maximum)

        self._pollInterval = pollInterval
        self._block = pr.LocalBlock(self,localSet,localGet,self._default)

    def set(self, value, write=True):
        try:
            self._block.set(self, value)
            self._updated()

        except Exception as e:
            self._log.error(e)

    def get(self,read=True):
        try:
            ret = self._block.get(self)

        except Exception as e:
            self._log.error(e)
            return None

        if read: self._block._updated()
        return ret


class LinkVariable(BaseVariable):

    def __init__(self, name=None, description="", parent=None, 
                 mode='RW', value=None, base='hex', disp=None,
                 enum=None, units=None, hidden=False, minimum=None, maximum=None,
                 linkedSet=None, linkedGet=None, dependencies=None, **dump):

        BaseVariable.__init__(self, name=name, description=description, parent=parent, 
                     mode=mode, value=value, base=base, disp=disp,
                     enum=enum, units=units, hidden=hidden, minimum=minimum, maximum=maximum)

        # Set and get functions
        self._linkedGet = linkedGet
        self._linkedSet = linkedSet

        # Dependency tracking
        if dependencies is not None:
            for d in dependencies:
                self.addDependency(d)


    def set(self, value, write=True):
        """
        The user can use the linkedSet attribute to pass a string containing python commands or
        a specific method to call. When using a python string the code will find the passed value
        as the variable 'value'. A passed method will accept the variable object and value as args.
        Listeners will be informed of the update.
        """
        if self._linkedSet is not None:
            if callable(self._linkedSet):
                self._linksedSet(self._parent,self,value)
            else:
                dev = self._parent
                var = self
                exec(textwrap.dedent(self._linkedSet))

    def get(self):
        """
        The user can use the linkedGet attribute to pass a string containing python commands or
        a specific method to call. When using a python string the code will set the 'value' variable
        with the value to return. A passed method will accept the variable as an arg and return the
        resulting value.
        """
        if self._linkedGet is not None:
            if callable(self._linkedGet):
                return(self._linkedGet(self._parent,self))
            else:
                dev = self._parent
                var = self
                value = 0
                ns = locals()
                exec(textwrap.dedent(self._linkedGet),ns)
                return ns['value']
        else:
            return None

# Legacy Support
def Variable(local=False, setFunction=None, getFunction=None, **kwargs):

    # Local Variables override get and set functions
    if local or setFunction is not None or getFunction is not None:
        return(LocalVariable(localSet=setFunction, localGet=getFunction, **kwargs))

    # Otherwise assume remote
    else: return(RemoteVariable(**kwargs))

