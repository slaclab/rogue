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
import rogue.interfaces.memory
import parse
import Pyro4
import math
from collections import Iterable

class VariableError(Exception):
    """ Exception for variable access errors."""
    pass

class BaseVariable(pr.Node):

    def __init__(self, name=None, description="", update=True,
                 mode='RW', value=None, disp='{}',
                 enum=None, units=None, hidden=False, minimum=None, maximum=None, **dump):

        # Public Attributes
        self._mode          = mode
        self._units         = units
        self._minimum       = minimum # For base='range'
        self._maximum       = maximum # For base='range'
        self._update        = update
        self._default       = value
        self._pollInterval  = 0
        self.__listeners    = []
        self.__dependencies = []

        # Build enum if specified
        self._disp = disp
        self._enum = enum
        if isinstance(disp, dict):
            self._disp = 'enum'
            self._enum = disp
        elif isinstance(disp, list):
            self._disp = 'enum'
            self._enum = {k:str(k) for k in disp}
        elif type(value) == bool and enum is None:
            self._disp = 'enum'
            self._enum = {False: 'False', True: 'True'}

        if enum is not None:
            self._disp = 'enum'
            if not self._default in enum:
                self._default = [k for k,v in enum.items()][0]

        # Determine typeStr from value type
        if value is not None:
            self._typeStr = value.__class__.__name__
        else:
            self._typeStr = 'Unknown'

        # Create inverted enum
        self._revEnum = None
        if self._enum is not None:
            self._revEnum = {v:k for k,v in self._enum.items()}

        # Legacy SL and CMD become RW
        if self._mode == 'SL': self._mode = 'RW'
        if self._mode == 'CMD' : self._mode = 'RW'

        # Check modes
        if (self._mode != 'RW') and (self._mode != 'RO') and \
           (self._mode != 'WO'):
            raise VariableError(f'Invalid variable mode {self._mode}. Supported: RW, RO, WO')

        # Call super constructor
        pr.Node.__init__(self, name=name, description=description, hidden=hidden)

    @Pyro4.expose
    @property
    def enum(self):
        return self._enum

    @Pyro4.expose
    @property
    def revEnum(self):
        return self._revEnum

    @Pyro4.expose
    @property
    def typeStr(self):
        return self._typeStr

    @Pyro4.expose
    @property
    def disp(self):
        return self._disp

    @Pyro4.expose
    @property
    def mode(self):
        return self._mode

    @Pyro4.expose
    @property
    def units(self):
        return self._units

    @Pyro4.expose
    @property
    def minimum(self):
        return self._minimum

    @Pyro4.expose
    @property
    def maximum(self):
        return self._maximum

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

    @Pyro4.expose
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

    @Pyro4.expose
    def set(self, value, write=True):
        pass

    @Pyro4.expose
    def post(self,value):
        pass

    @Pyro4.expose
    def get(self,read=True):
        return None

    @Pyro4.expose
    def value(self):
        return self.get(read=False)

    @Pyro4.expose
    def linkUpdated(self, var, value, disp):
        self._updated()

    @Pyro4.expose
    def genDisp(self, value):
        #print('{}.genDisp(read={}) disp={} value={}'.format(self.path, read, self.disp, value))
        if self.disp == 'enum':
            #print('enum: {}'.format(self.enum))
            #print('get: {}'.format(self.get(read)))
            return self.enum[value]
        else:
            if value == '' or value is None:
                return value
            else:
                return self.disp.format(value)

    @Pyro4.expose
    def getDisp(self, read=True):
        return(self.genDisp(self.get(read)))

    @Pyro4.expose
    def valueDisp(self, read=True):
        return self.getDisp(read=False)

    @Pyro4.expose
    def parseDisp(self, sValue):
        if sValue is '':
            return ''
        elif self.disp == 'enum':
            return self.revEnum[sValue]
        else:
            t = self.nativeType()
            if t == int:
                return int(sValue, 0)
            elif t == float:
                return float(sValue)
            elif t == bool:
                return str.lower(sValue) == "true"
            else:
                return str
            #return (parse.parse(self.disp, sValue)[0])

    @Pyro4.expose
    def setDisp(self, sValue, write=True):
        if isinstance(sValue, self.nativeType()):
            self.set(sValue, write)
        else:
            self.set(self.parseDisp(sValue), write)

    @Pyro4.expose
    def nativeType(self):
        return type(self.value())

    def _rootAttached(self):
        # Variables are always leaf nodes so no need to recurse
        if self._default is not None:
            self.set(self._default, write=False)

        if self._pollInterval > 0 and self._root._pollQueue is not None:
            self._root._pollQueue.updatePollInterval(self)

    def _updated(self):
        """Variable has been updated. Inform listeners."""
        if self._update is False: return

        value = self.value()
        disp  = self.valueDisp()

        for func in self.__listeners:
            if getattr(func,'varListener',None) is not None:
                func.varListener(self,value,disp)
            else:
                func(self,value,disp)

        # Root variable update log
        self._root._varUpdated(self,value,disp)

    def __set__(self, value):
        self.set(value, write=True)

    def __get__(self):
        self.get(read=True)


@Pyro4.expose
class RemoteVariable(BaseVariable):

    def __init__(self, name=None, description="", 
                 base=pr.UInt, mode='RW', value=None,  disp=None,
                 enum=None, units=None, hidden=False, minimum=None, maximum=None,
                 offset=None, bitSize=32, bitOffset=0, pollInterval=0, 
                 verify=True, **dump):

        if disp is None:
            disp = base.defaultdisp

        BaseVariable.__init__(self, name=name, description=description, 
                              base=base, mode=mode, value=value, disp=disp,
                              enum=enum, units=units, hidden=hidden, minimum=minimum, maximum=maximum);

        self._pollInterval  = pollInterval

        self._base     = base        
        self._block    = None

        # Convert the address parameters into lists
        addrParams = [offset, bitOffset, bitSize] # Make a copy
        addrParams = [list(x) if isinstance(x, Iterable) else [x] for x in addrParams] # convert to lists
        length = max((len(x) for x in addrParams)) 
        addrParams = [x*length if len(x)==1 else x for x in addrParams] # Make single element lists as long as max
        offset, bitOffset, bitSize = addrParams # Assign back

        # Verify the the list lengths match
        if len(offset) != len(bitOffset) != len(bitSize):
            raise VariableError('Lengths of offset: {}, bitOffset: {}, bitSize {} must match'.format(offset, bitOffset, bitSize))        

        # Normalize bitOffsets relative to the smallest offset
        baseAddr = min(offset)
        bitOffset = [x+((y-baseAddr)*8) for x,y in zip(bitOffset, offset)]
        offset = baseAddr

        self._offset    = offset
        self._bitSize   = bitSize
        self._bitOffset = bitOffset
        self._verify    = verify
        self._typeStr   = base.name(sum(bitSize))
        self._bytes     = int(math.ceil(float(self._bitOffset[-1] + self._bitSize[-1]) / 8.0))


    @property
    def varBytes(self):
        return self._bytes

    @Pyro4.expose
    @property
    def offset(self):
        return self._offset

    @Pyro4.expose
    @property
    def bitSize(self):
        return self._bitSize

    @Pyro4.expose
    @property
    def bitOffset(self):
        return self._bitOffset

    @Pyro4.expose
    @property
    def verify(self):
        return self._verify

    @Pyro4.expose
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
                self._parent.writeBlocks(force=False, recurse=False, variable=self)
                self._parent.checkBlocks(varUpdate=False, recurse=False, variable=self)

                if self._block.mode == 'RW':
                    self._parent.verifyBlocks(recurse=False, variable=self)
                    self._parent.checkBlocks(varUpdate=False, recurse=False, variable=self)

        except Exception as e:
            self._log.error(e)

    @Pyro4.expose
    def post(self,value):
        """
        Set the value and write to hardware if applicable using a posted write.
        This method does not call through parent.writeBlocks(), but rather
        calls on self._block directly.
        """
        self._log.debug("{}.post({})".format(self, value))
        
        try:
            self._block.set(self, value)
            self._updated()

            if self._block.mode != 'RO':
                self._block.backgroundTransaction(rogue.interfaces.memory.Post)

        except Exception as e:
            self._log.error(e)

    @Pyro4.expose
    def get(self,read=True):
        """ 
        Return the value after performing a read from hardware if applicable.
        Hardware read is blocking. An error will result in a logged exception.
        Listeners will be informed of the update.
        """
        try:
            if read and self._block.mode != 'WO':
                self._parent.readBlocks(recurse=False, variable=self)
                self._parent.checkBlocks(varUpdate=True, recurse=False, variable=self)

            ret = self._block.get(self)

        except Exception as e:
            self._log.error(e)
            return None

        # Update listeners for all variables in the block
        if read:
            self._block._updated()

        return ret

    @Pyro4.expose
    def parseDisp(self, sValue):
        #print("Parsing var {}, value= {}".format(self.name, sValue))
        if self.disp == 'enum':
            return self.revEnum[sValue]
        else:
            #print(self._base.fromString(sValue))
            return self._base.fromString(sValue)

    def _shiftOffsetDown(self,amount,minSize):
        if amount != 0:

            self._log.debug("Adjusting variable {} offset from 0x{:02x} to 0x{:02x}".format(self.name,self._offset,self._offset-amount))
            #print("Adjusting variable {} offset from 0x{:02x} to 0x{:02x}".format(self.name,self._offset,self._offset-amount))

            self._offset -= amount

            for i in range(0,len(self._bitOffset)):
                self._bitOffset[i] += (amount * 8)

        self._bytes = int(math.ceil(float(self._bitOffset[-1] + self._bitSize[-1]) / float(minSize*8))) * minSize



class LocalVariable(BaseVariable):

    def __init__(self, name=None, description="", 
                 mode='RW', value=None, disp='{}',
                 enum=None, units=None, hidden=False, minimum=None, maximum=None,
                 localSet=None, localGet=None, pollInterval=0, **dump):

        if value is None:
            raise VariableError(f'LocalVariable {self.path} must specify value= argument in constructor')

        BaseVariable.__init__(self, name=name, description=description, 
                              mode=mode, value=value, disp=disp,
                              enum=enum, units=units, hidden=hidden,
                              minimum=minimum, maximum=maximum)

        self._pollInterval = pollInterval
        self._block = pr.LocalBlock(self,localSet,localGet,self._default)

        
    @Pyro4.expose
    def set(self, value, write=True):
        try:
            self._block.set(self, value)

        except Exception as e:
            self._log.error(e)

        if write: self._updated()

    def __set__(self, value):
        self.set(value, write=False)

    @Pyro4.expose
    def get(self,read=True):
        try:
            ret = self._block.get(self)

        except Exception as e:
            self._log.error(e)
            return None

        if read: self._updated()
        return ret

    def __get__(self):
        return self.get(read=False)

@Pyro4.expose
class LinkVariable(BaseVariable):

    def __init__(self, name=None, description="", 
                 mode='RW', disp='{}', typeStr='Linked',
                 enum=None, units=None, hidden=False, minimum=None, maximum=None,
                 linkedSet=None, linkedGet=None, dependencies=None, **dump):

        BaseVariable.__init__(self, name=name, description=description, 
                              mode=mode, disp=disp,
                              enum=enum, units=units, hidden=hidden,
                              minimum=minimum, maximum=maximum)

        self._typeStr = typeStr

        # Set and get functions
        self._linkedGet = linkedGet
        self._linkedSet = linkedSet


        # Dependency tracking
        if dependencies is not None:
            for d in dependencies:
                self.addDependency(d)

    def __getitem__(self, key):
        # Allow dependencies to be accessed as indicies of self
        return self.dependencies[key]

    @Pyro4.expose
    def set(self, value, write=True):
        """
        The user can use the linkedSet attribute to pass a string containing python commands or
        a specific method to call. When using a python string the code will find the passed value
        as the variable 'value'. A passed method will accept the variable object and value as args.
        Listeners will be informed of the update.
        """
        if self._linkedSet is not None:
            if callable(self._linkedSet):
                self._linkedSet(self._parent,self,value,write)
            else:
                dev = self._parent
                var = self
                exec(textwrap.dedent(self._linkedSet))

    @Pyro4.expose
    def get(self, read=True):
        """
        The user can use the linkedGet attribute to pass a string containing python commands or
        a specific method to call. When using a python string the code will set the 'value' variable
        with the value to return. A passed method will accept the variable as an arg and return the
        resulting value.
        """
        if self._linkedGet is not None:
            if callable(self._linkedGet):
                return(self._linkedGet(self._parent,self,read))
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
        ret = LocalVariable(localSet=setFunction, localGet=getFunction, **kwargs)
        ret._depWarn = True
        return(ret)

    # Otherwise assume remote
    else:
        if 'base' not in kwargs:
            kwargs['base'] = pr.UInt
            
        base = kwargs['base']

        if isinstance(base, str):
            if base == 'hex' or base == 'uint' or base == 'bin' or base == 'enum' or base == 'range':
                kwargs['base'] = pr.UInt
            elif base == 'int':
                kwargs['base'] = pr.Int
            elif base == 'bool':
                kwargs['base'] = pr.Bool
            elif base == 'string':
                kwargs['base'] = pr.String
            elif base == 'float':
                kwargs['base'] = pr.Float


        if 'disp' not in kwargs and isinstance(base, str):
            if base == 'uint':
                kwargs['disp'] = '{:d}'
            elif base == 'bin':
                kwargs['disp'] = '{:#b}'
#             else:
#                 kwargs['disp'] = kwargs['base'].defaultdisp     # or None?       

        ret = RemoteVariable(**kwargs)
        ret._depWarn = True
        return(ret)

