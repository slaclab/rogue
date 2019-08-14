#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Title      : PyRogue base module - Node Classes
#-----------------------------------------------------------------------------
# File       : pyrogue/_Node.py
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
import sys
from collections import OrderedDict as odict
import logging
import re
import inspect
import pyrogue as pr
import functools as ft
import parse
import collections

def logInit(cls=None,name=None,path=None):

    # Support base class in order of precedence
    baseClasses = odict({pr.BaseCommand : 'Command', pr.BaseVariable : 'Variable',
                         pr.BaseBlock : 'Block', pr.Root : 'Root', pr.Device : 'Device'})

    """Init a logging pbject. Set global options."""
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

    # Property
    if inspect.isdatadescriptor(item):
        func = item.fget._rogueExposed = True
        return item

    # Method
    item._rogueExposed = True
    return item


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


    def __init__(self, *, name, description="", expand=True, hidden=False):
        """Init the node with passed attributes"""

        # Public attributes
        self._name        = name
        self._description = description
        self._hidden      = hidden
        self._path        = name
        self._expand      = expand

        # Tracking
        self._parent  = None
        self._root    = None
        self._nodes   = odict()

        # Setup logging
        self._log = logInit(cls=self,name=name,path=None)

    @property
    def name(self):
        return self._name

    @property
    def description(self):
        return self._description

    @property
    def hidden(self):
        return self._hidden

    @hidden.setter
    def hidden(self, value):
        self._hidden = value

    @property
    def path(self):
        return self._path

    @property
    def expand(self):
        return self._expand

    def __repr__(self):
        return self.path

    def __getattr__(self, name):
        """Allow child Nodes with the 'name[key]' naming convention to be accessed as if they belong to a 
        dictionary of Nodes with that 'name'.
        This override builds an OrderedDict of all child nodes named as 'name[key]' and returns it.
        Raises AttributeError if no such named Nodes are found. """

        ret = attrHelper(self._nodes,name)
        if ret is None:
            raise AttributeError('{} has no attribute {}'.format(self, name))
        else:
            return ret

    def __dir__(self):
        return(super().__dir__() + [k for k,v in self._nodes.items()])

    def __reduce__(self):
        attr = {}

        attr['name']        = self._name
        attr['class']       = self.__class__.__name__
        attr['bases']       = pr.genBaseList(self.__class__)
        attr['description'] = self._description
        attr['hidden']      = self._hidden
        attr['path']        = self._path
        attr['expand']      = self._expand
        attr['nodes']       = self._nodes
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

        return (pr.VirtualFactory, (attr,))

    def __contains__(self, item):
        return item in self._nodes.values()

    def add(self,node):
        """Add node as sub-node"""

        # Special case if list (or iterable of nodes) is passed
        if isinstance(node, collections.Iterable) and all(isinstance(n, Node) for n in node):
            for n in node:
                self.add(n)
            return

        # Fail if added to a non device node (may change in future)
        if not isinstance(self,pr.Device):
            raise NodeError('Attempting to add node with name %s to non device node %s.' % 
                             (node.name,self.name))

        # Fail if root already exists
        if self._root is not None:
            raise NodeError('Error adding node with name %s to %s. Tree is already started.' % 
                             (node.name,self.name))

        # Error if added node already has a parent
        if node._parent is not None:
            raise NodeError('Error adding node with name %s to %s. Node is already attached.' % 
                             (node.name,self.name))

        # Names of all sub-nodes must be unique
        if node.name in self.__dir__():
            raise NodeError('Error adding node with name %s to %s. Name collision.' % 
                             (node.name,self.name))

        self._nodes[node.name] = node 

    def addNode(self, nodeClass, **kwargs):
        self.add(nodeClass(**kwargs))

    def addNodes(self, nodeClass, number, stride, **kwargs):
        name = kwargs.pop('name')
        offset = kwargs.pop('offset')
        for i in range(number):
            self.add(nodeClass(name='{:s}[{:d}]'.format(name, i), offset=offset+(i*stride), **kwargs))
    
    @property
    def nodeList(self):
        return([k for k,v in self._nodes.items()])

    def getNodes(self,typ,exc=None,hidden=True):
        """
        Get a ordered dictionary of nodes.
        pass a class type to receive a certain type of node
        class type may be a string when called over Pyro4
        exc is a class type to exclude, if hidden = False, only visable nodes are returned
        """
        return odict([(k,n) for k,n in self._nodes.items() \
            if (n.isinstance(typ) and ((exc is None) or (not n.isinstance(exc))) and (hidden or n.hidden == False))])

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
        return self.getNodes(typ=pr.BaseVariable,exc=pr.BaseCommand,hidden=True)

    @property
    def visableVariables(self):
        """
        Return an OrderedDict of the variables but not commands (which are a subclass of Variable
        """
        return self.getNodes(typ=pr.BaseVariable,exc=pr.BaseCommand,hidden=False)

    @property
    def variableList(self):
        """
        Get a recursive list of variables and commands.
        """
        lst = []
        for key,value in self._nodes.items():
            if value.isinstance(pr.BaseVariable):
                lst.append(value)
            else:
                lst.extend(value.variableList)
        return lst

    @property
    def deviceList(self):
        """
        Get a recursive list of devices
        """
        lst = []
        for key,value in self._nodes.items():
            if value.isinstance(pr.Device):
                lst.append(value)
                lst.extend(value.deviceList)
        return lst

    @property
    def commands(self):
        """
        Return an OrderedDict of the Commands that are children of this Node
        """
        return self.getNodes(pr.BaseCommand,hidden=True)

    @property
    def visableCommands(self):
        """
        Return an OrderedDict of the Commands that are children of this Node
        """
        return self.getNodes(pr.BaseCommand,hidden=False)

    @property
    def devices(self):
        """
        Return an OrderedDict of the Devices that are children of this Node
        """
        return self.getNodes(pr.Device,hidden=True)

    @property
    def visableDevices(self):
        """
        Return an OrderedDict of the Devices that are children of this Node
        """
        return self.getNodes(pr.Device,hidden=False)

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

    def node(self, path):
        return attrHelper(self._nodes,path)

    @property
    def isDevice(self):
        return self.isinstance(pr.Device)

    @property
    def isVariable(self):
        return (self.isinstance(pr.BaseVariable) and (not self.isinstance(pr.BaseCommand)))

    @property
    def isCommand(self):
        return self.isinstance(pr.BaseCommand)

    def find(self, *, recurse=True, typ=None, **kwargs):
        """ 
        Find all child nodes that are a base class of 'typ'
        and whose properties match all of the kwargs.
        For string properties, accepts regexes.
        """
    
        if typ is None:
            typ = pr.Node

        found = []
        for node in self._nodes.values():
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
        # Call the function
        getattr(self, func)(**kwargs)

        if nodeTypes is None:
            nodeTypes = [pr.Node]

        # Recursively call the function
        for key, node in self._nodes.items():
            if any(isinstance(node, typ) for typ in nodeTypes):
                node.callRecursive(func, nodeTypes, **kwargs)

    # this might be useful
    def makeRecursive(self, func, nodeTypes=None):
        def closure(**kwargs):
            self.callRecursive(func, nodeTypes, **kwargs)
        return closure

    def isinstance(self,typ):
        return isinstance(self,typ)

    def _rootAttached(self,parent,root):
        """Called once the root node is attached."""
        self._parent = parent
        self._root   = root
        self._path   = parent.path + '.' + self.name
        self._log    = logInit(cls=self,name=self._name,path=self._path)

    def _exportNodes(self,daemon):
        for k,n in self._nodes.items():
            daemon.register(n)
            n._exportNodes(daemon)

    def _getDict(self,modes):
        """
        Get variable values in a dictionary starting from this level.
        Attributes that are Nodes are recursed.
        modes is a list of variable modes to include.
        """
        data = odict()
        for key,value in self._nodes.items():
            nv = value._getDict(modes)
            if nv is not None:
                data[key] = nv

        if len(data) == 0:
            return None
        else:
            return data

    def _setDict(self,d,writeEach,modes=['RW']):
        for key, value in d.items():
            nlist = nodeMatch(self._nodes,key)

            if nlist is None or len(nlist) == 0:
                self._log.error("Entry {} not found".format(key))
            else:
                for n in nlist:
                    n._setDict(value,writeEach,modes)

    def _setTimeout(self,timeout):
        pass


def attrHelper(nodes,name):
    """
    Return a single item or a list of items matching the passed

    name. If the name is an exact match to a single item in the list
    then return it. Otherwise attempt to find items which match the 
    passed name, but are array entries: name[n]. Return these items
    as a list
    """
    if name in nodes:
        return nodes[name]
    else:
        ret = odict()
        rg = re.compile('{:s}\\[(.*?)\\]'.format(name))
        for k,v in nodes.items():
            m = rg.match(k)
            if m:
                key = m.group(1)
                if key.isdigit():
                    key = int(key)
                ret[key] = v

        if len(ret) == 0:
            return None
        else:
            return ret


def nodeMatch(nodes,name):
    """
    Return a list of nodes which match the given name. The name can either
    be a single value or a list accessor:
        value
        value[9]
        value[0:1]
        value[*]
    """

    # First check to see if unit matches a node name
    # needed when [ and ] are in a variable or device name
    if name in nodes:
        return [nodes[name]]

    fields = re.split('\[|\]',name)

    # Wildcard
    if len(fields) > 1 and (fields[1] == '*' or fields[1] == ':'):
        return nodeMatch(nodes,fields[0])
    else:
        ah = attrHelper(nodes,fields[0])

        # None or exact match is an error
        if ah is None or not isinstance(ah,odict):
            return None

        # Non integer keys is an error
        if any(not isinstance(k,int) for k in ah.keys()):
            return None

        # no slicing, return list
        if len(fields) == 1:
            return [v for k,v in ah.items()]

        # Indexed ordered dictionary returned
        # Convert to list with gaps = None and apply slicing
        idxLast = max(ah)

        ret = [None] * (idxLast+1)
        for i,n in ah.items():
            ret[i] = n

        try:
            r = eval('ret[{}]'.format(fields[1]))
        except:
            r = None

        if r is None or any(v == None for v in r):
            return None
        elif isinstance(r,collections.Iterable):
            return r
        else:
            return [r]


