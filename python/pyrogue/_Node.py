#-----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
#-----------------------------------------------------------------------------
#  Description:
#       PyRogue base module - Node Classes
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
from __future__ import annotations

import collections
import inspect
import logging
import re
import sys
from collections import OrderedDict as odict
from typing import Any, Callable, Iterable, OrderedDict

import pyrogue as pr


def logException(log: logging.Logger, e: Exception) -> None:
    """Log a memory error or a generic exception.

    Parameters
    ----------
    log : logging.Logger
        Logger used to record the exception.
    e : Exception
        Exception instance to log.
    """
    if isinstance(e,pr.MemoryError):
        log.error(e)
    else:
        log.exception(e)


def logInit(cls: type[pr.Node] | None = None, name: str | None = None, path: str | None = None) -> logging.Logger:
    """Initialize a logger with a consistent PyRogue name.

    Parameters
    ----------
    cls : object, optional
        Instance used to derive the base-class tag.
    name : str, optional
        Node name to include in the logger.
    path : str, optional
        Full node path to include in the logger.

    Returns
    -------
    logging.Logger
        Configured logger instance.
    """

    # Support base class in order of precedence
    baseClasses = odict({pr.BaseCommand : 'Command', pr.BaseVariable : 'Variable',
                         pr.Root : 'Root', pr.Device : 'Device'})

    """Init a logging object. Set global options."""
    logging.basicConfig(
        #level=logging.NOTSET,
        format="%(levelname)s:%(name)s:%(message)s",
        stream=sys.stdout)

    # All logging starts with rogue prefix
    ln = 'pyrogue'

    # Next add the highest ranking base class
    if cls is not None:
        for k,v in baseClasses.items():
            if isinstance(cls,k):
                ln += f'.{v}'
                break

        # Next subclass name
        ln += f'.{cls.__class__.__name__}'

    # Add full path if passed
    if path is not None:
        ln += f'.{path}'

    # Otherwise just add name if passed
    elif name is not None:
        ln += f'.{name}'

    return logging.getLogger(ln)


def expose(item: Any) -> Any:
    """Mark a property or method as exposed to external interfaces.

    Parameters
    ----------
    item : Any
        Property or method to expose.

    Returns
    -------
    Any
        The original item for decorator chaining.
    """

    # Property
    if inspect.isdatadescriptor(item):
        item.fget._rogueExposed = True
        return item

    # Method
    item._rogueExposed = True
    return item


class NodeError(Exception):
    """Raised when node operations fail."""
    pass


class Node(object):
    """Base class for nodes in the PyRogue tree.

    Each node is associated with a parent and has a link to the top node of a tree.
    A node has a list of sub-nodes as well as each sub-node being attached as an
    attribute. This allows tree browsing using: node1.node2.node3

    Parameters
    ----------
    name : str
        Global name of the node.
    description : str, optional (default = "")
        Human-readable description.
    expand : bool, optional (default = True)
        Default GUI expand state.
    hidden : bool, optional (default = False)
        If True, add the node to the ``Hidden`` group.
    groups : list[str], optional
        Groups to assign.
    guiGroup : str, optional
        GUI grouping label.
    """
    _nodeCount = 0

    def __init__(
        self,
        *,
        name: str,
        description: str = "",
        expand: bool = True,
        hidden: bool = False,
        groups: list[str] | None = None,
        guiGroup: str | None = None,
    ) -> None:
        """Initialize the node."""
        pr.Node._nodeCount += 1

        # Public attributes
        self._name        = name
        self._description = description
        self._path        = name
        self._expand      = expand
        self._guiGroup    = guiGroup

        # Tracking
        self._parent  = None
        self._root    = None
        self._nodes   = odict()
        self._anodes  = odict()

        # Setup logging
        self._log = logInit(cls=self,name=name,path=None)

        if groups is None:
            self._groups = []
        elif isinstance(groups,list):
            self._groups = groups
        else:
            self._groups = [groups]

        if hidden is True:
            self.addToGroup('Hidden')

    def __repr__(self) -> str:
        return f'{self.__class__} - {self.path}'

    @property
    def nodeCount(self) -> int:
        """Return the total node count."""
        return pr.Node._nodeCount

    @property
    def name(self) -> str:
        """Return the node name."""
        return self._name

    @property
    def description(self) -> str:
        """Return the node description."""
        return self._description

    @property
    def groups(self) -> list[str]:
        """Return the node groups."""
        return self._groups

    def inGroup(self, group: str) -> bool:
        """Return True if the node is in the provided group or groups.

        Parameters
        ----------
        group : object
            Group name or list of groups to test.
        """
        if isinstance(group,list):
            return len(set(group) & set(self._groups)) > 0
        else:
            return group in self._groups

    def filterByGroup(self, incGroups: str | list[str] | None, excGroups: str | list[str] | None) -> bool:
        """Return True if the node passes include/exclude filters.

        Parameters
        ----------
        incGroups : str or list[str], optional
            Group name or group names to include.
        excGroups : str or list[str], optional
            Group name or group names to exclude.
        """
        return ((incGroups is None) or (len(incGroups) == 0) or (self.inGroup(incGroups))) and \
               ((excGroups is None) or (len(excGroups) == 0) or (not self.inGroup(excGroups)))

    def addToGroup(self, group: str) -> None:
        """Add this node to a group and propagate to children.

        Parameters
        ----------
        group : str
            Group name to add.
        """
        if group not in self._groups:
            self._groups.append(group)

        for k,v in self._nodes.items():
            v.addToGroup(group)

    def removeFromGroup(self, group: str) -> None:
        """Remove this node from a group.

        Parameters
        ----------
        group : str
            Group name to remove.
        """
        if group in self._groups:
            self._groups.remove(group)

    @property
    def hidden(self) -> bool:
        """Return True if the node is hidden."""
        return self.inGroup('Hidden')

    @hidden.setter
    def hidden(self, value: bool) -> None:
        """Set whether the node is hidden."""
        if value is True:
            self.addToGroup('Hidden')
        else:
            self.removeFromGroup('Hidden')

    @property
    def path(self) -> str:
        """Return the full node path."""
        return self._path

    @property
    def expand(self) -> bool:
        """Return the expand state."""
        return self._expand

    @property
    def guiGroup(self) -> str | None:
        """Return the GUI group label."""
        return self._guiGroup

    def __getattr__(self, name: str) -> Node:
        """
        Allow child Nodes with the 'name[key]' naming convention to be accessed as if they belong to a
        dictionary of Nodes with that 'name'.
        Raises AttributeError if no such named Nodes are found.

        Parameters
        ----------

        name : str
            Name of the node to access.
        Returns
        -------
        Node
            The node with the given name.
        """

        # Node matches name in node list
        if name in self._nodes:
            return self._nodes[name]

        # Node matches name in node dictionary list
        elif name in self._anodes:
            return self._anodes[name]

        else:
            raise AttributeError('{} has no attribute {}'.format(self, name))


    def __dir__(self) -> list[str]:
        return super().__dir__() + [k for k,v in self._nodes.items()]

    def __reduce__(self) -> tuple[Any, tuple[dict]]:
        attr = {}

        attr['name']        = self._name
        attr['class']       = self.__class__.__name__
        attr['bases']       = pr.genBaseList(self.__class__)
        attr['description'] = self._description
        attr['groups']      = self._groups
        attr['path']        = self._path
        attr['expand']      = self._expand
        attr['guiGroup']    = self._guiGroup
        attr['nodes']       = odict({k:None for k,v in self._nodes.items() if not v.inGroup('NoServe')})
        attr['props']       = []
        attr['funcs']       = {}

        # Get properties
        for k,v in inspect.getmembers(self.__class__, lambda a: isinstance(a,property)):
            if hasattr(v.fget,'_rogueExposed'):
                attr['props'].append(k)

        # Get methods
        for k,v in inspect.getmembers(self.__class__, callable):
            if hasattr(v,'_rogueExposed'):
                attr['funcs'][k] = {'args'   : [a for a in inspect.getfullargspec(v).args if a != 'self'],
                                    'kwargs' : inspect.getfullargspec(v).kwonlyargs}

        return (pr.interfaces.VirtualFactory, (attr,))

    def __contains__(self, item: Node) -> bool:
        return item in self.nodes.values()

    def add(self, node: Node | Iterable[Node]) -> None:
        """Add a node as a child."""

        # Special case if list (or iterable of nodes) is passed
        if isinstance(node, collections.abc.Iterable) and all(isinstance(n, Node) for n in node):
            for n in node:
                self.add(n)
            return

        # Fail if added to a non device node (may change in future)
        if not isinstance(self,pr.Device):
            raise NodeError('Attempting to add node with name %s to non device node %s.' % (node.name,self.name))

        # Fail if root already exists
        if self._root is not None:
            raise NodeError('Error adding node with name %s to %s. Tree is already started.' % (node.name,self.name))

        # Error if added node already has a parent
        if node._parent is not None:
            raise NodeError('Error adding node with name %s to %s. Node is already attached.' % (node.name,self.name))

        # Names of all sub-nodes must be unique
        if node.name in self.__dir__() or node.name in self._anodes:
            raise NodeError('Error adding node with name %s to %s. Name collision.' % (node.name,self.name))

        # Add some checking for characters which will make lookups problematic
        if re.match('^[\\w_\\[\\]]+$',node.name) is None:
            self._log.warning('Node {} with one or more special characters will cause lookup errors.'.format(node.name))

        # Detect and add array nodes
        self._addArrayNode(node)

        # Add to primary list
        self._nodes[node.name] = node

    def _addArrayNode(self, node: Node) -> None:


        # Generic test array method
        fields = re.split('\\]\\[|\\[|\\]',node.name)
        if len(fields) < 3:
            return

        # Extract name and keys
        aname = fields[0]
        keys  = fields[1:-1]

        if not all([key.isdigit() for key in keys]):
            self._log.warning('Array node {} with non numeric key will cause lookup errors.'.format(node.name))
            return

        # Detect collisions
        if aname in self.__dir__():
            raise NodeError('Error adding node with name %s to %s. Name collision.' % (node.name,self.name))

        # Create dictionary containers
        if aname not in self._anodes:
            self._anodes[aname] = {}

        # Start at primary list
        sub = self._anodes[aname]

        # Iterate through keys
        for i in range(len(keys)):
            k = int(keys[i])

            # Last key, set node, check for overlaps
            if i == (len(keys)-1):
                if k in sub:
                    raise NodeError('Error adding node with name %s to %s. Name collision.' % (node.name,self.name))

                sub[k] = node
                return

            # Next level is empty
            if k not in sub:
                sub[k] = {}

            # check for overlaps
            elif isinstance(sub[k],Node):
                raise NodeError('Error adding node with name %s to %s. Name collision.' % (node.name,self.name))

            sub = sub[k]


    def addNode(self, nodeClass: type[Node], **kwargs: Any) -> None:
        """Construct and add a node of ``nodeClass``."""
        self.add(nodeClass(**kwargs))

    def addNodes(self, nodeClass: type[Node], number: int, stride: int, **kwargs: Any) -> None:
        """Add a series of nodes with indexed names."""
        name = kwargs.pop('name')
        offset = kwargs.pop('offset')
        for i in range(number):
            self.add(nodeClass(name='{:s}[{:d}]'.format(name, i), offset=offset+(i*stride), **kwargs))

    @property
    def nodeList(self) -> list[Node]:
        """Return a recursive list of nodes."""
        lst = []
        for key,value in self._nodes.items():
            lst.append(value)
            lst.extend(value.nodeList)
        return lst

    def getNodes(
        self,
        typ: type[Node],
        excTyp: type[Node] | None = None,
        incGroups: str | list[str] | None = None,
        excGroups: str | list[str] | None = None,
    ) -> OrderedDict[str, Node]:
        """
        Get a filtered ordered dictionary of nodes.
        pass a class to typ to receive a certain type of node
        exc is a class type to exclude,
        incGroups is an optional group or list of groups that this node must be part of
        excGroups is an optional group or list of groups that this node must not be part of

        Parameters
        ----------
        typ :

        excTyp : object, optional
            Type to exclude.
        incGroups : str or list[str], optional
            Group name or group names to include.
        excGroups : str or list[str], optional
            Group name or group names to exclude.

        Returns
        -------
        OrderedDict[str, Node]
            Ordered dictionary of nodes.
        """
        return odict([(k,n) for k,n in self.nodes.items()
                      if (n.isinstance(typ) and ((excTyp is None) or (not n.isinstance(excTyp))) and n.filterByGroup(incGroups,excGroups))])

    @property
    def nodes(self) -> OrderedDict[str, Node]:
        """Return an ordered dictionary of direct child nodes."""
        return self._nodes

    @property
    def variables(self) -> OrderedDict[str, pr.BaseVariable]:
        """Return direct child variables (excluding commands)."""
        return self.getNodes(typ=pr.BaseVariable,excTyp=pr.BaseCommand)

    def variablesByGroup(self, incGroups: str | list[str] | None = None, excGroups: str | list[str] | None = None) -> OrderedDict[str, pr.BaseVariable]:
        """Return variables filtered by group."""
        return self.getNodes(typ=pr.BaseVariable,excTyp=pr.BaseCommand,incGroups=incGroups,excGroups=excGroups)

    @property
    def variableList(self) -> list[pr.BaseVariable]:
        """Return a recursive list of variables and commands."""
        lst = []
        for key,value in self.nodes.items():
            if value.isinstance(pr.BaseVariable):
                lst.append(value)
            else:
                lst.extend(value.variableList)
        return lst

    @property
    def commands(self) -> OrderedDict[str, pr.BaseCommand]:
        """Return direct child commands."""
        return self.getNodes(typ=pr.BaseCommand)

    def commandsByGroup(self, incGroups: str | list[str] | None = None, excGroups: str | list[str] | None = None) -> OrderedDict[str, pr.BaseCommand]:
        """Return commands filtered by group."""
        return self.getNodes(typ=pr.BaseCommand,incGroups=incGroups,excGroups=excGroups)

    @property
    def devices(self) -> OrderedDict[str, pr.Device]:
        """Return direct child devices."""
        return self.getNodes(pr.Device)

    def devicesByGroup(self, incGroups: str | list[str] | None = None, excGroups: str | list[str] | None = None) -> OrderedDict[str, pr.Device]:
        """Return devices filtered by group."""
        return self.getNodes(pr.Device,incGroups=incGroups,excGroups=excGroups)

    @property
    def deviceList(self) -> list[pr.Device]:
        """Return a recursive list of devices."""
        lst = []
        for key,value in self.nodes.items():
            if value.isinstance(pr.Device):
                lst.append(value)
                lst.extend(value.deviceList)
        return lst

    @property
    def parent(self) -> Node:
        """Return the parent node."""
        return self._parent

    @property
    def root(self) -> pr.Root:
        """Return the root node."""
        return self._root

    def node(self, name: str) -> Node:
        """Return a direct child node by name.

        Parameters
        ----------
        name : str
            Child node name.
        """
        if name in self._nodes:
            return self._nodes[name]
        else:
            return None

    @property
    def isDevice(self) -> bool:
        """Return True if this node is a device."""
        return self.isinstance(pr.Device)

    @property
    def isVariable(self) -> bool:
        """Return True if this node is a variable (excluding commands)."""
        return (self.isinstance(pr.BaseVariable) and (not self.isinstance(pr.BaseCommand)))

    @property
    def isCommand(self) -> bool:
        """Return True if this node is a command."""
        return self.isinstance(pr.BaseCommand)

    def find(self, *, recurse: bool = True, typ: type[Node] | None = None, **kwargs: Any) -> list[Node]:
        """
        Find all child nodes that are a base class of 'typ'
        and whose properties match all of the kwargs.
        For string properties, accepts regexes.

        Parameters
        ----------
        recurse : bool, optional (default = True)
            If True, recurse into child nodes.
        typ : type[Node], optional
            Base class type to match.
        **kwargs :


        Returns
        -------
        list[Node]
            List of nodes that match the criteria.
        """

        if typ is None:
            typ = pr.Node

        found = []
        for node in self.nodes.values():
            if node.isinstance(typ):
                for prop, value in kwargs.items():
                    if not hasattr(node, prop):
                        break
                    attr = getattr(node, prop)
                    if isinstance(value, str):
                        if not re.match(value, attr):
                            break

                    else:
                        if inspect.ismethod(attr):
                            attr = attr()
                        if not value == attr:
                            break
                else:
                    found.append(node)
            if recurse:
                found.extend(node.find(recurse=recurse, typ=typ, **kwargs))
        return found

    def callRecursive(self, func: str, nodeTypes: Iterable[type[Node]] | None = None, **kwargs: Any) -> None:
        """Call a named method on this node and matching children.

        Parameters
        ----------
        func : str
            Method name to call.
        nodeTypes : iterable[type[Node]], optional
            Node types to include.
        **kwargs : Any
            Arguments forwarded to the method call.
        """
        # Call the function
        getattr(self, func)(**kwargs)

        if nodeTypes is None:
            nodeTypes = [pr.Node]

        # Recursively call the function
        for key, node in self.nodes.items():
            if any(isinstance(node, typ) for typ in nodeTypes):
                node.callRecursive(func, nodeTypes, **kwargs)

    # this might be useful
    def makeRecursive(self, func: str, nodeTypes: Iterable[type[Node]] | None = None) -> Callable[..., None]:
        """Create a recursive wrapper for a named method.

        Parameters
        ----------
        func : str
            Method name to call.
        nodeTypes : iterable, optional
            Node types to include.
        """
        def closure(**kwargs: Any) -> None:
            self.callRecursive(func, nodeTypes, **kwargs)
        return closure

    def isinstance(self, typ: type[Node]) -> bool:
        """Return True if this node is an instance of ``typ``."""
        return isinstance(self,typ)

    def _rootAttached(self,parent: Node, root: pr.Root) -> None:
        """
        Called once the root node is attached.

        Parameters
        ----------
        parent : Node
            The parent node.

        root : pr.Root
            The root node.


        """
        self._parent = parent
        self._root   = root
        self._path   = parent.path + '.' + self.name
        self._log    = logInit(cls=self,name=self._name,path=self._path)

        # Inherit groups from parent
        for grp in parent.groups:
            self.addToGroup(grp)

    def _finishInit(self):
        for key,value in self._nodes.items():
            value._finishInit()

    @expose
    def getYaml(
        self,
        readFirst: bool = False,
        modes: list[str] = ['RW','RO','WO'],
        incGroups: str | list[str] | None = None,
        excGroups: str | list[str] | None = None,
        recurse: bool = True,
    ) -> str:
        """Return current values as YAML text.

        Parameters
        ----------
        readFirst : bool, optional (default = False)
            If True, perform a full hardware read before exporting.
        modes : list['RW' | 'WO' | 'RO'], optional (default = ['RW','RO','WO'])
            Variable modes to include. Allowed values are ``'RW'``, ``'WO'``, and ``'RO'``.
        incGroups : str or list[str], optional
            Group name or group names to include.
        excGroups : str or list[str], optional
            Group name or group names to exclude.
        recurse : bool, optional (default = True)
            If True, recurse into child devices.

        Returns
        -------
        str
            YAML-formatted representation of the node subtree.
        """
        if readFirst:
            self.root._read()
        return pr.dataToYaml({self.name:self._getDict(modes=modes, incGroups=incGroups, excGroups=excGroups, recurse=recurse)})

    def printYaml(
        self,
        readFirst: bool = False,
        modes: list[str] = ['RW','RO','WO'],
        incGroups: str | list[str] | None = None,
        excGroups: str | list[str] | None = None,
        recurse: bool = False,
    ) -> None:
        """Print the YAML representation to stdout.

        Parameters
        ----------
        readFirst : bool, optional (default = False)
            If True, perform a full hardware read before exporting.
        modes : list['RW' | 'WO' | 'RO'], optional (default = ['RW','RO','WO'])
            Variable modes to include. Allowed values are ``'RW'``, ``'WO'``, and ``'RO'``.
        incGroups : str or list[str], optional
            Group name or group names to include.
        excGroups : str or list[str], optional
            Group name or group names to exclude.
        recurse : bool, optional (default = False)
            If True, recurse into child devices.
        """
        print(self.getYaml(readFirst=readFirst, modes=modes, incGroups=incGroups, excGroups=excGroups, recurse=recurse))

    def _getDict(
        self,
        modes: list[str] = ['RW', 'RO', 'WO'],
        incGroups: str | list[str] | None = None,
        excGroups: str | list[str] | None = None,
        properties: bool = False,
        recurse: bool = True,
    ) -> OrderedDict[str, Any]:
        """
        Get variable values in a dictionary starting from this level.
        Attributes that are Nodes are recursed.
        modes is a list of variable modes to include.

        Parameters
        ----------
        modes : list['RW' | 'WO' | 'RO'], optional (default = ['RW', 'RO', 'WO'])
            Variable modes to include. Allowed values are ``'RW'``, ``'WO'``, and ``'RO'``.

        incGroups : str or list[str], optional
            Group name or group names to include.
        excGroups : str or list[str], optional
            Group name or group names to exclude.

        properties : bool, optional (default = False)
            If True, return the properties of the variables.
        recurse : bool, optional (default = True)
            If True, recurse into child devices.

        Returns
        -------
        OrderedDict[str, Any]
            Dictionary of variable values.
        """
        data = odict()
        for key,value in self.variablesByGroup(incGroups, excGroups).items():
            nv = value._getDict(modes=modes,incGroups=incGroups,excGroups=excGroups, properties=properties)
            if nv is not None:
                data[key] = nv

        if recurse:
            for key, value in self.devicesByGroup(incGroups, excGroups).items():
                nv = value._getDict(modes=modes,incGroups=incGroups,excGroups=excGroups, properties=properties)
                if nv is not None:
                    data[key] = nv

        if len(data) == 0:
            return None
        else:
            return data

    def _setDict(
        self,
        d: dict[str, str],
        writeEach: bool,
        modes: list[str],
        incGroups: str | list[str] | None = None,
        excGroups: str | list[str] | None = None,
        keys: list[str] | None = None,
    ) -> None:
        """Set variable values from a dictionary.

        Invoked recursively to set values for entire subtree.
        Override in BaseVariable subclasses to set values using setDisp method.

        Parameters
        ----------
        d : dict[str, str]
            Dictionary of variable values.
            Variable names are the keys.
            Values are the values to set using the Variable's setDisp method.
        writeEach : bool
            If True, wait for each variable write transaction to complete before setting the next variable.
        modes : list['RW' | 'WO' | 'RO']
            Variable modes to include. Allowed values are ``'RW'``, ``'WO'``, and ``'RO'``.
        incGroups : str or list[str], optional
            Group name or group names to include.
        excGroups : str or list[str], optional
            Group name or group names to exclude.
        keys : list[str], optional
            Keys to include.


        Returns
        -------
        None
        """

        # If keys is not none, someone tried to access this node with array
        # attributes incorrectly. This should only happen in the variable class.
        if keys is not None:
            self._log.error(f"Entry {self.name} with key {keys} not found")
        else:
            for key, value in d.items():
                nodes,keys = self.nodeMatch(key)

                if len(nodes) == 0:
                    self._log.error("Entry {} not found".format(key))
                else:
                    for n in nodes:
                        if n.filterByGroup(incGroups,excGroups):
                            n._setDict(value,writeEach,modes,incGroups,excGroups,keys)

    def _setTimeout(self, timeout: int) -> None:
        """Set the timeout for this Node's get and set operations.
        Not implemented in Node class.
        Override in subclasses to set the timeout for this Node's get and set operations.

        Parameters
        ----------
        timeout : int
            Timeout value in seconds.

        Returns
        -------
        None
        """
        pass

    def nodeMatch(self, name: str) -> list[Node]:
        """Match a node name, including array-style accessors.

        Parameters
        ----------
        name : str
            Node name or array accessor string.

        Returns
        -------
        list of Node
            Matching nodes.
        """
        # Node matches name in node list
        if name in self.nodes:
            return [self.nodes[name]],None

        # Otherwise we may need to slice an array
        else:

            # Generic test array method
            fields = re.split('\\]\\[|\\[|\\]',name)

            # Extract name and keys
            aname = fields[0]
            keys  = fields[1:-1]

            # Name is in standard list
            if aname in self.nodes:
                return [self.nodes[aname]],keys

            # Name not in list
            if aname is None or aname not in self._anodes or len(keys) == 0:
                return [],None

            return _iterateDict(self._anodes[aname],keys),None


def _iterateDict(d: dict[str], keys: list[str]) -> list[Node]:
    """Iterate into a nested dict using array-style keys."""
    retList = []

    # Wildcard, full list
    if keys[0] == '*' or keys[0] == ':':
        subList = list(d.values())

    # Single item
    elif keys[0].isdigit():
        try:
            subList = [d[int(keys[0])]]
        except Exception:
            subList = []

    # Slice
    else:

        # Form slice-able list
        tmpList = [None] * (max(d.keys())+1)
        for k,v in d.items():
            tmpList[k] = v

        try:
            subList = eval(f'tmpList[{keys[0]}]')
        except Exception:
            subList = []

    for e in subList:

        # Add nodes at this level only if key list has been exhausted
        if len(keys) == 1 and isinstance(e,Node):
            retList.append(e)

        # Don't go deeper in tree than the keys provided to avoid over-matching nodes
        elif len(keys) > 1 and isinstance(e,dict):
            retList.extend(_iterateDict(e,keys[1:]))

    return retList


def genBaseList(cls: Any) -> list[str]:
    """Return a list of base class names for a class."""
    ret = [str(cls)]

    for x in cls.__bases__:
        if x is not object:
            ret += genBaseList(x)

    return ret
