#-----------------------------------------------------------------------------
# Title      : PyRogue ZMQ Server
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
import pickle
import json


class ZmqServer(rogue.interfaces.ZmqServer):

    def __init__(self,*,root,addr,port):
        rogue.interfaces.ZmqServer.__init__(self,addr,port)
        self._root = root

    def _doOperation(self,d):
        path    = d['path']   if 'path'   in d else None
        attr    = d['attr']   if 'attr'   in d else None
        args    = d['args']   if 'args'   in d else ()
        kwargs  = d['kwargs'] if 'kwargs' in d else {}

        # Special case to get root node
        if path == "__ROOT__":
            return self._root

        node = self._root.getNode(path)

        if node is None:
            return None

        nAttr = getattr(node, attr)

        if nAttr is None:
            return None
        elif callable(nAttr):
            return nAttr(*args,**kwargs)
        else:
            return nAttr

    def _doRequest(self,data):
        try:
            return pickle.dumps(self._doOperation(pickle.loads(data)))
        except Exception as msg:
            return pickle.dumps(msg)

    def _doString(self,data):
        try:
            d = json.loads(data)
            if 'args' in d:
                d['args'] = tuple(d['args'])
            return str(self._doOperation(d))
        except Exception as msg:
            return "EXCEPTION: " + str(msg)
