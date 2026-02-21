#-----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
#-----------------------------------------------------------------------------
#  Description:
#       PyRogue base module - Virtual Classes
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
from typing import Any, Callable


class VirtualProperty(object):
    """Descriptor for virtual properties that fetch values from a remote client.

    Parameters
    ----------
    node : pyrogue.VirtualNode
        Virtual node instance owning this property.
    attr : str
        Attribute name to fetch from the remote.
    """

    def __init__(self, node: pr.VirtualNode, attr: str) -> None:
        self._attr = attr
        self._node = node

    def __get__(self, obj: Any = None, objtype: Any = None) -> Any:
        """Fetch attribute value from the remote client."""
        return self._node._client._remoteAttr(self._node._path, self._attr)

    def __set__(self, obj: Any, value: Any) -> None:
        """No-op setter; virtual properties are read-only."""
        pass


class VirtualMethod(object):
    """Descriptor for virtual methods that invoke remote calls.

    Parameters
    ----------
    node : pr.VirtualNode
        Virtual node instance owning this method.
    attr : str
        Attribute name to invoke on the remote.
    info : dict[str, Any]
        Method metadata including ``args`` and ``kwargs``.
    """

    def __init__(self, node: pr.VirtualNode, attr: str, info: dict[str, Any]) -> None:
        self._attr   = attr
        self._node   = node
        self._args   = info['args']
        self._kwargs = info['kwargs']

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """Invoke the remote attribute with the given arguments."""
        return self._node._client._remoteAttr(self._node._path, self._attr, *args, **kwargs)


def VirtualFactory(data: dict[str, Any]) -> Any:
    """Create a virtual class instance from serialized node data.

    Parameters
    ----------
    data : dict
        Serialized node data including 'funcs', 'props', 'bases', 'class', etc.

    Returns
    -------
    Any
        Instantiated virtual node with dynamic methods and properties.
    """

    def __init__(self, data: dict[str, Any]) -> None:
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
    """Virtual proxy node populated from remote tree metadata.

    Parameters
    ----------
    attrs : dict[str, Any]
        Serialized node attributes including ``name``, ``description``,
        ``path``, ``class``, ``bases``, and ``nodes``.
    """

    def __init__(self, attrs: dict[str, Any]) -> None:
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

    def addToGroup(self, group: str) -> None:
        """Not supported; raises NodeError."""
        raise pr.NodeError('addToGroup not supported in VirtualNode')

    def removeFromGroup(self, group: str) -> None:
        """Not supported; raises NodeError."""
        raise pr.NodeError('removeFromGroup not supported in VirtualNode')

    def add(self, node: pr.VirtualNode) -> None:
        """Not supported; raises NodeError."""
        raise pr.NodeError('add not supported in VirtualNode')

    def callRecursive(self, func: Callable[..., Any], nodeTypes: Any = None, **kwargs: Any) -> None:
        """Not supported; raises NodeError."""
        raise pr.NodeError('callRecursive not supported in VirtualNode')

    def __getattr__(self, name: str) -> Any:
        """Lazy-load children on first access, then resolve as a child attribute."""
        if not self._loaded:
            self._loadNodes()
        return pr.Node.__getattr__(self,name)

    @property
    def nodes(self) -> dict[str, Any]:
        """Child nodes keyed by name."""
        if not self._loaded:
            self._loadNodes()
        return self._nodes

    def node(self, name: str, load: bool = True) -> pr.VirtualNode | None:
        """Return child node by name, optionally loading children first.

        Parameters
        ----------
        name : str
            Child node name.
        load : bool, optional (default = True)
            If True, load child nodes before lookup.

        Returns
        -------
        Any
            Child node or None if not found.
        """
        if (not self._loaded) and load:
            self._loadNodes()

        if name in self._nodes:
            return self._nodes[name]
        else:
            return None

    def _call(self, *args: Any, **kwargs: Any) -> Any:
        """Invoke remote __call__ on this node."""
        return self._client._remoteAttr(self._path, '__call__', *args, **kwargs)

    def _addListener(self, listener: Callable[..., Any]) -> None:
        """Add a variable update listener."""
        if listener not in self._functions:
            self._functions.append(listener)

    def _delListener(self, listener: Callable[..., Any]) -> None:
        """Remove a variable update listener."""
        if listener in self._functions:
            self._functions.remove(listener)

    def _addVarListener(self, func: Callable[..., Any]) -> None:
        """Forward addVarListener to the client."""
        self._client._addVarListener(func)

    def _loadNodes(self) -> None:
        """Populate child nodes from remote metadata."""
        self._loaded = True

        for k,node in self._client._remoteAttr(self._path, 'nodes').items():
            if k in self._nodes:
                node._parent = self
                node._root   = self._root
                node._client = self._client

                self._nodes[k] = node
                self._addArrayNode(node)

    def _getNode(self, path: str, load: bool = True) -> pr.VirtualNode | None:
        """Resolve a dotted path to a node.

        Parameters
        ----------
        path : str
            Dotted path (e.g. 'root.Child.GrandChild').
        load : bool, optional (default = True)
            If True, load child nodes as needed.

        Returns
        -------
        Any
            Node at path or None if not found.
        """
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

    def isinstance(self, typ: type[pr.VirtualNode]) -> bool:
        """Check if this node's type string matches the given type."""
        cs = str(typ)
        return cs in self._bases

    def _rootAttached(self, parent: pr.VirtualNode, root: pr.VirtualNode) -> None:
        """Not supported; raises NodeError."""
        raise pr.NodeError('_rootAttached not supported in VirtualNode')

    def _getDict(self, modes: list[str]) -> Any:
        """Not supported; raises NodeError."""
        raise pr.NodeError('_getDict not supported in VirtualNode')

    def _setDict(self, *args: Any, **kwargs: Any) -> None:
        """Not supported; raises NodeError."""
        raise pr.NodeError('_setDict not supported in VirtualNode')

    def printYaml(
        self,
        readFirst: bool = False,
        modes: list[str] = ['RW', 'RO', 'WO'],
        incGroups: str | list[str] | None = None,
        excGroups: str | list[str] | None = ['Hidden'],
        recurse: bool = False,
    ) -> None:
        """Print remote YAML with selected access modes.

        Parameters
        ----------
        readFirst : bool, optional (default = False)
            If ``True``, perform a read before generating YAML output.
        modes : list['RW' | 'WO' | 'RO'], optional (default = ['RW','RO','WO'])
            Variable modes to include. Allowed values are ``'RW'``, ``'WO'``, and ``'RO'``.
        incGroups : str or list[str], optional
            Group name or group names to include.
        excGroups : str or list[str], optional
            Group name or group names to exclude.
        recurse : bool, optional (default = False)
            If ``True``, include child nodes recursively.
        """
        print(self.getYaml(readFirst=readFirst, modes=modes, incGroups=incGroups, excGroups=excGroups, recurse=recurse))

    def _doUpdate(self, val: Any) -> None:
        """Notify listeners of a value update."""
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

    def __new__(cls: type["VirtualClient"], addr: str = "localhost", port: int = 9099) -> "VirtualClient":
        """Return cached client instances keyed by ``(addr, port)``."""
        newHash = hash((addr, port))

        if newHash in cls.ClientCache:
            return VirtualClient.ClientCache[newHash]
        else:
            return super(VirtualClient, cls).__new__(cls, addr, port)

    def __init__(self, addr: str = "localhost", port: int = 9099) -> None:
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
        self._root = None
        self.setTimeout(1000,False)

        try:
            self._root = self._remoteAttr('__ROOT__',None)
        except Exception:
            error_message = (
                f"\n\nFailed to connect to {addr}:{port}!\n\n"
                "Possible causes for the issue:\n"
                "- ZeroMQ Server not included in the root class\n"
                "- Root process not running\n"
                "- Mismatch between Client address and Server address\n"
                "- Mismatch between Client port and Server port\n"
                "- Server ports being blocked\n"
            )
            print(error_message)
            return

        print("Connected to {} at {}:{}".format(self._root.name,addr,port))
        self.setTimeout(1000,True)

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

    def addLinkMonitor(self, function: Callable[[bool], None]) -> None:
        """
        Add a link monitor callback function. This function will be called
        any time the link state changes. A single boolean argument will be passed to
        the callback function containing the current link state.

        Parameters
        ----------
        function : callable
            Callback function with the form ``function(linkState: bool)``.
        """
        if function not in self._monitors:
            self._monitors.append(function)

    def remLinkMonitor(self, function: Callable[[bool], None]) -> None:
        """
        Remove a previously added link monitor function.

        Parameters
        ----------
        function : callable
            Previously registered callback function.
        """
        if function in self._monitors:
            self._monitors.remove(function)

    @property
    def linked(self) -> bool:
        """Whether the client is currently linked to the server."""
        return self._link

    def _monWorker(self) -> None:
        """Monitor link heartbeat and emit link-state callbacks."""
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


    def _remoteAttr(self, path: str, attr: str, *args: Any, **kwargs: Any) -> Any:
        """Invoke a remote attribute on the server."""
        try:
            ret = pickle.loads(self._send(pickle.dumps({ 'path':path, 'attr':attr, 'args':args, 'kwargs':kwargs })))
        except Exception as e:
            raise Exception(f"ZMQ Interface Exception: {e}")

        if isinstance(ret,Exception):
            raise ret

        return ret

    def _addVarListener(self, func: Callable[..., Any]) -> None:
        """Register a variable update listener."""
        if func not in self._varListeners:
            self._varListeners.append(func)

    def _doUpdate(self, data: bytes) -> None:
        """Process variable update data from the server."""
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

    def stop(self) -> None:
        """Stop the monitor thread and release resources."""
        self._monEnable = False

    @property
    def root(self) -> pr.VirtualNode:
        """Return the connected virtual root node."""
        return self._root

    def __hash__(self) -> int:
        """Hash based on host and port."""
        return hash((self._host, self._port))

    def __eq__(self, other: "VirtualClient") -> bool:
        """Compare by host and port."""
        return (self.host, self.port) == (other._host, other._port)

    def __ne__(self, other: "VirtualClient") -> bool:
        """Compare by host and port."""
        return not (self == other)

    def __enter__(self) -> "VirtualClient":
        """Return self for context-manager use."""
        return self

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        """Stop monitoring when leaving context-manager scope."""
        self.stop()
