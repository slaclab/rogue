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

import io as _io
import pickle as _pickle
import rogue.interfaces
import json
from typing import Any


class _SafeUnpickler(_pickle.Unpickler):
    """Restricted Unpickler for incoming ZMQ request payloads.

    Builtins cover the JSON-shaped scalars and containers used by
    ``SimpleClient`` calls.  ``numpy.ndarray`` payloads are explicitly
    permitted because clients (e.g. ``SimpleClient.set(path, value)`` and
    the PyDM ndarray write path) serialize numpy arrays directly; rejecting
    those would break legitimate writes.
    """

    _ALLOWED = {
        ('builtins', 'dict'),
        ('builtins', 'list'),
        ('builtins', 'tuple'),
        ('builtins', 'set'),
        ('builtins', 'frozenset'),
        ('builtins', 'str'),
        ('builtins', 'int'),
        ('builtins', 'float'),
        ('builtins', 'bool'),
        ('builtins', 'bytes'),
        ('builtins', 'bytearray'),
        ('builtins', 'NoneType'),
        ('builtins', 'complex'),
    }

    # Top-level package names whose submodules are permitted in addition to
    # the per-(module, name) allowlist above.
    #
    # Residual risk (acknowledged and accepted): pickle's REDUCE opcode can
    # invoke any allowed global as a callable, so a malicious client request
    # could in principle reach numpy.fromfile / numpy.ctypeslib.load_library
    # at deserialisation time.  A per-class allowlist is impractical because
    # ndarray pickle uses numpy.core.multiarray._reconstruct (an internal
    # function whose path varies across numpy versions) plus dtype/scalar
    # types that we do not want to chase across releases.  The threat model
    # for this socket is "the operator chose what binds to the REP port" -
    # typically loopback or a trusted lab network - and the builtins
    # narrowing above is what closes the eval/exec arbitrary-code path that
    # would otherwise be reachable from any picklable payload.
    _ALLOWED_TOP_PACKAGES = (
        'numpy',
    )

    def find_class(self, module: str, name: str) -> type:
        if (module, name) in self._ALLOWED:
            return super().find_class(module, name)
        if module.split('.')[0] in self._ALLOWED_TOP_PACKAGES:
            return super().find_class(module, name)
        raise _pickle.UnpicklingError(
            f"Unsafe pickle payload: {module}.{name}")


def _safe_loads(data: bytes) -> object:
    """Deserialise pickle bytes using a restricted Unpickler."""
    return _SafeUnpickler(_io.BytesIO(data)).load()


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
            return _pickle.dumps(self._doOperation(_safe_loads(data)))
        except Exception as msg:
            exc_type = type(msg)
            exc_name = getattr(exc_type, "__qualname__", exc_type.__name__)
            return _pickle.dumps(Exception(
                f"{exc_type.__module__}.{exc_name}: {msg}"))

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
            self._publish(_pickle.dumps(self._updateList))
            self._updateList = {}

    def _start(self) -> None:
        """Start the ZMQ server and print connection info."""
        rogue.interfaces.ZmqServer._start(self)
        print(f"Start: Started zmqServer on ports {self.port()}-{self.port()+2}")
        print(f"    To start a gui: python -m pyrogue gui --server='localhost:{self.port()}'")
        print(f"    To use a virtual client: client = pyrogue.interfaces.VirtualClient(addr='localhost', port={self.port()})")
