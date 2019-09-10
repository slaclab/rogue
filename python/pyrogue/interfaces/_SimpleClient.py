#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Title      : PyRogue Simple ZMQ Client for Rogue
#-----------------------------------------------------------------------------
# File       : pyrogue/interfaces/_SimpleClient.py
# Created    : 2017-05-16
#
# To use in matlab first you need both the zmq and jsonpickle package in your
# python insallation:
#
# > pip install zmq
# > pip install matlab
#
# You then need to set the appropriate flags in matlab to load the zmq module:
#
# >> py.sys.setdlopenflags(int32(bitor(2, 8)));
#
# c = py.SimpleClient.SimpleClient("localhost",9099);
# c.get("dummyTree.Time")
#
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
import threading

class SimpleClient(object):

    def __init__(self, addr="localhost", port=9099, cb=None):
        sport = port
        rport = port + 1
        self._ctx = zmq.Context()

        self._req = self._ctx.socket(zmq.REQ)
        self._req.connect(f'tcp://{addr}:{rport}')

        if cb:
            self._cb  = cb
            self._sub = self._ctx.socket(zmq.SUB)
            self._sub.connect(f'tcp://{addr}:{sport}')
            self._runEn = True
            self._subThread = threading.Thread(target=self._listen)
            self._subThread.start()

    def stop(self):
        self._runEn = False

    def _listen(self):
        self._sub.setsockopt(zmq.SUBSCRIBE,"".encode('utf-8'))

        while self._runEn:
            msg = self._sub.recv_string()

            d = jsonpickle.decode(msg)

            for k,val in d.items():
                self._cb(k,val)


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
        return self._remoteAttr(path, '__call__', arg)

