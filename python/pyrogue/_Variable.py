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
import inspect
import threading
from collections import Iterable

class VariableError(Exception):
    """ Exception for variable access errors."""
    pass

class BaseVariable(pr.Node):

    def __init__(self, *,
                 name,
                 description='',
                 mode='RW',
                 value=None,
                 disp='{}',
                 enum=None,
                 units=None,
                 hidden=False,
                 minimum=None,
                 maximum=None,
                 pollInterval=0
                ):

        # Public Attributes
        self._mode          = mode
        self._units         = units
        self._minimum       = minimum # For base='range'
        self._maximum       = maximum # For base='range'
        self._default       = value
        self._block         = None
        self._pollInterval  = pollInterval
        self.__listeners    = []
        self.__functions    = []
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

        # Determine typeStr from value type
        if value is not None:
            if isinstance(value, list):
                self._typeStr = f'List[{value[0].__class__.__name__}]'
            else:
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
        if dep not in self.__dependencies:
            self.__dependencies.append(dep)
            dep.addListener(self)

    @property
    def pollInterval(self):
        return self._pollInterval

    @pollInterval.setter
    def pollInterval(self, interval):
        self._pollInterval = interval
        self._updatePollInterval()

    @property
    def dependencies(self):
        return self.__dependencies

    def addListener(self, listener):
        """
        Add a listener Variable or function to call when variable changes. 
        This is usefull when chaining variables together. (adc conversions, etc)
        The variable, value and display string will be passed as an arg: func(path,value,disp)
        """
        if isinstance(listener, BaseVariable):
            self.__listeners.append(listener)
        else:
            self.__functions.append(listener)

    @Pyro4.expose
    def set(self, value, write=True):
        """
        Set the value and write to hardware if applicable
        Writes to hardware are blocking. An error will result in a logged exception.
        """
        self._log.debug("{}.set({})".format(self, value))
        try:
            if self._block is not None:
                self._block.set(self, value)

                if write:
                    self._parent.writeBlocks(force=False, recurse=False, variable=self)
                    self._parent.verifyBlocks(recurse=False, variable=self)
                    self._parent.checkBlocks(recurse=False, variable=self)

        except Exception as e:
            self._log.exception(e)
            self._log.error("Error setting value '{}' to variable '{}' with type {}".format(value,self.path,self.typeStr))

    @Pyro4.expose
    def post(self,value):
        """
        Set the value and write to hardware if applicable using a posted write.
        This method does not call through parent.writeBlocks(), but rather
        calls on self._block directly.
        """
        self._log.debug("{}.post({})".format(self, value))

        try:
            if self._block is not None:
                self._block.set(self, value)
                self._block.startTransaction(rogue.interfaces.memory.Post, check=True)

        except Exception as e:
            self._log.exception(e)
            self._log.error("Error posting value '{}' to variable '{}' with type {}".format(value,self.path,self.typeStr))

    @Pyro4.expose
    def get(self,read=True):
        """ 
        Return the value after performing a read from hardware if applicable.
        Hardware read is blocking. An error will result in a logged exception.
        Listeners will be informed of the update.
        """
        try:
            if self._block is not None:
                if read:
                    self._parent.readBlocks(recurse=False, variable=self)
                    self._parent.checkBlocks(recurse=False, variable=self)

                ret = self._block.get(self)
            else:
                ret = None

        except Exception as e:
            self._log.exception(e)
            self._log.error("Error reading value from variable '{}'".format(self.path))
            ret = None

        return ret

    @Pyro4.expose
    def value(self):
        return self.get(read=False)

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
        if sValue is None or isinstance(sValue, self.nativeType()):
            return sValue
        else:        
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
                elif t == list or t == dict:
                    return eval(sValue)
                else:
                    return sValue

    @Pyro4.expose
    def setDisp(self, sValue, write=True):
        self.set(self.parseDisp(sValue), write)

    @Pyro4.expose
    def nativeType(self):
        return type(self.value())

    def _setDefault(self):
        # Called by parent Device after _buildBlocks()
        if self._default is not None:
            self.setDisp(self._default, write=False)

    def _updatePollInterval(self):
        if self._pollInterval > 0 and self.root._pollQueue is not None:
            self.root._pollQueue.updatePollInterval(self)

    def _finishInit(self):
        self._setDefault()
        self._updatePollInterval()


    #def __set__(self, value):
        #self.set(value, write=True)

    #def __get__(self):
        #self.get(read=True)

    def _setDict(self,d,writeEach,modes):
        if self._mode in modes:
            self.setDisp(d,writeEach)

    def _getDict(self,modes):
        if self._mode in modes:
            return self.valueDisp()
        else:
            return None

    def _queueUpdate(self):
        self._root._queueUpdates(self)

        for var in self.__listeners:
            var._queueUpdate()

    def _doUpdate(self):
        value = self.value()
        disp  = self.valueDisp()

        for func in self.__functions:
            if hasattr(func,'varListener'):
                func.varListener(self.path,value,disp)
            else:
                func(self.path,value,disp)

        return self.path,value,disp


@Pyro4.expose
class RemoteVariable(BaseVariable):

    def __init__(self, *,
                 name,
                 description='',
                 mode='RW',
                 value=None,
                 disp=None,
                 enum=None,
                 units=None,
                 hidden=False,
                 minimum=None,
                 maximum=None,
                 base=pr.UInt,                                 
                 offset=None,
                 bitSize=32,
                 bitOffset=0,
                 pollInterval=0, 
                 verify=True, ):

        if disp is None:
            disp = base.defaultdisp

        BaseVariable.__init__(self, name=name, description=description, 
                              mode=mode, value=value, disp=disp, 
                              enum=enum, units=units, hidden=hidden,
                              minimum=minimum, maximum=maximum,
                              pollInterval=pollInterval)

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
    @property
    def base(self):
        return self._base

    @Pyro4.expose
    def parseDisp(self, sValue):
        if sValue is None or isinstance(sValue, self.nativeType()):
            return sValue
        else:        

            if self.disp == 'enum':
                return self.revEnum[sValue]
            else:
                return self._base.fromString(sValue, sum(self._bitSize))
            
    def _setDefault(self):
        if self._default is not None:
            self._block._setDefault(self, self.parseDisp(self._default))

    def _shiftOffsetDown(self,amount,minSize):
        if amount != 0:

            self._log.debug("Adjusting variable {} offset from 0x{:02x} to 0x{:02x}".format(self.name,self._offset,self._offset-amount))
            #print("Adjusting variable {} offset from 0x{:02x} to 0x{:02x}".format(self.name,self._offset,self._offset-amount))

            self._offset -= amount

            for i in range(0,len(self._bitOffset)):
                self._bitOffset[i] += (amount * 8)

        self._bytes = int(math.ceil(float(self._bitOffset[-1] + self._bitSize[-1]) / float(minSize*8))) * minSize



class LocalVariable(BaseVariable):

    def __init__(self, *,
                 name,
                 description='',
                 mode='RW',
                 value=None,
                 disp='{}',
                 enum=None,
                 units=None,
                 hidden=False,
                 minimum=None,
                 maximum=None,
                 localSet=None,
                 localGet=None,
                 pollInterval=0):

        if value is None:
            raise VariableError(f'LocalVariable {self.path} must specify value= argument in constructor')

        BaseVariable.__init__(self, name=name, description=description, 
                              mode=mode, value=value, disp=disp, 
                              enum=enum, units=units, hidden=hidden,
                              minimum=minimum, maximum=maximum,
                              pollInterval=pollInterval)

        self._block = pr.LocalBlock(variable=self,localSet=localSet,localGet=localGet,value=self._default)

    def __get__(self):
        return self.get(read=False)

@Pyro4.expose
class LinkVariable(BaseVariable):

    def __init__(self, *,
                 name,
                 variable=None,
                 dependencies=None,
                 typeStr='Linked',
                 linkedSet=None,
                 linkedGet=None,
                 **kwargs): # Args passed to BaseVariable
        
        # Set and get functions
        self._linkedGet = linkedGet
        self._linkedSet = linkedSet        

        if variable is not None:
            # If directly linked to a variable, use it's value and set by defualt
            # for linkedGet and linkedSet unless overridden
            self._linkedGet = linkedGet if linkedGet else variable.value
            self._linkedSet = linkedSet if linkedSet else variable.set

            
            # Search the kwargs for overridden properties, otherwise the properties from the linked variable will be used
            args = ['disp', 'enum', 'units', 'minimum', 'maximum']
            for arg in args:
                if arg not in kwargs:
                    kwargs[arg] = getattr(variable, arg)

        # Call super constructor
        BaseVariable.__init__(self, name=name, **kwargs)

        # Must be done after super cunstructor to override it
        self._typeStr = typeStr        

        # Dependency tracking
        if variable is not None:
            # Add the directly linked variable as a dependency
            self.addDependency(variable)

        if dependencies is not None:
            for d in dependencies:
                self.addDependency(d)

    def __getitem__(self, key):
        # Allow dependencies to be accessed as indicies of self
        return self.dependencies[key]

    @Pyro4.expose
    def set(self, value, write=True):
        if self._linkedSet is not None:

            # Possible args
            pargs = {'dev' : self.parent, 'var' : self, 'value' : value, 'write' : write}

            varFuncHelper(self._linkedSet,pargs,self._log,self.path)

    @Pyro4.expose
    def get(self, read=True):
        if self._linkedGet is not None:

            # Possible args
            pargs = {'dev' : self.parent, 'var' : self, 'read' : read}

            return varFuncHelper(self._linkedGet,pargs,self._log,self.path)
        else:
            return None


# Legacy Support
def Variable(local=False, setFunction=None, getFunction=None, **kwargs):
        
    # Local Variables override get and set functions
    if local or setFunction is not None or getFunction is not None:

        # Get list of possible class args
        cargs = inspect.getfullargspec(LocalVariable.__init__).args + \
                inspect.getfullargspec(LocalVariable.__init__).kwonlyargs

        # Pass supported args
        args = {k:kwargs[k] for k in kwargs if k in cargs}

        ret = LocalVariable(localSet=setFunction, localGet=getFunction, **args)
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

        # Get list of possible class args
        cargs = inspect.getfullargspec(RemoteVariable.__init__).args + \
                inspect.getfullargspec(RemoteVariable.__init__).kwonlyargs

        # Pass supported args
        args = {k:kwargs[k] for k in kwargs if k in cargs}

        ret = RemoteVariable(**args)
        ret._depWarn = True
        return(ret)


# Function helper
def varFuncHelper(func,pargs,log,path):

    if not callable(func):
        log.warning("Using deprecated eval string. Please change to function: {}".format(path))

        dev   = None
        var   = None
        cmd   = None
        arg   = None
        value = 0

        if 'dev' in pargs:
            dev = pargs['dev']

        if 'var' in pargs:
            var = pargs['var']

        if 'cmd' in pargs:
            cmd = pargs['cmd']

        if 'arg' in pargs:
            arg = pargs['arg']

        ns = locals()
        exec(textwrap.dedent(func),ns)
        value = ns['value']
        return value

    else:

        # Python functions
        try:
            # Function args
            fargs = inspect.getfullargspec(func).args + \
                    inspect.getfullargspec(func).kwonlyargs 

            # Build overlapping arg list
            args = {k:pargs[k] for k in fargs if k is not 'self' and k in pargs}

        # handle c++ functions, no args supported for now
        except:
            args = {}

        return func(**args)

