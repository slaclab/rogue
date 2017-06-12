#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Title      : PyRogue base module - Device Class
#-----------------------------------------------------------------------------
# File       : pyrogue/_Device.py
# Created    : 2017-05-16
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
import collections
import datetime
import functools as ft
import pyrogue as pr
import inspect
import threading
import Pyro4

class EnableVariable(pr.BaseVariable):
    def __init__(self, enabled):
        pr.BaseVariable.__init__(self, name='enable', mode='RW', value=enabled,
                                 disp={False: 'False', True: 'True', 'parent': 'ParentFalse'},
                                 description='Determines if device is enabled for hardware access')

        self._value = enabled
        self._lock = threading.Lock()
        

    @Pyro4.expose
    def get(self, read=False):
        ret = self._value
        with self._lock:
            if self._value is False:
                ret = False
            elif self._parent == self._root:
                #print("Root enable = {}".format(self._value))
                ret = self._value
            else:
                if self._parent._parent.enable.value() is not True:
                    ret = 'parent'
                else:
                    ret = True

        if read:
            self._updated()
        return ret
        
    @Pyro4.expose
    def set(self, value, write=True):
        with self._lock:
            if value != 'parent':
                self._value = value
        self._updated()

    def _rootAttached(self):
        if self._parent != self._root:
            self._parent._parent.enable.addListener(self)
        

class DeviceError(Exception):
    """ Exception for device manipulation errors."""
    pass

class Device(pr.Node,rogue.interfaces.memory.Hub):
    """Device class holder. TODO: Update comments"""

    def __init__(self, name=None, description="", memBase=None, offset=0, hidden=False, parent=None,
                 variables=None, expand=True, enabled=True, **dump):
        """Initialize device class"""
        if name is None:
            name = self.__class__.__name__

        # Hub.__init__ must be called first for _setSlave to work below
        rogue.interfaces.memory.Hub.__init__(self,offset)

        # Blocks
        self._blocks    = []
        self._memBase   = memBase
        self._expand    = expand

        # Connect to memory slave
        if memBase: self._setSlave(memBase)

        # Node.__init__ can't be called until after self._memBase is created
        pr.Node.__init__(self, name=name, hidden=hidden, description=description)

        self._log.info("Making device {:s}".format(name))

        # Convenience methods
        self.addVariable = ft.partial(self.addNode, pr.Variable) # Legacy
        self.addVariables = ft.partial(self.addNodes, pr.Variable) # Legacy
        self.addRemoteVariables = ft.partial(self.addNodes, pr.RemoteVariable)
        self.addCommand = ft.partial(self.addNode, pr.Command) # Legacy
        self.addCommands = ft.partial(self.addNodes, pr.Command) # Legacy
        self.addRemoteCommands = ft.partial(self.addNodes, pr.RemoteCommand)

        # Variable interface to enable flag
        self.add(EnableVariable(enabled))

        if variables is not None and isinstance(variables, collections.Iterable):
            if all(isinstance(v, pr.BaseVariable) for v in variables):
                # add the list of Variable objects
                self.add(variables)
            elif all(isinstance(v, dict) for v in variables):
                # create Variable objects from a dict list
                self.add(pr.Variable(**v) for v in variables)

        cmds = sorted((d for d in (getattr(self, c) for c in dir(self)) if hasattr(d, 'PyrogueCommandArgs')),
                      key=lambda x: x.PyrogueCommandOrder)
        for cmd in cmds:
            args = getattr(cmd, 'PyrogueCommandArgs')
            if 'name' not in args:
                args['name'] = cmd.__name__
            self.add(pr.Command(function=cmd, **args))

    @Pyro4.expose
    @property
    def expand(self):
        return self._expand

    def add(self,node):
        """
        Add node as sub-node in the object
        Device specific implementation to add blocks as required.
        """

        # Special case if list (or iterable of nodes) is passed
        if isinstance(node, collections.Iterable) and all(isinstance(n, pr.Node) for n in node):
            for n in node:
                self.add(n)
            return

        # Can't add if we already have a block list
        if len(self._blocks) != 0:
            raise DeviceError('Error adding %s with name %s to %s. Device has already been attached.' % 
                              (str(node.classType),node.name,self.name))

        # Adding device
        if isinstance(node,Device):
           
            # Device does not have a membase
            if node._memBase is None:
                node._setSlave(self)

            # Build the device blocks
            node._buildBlocks()

        # Call node add
        pr.Node.add(self,node)


    def hideVariables(self, hidden, variables=None):
        """Hide a list of Variables (or Variable names)"""
        if variables is None:
            variables=self.variables.values()
            
        for v in variables:
            if isinstance(v, pr.BaseVariable):
                v._hidden = hidden;
            elif isinstance(variables[0], str):
                self.variables[v]._hidden = hidden

    def softReset(self):
        pass

    def hardReset(self):
        pass

    def countReset(self):
        pass

    def writeBlocks(self, force=False, recurse=True, variable=None):
        """
        Perform background writes
        """
        if not self.enable: return

        # Process local blocks.
        if variable is not None:
            variable._blocks.backgroundTransaction(rogue.interface.memory.Write)
        else:
            for block in self._blocks:
                if force or block.stale:
                    block.backgroundTransaction(rogue.interfaces.memory.Write)

        # Process rest of tree
        if recurse:
            for key,value in self.devices.items():
                value.writeBlocks(force=force, recurse=True)


    def verifyBlocks(self, recurse=True, variable=None):
        """
        Perform background verify
        """
        if not self.enable: return

        # Process local blocks.
        if variable is not None:
            variable._blocks.backgroundTransaction(rogue.interface.memory.Verify)
        else:
            for block in self._blocks:
                block.backgroundTransaction(rogue.interfaces.memory.Verify)

        # Process rest of tree
        if recurse:
            for key,value in self.devices.items():
                value.verifyBlocks(recurse=True)

    def readBlocks(self, recurse=True, variable=None):
        """
        Perform background reads
        """
        if not self.enable: return

        # Process local blocks.
        if variable is not None:
            variable._block.backgroundTransaction(rogue.interfaces.memory.Read)
        else:
            for block in self._blocks:
                block.backgroundTransaction(rogue.interfaces.memory.Read)

        # Process rest of tree
        if recurse:
            for key,value in self.devices.items():
                value.readBlocks(recurse=True)

    def checkBlocks(self,varUpdate=True, recurse=True, variable=None):
        """Check errors in all blocks and generate variable update nofifications"""
        if not self.enable: return

        # Process local blocks
        if variable is not None:
            variable._block._checkTransaction(varUpdate)
        else:
            for block in self._blocks:
                block._checkTransaction(varUpdate)

        # Process rest of tree
        if recurse:
            for key,value in self.devices.items():
                value.blockCheck(varUpdate=varUpdate, recurse=True)

    def _buildBlocks(self):
        # Get all of the variables
        for k,n in self.nodes.items():

            if isinstance(n,pr.LocalVariable):
                self._blocks.append(n._block)

            elif isinstance(n,pr.RemoteVariable) and n.offset is not None:
                if not any(block._addVariable(n) for block in self._blocks):
                    self._log.debug("Adding new block %s at offset %x" % (n.name,n.offset))
                    self._blocks.append(pr.MemoryBlock(n))

    def _devReset(self,rstType):
        """Generate a count, soft or hard reset"""

        if rstType == 'hard':
            self.hardReset()
        elif rstType == 'soft':
            self.softReset()
        elif rstType == 'count':
            self.countReset()

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

            argCount = len(inspect.signature(func).parameters)
            def newFunc(dev, var, val):
                if argCount == 0:
                    return func()
                else:
                    return func(val)
            self.add(pr.Command(function=newFunc, **kwargs))
            return func
        return _decorator


class DataWriter(Device):
    """Special base class to control data files. TODO: Update comments"""

    def __init__(self, name, description='', hidden=False, **dump):
        """Initialize device class"""

        Device.__init__(self, name=name, description=description,
                        size=0, memBase=None, offset=0, hidden=hidden)

        self.add(pr.LocalVariable(name='dataFile', mode='RW', value='',
            description='Data file for storing frames for connected streams.'))

        self.add(pr.LocalVariable(name='open', mode='RW', value=False,
            setFunction=self._setOpen, description='Data file open state'))

        self.add(pr.LocalVariable(name='bufferSize', mode='RW', value=0, setFunction=self._setBufferSize,
            description='File buffering size. Enables caching of data before call to file system.'))

        self.add(pr.LocalVariable(name='maxFileSize', mode='RW', value=0, setFunction=self._setMaxFileSize,
            description='Maximum size for an individual file. Setting to a non zero splits the run data into multiple files.'))

        self.add(pr.LocalVariable(name='fileSize', mode='RO', value=0, pollInterval=1, getFunction=self._getFileSize,
            description='Size of data files(s) for current open session in bytes.'))

        self.add(pr.LocalVariable(name='frameCount', mode='RO', value=0, pollInterval=1, getFunction=self._getFrameCount,
            description='Frame in data file(s) for current open session in bytes.'))

        self.add(pr.LocalCommand(name='autoName', function=self._genFileName,
            description='Auto create data file name using data and time.'))

    def _setOpen(self,dev,var,value,changed):
        """Set open state. Override in sub-class"""
        pass

    def _setBufferSize(self,dev,var,value):
        """Set buffer size. Override in sub-class"""
        pass

    def _setMaxFileSize(self,dev,var,value):
        """Set max file size. Override in sub-class"""
        pass

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
        idx = self.dataFile.value().rfind('/')

        if idx < 0:
            base = ''
        else:
            base = self.dataFile.value()[:idx+1]

        self.dataFile.set(base + datetime.datetime.now().strftime("%Y%m%d_%H%M%S.dat")) 

class RunControl(Device):
    """Special base class to control runs. TODO: Update comments."""

    def __init__(self, name, description='', hidden=True, rates=None, states=None, **dump):
        """Initialize device class"""

        if rates is None:
            rates={1:'1 Hz', 10:'10 Hz'}

        if states is None:
            states={0:'Stopped', 1:'Running'}

        Device.__init__(self, name=name, description=description,
                        size=0, memBase=None, offset=0, hidden=hidden)

        value = [k for k,v in states.items()][0]

        self.add(pr.LocalVariable(name='runState', value=value, mode='RW', enum=states,
            setFunction=self._setRunState, description='Run state of the system.'))

        value = [k for k,v in rates.items()][0]

        self.add(pr.LocalVariable(name='runRate', value=value, mode='RW', enum=rates,
            setFunction=self._setRunRate, description='Run rate of the system.'))

        self.add(pr.LocalVariable(name='runCount', value=0, mode='RO', pollInterval=1,
            description='Run Counter updated by run thread.'))

    def _setRunState(self,dev,var,value,changed):
        """
        Set run state. Reimplement in sub-class.
        Enum of run states can also be overriden.
        Underlying run control must update _runCount variable.
        """
        pass

    def _setRunRate(self,dev,var,value):
        """
        Set run rate. Reimplement in sub-class.
        Enum of run rates can also be overriden.
        """
        pass

