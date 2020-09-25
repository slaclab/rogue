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


class ZmqServer(rogue.interfaces.ZmqServer):

    def __init__(self,*,root,addr,port):
        rogue.interfaces.ZmqServer.__init__(self,addr,port)
        self._root = root

    def _doRequest(self,data):
        try:
            d = pickle.loads(data)

            path    = d['path']   if 'path'   in d else None
            attr    = d['attr']   if 'attr'   in d else None
            args    = d['args']   if 'args'   in d else ()
            kwargs  = d['kwargs'] if 'kwargs' in d else {}

            # Special case to get root node
            if path == "__ROOT__":
                return pickle.dumps(self._root)

            node = self._root.getNode(path)

            if node is None:
                return pickle.dumps(None)

            nAttr = getattr(node, attr)

            if nAttr is None:
                resp = None
            elif callable(nAttr):
                resp = nAttr(*args,**kwargs)
            else:
                resp = nAttr

            return pickle.dumps(resp)

        except Exception as msg:
            return pickle.dumps(msg)
