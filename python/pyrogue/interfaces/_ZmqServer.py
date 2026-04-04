#-----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
#-----------------------------------------------------------------------------
#  Description:
#       PyRogue ZMQ Server
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
from typing import Any


class ZmqServer(rogue.interfaces.ZmqServer):
    """ZMQ server for exposing a PyRogue root to remote clients.

    Parameters
    ----------
    root : object
        PyRogue root node to expose.
    addr : str
        Bind address (for example ``*`` or hostname).
    port : int
        Base port number.
    incGroups : object, optional
        Groups to include in variable updates.
    excGroups : object, optional
        Groups to exclude from variable updates.
    """

    def __init__(
        self,
        *,
        root: Any,
        addr: str,
        port: int,
        incGroups: str | list[str] | None = None,
        excGroups: str | list[str] | None = ['NoServe'],
    ) -> None:
        rogue.interfaces.ZmqServer.__init__(self,addr,port)
        self._root = root
        self._addr = addr
        self._root.addVarListener(func=self._varUpdate, done=self._varDone, incGroups=incGroups, excGroups=excGroups)
        self._updateList = {}

    @property
    def address(self) -> str:
        """Resolved address string (host:port)."""
        if self._addr == "*":
            return f"127.0.0.1:{self.port()}"
        else:
            return f"{self._addr}:{self.port()}"

    def _doOperation(self, d: dict[str, Any]) -> Any:
        """Execute a remote operation (path, attr, args, kwargs)."""
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

    def _doRequest(self, data: bytes) -> bytes:
        """Handle a pickle-serialized request and return serialized response."""
        try:
            return pickle.dumps(self._doOperation(pickle.loads(data)))
        except Exception as msg:
            try:
                return pickle.dumps(msg)
            except Exception:
                return pickle.dumps(Exception(f"{type(msg).__module__}.{type(msg).__name__}: {msg}"))

    def _doString(self, data: str) -> str:
        """Handle a JSON-serialized request and return string response."""
        try:
            d = json.loads(data)
            if 'args' in d:
                d['args'] = tuple(d['args'])
            return str(self._doOperation(d))
        except Exception as msg:
            return "EXCEPTION: " + str(msg)

    def _varUpdate(self, path: str, value: Any) -> None:
        """Queue a variable update for batching."""
        self._updateList[path] = value

    def _varDone(self) -> None:
        """Flush queued variable updates to subscribers."""
        if len(self._updateList) > 0:
            self._publish(pickle.dumps(self._updateList))
            self._updateList = {}

    def _start(self) -> None:
        """Start the ZMQ server and print connection info."""
        rogue.interfaces.ZmqServer._start(self)
        print(f"Start: Started zmqServer on ports {self.port()}-{self.port()+2}")
        print(f"    To start a gui: python -m pyrogue gui --server='localhost:{self.port()}'")
        print(f"    To use a virtual client: client = pyrogue.interfaces.VirtualClient(addr='localhost', port={self.port()})")
