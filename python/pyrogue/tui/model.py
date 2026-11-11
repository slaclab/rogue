#-----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
#-----------------------------------------------------------------------------
#  Description:
#       PyRogue TUI: server connections, node metadata and value caches
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
"""
Client-side state shared by the TUI and the one-shot commands: server
connections, cached node metadata, the live value cache and a worker thread
that runs blocking remote calls off the UI thread.
"""
import queue
import threading
import time

import pyrogue as pr
from pyrogue.interfaces import VirtualClient


def parse_channel(channel):
    """'rogue://1/root.X' -> (1, 'root.X'); a bare path maps to server 0."""
    if channel.startswith('rogue://'):
        idx, path = channel[len('rogue://'):].split('/', 1)
        return int(idx), path
    return 0, channel


class Meta:
    """Static attributes of one node, fetched once (each is a remote round trip)."""

    def __init__(self, node):
        self.node = node
        self.name = node.name
        self.path = node.path
        self.description = node.description or ''
        self.isDevice = node.isDevice
        self.isCommand = node.isCommand
        self.isVariable = node.isVariable
        self.guiGroup = node.guiGroup
        self.offset = None
        self.bitOffset = None
        self.bitSize = None
        self.mode = ''
        self.typeStr = ''
        self.disp = None
        self.enum = None
        self.units = None
        self.arg = False
        self.expand = node.expand
        self.isRoot = node.isinstance(pr.Root)

        if self.isDevice:
            self.offset = node.offset
            return

        self.mode = node.mode
        self.typeStr = node.typeStr
        self.disp = node.disp
        self.enum = node.enum
        self.units = node.units
        if self.isCommand:
            self.arg = node.arg
        if node.isinstance(pr.RemoteVariable):
            self.offset = node.offset
            self.bitOffset = node.bitOffset
            self.bitSize = node.bitSize

    @property
    def isEnum(self):
        """Same rule as the PyDM combo box: writable enum, not a list."""
        return (self.disp == 'enum' and self.enum is not None
                and (self.mode != 'RO' or self.isCommand) and self.typeStr != 'list')

    @property
    def writable(self):
        return self.isVariable and self.mode != 'RO'

    def offsetStr(self):
        if self.offset is None:
            return ''
        if self.bitOffset is None:
            return f'0x{self.offset:X}'
        bo = self.bitOffset[0]
        return f'0x{self.offset:X} [{bo + self.bitSize[0] - 1}:{bo}]'


class Server:
    def __init__(self, index, addr, linkTimeout):
        host, port = addr.rsplit(':', 1)
        self.index = index
        self.addr = addr
        self.client = VirtualClient(host, int(port), linkTimeout=linkTimeout)
        self.root = self.client.root
        if self.root is None:
            raise ConnectionError(f'no Rogue root at {addr}')
        self.link = True


class Session:
    """All servers of one TUI session plus the caches the views draw from."""

    def __init__(self, serverList, linkTimeout=10.0, excGroups=('Hidden',), incGroups=None):
        self.servers = []
        self.incGroups = list(incGroups) if incGroups else None
        self.excGroups = list(excGroups) if excGroups else None
        self.values = {}       # (srv, path) -> VariableValue
        self._nodes = {}       # (srv, path) -> node
        self._meta = {}        # (srv, path) -> Meta
        self._failed = set()   # (srv, path) whose initial fetch failed
        self.dirty = threading.Event()
        self.messages = []     # (time, level, text)
        self.listeners = []    # f(level, text) for every message (the TUI console)
        self.busy = []         # labels of queued/running jobs
        self._jobs = queue.Queue()

        for i, addr in enumerate(a.strip() for a in serverList.split(',') if a.strip()):
            srv = Server(i, addr, linkTimeout)
            srv.client.addLinkMonitor(lambda state, s=srv: self._link(s, state))
            srv.root.addVarListener(lambda path, val, i=i: self._update(i, path, val))
            self.servers.append(srv)

        self._worker = threading.Thread(target=self._run, daemon=True)
        self._worker.start()

    # ---- listeners -------------------------------------------------------
    def _update(self, srv, path, val):
        self.values[(srv, path)] = val
        self.dirty.set()

    def _link(self, srv, state):
        srv.link = state
        self.message('info' if state else 'error',
                     f'server {srv.addr}: link {"restored" if state else "lost"}')

    def message(self, level, text):
        self.messages.append((time.time(), level, text))
        del self.messages[:-500]
        for f in self.listeners:
            f(level, text)
        self.dirty.set()

    # ---- node access -----------------------------------------------------
    def node(self, srv, path):
        """Resolve a path; 'root.' and a missing root prefix are accepted."""
        key = (srv, path)
        if key in self._nodes:
            return self._nodes[key]
        root = self.servers[srv].root
        full = path
        if path == 'root' or path.startswith('root.'):
            full = root.name + path[4:]
        elif path != root.name and not path.startswith(root.name + '.'):
            full = root.name + '.' + path
        node = root.getNode(full)
        if node is None:
            raise KeyError(f'node not found: {path}')
        self._nodes[key] = node
        return node

    def meta(self, srv, node):
        key = (srv, node.path)
        m = self._meta.get(key)
        if m is None:
            m = self._meta[key] = Meta(node)
        return m

    def value(self, srv, path):
        """Cached VariableValue; first access fetches it without a hardware read."""
        key = (srv, path)
        v = self.values.get(key)
        if v is None:
            # listeners publish under the real root name, not the 'root.' alias
            node = self.node(srv, path)
            if node.path != path:
                return self.value(srv, node.path)
            if key in self._failed:
                raise LookupError(f'no value for {path}')
            try:
                v = self.values[key] = self.node(srv, path).getVariableValue(read=False)
            except Exception:
                # don't retry every frame; a later listener update still fills it in
                self._failed.add(key)
                raise
        return v

    def disp(self, srv, path, default='n/a'):
        try:
            return self.value(srv, path).valueDisp
        except Exception:
            return default

    def children(self, srv, dev):
        """(vars+commands, devices) of a device, in DebugTree order and group filter."""
        lst = dev.variablesByGroup(incGroups=self.incGroups, excGroups=self.excGroups)
        lst.update(dev.commandsByGroup(incGroups=self.incGroups, excGroups=self.excGroups))
        devs = dev.devicesByGroup(incGroups=self.incGroups, excGroups=self.excGroups)
        return list(lst.values()), list(devs.values())

    # ---- worker ----------------------------------------------------------
    def submit(self, label, func, done=None, quiet=False):
        """Run func() on the worker thread; done(result) is called there on success.
        quiet: report failures only (the console prints its own results)."""
        self.busy.append(label)
        self.dirty.set()
        self._jobs.put((label, func, done, quiet))

    def _run(self):
        while True:
            label, func, done, quiet = self._jobs.get()
            t0 = time.time()
            try:
                ret = func()
                if not quiet:
                    msg = f'{label}: done ({time.time() - t0:.2f} s)'
                    if ret is not None:
                        msg += f' -> {ret!r}'[:300]
                    self.message('ok', msg)
                if done is not None:
                    done(ret)
            except Exception as e:  # noqa: BLE001 -- report every remote failure in the UI
                self.message('error', f'{label}: {e}')
            finally:
                self.busy.remove(label)
                self.dirty.set()

    def stop(self):
        for s in self.servers:
            try:
                s.client.stop()
            except Exception:
                pass
