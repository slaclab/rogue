#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Title      : PyRogue epics support
#-----------------------------------------------------------------------------
# File       : pyrogue/epics.py
# Author     : Ryan Herbst, rherbst@slac.stanford.edu
# Created    : 2016-09-29
# Last update: 2016-09-29
#-----------------------------------------------------------------------------
# Description:
# Module containing epics support classes and routines
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
import pyrogue
import time
import pcaspy.SimpleServer
import pcaspy.Driver

class EpicsCaServer(threading.Thread):
    """
    Class to contain an epics ca server
    """
    def __init__(self,base,root):
        threading.Thread.__init__(self)
        self._root    = root
        self._base    = base 
        self._runEn   = True
        self._server  = SimpleServer()

        self._mesh = zyre.Zyre(self._name)
        self._mesh.set_interface(iface)

        if self._root:
            self._root.addVarListener(self._variableStatus)

        self.start()

    def _addDevice(self,node):

        # Get variables
        for key,value in node.getNodes(pyrogue.Variable).iteritems():

        # Get devices
        for key,value in node.getNodes(pyrogue.Device).iteritems():
            self._addDevice(value)

    def run(self):
        server = SimpleServer()

        # Create PVs
        self._addDevice(root)


        self._mesh.set_header('server','True' if self._root else 'False')
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
                if cmd == 'variable_set' and size > 1:
                    self._root.setYamlVariables(e.msg().popstr(),write=True)

                # Command from client to server
                elif cmd == 'command' and size > 1:
                    self._root.execYamlCommands(e.msg().popstr())

                # Structure update from server to client
                elif cmd == 'structure_status' and size > 2:
                    nr = pyrogue.rootFromYaml(e.msg().popstr(),self._setFunction,self._cmdFunction)

                    if not self._servers.has_key(nr.name):
                        setattr(nr,'uuid',sid)
                        self._servers[nr.name] = nr
                        self._noMsg = True
                        nr.setYamlVariables(e.msg().popstr(),modes=['RW','RO'],write=False)
                        self._noMsg = False

                        if self._newNode:
                            self._newNode(nr)

                # Structure request from client to server
                elif cmd == 'get_structure':
                    msg = czmq.Zmsg()
                    msg.addstr('structure_status')
                    msg.addstr(self._root.getYamlStructure())
                    msg.addstr(self._root.getYamlVariables(modes=['RW','RO'],read=False))
                    self._mesh.whisper(sid,msg)

            # Commands sent as a broadcast
            elif e.type() == 'SHOUT':

                # Field update from server to client
                if cmd == 'variable_status' and size > 1:
                    self._noMsg = True
                    for key,value in self._servers.iteritems():
                        value.setYamlVariables(e.msg().popstr(),modes=['RW','RO'],write=False)

                    self._noMsg = False

            # New node, request structure if a server and we are not already tracking it
            elif e.type() == 'JOIN':
                if self._mesh.peer_header_value(sid,'server') == 'True' and not self._servers.has_key(src):
                    msg = czmq.Zmsg()
                    msg.addstr('get_structure')
                    self._mesh.whisper(sid,msg)

    def stop(self):
        self._runEn = False
        self._mesh.leave(self._group)
        self._mesh.stop()

    def getRoot(self,name):
        if self._servers.has_key(name):
            return self._servers[name]
        else:
            return None

    def waitRoot(self,name):
        while self.getRoot(name) == None:
            time.sleep(.1)

    def setNewNodeCb(self,func):
        self._newNode = func

    # Command button pressed on client
    def _cmdFunction(self,dev,cmd,arg):
        d = {}
        pyrogue.addPathToDict(d,cmd.path,arg)
        name = cmd.path[:cmd.path.find('.')]
        yml = yaml.dump(d,default_flow_style=False)

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
        yml = yaml.dump(d,default_flow_style=False)

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

