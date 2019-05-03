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

class ZmqServer(rogue.interfaces.ZmqServer):
    def __init__(self,*,root,addr,port):
        rogue.interfaces.ZmqServer.__init__(self,addr,port)
        self._root = root

    def _doRequest(self,type,path,arg):
        ret = ""

        if type == "get":
            ret = self._root.getDisp(path)
        elif type == "set":
            self._root.setDisp(path,arg)
        elif type == "exec":
            ret = self._root.exec(path,arg)
            if ret is None: ret = ""
        elif type == "value":
            ret = self._root.valueDisp(path)

        return ret

