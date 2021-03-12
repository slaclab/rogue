#-----------------------------------------------------------------------------
# Title      : PyRogue base module - Virtual Classes
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

import pyrogue as pr
import rogue.interfaces
import pickle
import time
import threading


class VirtualProperty(object):
    def __init__(self, node, attr):
        self._attr = attr
        self._node = node

    def __get__(self, obj=None, objtype=None):
        return self._node._client._remoteAttr(self._node._path, self._attr)

    def __set__(self, obj, value):
        pass


class VirtualMethod(object):
    def __init__(self, node, attr, info):
        self._attr   = attr
        self._node   = node
        self._args   = info['args']
        self._kwargs = info['kwargs']

    def __call__(self, *args, **kwargs):
        return self._node._client._remoteAttr(self._node._path, self._attr, *args, **kwargs)


def VirtualFactory(data):

    def __init__(self,data):

        # Add dynamic methods
        for k,v in data['funcs'].items():
            setattr(self.__class__,k,VirtualMethod(self,k,v))

        # Add dynamic properties
        for k in data['props']:
            setattr(self.__class__,k,VirtualProperty(self,k))

        # Add __call__ if command or Process
        if str(pr.BaseCommand) in data['bases'] or str(pr.Process) in data['bases']:
            setattr(self.__class__,'__call__',self._call)

        # Add getNode and addVarListener if root
        if str(pr.Root) in data['bases']:
            setattr(self.__class__,'getNode',self._getNode)
            setattr(self.__class__,'addVarListener',self._addVarListener)

        # Add addListener if Variable
        if str(pr.BaseVariable) in data['bases']:
            setattr(self.__class__,'addListener',self._addListener)
            setattr(self.__class__,'delListener',self._delListener)

        VirtualNode.__init__(self,data)

    newclass = type('Virtual' + data['class'], (VirtualNode,), {"__init__": __init__})
    return newclass(data)


class VirtualNode(pr.Node):
    def __init__(self, attrs):
        super().__init__(name=attrs['name'],
                         description=attrs['description'],
                         expand=attrs['expand'],
                         groups=attrs['groups'],
                         guiGroup=attrs['guiGroup'])

        self._path  = attrs['path']
        self._class = attrs['class']
        self._nodes = attrs['nodes']
        self._bases = attrs['bases']

        # Tracking
        self._parent    = None
        self._root      = None
        self._client    = None
        self._functions = []
        self._loaded    = False

        # Setup logging
        self._log = pr.logInit(cls=self,name=self.name,path=self._path)

    def addToGroup(self,group):
        raise pr.NodeError('addToGroup not supported in VirtualNode')

    def removeFromGroup(self,group):
        raise pr.NodeError('removeFromGroup not supported in VirtualNode')

    def add(self,node):
        raise pr.NodeError('add not supported in VirtualNode')

    def callRecursive(self, func, nodeTypes=None, **kwargs):
        raise pr.NodeError('callRecursive not supported in VirtualNode')

    def __getattr__(self, name):
        if not self._loaded:
            self._loadNodes()
        return pr.Node.__getattr__(self,name)

    @property
    def nodes(self):
        if not self._loaded:
            self._loadNodes()
        return self._nodes

    def node(self, name, load=True):
        if (not self._loaded) and load:
            self._loadNodes()

        if name in self._nodes:
            return self._nodes[name]
        else:
            return None

    def _call(self, *args, **kwargs):
        return self._client._remoteAttr(self._path, '__call__', *args, **kwargs)

    def _addListener(self, listener):
        if listener not in self._functions:
            self._functions.append(listener)

    def _delListener(self, listener):
        if listener in self._functions:
            self._functions.remove(listener)

    def _addVarListener(self,func):
        self._client._addVarListener(func)

    def _loadNodes(self):
        self._loaded = True

        for k,node in self._client._remoteAttr(self._path, 'nodes').items():
            if k in self._nodes:
                node._parent = self
                node._root   = self._root
                node._client = self._client

                self._nodes[k] = node
                self._addArrayNode(node)

    def _getNode(self,path,load=True):
        obj = self

        if '.' in path:
            lst = path.split('.')

            if lst[0] != self.name and lst[0] != 'root':
                return None

            for a in lst[1:]:
                if not hasattr(obj,'node'):
                    return None
                obj = obj.node(a,load)

        elif path != self.name and path != 'root':
            return None

        return obj

    def isinstance(self,typ):
        cs = str(typ)
        return cs in self._bases

    def _rootAttached(self,parent,root):
        raise pr.NodeError('_rootAttached not supported in VirtualNode')

    def _getDict(self,modes):
        raise pr.NodeError('_getDict not supported in VirtualNode')

    def _setDict(self,*args,**kwargs):
        raise pr.NodeError('_setDict not supported in VirtualNode')

    def _doUpdate(self, val):
        for func in self._functions:
            func(self.path,val)


class VirtualClient(rogue.interfaces.ZmqClient):
    """
    A full featured client interface for Rogue. This can be used in
    scripts or other clients which require remote access to the running
    Rogue instance.

    This class ues a custom factory ensuring that only one instance of this
    class is created in a python script for a given remote connection.

    Parameters
    ----------
    addr : str
        host address

    port : int
        host port

    Attributes
    ----------
    linked: bool
        link state

    root: obj
        root class reference

    """
    ClientCache = {}

    def __new__(cls, addr="localhost", port=9099):
        newHash = hash((addr, port))

        if newHash in cls.ClientCache:
            return VirtualClient.ClientCache[newHash]
        else:
            return super(VirtualClient, cls).__new__(cls, addr, port)

    def __init__(self, addr="localhost", port=9099):
        if hash((addr,port)) in VirtualClient.ClientCache:
            return

        VirtualClient.ClientCache[hash((addr, port))] = self

        rogue.interfaces.ZmqClient.__init__(self,addr,port,False)
        self._varListeners = []
        self._monitors = []
        self._root  = None
        self._link  = False
        self._ltime = time.time()

        # Setup logging
        self._log = pr.logInit(cls=self,name="VirtualClient",path=None)

        # Get root name as a connection test
        self.setTimeout(1000,True)
        self._root = None
        while self._root is None:
            self._root = self._remoteAttr('__ROOT__',None)

        print("Connected to {} at {}:{}".format(self._root.name,addr,port))

        self._root._parent = self._root
        self._root._root   = self._root
        self._root._client = self

        setattr(self,self._root.name,self._root)

        # Link tracking
        self._link  = True
        self._ltime = self._root.Time.value()

        # Create monitoring thread
        self._monEnable = True
        self._monThread = threading.Thread(target=self._monWorker)
        self._monThread.start()

    def addLinkMonitor(self, function):
        """
        Add a link monitor callback function. This function will be called
        any time the link state changes. A single boolean argument will be passed to
        the callback function containing the current link state.

        Parameters
        ----------
        function : obj
            Call back function with the form function(linkState)
        """
        if function not in self._monitors:
            self._monitors.append(function)

    def remLinkMonitor(self, function):
        """
        Remove a previously added link monitor function.

        Parameters
        ----------
        function : obj
            Call back function
        """
        if function in self._monitors:
            self._monitors.remove(function)

    @property
    def linked(self):
        return self._link

    def _monWorker(self):
        while self._monEnable:
            time.sleep(1)

            if self._link and (time.time() - self._ltime) > 10.0:
                self._link = False
                self._log.warning(f"I have not heard from {self._root.name} in 10 seconds. It may be busy, continuing to wait...")
                for mon in self._monitors:
                    mon(self._link)

            elif (not self._link) and (time.time() - self._ltime) < 10.0:
                self._link = True
                self._log.warning(f"I have finally heard from {self._root.name}. All is good!")
                for mon in self._monitors:
                    mon(self._link)


    def _remoteAttr(self, path, attr, *args, **kwargs):
        try:
            ret = pickle.loads(self._send(pickle.dumps({ 'path':path, 'attr':attr, 'args':args, 'kwargs':kwargs })))
        except Exception as e:
            raise Exception(f"ZMQ Interface Exception: {e}")

        if isinstance(ret,Exception):
            raise(ret)

        return ret

    def _addVarListener(self,func):
        if func not in self._varListeners:
            self._varListeners.append(func)

    def _doUpdate(self,data):
        self._ltime = time.time()

        if self._root is None:
            return

        d = pickle.loads(data)

        for k,val in d.items():
            n = self._root.getNode(k,False)
            if n is not None:
                n._doUpdate(val)

            # Call listener functions,
            for func in self._varListeners:
                func(k,val)

    def stop(self):
        self._monEnable = False

    @property
    def root(self):
        return self._root

    def __hash__(self):
        return hash((self._host, self._port))

    def __eq__(self, other):
        return (self.host, self.port) == (other._host, other._port)

    def __ne__(self, other):
        return not (self == other)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.stop()
