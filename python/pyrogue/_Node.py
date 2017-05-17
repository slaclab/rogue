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

    def __init__(self, name, description="", hidden=False, parent=None):
        """Init the node with passed attributes"""

        # Public attributes
        self.name        = name
        self.description = description
        self.hidden      = hidden
        self.classType   = type(self)
        self.classList   = inspect.getmro(type(self))
        self.path        = self.name

        # Tracking
        self._parent = parent
        self._root   = self
        self._nodes  = odict()

        # Setup logging
        self._log = logInit(self,name)

        if parent is not None:
            parent.add(self)

    def __repr__(self):
        return self.path

    def __getattr__(self, name):
        """Allow child Nodes with the 'name[key]' naming convention to be accessed as if they belong to a 
        dictionary of Nodes with that 'name'.
        This override builds an OrderedDict of all child nodes named as 'name[key]' and returns it.
        Raises AttributeError if no such named Nodes are found. """

        ret = odict()
        rg = re.compile('{:s}\\[(.*?)\\]'.format(name))
        for k,v in self._nodes.items():
            m = rg.match(k)
            if m:
                key = m.group(1)
                if key.isdigit():
                    key = int(key)
                ret[key] = v

        if len(ret) == 0:
            raise AttributeError('{} has no attribute {}'.format(self, name))

        return ret

    def add(self,node):
        """Add node as sub-node"""

        # Names of all sub-nodes must be unique
        if node.name in self._nodes:
            raise NodeError('Error adding %s with name %s to %s. Name collision.' % 
                             (str(node.classType),node.name,self.name))

        # Attach directly as attribute and add to ordered node dictionary
        setattr(self,node.name,node)
        self._nodes[node.name] = node

        # Update path related attributes
        node._updateTree(self)

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
        return odict([(k,n) for k,n in self._nodes.items()
                      if isinstance(n, pr.BaseVariable) and not isinstance(n, pr.BaseCommand)])

    @property
    def commands(self):
        """
        Return an OrderedDict of the Commands that are children of this Node
        """
        return self._getNodes(pr.BaseCommand)

    @property
    def devices(self):
        """
        Return an OrderedDict of the Devices that are children of this Node
        """
        return self._getNodes(pr.Device)

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

    def getNode(self, path):
        """Find a node in the tree that has a particular path string"""
        obj = self
        for a in path.split('.')[1:]:
            obj = getattr(obj, a)
        return obj

    def _rootAttached(self):
        """Called once the root node is attached. Can override to do anything depends on the full tree existing"""
        pass

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

        if isinstance(self._root, pr.Root):
            self._rootAttached()

        for key,value in self._nodes.items():
            value._updateTree(self)

    def _getStructure(self):
        """
        Get structure starting from this level.
        Attributes that are Nodes are recursed.
        Called from getYamlStructure in the root node.
        """
        data = odict()

        # First get non-node local values
        for key,value in self.__dict__.items():
            if (not key.startswith('_')) and (not isinstance(value,Node)) and (not callable(value)):
                data[key] = value

        # Next get sub nodes
        for key,value in self.nodes.items():
            data[key] = value._getStructure()

        return data

    def _addStructure(self,d,setFunction,cmdFunction):
        """
        Creation structure from passed dictionary. Used for clients.
        Blocks are not created and functions are set to the passed values.
        """
        for key, value in d.items():

            # Only work on nodes
            if isinstance(value,dict) and 'classType' in value:

                # If entry is a device add and recurse
                if pyrogue._Device.Device in value['classList']:
                    dev = pr.Device(**value)
                    dev.classType = value['classType']
                    dev.classList = value['classList']
                    self.add(dev)
                    dev._addStructure(value,setFunction,cmdFunction)

                # If entry is a variable add and recurse
                elif pyrogue._Command.BaseCommnd in value['classList']:
                    if not value['name'] in self._nodes:
                        value['function'] = cmdFunction
                        cmd = pr.BaseCommand(**value)
                        dev.classType = value['classType']
                        dev.classList = value['classList']
                        self.add(cmd)
                    else:
                        getattr(self,value['name'])._function = cmdFunction

                # If entry is a variable add and recurse
                elif value['classType'] == 'variable':
                    if not value['name'] in self._nodes:
                        value['setLocal'] = setFunction
                        var = pr.LocalVariable(**value)
                        dev.classType = value['classType']
                        dev.classList = value['classList']
                        self.add(var)
                    else:
                        getattr(self,value['name'])._setFunction = setFunction

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
            elif isinstance(value,pr.BaseVariable) and (value.mode in modes):
                data[key] = value.get(read=False)

        return data

    def _setOrExec(self,d,writeEach,modes):
        """
        Set variable values or execute commands from a dictionary starting 
        from this level.  Attributes that are Nodes are recursed.
        modes is a list of variable nodes to act on for variable accesses.
        Called from setOrExecYaml in the root node.
        """
        for key, value in d.items():

            # Entry is in node list
            if key in self._nodes:

                # If entry is a device, recurse
                if isinstance(self._nodes[key],pr.Device):
                    self._nodes[key]._setOrExec(value,writeEach,modes)

                # Execute if command
                elif isinstance(self._nodes[key],pr.BaseCommand):
                    self._nodes[key](value)

                # Set value if variable with enabled mode
                elif isinstance(self._nodes[key],pr.BaseVariable) and (self._nodes[key].mode in modes):
                    self._nodes[key].set(value,writeEach)

