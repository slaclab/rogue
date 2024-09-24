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
import sys
from collections import OrderedDict as odict
import logging
import re
import inspect
import pyrogue as pr
import collections


def logException(log,e):
    """
    logs instances of memory error, else, will log the exception.

    Parameters
    ----------
    log :
        calls command to log instance of memory error or exception
    e :
        stores values of memory errors or exceptions

    Returns
    -------
    none
    """
    if isinstance(e,pr.MemoryError):
        log.error(e)
    else:
        log.exception(e)


def logInit(cls=None,name=None,path=None):
    """
    logs base classes in order of highest ranking class. Checks values of  cls, name, and path, if their value is not  =None, will do something

    Parameters
    ----------
    cls :
         (Default value = None)
    name :
         (Default value = None)
    path :
         (Default value = None)

    Returns
    -------
    returns logger
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


def expose(item):
    """
    Allows user to interface with function under item parameter

    Parameters
    ----------
    item :


    Returns
    -------
    returns item
    """

    # Property
    if inspect.isdatadescriptor(item):
        item.fget._rogueExposed = True
        return item

    # Method
    item._rogueExposed = True
    return item


class NodeError(Exception):
    """ """
    pass


class Node(object):
    """
    Class which serves as a managed object within the pyrogue package.
    Each node has the following public fields:
        name: Global name of object
        description: Description of the object.
        groups: Group or groups this node belongs to.
           Examples: 'Hidden', 'NoState', 'NoConfig', 'NoStream', 'NoSql', 'NoServe'
        classtype: text string matching name of node sub-class
        path: Full path to the node (ie. node1.node2.node3)

    Each node is associated with a parent and has a link to the top node of a tree.
    A node has a list of sub-nodes as well as each sub-node being attached as an
    attribute. This allows tree browsing using: node1.node2.node3

    Parameters
    ----------
    name :
        global name of object

    description :
        Description of object

    path :
        full path to the node (ie. node1.node2.node3)

    expand :

    guiGroup :
        arbitrary groups for gui and graphical aesthetic purposes
    Returns
    -------

    """
    _nodeCount = 0

    def __init__(self, *, name, description="", expand=True, hidden=False, groups=None, guiGroup=None):
        """
        Init the node with passed attributes

        Parameters
        ----------
        name : str
            name of variable

        description : str
            description of variable

        expand : bool


        hidden : bool
            Default value = False, variable is not part of hidden group

        groups :


        guiGroup :


        Returns
        -------

        """
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

    def __repr__(self):
        return f'{self.__class__} - {self.path}'

    @property
    def nodeCount(self):
        return pr.Node._nodeCount

    @property
    def name(self):
        """
        assigns and returns name attribute to class variable
        """
        return self._name

    @property
    def description(self):
        """
        assigns and returns description attribute to class variable
        """
        return self._description

    @property
    def groups(self):
        """
        assigns and returns groups attribute to class variable
        """
        return self._groups

    def inGroup(self, group):
        """


        Parameters
        ----------
        group :


        Returns
        -------
        """
        if isinstance(group,list):
            return len(set(group) & set(self._groups)) > 0
        else:
            return group in self._groups

    def filterByGroup(self, incGroups, excGroups):
        """
        Filter by the passed list of inclusion and exclusion groups

        Parameters
        ----------
        incGroups :
            list of passed inclusion groups
        excGroups :
            list of passed exclusion groups

        Returns
        -------

        """
        return ((incGroups is None) or (len(incGroups) == 0) or (self.inGroup(incGroups))) and \
               ((excGroups is None) or (len(excGroups) == 0) or (not self.inGroup(excGroups)))

    def addToGroup(self,group):
        """
        Add this node to the passed group, recursive to children

        Parameters
        ----------
        group :
            variable denoting a node that has not been passed

        Returns
        -------

        """
        if group not in self._groups:
            self._groups.append(group)

        for k,v in self._nodes.items():
            v.addToGroup(group)

    def removeFromGroup(self,group):
        """
        Remove this node from the passed group, not recursive

        Parameters
        ----------
        group :
            variable denoting a node that is in the passed group

        Returns
        -------
        if in group, remove from group
        """
        if group in self._groups:
            self._groups.remove(group)

    @property
    def hidden(self):
        """
        assigns and returns hidden attribute to class variable
        """
        return self.inGroup('Hidden')

    @hidden.setter
    def hidden(self, value):
        """
        Add or remove node from the Hidden group

        Parameters
        ----------
        value : bool
            Boolean value assigned to the Hidden group

        Returns
        -------
        if value = true, add to group, else remove from group
        """
        if value is True:
            self.addToGroup('Hidden')
        else:
            self.removeFromGroup('Hidden')

    @property
    def path(self):
        """ """
        return self._path

    @property
    def expand(self):
        """ """
        return self._expand

    @property
    def guiGroup(self):
        """ """
        return self._guiGroup

    def __getattr__(self, name):
        """
        Allow child Nodes with the 'name[key]' naming convention to be accessed as if they belong to a
        dictionary of Nodes with that 'name'.
        Raises AttributeError if no such named Nodes are found.

        Parameters
        ----------

        name : str
            builds an OrderedDict of all child nodes named as 'name[key]' and returns it.
        Returns
        -------

        """

        # Node matches name in node list
        if name in self._nodes:
            return self._nodes[name]

        # Node matches name in node dictionary list
        elif name in self._anodes:
            return self._anodes[name]

        else:
            raise AttributeError('{} has no attribute {}'.format(self, name))


    def __dir__(self):
        return super().__dir__() + [k for k,v in self._nodes.items()]

    def __reduce__(self):
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

    def __contains__(self, item):
        return item in self.nodes.values()

    def add(self,node):
        """
        Add node as sub-node

        Parameters
        ----------
        node :


        Returns
        -------

        """

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

    def _addArrayNode(self, node):
        """


        Parameters
        ----------
        node :


        Returns
        -------

        """

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


    def addNode(self, nodeClass, **kwargs):
        """


        Parameters
        ----------
        nodeClass :

        **kwargs :


        Returns
        -------

        """
        self.add(nodeClass(**kwargs))

    def addNodes(self, nodeClass, number, stride, **kwargs):
        """


        Parameters
        ----------
        nodeClass :

        number :

        stride :

        **kwargs :


        Returns
        -------

        """
        name = kwargs.pop('name')
        offset = kwargs.pop('offset')
        for i in range(number):
            self.add(nodeClass(name='{:s}[{:d}]'.format(name, i), offset=offset+(i*stride), **kwargs))

    @property
    def nodeList(self):
        """Get a recursive list of nodes."""
        lst = []
        for key,value in self._nodes.items():
            lst.append(value)
            lst.extend(value.nodeList)
        return lst

    def getNodes(self,typ,excTyp=None,incGroups=None,excGroups=None):
        """
        Get a filtered ordered dictionary of nodes.
        pass a class type to receive a certain type of node
        class type may be a string when called over Pyro4
        exc is a class type to exclude,
        incGroups is an optional group or list of groups that this node must be part of
        excGroups is an optional group or list of groups that this node must not be part of

        Parameters
        ----------
        typ :

        excTyp :
             (Default value = None)
        incGroups :
             (Default value = None)
        excGroups :
             (Default value = None)

        Returns
        -------
        ordered dictionary of nodes
        """
        return odict([(k,n) for k,n in self.nodes.items()
                      if (n.isinstance(typ) and ((excTyp is None) or (not n.isinstance(excTyp))) and n.filterByGroup(incGroups,excGroups))])

    @property
    def nodes(self):
        """Get a ordered dictionary of all nodes."""
        return self._nodes

    @property
    def variables(self):
        """ """
        return self.getNodes(typ=pr.BaseVariable,excTyp=pr.BaseCommand)

    def variablesByGroup(self,incGroups=None,excGroups=None):
        """


        Parameters
        ----------
        incGroups :
             (Default value = None)
        excGroups :
             (Default value = None)

        Returns
        -------
        type
            Pass list of include and / or exclude groups

        """
        return self.getNodes(typ=pr.BaseVariable,excTyp=pr.BaseCommand,incGroups=incGroups,excGroups=excGroups)

    @property
    def variableList(self):
        """Get a recursive list of variables and commands."""
        lst = []
        for key,value in self.nodes.items():
            if value.isinstance(pr.BaseVariable):
                lst.append(value)
            else:
                lst.extend(value.variableList)
        return lst

    @property
    def commands(self):
        """ """
        return self.getNodes(typ=pr.BaseCommand)

    def commandsByGroup(self,incGroups=None,excGroups=None):
        """


        Parameters
        ----------
        incGroups :
             (Default value = None)
        excGroups :
             (Default value = None)

        Returns
        -------
        type
            Pass list of include and / or exclude groups

        """
        return self.getNodes(typ=pr.BaseCommand,incGroups=incGroups,excGroups=excGroups)

    @property
    def devices(self):
        """ """
        return self.getNodes(pr.Device)

    def devicesByGroup(self,incGroups=None,excGroups=None):
        """


        Parameters
        ----------
        incGroups :
             (Default value = None)
        excGroups :
             (Default value = None)

        Returns
        -------
        type
            Pass list of include and / or exclude groups

        """
        return self.getNodes(pr.Device,incGroups=incGroups,excGroups=excGroups)

    @property
    def deviceList(self):
        """Get a recursive list of devices"""
        lst = []
        for key,value in self.nodes.items():
            if value.isinstance(pr.Device):
                lst.append(value)
                lst.extend(value.deviceList)
        return lst

    @property
    def parent(self):
        """ """
        return self._parent

    @property
    def root(self):
        """ """
        return self._root

    def node(self, name):
        """


        Parameters
        ----------
        name :


        Returns
        -------

        """
        if name in self._nodes:
            return self._nodes[name]
        else:
            return None

    @property
    def isDevice(self):
        """ """
        return self.isinstance(pr.Device)

    @property
    def isVariable(self):
        """ """
        return (self.isinstance(pr.BaseVariable) and (not self.isinstance(pr.BaseCommand)))

    @property
    def isCommand(self):
        """ """
        return self.isinstance(pr.BaseCommand)

    def find(self, *, recurse=True, typ=None, **kwargs):
        """
        Find all child nodes that are a base class of 'typ'
        and whose properties match all of the kwargs.
        For string properties, accepts regexes.

        Parameters
        ----------
        * :

        recurse :
             (Default value = True)
        typ :
             (Default value = None)
        **kwargs :


        Returns
        -------

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

    def callRecursive(self, func, nodeTypes=None, **kwargs):
        """


        Parameters
        ----------
        func :

        nodeTypes :
             (Default value = None)
        **kwargs :


        Returns
        -------

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
    def makeRecursive(self, func, nodeTypes=None):
        """


        Parameters
        ----------
        func :

        nodeTypes :
             (Default value = None)

        Returns
        -------

        """
        def closure(**kwargs):
            """


            Parameters
            ----------
            **kwargs :


            Returns
            -------

            """
            self.callRecursive(func, nodeTypes, **kwargs)
        return closure

    def isinstance(self,typ):
        """


        Parameters
        ----------
        typ :


        Returns
        -------

        """
        return isinstance(self,typ)

    def _rootAttached(self,parent,root):
        """
        Called once the root node is attached.

        Parameters
        ----------
        parent :

        root :


        Returns
        -------

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
    def getYaml(self, readFirst=False, modes=['RW','RO','WO'], incGroups=None, excGroups=['Hidden'], recurse=True):

        """
        Get current values as yaml data.
        modes is a list of variable modes to include.
        If readFirst=True a full read from hardware is performed.
        """
        if readFirst:
            self.root._read()
        return pr.dataToYaml({self.name:self._getDict(modes=modes, incGroups=incGroups, excGroups=excGroups, recurse=recurse)})

    def printYaml(self, readFirst=False, modes=['RW','RO','WO'], incGroups=None, excGroups=['Hidden'], recurse=False):
        print(self.getYaml(readFirst=readFirst, modes=modes, incGroups=incGroups, excGroups=excGroups, recurse=recurse))

    def _getDict(self, modes=['RW', 'RO', 'WO'], incGroups=None, excGroups=None, properties=False, recurse=True):
        """
        Get variable values in a dictionary starting from this level.
        Attributes that are Nodes are recursed.
        modes is a list of variable modes to include.

        Parameters
        ----------
        modes :

        incGroups :

        excGroups :


        Returns
        -------

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

    def _setDict(self,d,writeEach,modes,incGroups,excGroups,keys):
        """


        Parameters
        ----------
        d :

        writeEach :

        modes :

        incGroups :

        excGroups :

        keys :


        Returns
        -------

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

    def _setTimeout(self,timeout):
        """


        Parameters
        ----------
        timeout :


        Returns
        -------

        """
        pass

    def nodeMatch(self,name):
        """


        Parameters
        ----------
        name :


        Returns
        -------
        type
            be a single value or a list accessor:
            value
            value[9]
            value[0:1]
            value[*]
            value[:]
            Variables will only match if their depth matches the passed lookup and wildcard:
            value[*] will match a variable named value[1] but not a variable named value[2][3]
            value[*][*] will match a variable named value[2][3].
            The second return field will contain the array information if the base name
            matches an item in the non list array.

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


def _iterateDict(d, keys):
    """


    Parameters
    ----------
    d :

    keys :


    Returns
    -------

    """
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


def genBaseList(cls):
    """ """
    ret = [str(cls)]

    for x in cls.__bases__:
        if x is not object:
            ret += genBaseList(x)

    return ret
