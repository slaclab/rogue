#-----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
#-----------------------------------------------------------------------------
#  Description:
#       PyRogue TUI: main loop, output capture and runTui
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
Full-screen terminal front end: tab bar, header with link/busy state, a
description line, a status line with the last result, a clickable key bar
and the dialog stack. run_tui() takes the same tab layout as
the nested tab layout list described in runTui.
"""
import contextlib
import ctypes
import curses
import io
import logging
import os
import sys
import threading
import time
import traceback

from pyrogue.tui import ui
from pyrogue.tui.console import Console
from pyrogue.tui.model import Session, parse_channel
from pyrogue.tui.ui import attr, put
from pyrogue.tui.views import SystemView, TreeView

VIEWS = {'system': SystemView, 'tree': TreeView}
BUTTON5 = getattr(curses, 'BUTTON5_PRESSED', 0x200000)
GLOBAL_KEYS = [(':', 'Command', ':'), ('L', 'Console', 'L'), ('Tab', 'NextTab', 9), ('m', 'Messages', 'm'),
               ('?', 'Help', '?'), ('q', 'Quit', 'q')]

HELP = """\
PyRogue TUI: terminal version of the default Rogue PyDM GUI

The key bar at the bottom is always shown; click an entry to send that key.
The line above it shows the result of the last action (m: full history).

Global
  Tab / Shift-Tab, 1..9    switch tab (mouse: click the tab)
  L                        show/hide the console pane: everything the process prints
                           (logging, Rogue C++, child processes) scrolls there
  :                        command line in the console (type help there); e.g.
                             AxiVersion.ScratchPad    AxiVersion.ScratchPad = 0x10
                             AxiVersion.TestCommand(hi)   ls AxiVersion   read -R AxiVersion   py root.Time.get()
                           Tab completes paths, Up/Down history, Esc closes
  ?                        this help
  m                        message history (results and errors of every action)
  Ctrl-L                   redraw          q  quit

Mouse (off with --no-mouse; hold Shift to select text in most terminals)
  click                    select / press a button / choose in menus and lists
  double-click             open (tree rows, files in the file browser)
  right-click              Debug Tree: Rogue tools menu (as the PyDM context menu)
  wheel                    scroll

System tab  (Reset And Configuration, Data File Control, Run Control, System Log)
  arrows / h j k l         move between fields and buttons
  Enter                    press button, choose enum, edit field, expand log entry
  Load Config directory list (below the Load Config row):
    Enter / click          directory: open it; file: select it for Load Config
    Space / click on [ ]   add/remove a file (several files are loaded in order)
    Backspace              parent directory; [ Up ] [ All files ] [ Hide list ] buttons
  a                        System Log: last 20 entries <-> all entries
  e                        System Log: expand/collapse all shown entries
  i                        node information; on a log entry: the full entry

Debug Tree tab
  up/down PgUp/PgDn Home/End    move
  Right / l / +            expand device or group   Left / h / -  collapse / go to parent
  Enter                    var: edit (enum: choose)  cmd: Exec (prompt if it takes an arg)
                           device/group: expand/collapse   [Read All] row: ReadAll
  Space                    expand/collapse (or activate on a leaf)
  o / F10                  Rogue tools menu for the row (right-click does the same)
  x                        Command column: device [Read] (recursive) or command [Exec]
  r / R                    Read Node / Read Recursive
  w / W                    Write Node / Write Recursive
  A                        Read All (root) / Read Recursive (sub-tree tab)
  i                        Node Information
  f                        file browser: set the variable / pass the path to the command
  /  n  N                  find by name/path in loaded nodes, next, previous
  g                        go to a path (expands down to it)
  *  _                     expand everything below / collapse all
  c                        show/hide columns (or click the column header)
  y / Y                    copy value / path to the clipboard (OSC 52)
  Mouse: click the glyph to expand, the Value to edit, [Read]/[Exec] to run.

Dialogs
  Enter accept, Esc cancel (or the [ OK ] / [ Cancel ] buttons), Tab completes paths.
  File browser: Tab list<->name field, Space marks (Load Config), ^T filter, . hidden, ~ home.
  File paths are resolved on THIS machine and sent to the server as text, as in PyDM.

Values are updated live from the server. An action runs on a worker thread;
the header shows it while busy.
"""


def flatten_tabs(tabs, prefix=''):
    out = []
    for label, spec in tabs:
        name = f'{prefix}{label}'
        if isinstance(spec, list):
            out += flatten_tabs(spec, name + ' / ')
        else:
            out.append((name, spec))
    return out


def default_tabs(nServers):
    """PyDM DefaultTop per server: System + Debug Tree."""
    if nServers == 1:
        return [('System', ('system', 'rogue://0/root')), ('Debug Tree', ('tree', 'rogue://0/root'))]
    return [(f'Server {i}', [('System', ('system', f'rogue://{i}/root')),
                             ('Debug Tree', ('tree', f'rogue://{i}/root'))]) for i in range(nServers)]


class App:
    def __init__(self, session, tabs, title, startTab=None, mouse=True, configDir=None):
        self.session = session
        self.title = title
        self.configDir = configDir
        self.tabSpecs = flatten_tabs(tabs)
        self.views = [None] * len(self.tabSpecs)
        if startTab is None:
            startTab = 1 if len(self.tabSpecs) > 1 and self.tabSpecs[1][1][0] == 'tree' else 0
        self.cur = max(0, min(startTab, len(self.tabSpecs) - 1))
        self.dialogs = []
        self._status = ('', 'info', 0)
        self.mouse = mouse
        self.quit = False
        self.scr = None
        self._tabX = []
        self._keyHits = []
        self._content = (2, 2)
        self._statusRow = None
        self._lastClick = (0, -1, -1, 0)
        self.console = Console(self)

    # ---- api for views ---------------------------------------------------
    def push(self, dlg):
        self.dialogs.append(dlg)

    def status(self, text, level='info', now=False):
        self._status = (text, level, time.time())
        if now and text and self.scr is not None and self._statusRow is not None:
            # only the status line: a full draw() could re-enter the view being built
            W = self.scr.getmaxyx()[1]
            put(self.scr, self._statusRow, 0, text.ljust(W - 1), curses.A_BOLD, W - 1)
            self.scr.refresh()

    def view(self, i=None):
        i = self.cur if i is None else i
        if self.views[i] is None:
            kind, channel = self.tabSpecs[i][1]
            srv, path = parse_channel(channel)
            self.status(f'loading {self.tabSpecs[i][0]} ...', now=True)
            self.views[i] = VIEWS[kind](self, srv, path)
            self.status('')
        return self.views[i]

    # ---- drawing ---------------------------------------------------------
    def _keybar(self, W):
        """Lay the view's and the global keys out on up to two rows."""
        items = list(getattr(self.view(), 'keys', [])) + GLOBAL_KEYS
        rows, row, x = [], [], 0
        for key, text, code in items:
            n = len(key) + len(text) + 2
            if x + n > W - 1 and row:
                rows.append(row)
                if len(rows) == 2:
                    return rows
                row, x = [], 0
            row.append((x, key, text, code))
            x += n
        if row:
            rows.append(row)
        return rows

    def draw(self):
        scr = self.scr
        scr.erase()
        H, W = scr.getmaxyx()
        if H < 12 or W < 40:
            put(scr, 0, 0, 'terminal too small')
            scr.refresh()
            return

        down = [s.addr for s in self.session.servers if not s.link]
        hdr = attr('linkbad') if down else attr('header')
        put(scr, 0, 0, ' ' * W, hdr)
        right = ''
        if self.session.busy:
            spin = '|/-\\'[int(time.time() * 4) % 4]
            right = f'{spin} busy: {self.session.busy[0]}' + (f' (+{len(self.session.busy) - 1})'
                                                              if len(self.session.busy) > 1 else '')
        if down:
            right = f'LINK DOWN: {",".join(down)}  ' + right
        elif not right:
            right = ' '.join(s.addr for s in self.session.servers)
        if self.console.unread and not self.console.visible:
            right = f'log +{self.console.unread} (L)  ' + right
        right = right[:W // 2]
        put(scr, 0, W - len(right) - 1, right, hdr)
        put(scr, 0, 1, f'pyrogue tui  {self.title}', hdr, max(0, W - len(right) - 3))

        # tab bar scrolls sideways so the current tab is always visible
        labels = [f' {i + 1}:{lab} ' if i < 9 else f' {lab} ' for i, (lab, _) in enumerate(self.tabSpecs)]
        first = 0
        while sum(len(t) + 1 for t in labels[first:self.cur + 1]) + (2 if first else 0) > W - 2:
            first += 1
        x = 0
        self._tabX = [(-1, -1)] * len(labels)
        if first:
            x += put(scr, 1, 0, '<', curses.A_BOLD) + 1
        for i in range(first, len(labels)):
            t = labels[i]
            if x + len(t) > W - 2 and i > self.cur:
                put(scr, 1, W - 1, '>', curses.A_BOLD)
                break
            self._tabX[i] = (x, x + len(t))
            x += put(scr, 1, x, t, attr('tab') if i == self.cur else attr('tabin')) + 1

        kb = self._keybar(W)
        bottom = 3 + len(kb)
        paneH = self.console.height(H - bottom - 2)
        view = self.view()
        self._content = (2, H - bottom - paneH)
        cur = view.draw(scr, 2, H - bottom - 2 - paneH, W)
        if paneH:
            ccur = self.console.draw(scr, H - bottom - paneH, paneH, W)
            if self.console.active:
                cur = ccur

        y = H - bottom
        put(scr, y, 0, ui.HLINE * W, attr('dim'))
        put(scr, y + 1, 0, view.describe().replace('\n', ' '), curses.A_BOLD, W)

        text, level, t = self._status
        if self.session.messages and (not text or self.session.messages[-1][0] >= t):
            mt, level, text = self.session.messages[-1]
            text = f'{time.strftime("%H:%M:%S", time.localtime(mt))}  {text}'
        a = {'error': attr('err'), 'ok': attr('ok')}.get(level, 0)
        self._statusRow = y + 2
        put(scr, y + 2, 0, text.replace('\n', ' '), a, W - 1)

        self._keyHits = []
        for r, row in enumerate(kb):
            ky = y + 3 + r
            put(scr, ky, 0, ' ' * (W - 1), attr('keytext'))
            for kx, key, label, code in row:
                put(scr, ky, kx, key, attr('keykey'))
                put(scr, ky, kx + len(key), f'{label} ', attr('keytext'))
                self._keyHits.append((ky, kx, kx + len(key) + len(label) + 2, code))

        for dlg in self.dialogs:
            cur = dlg.draw(scr)
        try:
            curses.curs_set(1 if cur is not None else 0)
            if cur is not None:
                scr.move(*cur)
        except curses.error:
            pass
        scr.refresh()

    # ---- input -----------------------------------------------------------
    def read_key(self):
        try:
            k = self.scr.get_wch()
        except curses.error:
            return None
        if isinstance(k, str) and len(k) == 1 and (ord(k) < 32 or ord(k) == 127):
            return ord(k)
        return k

    def _dialog_closed(self):
        dlg = self.dialogs[-1]
        if not dlg.closed:
            return
        self.dialogs.pop()
        if dlg.on_done is not None:
            try:
                dlg.on_done(dlg.result)
            except Exception as e:  # noqa: BLE001
                self.status(f'{e}', level='error')

    def handle(self, k):
        if k == curses.KEY_RESIZE:
            curses.update_lines_cols()
            return
        if k == curses.KEY_MOUSE:
            self._mouse()
            return
        if self.dialogs:
            self.dialogs[-1].key(k)
            self._dialog_closed()
            return
        if self.console.active:
            self.console.key(k)
            return
        if k == ':':
            self.console.open_prompt()
            return
        if k == 'L':
            self.console.show()
            return
        try:
            if self.view().key(k):
                return
        except Exception as e:  # noqa: BLE001
            self.status(f'{e}', level='error')
            return
        n = len(self.tabSpecs)
        if k == ui.K_TAB:
            self.cur = (self.cur + 1) % n
        elif k == curses.KEY_BTAB:
            self.cur = (self.cur - 1) % n
        elif isinstance(k, str) and k.isdigit() and 1 <= int(k) <= min(n, 9):
            self.cur = int(k) - 1
        elif k == 'q':
            self.push(ui.Confirm('Quit', 'Quit the PyRogue TUI?', on_done=lambda r: r and self._quit()))
        elif k == '?':
            self.push(ui.TextView('Help', HELP.splitlines()))
        elif k == 'm':
            lines = []
            for t, lvl, txt in self.session.messages:
                a = {'error': attr('err'), 'ok': attr('ok'), 'log': attr('dim')}.get(lvl, 0)
                lines.append((f'{time.strftime("%H:%M:%S", time.localtime(t))} {txt}', a))
            tv = ui.TextView('Messages', lines or ['(none)'])
            tv.sel = len(lines) - 1
            self.push(tv)
        elif k == 12:  # ^L
            self.scr.clear()

    def _quit(self):
        self.quit = True

    def _mouse_kind(self, b, y, x):
        if b & curses.BUTTON4_PRESSED:
            return 'wheelup'
        if b & BUTTON5:
            return 'wheeldown'
        if b & (curses.BUTTON3_PRESSED | curses.BUTTON3_CLICKED):
            return 'right'
        if b & curses.BUTTON1_DOUBLE_CLICKED:
            return 'double'
        if b & (curses.BUTTON1_PRESSED | curses.BUTTON1_CLICKED):
            now = time.time()
            t, ly, lx, nd = self._lastClick
            self._lastClick = (now, y, x, len(self.dialogs))
            if now - t < 0.4 and ly == y and abs(lx - x) <= 1:
                self._lastClick = (0, -1, -1, 0)
                # the first click opened or closed a dialog: this one is not meant for it
                return 'double' if nd == len(self.dialogs) else None
            return 'click'
        return None  # releases, drags

    def _mouse(self):
        try:
            _, x, y, _, b = curses.getmouse()
        except curses.error:
            return
        kind = self._mouse_kind(b, y, x)
        if kind is None:
            return
        try:
            if self.dialogs:
                self.dialogs[-1].mouse(kind, y, x)
                self._dialog_closed()
                return
            if kind == 'click':
                if y == 1:
                    for i, (a, b2) in enumerate(self._tabX):
                        if a <= x < b2:
                            self.cur = i
                    return
                for ky, x0, x1, code in self._keyHits:
                    if y == ky and x0 <= x < x1:
                        if code is not None:
                            self.handle(code)
                        return
            if self.console.visible and self.console.mouse(kind, y, x):
                return
            if kind == 'click':
                self.console.active = False   # clicking the view leaves the command line
            if self._content[0] <= y < self._content[1]:
                self.view().mouse(kind, y, x)
        except Exception as e:  # noqa: BLE001
            self.status(f'{e}', level='error')

    def main(self, scr):
        self.scr = scr
        ui.init_colors()
        scr.keypad(True)
        scr.timeout(100)
        if self.mouse:
            curses.mousemask(curses.ALL_MOUSE_EVENTS)
            curses.mouseinterval(0)   # press events right away; double-clicks are timed here
        last = 0
        while not self.quit:
            k = self.read_key()
            if k is not None:
                self.handle(k)
                # drain queued keys (fast typing, key repeat) before redrawing
                scr.timeout(0)
                while not self.quit:
                    k2 = self.read_key()
                    if k2 is None:
                        break
                    self.handle(k2)
                scr.timeout(100)
            now = time.time()
            if k is not None or self.session.dirty.is_set() or now - last > 0.25:
                self.session.dirty.clear()
                try:
                    self.draw()
                except Exception as e:  # noqa: BLE001 -- a draw bug must not kill the session
                    err = f'draw error: {e!r}'
                    if err != getattr(self, '_lastDrawErr', None):
                        self._lastDrawErr = err
                        self.session.message('error', err)
                        for ln in traceback.format_exc().splitlines():
                            self.session.message('log', ln)
                last = now
        # swallow the mouse release of the click that quit, or the shell echoes it
        time.sleep(0.05)
        curses.flushinp()


class _LineSink(io.TextIOBase):
    """File-like object feeding complete lines to a callback."""

    def __init__(self, sink):
        self.sink = sink
        self.buf = ''

    def write(self, s):
        self.buf += s
        while '\n' in self.buf:
            line, self.buf = self.buf.split('\n', 1)
            if line.strip():
                self.sink(line)
        return len(s)

    def flush(self):
        pass


def _pump(fd, sink):
    """Feed lines read from fd to sink until EOF (daemon thread)."""
    def reader():
        lines = _LineSink(sink)
        while True:
            try:
                data = os.read(fd, 4096)
            except OSError:
                return
            if not data:
                return
            lines.write(data.decode(errors='replace'))
    threading.Thread(target=reader, daemon=True).start()


def _redirect_fd(fd, sink):
    """Point fd at a pipe feeding sink; returns the saved original fd."""
    saved = os.dup(fd)
    r, w = os.pipe()
    os.dup2(w, fd)
    os.close(w)
    _pump(r, sink)
    return saved


@contextlib.contextmanager
def capture_output(sink):
    """Python prints, logging and anything written to fd 2 go to sink(line), not the screen."""
    saved = sys.stdout, sys.stderr
    fd2 = _redirect_fd(2, sink)
    sys.stdout = sys.stderr = _LineSink(sink)
    # pyrogue's basicConfig handler holds the original sys.stdout (the tty)
    handlers = [h for lg in [logging.getLogger()] + [logging.getLogger(n) for n in logging.root.manager.loggerDict]
                for h in getattr(lg, 'handlers', []) if isinstance(h, logging.StreamHandler)
                and getattr(h, 'stream', None) in saved + (sys.__stdout__, sys.__stderr__)]
    streams = [h.setStream(sys.stdout) for h in handlers]
    try:
        yield
    finally:
        for h, st in zip(handlers, streams):
            h.setStream(st)
        sys.stdout, sys.stderr = saved
        os.dup2(fd2, 2)
        os.close(fd2)


def run_curses(main, sink):
    """
    curses.wrapper, but ncurses draws on a duplicate of the terminal fd so fd 1
    can go to sink as well: Rogue C++ logging, printf from libraries and child
    processes (e.g. viewers started by commands) write there and would
    otherwise scroll over the screen. initscr() takes C stdout at that moment,
    so C stdout points at the duplicate just for that call. Falls back to
    plain curses (fd 1 not captured) if libc's stdout can't be reached.
    """
    libc = sym = orig = None
    try:
        libc = ctypes.CDLL(None)
        libc.fdopen.restype = ctypes.c_void_p
        libc.fdopen.argtypes = [ctypes.c_int, ctypes.c_char_p]
        for name in ('stdout', '__stdoutp'):   # glibc, macOS libc
            try:
                sym = ctypes.c_void_p.in_dll(libc, name)
                break
            except ValueError:
                continue
        else:
            raise ValueError('no C stdout symbol')
        libc.fflush(None)
        fp = libc.fdopen(os.dup(1), b'w')
        if fp:
            orig, sym.value = sym.value, fp
    except (OSError, AttributeError, ValueError):
        sym = None
    try:
        scr = curses.initscr()
    finally:
        if orig is not None:
            sym.value = orig
    saved1 = _redirect_fd(1, sink) if orig is not None else None
    try:
        curses.noecho()
        curses.cbreak()
        scr.keypad(True)
        main(scr)
    finally:
        scr.keypad(False)
        curses.echo()
        curses.nocbreak()
        curses.endwin()
        if saved1 is not None:
            libc.fflush(None)
            os.dup2(saved1, 1)
            os.close(saved1)


def runTui(
    serverList: str = 'localhost:9099',
    tabs: list | None = None,
    title: str | None = None,
    startTab: int | None = None,
    mouse: bool = True,
    linkTimeout: float = 10.0,
    excGroups: list[str] | None = ['Hidden'],
    incGroups: list[str] | None = None,
    configDir: str | None = None,
) -> None:
    """Run the terminal UI until the user quits.

    Text-mode counterpart of :func:`pyrogue.pydm.runPyDM`: the same System
    and Debug Tree tabs, driven from a terminal with no Qt or X display.

    Parameters
    ----------
    serverList : str, optional
        Comma-separated list of ``host:port`` Rogue ZMQ servers.
    tabs : list | None, optional
        Tab layout: a list of ``(label, spec)`` where spec is
        ``('system', channel)``, ``('tree', channel)`` or a nested list
        (shown as ``label / sublabel``). Channels are
        ``rogue://<server index>/root.Path``. Defaults to System and
        Debug Tree for each server.
    title : str | None, optional
        Header title. Defaults to ``"Rogue Server: <servers>"``.
    startTab : int | None, optional
        Index of the tab shown first; defaults to the Debug Tree.
    mouse : bool, optional
        Enable mouse clicks and the wheel. Text selection then needs the
        terminal's override modifier (usually Shift).
    linkTimeout : float, optional
        Seconds without traffic before a server is reported down.
    excGroups : list[str] | None, optional
        Groups hidden from the Debug Tree, as in ``DebugTree``.
    incGroups : list[str] | None, optional
        Groups to show exclusively.
    configDir : str | None, optional
        Directory listed under Load Config on the System tab; defaults to
        the current directory.
    """
    os.environ.setdefault('ESCDELAY', '25')
    session = Session(serverList, linkTimeout=linkTimeout, excGroups=excGroups, incGroups=incGroups)
    tabs = tabs or default_tabs(len(session.servers))
    title = title or f'Rogue Server: {serverList}'
    app = App(session, tabs, title, startTab=startTab, mouse=mouse, configDir=configDir)
    try:
        sink = lambda line: app.console.add(line, 'log')  # noqa: E731
        with capture_output(sink):
            run_curses(app.main, sink)
    finally:
        session.stop()
