#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Title      : PyRogue mesh support
#-----------------------------------------------------------------------------
# File       : pyrogue/mesh.py
# Author     : Ryan Herbst, rherbst@slac.stanford.edu
# Created    : 2016-09-29
# Last update: 2016-09-29
#-----------------------------------------------------------------------------
# Description:
# Module containing mesh support classes and routines
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to 
# the license terms in the LICENSE.txt file found in the top-level directory 
# of this distribution and at: 
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html. 
# No part of the rogue software platform, including this file, may be 
# copied, modified, propagated, or distributed except according to the terms 
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
import yaml
import threading
import zyre
import czmq
import pyrogue

class MeshNode(threading.Thread):
    """
    Class to contain a Zyre node which acts as a client and/or server for 
    inter-connection between pyrogue nodes.
    """
    def __init__(self,group,iface='eth0',root=None):
        threading.Thread.__init__(self)
        self._root    = root
        self._group   = group
        self._name    = self._root.name if self._root else None
        self._runEn   = True
        self._noSet   = False
        self._servers = {}

        self._mesh = zyre.Zyre(self._name)
        self._mesh.set_interface(iface)

        self._mesh.start()
        self._mesh.join(group)

        # register callback and send out structure if root
        if self._root:
            self._root.addVarListener(self._variableStatus)
            self._sendStructure()

        self.start()

    def run(self):

        while(self._runEn):
           e = zyre.ZyreEvent(self._mesh)
           src = e.peer_name()

           if e.type() == 'WHISPER' or e.type() == 'SHOUT':
               cmd = e.msg().popstr()
               yml = e.msg().popstr()

               if cmd == 'variable_set':
                   self._root._setYamlVariables(yml)
               elif cmd == 'command':
                   print("got command")
                   self._root._execYamlCommands(yml)
               elif cmd == 'get_structure':
                   self._sendStructure(self,src=None)
               elif cmd == 'structure':
                   nr = pyrogue.rootFromYaml(yml,self._setFunction,self._cmdFunction)
                   if not self._servers.has_key(nr.name):
                       self._servers[nr.name] = nr
               elif cmd == 'variable_status':
                   self._noSet = True
                   for key,value in self._servers.iteritems():
                       try:
                           value._setYamlVariables(yml,modes=['RW','RO'])
                       except Exception as e:
                           value._logException(e)
                       value._write()

                   self._noSet = False

           #elif e.type() == 'JOIN':
               #msg = czmq.Zmsg()
               #msg.addstr('get_structure')
               ##self._mesh.whisper(name,msg)
               #self._mesh.shout(self._group,msg)

    def stop(self):
        self._runEn = False
        self._mesh.leave(self._group)
        self._mesh.stop()

    def getRoot(self,name):
        if self._servers.has_key(name):
            return self._servers[name]
        else:
            return None

    def _cmdFunction(self,dev,cmd,arg):
        d = {}
        pyrogue.addPathToDict(d,cmd.path,arg)
        name = cmd.path[:cmd.path.find('.')]
        yml = yaml.dump(d,default_flow_style=False)

        msg = czmq.Zmsg()
        msg.addstr('command')
        msg.addstr(yml)
        #self._mesh.whisper(name,msg)
        self._mesh.shout(self._group,msg)

    def _setFunction(self,dev,var,value):
        var._scratch = value
        if self._noSet: return
        d = {}
        pyrogue.addPathToDict(d,var.path,value)
        name = var.path[:var.path.find('.')]
        yml = yaml.dump(d,default_flow_style=False)

        msg = czmq.Zmsg()
        msg.addstr('variable_set')
        msg.addstr(yml)
        #self._mesh.whisper(name,msg)
        self._mesh.shout(self._group,msg)

    def _variableStatus(self,yml):
        msg = czmq.Zmsg()
        msg.addstr('variable_status')
        msg.addstr(yml)
        #self._mesh.whisper(name,msg)
        self._mesh.shout(self._group,msg)

    def _sendStructure(self,src=None):
        if self._root:
            yml = self._root._getYamlStructure()
            msg = czmq.Zmsg()
            msg.addstr('structure')
            msg.addstr(yml)

            if src:
                self._mesh.whisper(src,msg)
            else:
                self._mesh.shout(self._group,msg)

