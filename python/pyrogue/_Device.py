import rogue.interfaces.memory
import collections
import datetime
import functools as ft
from inspect import signature
import pyrogue as pr



class Device(pr.Node, rogue.interfaces.memory.Hub):
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
        pr.Node.__init__(self, name=name, hidden=hidden, classType=classType, description=description, parent=parent)

        self._log.info("Making device {:s}".format(name))

        # Convenience methods
        self.addDevice = ft.partial(self.addNode, pr.Device)
        self.addDevices = ft.partial(self.addNodes, pr.Device)
        self.addVariable = ft.partial(self.addNode, pr.Variable)        
        self.addVariables = ft.partial(self.addNodes, pr.Variable)
        self.addCommand = ft.partial(self.addNode, pr.Command)        
        self.addCommands = ft.partial(self.addNodes, pr.Command)

        # Variable interface to enable flag
        self.add(pr.Variable(name='enable', value=enabled, base='bool', mode='RW',
                          setFunction=self._setEnable, getFunction=self._getEnable,
                          description='Determines if device is enabled for hardware access'))

        if variables is not None and isinstance(variables, collections.Iterable):
            if all(isinstance(v, pr.Variable) for v in variables):
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

        # Call node add
        pr.Node.add(self,node)

        # Adding device whos membase is not yet set
        if isinstance(node,Device) and node._memBase is None:
            node._setSlave(self)

        if isinstance(node,pr.Variable) and node.offset is not None:
            if not any(block._addVariable(node) for block in self._blocks):
                self._log.debug("Adding new block %s at offset %x" % (node.name,node.offset))
                self._blocks.append(pr.Block(node))

    def hideVariables(self, hidden, variables=None):
        """Hide a list of Variables (or Variable names)"""
        if variables is None:
            variables=self.variables.values()
            
        for v in variables:
            if isinstance(v, pr.Variable):
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
            self.add(pr.Command(function=newFunc, **kwargs))
            return func
        return _decorator

class DataWriter(Device):
    """Special base class to control data files. TODO: Update comments"""

    def __init__(self, name, description='', hidden=False, **dump):
        """Initialize device class"""

        Device.__init__(self, name=name, description=description,
                        size=0, memBase=None, offset=0, hidden=hidden)

        self.classType    = 'dataWriter'

        self.add((
            pr.Variable(name='dataFile', value='',
                          description='Data file for storing frames for connected streams.'),

            pr.Variable(name='open', value=False, setFunction=self._setOpen,
                          description='Data file open state'),

            pr.Variable(name='bufferSize', value=0, setFunction=self._setBufferSize,
                          description='File buffering size. Enables caching of data before call to file system.'),

            pr.Variable(name='maxFileSize', value=0, setFunction=self._setMaxFileSize,
                          description='Maximum size for an individual file. Setting to a non zero splits the run data into multiple files.'),

            pr.Variable(name='fileSize', value=0, mode='RO', pollInterval=1, getFunction=self._getFileSize,
                          description='Size of data files(s) for current open session in bytes.'),

            pr.Variable(name='frameCount', value=0, mode='RO', pollInterval=1, getFrameCount=self._getFrameCount,
                          description='Frame in data file(s) for current open session in bytes.'),

            pr.Command(name='autoName', function=self._genFileName,
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

        self.add(pr.Variable(name='runState', value=0, local=True, enum={0:'Stopped', 1:'Running'},
                          setFunction=self._setRunState, 
                          description='Run state of the system.'))

        self.add(pr.Variable(name='runRate', value=1, local=True, enum={1:'1 Hz', 10:'10 Hz'},
                          setFunction=self._setRunRate, 
                          description='Run rate of the system.'))

        self.add(pr.Variable(name='runCount', value=0, mode='RO', pollInterval=1,
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

