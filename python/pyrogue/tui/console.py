#-----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
#-----------------------------------------------------------------------------
#  Description:
#       PyRogue TUI: console pane and command line
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
Console pane: everything the process prints (Python, logging, Rogue C++,
child processes) scrolls here instead of over the screen, and ':' opens a
command line on the same pane.
"""
import collections
import curses
import os
import re
import shlex
import time

import pyrogue as pr

from pyrogue.tui import ui
from pyrogue.tui.commands import log_lines, tree_lines
from pyrogue.tui.model import parse_channel
from pyrogue.tui.ui import attr, put
from pyrogue.tui.views import TreeView, node_info_lines

HELP = """\
Paths are relative to the root (root.X and rogue://<server>/root.X also work); Tab completes.
  AxiVersion.ScratchPad        show a value (a device: list it)
  AxiVersion.ScratchPad = 0x10 set from the display string (0x10, True, an enum name, [1, 2])
  AxiVersion.TestCommand(hi)   execute a command (argument optional)
  get [-r] PATH...             values; -r reads the hardware first
  set PATH VALUE   exec PATH [ARG]
  read [-R] [PATH]   write [-R] [PATH]     Read/Write Node, -R recursive (default: root)
  ls [PATH] [-d N]             list a device N levels down (default 1)
  info PATH                    node information
  goto PATH                    show the node in the Debug Tree
  load FILE...   save FILE   state FILE  LoadConfig / SaveConfig / SaveState
  log [N]                      System Log (last N, default 20)
  py EXPR                      Python with root, client, pr (e.g. py root.AxiVersion.ScratchPad.get() + 1)
  clear                        clear the console
Up/Down: history  PgUp/PgDn/wheel: scroll  Esc: close the command line  L: show/hide the pane"""

COMMANDS = ['help', 'get', 'set', 'exec', 'read', 'write', 'ls', 'info', 'goto', 'load', 'save',
            'state', 'log', 'py', 'clear']
PATH = r'[\w.\[\]:/]+'
KIND = {'err': 'err', 'warn': 'warn', 'cmd': 'dtitle', 'ok': 'ok', 'dim': 'dim'}


class ConsoleError(Exception):
    pass


class Console:
    def __init__(self, app):
        self.app = app
        self.session = app.session
        self.lines = collections.deque(maxlen=5000)
        self.visible = False
        self.active = False
        self._autoShown = False
        self.scroll = 0       # display rows back from the newest line
        self.unread = 0
        self.edit = ui.LineEdit()
        self.history = []
        self._hpos = None
        self._ns = None
        self._geom = (0, 0)
        level = {'error': 'err', 'ok': 'ok', 'info': 'out', 'log': 'log'}
        self.session.listeners.append(lambda lvl, text: self.add(text, level.get(lvl, 'out')))

    # ---- output ----------------------------------------------------------
    def add(self, text, kind='log'):
        for ln in str(text).splitlines() or ['']:
            k = kind
            if kind == 'log':
                if re.search(r'\b(ERROR|CRITICAL|Error|Traceback|Exception)\b', ln):
                    k = 'err'
                elif re.search(r'\bWARN(ING)?\b', ln):
                    k = 'warn'
            self.lines.append((time.time(), k, ln.rstrip()))
            if not self.visible:
                self.unread += 1
            elif self.scroll:
                self.scroll += 1   # hold the view still while scrolled back
        self.session.dirty.set()

    def show(self, state=None):
        self.visible = (not self.visible) if state is None else state
        if self.visible:
            self.unread = 0
        else:
            self.active = False

    def open_prompt(self):
        if not self.visible:
            self._autoShown = True
            self.show(True)
        self.active = True

    def height(self, H):
        return max(6, min(20, H * 2 // 5)) if self.visible else 0

    def draw(self, win, y0, h, w):
        self._geom = (y0, h)
        hint = '  [scrolled back: End to follow]' if self.scroll else ''
        title = f'{ui.HLINE * 2} Console  (L hide, : command, PgUp/PgDn/wheel scroll){hint} '
        put(win, y0, 0, title + ui.HLINE * max(0, w - len(title)), attr('section'))
        rows = h - 1 - (1 if self.active else 0)
        width = max(10, w - 1)
        need = rows + self.scroll
        out = []   # newest first
        for _, kind, text in reversed(self.lines):
            chunks = [text[i:i + width] for i in range(0, max(len(text), 1), width)]
            for c in reversed(chunks):
                out.append((kind, c))
            if len(out) >= need:
                break
        if len(out) < need:
            self.scroll = max(0, len(out) - rows)
        shown = out[self.scroll:self.scroll + rows]
        top = y0 + 1 + rows - len(shown)
        for i, (kind, c) in enumerate(reversed(shown)):
            put(win, top + i, 0, c, attr(KIND[kind]) if kind in KIND else 0)
        if not self.active:
            return None
        y = y0 + h - 1
        put(win, y, 0, 'rogue> ', attr('dtitle'))
        return self.edit.draw(win, y, 7, w - 8, a=0)

    # ---- input -----------------------------------------------------------
    def key(self, k):
        if k in ui.K_ENTER:
            line = self.edit.text.strip()
            self.edit = ui.LineEdit()
            self._hpos = None
            self.scroll = 0
            if line:
                if not self.history or self.history[-1] != line:
                    self.history.append(line)
                self.run(line)
        elif k == ui.K_ESC:
            self.active = False
            if self._autoShown:
                self.show(False)
            self._autoShown = False
        elif k == curses.KEY_UP:
            if self.history:
                self._hpos = len(self.history) - 1 if self._hpos is None else max(0, self._hpos - 1)
                self._recall()
        elif k == curses.KEY_DOWN:
            if self._hpos is not None:
                self._hpos += 1
                if self._hpos >= len(self.history):
                    self._hpos = None
                    self.edit = ui.LineEdit()
                else:
                    self._recall()
        elif k == curses.KEY_PPAGE:
            self.scroll += max(1, self._geom[1] - 3)
        elif k == curses.KEY_NPAGE:
            self.scroll = max(0, self.scroll - max(1, self._geom[1] - 3))
        elif k == ui.K_TAB:
            self.complete()
        elif k == curses.KEY_END and not self.edit.text:
            self.scroll = 0
        else:
            self.edit.key(k)

    def _recall(self):
        self.edit = ui.LineEdit(self.history[self._hpos])

    def mouse(self, kind, y, x):
        y0, h = self._geom
        if not (y0 <= y < y0 + h):
            return False
        if kind == 'wheelup':
            self.scroll += 3
        elif kind == 'wheeldown':
            self.scroll = max(0, self.scroll - 3)
        elif kind == 'click':
            self.active = True
            if y == y0 + h - 1:
                self.edit.hit(y, x)
        return True

    # ---- completion --------------------------------------------------------
    def complete(self):
        text = self.edit.text[:self.edit.pos]
        m = re.search(r'[\w.\[\]]*$', text)
        tok, start = m.group(0), m.start()
        first = text[:start].strip() == ''
        cands = [c + ' ' for c in COMMANDS if first and '.' not in tok and c.startswith(tok)]
        parent, prefix = tok.rsplit('.', 1) if '.' in tok else ('root', tok)
        try:
            node = self.session.node(self._srv(), parent)
            base = parent + '.' if '.' in tok else ''
            for n in node.nodes.values():
                if n.filterByGroup(self.session.incGroups, self.session.excGroups) and n.name.startswith(prefix):
                    cands.append(base + n.name + ('.' if n.isDevice else ''))
        except Exception:  # noqa: BLE001 -- nothing to complete
            pass
        if not cands:
            return
        common = os.path.commonprefix(cands)
        rest = self.edit.text[self.edit.pos:]
        self.edit.text = self.edit.text[:start] + common + rest
        self.edit.pos = start + len(common)
        if len(cands) > 1 and common == tok:
            base = tok[:len(tok) - len(prefix)]
            names = sorted(c.strip()[len(base):] for c in cands)
            more = f'  ... {len(names) - 40} more, type more letters' if len(names) > 40 else ''
            self.add('  '.join(names[:40]) + more, 'dim')

    # ---- commands ----------------------------------------------------------
    def _srv(self):
        return getattr(self.app.view(), 'srv', 0)

    def resolve(self, path):
        if path.startswith('rogue://'):
            srv, p = parse_channel(path)
        else:
            srv, p = self._srv(), path
        try:
            return srv, self.session.node(srv, p)
        except KeyError:
            raise ConsoleError(f'no node {path}  (type help for the commands)') from None

    def run(self, line):
        self.add(f'rogue> {line}', 'cmd')
        try:
            words = shlex.split(line)
        except ValueError:
            words = line.split()
        cmd = words[0]
        try:
            if cmd in ('help', '?'):
                self.add(HELP, 'out')
            elif cmd == 'clear':
                self.lines.clear()
            elif cmd == 'goto':
                self._goto(words[1:])
            elif cmd == 'py':
                code = line.split(None, 1)[1] if len(words) > 1 else ''
                self._submit(line, lambda: self._py(code))
            elif cmd in COMMANDS:
                fn = getattr(self, f'_c_{cmd}')
                self._submit(line, lambda: fn(words[1:]))
            else:
                self._shorthand(line)
        except ConsoleError as e:
            self.add(str(e), 'err')

    def _submit(self, label, fn):
        def job():
            try:
                fn()
            except ConsoleError as e:
                self.add(str(e), 'err')
        self.session.submit(f'console: {label}'[:80], job, quiet=True)

    def _shorthand(self, line):
        m = re.match(rf'^\s*({PATH})\s*\((.*)\)\s*$', line)
        if m:
            path, arg = m.group(1), m.group(2).strip()
            if len(arg) >= 2 and arg[0] == arg[-1] and arg[0] in '\'"':
                arg = arg[1:-1]
            self._submit(line, lambda: self._c_exec([path] + ([arg] if arg else [])))
            return
        m = re.match(rf'^\s*({PATH})\s*=(?!=)\s*(.*?)\s*$', line)
        if m:
            path, val = m.group(1), m.group(2)
            if len(val) >= 2 and val[0] == val[-1] and val[0] in '\'"':
                val = val[1:-1]
            self._submit(line, lambda: self._c_set([path, val]))
            return
        m = re.match(rf'^\s*({PATH})\s*$', line)
        if m:
            self._submit(line, lambda: self._c_get([m.group(1)]))
            return
        raise ConsoleError(f'unknown command: {line.split()[0]}  (type help; Python: py ...)')

    @staticmethod
    def _flags(args, *flags):
        on = {f for f in flags if f in args}
        return on, [a for a in args if a not in flags]

    def _c_get(self, args):
        on, paths = self._flags(args, '-r')
        if not paths:
            raise ConsoleError('get PATH...')
        for p in paths:
            srv, n = self.resolve(p)
            if n.isinstance(pr.Device):
                self.add('\n'.join(tree_lines(self.session, srv, n, 1)), 'out')
            elif n.isinstance(pr.BaseCommand):
                self.add(f'{n.path} is a command: {n.name}() to execute', 'out')
            else:
                self.add(f'{n.path} = {n.getDisp(read="-r" in on)}', 'out')

    def _c_set(self, args):
        if len(args) < 2:
            raise ConsoleError('set PATH VALUE')
        _, n = self.resolve(args[0])
        n.setDisp(' '.join(args[1:]))
        self.add(f'{n.path} = {n.getDisp(read=False)}', 'ok')

    def _c_exec(self, args):
        if not args:
            raise ConsoleError('exec PATH [ARG]')
        _, n = self.resolve(args[0])
        if not n.isinstance(pr.BaseCommand):
            raise ConsoleError(f'{n.path} is not a command (set it with {args[0]} = VALUE)')
        ret = n() if len(args) == 1 else n(' '.join(args[1:]))
        self.add(f'{n.path}: done' + (f' -> {ret!r}' if ret is not None else ''), 'ok')

    def _rw(self, args, write):
        on, rest = self._flags(args, '-R')
        rec = '-R' in on
        _, n = self.resolve(rest[0] if rest else 'root')
        what = 'WriteDevice' if write else 'ReadDevice'
        if n.isinstance(pr.Device):
            getattr(n, what)(rec)
        elif n.isinstance(pr.BaseCommand):
            raise ConsoleError(f'{n.path} is a command')
        elif rec:
            getattr(n.parent, what)(True)
        elif write:
            n.write()
        else:
            self.add(f'{n.path} = {n.getDisp(read=True)}', 'out')
            return
        self.add(f'{n.path}: {what}({"recursive" if rec else "node"}) done', 'ok')

    def _c_read(self, args):
        self._rw(args, False)

    def _c_write(self, args):
        self._rw(args, True)

    def _c_ls(self, args):
        depth = 1
        if '-d' in args:
            i = args.index('-d')
            try:
                depth = int(args[i + 1])
            except (IndexError, ValueError):
                raise ConsoleError('ls [PATH] [-d N]') from None
            args = args[:i] + args[i + 2:]
        srv, n = self.resolve(args[0] if args else 'root')
        self.add('\n'.join(tree_lines(self.session, srv, n, depth)), 'out')

    def _c_info(self, args):
        if not args:
            raise ConsoleError('info PATH')
        srv, n = self.resolve(args[0])
        self.add('\n'.join(node_info_lines(self.session, srv, n)), 'out')

    def _root(self):
        return self.session.servers[self._srv()].root

    def _files(self, args, what):
        if not args:
            raise ConsoleError(f'{what} FILE')
        return [os.path.abspath(os.path.expanduser(a)) for a in args]

    def _c_load(self, args):
        files = self._files(args, 'load')
        ret = self._root().LoadConfig(','.join(files))
        self.add(f'LoadConfig({", ".join(os.path.basename(f) for f in files)}) -> {ret!r}', 'ok')

    def _c_save(self, args):
        f = self._files(args, 'save')[0]
        self.add(f'SaveConfig({f}) -> {self._root().SaveConfig(f)!r}', 'ok')

    def _c_state(self, args):
        f = self._files(args, 'state')[0]
        self.add(f'SaveState({f}) -> {self._root().SaveState(f)!r}', 'ok')

    def _c_log(self, args):
        n = int(args[0]) if args and args[0].isdigit() else 20
        self.add('\n'.join(log_lines(self._root(), n, verbose='-v' in args)), 'out')

    def _goto(self, args):
        """UI thread: switch to a Debug Tree tab that contains the node and select it."""
        if not args:
            raise ConsoleError('goto PATH')
        srv, n = self.resolve(args[0])
        app = self.app
        for i, (_, (kind, channel)) in enumerate(app.tabSpecs):
            s, p = parse_channel(channel)
            if kind != 'tree' or s != srv:
                continue
            base = self.session.node(s, p).path
            if n.path == base or n.path.startswith(base + '.'):
                app.cur = i
                view = app.view()
                if isinstance(view, TreeView):
                    view.goto(n.path)
                    self.add(f'-> {n.path}', 'dim')
                return
        raise ConsoleError(f'no Debug Tree tab shows {n.path}')

    def _py(self, code):
        if self._ns is None:
            srv = self.session.servers[self._srv()]
            self._ns = {'root': srv.root, 'client': srv.client, 'pr': pr,
                        'servers': [s.root for s in self.session.servers]}
        if not code:
            raise ConsoleError('py EXPR')
        try:
            ret = eval(compile(code, '<console>', 'eval'), self._ns)  # noqa: S307 -- user's own console
        except SyntaxError:
            exec(compile(code, '<console>', 'exec'), self._ns)  # noqa: S102
            return
        if ret is not None:
            self.add(repr(ret), 'out')
