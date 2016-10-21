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
import time

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
        self._runEn   = False
        self._noMsg   = False
        self._servers = {}
        self._newTree = None
        self._thread  = None

        self._mesh = zyre.Zyre(self._name)
        self._mesh.set_interface(iface)
        #self._mesh.set_verbose()

        if self._root:
            self._root.addVarListener(self._variableStatus)

    def start(self):
        self._runEn = True
        self._thread = threading.Thread(target=self._run)
        self._thread.start()

    def stop(self):
        self._runEn = False
        self._mesh.leave(self._group)
        self._mesh.stop()
        self._thread.join()

    def getTree(self,name):
        if self._servers.has_key(name):
            return self._servers[name]
        else:
            return None

    def waitTree(self,name):
        t = self.getTree(name)
        while (not t):
            time.sleep(.1)
            t = self.getTree(name)
        return t

    def setNewTreeCb(self,func):
        self._newTree = func

    def _run(self):
        self._mesh.set_header('server','True' if self._root else 'False')
        #self._mesh.set_header('hostname',socket.getfqdn())
        self._mesh.start()
        self._mesh.join(self._group)

        while(self._runEn):

            # Get a message
            e = zyre.ZyreEvent(self._mesh)
            src = e.peer_name()
            sid = e.peer_uuid()

            if e.type() == 'WHISPER' or e.type() == 'SHOUT': size = e.msg().size()
            else: size = 0

            if size > 0: cmd = e.msg().popstr()
            else: cmd = None

            # Commands sent directly to this node
            if e.type() == 'WHISPER':

                # Variable set from client to server
                if (cmd == 'variable_set' or cmd == 'command') and size > 1:
                    self._root.setOrExecYaml(e.msg().popstr(),True,['RW'])

                # Structure update from server to client
                elif cmd == 'structure_status' and size > 2:
                    yml = e.msg().popstr()
                    
                    # Does name already exist? Update UUID
                    if self._servers.has_key(src):
                        t = self._servers[src]
                        t.uuid = sid

                    # Otherwise create new tree
                    else:
                        t = pyrogue.treeFromYaml(yml,self._setFunction,self._cmdFunction)
                        setattr(t,'uuid',sid)
                        self._servers[t.name] = t
                        if self._newTree:
                            self._newTree(t)
                    
                    # Apply updates
                    self._noMsg = True
                    t.setOrExecYaml(e.msg().popstr(),False,['RW','RO'])
                    self._noMsg = False

                # Structure request from client to server
                elif cmd == 'get_structure':
                    msg = czmq.Zmsg()
                    msg.addstr('structure_status')
                    msg.addstr(self._root.getYamlStructure())
                    msg.addstr(self._root.getYamlVariables(False,['RW','RO']))
                    self._mesh.whisper(sid,msg)

            # Commands sent as a broadcast
            elif e.type() == 'SHOUT':
                msg = e.msg().popstr()

                # Field update from server to client
                if cmd == 'variable_status' and size > 1:
                    self._noMsg = True
                    for key,value in self._servers.iteritems():
                        value.setOrExecYaml(msg,False,['RW','RO'])

                    self._noMsg = False

            # New node, request structure and status
            elif e.type() == 'JOIN':
                if self._mesh.peer_header_value(sid,'server') == 'True':
                    msg = czmq.Zmsg()
                    msg.addstr('get_structure')
                    self._mesh.whisper(sid,msg)


    # Command button pressed on client
    def _cmdFunction(self,dev,cmd,arg):
        d = {}
        pyrogue.addPathToDict(d,cmd.path,arg)
        name = cmd.path[:cmd.path.find('.')]
        yml = pyrogue.dictToYaml(d,default_flow_style=False)

        msg = czmq.Zmsg()
        msg.addstr('command')
        msg.addstr(yml)
        self._mesh.whisper(self._servers[name].uuid,msg)

    # Variable field updated on client
    def _setFunction(self,dev,var,value):
        var._scratch = value
        if self._noMsg: return
        d = {}
        pyrogue.addPathToDict(d,var.path,value)
        name = var.path[:var.path.find('.')]
        yml = pyrogue.dictToYaml(d,default_flow_style=False)

        msg = czmq.Zmsg()
        msg.addstr('variable_set')
        msg.addstr(yml)
        self._mesh.whisper(self._servers[name].uuid,msg)

    # Variable field updated on server
    def _variableStatus(self,yml,d):
        msg = czmq.Zmsg()
        msg.addstr('variable_status')
        msg.addstr(yml)
        self._mesh.shout(self._group,msg)

