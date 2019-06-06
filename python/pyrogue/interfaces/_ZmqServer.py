#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Title      : PyRogue ZMQ Server
#-----------------------------------------------------------------------------
# File       : pyrogue/interfaces/_ZmqServer.py
# Created    : 2017-06-07
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to 
# the license terms in the LICENSE.txt file found in the top-level directory 
# of this distribution and at: 
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html. 
# No part of the rogue software platform, including this file, may be 
# copied, modified, propagated, or distributed except according to the terms 
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
import rogue.interfaces
import pyrogue

class ZmqServer(rogue.interfaces.ZmqServer):
    def __init__(self,*,root,addr,port):
        rogue.interfaces.ZmqServer.__init__(self,addr,port)
        self._root = root

    def _doRequest(self,data):
        try:
            d = pyrogue.yamlToData(data,config=False)

            path    = d['path']   if 'path'   in d else None
            attr    = d['attr']   if 'attr'   in d else None
            args    = d['args']   if 'args'   in d else ()
            kwargs  = d['kwargs'] if 'kwargs' in d else {}
            rawStr  = d['rawStr'] if 'rawStr' in d else False

            if path is None:
                node = self._root
            else:
                node = self._root.getNode(path)

            if attr is None:
                return pyrogue.dataToYaml(node,config=False)
            else:
                nAttr = getattr(node, attr)

            if nAttr is None:
                return pyrogue.dataToYaml(None,config=False)
            elif callable(nAttr):
                return pyrogue.dataToYaml(nAttr(*args,**kwargs),config=False,rawStr=rawStr)
            else:
                return pyrogue.dataToYaml(nAttr,config=False,rawStr=rawStr)

        except Exception as msg:
            print("ZMQ Got Exception: {}".format(msg))
            return 'null\n'

