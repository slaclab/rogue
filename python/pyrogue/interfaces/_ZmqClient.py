#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Title      : PyRogue base module - ZMQ Client
#-----------------------------------------------------------------------------
# File       : pyrogue/interfaces/_ZmqClient.py
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

class ZmqClient(rogue.interfaces.ZmqClient):

    def __init__(self, addr="localhost", port=9099):
        rogue.interfaces.ZmqClient.__init__(self,addr,port)

        # Setup logging
        self._log = pr.logInit(cls=self,name="ZmqClient",path=None)

        # Get root name as a connection test
        self.setTimeout(1000)
        rn = None
        while rn is None:
            rn = self._remoteAttr('__rootname__',None)

        print("Connected to {} at {}:{}".format(rn,addr,port))

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

