#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Title      : PyRogue base module - ZMQ Client
#-----------------------------------------------------------------------------
# File       : pyrogue/interfaces/_SimpleClient.py
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
import zmq
import jsonpickle

class SimpleClient(object):

    def __init__(self, addr="localhost", port=9099):
        rport = port + 1
        self._ctx = zmq.Context()
        self._req = self._ctx.socket(zmq.REQ)
        self._req.connect(f'tcp://{addr}:{rport}')

    def _remoteAttr(self,path,attr,*args,**kwargs):
        msg = {'path':path, 
               'attr':attr,
               'args':args,
               'kwargs':kwargs}
        try:
            self._req.send_string(jsonpickle.encode(msg))
            resp = jsonpickle.decode(self._req.recv_string())
        except Exception as msg:
            print("got remote exception: {}".format(msg))
            resp = None

        return resp

    def get(self,path):
        return self._remoteAttr(path, 'get')

    def getDisp(self,path):
        return self._remoteAttr(path, 'getDisp')

    def value(self,path):
        return self._remoteAttr(path, 'value')

    def valueDisp(self,path):
        return self._remoteAttr(path, 'valueDisp')

    def set(self,path,value):
        return self._remoteAttr(path, 'set', value)

    def setDisp(self,path,value):
        return self._remoteAttr(path, 'setDisp', value)

    def exec(self,path,arg):
        return self._remoteAttr(path, 'exec', arg)

