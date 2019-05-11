#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Title      : PyRogue base module - Virtual Classes
#-----------------------------------------------------------------------------
# File       : pyrogue/_Virtual.py
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
import inspect
import pyrogue as pr


def genBaseList(cls):
    ret = [str(cls)]

    for l in cls.__bases__:
        if l is not object:
            ret += genBaseList(l)

    return ret


class VirtualProperty(object):
    def __init__(self, node, attr):
        self._attr = attr
        self._node = node

    def __get__(self, obj=None, objtype=None):
        print("VirtualProperty get node={}, obj={}, objtype={}, attr={}".format(self._node,obj,objtype,self._attr))
        return 1

    def __set__(self, obj, value):
        pass


class VirtualMethod(object):
    def __init__(self, node, attr, info):
        self._attr   = attr
        self._node   = node
        self._args   = info['args']
        self._kwargs = info['kwargs']

    def __call__(self, *args, **kwargs):
        print("VirtualMethod: attr={}, node={}, args={}, kwargs={}".format(self._attr,self._node,args,kwargs))
        return 1


def VirtualFactory(data):

    def __init__(self,data):

        # Add dynamic methods
        for k,v in data['funcs'].items():
            setattr(self.__class__,k,VirtualMethod(self,k,v))

        # Add dynamic properties
        for k in data['props']:
            setattr(self.__class__,k,VirtualProperty(self,k))

        VirtualNode.__init__(self,data)

    newclass = type('Virtual' + data['class'], (VirtualNode,), {"__init__": __init__})
    return newclass(data)


class VirtualNode(pr.Node):
    def __init__(self, attrs):
        super().__init__(name=attrs['name'], 
                         description=attrs['description'], 
                         expand=attrs['expand'], 
                         hidden=attrs['hidden'])

        self._path  = attrs['path']
        self._class = attrs['class']

        self._nodes = {k:None for k in attrs['nodes']}
        self._bases = attrs['bases']

        # Tracking
        self._parent  = None
        self._root    = None

        # Setup logging
        self._log = pr.logInit(cls=self,name=self.name,path=self._path)

    def __getattr__(self, name):

        ret = pr.attrHelper(self._nodes,name)
        if ret is None:
            raise AttributeError('{} has no attribute {}'.format(self, name))
        else:
            return ret

    def __dir__(self):
        return(super().__dir__() + [k for k,v in self._nodes.items()])

    def add(self,node):
        raise NodeError('add not supported in VirtualNode')

    def find(self, *, recurse=True, typ=None, **kwargs):
        raise NodeError('find not supported in VirtualNode')

    def callRecursive(self, func, nodeTypes=None, **kwargs):
        raise NodeError('callRecursive not supported in VirtualNode')

    def addListener(self, listener):
        pass

    def addVarListener(self,func):
        pass

    def _isinstance(self,typ):
        cs = str(typ)
        return cs in self._bases

    def _rootAttached(self,parent,root):
        raise NodeError('_rootAttached not supported in VirtualNode')

    def _getDict(self,modes):
        raise NodeError('_getDict not supported in VirtualNode')

    def _setDict(self,d,writeEach,modes=['RW']):
        raise NodeError('_setDict not supported in VirtualNode')

#class PyroRoot(pr.PyroNode):
#    def __init__(self, *, node,daemon):
#        pr.PyroNode.__init__(self,root=self,node=node,daemon=daemon)
#
#        self._varListeners   = []
#        self._relayListeners = {}
#
#    def addInstance(self,node):
#        self._daemon.register(node)
#
#    def getNode(self, path):
#        return pr.PyroNode(root=self,node=self._node.getNode(path),daemon=self._daemon)
#
#    def addVarListener(self,listener):
#        self._varListeners.append(listener)
#
#    def _addRelayListener(self, path, listener):
#        if not path in self._relayListeners:
#            self._relayListeners[path] = []
#
#        self._relayListeners[path].append(listener)
#
#    @pr.expose
#    def varListener(self, path, value, disp):
#        for f in self._varListeners:
#            f.varListener(path=path, value=value, disp=disp)
#
#        if path in self._relayListeners:
#            for f in self._relayListeners[path]:
#                f.varListener(path=path, value=value, disp=disp)
#
#class PyroClient(object):
#    def __init__(self, group, localAddr=None, nsAddr=None):
#        self._group = group
#
#        Pyro4.config.THREADPOOL_SIZE = 100
#        Pyro4.config.SERVERTYPE = "multiplex"
#        Pyro4.config.POLLTIMEOUT = 3
#
#        Pyro4.util.SerializerBase.register_dict_to_class("collections.OrderedDict", recreate_OrderedDict)
#
#        if nsAddr is None:
#            nsAddr = localAddr
#
#        try:
#            self._ns = Pyro4.locateNS(host=nsAddr)
#        except:
#            raise pr.NodeError("PyroClient Failed to find nameserver")
#
#        self._pyroDaemon = Pyro4.Daemon(host=localAddr)
#
#        self._pyroThread = threading.Thread(target=self._pyroDaemon.requestLoop)
#        self._pyroThread.start()
#
#    def stop(self):
#        self._pyroDaemon.shutdown()
#
#    def getRoot(self,name):
#        try:
#            uri = self._ns.lookup("{}.{}".format(self._group,name))
#            ret = PyroRoot(node=Pyro4.Proxy(uri),daemon=self._pyroDaemon)
#            self._pyroDaemon.register(ret)
#
#            ret._node.addVarListener(ret)
#            return ret
#        except:
#            raise pr.NodeError("PyroClient Failed to find {}.{}.".format(self._group,name))

