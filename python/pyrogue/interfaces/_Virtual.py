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
import zmq
import rogue.interfaces
import functools as ft
import jsonpickle
import re
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
                         groups=attrs['groups'])

        self._path  = attrs['path']
        self._class = attrs['class']
        self._nodes = attrs['nodes']
        self._bases = attrs['bases']

        # Tracking
        self._parent    = None
        self._root      = None
        self._client    = None
        self._functions = []

        # Rebuild array nodes list locally
        for k,v in self._nodes.items():
            self._addArrayNode(v)

        # Setup logging
        self._log = pr.logInit(cls=self,name=self.name,path=self._path)

    def add(self,node):
        raise pr.NodeError('add not supported in VirtualNode')

    def callRecursive(self, func, nodeTypes=None, **kwargs):
        raise pr.NodeError('callRecursive not supported in VirtualNode')

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

    @ft.lru_cache(maxsize=None)
    def _getNode(self,path):
        obj = self

        if '.' in path:
            lst = path.split('.')

            if lst[0] != self.name and lst[0] != 'root':
                return None

            for a in lst[1:]:
                if not hasattr(obj,'node'):
                    return None
                obj = obj.node(a)

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

    def _setDict(self,d,writeEach,modes=['RW']):
        raise pr.NodeError('_setDict not supported in VirtualNode')

    def _doUpdate(self, val):
        for func in self._functions:
            func(self.path,val)

    def _virtAttached(self,parent,root,client):
        """Called once the root node is attached."""
        self._parent = parent
        self._root   = root
        self._client = client

        for key,value in self._nodes.items():
            value._virtAttached(self,root,client)


class VirtualClient(rogue.interfaces.ZmqClient):
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

        rogue.interfaces.ZmqClient.__init__(self,addr,port)
        self._varListeners = []
        self._monitors = []
        self._root  = None
        self._link  = False
        self._ltime = time.time()

        # Setup logging
        self._log = pr.logInit(cls=self,name="VirtualClient",path=None)

        # Get root name as a connection test
        self.setTimeout(1000)
        self._rn = None
        while self._rn is None:
            self._rn = self._remoteAttr('__rootname__',None)

        print("Connected to {} at {}:{}".format(self._rn,addr,port))

        # Try to connect to root entity, long timeout
        print("Getting structure for {}".format(self._rn))
        self.setTimeout(120000)
        r = self._remoteAttr('__structure__', None)
        print("Ready to use {}".format(self._rn))

        # Update tree
        r._virtAttached(r,r,self)
        self._root = r

        setattr(self,self._root.name,self._root)

        # Link tracking
        self._link  = True
        self._root.Time.addListener(self._monListener)
        self._ltime = self._root.Time.value()

    def addLinkMonitor(self, function):
        if not function in self._monitors:
            self._monitors.append(function)
        self._monWorker()

    def remLinkMonitor(self, function):
        if function in self._monitors:
            self._monitors.remove(function)
        self._monWorker()

    @property
    def linked(self):
        return self._link

    def _monListener(self,path,val):
        self._ltime = val.value

    def _monWorker(self):
        if len(self._monitors) == 0: return

        threading.Timer(1.0,self._monWorker).start()

        if self._link and (time.time() - self._ltime) > 1.5:
            self._link = False
            print(f"Link to {self._rn} lost!")
            for mon in self._monitors:
                mon(self._link)

        elif (not self._link) and (time.time() - self._ltime) < 1.5:
            self._link = True
            print(f"Link to {self._rn} restored!")
            for mon in self._monitors:
                mon(self._link)


    def _remoteAttr(self, path, attr, *args, **kwargs):
        snd = { 'path':path, 'attr':attr, 'args':args, 'kwargs':kwargs }
        y = jsonpickle.encode(snd)
        try:
            resp = self._send(y)
            ret = jsonpickle.decode(resp)
        except Exception as msg:
            print("got remote exception: {}".format(msg))
            ret = None

        return ret

    def _addVarListener(self,func):
        if func not in self._varListeners:
            self._varListeners.append(func)

    def _doUpdate(self,data):
        if self._root is None:
            return

        d = jsonpickle.decode(data)

        for k,val in d.items():
            n = self._root.getNode(k)
            if n is None:
                self._log.error("Failed to find node {}".format(k))
            else:
                n._doUpdate(val)

            # Call listener functions,
            for func in self._varListeners:
                func(k,val)

    @property
    def root(self):
        return self._root

    def __hash__(self):
        return hash((self._host, self._port))

    def __eq__(self, other):
        return (self.host, self.port) == (other._host, other._port)

    def __ne__(self, other):
        return not (self == other)
