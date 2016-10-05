#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Title      : PyRogue base module
#-----------------------------------------------------------------------------
# File       : pyrogue/__init__.py
# Author     : Ryan Herbst, rherbst@slac.stanford.edu
# Created    : 2016-09-29
# Last update: 2016-09-29
#-----------------------------------------------------------------------------
# Description:
# Module containing the top functions and classes within the pyrouge library
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
import yaml
import threading
import time
import collections
import datetime

def streamConnect(source, dest):
    """Connect source and destination stream devices"""

    # Is object a native master or wrapped?
    if isinstance(source,rogue.interfaces.stream.Master):
        master = source
    else:
        master = source._getStreamMaster()

    # Is object a native slave or wrapped?
    if isinstance(dest,rogue.interfaces.stream.Slave):
        slave = dest
    else:
        slave = dest._getStreamSlave()

    master._setSlave(slave)


def streamTap(source, tap):
    """Add a stream tap"""

    # Is object a native master or wrapped?
    if isinstance(source,rogue.interfaces.stream.Master):
        master = source
    else:
        master = source._getStreamMaster()

    # Is object a native slave or wrapped?
    if isinstance(tap,rogue.interfaces.stream.Slave):
        slave = tap
    else:
        slave = tap._getStreamSlave()

    master._addSlave(slave)


def streamConnectBiDir(deviceA, deviceB):
    """Connect two endpoints of a bi-directional stream"""

    streamConnect(deviceA,deviceB)
    streamConnect(deviceB,deviceA)


def busConnect(source,dest):
    """Connector a memory bus client and server"""

    # Is object a native master or wrapped?
    if isinstance(source,rogue.interfaces.stream.Master):
        master = source
    else:
        master = source._getMemoryMaster()

    # Is object a native slave or wrapped?
    if isinstance(dest,rogue.interfaces.stream.Slave):
        slave = dest
    else:
        slave = dest._getMemorySlave()

    master._setSlave(slave)


class VariableError(Exception):
    pass


class NodeError(Exception):
    pass


class Poller(threading.Thread):
    def __init__(self,root):
        threading.Thread.__init__(self)
        self.period = 0
        self.root = root

    def run(self):
        while(self.period != None):
            if self.period != 0:
                time.sleep(self.period)
                self.root.readPollable()
            else:
                time.sleep(1)


class Root(rogue.interfaces.stream.Master):
    """System base"""

    def __init__(self,name):
        rogue.interfaces.stream.Master.__init__(self)

        self.name = name
        self._poller = Poller(self)
        self._systemLog = ""
        self._nodes = collections.OrderedDict()

        # Config write command exposed to higher level
        Command(parent=self, name='writeConfig',description='Write Configuration', base='string',
           function=self._writeYamlConfig)

        # Config read command exposed to higher level
        Command(parent=self, name='readConfig',description='Read Configuration', base='string',
           function=self._readYamlConfig)

        # Soft reset
        Command(parent=self, name='softReset',description='Soft Reset',
           function=self._softReset)

        # Hard reset
        Command(parent=self, name='hardReset',description='Hard Reset',
           function=self._hardReset)

        # Count reset
        Command(parent=self, name='countReset',description='Count Reset',
           function=self._hardReset)

        # Clear log window
        Command(parent=self, name='clearLog',description='Clear Log',
           function=self._clearLog)

        # System log variable
        Variable(parent=self, name='systemLog', description='System Log', base='string', mode='RO', hidden=True,
                 setFunction=None, getFunction='value=self._parent._systemLog')

        # Polling period variable
        Variable(parent=self, name='pollPeriod', description='Polling Period', base='float', mode='RW', 
                 setFunction='self._parent._poller.period=value', 
                 getFunction='value=self._parent._poller.period')
        
        self._poller.start()

    def stop(self):
        self._poller.period=None

    def streamConfig(self):
        """Push confiuration string out on a stream"""
        s = self.getYamlConfig()
        f = self._reqFrame(len(s),True,0)
        b = bytearray()
        b.extend(s)
        f.write(b,0)
        self._sendFrame(f)

    def getStructure(self):
        """Get structure as a dictionary"""
        return {self.name:_getStructure(self)}

    def getYamlStructure(self):
        """Get structure as a yaml string"""
        return yaml.dump(self.getStructure(),default_flow_style=False)

    def getConfig(self):
        """Get configuration as a dictionary"""
        self.readAll()
        return {self.name:_getConfig(self)}

    def getYamlConfig(self):
        """Get configuration as a yaml string"""
        return yaml.dump(self.getConfig(),default_flow_style=False)

    def setConfig(self,d):
        """Set configuration from a dictionary"""
        for key, value in d.iteritems():
            if key == self.name:
                _setConfig(self,value)
        self.writeAll()

    def setYamlConfig(self,yml):
        """Set configuration from a yaml string"""
        d = yaml.load(yml)
        self.setConfig(d)

    def writeAll(self):
        """Write all blocks"""
        try:
            _writeAll(self)
            _checkUpdatedBlocks(self)
        except Exception as e:
            self._logException(e)

    def writeStale(self):
        """Write stale blocks"""
        try:
            _writeStale(self)
            _checkUpdatedBlocks(self)
        except Exception as e:
            self._logException(e)

    def readAll(self):
        """Read all blocks"""
        try:
            _readAll(self)
            _checkUpdatedBlocks(self)
        except Exception as e:
            self._logException(e)

    def readPollable(self):
        """Read pollable blocks"""
        try:
            _readPollable(self)
            _checkUpdatedBlocks(self)
        except Exception as e:
            self._logException(e)

    def verify(self):
        """Verify read/write blocks"""
        try:
            pass
        except Exception as e:
            self._logException(e)

    def getAtPath(self,path):
        """Get dictionary entry at path"""

        if not '.' in path:
            if path == self.name: 
                return self
            else:
                return None
        else:
            base = path[:path.find('.')]
            rest = path[path.find('.')+1:]

            if base == self.name:
                return(_getAtPath(self,rest))
            else:
                return None

    def _writeYamlConfig(self,cmd,arg):
        """Write YAML configuration to a file. Called from command"""
        with open(arg,'w') as f:
            f.write(self.getYamlConfig())

    def _readYamlConfig(self,cmd,arg):
        """Read YAML configuration from a file. Called from command"""
        with open(arg,'r') as f:
            self.setYamlConfig(f.read())

    def _softReset(self,cmd,arg):
       _softReset(self)

    def _hardReset(self,cmd,arg):
       _hardReset(self)

    def _countReset(self,cmd,arg):
       _countReset(self)

    def _clearLog(self,cmd,arg):
        self._systemLog = ""
        self.systemLog._updated()

    def _logException(self,ex):
        self._addToLog(str(ex))

    def _addToLog(self,string):
        self._systemLog += string
        self._systemLog += '\n'
        self.systemLog._updated()


class Node(object):
    """Common system node"""

    def __init__(self, parent, name, description, hidden, classType):

        # Public attributes
        self.name        = name     
        self.description = description
        self.hidden      = hidden
        self.classType   = classType

        # Tracking
        self._parent = parent
        self._nodes = collections.OrderedDict()

        if isinstance(parent,Node):
            self._root = parent._root
            self.path  = parent.path + '.' + self.name
        else:
            self._root = parent
            self.path  = parent.name + '.' + self.name

        # Add to parent list
        if hasattr(self._parent,self.name):
            raise NodeError('Invalid %s name %s. Name already exists' % (self.classType,self.name))
        else:
            setattr(self._parent,self.name,self)
            self._parent._nodes[self.name] = self


class Variable(Node):
    """Variable holder"""

    def __init__(self, parent, name, description, bitSize=32, bitOffset=0, 
                 base='hex', mode='RW', enum=None, hidden=False, minimum=None, maximum=None,
                 setFunction=None, getFunction=None):
        """Initialize variable class"""
        # Currently supported bases:
        #    uint, hex, enum, bool, range, string, float
        # Enums are in the form:
        #   idx : value

        Node.__init__(self,parent,name,description,hidden,'variable')

        # Public Attributes
        self.bitSize   = bitSize
        self.bitOffset = bitOffset
        self.base      = base      
        self.mode      = mode
        self.enum      = enum
        self.hidden    = hidden
        self.minimum   = minimum # For base='range'
        self.maximum   = maximum # For base='range'

        # Check modes
        if (self.mode != 'RW') and (self.mode != 'RO') and (self.mode != 'WO') and (self.mode != 'CMD'):
            raise VariableError('Invalid variable mode %s. Supported: RW, RO, WO, CMD' % (self.mode))

        # Tracking variables
        self._block       = None
        self._setFunction = setFunction
        self._getFunction = getFunction
        self.__listeners  = []

    def _intSet(self,value):
        if self._setFunction != None:
            if callable(self._setFunction):
                self._setFunction(self,value)
            else:
                exec(textwrap.dedent(self._setFunction))

        elif self._block:        
            if self.base == 'string':
                self._block.setString(value)
            elif self.base == 'bool':
                if value: val = 1
                else: val = 0
                self._block.setUInt(self.bitOffset,self.bitSize,val)
            elif self.base == 'enum':
                val = {value: key for key,value in self.enum.iteritems()}[value]
                self._block.setUInt(self.bitOffset,self.bitSize,val)
            else:
                self._block.setUInt(self.bitOffset,self.bitSize,value)

        self._updated()
                
    def _intGet(self):
        if self._getFunction != None:
            if callable(self._getFunction):
                return(self._getFunction(self))
            else:
                value = None
                exec(textwrap.dedent(self._getFunction))
                return value

        elif self._block:        
            if self.base == 'string':
                return(self._block.getString())
            elif self.base == 'bool':
                return(self._block.getUInt(self.bitOffset,self.bitSize) != 0)
            elif self.base == 'enum':
                return self.enum[self._block.getUInt(self.bitOffset,self.bitSize)]
            else:
                return(self._block.getUInt(self.bitOffset,self.bitSize))
        else:
            return None

    def _addListener(self, dest):
        """Add a listner for variable changes. Function newValue will be called"""
        self.__listeners.append(dest)

    def _updated(self):
        """Update liteners with new value"""
        for l in self.__listeners:
            l.newValue(self)

    def set(self,value):
        """Set a value without writing to hardware"""
        try:
            self._intSet(value)
        except Exception as e:
            self._root._logException(e)

    def write(self,value):
        """Set a value with write to hardware"""
        try:
            self._intSet(value)
            if self._block and self._block.mode != 'RO':
                self._block.blockingWrite()
        except Exception as e:
            self._root._logException(e)

    def writePosted(self,value):
        """Set a value with posted write to hardware"""
        try:
            self._intSet(value)
            if self._block and self._block.mode != 'RO':
                self._block.postedWrite()
        except Exception as e:
            self._root._logException(e)

    def get(self):
        """Get a value from shadow memory"""
        try:
            return self._intGet()
        except Exception as e:
            self._root._logException(e)

    def read(self):
        """Get a value after read from hardware"""
        try:
            if self._block and self._block.mode != 'WO':
                self._block.blockingRead()
                self._updated()
            return self._intGet()
        except Exception as e:
            self._root._logException(e)


class Command(Node):
    """Command holder"""

    def __init__(self, parent, name, description, base='None', function=None, hidden=False):
        """Initialize command class"""

        Node.__init__(self,parent,name,description,hidden,'command')

        # Currently supported bases:
        #    uint, hex, string, float

        # Public attributes
        self.hidden = hidden
        self.base   = base

        # Tracking
        self._function = function

    def __call__(self,arg=None):
        """Execute command"""
        try:
            if self._function != None:

                # Function is really a function
                if callable(self._function):
                    self._function(self,arg)

                # Function is a CPSW sequence
                elif type(self._function) is collections.OrderedDict:
                    for key,value in self._function.iteritems():

                        # Built in
                        if key == 'usleep':
                            time.sleep(value/1e6)

                        # Determine if it is a command or variable
                        else:
                            n = self._parent._nodes[key]

                            if callable(n): 
                                n(value)
                            else: 
                                n.write(value)

                # Attempt to execute string as a python script
                else:
                    exec(textwrap.dedent(self._function))

        except Exception as e:
            self._root._logException(e)


class Block(rogue.interfaces.memory.Block):
    """Memory block holder"""

    def __init__(self,parent,offset,size,variables,pollEn=False):
        """Initialize memory block class"""
        rogue.interfaces.memory.Block.__init__(self,offset,size)

        self.variables = variables
        self.pollEn    = pollEn
        self.mode      = 'RO'

        # Add to device tracking list
        parent._blocks.append(self)

        # Update position in memory map
        self._inheritFrom(parent)

        for variable in variables:
            variable._block = self

            # Determine block mode based upon variables
            # mismatch assumes block is read/write
            if self.mode == '':
                self.mode = variable.mode
            elif self.mode != variable.mode:
                self.mode = 'RW'

    # Generate variable updates if block has been updated
    def _checkUpdated(self):
        if self.getUpdated():
            for variable in self.variables:
                variable._updated()


class Device(Node,rogue.interfaces.memory.Master):
    """Device class holder"""

    def __init__(self, parent, name, description, size, memBase=None, offset=0, hidden=False):
        """Initialize device class"""

        Node.__init__(self,parent,name,description,hidden,'device')
        rogue.interfaces.memory.Master.__init__(self,offset,size)

        # Blocks
        self._blocks = []
        self._enable = True

        # Adjust position in tree
        if memBase:
            self._setMemBase(memBase,offset)
        elif isinstance(self._parent,rogue.interfaces.memory.Master):
            self._inheritFrom(self._parent)

        # Variable interface to enable flag
        Variable(parent=self, name='enable', description='Enable Flag', base='bool', mode='RW', 
                 setFunction=self._setEnable, getFunction='value = self._parent._enable')

    def _setEnable(self, var, enable):
        self._enable = enable

        for block in self._blocks:
            block.setEnable(enable)

    def _setMemBase(self,memBase,offset=None):
        """Connect to memory slave at offset"""
        if offset: self._setAddress(offset)

        # Membase is a Device
        if isinstance(memBase,Device):
            # Inhertit base address and slave pointer from one level up
            self._inheritFrom(memBase)

        # Direct connection to slae
        else:
            self._setSlave(memBase)

        # Adust address map in blocks
        for block in self._blocks:
            block._inheritFrom(self)

        # Adust address map in sub devices
        for key,dev in self._nodes.iteritems():
            if isinstance(dev,Device):
                dev._setMemBase(self)

    def _readOthers(self):
        """Method to read and update non block based variables. Called from readAllBlocks."""
        # Be sure to call variable._updated() on variables to propogate changes to listeners
        pass

    def _pollOthers(self):
        """Method to poll and update non block based variables. Called from pollAllBlocks."""
        # Be sure to call variable._updated() on variables to propogate changes to listeners
        pass

    def _softReset(self):
        """Method to perform a softReset."""
        pass

    def _hardReset(self):
        """Method to perform a hardReset."""
        pass

    def _countReset(self):
        """Method to perform a countReset."""
        pass


class DataWriter(Device):
    """Special base class to control data files"""

    def __init__(self, parent, name, description='', hidden=False):
        """Initialize device class"""

        Device.__init__(self, parent=parent, name=name, description=description,
                        size=0, memBase=None, offset=0, hidden=hidden)

        self.classType    = 'dataWriter'
        self._open        = False
        self._dataFile    = ''
        self._bufferSize  = 0
        self._maxFileSize = 0

        Variable(parent=self, name='dataFile', description='Data File', base='string', mode='RW',
                 setFunction='self._parent._dataFile = value',
                 getFunction='value = self._parent._dataFile')

        Variable(parent=self, name='open', description='Data file open state',
                 base='bool', mode='RW',
                 setFunction=self._setOpen,  # Implement in sub class
                 getFunction='value = self._parent._open')

        Variable(parent=self, name='bufferSize', description='File buffering size',
                 base='uint', mode='RW',
                 setFunction=self._setBufferSize,  # Implement in sub class
                 getFunction='value = self._parent._bufferSize')

        Variable(parent=self, name='maxSize', description='File maximum size',
                 base='uint', mode='RW',
                 setFunction=self._setMaxSize,  # Implement in sub class
                 getFunction='value = self._parent._maxFileSize')

        Variable(parent=self, name='fileSize', description='File size in bytes',
                 base='uint', mode='RO',
                 setFunction=None, getFunction=self._getFileSize)  # Implement in sub class

        Variable(parent=self, name='frameCount', description='Total frames in file',
                 base='uint', mode='RO',
                 setFunction=None, getFunction=self._getFrameCount)  # Implement in sub class

        Command(parent=self, name='autoName',description='Generate File Name',
           function=self._genFileName)

    def _genFileName(self,var,arg):
        idx = self._dataFile.rfind('/')

        if idx < 0:
            base = ''
        else:
            base = self._dataFile[:idx+1]

        self._dataFile = base
        self._dataFile += datetime.datetime.now().strftime("%Y%m%d_%H%M%S.dat") 
        self.dataFile._updated()

    def _readOthers(self):
        self.fileSize.read()
        self.frameCount.read()

        self.fileSize._updated()
        self.frameCount._updated()

    def _pollOthers(self):
        self._readOthers()


class RunControl(Device):
    """Special base class to control runs"""

    def __init__(self, parent, name, description='', hidden=False):
        """Initialize device class"""

        Device.__init__(self, parent=parent, name=name, description=description,
                        size=0, memBase=None, offset=0, hidden=hidden)

        self.classType = 'runControl'
        self._runState = 'Stopped'
        self._runCount = 0
        self._runRate  = '1 Hz'

        Variable(parent=self, name='runState', description='Run State', base='enum', mode='RW',
                 enum={0:'Stopped', 1:'Running'},
                 setFunction=self._setRunState,
                 getFunction='value = self._parent._runState')

        Variable(parent=self, name='runRate', description='Run Rate', base='enum', mode='RW',
                 enum={1:'1 Hz',    10:'10 Hz'},
                 setFunction=self._setRunRate,
                 getFunction='value = self._parent._runRate')

        Variable(parent=self, name='runCount', description='Run Counter',
                 base='uint', mode='RO',
                 setFunction=None, getFunction='value = self._parent._runCount')

    # Reimplement in sub class
    def _setRunState(self,cmd,value):
        self._runState = value

    # Reimplement in sub class
    def _setRunRate(self,cmd,value):
        self._runRate = value

    def _readOthers(self):
        self.runCount.read()
        self.runCount._updated()

    def _pollOthers(self):
        self._readOthers()


def _getStructure(obj):
    """Recursive function to generate a dictionary for the structure"""
    data = {}
    for key,value in obj.__dict__.iteritems():
        if isinstance(value,Node):
            data[key] = _getStructure(value)
        else:
            data[key] = value

    return data


def _getConfig(obj):
    """Recursive function to generate a dictionary for the configuration"""
    data = {}
    for key,value in obj._nodes.iteritems():
        if isinstance(value,Device):
            data[key] = _getConfig(value)
        elif isinstance(value,Variable) and value.mode=='RW':
            data[key] = value.get()

    return data


def _setConfig(obj,d):
    """Recursive function to set configuration from a dictionary"""
    for key, value in d.iteritems():
        v = getattr(obj,key)
        if isinstance(v,Device):
            _setConfig(v,value)
        elif isinstance(v,Variable):
            v.set(value)


def _writeAll(obj):
    """Recursive function to write all blocks in each Device"""
    for key,value in obj._nodes.iteritems():
        if isinstance(value,Device):
            if value._enable:
                for block in value._blocks:
                    if block.mode == 'WO' or block.mode == 'RW':
                        block.backgroundWrite()
                _writeAll(value)


def _writeStale(obj):
    """Recursive function to write stale blocks in each Device"""
    for key,value in obj._nodes.iteritems():
        if isinstance(value,Device):
            if value._enable:
                for block in value._blocks:
                    if block.getStale() and (block.mode == 'WO' or block.mode == 'RW'):
                        block.backgroundWrite()
                _writeStale(value)


def _readAll(obj):
    """Recursive function to read all of the blocks in each Device"""
    for key,value in obj._nodes.iteritems():
        if isinstance(value,Device):
            if value._enable:
                for block in value._blocks:
                    if block.mode == 'RO' or block.mode == 'RW':
                        block.backgroundRead()

                value._readOthers()
                _readAll(value)


def _readPollable(obj):
    """Recursive function to read pollable blocks in each Device"""
    for key,value in obj._nodes.iteritems():
        if isinstance(value,Device):
            if value._enable:
                for block in value._blocks:
                    if block.pollEn and (block.mode == 'RO' or block.mode == 'RW'):
                        block.backgroundRead()

                value._pollOthers()
                _readPollable(value)


def _checkUpdatedBlocks(obj):
    """Recursive function to check status of all blocks in each Device"""
    for key,value in obj._nodes.iteritems():
        if isinstance(value,Device):
            if value._enable:
                for block in value._blocks:
                    block._checkUpdated()

                _checkUpdatedBlocks(value)


def _getAtPath(obj,path):
    """Recursive function to return object at passed path"""
    if not '.' in path:
        if hasattr(obj,path):
            return getattr(obj,path)
        else:
            return None
    else:
        base = path[:path.find('.')]
        rest = path[path.find('.')+1:]
        return(_getAtPath(getattr(obj,base),rest))


def _softReset(obj):
    """Recursive function to execute softReset commands in each device"""
    for key,value in obj._nodes.iteritems():
        if isinstance(value,Device):
             value._softReset()
             _softReset(value)


def _hardReset(obj):
    """Recursive function to execute hardReset commands in each device"""
    for key,value in obj._nodes.iteritems():
        if isinstance(value,Device):
             value._hardReset()
             _hardReset(value)


def _countReset(obj):
    """Recursive function to execute countReset commands in each device"""
    for key,value in obj._nodes.iteritems():
        if isinstance(value,Device):
             value._countReset()
             _countReset(value)

