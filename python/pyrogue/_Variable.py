import pyrogue as pr
import textwrap

class VariableError(Exception):
    """ Exception for variable access errors."""
    pass


class Variable(pr.Node):
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
    mode: Access mode of the variable
          RW = Read/Write
          RO = Read Only
          WO = Write Only
          SL = A slave variable which is not included in block writes or config/status dumps.
    enum: A dictionary of index:value pairs ie {0:'Zero':0,'One'} for disp='enum'
    minimum: Minimum value for disp='range'
    maximum: Maximum value for disp='range'
    hidden: Variable is hidden
    """
    def __init__(self, name=None, description="", parent=None, classType='variable',
                 offset=None, bitSize=32, bitOffset=0, pollInterval=0, mode='RW', verify=True,
                 value=None, local=False, getFunction=None, setFunction=None,
                 base='hex',
                 disp=None, enum=None, units=None, hidden=False, minimum=None, maximum=None,
                 dependencies=None,
                 beforeReadCmd=lambda: None, afterWriteCmd=lambda: None,
                 **dump):
        """Initialize variable class""" 

        # Public Attributes
        self.offset    = offset
        self.bitSize   = bitSize
        self.bitOffset = bitOffset
        self.mode      = mode
        self.verify    = verify
        self.enum      = enum
        self.units     = units
        self.minimum   = minimum # For base='range'
        self.maximum   = maximum # For base='range'
        self.value     = value  
        
        #print('Variable.__init__( name={}, base={}, disp={}, model={} )'.format(name, base, disp, model))        


        self.base = base
        # Handle legacy model declarations
        if base == 'hex' or base == 'uint' or base == 'bin' or base == 'enum' or base == 'range':
            self.base = pr.IntModel(numBits=bitSize, signed=False, endianness='little')
        elif base == 'int':
            self.base = pr.IntModel(numBits=bitSize, signed=True, endianness='little')
        elif base == 'bool':
            self.base = pr.BoolModel()
        elif base == 'string':
            self.base = pr.StringModel()
        elif base == 'float':
            self.base = pr.FloatModel()

        # disp follows base if not specified
        if disp is None and isinstance(base, str):
            disp = base
        elif disp is None:
            disp = self.base.defaultdisp
            
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

        self.typeStr = str(self.base)

        self.revEnum = None
        if self.enum is not None:
            self.revEnum = {v:k for k,v in self.enum.items()}

        self._pollInterval = pollInterval

        # Check modes
        if (self.mode != 'RW') and (self.mode != 'RO') and \
           (self.mode != 'WO') and (self.mode != 'SL') and \
           (self.mode != 'CMD'):
            raise VariableError('Invalid variable mode %s. Supported: RW, RO, WO, SL, CMD' % (self.mode))

        #Tracking variables
        self._block = None
        self.__listeners  = []

        # Local Variables override get and set functions
        self.__local = local or setFunction is not None or getFunction is not None
        self._setFunction = setFunction
        self._getFunction = getFunction
        if self.__local == True:
            if setFunction is None:
                self._setFunction = self._localSetFunction
            if getFunction is None:
                self._getFunction = self._localGetFunction


        if isinstance(self.base, pr.StringModel):
            self._scratch = ''
        else:
            self._scratch = 0

        # Dependency tracking
        self.__dependencies = []
        if dependencies is not None:
            for d in dependencies:
                self.addDependency(d)

        # These run before or after block access
        self._beforeReadCmd = beforeReadCmd
        self._afterWriteCmd = afterWriteCmd

        # Call super constructor
        pr.Node.__init__(self, name=name, classType=classType, description=description, hidden=hidden, parent=parent)

    def _rootAttached(self):
        # Variables are always leaf nodes so no need to recurse
        if self.value is not None:
            self.set(self.value, write=False)

        if self._pollInterval > 0 and self._root._pollQueue is not None:
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

    @staticmethod
    def _localGetFunction(dev, var):
        return var.value

    @staticmethod
    def _localSetFunction(dev, var, val):
        var.value = val

    def set(self, value, write=True):
        """
        Set the value and write to hardware if applicable
        Writes to hardware are blocking. An error will result in a logged exception.
        """

        self._log.debug("{}.set({})".format(self, value))
        try:
            self._rawSet(value)
            
            if write and self._block is not None and self._block.mode != 'RO':
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
            if read and not self.__local and self._block.mode != 'WO':
                self._beforeReadCmd()
                self._block.blockingTransaction(rogue.interfaces.memory.Read)

            ret = self._rawGet()
            
        except Exception as e:
            self._log.error(e)
            return None

        # Update listeners for all variables in the block
        if read:
            if self._block is not None:
                self._block._updated()
            else:
                self._updated()
                
        return ret

    def _updated(self):
        """Variable has been updated. Inform listeners."""
        
        # Don't generate updates for SL and WO variables
        if self.mode == 'WO' or self.mode == 'SL': return

        if self._block is not None:
            self.value = self._block.get(self)
        
        for func in self.__listeners:
            func(self, self.value)

        # Root variable update log
        self._root._varUpdated(self,self.value)    

    def _rawSet(self, value):
        # If a setFunction exists, call it (Used by local variables)        
        if self._setFunction is not None:
            if callable(self._setFunction):
                self._setFunction(self._parent, self, value)
            else:
                dev = self._parent
                exec(textwrap.dedent(self._setFunction))
                
        elif self._block is not None:
            # No setFunction, write to the block
            self._block.set(self, value)

        # Inform listeners
        self._updated()

    def _rawGet(self):
        if self._getFunction is not None:
            if callable(self._getFunction):
                return(self._getFunction(self._parent,self))
            else:
                dev = self._parent
                value = 0
                ns = locals()
                exec(textwrap.dedent(self._getFunction),ns)
                return ns['value']

        elif self._block is not None:        
            return self._block.get(self)
        else:
            return None

    # Not sure if we really want these        
    def __set__(self, value):
        self.set(value, write=True)

    def __get__(self):
        self.get(read=True)

 

    def linkUpdated(self, var, value):
        self._updated()

    def getDisp(self, read=True):
        
        if self.disp == 'enum':
            print('{}.getDisp(read={}) disp={} value={}'.format(self.path, read, self.disp, self.value))            
            print('enum: {}'.format(self.enum))
            print('get: {}'.format(self.get(read)))
            return self.enum[self.get(read)]
        else:
            return self.disp.format(self.get(read))

    def parseDisp(self, sValue):
        if self.disp == 'enum':
            return self.revEnum[sValue]
        else:
            #return (parse.parse(self.disp, sValue)[0])
            return self.base._fromString(sValue)
        
    def setDisp(self, sValue, write=True):
        self.set(self.parseDisp(sValue), write)
        
        

