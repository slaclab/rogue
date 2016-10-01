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

def streamConnect(source, dest):
    """Connect soruce and destination stream devices"""
    source._setSlave(dest)


def streamTap(source, tap):
    """Add a stream tap"""
    source._addSlave(tap)


def streamConnectBiDir(deviceA, deviceB):
    """Connect two endpoints of a bi-directional stream"""
    deviceA._setSlave(deviceB)
    deviceB._setSlave(deviceA)


def busConnect(client,server):
    """Connector a memory bus client and server"""
    client._setSlave(server)


class VariableError(Exception):
    pass


class NodeError(Exception):
    pass


def getStructure(obj):
    """Recursive function to generate a dictionary for the structure"""
    data = {}
    for key,value in obj.__dict__.iteritems():
       if not callable(value) and not key.startswith('_'):
          if isinstance(value,Node):
              data[key] = getStructure(value)
          else:
              data[key] = value
    return data


def getConfig(obj):
    """Recursive function to generate a dictionary for the configuration"""
    data = {}
    for key,value in obj.__dict__.iteritems():
        if isinstance(value,Device):
            data[key] = getConfig(value)
        elif isinstance(value,Variable) and value.mode=='RW':
            data[key] = value.get()
    return data


def setConfig(obj,d):
    """Recursive function to set configuration from a dictionary"""
    for key, value in d.iteritems():
        v = getattr(obj,key)
        if isinstance(v,Device):
            setConfig(v,value)
        elif isinstance(v,Variable):
            v.set(value)


def getAtPath(obj,path):
    """Recursive function to return object at passed path"""
    if not '.' in path:
        return getattr(obj,path)
    else:
        base = path[:path.find('.')]
        rest = path[path.find('.')+1:]
        return(getAtPath(getattr(obj,base),rest))


class Root(rogue.interfaces.stream.Master):
    """System base"""

    def __init__(self):
        rogue.interfaces.stream.Master.__init__(self)

        self.__updated = []
        self.__errorLog = []

        # Config write command exposed to higher level
        Command(parent=self, name='writeConfig',description='Write Configuration',
           function=self._writeConfig)

        # Config read command exposed to higher level
        Command(parent=self, name='readConfig',description='Read Configuration',
           function=self._readConfig)

    # Track updated variables
    def _variableUpdated(self,node):
        if not (node in self.__updated):
            self.__updated.append(node)

    # Add an entry
    def _addNode(self,node):
        if hasattr(self,node.name):
            raise NodeError('Invalid %s name %s. Name already exists' % (node.classType,node.name))
        else:
            setattr(self,node.name,node)

    # Push configuration on stream
    def streamConfig(self):
        s = self.getYamlConfig()
        f = self._reqFrame(len(s),True)
        b = bytearray()
        b.extend(s)
        f.write(b,0)
        self._sendFrame(f)

    # Generate structure
    def getStructure(self):
        return getStructure(self)

    # Get copy of updated list and clear
    def getUpdated(self):
        ret = self.__updated
        self.__updated = []
        return ret

    def readAll(self):
        """Read all"""

        # Generate transactions for sub devices
        for key,dev in self.__dict__.iteritems():
            if isinstance(dev,Device):
                dev.readAll()
            
    def writeAll(self):
        """Write all with error check"""

        # Generate transactions for sub devices
        for key,dev in self.__dict__.iteritems():
            if isinstance(dev,Device):
                dev.writeAll()

    def writeStale(self):
        """Write stale with error check"""

        # Generate transactions for sub devices
        for key,dev in self.__dict__.iteritems():
            if isinstance(dev,Device):
                dev.writeStale()

    def _writeConfig(self,cmd,arg):
        with open(arg,'w') as f:
            f.write(self.getYamlConfig())

    def getYamlConfig(self):
        return yaml.dump(getConfig(self),default_flow_style=False)

    def _readConfig(self,cmd,arg):
        with open(arg,'r') as f:
            self.setYamlConfig(f.read())

    def setYamlConfig(self,yml):
        d = yaml.load(yml)
        setConfig(self,d)
        self.writeAll()

    def set(self,path,value):
        v = getAtPath(self,path)
        v.set(value)

    def setAndWrite(self,path,value):
        v = getAtPath(self,path)
        v.setAndWrite(value)

    def setAndWait(self,path,value):
        v = getAtPath(self,path)
        v.setAndWait(value)

    def get(self,path):
        v = getAtPath(self,path)
        return(v.get())

    def readAndGet(self,path):
        v = getAtPath(self,path)
        return(v.readAndGet())

    def command(self,path,arg=None):
        v = getAtPath(self,path)
        v(arg)


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

        if isinstance(parent,Node):
            self._root = parent._root
            self.path  = parent.path + "." + self.name
        else:
            self._root = parent
            self.path  = self.name

        # Add to parent list
        self._parent._addNode(self)

    def _addNode(self,node):
        if hasattr(self,node.name):
            raise NodeError('Invalid %s name %s. Name already exists' % (node.classType,node.name))
        else:
            setattr(self,node.name,node)


class Variable(Node):
    """Variable holder"""

    def __init__(self, parent, name, description, bitSize=32, bitOffset=0, 
                 base='hex', mode='RW', enums=None, hidden=False, setFunction=None, getFunction=None):
        """Initialize variable class"""

        Node.__init__(self,parent,name,description,hidden,'variable')

        # Public Attributes
        self.bitSize   = bitSize
        self.bitOffset = bitOffset
        self.base      = base      
        self.mode      = mode
        self.enums     = enums
        self.hidden    = hidden

        # Check modes
        if (self.mode != 'RW') and (self.mode != 'RO') and (self.mode != 'WO') and (self.mode != 'CMD'):
            raise VariableError('Invalid variable mode %s. Supported: RW, RO, WO, CMD' % (self.mode))

        # Tracking variables
        self._block       = None
        self._setFunction = setFunction
        self._getFunction = getFunction

    def _intSet(self,value):
        if self.mode == 'RW' or self.mode == 'WO' or self.mode == 'CMD':
            if self._setFunction != None:
                if callable(self._setFunction):
                    self._setFunction(self,value)
                else:
                    exec(textwrap.dedent(self._setFunction))

            elif self._block:        
                if self.base == 'string':
                    self._block.setString(value)
                else:
                    self._block.setUInt(self.bitOffset,self.bitSize,value)
        else:
            raise VariableError('Attempt to set variable with mode %s' % (self.mode))
                
    def _intGet(self):
        if self.mode == 'RW' or self.mode == 'RO':
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
                else:
                    return(self._block.getUInt(self.bitOffset,self.bitSize))
            else:
                return None
        else:
            raise VariableError('Attempt to get variable with mode %s' % (self.mode))

    def _updated(self):
        self._root._variableUpdated(self)

    def set(self,value):
        """Set a value to shadow memory without writing"""
        self._intSet(value)
        self._updated()

    def setAndWrite(self,value):
        """Set a value to shadow memory with background write"""
        self._intSet(value)
        self._block.backgroundWrite()
        self._updated()

    def setAndWait(self,value):
        """Set a value to shadow memory with blocking write"""
        self._intSet(value)
        self._block.blockingWrite()
        self._updated()

    def get(self):
        """Get a value from shadow memory"""
        return self._intGet()

    def readAndGet(self):
        """Get a value from shadow memory after blocking read"""
        self._block.blockingRead()
        self._updated()
        return self._intGet()


class Command(Node):
    """Command holder"""

    def __init__(self, parent, name, description, function=None, hidden=False):
        """Initialize command class"""

        Node.__init__(self,parent,name,description,hidden,'command')

        # Public attributes
        self.hidden = hidden

        # Tracking
        self._function = function

    def __call__(self,arg=None):
        """Execute command"""

        if self._function != None:
            if callable(self._function):
                self._function(self,arg)
            else:
                exec(textwrap.dedent(self._function))


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

    # Generate variable updates to base level
    def _genVariableUpdates(self):
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
            self.setMemBase(memBase,offset)
        elif isinstance(self._parent,rogue.interfaces.memory.Master):
            self._inheritFrom(self._parent)

        # Variable interface to enable flag
        Variable(parent=self, name='enable', description='Enable Flag', bitSize=1, 
                bitOffset=0, base='bool', mode='RW', setFunction=self._setEnable, getFunction=self._getEnable)

    def _setEnable(self, var, enable):
        self._enable = enable

        for block in self._blocks:
            block.setEnable(enable)

    def _getEnable(self,var):
        return(self._enable)

    def setMemBase(self,memBase,offset):
        """Connect to memory slave at offset"""
        self._setAddress(offset)

        # Device is a master (Device)
        if isinstance(memBase,rogue.interfaces.memory.Master):
            # Inhertit base address and slave pointer from one level up
            self._inheritFrom(memBase)

        # Direct connection to slae
        else:
            self._setSlave(memBase)

        # Adust address map in blocks
        for block in self._blocks:
            block._inheritFrom(self)

        # Adust address map in sub devices
        for key,dev in self.__dict__.iteritems():
            if isinstance(dev,Device):
                dev._inheritFrom(self)

    def readAll(self):
        """Read all with error check"""
        if self._enable:

            # Generate transactions for local blocks
            for block in self._blocks:
                if block.mode == 'RO' or block.mode == 'RW':
                    block.backgroundRead()

            # Generate transactions for sub devices
            for key,dev in self.__dict__.iteritems():
                if isinstance(dev,Device):
                    dev.readAll()

            # Check status of local blocks
            for block in self._blocks:
                if block.mode == 'RO' or block.mode == 'RW':
                    block.checkError()
                    block._genVariableUpdates()

    def readPoll(self):
        """Read all with error check"""
        if self._enable:

            # Generate transactions for local blocks
            for block in self._blocks:
                if block.pollEn and (block.mode == 'RO' or block.mode == 'RW'):
                    block.backgroundRead()

            # Generate transactions for sub devices
            for key,dev in self.__dict__.iteritems():
                if isinstance(dev,Device):
                    dev.readPoll()

            # Check status of local blocks
            for block in self._blocks:
                if block.pollEn and (block.mode == 'RO' or block.mode == 'RW'):
                    block.checkError()
                    block._genVariableUpdates()

    def writeAll(self):
        """Write all with error check"""
        if self._enable:

            # Generate transactions for local blocks
            for block in self._blocks:
                if block.mode == 'WO' or block.mode == 'RW':
                    block.backgroundWrite()

            # Generate transactions for sub devices
            for key,dev in self.__dict__.iteritems():
                if isinstance(dev,Device):
                    dev.writeAll()

            # Check status of local blocks
            for block in self._blocks:
                if block.mode == 'WO' or block.mode == 'RW':
                    block.checkError()
                    block._genVariableUpdates()

    def writeStale(self):
        """Write stale with error check"""
        if self._enable:

            # Generate transactions for local blocks
            for block in self._blocks:
                if block.getStale() and (block.mode == 'WO' or block.mode == 'RW'):
                    block.backgroundWrite()

            # Generate transactions for sub devices
            for key,dev in self.__dict__.iteritems():
                if isinstance(dev,Device):
                    dev.writeStale()

            # Check status of local blocks
            for block in self._blocks:
                if block.mode == 'WO' or block.mode == 'RW':
                    block.checkError()
                    block._genVariableUpdates()

