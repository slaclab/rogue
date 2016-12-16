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
        self._nodes  = odict()

    def __repr__(self):
        return self.path

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

    def _getNodes(self,typ):
        """
        Get a ordered dictionary of nodes.
        pass a class type to receive a certain type of node
        """
        return odict([(k,n) for k,n in self._nodes.iteritems() if isinstance(n, typ)])

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
        return odict([(k,n) for k,n in self._nodes.iteritems()
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
        data = odict()

        # First get non-node local values
        for key,value in self.__dict__.iteritems():
            if (not key.startswith('_')) and (not isinstance(value,Node)):
                data[key] = value

        # Next get sub nodes
        for key,value in self.nodes.iteritems():
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
        data = odict()
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
        self._updatedDict = odict()
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
            self._updatedDict = odict()

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
                    value._check(update=False)
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
                    value._check(update=True)
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
                    value._check(update=True)
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
                 setFunction=None, getFunction=None, dependencies=None,               
                 beforeReadCmd=None, afterWriteCmd=None, beforeVerifyCmd=None, **dump):
 
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

        # Dependency tracking
        self.__dependencies = []
        if dependencies is not None:
            for d in dependencies:
                self.addDependency(d)

        # Commands that run before or after block access
        self._beforeReadCmd   = beforeReadCmd
        self._afterWriteCmd   = afterWriteCmd
                

    def addDependency(self, dep):
        self.__dependencies.append(dep)
        dep.addListener(self)

    @property
    def dependencies(self):
        return self.__dependencies[:]
    
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
                self._block.blockingWrite()
                if self._afterWriteCmd is not None:
                    self._afterWriteCmd()

                if self._block.mode == 'RW':
                    if self._beforeReadCmd is not None:
                        self._beforeReadCmd()
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
                if self._beforeReadCmd is not None:
                    self._beforeReadCmd()
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
                    ivalue = {value: key for key,value in self.enum.iteritems()}[value]
                else:
                    ivalue = int(value)
                self._block.setUInt(self.bitOffset, self.bitSize, value)        

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
                value = None
                dev = self._parent
                exec(textwrap.dedent(self._getFunction))
                return value

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

    def __init__(self, name, description, base='None', function=None, hidden=False, 
                 enum=None, minimum=None, maximum=None, offset=None, bitSize=32, bitOffset=0, **dump):

        Variable.__init__(self, name=name, description=description, offset=offset, bitSize=bitSize,
                          bitOffset=bitOffset, pollEn=False, base=base, mode='CMD', enum=enum,
                          hidden=hidden, minimum=minimum, maximum=maximum, setFunction=None, getFunction=None)

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

BLANK_COMMAND = Command(name='Blank', description='A singleton command that does nothing')


class BlockError(Exception):
    """ Exception for memory access errors."""

    def __init__(self,block):
        self._error = block.error
        self._value = "Error in block %s with address 0x%x: " % (block.name,block.address)

        if (self._error & 0xFF000000) == rogue.interfaces.memory.TimeoutError:
            self._value += "Timeout after %s seconds" % (block.timeout)

        elif (self._error & 0xFF000000) == rogue.interfaces.memory.VerifyError:
            self._value += "Verify error"

        elif (self._error & 0xFF000000) == rogue.interfaces.memory.AddressError:
            self._value += "Address error"

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
        self._pollEn    = variable.pollEn
        self._bData     = bytearray()
        self._vData     = bytearray()
        self._mData     = bytearray()
        self._size      = 0
        self._variables = []
        self._timeout   = 1.0
        self._enable    = True
        self._lock      = threading.Lock()
        self._cond      = threading.Condition(self._lock)
        self._error     = 0
        self._doUpdate  = False
        self._doVerify  = False

        self._setSlave(device)
        self._addVariable(variable)

    def set(self,bitOffset,bitCount,ba):
        """
        Update block with bitCount bits from passed byte array.
        Offset sets the starting point in the block array.
        """
        with self._cond:
            self._waitWhileBusy()

            # Access is fully byte aligned
            if (bitOffset % 8) == 0 and (bitCount % 8) == 0:
                self._bData[bitOffset/8:(bitOffset+bitCount)/8] = ba

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
            self._waitWhileBusy()

            # Access is fully byte aligned
            if (bitOffset % 8) == 0 and (bitCount % 8) == 0:
                return self._bData[bitOffset/8:(bitOffset+bitCount)/8]

            # Bit level access
            else:
                ba = bytearray(bitCount / 8)
                if (bitCount % 8) > 0: ba.extend(bytearray(1))
                for x in range(0,bitCount):
                    setBitToBytes(ba,x,getBitFromBytes(self._bData,x+bitOffset))
                return ba

    def setUInt(self,bitOffset,bitCount,value):
        """
        Set a uint. to be deprecated
        """
        bCount = bitCount / 8
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
        ba = bytarray(value)
        ba.extend(bytearray(1))

        self.set(0,len(ba)*8,ba)

    def getString(self):
        """
        Get a string. to be deprecated
        """
        ba = self.get(0,self._size)

        ba.rstrip('\0')
        return str(ba)

    def backgroundRead(self):
        """
        Perform a background read. 
        """
        self._startTransaction(write=False,posted=False,verify=False)

    def blockingRead(self):
        """
        Perform a foreground read. 
        """
        self._startTransaction(write=False,posted=False,verify=False)
        self._check(update=False)

    def backgroundWrite(self):
        """
        Perform a background write.
        """
        self._startTransaction(write=True,posted=False,verify=False)

    def blockingWrite(self):
        """
        Perform a foreground write.
        """
        self._startTransaction(write=True,posted=False,verify=False)
        self._check(update=False)

    def postedWrite(self):
        """
        Perform a posted write.
        """
        self._startTransaction(write=True,posted=True,verify=False)

    def backgroundVerify(self):
        """
        Perform a background verify.
        """
        self._startTransaction(write=False,posted=False,verify=True)

    def blockingVerify(self):
        """
        Perform a foreground verify.
        """
        self._startTransaction(write=False,posted=False,verify=True)
        self._check(update=False)

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
    def pollEn(self):
        return self._pollEn

    @property
    def timeout(self):
        return self._timeout

    @timeout.setter
    def timeout(self,value):
        with self._cond:
            self._waitWhileBusy()
            self._timeout = value

    @property
    def enable(self):
        return self._enable

    @enable.setter
    def enable(self,value):
        with self._cond:
            self._waitWhileBusy()
            self._enable = value

    @property
    def error(self):
        return self._error

    def _waitWhileBusy(self):
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
            self._waitWhileBusy()

            # Return false if offset does not match
            if var.offset != self._offset:
                return False

            # Compute the max variable address to determine required size of block
            varBytes = int(math.ceil(float(var.bitOffset + var.bitSize) / 8.0))

            # Link variable to block
            var._block = self
            self._variables.append(var)

            # Update polling, set true if any variable have poll enable set
            if var.pollEn:
                self._pollEn = True

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

    def _startTransaction(self,write,posted,verify):
        """
        Start a transaction.
        """
        minSize = self._reqMinAccess()
        tData = None

        with self._cond:
            self._waitWhileBusy()

            # Adjust size if required
            if (self._size % minSize) > 0:
                newSize = ((self._size / minSize) + 1) * minSize
                self._bData.extend(bytearray(newSize - self._size))
                self._vData.extend(bytearray(newSize - self._size))
                self._mData.extend(bytearray(newSize - self._size))
                self._size = newSize

            # Return if not enabled
            if not self._enable:
                return

            # Setup transaction
            self._doVerify = verify
            self._doUpdate = not (write or verify)
            self._error    = 0

            # Set data pointer
            tData = self._vData if verify else self._bData

        # Start transaction outside of lock
        self._reqTransaction(self._offset,tData,write,posted)

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
                return

            # Do verify
            if self._doVerify:
                for x in range(0,self._size):
                    if (self._vData[x] & self._mData[x]) != (self._bData[x] & self._mData[x]):
                        self._error = rogue.interfaces.memory.VerifyError
                        return

    def _check(self,update):
        """
        Check status of block.
        If update=True notify variables if read
        """
        doUpdate = False
        with self._cond:
            self._waitWhileBusy()

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

    def __init__(self, name=None, description="", memBase=None, offset=0, hidden=False,
                 variables=None, expand=True, enabled=True, **dump):
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
            if not any(block._addVariable(node) for block in self._blocks):
                self._blocks.append(Block(self,node))

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

        # Execute all unique afterWriteCmds
        cmds = set([v._afterWriteCmd for v in self.variables.values() if v._afterWriteCmd is not None])
        for cmd in cmds:
            cmd()

    def _verify(self):
        """ Verify all blocks. """
        if not self._enable: return

        # Device level pre-verify function
        self._beforeRead()

        # Execute all unique beforeReadCmds
        cmds = set([v._beforeReadCmd for v in self.variables.values() if v._beforeReadCmd is not None])
        for cmd in cmds:
            cmd()

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

        # Do the device level _beforeRead (if one exists)
        self._beforeRead()

        # Execute all unique beforeReadCmds
        cmds = set([v._beforeReadCmd for v in self.variables.values() if v._beforeReadCmd is not None])
        for cmd in cmds:
            cmd()

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

    def _check(self,update):
        """Check errors in all blocks and generate variable update nofifications"""
        if not self._enable: return

        # Process local blocks
        for block in self._blocks:
            block._check(update)

        # Process rest of tree
        for key,value in self._nodes.iteritems():
            if isinstance(value,Device):
                value._check(update)

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
            block.timeout = timeout

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

    for key, value in d.iteritems():
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
    byte = bitOffset / 8
    bit  = bitOffset % 8

    if value > 0:
        ba[byte] |= (1 << bit)
    else:
        ba[byte] &= (0xFF ^ (1 << bit))

def getBitFromBytes(ba, bitOffset):
    """
    Get a bit from a specific location in an array of bytes
    """
    byte = bitOffset / 8
    bit  = bitOffset % 8

    return ((ba[byte] >> bit) & 0x1)

