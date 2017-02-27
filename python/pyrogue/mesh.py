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
import pyre
import pyrogue
import uuid
import time
import zmq

class MeshNode(threading.Thread):
    """
    Class to contain a Zyre node which acts as a client and/or server for 
    inter-connection between pyrogue nodes.
    """
    def __init__(self,group,iface=None,root=None):
        threading.Thread.__init__(self)
        self._root    = root
        self._group   = group
        self._name    = self._root.name if self._root else None
        self._runEn   = False
        self._noMsg   = False
        self._servers = {}
        self._newTree = None
        self._thread  = None

        self._mesh = pyre.Pyre(name=self._name,interface=iface)
        #self._mesh.set_verbose()

        if self._root:
            self._root.addVarListener(self._variableStatus)

    def start(self):
        self._runEn = True
        self._thread = threading.Thread(target=self._run)
        self._thread.start()

    def stop(self):
        self._runEn = False
        self._thread.join()

    def getTree(self,name):
        if name in self._servers:
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
        self._mesh.start()
        self._mesh.join(self._group)

        poller = zmq.Poller()
        poller.register(self._mesh.socket(),zmq.POLLIN)

        while(self._runEn):
            evts = dict(poller.poll(100))
            if self._mesh.socket() in evts and evts[self._mesh.socket()] == zmq.POLLIN:

                # Get a message
                e = self._mesh.recv()
                typ  = e[0].decode('utf-8')
                sid  = uuid.UUID(bytes=e[1])
                src  = e[2].decode('utf-8')

                # Commands sent directly to this node
                if typ == 'WHISPER':
                    m = yaml.load(e[3].decode('utf-8'))
                    cmd  = m['cmd']
                    msg1 = m['msg1']
                    msg2 = m['msg2']

                    # Variable set from client to server
                    if (cmd == 'variable_set' or cmd == 'command'):
                        self._root.setOrExecYaml(msg1,True,['RW'])

                    # Structure update from server to client
                    elif cmd == 'structure_status':

                        # Does name already exist? Update UUID
                        if src in self._servers:
                            t = self._servers[src]
                            t.uuid = sid

                        # Otherwise create new tree
                        else:
                            t = pyrogue.treeFromYaml(msg1,self._setFunction,self._cmdFunction)
                            setattr(t,'uuid',sid)
                            self._servers[t.name] = t
                            if self._newTree:
                                self._newTree(t)

                        # Apply updates
                        self._noMsg = True
                        t.setOrExecYaml(msg2,False,['RW','RO'])
                        self._noMsg = False

                    # Structure request from client to server
                    elif cmd == 'get_structure':
                        self._intWhisper(sid,'structure_status',self._root.getYamlStructure(),
                                         self._root.getYamlVariables(False,['RW','RO']))

                # Commands sent as a broadcast
                elif typ == 'SHOUT':
                    if e[3].decode('utf-8') == self._group:
                        m = yaml.load(e[4].decode('utf-8'))
                        cmd  = m['cmd']
                        msg  = m['msg']

                        # Field update from server to client
                        if cmd == 'variable_status':
                            self._noMsg = True
                            for key,value in self._servers.items():
                                value.setOrExecYaml(msg,False,['RW','RO'])
                            self._noMsg = False

                # New node, request structure and status
                elif typ == 'JOIN':
                    if e[3].decode('utf-8') == self._group:
                        if self._mesh.peer_header_value(sid,'server') == 'True':
                            self._intWhisper(sid,'get_structure')

        self._mesh.leave(self._group)
        self._mesh.stop()

    # Shout a message/payload combination
    def _intShout(self,cmd,msg=None):
        m = {'cmd':cmd,'msg':msg}
        ym = yaml.dump(m)
        self._mesh.shouts(self._group,ym)

    # Whisper a message/payload combination
    def _intWhisper(self,uuid,cmd,msg1=None,msg2=None):
        m = {'cmd':cmd,'msg1':msg1,'msg2':msg2}
        ym = yaml.dump(m)
        self._mesh.whispers(uuid,ym)

    # Command button pressed on client
    def _cmdFunction(self,dev,cmd,arg):
        d = {}
        pyrogue.addPathToDict(d,cmd.path,arg)
        name = cmd.path[:cmd.path.find('.')]
        yml = pyrogue.dictToYaml(d,default_flow_style=False)
        self._intWhisper(self._servers[name].uuid,'command',yml)

    # Variable field updated on client
    def _setFunction(self,dev,var,value):
        var._scratch = value
        if self._noMsg: return
        d = {}
        pyrogue.addPathToDict(d,var.path,value)
        name = var.path[:var.path.find('.')]
        yml = pyrogue.dictToYaml(d,default_flow_style=False)
        self._intWhisper(self._servers[name].uuid,'variable_set',yml)

    # Variable field updated on server
    def _variableStatus(self,yml,d):
        self._intShout('variable_status',yml)

