#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Title      : PyRogue shared memory
#-----------------------------------------------------------------------------
# File       : pyrogue/interfaces/smem.py
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
            d = pyrogue.yamlToData(data)

            path   = d['path']
            attr   = d['attr']
            args   = d['args']
            kwargs = d['kwargs']

            node = self._root.getNode(path)

            if node is None:
                return 'null\n'

            nAttr = getattr(node, attr)

            if nAttr is None:
                return 'null\n'
            elif callable(nAttr):
                return pyrogue.dataToYaml(nAttr(*args,**kwargs)) + '\n'
            else:
                return pyrogue.dataToYaml(nAttr) + '\n'

        except:
            return 'null\n'

