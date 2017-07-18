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
import Pyro4
import functools as ft
import parse
import collections

def logInit(cls=None,name=None):
    """Init a logging pbject. Set global options."""
    logging.basicConfig(
        #level=logging.NOTSET,
        format="%(levelname)s:%(name)s:%(message)s",
        stream=sys.stdout)

    msg = 'pyrogue'
    if cls: msg += "." + cls.__class__.__name__
    if name: msg += "." + name
    return logging.getLogger(msg)


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
        self._depWarn     = False
        self._expand      = expand

        # Tracking
        self._parent = None
        self._root   = None
        self._nodes  = odict()

        # Setup logging
        self._log = logInit(self,name)

    @Pyro4.expose
    @property
    def name(self):
        return self._name

    @Pyro4.expose
    @property
    def description(self):
        return self._description

    @Pyro4.expose
    @property
    def hidden(self):
        return self._hidden

    @Pyro4.expose
    @property
    def path(self):
        return self._path

    @Pyro4.expose
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

    def add(self,node):
        """Add node as sub-node"""

        # Special case if list (or iterable of nodes) is passed
        if isinstance(node, collections.Iterable) and all(isinstance(n, Node) for n in node):
            for n in node:
                self.add(n)
            return

        # Fail if added to a non device node (may change in future)
        if not isinstance(self,pr.Device):
            raise NodeError('Attempting to add %s with name %s to non device node %s.' % 
                             (str(node.classType),node.name,self.name))

        # Fail if root already exists
        if self._root is not None:
            raise NodeError('Error adding %s with name %s to %s. Tree is already started.' % 
                             (str(node.classType),node.name,self.name))

        # Error if added node already has a parent
        if node._parent is not None:
            raise NodeError('Error adding %s with name %s to %s. Node is already attached.' % 
                             (str(node.classType),node.name,self.name))

        # Names of all sub-nodes must be unique
        if node.name in self._nodes:
            raise NodeError('Error adding %s with name %s to %s. Name collision.' % 
                             (str(node.classType),node.name,self.name))

        self._nodes[node.name] = node 

    def addNode(self, nodeClass, **kwargs):
        self.add(nodeClass(**kwargs))

    def addNodes(self, nodeClass, number, stride, **kwargs):
        name = kwargs.pop('name')
        offset = kwargs.pop('offset')
        for i in range(number):
            self.add(nodeClass(name='{:s}[{:d}]'.format(name, i), offset=offset+(i*stride), **kwargs))

    def _getNodes(self,typ):
        """
        Get a ordered dictionary of nodes.
        pass a class type to receive a certain type of node
        """
        return odict([(k,n) for k,n in self._nodes.items() if isinstance(n, typ)])

    @Pyro4.expose
    @property
    def nodes(self):
        """
        Get a ordered dictionary of all nodes.
        """
        return self._nodes

    @Pyro4.expose
    @property
    def variables(self):
        """
        Return an OrderedDict of the variables but not commands (which are a subclass of Variable
        """
        return odict([(k,n) for k,n in self._nodes.items()
                      if isinstance(n, pr.BaseVariable) and not isinstance(n, pr.BaseCommand)])

    @Pyro4.expose
    @property
    def commands(self):
        """
        Return an OrderedDict of the Commands that are children of this Node
        """
        return self._getNodes(pr.BaseCommand)

    @Pyro4.expose
    @property
    def devices(self):
        """
        Return an OrderedDict of the Devices that are children of this Node
        """
        return self._getNodes(pr.Device)

    @Pyro4.expose
    @property
    def parent(self):
        """
        Return parent node or NULL if no parent exists.
        """
        return self._parent

    @Pyro4.expose
    @property
    def root(self):
        """
        Return root node of tree.
        """
        return self._root

    @Pyro4.expose
    def node(self, path):
        return self._nodes[path]

    def _rootAttached(self,parent,root):
        """Called once the root node is attached."""
        self._parent = parent
        self._root   = root
        self._path   = parent.path + '.' + self.name

    def _exportNodes(self,daemon):
        for k,n in self._nodes.items():
            daemon.register(n)

            if isinstance(n,pr.Device):
                n._exportNodes(daemon)

    def _getVariables(self,modes):
        """
        Get variable values in a dictionary starting from this level.
        Attributes that are Nodes are recursed.
        modes is a list of variable modes to include.
        Called from getYamlVariables in the root node.
        """
        data = odict()
        for key,value in self._nodes.items():
            if isinstance(value,pr.Device):
                data[key] = value._getVariables(modes)
            elif isinstance(value,pr.BaseVariable) and not isinstance(value, pr.BaseCommand) \
                 and (value.mode in modes):
                data[key] = value.valueDisp()

        return data

    def _nodeList(self,name):

        # First check to see if unit matches a node name
        # needed when [ and ] are in a variable or device name
        if name in self._nodes:
            return [self._nodes[name]]

        fields = re.split('\[|\]',name)

        # Wildcard
        if len(fields) > 1 and fields[1] == '*':
            return self._nodeList(fields[0])
        else:
            ah = attrHelper(self._nodes,fields[0])

            if ah is None:
                return []

            # Single entry returned
            elif not isinstance(ah,odict):

                # Should be indexed
                if len(fields) > 1:
                    return []
                else:
                    return [ah]

            # Indexed ordered dictionary returned
            # Convert to list with gaps = None
            else:
                idxLast = list(ah.items())[-1][0] # Last index
                if not isinstance(idxLast,int):
                    return []

                ret = [None] * (idxLast+1)
                for i,n in ah.items():
                    ret[i] = n

                if len(fields) > 1:
                    r =  eval('ret[{}]'.format(fields[1]))
                    if isinstance(r,collections.Iterable):
                        return r
                    else:
                        return [r]
                else:
                    return ret
         
    def _getDepWarn(self):
        ret = []

        if self._depWarn:
            ret += [self.path]

        for key,value in self._nodes.items():
            ret += value._getDepWarn()

        return ret

    def _setOrExec(self,d,writeEach,modes):
        """
        Set variable values or execute commands from a dictionary starting 
        from this level.  Attributes that are Nodes are recursed.
        modes is a list of variable nodes to act on for variable accesses.
        Called from setOrExecYaml in the root node.
        """
        for key, value in d.items():
            nlist = self._nodeList(key)

            if len(nlist) == 0:
                self._log.error("Entry {} not found".format(key))
            else:
                for n in nlist:

                    # If entry is a device, recurse
                    if isinstance(n,pr.Device):
                        n._setOrExec(value,writeEach,modes)

                    # Execute if command
                    elif isinstance(n,pr.BaseCommand):
                        n.call(value)

                    # Set value if variable with enabled mode
                    elif isinstance(n,pr.BaseVariable) and (n.mode in modes):
                        n.setDisp(value,writeEach)


class PyroNode(object):
    def __init__(self, *, node,daemon):
        self._node   = node
        self._nodes  = None
        self._daemon = daemon

    def __repr__(self):
        return self._node.path

    def __getattr__(self, name):
        if self._nodes is None:
            self._nodes = self._convert(self._node.nodes)

        ret = attrHelper(self._nodes,name)
        if ret is None:
            return self._node.__getattr__(name)
        else:
            return ret

    def __dir__(self):
        if self._nodes is None:
            self._nodes = self._convert(self._node.nodes)

        return(super().__dir__() + [k for k,v in self._nodes.items()])

    def _convert(self,d):
        ret = odict()
        for k,n in d.items():

            if isinstance(n,dict):
                ret[k] = PyroNode(node=Pyro4.util.SerializerBase.dict_to_class(n),daemon=self._daemon)
            else:
                ret[k] = PyroNode(node=n,daemon=self._daemon)

        return ret

    def attr(self,attr,**kwargs):
        return self.__getattr__(attr)(**kwargs)

    def addInstance(self,node):
        self._daemon.register(node)

    def node(self, path):
        return PyroNode(node=self._node.node(path),daemon=self._daemon)

    @property
    def nodes(self):
        return self._convert(self._node.nodes)

    @property
    def variables(self):
        return self._convert(self._node.variables)

    @property
    def commands(self):
        return self._convert(self._node.commands)

    @property
    def devices(self):
        return self._convert(self._node.devices)

    @property
    def parent(self):
        return PyroNode(node=self._node.parent,daemon=self._daemon)

    @property
    def root(self):
        return pr.PyroRoot(self._node.root,self._daemon)

    def addListener(self, listener):
        self._daemon.register(listener)
        self._node.addListener(listener)

    def __call__(self,arg=None):
        self._node.call(arg)


def attrHelper(nodes,name):
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

