#-----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
#-----------------------------------------------------------------------------
#  Description:
#       PyRogue base module - Device Class
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
import rogue.interfaces.memory as rim
import collections
import functools as ft
import pyrogue as pr
import threading


class EnableVariable(pr.BaseVariable):
    """ """
    def __init__(self, *, enabled, deps=None):
        pr.BaseVariable.__init__(
            self,
            description='Determines if device is enabled for hardware access',
            name='enable',
            mode='RW',
            value=enabled,
            groups='Enable',
            disp={False: 'False', True: 'True', 'parent': 'ParentFalse', 'deps': 'ExtDepFalse'})

        if deps is None:
            self._deps   = []
            self._depDis = False
        else:
            self._deps   = deps
            self._depDis = True

        for d in self._deps:
            d.addListener(self)

        self._value  = enabled
        self._lock   = threading.Lock()

    @pr.expose
    def get(self, read=False, index=-1):
        """


        Parameters
        ----------
        read : bool
             (Default value = False)
        index : int
             (Default value = -1)

        Returns
             ret :
        -------

        """
        ret = self._value

        with self._lock:
            if self._value is False:
                ret = False
            elif self._depDis:
                ret = 'deps'
            elif self._parent is self._root:
                #print("Root enable = {}".format(self._value))
                ret = self._value
            else:
                if self._parent._parent.enable.value() is not True:
                    ret = 'parent'
                else:
                    ret = True

        return ret

    @pr.expose
    def set(self, value, write=True, index=-1):
        """


        Parameters
        ----------
        value :
             (Default value = enabled)
        write : bool
             (Default value = True)
        index : int
             (Default value = -1)

        Returns
        -------

        """
        if value != 'parent' and value != 'deps':
            old = self.value()

            with self._lock:
                self._value = value

            if old != value and old != 'parent' and old != 'deps':
                self.parent._updateBlockEnable()
                self.parent.enableChanged(value)

            with self.parent.root.updateGroup():
                self._queueUpdate()

            # The following concept will trigger enable listeners
            # directly. This is causing lock contentions in practice
            # (epics4 as an example)

            #self._doUpdate()
            #for var in self._listeners:
            #    var._doUpdate()

    def _doUpdate(self):
        """ """
        if len(self._deps) != 0:
            oldEn = (self.value() is True)

            with self._lock:
                self._depDis = not all(x.value() for x in self._deps)

            newEn = (self.value() is True)

            if oldEn != newEn:
                self.parent._updateBlockEnable()
                self.parent.enableChanged(newEn)

        return super()._doUpdate()

    def _rootAttached(self,parent,root):
        """


        Parameters
        ----------
        parent :

        root :


        Returns
        -------

        """
        pr.Node._rootAttached(self,parent,root)

        if parent is not root:
            parent._parent.enable.addListener(self)


class DeviceError(Exception):
    """ """
    pass


class Device(pr.Node,rim.Hub):
    """Device class holder. TODO: Update comments"""

    def __init__(self, *,
                 name=None,
                 description='',
                 memBase=None,
                 offset=0,
                 hidden=False,
                 groups=None,
                 expand=False,
                 enabled=True,
                 defaults=None,
                 enableDeps=None,
                 hubMin=0,
                 hubMax=0,
                 guiGroup=None):

        """Initialize device class"""
        if name is None:
            name = self.__class__.__name__

        # Hub.__init__ must be called first for _setSlave to work below
        rim.Hub.__init__(self,offset,hubMin,hubMax)

        # Blocks
        self._blocks     = []
        self._custBlocks = []
        self._memBase    = memBase
        self._memLock    = threading.RLock()
        self._defaults   = defaults if defaults is not None else {}

        self._ifAndProto = []

        self.forceCheckEach = False

        # Connect to memory slave
        if memBase:
            self._setSlave(memBase)

        # Node.__init__ can't be called until after self._memBase is created
        pr.Node.__init__(self, name=name, hidden=hidden, groups=groups, description=description, expand=expand, guiGroup=guiGroup)

        self._log.info("Making device {:s}".format(name))

        # Convenience methods
        self.addRemoteCommands = ft.partial(self.addNodes, pr.RemoteCommand)

        # Variable interface to enable flag
        self.add(EnableVariable(enabled=enabled, deps=enableDeps))

        self.add(pr.LocalCommand(name='ReadDevice', value=False, hidden=True,
                                 function=lambda arg: self.readAndCheckBlocks(recurse=arg),
                                 description='Force read of device without recursion'))

        self.add(pr.LocalCommand(name='WriteDevice', value='', hidden=True,
                                 function=lambda arg: self.writeAndVerifyBlocks(force=True,recurse=arg),
                                 description='Force write of device without recursion'))

    @pr.expose
    @property
    def address(self):
        """ """
        return self._getAddress()

    @pr.expose
    @property
    def offset(self):
        """ """
        return self._getOffset()

    def addCustomBlock(self, block):
        """


        Parameters
        ----------
        block :


        Returns
        -------

        """
        self._custBlocks.append(block)
        self._custBlocks.sort(key=lambda x: (x.offset, x.size))

    def add(self,node):
        """


        Parameters
        ----------
        node :


        Returns
        -------

        """
        # Call node add
        pr.Node.add(self,node)

        # Adding device
        if isinstance(node,Device):

            # Device does not have a membase
            if node._memBase is None:
                node._setSlave(self)

    def addInterface(self, *interfaces):
        """
        Add one or more rogue.interfaces.stream.Master or rogue.interfaces.memory.Master
        Also accepts iterables for adding multiple at once

        Parameters
        ----------
        *interfaces :


        Returns
        -------

        """
        for interface in interfaces:
            if isinstance(interface, collections.abc.Iterable):
                self._ifAndProto.extend(interface)
            else:
                self._ifAndProto.append(interface)

    def addProtocol(self, *protocols):
        """
        Add a protocol entity.
        Also accepts iterables for adding multiple at once

        Parameters
        ----------
        *protocols :


        Returns
        -------

        """
        self.addInterface(protocols)

    def manage(self, *interfaces):
        """


        Parameters
        ----------
        *interfaces :


        Returns
        -------

        """
        self._ifAndProto.extend(interfaces)

    def _start(self):
        """ Called recursively from Root.start when starting """
        for intf in self._ifAndProto:
            if hasattr(intf,"_start"):
                intf._start()
        for d in self.devices.values():
            d._start()

    def _stop(self):
        """Called recursively from Root.stop when exiting"""
        for intf in self._ifAndProto:
            if hasattr(intf,"_stop"):
                intf._stop()
        for d in self.devices.values():
            d._stop()

    @property
    def running(self):
        """ Check if Device._start() has been called """
        return self.root is not None and self.root.running


    def addRemoteVariables(self, number, stride, pack=False, **kwargs):
        """


        Parameters
        ----------
        number :

        stride :

        pack : bool
             (Default value = False)
        **kwargs :


        Returns
        -------

        """
        if pack:
            hidden=True
        else:
            hidden=kwargs.pop('hidden', False)

        self.addNodes(pr.RemoteVariable, number, stride, hidden=hidden, **kwargs)

        # If pack specified, create a linked variable to combine everything
        if pack:
            varList = getattr(self, kwargs['name']).values()

            def linkedSet(dev, var, val, write):
                """


                Parameters
                ----------
                dev :

                var :

                val :

                write :


                Returns
                -------

                """
                if val == '':
                    return
                values = reversed(val.split('_'))
                for variable, value in zip(varList, values):
                    variable.setDisp(value, write=write)

            def linkedGet(dev, var, read):
                """


                Parameters
                ----------
                dev :

                var :

                read :


                Returns
                -------

                """
                values = [v.getDisp(read=read) for v in varList]
                return '_'.join(reversed(values))

            name = kwargs.pop('name')
            kwargs.pop('value', None)

            lv = pr.LinkVariable(name=name, value='', dependencies=varList, linkedGet=linkedGet, linkedSet=linkedSet, **kwargs)
            self.add(lv)

    def setPollInterval(self, interval, variables=None):
        """
        Set the poll interval for a group of variables.
        The variables param is an Iterable of strings
        If variables=None, set interval for all variables that currently have nonzero pollInterval

        Parameters
        ----------
        interval :

        variables : str
             (Default value = None)

        Returns
        -------

        """
        if variables is None:
            variables = [k for k,v in self.variables.items() if v.pollInterval != 0]

        for x in variables:
            self.node(x).setPollInterval(interval)

    def hideVariables(self, hidden, variables=None):
        """
        Hide a list of Variables (or Variable names)

        Parameters
        ----------
        hidden :

        variables : str
             (Default value = None)

        Returns
        -------

        """
        if variables is None:
            variables=self.variables.values()

        for v in variables:
            if isinstance(v, pr.BaseVariable):
                v.hidden = hidden
            elif isinstance(variables[0], str):
                self.variables[v].hidden = hidden

    def initialize(self):
        """ """
        for key,value in self.devices.items():
            value.initialize()

    def hardReset(self):
        """ """
        for key,value in self.devices.items():
            value.hardReset()

    def countReset(self):
        """ """
        for key,value in self.devices.items():
            value.countReset()

    def enableChanged(self,value):
        """


        Parameters
        ----------
        value :


        Returns
        -------

        """
        pass

        #if value is True:
        #    self.writeAndVerifyBlocks(force=True, recurse=True, variable=None)

    def writeBlocks(self, *, force=False, recurse=True, variable=None, checkEach=False, index=-1, **kwargs):
        """
        Write all of the blocks held by this Device to memory

        Parameters
        ----------
        * :

        force : bool
             (Default value = False)
        recurse : bool
             (Default value = True)
        variable : str
             (Default value = None)
        checkEach : bool
             (Default value = False)
        index : int
             (Default value = -1)
        **kwargs :


        Returns
        -------

        """
        checkEach = checkEach or self.forceCheckEach

        if variable is not None:
            pr.startTransaction(variable._block, type=rim.Write, forceWr=force, checkEach=checkEach, variable=variable, index=index, **kwargs)

        else:
            for block in self._blocks:
                if block.bulkOpEn:
                    pr.startTransaction(block, type=rim.Write, forceWr=force, checkEach=checkEach, **kwargs)

            if recurse:
                for key,value in self.devices.items():
                    value.writeBlocks(force=force, recurse=True, checkEach=checkEach, **kwargs)

    def verifyBlocks(self, *, recurse=True, variable=None, checkEach=False, **kwargs):
        """
        Perform background verify

        Parameters
        ----------
              * :

        recurse : bool
             (Default value = True)
        variable : str
             (Default value = None)
        checkEach : bool
             (Default value = False)
        **kwargs :


        Returns
        -------

        """
        checkEach = checkEach or self.forceCheckEach

        if variable is not None:
            pr.startTransaction(variable._block, type=rim.Verify, checkEach=checkEach, **kwargs) # Verify range is set by previous write

        else:
            for block in self._blocks:
                if block.bulkOpEn:
                    pr.startTransaction(block, type=rim.Verify, checkEach=checkEach, **kwargs)

            if recurse:
                for key,value in self.devices.items():
                    value.verifyBlocks(recurse=True, checkEach=checkEach, **kwargs)

    def readBlocks(self, *, recurse=True, variable=None, checkEach=False, index=-1, **kwargs):
        """
        Perform background reads

        Parameters
        ----------
              * :

        recurse : bool
             (Default value = True)
        variable : str
             (Default value = None)
        checkEach : bool
             (Default value = False)
        index : int
             (Default value = -1)
        **kwargs :


        Returns
        -------

        """
        checkEach = checkEach or self.forceCheckEach

        if variable is not None:
            pr.startTransaction(variable._block, type=rim.Read, checkEach=checkEach, variable=variable, index=index, **kwargs)

        else:
            for block in self._blocks:
                if block.bulkOpEn:
                    pr.startTransaction(block, type=rim.Read, checkEach=checkEach, **kwargs)

            if recurse:
                for key,value in self.devices.items():
                    value.readBlocks(recurse=True, checkEach=checkEach, **kwargs)

    def checkBlocks(self, *, recurse=True, variable=None, **kwargs):
        """
        Check errors in all blocks and generate variable update notifications

        Parameters
        ----------
              * :

        recurse : bool
             (Default value = True)
        variable : str
             (Default value = None)
        **kwargs :


        Returns
        -------

        """
        if variable is not None:
            pr.checkTransaction(variable._block, **kwargs)

        else:
            for block in self._blocks:
                pr.checkTransaction(block, **kwargs)

            if recurse:
                for key,value in self.devices.items():
                    value.checkBlocks(recurse=True, **kwargs)

    def writeAndVerifyBlocks(self, force=False, recurse=True, variable=None, checkEach=False):
        """
        Perform a write, verify and check. Useful for committing any stale variables

        Parameters
        ----------
        force : bool
             (Default value = False)
        recurse : bool
             (Default value = True)
        variable : str
             (Default value = None)
        checkEach : bool
             (Default value = False)

        Returns
        -------

        """
        self.writeBlocks(force=force, recurse=recurse, variable=variable, checkEach=checkEach)
        self.verifyBlocks(recurse=recurse, variable=variable, checkEach=checkEach)
        self.checkBlocks(recurse=recurse, variable=variable)

    def readAndCheckBlocks(self, recurse=True, variable=None, checkEach=False):
        """
        Perform a read and check.

        Parameters
        ----------
        recurse : bool
             (Default value = True)
        variable : str
             (Default value = None)
        checkEach : bool
             (Default value = False)

        Returns
        -------

        """
        self.readBlocks(recurse=recurse, variable=variable, checkEach=checkEach)
        self.checkBlocks(recurse=recurse, variable=variable)

    def _updateBlockEnable(self):
        """ """
        for block in self._blocks:
            block.setEnable(self.enable.value() is True)

        for key,value in self.devices.items():
            value._updateBlockEnable()

    def _buildBlocks(self):
        """ """
        remVars = []

        # Use min block size, larger blocks can be pre-created
        blkSize = self._blkMinAccess()

        # Process all of the variables
        for k,n in self.nodes.items():

            # Local variables have a 1:1 block association
            if isinstance(n,pr.LocalVariable):
                self._blocks.append(n._block)

            # Align to min access, create list of remote variables
            elif isinstance(n,pr.RemoteVariable) and n.offset is not None:
                self._log.info(f"Before Shift variable {n.name} offset={n.offset} bitSize={n.bitSize} bytes={n.varBytes}")
                n._updatePath(n.path)
                n._shiftOffsetDown(n.offset % blkSize, blkSize)
                remVars += [n]

                self._log.info(f"Creating variable {n.name} offset={n.offset} bitSize={n.bitSize} bytes={n.varBytes}")

        # Sort var list by offset, size
        remVars.sort(key=lambda x: (x.offset, x.varBytes))
        blocks = []
        blk = None

        # Go through sorted variable list, look for overlaps, group into blocks
        for n in remVars:

            if blk is not None and ( (blk['offset'] + blk['size']) > n.offset):
                self._log.info("Overlap detected var offset={} block offset={} block bytes={}".format(n.offset,blk['offset'],blk['size']))
                n._shiftOffsetDown(n.offset - blk['offset'], blkSize)
                blk['vars'].append(n)

                if n.varBytes > blk['size']:
                    blk['size'] = n.varBytes

            # We need a new block for this variable
            else:
                blk = None

                # Look for pre-made block which overlaps
                for b in self._custBlocks:
                    if ( (n.offset >= b.offset) and ((b.offset + b.size) > n.offset)):

                        # Just in case a variable extends past the end of pre-made block, user mistake
                        if n.varBytes > b.size:
                            msg = 'Failed to add variable {n.name} to pre-made block with offset {b.offset} and size {b.size}'
                            raise pr.MemoryError(name=self.path, address=self.address, msg=msg)

                        blk = {'offset':b.offset, 'size':b.size, 'vars':[n], 'block':b}
                        break

                # Block not found
                if blk is None:
                    blk = {'offset':n.offset, 'size':n.varBytes, 'vars':[n], 'block':None}
                    blocks.append(blk)

        # Clear pre-made list
        self._custBlocks = []

        # Create new blocks and add new and pre-made blocks to device
        # Add variables to the block
        for b in blocks:

            # Create new block
            if b['block'] is None:
                newBlock = rim.Block(b['offset'], b['size'])
                self._log.debug("Adding new block at offset {:#02x}, size {}".format(b['offset'], b['size']))
            else:
                newBlock = b['block']

            # Set memory slave
            newBlock._setSlave(self)

            # Verify the block is not too small or large for the memory interface
            if newBlock.size > self._blkMaxAccess() or newBlock.size < self._blkMinAccess():
                msg = f'Block size {newBlock.size} is not in the range: {self._blkMinAccess()} - {self._blkMaxAccess()}'
                raise pr.MemoryError(name=self.path, address=self.address, msg=msg)

            # Add variables to the block
            newBlock.addVariables(b['vars'])

            # Set varible block links
            for v in b['vars']:
                v._block = newBlock

            # Add to device
            self._blocks.append(newBlock)
            newBlock.setEnable(self.enable.value() is True)

    def _rootAttached(self, parent, root):
        """


        Parameters
        ----------
        parent :

        root :


        Returns
        -------

        """
        pr.Node._rootAttached(self, parent, root)

        for key,value in self._nodes.items():
            value._rootAttached(self,root)

        self._buildBlocks()

        # Override defaults as dictated by the _defaults dict
        for varName, defValue in self._defaults.items():
            nodes,keys = self.nodeMatch(varName)

            if keys is None:
                for var in nodes:
                    var._default = defValue

    def _setTimeout(self,timeout):
        """
        Set timeout value on all devices & blocks

        Parameters
        ----------
        timeout :


        Returns
        -------

        """

        for block in self._blocks:
            block._setTimeout(int(timeout*1000000))

        rim.Master._setTimeout(self, int(timeout*1000000))

        for key,value in self._nodes.items():
            if isinstance(value,Device):
                value._setTimeout(timeout)

    def command(self, **kwargs):
        """
        A Decorator to add inline constructor functions as commands

        Parameters
        ----------
        **kwargs :


        Returns
        -------

        """
        def _decorator(func):
            """


            Parameters
            ----------
            func :


            Returns
            -------

            """
            if 'name' not in kwargs:
                kwargs['name'] = func.__name__

            self.add(pr.LocalCommand(function=func, **kwargs))

            return func
        return _decorator

    def linkVariableGet(self, **kwargs):
        """
        Decorator to add inline constructor functions as LinkVariable.linkedGet functions

        Parameters
        ----------
        **kwargs :


        Returns
        -------

        """
        def _decorator(func):
            """


            Parameters
            ----------
            func :


            Returns
            -------

            """
            if 'name' not in kwargs:
                kwargs['name'] = func.__name__

            self.add(pr.LinkVariable(linkedGet=func, **kwargs))

            return func
        return _decorator

    def genDocuments(self,path,incGroups, excGroups):
        """


        Parameters
        ----------
        path :

        incGroups :

        excGroups :


        Returns
        -------

        """

        with open(path + '/' + self.path.replace('.','_') + '.rst','w') as file:

            print("****************************",file=file)
            print(self.name,file=file)
            print("****************************",file=file)

            print('',file=file)
            print(pr.genDocDesc(self.description,0),file=file)
            print('',file=file)

            plist = self.getNodes(typ=pr.Process,incGroups=incGroups,excGroups=excGroups)
            dlist = self.devicesByGroup(incGroups=incGroups,excGroups=excGroups)
            vlist = self.variablesByGroup(incGroups=incGroups,excGroups=excGroups)
            clist = self.commandsByGroup(incGroups=incGroups,excGroups=excGroups)

            tlist = {k:v for k,v in dlist.items() if k not in plist}

            if len(tlist) > 0:
                print(".. toctree::",file=file)
                print("   :maxdepth: 1",file=file)
                print("   :caption: Sub Devices:",file=file)
                print('',file=file)
                for k,v in tlist.items():
                    print('   ' + v.path.replace('.','_'),file=file)
                    v.genDocuments(path,incGroups,excGroups)
                print('',file=file)

            if len(plist) > 0:
                print(".. toctree::",file=file)
                print("   :maxdepth: 1",file=file)
                print("   :caption: Processes:",file=file)
                print('',file=file)
                for k,v in plist.items():
                    print('   ' + v.path.replace('.','_'),file=file)
                    v.genDocuments(path,incGroups,excGroups)
                print('',file=file)

            print("Summary",file=file)
            print("#######",file=file)
            print('',file=file)

            if len(vlist):
                print("Variable List",file=file)
                print("*************",file=file)
                print('',file=file)
                for k,v in vlist.items():
                    print(f"* {k}",file=file)
                print('',file=file)

            if len(clist):
                print("Command List",file=file)
                print("*************",file=file)
                print('',file=file)
                for k,v in clist.items():
                    print(f"* {k}",file=file)
                print('',file=file)

            print("Details",file=file)
            print("#######",file=file)
            print('',file=file)

            if len(vlist):
                print("Variables",file=file)
                print("*********",file=file)
                print('',file=file)
                for k,v in vlist.items():
                    v._genDocs(file=file)
                    print('',file=file)

            if len(clist):
                print("Commands",file=file)
                print("********",file=file)
                print('',file=file)
                for k,v in clist.items():
                    v._genDocs(file=file)
                    print('',file=file)


class ArrayDevice(Device):
    """ """
    def __init__(self, *, arrayClass, number, stride=0, arrayArgs=None, **kwargs):
        if 'name' not in kwargs:
            kwargs['name'] = f'{arrayClass.__name__}Array'
        super().__init__(**kwargs)

        if arrayArgs is None:
            arrayArgs = [{} for x in range(number)]
        elif isinstance(arrayArgs, dict):
            arrayArgs = [arrayArgs.copy() for x in range(number)]

        for i in range(number):
            args = arrayArgs[i]
            if 'name' in args:
                name = args.pop('name')
            else:
                name = f'{arrayClass.__name__}[{i}]'
            self.add(arrayClass(
                name=name,
                offset=i*stride,
                **args))
