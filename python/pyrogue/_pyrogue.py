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
import heapq
from inspect import signature

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
        for i in xrange(number):
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

                # Set value if variable with enabled mode
                elif isinstance(self._nodes[key],Variable) and (self._nodes[key].mode in modes):
                    self._nodes[key].set(value,writeEach)

                # Execute if command
                elif isinstance(self._nodes[key],Command):
                    self._nodes[key](value)


class VariableError(Exception):
    """ Exception for variable access errors."""
    pass


class Base(object):
    """
    Class which defines how data is stored, displayed and converted.
    """
    def __init__(self):
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
                 base='hex', mode='RW', enum=None, units=None, hidden=False, minimum=None, maximum=None,
                 setFunction=None, getFunction=None, dependencies=None, 
                 beforeReadCmd=None, afterWriteCmd=None, **dump):
        """Initialize variable class""" 

        # Public Attributes
        self.offset    = offset
        self.bitSize   = bitSize
        self.bitOffset = bitOffset
        self.base      = base      
        self.mode      = mode
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
        Node.__init__(self, name=name, classType='variable', description=description, hidden=hidden, parent=parent)

    def _rootAttached(self):
        # Variables are always leaf nodes so no need to recurse
        if self._defaultValue is not None:
            self.set(self._defaultValue, write=True)
            
        if self._pollInterval > 0:
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
        if isinstance(self._root, Root):
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
            self._root._logException(e)

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
            self._root._logException(e)

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
            print("Got exception in get: %s" % (str(e)))
            self._root._logException(e)
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
                    return self.enum[ivalue]
                else:
                    return ivalue
        else:
            return None

    def linkUpdated(self, var, value):
        self._updated()


class Command(Variable):
    """Command holder: Subclass of variable with callable interface"""

    def __init__(self, parent=None, base='None', mode='CMD', function=None, **kwargs):

        Variable.__init__(self, base=base, mode=mode, parent=parent, **kwargs)

        self.classType = 'command'
        self._function = function if function is not None else Command.nothing

    def __call__(self,arg=None):
        """Execute command: TODO: Update comments"""
        try:
            if self._function is not None:

                # Function is really a function
                if callable(self._function):
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
            self._root._logException(e)

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
        self._value = "Error in block %s with address 0x%x: " % (block.name,block.address)

        if (self._error & 0xFF000000) == rogue.interfaces.memory.TimeoutError:
            self._value += "Timeout after %s seconds" % (block.timeout)

        elif (self._error & 0xFF000000) == rogue.interfaces.memory.VerifyError:
            self._value += "Verify error. Local=%s, Verify=%s, Mask=%s" % (block._bData,block._vData,block._mData)

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

    def __init__(self,device,variable):
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

        self._setSlave(self._device)
        self._addVariable(variable)

    def __repr__(self):
        return repr(self._variables)

    def set(self,bitOffset,bitCount,ba):
        """
        Update block with bitCount bits from passed byte array.
        Offset sets the starting point in the block array.
        """
        with self._cond:
            self._waitTransaction()

            # Access is fully byte aligned
            if (bitOffset % 8) == 0 and (bitCount % 8) == 0:
                self._bData[int(bitOffset/8):int((bitOffset+bitCount)/8)] = ba

            # Bit level access
            else:
                for x in range(0,bitCount):
                    setBitToBytes(self._bData,x+bitOffset,getBitFromBytes(ba,x))

    def get(self,bitOffset,bitCount):
        """
        Get bitCount bytes from block data.
        Offset sets the starting point in the block array.
        bytearray is returned
        """
        with self._cond:
            self._waitTransaction()

            # Error
            if self._error > 0:
                raise BlockError(self)

            # Access is fully byte aligned
            if (bitOffset % 8) == 0 and (bitCount % 8) == 0:
                return self._bData[int(bitOffset/8):int((bitOffset+bitCount)/8)]

            # Bit level access
            else:
                ba = bytearray(int(bitCount / 8))
                if (bitCount % 8) > 0: ba.extend(bytearray(1))
                for x in range(0,bitCount):
                    setBitToBytes(ba,x,getBitFromBytes(self._bData,x+bitOffset))
                return ba

    def setUInt(self,bitOffset,bitCount,value):
        """
        Set a uint. to be deprecated
        """
        bCount = (int)(bitCount / 8)
        if ( bitCount % 8 ) > 0: bCount += 1
        ba = bytearray(bCount)

        for x in range(0,bCount):
            ba[x] = (value >> (x*8)) & 0xFF

        self.set(bitOffset,bitCount,ba)

    def getUInt(self,bitOffset,bitCount):
        """
        Get a uint. to be deprecated
        """
        ba = self.get(bitOffset,bitCount)
        ret = 0

        for x in range(0,len(ba)):
            ret += (ba[x] << (x*8))

        return ret

    def setString(self,value):
        """
        Set a string. to be deprecated
        """
        ba = bytarray(value,'utf-8')
        ba.extend(bytearray(1))

        self.set(0,len(ba)*8,ba)

    def getString(self):
        """
        Get a string. to be deprecated
        """
        ba = self.get(0,self._size*8).rstrip(bytearray(1))
        return(ba.decode('utf-8'))

    def backgroundTransaction(self,type):
        """
        Perform a background transaction
        """
        self._startTransaction(type)

    def blockingTransaction(self,type):
        """
        Perform a blocking transaction
        """
        self._startTransaction(type)
        self._checkTransaction(update=False)

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
            self._cond.wait(self._timeout)
            if self._getId() == lid:
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
            if var.mode == 'RW':
                for x in range(var.bitOffset,var.bitOffset+var.bitSize):
                    setBitToBytes(self._mData,x,1)

    def _startTransaction(self,type):
        """
        Start a transaction.
        """
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
            if not self._device._enable:
                return

            # Setup transaction
            self._doVerify = (type == rogue.interfaces.memory.Verify)
            self._doUpdate = (type == rogue.interfaces.memory.Read)
            self._error    = 0

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

        print("Making device {:s}".format(name))

        # Hub.__init__ must be called first for _setSlave to work below
        rogue.interfaces.memory.Hub.__init__(self,offset)

        # Blocks
        self._blocks    = []
        self._enable    = enabled
        self._memBase   = memBase
        self._resetFunc = None
        self.expand     = expand

        # Connect to memory slave
        if memBase: self._setSlave(memBase)

        # Node.__init__ can't be called until after self._memBase is created
        Node.__init__(self, name=name, hidden=hidden, classType=classType, description=description, parent=parent)

        # Convenience methods
        self.addDevice = ft.partial(self.addNode, Device)
        self.addDevices = ft.partial(self.addNodes, Device)
        self.addVariable = ft.partial(self.addNode, Variable)        
        self.addVariables = ft.partial(self.addNodes, Variable)
        self.addCommand = ft.partial(self.addNode, Command)        
        self.addCommands = ft.partial(self.addNodes, Command)

        # Variable interface to enable flag
        self.add(Variable(name='enable', base='bool', mode='RW',
            setFunction=self._setEnable, getFunction='value=dev._enable',
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

        # Adding variable
        if isinstance(node,Variable) and node.offset is not None:
            if not any(block._addVariable(node) for block in self._blocks):
                self._blocks.append(Block(self,node))

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
        self._enable = enable

    def _backgroundTransaction(self,type):
        """
        Perform background transactions
        """
        if not self._enable: return

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
        if not self._enable: return

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


class Root(rogue.interfaces.stream.Master,Device):
    """
    Class which serves as the root of a tree of nodes.
    The root is the interface point for tree level access and updats.
    The root is a stream master which generates frames containing tree
    configuration and status values. This allows confiuration and status
    to be stored in data files.
    """

    def __init__(self, name, description, **dump):
        """Init the node with passed attributes"""

        rogue.interfaces.stream.Master.__init__(self)
        Device.__init__(self, name=name, description=description, classType='root')


        # Keep of list of errors, exposed as a variable
        self._systemLog = ""
        self._sysLogLock = threading.Lock()

        # Polling
        self._pollQueue = PollQueue()

        # Variable update list
        self._updatedDict = odict()
        self._updatedLock = threading.Lock()

        # Variable update listener
        self._varListeners = []

        # Variables
        self.add(Variable(name='systemLog', base='string', mode='RO',
            setFunction=None, getFunction='value=dev._systemLog',
            description='String containing newline seperated system logic entries'))


    def stop(self):
        """Stop the polling thread. Must be called for clean exit."""
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
            self._root._logException(e)

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
        try:
            self._backgroundTransaction(rogue.interfaces.memory.Write)
            self._backgroundTransaction(rogue.interfaces.memory.Verify)
            self._checkTransaction(update=False)
        except Exception as e:
            self._root._logException(e)

    @command(order=6, name="readAll", description='Read all values from the hardware')
    def _read(self,dev=None,cmd=None,arg=None):
        """Read all blocks"""
        self._initUpdatedVars()
        try:
            self._backgroundTransaction(rogue.interfaces.memory.Read)
            self._checkTransaction(update=True)
        except Exception as e:
            self._root._logException(e)
        self._doneUpdatedVars()

    @command(order=0, name='writeConfig', base='string', description='Write configuration to passed filename in YAML format')
    def _writeConfig(self,dev,cmd,arg):
        """Write YAML configuration to a file. Called from command"""
        try:
            with open(arg,'w') as f:
                f.write(self.getYamlVariables(True,modes=['RW']))
        except Exception as e:
            self._root._logException(e)

    @command(order=1, name='readConfig', base='string', description='Read configuration from passed filename in YAML format')
    def _readConfig(self,dev,cmd,arg):
        """Read YAML configuration from a file. Called from command"""
        try:
            with open(arg,'r') as f:
                self.setOrExecYaml(f.read(),False,['RW'])
        except Exception as e:
            self._root._logException(e)
            
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
            self._systemLog = ""
        self.systemLog._updated()

    def _logException(self,exception):
        """Add an exception to the log"""
        #traceback.print_exc(limit=1)
        traceback.print_exc()
        self._addToLog(str(exception))

    def _addToLog(self,string):
        """Add an string to the log"""
        with self._sysLogLock:
            self._systemLog += string
            self._systemLog += '\n'

        self.systemLog._updated()

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
        self._open        = False
        self._dataFile    = ''
        self._bufferSize  = 0
        self._maxFileSize = 0

        self.add(Variable(name='dataFile', base='string', mode='RW',
            setFunction='dev._dataFile = value', getFunction='value = dev._dataFile',
            description='Data file for storing frames for connected streams.'))

        self.add(Variable(name='open', base='bool', mode='RW',
            setFunction=self._setOpen, getFunction='value = dev._open',
            description='Data file open state'))

        self.add(Variable(name='bufferSize', base='uint', mode='RW',
            setFunction=self._setBufferSize, getFunction='value = dev._bufferSize',
            description='File buffering size. Enables caching of data before call to file system.'))

        self.add(Variable(name='maxFileSize', base='uint', mode='RW',
            setFunction=self._setMaxFileSize, getFunction='value = dev._maxFileSize',
            description='Maximum size for an individual file. Setting to a non zero splits the run data into multiple files.'))

        self.add(Variable(name='fileSize', base='uint', mode='RO', pollInterval=1,
                          setFunction=None, getFunction=self._getFileSize,
                          description='Size of data files(s) for current open session in bytes.'))

        self.add(Variable(name='frameCount', base='uint', mode='RO', pollInterval=1,
            setFunction=None, getFunction=self._getFrameCount,
            description='Frame in data file(s) for current open session in bytes.'))

        self.add(Command(name='autoName', function=self._genFileName,
            description='Auto create data file name using data and time.'))

    def _setOpen(self,dev,var,value):
        """Set open state. Override in sub-class"""
        self._open = value

    def _setBufferSize(self,dev,var,value):
        """Set buffer size. Override in sub-class"""
        self._bufferSize = value

    def _setMaxFileSize(self,dev,var,value):
        """Set max file size. Override in sub-class"""
        self._maxFileSize = value

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
            base = self._dataFile[:idx+1]

        self._dataFile = base
        self._dataFile += datetime.datetime.now().strftime("%Y%m%d_%H%M%S.dat") 
        self.dataFile._updated()

    def _backgroundTransaction(self,type):
        """Force update of non block status variables"""
        if type == rogue.interfaces.memory.Read:
            self.fileSize.get()
            self.frameCount.get()
        Device._backgroundTransaction(self,type)


class RunControl(Device):
    """Special base class to control runs. TODO: Update comments."""

    def __init__(self, name, description='', hidden=False, **dump):
        """Initialize device class"""

        Device.__init__(self, name=name, description=description,
                        size=0, memBase=None, offset=0, hidden=hidden)

        self.classType = 'runControl'
        self._runState = 'Stopped'
        self._runCount = 0
        self._runRate  = '1 Hz'

        self.add(Variable(name='runState', base='enum', mode='RW', enum={0:'Stopped', 1:'Running'},
            setFunction=self._setRunState, getFunction='value = dev._runState',
            description='Run state of the system.'))

        self.add(Variable(name='runRate', base='enum', mode='RW', enum={1:'1 Hz', 10:'10 Hz'},
            setFunction=self._setRunRate, getFunction='value = dev._runRate',
            description='Run rate of the system.'))

        self.add(Variable(name='runCount', base='uint', mode='RO', pollInterval=1,
            setFunction=None, getFunction='value = dev._runCount',
            description='Run Counter updated by run thread.'))

    def _setRunState(self,dev,var,value):
        """
        Set run state. Reimplement in sub-class.
        Enum of run states can also be overriden.
        Underlying run control must update _runCount variable.
        """
        self._runState = value

    def _setRunRate(self,dev,var,value):
        """
        Set run rate. Reimplement in sub-class.
        Enum of run rates can also be overriden.
        """
        self._runRate = value

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
        root = Root(**value)
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

    def __init__(self):
        self._pq = [] # The heap queue
        self._entries = {} # {Block/Variable: Entry} mapping to look up if a block is already in the queue
        self._counter = itertools.count()
        self._lock = threading.RLock()
        self._update = threading.Condition()
        self._run = True
        self._pollThread = threading.Thread(target=self._poll)
        self._pollThread.start()
        print("PollQueue Started")

    def _addEntry(self, block, interval):
        with self._lock:
            timedelta = datetime.timedelta(seconds=interval)
            # new entries are always polled first immediately 
            # (rounded up to the next second)
            readTime = datetime.datetime.now()
            readTime = readTime.replace(second=readTime.second+1, microsecond=0)
            entry = PollQueue.Entry(readTime, next(self._counter), timedelta, block)
            self._entries[block] = entry
            heapq.heappush(self._pq, entry)
            # Wake up the thread
            with self._update:
                self._update.notify()            

    def updatePollInterval(self, var):
        with self._lock:
            #print('updatePollInterval {} - {}'.format(var, var.pollInterval))
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
                    #print('Poll thread sleeping for {}'.format(waitTime))
                    self._update.wait(waitTime)
                
            with self._lock:
                # Stop the thread if someone set run to False
                if self._run is False:
                    print("PollQueue thread exiting")
                    return

                # Pop all timed out entries from the queue
                now = datetime.datetime.now()                
                blockEntries = []
                for entry in self._expiredEntries(now):
                    if isinstance(entry.block, Block):
                        #print('Polling {}'.format(entry.block._variables))
                        blockEntries.append(entry)
                        entry.block._startTransaction(rogue.interfaces.memory.Read)
                    else:
                        # Hack for handling local variables
                        #print('Polling {}'.format(entry.block))
                        entry.block.get(read=True)
                        
                    # Update the entry with new read time
                    entry = entry._replace(readTime=(entry.readTime + entry.interval),
                                           count=next(self._counter))
                    # Push the updated entry back into the queue
                    heapq.heappush(self._pq, entry)


                # Wait for reads to be done
                for entry in blockEntries:
                    entry.block._checkTransaction(update=True)

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

                    
