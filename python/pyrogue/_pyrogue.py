#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Title      : PyRogue base module
#-----------------------------------------------------------------------------
# File       : pyrogue/__init__.py
# Created    : 2016-09-29
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
import sys
import rogue.interfaces.memory
import textwrap
import yaml
import threading
import time
import math
from collections import OrderedDict as odict
import collections
import datetime
import traceback
import re
import functools as ft
import itertools
import logging
import heapq
from inspect import signature


def logInit(cls=None,name=None):
    """Init a logging pbject. Set global options."""
    logging.basicConfig(
        #level=logging.NOTSET,
        format="%(levelname)s:%(name)s:%(message)s",
        stream=sys.stdout)

    msg = 'pyrogue'
    if cls: msg += "." + cls.__class__.__name__
    if name: msg += "." + name
    return logging.getLogger(msg)


def streamConnect(source, dest):
    """
    Attach the passed dest object to the source a stream.
    Connect source and destination stream devices.
    source is either a stream master sub class or implements
    the _getStreamMaster call to return a contained master.
    Similiarly dest is either a stream slave sub class or implements
    the _getStreamSlave call to return a contained slave.
    """

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
    """
    Attach the passed dest object to the source for a streams
    as a secondary destination.
    Connect source and destination stream devices.
    source is either a stream master sub class or implements
    the _getStreamMaster call to return a contained master.
    Similiarly dest is either a stream slave sub class or implements
    the _getStreamSlave call to return a contained slave.
    """

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
    """
    Attach the passed dest object to the source a stream.
    Connect source and destination stream devices.
    source is either a stream master sub class or implements
    the _getStreamMaster call to return a contained master.
    Similiarly dest is either a stream slave sub class or implements
    the _getStreamSlave call to return a contained slave.
    """

    """
    Connect deviceA and deviceB as end points to a
    bi-directional stream. This method calls the
    streamConnect method to perform the actual connection. 
    See streamConnect description for object requirements.
    """

    streamConnect(deviceA,deviceB)
    streamConnect(deviceB,deviceA)


def busConnect(source,dest):
    """
    Connect the source object to the dest object for 
    memory accesses. 
    source is either a memory master sub class or implements
    the _getMemoryMaster call to return a contained master.
    Similiarly dest is either a memory slave sub class or implements
    the _getMemorySlave call to return a contained slave.
    """

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

def wordCount(bits, wordSize):
    ret = bits // wordSize
    if (bits % wordSize != 0 or bits == 0):
        ret += 1
    return ret

def byteCount(bits):
    return wordCount(bits, 8)

# def numBytes(bits):
#     if bits == 0: return 1
#     return int(math.ceil(float(bits) / 8.0))


class NodeError(Exception):
    """ Exception for node manipulation errors."""
    pass


class Node(object):
    """
    Class which serves as a managed obect within the pyrogue package. 
    Each node has the following public fields:
        name: Global name of object
        description: Description of the object.
        hidden: Flag to indicate if object should be hidden from external interfaces.
        classtype: text string matching name of node sub-class
        path: Full path to the node (ie. node1.node2.node3)

    Each node is associated with a parent and has a link to the top node of a tree.
    A node has a list of sub-nodes as well as each sub-node being attached as an
    attribute. This allows tree browsing using: node1.node2.node3
    """

    def __init__(self, name, classType, description="", hidden=False, parent=None):
        """Init the node with passed attributes"""

        # Public attributes
        self.name        = name     
        self.description = description
        self.hidden      = hidden
        self.classType   = classType
        self.path        = self.name

        # Tracking
        self._parent = parent
        self._root   = self
        self._nodes  = odict()
       
        # Setup logging
        self._log = logInit(self,name)

        if parent is not None:
            parent.add(self)

    def __repr__(self):
        return self.path

    def __getattr__(self, name):
        """Allow child Nodes with the 'name[key]' naming convention to be accessed as if they belong to a 
        dictionary of Nodes with that 'name'.
        This override builds an OrderedDict of all child nodes named as 'name[key]' and returns it.
        Raises AttributeError if no such named Nodes are found. """
        
        ret = odict()
        rg = re.compile('{:s}\\[(.*?)\\]'.format(name))
        for k,v in self._nodes.items():
            m = rg.match(k)
            if m:
                key = m.group(1)
                if key.isdigit():
                    key = int(key)
                ret[key] = v

        if len(ret) == 0:
            raise AttributeError('{} has no attribute {}'.format(self, name))
        
        return ret
        

    def add(self,node):
        """Add node as sub-node"""

        # Names of all sub-nodes must be unique
        if node.name in self._nodes:
            raise NodeError('Error adding %s with name %s to %s. Name collision.' % 
                             (node.classType,node.name,self.name))

        # Attach directly as attribute and add to ordered node dictionary
        setattr(self,node.name,node)
        self._nodes[node.name] = node

        # Update path related attributes
        node._updateTree(self)

    def addNode(self, nodeClass, **kwargs):
        self.add(nodeClass(**kwargs))

    def addNodes(self, nodeClass, number, stride, **kwargs):
        name = kwargs.pop('name')
        offset = kwargs.pop('offset')
        for i in range(number):
            self.add(nodeClass(name='{:s}[{:d}]'.format(name, i), offset=offset+(i*stride), **kwargs))

    def _getNodes(self,typ):
        """
        Get a ordered dictionary of nodes.
        pass a class type to receive a certain type of node
        """
        return odict([(k,n) for k,n in self._nodes.items() if isinstance(n, typ)])

    @property
    def nodes(self):
        """
        Get a ordered dictionary of all nodes.
        """
        return self._nodes

    @property
    def variables(self):
        """
        Return an OrderedDict of the variables but not commands (which are a subclass of Variable
        """
        return odict([(k,n) for k,n in self._nodes.items()
                      if isinstance(n, Variable) and not isinstance(n, Command)])

    @property
    def commands(self):
        """
        Return an OrderedDict of the Commands that are children of this Node
        """
        return self._getNodes(Command)

    @property
    def devices(self):
        """
        Return an OrderedDict of the Devices that are children of this Node
        """
        return self._getNodes(Device)

    @property
    def parent(self):
        """
        Return parent node or NULL if no parent exists.
        """
        return self._parent

    @property
    def root(self):
        """
        Return root node of tree.
        """
        return self._root

    def getNode(self, path):
        """Find a node in the tree that has a particular path string"""
        obj = self
        for a in path.split('.')[1:]:
            obj = getattr(obj, a)
        return obj

    def _rootAttached(self):
        """Called once the root node is attached. Can override to do anything depends on the full tree existing"""
        pass

    def _updateTree(self,parent):
        """
        Update tree. In some cases nodes such as variables, commands and devices will
        be added to a device before the device is inserted into a tree. This call
        ensures the nodes and sub-nodes attached to a device can be updated as the tree
        gets created.
        """
        self._parent = parent
        self._root   = self._parent._root
        self.path    = self._parent.path + '.' + self.name

        if isinstance(self._root, Root):
            self._rootAttached()

        for key,value in self._nodes.items():
            value._updateTree(self)


    def _getStructure(self):
        """
        Get structure starting from this level.
        Attributes that are Nodes are recursed.
        Called from getYamlStructure in the root node.
        """
        data = odict()

        # First get non-node local values
        for key,value in self.__dict__.items():
            if (not key.startswith('_')) and (not isinstance(value,Node)) and (not callable(value)):
                data[key] = value

        # Next get sub nodes
        for key,value in self.nodes.items():
            data[key] = value._getStructure()

        return data

    def _addStructure(self,d,setFunction,cmdFunction):
        """
        Creation structure from passed dictionary. Used for clients.
        Blocks are not created and functions are set to the passed values.
        """
        for key, value in d.items():

            # Only work on nodes
            if isinstance(value,dict) and 'classType' in value:

                # If entry is a device add and recurse
                if value['classType'] == 'device' or value['classType'] == 'dataWriter' or \
                   value['classType'] == 'runControl':

                    dev = Device(**value)
                    dev.classType = value['classType']
                    self.add(dev)
                    dev._addStructure(value,setFunction,cmdFunction)

                # If entry is a variable add and recurse
                elif value['classType'] == 'variable':
                    if not value['name'] in self._nodes:
                        value['offset']      = None
                        value['setFunction'] = setFunction
                        value['getFunction'] = 'value = self._scratch'
                        var = Variable(**value)
                        self.add(var)
                    else:
                        getattr(self,value['name'])._setFunction = setFunction
                        getattr(self,value['name'])._getFunction = 'value = self._scratch'

                # If entry is a variable add and recurse
                elif value['classType'] == 'command':
                    if not value['name'] in self._nodes:
                        value['function'] = cmdFunction
                        cmd = Command(**value)
                        self.add(cmd)
                    else:
                        getattr(self,value['name'])._function = cmdFunction

    def _getVariables(self,modes):
        """
        Get variable values in a dictionary starting from this level.
        Attributes that are Nodes are recursed.
        modes is a list of variable modes to include.
        Called from getYamlVariables in the root node.
        """
        data = odict()
        for key,value in self._nodes.items():
            if isinstance(value,Device):
                data[key] = value._getVariables(modes)
            elif isinstance(value,Variable) and (value.mode in modes):
                data[key] = value.get(read=False)

        return data

    def _setOrExec(self,d,writeEach,modes):
        """
        Set variable values or execute commands from a dictionary starting 
        from this level.  Attributes that are Nodes are recursed.
        modes is a list of variable nodes to act on for variable accesses.
        Called from setOrExecYaml in the root node.
        """
        for key, value in d.items():

            # Entry is in node list
            if key in self._nodes:

                # If entry is a device, recurse
                if isinstance(self._nodes[key],Device):
                    self._nodes[key]._setOrExec(value,writeEach,modes)

                # Execute if command
                elif isinstance(self._nodes[key],Command):
                    self._nodes[key](value)

                # Set value if variable with enabled mode
                elif isinstance(self._nodes[key],Variable) and (self._nodes[key].mode in modes):
                    self._nodes[key].set(value,writeEach)


class VariableError(Exception):
    """ Exception for variable access errors."""
    pass


class Variable(Node):
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
            self.base = IntModel(numBits=bitSize, signed=False, endianness='little')
        elif base == 'int':
            self.base = IntModel(numBits=bitSize, signed=True, endianness='little')
        elif base == 'bool':
            self.base = BoolModel()
        elif base == 'string':
            self.base = StringModel()
        elif base == 'float':
            self.base = FloatModel()

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


        if isinstance(self.base, StringModel):
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
        Node.__init__(self, name=name, classType=classType, description=description, hidden=hidden, parent=parent)

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
        
        

class ModelMeta(type):
    def __init__(cls, *args, **kwargs):
        super().__init__(*args, **kwargs)
        cls.cache = {}

    def __call__(cls, *args, **kwargs):
        key = str(args) + str(kwargs)
        if key not in cls.cache:
            inst = super().__call__(*args, **kwargs)
            cls.cache[key] = inst
        return cls.cache[key]

class Model(metaclass=ModelMeta):
    pass

class IntModel(Model):
    """Variable holding an unsigned integer"""
    def __init__(self, numBits=1, signed=False, endianness='little'):
        self.numBits = numBits
        self.numBytes = byteCount(numBits)
        self.defaultdisp = '{:x}'
        self.signed = signed
        self.endianness = endianness

    def _toBlock(self, value):
        return value.to_bytes(self.numBytes, self.endianness, signed=self.signed)

    def _fromBlock(self, ba):
        return int.from_bytes(ba, self.endianness, signed=self.signed)

    def _fromString(self, string):
        i = int(string, 0)
        # perform twos complement if necessary
        if self.signed and i>0 and ((i >> self.numBits) & 0x1 == 1):
            i = i - (1 << self.numBits)
        return i            

    def __str__(self):
        if self.signed is True:
            return 'Int{}'.format(self.numBits)
        else:
            return 'UInt{}'.format(self.numBits)

class BoolModel(Model):

    def __init__(self):
        self.defaultdisp = {False: 'False', True: 'True'}

    def _toBlock(self, value):
        return value.to_bytes(1, 'little', signed=False)

    def _fromBlock(self, ba):
        return bool(int.from_bytes(ba, 'little', signed=False))

    def _fromString(self, string):
        return str.lower(string) == "true"

    def __str__(self):
        return 'Bool'
        
class StringModel(Model):
    """Variable holding a string"""
    def __init__(self, encoding='utf-8', **kwargs):
        super().__init__(**kwargs)
        self.encoding = encoding
        self.defaultdisp = '{}'

    def _toBlock(self, value):
        ba = bytearray(value, self.encoding)
        ba.extend(bytearray(1))
        return ba

    def _fromBlock(self, ba):
        s = ba.rstrip(bytearray(1))
        return s.decode(self.encoding)

    def _fromString(self, string):
        return string

    def __str__(self):
        return 'String'

class FloatModel(Model):
    def __init__(self, endianness='little'):
        super().__init__(self)
        self.defaultdisp = '{:f}'
        if endianness == 'little':
            self.format = 'f'
        if endianness == 'big':
            self.format = '!f'

    def _toBlock(self, value):
        return bytearray(struct.pack(self.format, value))

    def _fromBlock(self, ba):
        return struct.unpack(self.format, ba)

    def _fromString(self, string):
        return float(string)

    def __str__(self):
        return 'Float32'

class DoubleModel(FloatModel):
    def __init__(self, endianness='little'):
        super().__init__(self, endianness)
        if endianness == 'little':
            self.format = 'd'
        if endianness == 'big':
            self.format = '!d'

    def __str__(self):
        return 'Float64'

class Command(Variable):
    """Command holder: Subclass of variable with callable interface"""

    def __init__(self, name=None, mode='CMD', function=None, **kwargs):
        Variable.__init__(self, name=name, mode=mode, classType='command', **kwargs)

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

class BlockError(Exception):
    """ Exception for memory access errors."""

    def __init__(self,block):
        self._error = block.error
        block._error = 0
        self._value = "Error in block %s with address 0x%x: Block Variables: %s. " % (block.name,block.address,block._variables)

        if (self._error & 0xFF000000) == rogue.interfaces.memory.TimeoutError:
            self._value += "Timeout after %s seconds" % (block.timeout)

        elif (self._error & 0xFF000000) == rogue.interfaces.memory.VerifyError:
            bStr = ''.join('0x{:02x} '.format(x) for x in block._bData)
            vStr = ''.join('0x{:02x} '.format(x) for x in block._vData)
            mStr = ''.join('0x{:02x} '.format(x) for x in block._mData)
            self._value += "Verify error. Local=%s, Verify=%s, Mask=%s" % (bStr,vStr,mStr)

        elif (self._error & 0xFF000000) == rogue.interfaces.memory.AddressError:
            self._value += "Address error"

        elif (self._error & 0xFF000000) == rogue.interfaces.memory.SizeError:
            self._value += "Size error. Size=%i" % (block._size)

        elif (self._error & 0xFF000000) == rogue.interfaces.memory.AxiTimeout:
            self._value += "AXI timeout"

        elif (self._error & 0xFF000000) == rogue.interfaces.memory.AxiFail:
            self._value += "AXI fail"

        else:
            self._value += "Unknown error 0x%x" % (self._error)

    def __str__(self):
        return repr(self._value)


 
class Block(rogue.interfaces.memory.Master):
    """Internal memory block holder"""

    def __init__(self, variable):
        """
        Initialize memory block class.
        Pass initial variable.
        """
        rogue.interfaces.memory.Master.__init__(self)

        # Attributes
        self._offset    = variable.offset
        self._mode      = variable.mode
        self._name      = variable.name
        self._bData     = bytearray()
        self._vData     = bytearray()
        self._mData     = bytearray()
        self._size      = 0
        self._variables = []
        self._timeout   = 1.0
        self._lock      = threading.Lock()
        self._cond      = threading.Condition(self._lock)
        self._error     = 0
        self._doUpdate  = False
        self._doVerify  = False
        self._device    = variable.parent
        self._tranTime  = time.time()

        self._setSlave(self._device)
        self._addVariable(variable)

        # Setup logging
        self._log = logInit(self,self._name)

    def __repr__(self):
        return repr(self._variables)

    def set(self, var, value):
        """
        Update block with bitSize bits from passed byte array.
        Offset sets the starting point in the block array.
        """
        with self._cond:
            self._waitTransaction()

            ba = var.base._toBlock(value)

            # Access is fully byte aligned
            if (var.bitOffset % 8) == 0 and (var.bitSize % 8) == 0:
                self._bData[var.bitOffset//8:(var.bitOffset+var.bitSize)//8] = ba

            # Bit level access
            else:
                for x in range(0, var.bitSize):
                    setBitToBytes(self._bData,x+var.bitOffset,getBitFromBytes(ba,x))

    def get(self, var):
        """
        Get bitSize bytes from block data.
        Offset sets the starting point in the block array.
        bytearray is returned
        """
        with self._cond:
            self._waitTransaction()

            # Error
            if self._error > 0:
                raise BlockError(self)


            # Access is fully byte aligned
            if (var.bitOffset % 8) == 0 and (var.bitSize % 8) == 0:
                return var.base._fromBlock(self._bData[int(var.bitOffset/8):int((var.bitOffset+var.bitSize)/8)])

            # Bit level access
            else:
                ba = bytearray(int(var.bitSize / 8))
                if (var.bitSize % 8) > 0: ba.extend(bytearray(1))
                for x in range(0,var.bitSize):
                    setBitToBytes(ba,x,getBitFromBytes(self._bData,x+var.bitOffset))
                return var.base._fromBlock(ba)

    def backgroundTransaction(self,type):
        """
        Perform a background transaction
        """
        self._startTransaction(type)

    def blockingTransaction(self,type):
        """
        Perform a blocking transaction
        """
        self._log.debug("Setting block. Addr=%x, Data=%s" % (self._offset,self._bData))
        self._startTransaction(type)
        self._checkTransaction(update=False)
        self._log.debug("Done block. Addr=%x, Data=%s" % (self._offset,self._bData))

    @property
    def offset(self):
        return self._offset

    @property
    def address(self):
        return self._offset | self._reqOffset()

    @property
    def name(self):
        return self._name

    @property
    def mode(self):
        return self._mode

    @property
    def timeout(self):
        return self._timeout

    @timeout.setter
    def timeout(self,value):
        with self._cond:
            self._waitTransaction()
            self._timeout = value

    @property
    def error(self):
        return self._error

    def _waitTransaction(self):
        """
        Wait while a transaction is pending.
        Set an error on timeout.
        Lock must be held before calling this method
        """
        lid = self._getId()
        while lid > 0:
            self._cond.wait(.01)
            if self._getId() == lid and (time.time() - self._tranTime) > self._timeout:
                self._endTransaction()
                self._error = rogue.interfaces.memory.TimeoutError
                break
            lid = self._getId()

    def _addVariable(self,var):
        """
        Add a variable to the block
        """

	
        with self._cond:
            self._waitTransaction()

            # Return false if offset does not match
            if var.offset != self._offset:
                return False

            # Compute the max variable address to determine required size of block
            varBytes = int(math.ceil(float(var.bitOffset + var.bitSize) / 8.0))

            # Link variable to block
            var._block = self
            self._variables.append(var)

            # If variable modes mismatch, set to read/write
            if var.mode != self._mode:
                self._mode = 'RW'

            # Adjust size to hold variable. Underlying class will adjust
            # size to align to minimum protocol access size 
            if self._size < varBytes:
                self._bData.extend(bytearray(varBytes - self._size))
                self._vData.extend(bytearray(varBytes - self._size))
                self._mData.extend(bytearray(varBytes - self._size))
                self._size = varBytes

            # Update verify mask
            if var.mode == 'RW' and var.verify is True:
                for x in range(var.bitOffset,var.bitOffset+var.bitSize):
                    setBitToBytes(self._mData,x,1)

            return True

    def _startTransaction(self,type):
        """
        Start a transaction.
        """

        self._log.debug('_startTransaction type={}'.format(type))

        minSize = self._reqMinAccess()
        tData = None

        with self._cond:
            self._waitTransaction()

            # Adjust size if required
            if (self._size % minSize) > 0:
                newSize = (((int)(self._size / minSize) + 1) * minSize)
                self._bData.extend(bytearray(newSize - self._size))
                self._vData.extend(bytearray(newSize - self._size))
                self._mData.extend(bytearray(newSize - self._size))
                self._size = newSize

            # Return if not enabled
            if not self._device.enable.get(read=False):
                return
            
            self._log.debug('len bData = {}, vData = {}, mData = {}'.format(len(self._bData), len(self._vData), len(self._mData)))
                  
            # Setup transaction
            self._doVerify = (type == rogue.interfaces.memory.Verify)
            self._doUpdate = (type == rogue.interfaces.memory.Read)
            self._error    = 0
            self._tranTime = time.time()

            # Set data pointer
            tData = self._vData if self._doVerify else self._bData

        # Start transaction outside of lock
        self._reqTransaction(self._offset,tData,type)

    def _doneTransaction(self,tid,error):
        """
        Callback for when transaction is complete
        """
        with self._lock:

            # Make sure id matches
            if tid != self._getId():
                return

            # Clear transaction state
            self._endTransaction()
            self._error = error

            # Check for error
            if error > 0:
                self._doUpdate = False

            # Do verify
            elif self._doVerify:
                for x in range(0,self._size):
                    if (self._vData[x] & self._mData[x]) != (self._bData[x] & self._mData[x]):
                        self._error = rogue.interfaces.memory.VerifyError
                        break

            # Notify waiters
            self._cond.notify()

    def _checkTransaction(self,update):
        """
        Check status of block.
        If update=True notify variables if read
        """
        doUpdate = False
        with self._cond:
            self._waitTransaction()

            # Updated
            doUpdate = update and self._doUpdate
            self._doUpdate = False

            # Error
            if self._error > 0:
                raise BlockError(self)

        # Update variables outside of lock
        if doUpdate: self._updated()

    def _updated(self):
        for variable in self._variables:
            variable._updated()


class Device(Node,rogue.interfaces.memory.Hub):
    """Device class holder. TODO: Update comments"""

    def __init__(self, name=None, description="", memBase=None, offset=0, hidden=False, parent=None,
                 variables=None, expand=True, enabled=True, classType='device', **dump):
        """Initialize device class"""
        if name is None:
            name = self.__class__.__name__

        # Hub.__init__ must be called first for _setSlave to work below
        rogue.interfaces.memory.Hub.__init__(self,offset)

        # Blocks
        self._blocks    = []
        self._memBase   = memBase
        self._resetFunc = None
        self.expand     = expand

        # Connect to memory slave
        if memBase: self._setSlave(memBase)

        # Node.__init__ can't be called until after self._memBase is created
        Node.__init__(self, name=name, hidden=hidden, classType=classType, description=description, parent=parent)

        self._log.info("Making device {:s}".format(name))

        # Convenience methods
        self.addDevice = ft.partial(self.addNode, Device)
        self.addDevices = ft.partial(self.addNodes, Device)
        self.addVariable = ft.partial(self.addNode, Variable)        
        self.addVariables = ft.partial(self.addNodes, Variable)
        self.addCommand = ft.partial(self.addNode, Command)        
        self.addCommands = ft.partial(self.addNodes, Command)

        # Variable interface to enable flag
        self.add(Variable(name='enable', value=enabled, base='bool', mode='RW',
                          setFunction=self._setEnable, getFunction=self._getEnable,
                          description='Determines if device is enabled for hardware access'))

        if variables is not None and isinstance(variables, collections.Iterable):
            if all(isinstance(v, Variable) for v in variables):
                # add the list of Variable objects
                self.add(variables)
            elif all(isinstance(v, dict) for v in variables):
                # create Variable objects from a dict list
                self.add(Variable(**v) for v in variables)

        cmds = sorted((d for d in (getattr(self, c) for c in dir(self)) if hasattr(d, 'PyrogueCommandArgs')),
                      key=lambda x: x.PyrogueCommandOrder)
        for cmd in cmds:
            args = getattr(cmd, 'PyrogueCommandArgs')
            if 'name' not in args:
                args['name'] = cmd.__name__
            self.add(Command(function=cmd, **args))

    def add(self,node):
        """
        Add node as sub-node in the object
        Device specific implementation to add blocks as required.
        """

        # Special case if list (or iterable of nodes) is passed
        if isinstance(node, collections.Iterable) and all(isinstance(n, Node) for n in node):
            for n in node:
                self.add(n)
            return

        # Call node add
        Node.add(self,node)

        # Adding device whos membase is not yet set
        if isinstance(node,Device) and node._memBase is None:
            node._setSlave(self)

        if isinstance(node,Variable) and node.offset is not None:
            if not any(block._addVariable(node) for block in self._blocks):
                self._log.debug("Adding new block %s at offset %x" % (node.name,node.offset))
                self._blocks.append(Block(node))

    def hideVariables(self, hidden, variables=None):
        """Hide a list of Variables (or Variable names)"""
        if variables is None:
            variables=self.variables.values()
            
        for v in variables:
            if isinstance(v, Variable):
                v.hidden = hidden;
            elif isinstance(variables[0], str):
                self.variables[v].hidden = hidden

    def setResetFunc(self,func):
        """
        Set function for count, hard or soft reset
        resetFunc(type) 
        where type = 'soft','hard','count'
        """
        self._resetFunc = func

    def _setEnable(self, dev, var, enable):
        """
        Method to update enable in underlying block.
        May be re-implemented in some sub-class to 
        propogate enable to leaf nodes in the tree.
        """
        var.value = enable

    def _getEnable(self, dev, var):
        if var.value is False:
            return False
        if dev == dev._root:
            return dev.enable.value
        else:
            return dev._parent.enable.get(read=False)

    def _backgroundTransaction(self,type):
        """
        Perform background transactions
        """
        if not self.enable: return

        # Execute all unique beforeReadCmds for reads or verify
        if type == rogue.interfaces.memory.Read or type == rogue.interfaces.memory.Verify:
            cmds = set([v._beforeReadCmd for v in self.variables.values() if v._beforeReadCmd is not None])
            for cmd in cmds:
                cmd()

        # Process local blocks. 
        for block in self._blocks:

            # Only process writes if block is WO or RW
            # Only process reads if block is RO or RW
            # Only process verify if block is RW
            if (type == rogue.interfaces.memory.Write  and (block.mode == 'WO' or block.mode == 'RW')) or \
               (type == rogue.interfaces.memory.Read   and (block.mode == 'RO' or block.mode == 'RW')) or  \
               (type == rogue.interfaces.memory.Verify and block.mode == 'RW'):
                block.backgroundTransaction(type)

        # Process rest of tree
        for key,value in self._nodes.items():
            if isinstance(value,Device):
                value._backgroundTransaction(type)

        # Execute all unique afterWriteCmds for writes
        if type == rogue.interfaces.memory.Write:
            cmds = set([v._afterWriteCmd for v in self.variables.values() if v._afterWriteCmd is not None])
            for cmd in cmds:
                cmd()

    def _checkTransaction(self,update):
        """Check errors in all blocks and generate variable update nofifications"""
        if not self.enable: return

        # Process local blocks
        for block in self._blocks:
            block._checkTransaction(update)

        # Process rest of tree
        for key,value in self._nodes.items():
            if isinstance(value,Device):
                value._checkTransaction(update)

    def _devReset(self,rstType):
        """Generate a count, soft or hard reset"""
        if callable(self._resetFunc):
            self._resetFunc(self,rstType)

        # process remaining blocks
        for key,value in self._nodes.items():
            if isinstance(value,Device):
                value._devReset(rstType)

    def _setTimeout(self,timeout):
        """
        Set timeout value on all devices & blocks
        """

        for block in self._blocks:
            block.timeout = timeout

        for key,value in self._nodes.items():
            if isinstance(value,Device):
                value._setTimeout(timeout)


    def command(self, **kwargs):
        """A Decorator to add inline constructor functions as commands"""
        def _decorator(func):
            if 'name' not in kwargs:
                kwargs['name'] = func.__name__

            argCount = len(signature(func).parameters)
            def newFunc(dev, var, val):
                if argCount == 0:
                    return func()
                else:
                    return func(val)
            self.add(Command(function=newFunc, **kwargs))
            return func
        return _decorator

# class MultiDevice(Device):
#     def __init__(self, name, devices, **kwargs):
#         super(name=name, **kwargs)

#         # First check that all devices are of same type
#         if len(set((d.__class__ for d in devices))) != 1:
#             raise Exception("Devices must all be of same class")

#         for v in devices[0].variables.values():
#             if v.mode == 'RW':
#                 self.add(LocalVariable.clone(v))

#         for locVar in self.variables.values():
#             depVars = [v for d in devices for v in d.variables.items() if v.name == locVar.name]


#             # Create a new set method that mirrors the set value out to all the dependent variables
#             def locSet(self, value, write=True):
#                 self.value = value
#                 for v in depVars:
#                     v.set(locVar.value, write)

#             # Monkey patch the new set method in to the local variable
#             locVar.setSetFunc(locSet)
            
#             def locGet(self, read=True):
#                 values = {v: v.get(read) for v in depVars}

#                 self.value = list(values.values())[0]
#                 if len(set(values)) != 1:
#                     raise Exception("MultiDevice variables do not match: {}".format(values))

#                 return self.value

#             locVar.setGetFunc(locGet)
            

class RootLogHandler(logging.Handler):
    """ Class to listen to log entries and add them to syslog variable"""
    def __init__(self,root):
        logging.Handler.__init__(self)
        self._root = root

    def emit(self,record):
        with self._root._sysLogLock:
            self._root.systemLog += (self.format(record) + '\n')

class Root(rogue.interfaces.stream.Master,Device):
    """
    Class which serves as the root of a tree of nodes.
    The root is the interface point for tree level access and updats.
    The root is a stream master which generates frames containing tree
    configuration and status values. This allows confiuration and status
    to be stored in data files.
    """

    def __init__(self, name, description, pollEn=True, **dump):
        """Init the node with passed attributes"""
        rogue.interfaces.stream.Master.__init__(self)

        
        # Create log listener to add to systemlog variable
        formatter = logging.Formatter("%(msg)s")
        handler = RootLogHandler(self)
        handler.setLevel(logging.ERROR)
        handler.setFormatter(formatter)
        self._logger = logging.getLogger('pyrogue')
        #self._logger.addHandler(handler)

        # Keep of list of errors, exposed as a variable
        self._sysLogLock = threading.Lock()

        # Polling
        if pollEn:
            self._pollQueue = PollQueue(self)
        else:
            self._pollQueue = None

        # Variable update list
        self._updatedDict = None
        self._updatedLock = threading.Lock()

        # Variable update listener
        self._varListeners = []

        #Can't init the device until _updatedLock exists.
        Device.__init__(self, name=name, description=description, classType='root')

        # Variables
        self.add(Variable(name='systemLog', value='', local=True, mode='RO',hidden=True,
            description='String containing newline seperated system logic entries'))


    def stop(self):
        """Stop the polling thread. Must be called for clean exit."""
        if self._pollQueue:
            self._pollQueue.stop()

    def addVarListener(self,func):
        """
        Add a variable update listener function.
        The function should accept a dictionary of update
        variables in both yaml and dict form:
            func(yaml,dict)
        """
        self._varListeners.append(func)

    def getYamlStructure(self):
        """Get structure as a yaml string"""
        return dictToYaml({self.name:self._getStructure()},default_flow_style=False)

    def getYamlVariables(self,readFirst,modes=['RW']):
        """
        Get current values as a yaml dictionary.
        modes is a list of variable modes to include.
        If readFirst=True a full read from hardware is performed.
        """
        ret = None

        if readFirst: self._read()
        try:
            ret = dictToYaml({self.name:self._getVariables(modes)},default_flow_style=False)
        except Exception as e:
            self._log.error(e)

        return ret

    def setOrExecYaml(self,yml,writeEach,modes=['RW']):
        """
        Set variable values or execute commands from a dictionary.
        modes is a list of variable modes to act on.
        writeEach is set to true if accessing a single variable at a time.
        Writes will be performed as each variable is updated. If set to 
        false a bulk write will be performed after all of the variable updates
        are completed. Bulk writes provide better performance when updating a large
        quanitty of variables.
        """
        d = yamlToDict(yml)

        self._initUpdatedVars()

        for key, value in d.items():
            if key == self.name:
                self._setOrExec(value,writeEach,modes)

        self._doneUpdatedVars()

        if not writeEach: self._write()

    def setOrExecPath(self,path,value):
        """
        Set variable values or execute commands from a dictionary.
        Pass the variable or command path and associated value or arg.
        """
        d = {}
        addPathToDict(d,path,value)
        name = path[:path.find('.')]
        yml = dictToYaml(d,default_flow_style=False)
        self.setOrExecYaml(yml,writeEach=True,modes=['RW'])

    def setTimeout(self,timeout):
        """
        Set timeout value on all devices & blocks
        """
        for key,value in self._nodes.items():
            if isinstance(value,Device):
                value._setTimeout(timeout)

    def _updateVarListeners(self, yml, d):
        """Send yaml and dict update to listeners"""
        for f in self._varListeners:
            f(yml,d)

    def _streamYaml(self,yml):
        """
        Generate a frame containing the passed yaml string.
        """
        frame = self._reqFrame(len(yml),True,0)
        b = bytearray(yml,'utf-8')
        frame.write(b,0)
        self._sendFrame(frame)

    def _streamYamlVariables(self,modes=['RW','RO']):
        """
        Generate a frame containing all variables values in yaml format.
        A hardware read is not generated before the frame is generated.
        Vlist can contain an optional list of variale paths to include in the
        stream. If this list is not NULL only these variables will be included.
        """
        self._streamYaml(self.getYamlVariables(False,modes))

    def _initUpdatedVars(self):
        """Initialize the update tracking log before a bulk variable update"""
        with self._updatedLock:
            self._updatedDict = odict()

    def _doneUpdatedVars(self):
        """Stream the results of a bulk variable update and update listeners"""
        with self._updatedLock:
            if self._updatedDict:
                yml = dictToYaml(self._updatedDict,default_flow_style=False)
                self._streamYaml(yml)
                self._updateVarListeners(yml,self._updatedDict)
            self._updatedDict = None


    @command(order=7, name='writeAll', description='Write all values to the hardware')
    def _write(self,dev=None,cmd=None,arg=None):
        """Write all blocks"""
        self._log.info("Start root write")
        try:
            self._backgroundTransaction(rogue.interfaces.memory.Write)
            self._log.info("Verify root read")
            self._backgroundTransaction(rogue.interfaces.memory.Verify)
            self._log.info("Check root read")
            self._checkTransaction(update=False)
        except Exception as e:
            self._log.error(e)
        self._log.info("Done root write")

    @command(order=6, name="readAll", description='Read all values from the hardware')
    def _read(self,dev=None,cmd=None,arg=None):
        """Read all blocks"""
        self._log.info("Start root read")
        self._initUpdatedVars()
        try:
            self._backgroundTransaction(rogue.interfaces.memory.Read)
            self._log.info("Check root read")
            self._checkTransaction(update=True)
        except Exception as e:
            self._log.error(e)
        self._doneUpdatedVars()
        self._log.info("Done root read")

    @command(order=0, name='writeConfig', base='string', description='Write configuration to passed filename in YAML format')
    def _writeConfig(self,dev,cmd,arg):
        """Write YAML configuration to a file. Called from command"""
        try:
            with open(arg,'w') as f:
                f.write(self.getYamlVariables(True,modes=['RW']))
        except Exception as e:
            self._log.error(e)

    @command(order=1, name='readConfig', base='string', description='Read configuration from passed filename in YAML format')
    def _readConfig(self,dev,cmd,arg):
        """Read YAML configuration from a file. Called from command"""
        try:
            with open(arg,'r') as f:
                self.setOrExecYaml(f.read(),False,['RW'])
        except Exception as e:
            self._log.error(e)

    @command(order=3, name='softReset', description='Generate a soft reset to each device in the tree')
    def _softReset(self,dev,cmd,arg):
        """Generate a soft reset on all devices"""
        self._devReset('soft')

    @command(order=2, name='hardReset', description='Generate a hard reset to each device in the tree')
    def _hardReset(self,dev,cmd,arg):
        """Generate a hard reset on all devices"""
        self._devReset('hard')
        self._clearLog(dev,cmd,arg)

    @command(order=4, name='countReset', description='Generate a count reset to each device in the tree')
    def _countReset(self,dev,cmd,arg):
        """Generate a count reset on all devices"""
        self._devReset('count')

    @command(order=5, name='clearLog', description='Clear the message log cntained in the systemLog variable')
    def _clearLog(self,dev,cmd,arg):
        """Clear the system log"""
        with self._sysLogLock:
            self.systemLog = ""

    def _varUpdated(self,var,value):
        """ Log updated variables"""
        yml = None

        with self._updatedLock:

            # Log is active add to log
            if self._updatedDict is not None:
                addPathToDict(self._updatedDict,var.path,value)

            # Otherwise act directly
            else:
                d = {}
                addPathToDict(d,var.path,value)
                yml = dictToYaml(d,default_flow_style=False)

        if yml:
            self._streamYaml(yml)
            self._updateVarListeners(yml,d)


class DataWriter(Device):
    """Special base class to control data files. TODO: Update comments"""

    def __init__(self, name, description='', hidden=False, **dump):
        """Initialize device class"""

        Device.__init__(self, name=name, description=description,
                        size=0, memBase=None, offset=0, hidden=hidden)

        self.classType    = 'dataWriter'

        self.add((
            Variable(name='dataFile', value='',
                          description='Data file for storing frames for connected streams.'),

            Variable(name='open', value=False, setFunction=self._setOpen,
                          description='Data file open state'),

            Variable(name='bufferSize', value=0, setFunction=self._setBufferSize,
                          description='File buffering size. Enables caching of data before call to file system.'),

            Variable(name='maxFileSize', value=0, setFunction=self._setMaxFileSize,
                          description='Maximum size for an individual file. Setting to a non zero splits the run data into multiple files.'),

            Variable(name='fileSize', value=0, mode='RO', pollInterval=1, getFunction=self._getFileSize,
                          description='Size of data files(s) for current open session in bytes.'),

            Variable(name='frameCount', value=0, mode='RO', pollInterval=1, getFrameCount=self._getFrameCount,
                          description='Frame in data file(s) for current open session in bytes.'),

            Command(name='autoName', function=self._genFileName,
                    description='Auto create data file name using data and time.')))

    def _setOpen(self,dev,var,value):
        """Set open state. Override in sub-class"""
        var.value = value

    def _setBufferSize(self,dev,var,value):
        """Set buffer size. Override in sub-class"""
        var.value = value

    def _setMaxFileSize(self,dev,var,value):
        """Set max file size. Override in sub-class"""
        var.value = value

    def _getFileSize(self,dev,cmd):
        """get current file size. Override in sub-class"""
        return(0)

    def _getFrameCount(self,dev,cmd):
        """get current file frame count. Override in sub-class"""
        return(0)

    def _genFileName(self,dev,cmd,arg):
        """
        Auto create data file name based upon date and time.
        Preserve file's location in path.
        """
        idx = self._dataFile.rfind('/')

        if idx < 0:
            base = ''
        else:
            base = self.dataFile.get()[:idx+1]

        self.dataFile = base + datetime.datetime.now().strftime("%Y%m%d_%H%M%S.dat") 

    def _backgroundTransaction(self,type):
        """Force update of non block status variables"""
        if type == rogue.interfaces.memory.Read:
            self.fileSize.get()
            self.frameCount.get()
        Device._backgroundTransaction(self,type)


class RunControl(Device):
    """Special base class to control runs. TODO: Update comments."""

    def __init__(self, name, description='', hidden=True, **dump):
        """Initialize device class"""

        Device.__init__(self, name=name, description=description,
                        size=0, memBase=None, offset=0, hidden=hidden)

        self.classType = 'runControl'

        self.add(Variable(name='runState', value=0, local=True, enum={0:'Stopped', 1:'Running'},
                          setFunction=self._setRunState, 
                          description='Run state of the system.'))

        self.add(Variable(name='runRate', value=1, local=True, enum={1:'1 Hz', 10:'10 Hz'},
                          setFunction=self._setRunRate, 
                          description='Run rate of the system.'))

        self.add(Variable(name='runCount', value=0, mode='RO', pollInterval=1,
                          local=True, setFunction=None, 
                          description='Run Counter updated by run thread.'))

    def _setRunState(self,dev,var,value):
        """
        Set run state. Reimplement in sub-class.
        Enum of run states can also be overriden.
        Underlying run control must update _runCount variable.
        """
        var.value = value

    def _setRunRate(self,dev,var,value):
        """
        Set run rate. Reimplement in sub-class.
        Enum of run rates can also be overriden.
        """
        var.value = value

    def _backgroundTransaction(self,type):
        """Force update of non block status variables"""
        if type == rogue.interfaces.memory.Read:
            self.runCount.get()
        Device._backgroundTransaction(self,type)


def addPathToDict(d, path, value):
    """Helper function to add a path/value pair to a dictionary tree"""
    npath = path
    sd = d

    # Transit through levels
    while '.' in npath:
        base  = npath[:npath.find('.')]
        npath = npath[npath.find('.')+1:]

        if base in sd:
           sd = sd[base]
        else:
           sd[base] = odict()
           sd = sd[base]

    # Add final node
    sd[npath] = value


def treeFromYaml(yml,setFunction,cmdFunction):
    """
    Create structure from yaml.
    """
    d = yamlToDict(yml)
    root = None

    for key, value in d.items():
        root = Root(pollEn=False,**value)
        root._addStructure(value,setFunction,cmdFunction)

    return root


def yamlToDict(stream, Loader=yaml.Loader, object_pairs_hook=odict):
    """Load yaml to ordered dictionary"""
    class OrderedLoader(Loader):
        pass
    def construct_mapping(loader, node):
        loader.flatten_mapping(node)
        return object_pairs_hook(loader.construct_pairs(node))
    OrderedLoader.add_constructor(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
        construct_mapping)
    return yaml.load(stream, OrderedLoader)


def dictToYaml(data, stream=None, Dumper=yaml.Dumper, **kwds):
    """Convert ordered dictionary to yaml"""
    class OrderedDumper(Dumper):
        pass
    def _dict_representer(dumper, data):
        return dumper.represent_mapping(
            yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,data.items())
    OrderedDumper.add_representer(odict, _dict_representer)
    return yaml.dump(data, stream, OrderedDumper, **kwds)

def setBitToBytes(ba, bitOffset, value):
    """
    Set a bit to a specific location in an array of bytes
    """
    byte = int(bitOffset / 8)
    bit  = bitOffset % 8

    if value > 0:
        ba[byte] |= (1 << bit)
    else:
        ba[byte] &= (0xFF ^ (1 << bit))

def getBitFromBytes(ba, bitOffset):
    """
    Get a bit from a specific location in an array of bytes
    """
    byte = int(bitOffset / 8)
    bit  = bitOffset % 8

    return ((ba[byte] >> bit) & 0x1)




class PollQueue(object):

    Entry = collections.namedtuple('PollQueueEntry', ['readTime', 'count', 'interval', 'block'])

    def __init__(self,root):
        self._pq = [] # The heap queue
        self._entries = {} # {Block/Variable: Entry} mapping to look up if a block is already in the queue
        self._counter = itertools.count()
        self._lock = threading.RLock()
        self._update = threading.Condition()
        self._run = True
        self._root = root
        self._pollThread = threading.Thread(target=self._poll)
        self._pollThread.start()

        # Setup logging
        self._log = logInit(self)

        self._log.info("PollQueue Started")

    def _addEntry(self, block, interval):
        with self._lock:
            timedelta = datetime.timedelta(seconds=interval)
            # new entries are always polled first immediately 
            # (rounded up to the next second)
            readTime = datetime.datetime.now()
            readTime = readTime.replace(microsecond=0)
            entry = PollQueue.Entry(readTime, next(self._counter), timedelta, block)
            self._entries[block] = entry
            heapq.heappush(self._pq, entry)
            # Wake up the thread
            with self._update:
                self._update.notify()            

    def updatePollInterval(self, var):
        with self._lock:
            self._log.debug('updatePollInterval {} - {}'.format(var, var.pollInterval))
            # Special case: Variable has no block and just depends on other variables
            # Then do update on each dependency instead
            if var._block is None:
                if len(var.dependencies) > 0:
                    for dep in var.dependencies:
                        if dep.pollInterval == 0 or var.pollInterval < dep.pollInterval:
                            dep.pollInterval = var.pollInterval

                else:
                    # Special case for variables without a block
                    # Add the variable itself
                    if var in self._entries.keys():
                        self._entries[var].block = None
                    self._addEntry(var, var.pollInterval)
                return
            
            if var._block in self._entries.keys():
                oldInterval = self._entries[var._block].interval
                blockVars = [v for v in var._block._variables if v.pollInterval > 0]
                if len(blockVars) > 0:
                    newInterval = min(blockVars, key=lambda x: x.pollInterval)
                    # If block interval has changed, invalidate the current entry for the block
                    # and re-add it with the new interval
                    if newInterval != oldInterval:
                        self._entries[var._block].block = None
                        self._addEntry(var._block, newInterval)
                else:
                    # No more variables belong to block entry, can remove it
                    self._entries[var._block].blocks = None
            else:
                # Pure entry add
                self._addEntry(var._block, var.pollInterval)
                     
    def _poll(self):
        """Run by the poll thread"""
        while True:
            now = datetime.datetime.now()

            if self.empty() is True:
                # Sleep until woken
                with self._update:
                    self._update.wait()
            else:
                # Sleep until the top entry is ready to be polled
                # Or a new entry is added by updatePollInterval
                readTime = self.peek().readTime
                waitTime = (readTime - now).total_seconds()
                with self._update:
                    self._log.debug('Poll thread sleeping for {}'.format(waitTime))
                    self._update.wait(waitTime)

            self._log.debug("Global reference count: %s" % (sys.getrefcount(None)))

            with self._lock:
                # Stop the thread if someone set run to False
                if self._run is False:
                    self._log.info("PollQueue thread exiting")
                    return

                # Start update capture
                self._root._initUpdatedVars()

                # Pop all timed out entries from the queue
                now = datetime.datetime.now()                
                blockEntries = []
                for entry in self._expiredEntries(now):
                    if isinstance(entry.block, Block):
                        self._log.debug('Polling {}'.format(entry.block._variables))
                        blockEntries.append(entry)
                        try:
                            entry.block._startTransaction(rogue.interfaces.memory.Read)
                        except Exception as e:
                            self._log.error(e)

                    else:
                        # Hack for handling local variables
                        self._log.debug('Polling {}'.format(entry.block))
                        entry.block.get(read=True)

                    # Update the entry with new read time
                    entry = entry._replace(readTime=(entry.readTime + entry.interval),
                                           count=next(self._counter))
                    # Push the updated entry back into the queue
                    heapq.heappush(self._pq, entry)

                try:
                    for entry in blockEntries:
                        entry.block._checkTransaction(update=True)
                except Exception as e:
                    self._log.error(e)
                # End update capture
                self._root._doneUpdatedVars()

    def _expiredEntries(self, time=None):
        """An iterator of all entries that expire by a given time. 
        Use datetime.now() if no time provided. Each entry is popped from the queue before being 
        yielded by the iterator
        """
        with self._lock:
            if time == None:
                time = datetime.datetime.now()
            while self.empty() is False and self.peek().readTime <= time:
                entry = heapq.heappop(self._pq)
                if entry.block is not None:
                    yield entry


    def peek(self):
        with self._lock:
            if self.empty() is False:
                return self._pq[0]
            else:
                return None

    def empty(self):
        with self._lock:
            return len(self._pq)==0

    def stop(self):
        with self._lock, self._update:
            self._run = False
            self._update.notify()

                    
