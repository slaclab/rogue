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
import math
import collections
import datetime
import traceback

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


class VariableError(Exception):
    """ Exception for variable access errors."""
    pass


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

    def __init__(self, name, classType, description="", hidden=False):
        """Init the node with passed attributes"""

        # Public attributes
        self.name        = name     
        self.description = description
        self.hidden      = hidden
        self.classType   = classType
        self.path        = self.name

        # Tracking
        self._parent = None
        self._root   = self
        self._nodes  = collections.OrderedDict()

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

    def getNodes(self,typ=None):
        """
        Get a ordered dictionary of nodes.
        pass a class type to receive a certain type of node
        """
        if typ:
            ret = collections.OrderedDict()
            for key,node in self._nodes.iteritems():
                if isinstance(node,typ):
                    ret[key] = node
            return ret
        else:
            return self._nodes

    def getParent(self):
        """
        Return parent node or NULL if no parent exists.
        """
        return self._parent

    def getRoot(self):
        """
        Return root node of tree.
        """
        return self._root

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

        for key,value in self._nodes.iteritems():
            value._updateTree(self)

    def _getStructure(self):
        """
        Get structure starting from this level.
        Attributes that are Nodes are recursed.
        Called from getYamlStructure in the root node.
        """
        data = collections.OrderedDict()

        # First get non-node local values
        for key,value in self.__dict__.iteritems():
            if (not key.startswith('_')) and (not isinstance(value,Node)):
                data[key] = value

        # Next get sub nodes
        for key,value in self.getNodes().iteritems():
            data[key] = value._getStructure()

        return data

    def _addStructure(self,d,setFunction,cmdFunction):
        """
        Creation structure from passed dictionary. Used for clients.
        Blocks are not created and functions are set to the passed values.
        """
        for key, value in d.iteritems():

            # Only work on nodes
            if isinstance(value,dict) and value.has_key('classType'):

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
        data = collections.OrderedDict()
        for key,value in self._nodes.iteritems():
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
        for key, value in d.iteritems():

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


class Root(rogue.interfaces.stream.Master,Node):
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
        Node.__init__(self, name=name, classType='root', description=description, hidden=False)

        # Polling period. Set to None to exit. 0 = don't poll
        self._pollPeriod = 0

        # Keep of list of errors, exposed as a variable
        self._systemLog = ""
        self._sysLogLock = threading.Lock()

        # Add poller
        self._pollThread = None

        # Variable update list
        self._updatedDict = collections.OrderedDict()
        self._updatedLock = threading.Lock()

        # Variable update listener
        self._varListeners = []

        # Commands

        self.add(Command(name='writeConfig', base='string', function=self._writeConfig,
            description='Write configuration to passed filename in YAML format'))

        self.add(Command(name='readConfig', base='string', function=self._readConfig,
            description='Read configuration from passed filename in YAML format'))

        self.add(Command(name='hardReset', base='None', function=self._hardReset,
            description='Generate a hard reset to each device in the tree'))

        self.add(Command(name='softReset', base='None', function=self._softReset,
            description='Generate a soft reset to each device in the tree'))

        self.add(Command(name='countReset', base='None', function=self._countReset,
            description='Generate a count reset to each device in the tree'))

        self.add(Command(name='clearLog', base='None', function=self._clearLog,
            description='Clear the message log cntained in the systemLog variable'))

        self.add(Command(name='readAll', base='None', function=self._read,
            description='Read all values from the hardware'))

        self.add(Command(name='writeAll', base='None', function=self._write,
            description='Write wll values to the hardware'))

        # Variables

        self.add(Variable(name='systemLog', base='string', mode='RO',
            setFunction=None, getFunction='value=dev._systemLog',
            description='String containing newline seperated system logic entries'))

        self.add(Variable(name='pollPeriod', base='float', mode='RW',
            setFunction=self._setPollPeriod, getFunction='value=dev._pollPeriod',
            description='Polling period for pollable variables. Set to 0 to disable polling'))

    def stop(self):
        """Stop the polling thread. Must be called for clean exit."""
        self._pollPeriod=0

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

        for key, value in d.iteritems():
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
        for key,value in self._nodes.iteritems():
            if isinstance(value,Device):
                value._setTimeout(timeout)

    def _updateVarListeners(self, yml, d):
        """Send yaml and dict update to listeners"""
        for f in self._varListeners:
            f(yml,d)

    def _setPollPeriod(self,dev,var,value):
        """Set poller period"""
        old = self._pollPeriod
        self._pollPeriod = value

        # Start thread
        if old == 0 and value != 0:
            self._pollThread = threading.Thread(target=self._runPoll)
            self._pollThread.start()

        # Stop thread
        elif old != 0 and value == 0:
            self._pollThread.join()
            self._pollThread = None

    def _runPoll(self):
        """Polling function"""
        while(self._pollPeriod != 0):
            time.sleep(self._pollPeriod)
            self._poll()

    def _streamYaml(self,yml):
        """
        Generate a frame containing the passed yaml string.
        """
        frame = self._reqFrame(len(yml),True,0)
        b = bytearray()
        b.extend(yml)
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
            self._updatedDict = collections.OrderedDict()

    def _doneUpdatedVars(self):
        """Stream the results of a bulk variable update and update listeners"""
        with self._updatedLock:
            if self._updatedDict:
                yml = dictToYaml(self._updatedDict,default_flow_style=False)
                self._streamYaml(yml)
                self._updateVarListeners(yml,self._updatedDict)
            self._updatedDict = None


    def _write(self,dev=None,cmd=None,arg=None):
        """Write all blocks"""

        try:
            for key,value in self._nodes.iteritems():
                if isinstance(value,Device):
                    value._write()
            for key,value in self._nodes.iteritems():
                if isinstance(value,Device):
                    value._verify()
            for key,value in self._nodes.iteritems():
                if isinstance(value,Device):
                    value._check()
        except Exception as e:
            self._root._logException(e)

    def _read(self,dev=None,cmd=None,arg=None):
        """Read all blocks"""

        self._initUpdatedVars()

        try:
            for key,value in self._nodes.iteritems():
                if isinstance(value,Device):
                    value._read()
            for key,value in self._nodes.iteritems():
                if isinstance(value,Device):
                    value._check()
        except Exception as e:
            self._root._logException(e)

        self._doneUpdatedVars()

    def _poll(self):
        """Read pollable blocks"""

        self._initUpdatedVars()

        try:
            for key,value in self._nodes.iteritems():
                if isinstance(value,Device):
                    value._poll()
            for key,value in self._nodes.iteritems():
                if isinstance(value,Device):
                    value._check()
        except Exception as e:
            self._root._logException(e)

        self._doneUpdatedVars()

    def _writeConfig(self,dev,cmd,arg):
        """Write YAML configuration to a file. Called from command"""
        try:
            with open(arg,'w') as f:
                f.write(self.getYamlVariables(True,modes=['RW']))
        except Exception as e:
            self._root._logException(e)

    def _readConfig(self,dev,cmd,arg):
        """Read YAML configuration from a file. Called from command"""
        try:
            with open(arg,'r') as f:
                self.setOrExecYaml(f.read(),False,['RW'])
        except Exception as e:
            self._root._logException(e)

    def _softReset(self,dev,cmd,arg):
        """Generate a soft reset on all devices"""
        for key,value in self._nodes.iteritems():
            if isinstance(value,Device):
                value._devReset('soft')

    def _hardReset(self,dev,cmd,arg):
        """Generate a hard reset on all devices"""
        for key,value in self._nodes.iteritems():
            if isinstance(value,Device):
                value._devReset('hard')
        self._clearLog(dev,cmd,arg)

    def _countReset(self,dev,cmd,arg):
        """Generate a count reset on all devices"""
        for key,value in self._nodes.iteritems():
            if isinstance(value,Device):
                value._devReset('count')

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
    pollEn: Set to true to enable polling of the associated memory.
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
    def __init__(self, name, description="", offset=None, bitSize=32, bitOffset=0, pollEn=False,
                 base='hex', mode='RW', enum=None, units=None, hidden=False, minimum=None, maximum=None,
                 setFunction=None, getFunction=None, dependencies=None, **dump):
        """Initialize variable class"""

        Node.__init__(self, name=name, classType='variable', description=description, hidden=hidden)

        # Public Attributes
        self.offset    = offset
        self.bitSize   = bitSize
        self.bitOffset = bitOffset
        self.pollEn    = pollEn
        self.base      = base      
        self.mode      = mode
        self.enum      = enum
        self.units     = units
        self.minimum   = minimum # For base='range'
        self.maximum   = maximum # For base='range'


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

        self.setDependencies(dependencies)

    def __repr__(self):
        return self.name

    def setDependencies(self, deps):
        self.dependencies = deps        
        if deps is not None:
            for d in deps:
                d.addListener(self)
        

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

    def set(self,value,write=True):
        """
        Set the value and write to hardware if applicable
        Writes to hardware are blocking. An error will result in a logged exception.
        """
        try:
            self._rawSet(value)
            
            if write and self._block and self._block.mode != 'RO':
                self._block.blockingWrite()
                self._parent._afterWrite()

                if self._block.mode == 'RW':
                   self._parent._beforeVerify()
                   self._block.blockingVerify()
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
                self._block.postedWrite()
        except Exception as e:
            self._root._logException(e)

    def get(self,read=True):
        """ 
        Return the value after performing a read from hardware if applicable.
        Hardware read is blocking. An error will result in a logged exception.
        Listeners will be informed of the update.
        """
        if read:
            print "{:s}.read(True)".format(self.name)
            
        try:
            if read and self._block and self._block.mode != 'WO':
                self._parent._beforeRead()
                self._block.blockingRead()
            ret = self._rawGet()
        except Exception as e:
            self._root._logException(e)
            return None

        # Update listeners for all variables in the block
        if read:
            if self._block:
                self._block._updated()
            else:
                self._updated()
        return ret

    def getBlock(self):
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

    def _setRawUInt(self, value):
        self._block.setUInt(self.bitOffset, self.bitSize, value)        

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
                    ivalue = {value: key for key,value in self.enum.iteritems()}[value]
                else:
                    ivalue = int(value)
                self._setRawUInt(ivalue)

        # Inform listeners
        self._updated()

    def _getRawUInt(self):
        return self._block.getUInt(self.bitOffset,self.bitSize)
                
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
                value = None
                dev = self._parent
                exec(textwrap.dedent(self._getFunction))
                return value

        elif self._block:        
            if self.base == 'string':
                return(self._block.getString())
            else:
                ivalue = self._getRawUInt()

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

    def __init__(self, name, description, base='None', function=None, hidden=False, 
                 enum=None, minimum=None, maximum=None, offset=None, bitSize=32, bitOffset=0, **dump):

        Variable.__init__(self, name=name, description=description, offset=offset, bitSize=bitSize,
                          bitOffset=bitOffset, pollEn=False, base=base, mode='CMD', enum=enum,
                          hidden=hidden, minimum=minimum, maximum=maximum, setFunction=None, getFunction=None)

        self.classType = 'command'
        self._function = function

    def __call__(self,arg=None):
        """Execute command: TODO: Update comments"""
        try:
            if self._function is not None:

                # Function is really a function
                if callable(self._function):
                    self._function(self._parent,self,arg)

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
                                n.set(value)

                # Attempt to execute string as a python script
                else:
                    dev = self._parent
                    exec(textwrap.dedent(self._function))

        except Exception as e:
            self._root._logException(e)

    def toggle(dev, cmd, arg):
        cmd.set(1)
        cmd.set(0)

    def touch(dev, cmd, arg):
        if arg is not None:
            cmd.set(arg)
        else:
            cmd.set(1)

    def postedTouch(dev, cmd, arg):
        if arg is not None:
            cmd.post(arg)
        else:
            cmd.post(1)


class Block(rogue.interfaces.memory.Block):
    """Internal memory block holder"""

    def __init__(self,offset,size):
        """Initialize memory block class"""
        rogue.interfaces.memory.Block.__init__(self,offset,size)

        # Attributes
        self.offset    = offset # track locally because memory::Block address is global
        self.variables = []
        self.pollEn    = False
        self.mode      = ''

    def _check(self):
        if self.getUpdated(): # Throws exception if error
            self._updated()

    def _updated(self):
        for variable in self.variables:
            variable._updated()


class Device(Node,rogue.interfaces.memory.Hub):
    """Device class holder. TODO: Update comments"""

    def __init__(self, name=None, description="", memBase=None, offset=0, hidden=False, variables=None, expand=True, enabled=True, **dump):
        """Initialize device class"""
        if name is None:
            name = self.__class__.__name__

        print("Making device {:s}".format(name))

        Node.__init__(self, name=name, hidden=hidden, classType='device', description=description)
        rogue.interfaces.memory.Hub.__init__(self,offset)

        # Blocks
        self._blocks    = []
        self._enable    = enabled
        self._memBase   = memBase
        self._resetFunc = None
        self.expand     = expand

        # Connect to memory slave
        if memBase: self._setSlave(memBase)

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
                    

    def add(self,node):
        """
        Add node as sub-node in the object
        Device specific implementation to add blocks as required.
        """

        # Special case if list (or iterable of nodes) is passed
        if isinstance(node, collections.Iterable) and all(isinstance(n, Node) for n in nodes):
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
            varBytes = int(math.ceil(float(node.bitOffset + node.bitSize) / 8.0))

            # First find if and existing block matches
            vblock = None
            for block in self._blocks:
                if node.offset == block.offset:
                    vblock = block

            # Create new block if not found
            if vblock is None:
                vblock = Block(node.offset,varBytes)
                vblock._setSlave(self)
                self._blocks.append(vblock)

            # Do association
            node._block = vblock
            vblock.variables.append(node)

            if node.pollEn: 
                vblock.pollEn = True

            if vblock.mode == '': 
                vblock.mode = node.mode
            elif vblock.mode != node.mode:
                vblock.mode = 'RW'

            # Adjust size to hold variable. Underlying class will adjust
            # size to align to minimum protocol access size 
            if vblock.getSize() < varBytes:
               vblock._setSize(varBytes)

            # Update verify mask
            if node.mode == 'RW':
               vblock.addVerify(node.bitOffset,node.bitSize)

    def setResetFunc(self,func):
        """
        Set function for count, hard or soft reset
        resetFunc(type) 
        where type = 'soft','hard','count'
        """
        self._resetFunc = func

    def _beforeRead(self):
        pass

    def _beforeVerify(self):
        pass

    def _afterWrite(self):
        pass

    def _setEnable(self, dev, var, enable):
        """
        Method to update enable in underlying block.
        May be re-implemented in some sub-class to 
        propogate enable to leaf nodes in the tree.
        """
        self._enable = enable

        for block in self._blocks:
            block.setEnable(enable)

    def _write(self):
        """ Write all blocks. """
        if not self._enable: return

        # Process local blocks
        for block in self._blocks:
            if block.mode == 'WO' or block.mode == 'RW':
                block.backgroundWrite()

        # Process rest of tree
        for key,value in self._nodes.iteritems():
            if isinstance(value,Device):
                value._write()

        # Post write function for special cases
        self._afterWrite()

    def _verify(self):
        """ Verify all blocks. """
        if not self._enable: return

        # Post write function for special cases
        self._beforeVerify()

        # Process local blocks
        for block in self._blocks:
            if block.mode == 'WO' or block.mode == 'RW':
                block.backgroundVerify()

        # Process reset of tree
        for key,value in self._nodes.iteritems():
            if isinstance(value,Device):
                value._verify()

    def _read(self):
        """Read all blocks"""
        if not self._enable: return

        # Post write function for special cases
        self._beforeRead()

        # Process local blocks
        for block in self._blocks:
            if block.mode == 'RO' or block.mode == 'RW':
                block.backgroundRead()

        # Process rest of tree
        for key,value in self._nodes.iteritems():
            if isinstance(value,Device):
                value._read()

    def _poll(self):
        """Read pollable blocks"""
        if not self._enable: return

        # Process local blocks
        for block in self._blocks:
            if block.pollEn and (block.mode == 'RO' or block.mode == 'RW'):
                block.backgroundRead()

        # Process rest of tree
        for key,value in self._nodes.iteritems():
            if isinstance(value,Device):
                value._poll()

    def _check(self):
        """Check errors in all blocks and generate variable update nofifications"""
        if not self._enable: return

        # Process local blocks
        for block in self._blocks:
            block._check()

        # Process rest of tree
        for key,value in self._nodes.iteritems():
            if isinstance(value,Device):
                value._check()

    def _devReset(self,rstType):
        """Generate a count, soft or hard reset"""
        if callable(self._resetFunc):
            self._resetFunc(self,rstType)

        # process remaining blocks
        for key,value in self._nodes.iteritems():
            if isinstance(value,Device):
                value._devReset(rstType)

    def _hardReset(self):
        self._resetFunc(self, "hard")

    def _softReset(self):
        self._resetFunc(self, "soft")

    def _countReset(self):
        self._resetFunc(self, "count")

    def _setTimeout(self,timeout):
        """
        Set timeout value on all devices & blocks
        """

        for block in self._blocks:
            block.setTimeout(timeout)

        for key,value in self._nodes.iteritems():
            if isinstance(value,Device):
                value._setTimeout(timeout)


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

        self.add(Variable(name='fileSize', base='uint', mode='RO',
            setFunction=None, getFunction=self._getFileSize,
            description='Size of data files(s) for current open session in bytes.'))

        self.add(Variable(name='frameCount', base='uint', mode='RO',
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

    def _read(self):
        """Force update of non block status variables"""
        self.fileSize.get()
        self.frameCount.get()
        Device._read(self)

    def _poll(self):
        """Force update of non block status variables"""
        self.fileSize.get()
        self.frameCount.get()
        Device._poll(self)


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

        self.add(Variable(name='runCount', base='uint', mode='RO',
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

    def _read(self):
        """Force update of non block status variables"""
        self.runCount.get()
        Device._read(self)

    def _poll(self):
        """Force update of non block status variables"""
        self.runCount.get()
        Device._poll(self)


def addPathToDict(d, path, value):
    """Helper function to add a path/value pair to a dictionary tree"""
    npath = path
    sd = d

    # Transit through levels
    while '.' in npath:
        base  = npath[:npath.find('.')]
        npath = npath[npath.find('.')+1:]

        if sd.has_key(base):
           sd = sd[base]
        else:
           sd[base] = collections.OrderedDict()
           sd = sd[base]

    # Add final node
    sd[npath] = value


def treeFromYaml(yml,setFunction,cmdFunction):
    """
    Create structure from yaml.
    """
    d = yamlToDict(yml)
    root = None

    for key, value in d.iteritems():
        root = Root(**value)
        root._addStructure(value,setFunction,cmdFunction)

    return root


def yamlToDict(stream, Loader=yaml.Loader, object_pairs_hook=collections.OrderedDict):
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
    OrderedDumper.add_representer(collections.OrderedDict, _dict_representer)
    return yaml.dump(data, stream, OrderedDumper, **kwds)

