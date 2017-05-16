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
import pyrogue
import textwrap


class VariableError(Exception):
    """ Exception for variable access errors."""
    pass


class Base(object):
    """
    Class which defines how data is stored, displayed and converted.
    """
    def __init__(self):
        pass


class Variable(pyrogue.Node):
    """
    Variable holder.
    A variable can be associated with a block of real memory or just manage a local variable.

    offset: offset is the memory offset (in bytes) if the associated with memory. 
            This offset must be aligned to the minimum accessable memory entry for 
            the underlying hardware. Variables with the same offset value will be 
            associated with the same block object. 
    bitSize: The size in bits of the variable entry if associated with memory.
    bitOffset: The offset in bits from the byte offset if associated with memory.
    pollInterval: How often the variable should be polled (in seconds) defualts to 0 (not polled)
    value: An initial value to set the variable to
    base: This defined the type of entry tracked by this variable.
          hex = An unsigned integer in hex form
          bin = An unsigned integer in binary form
          uint = An unsigned integer
          enum = An enum with value,key pairs passed
          bool = A True,False value
          range = An unsigned integer with a bounded range
          string = A string value
          float = A float value
    mode: Access mode of the variable
          RW = Read/Write
          RO = Read Only
          WO = Write Only
          SL = A slave variable which is not included in block writes or config/status dumps.
    enum: A dictionary of index:value pairs ie {0:'Zero':0,'One'}
    minimum: Minimum value for base=range
    maximum: Maximum value for base=range
    setFunction: Function to call to set the value. dev, var, value passed.
        setFunction(dev,var,value)
    getFunction: Function to call to set the value. dev, var passed. Return value.
        value = getFunction(dev,var)
    hidden: Variable is hidden

    The set and get functions can be in one of two forms. They can either be a series 
    of python commands in a string or a pointer to a class function. When defining 
    pythone functions in a string the get function must update the 'value' variable with
    the variable value. For the set function the variable 'value' is set in the value 
    variable. ie setFunction='_someVariable = value', getFunction='value = _someVariable'
    The string function is executed in the context of the variable object with 'dev' set
    to the parent device object.
    """
    def __init__(self, name, description="", parent=None, offset=None, bitSize=32, bitOffset=0, pollInterval=0, value=None,
                 base='hex', mode='RW', enum=None, units=None, hidden=False,
                 minimum=None, maximum=None, verify=True,
                 setFunction=None, getFunction=None, dependencies=None, 
                 beforeReadCmd=None, afterWriteCmd=None, **dump):
        """Initialize variable class""" 

        # Public Attributes
        self.offset    = offset
        self.bitSize   = bitSize
        self.bitOffset = bitOffset
        self.base      = base      
        self.mode      = mode
        self.verify    = verify
        self.enum      = enum
        self.units     = units
        self.minimum   = minimum # For base='range'
        self.maximum   = maximum # For base='range'
        self._defaultValue = value
        self._pollInterval = pollInterval

        # Check modes
        if (self.mode != 'RW') and (self.mode != 'RO') and \
           (self.mode != 'WO') and (self.mode != 'SL') and \
           (self.mode != 'CMD'):
            raise VariableError('Invalid variable mode %s. Supported: RW, RO, WO, SL, CMD' % (self.mode))

        # Tracking variables
        self._block       = None
        self._setFunction = setFunction
        self._getFunction = getFunction
        self.__listeners  = []

        if self.base == 'string':
            self._scratch = ''
        else:
            self._scratch = 0

        # Dependency tracking
        self.__dependencies = []
        if dependencies is not None:
            for d in dependencies:
                self.addDependency(d)

        # Commands that run before or after block access
        self._beforeReadCmd   = beforeReadCmd
        self._afterWriteCmd   = afterWriteCmd

        # Call super constructor
        pyrogue.Node.__init__(self, name=name, classType='variable', description=description, hidden=hidden, parent=parent)

    def _rootAttached(self):
        # Variables are always leaf nodes so no need to recurse
        if self._defaultValue is not None:
            self.set(self._defaultValue, write=True)

        if self._pollInterval > 0 and self._root._pollQueue:
            self._root._pollQueue.updatePollInterval(self)


    def addDependency(self, dep):
        self.__dependencies.append(dep)
        dep.addListener(self)

    @property
    def pollInterval(self):
        return self._pollInterval

    @pollInterval.setter
    def pollInterval(self, interval):
        self._pollInterval = interval        
        if isinstance(self._root, Root) and self._root._pollQueue:
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
        if isinstance(listener, Variable):
            self.__listeners.append(listener.linkUpdated)
        else:
            self.__listeners.append(listener)

    def beforeReadCmd(self, cmd):
        self._beforeReadCmd = cmd
    beforeReadCmd = property(None, beforeReadCmd)

    def afterWriteCmd(self, cmd):
        self._afterWriteCmd = cmd
    afterWriteCmd = property(None, afterWriteCmd)

    def set(self,value,write=True):
        """
        Set the value and write to hardware if applicable
        Writes to hardware are blocking. An error will result in a logged exception.
        """

        self._log.debug("{}.set({})".format(self, value))
        try:
            self._rawSet(value)

            if write and self._block and self._block.mode != 'RO':
                self._block.blockingTransaction(rogue.interfaces.memory.Write)
                if self._afterWriteCmd is not None:
                    self._afterWriteCmd()

                if self._block.mode == 'RW':
                    if self._beforeReadCmd is not None:
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
            self._rawSet(value)
            if self._block and self._block.mode != 'RO':
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
            if read and self._block and self._block.mode != 'WO':
                if self._beforeReadCmd is not None:
                    self._beforeReadCmd()
                self._block.blockingTransaction(rogue.interfaces.memory.Read)
            ret = self._rawGet()
        except Exception as e:
            self._log.error(e)
            return None

        # Update listeners for all variables in the block
        if read:
            if self._block:
                self._block._updated()
            else:
                self._updated()
        return ret

    @property
    def block(self):
        """Get the block associated with this varable if it exists"""
        return self._block

    def _updated(self):
        """Variable has been updated. Inform listeners."""
        
        # Don't generate updates for SL and WO variables
        if self.mode == 'WO' or self.mode == 'SL': return

        value = self._rawGet()
        
        for func in self.__listeners:
            func(self,value)

        # Root variable update log
        self._root._varUpdated(self,value)

    def _rawSet(self,value):
        """
        Raw set method. This is called by the set() method in order to convert the passed
        variable to a value which can be written to a local container (block or local variable).
        The set function defaults to setting a string value to the local block if mode='string'
        or an integer value for mode='hex', mode='uint' or mode='bool'. All others will default to
        a uint set. 
        The user can use the setFunction attribute to pass a string containing python commands or
        a specific method to call. When using a python string the code will find the passed value
        as the variable 'value'. A passed method will accept the variable object and value as args.
        Listeners will be informed of the update.
        _rawSet() is called during bulk configuration loads with a seperate hardware access generated later.
        """
        if self._setFunction is not None:
            if callable(self._setFunction):
                self._setFunction(self._parent,self,value)
            else:
                dev = self._parent
                exec(textwrap.dedent(self._setFunction))

        elif self._block:        
            if self.base == 'string':
                self._block.setString(value)
            else:
                if self.base == 'bool':
                    if value: ivalue = 1
                    else: ivalue = 0
                elif self.base == 'enum':
                    ivalue = {value: key for key,value in self.enum.items()}[value]
                    self._log.debug('_rawSet enum value= {}, ivalue={}'.format(value, ivalue))
                else:
                    ivalue = int(value)
                self._block.setUInt(self.bitOffset, self.bitSize, ivalue)        

        # Inform listeners
        self._updated()

    def _rawGet(self):
        """
        Raw get method. This is called by the get() method in order to convert the local
        container value (block or local variable) to a value returned to the caller.
        The set function defaults to getting a string value from the local block if mode='string'
        or an integer value for mode='hex', mode='uint' or mode='bool'. All others will default to
        a uint get. 
        The user can use the getFunction attribute to pass a string containing python commands or
        a specific method to call. When using a python string the code will set the 'value' variable
        with the value to return. A passed method will accept the variable as an arg and return the
        resulting value.
        _rawGet() can be called from other levels to get current value without generating a hardware access.
        """
        if self._getFunction is not None:
            if callable(self._getFunction):
                return(self._getFunction(self._parent,self))
            else:
                dev = self._parent
                value = 0
                ns = locals()
                exec(textwrap.dedent(self._getFunction),ns)
                return ns['value']

        elif self._block:        
            if self.base == 'string':
                return(self._block.getString())
            else:
                ivalue = self._block.getUInt(self.bitOffset,self.bitSize)

                if self.base == 'bool':
                    return(ivalue != 0)
                elif self.base == 'enum':
                    self._log.debug('_rawGet enum value= {}, ivalue = {}'.format(self.enum[ivalue], ivalue))
                    return self.enum[ivalue]
                else:
                    return ivalue
        else:
            return None

    def linkUpdated(self, var, value):
        self._updated()

