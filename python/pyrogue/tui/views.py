#-----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
#-----------------------------------------------------------------------------
#  Description:
#       PyRogue TUI: System and Debug Tree tabs
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
The two tab kinds of the PyDM top display: SystemView (pyrogue.pydm
SystemWindow: RootControl, DataWriter, RunControl, SystemLog, plus a
directory panel for Load Config) and TreeView (DebugTree plus the Rogue
right-click tools: read/write node, read/write recursive, node info, file).
"""
import curses
import json
import os
import time

import pyrogue as pr

from pyrogue.tui import ui
from pyrogue.tui.ui import attr, put


def severity_attr(val):
    sev = getattr(val, 'severity', None)
    if sev == 'AlarmMajor':
        return attr('major')
    if sev == 'AlarmMinor':
        return attr('minor')
    return 0


def level_attr(levelNumber):
    lvl = levelNumber or 0
    return attr('err') if lvl >= 40 else attr('warn') if lvl >= 30 else 0 if lvl >= 20 else attr('dim')


def node_info_lines(session, srv, node):
    """Same fields as pyrogue.pydm.tools.NodeInformation."""
    if node.isinstance(pr.Device):
        attrs = ['name', 'path', 'description', 'hidden', 'groups']
    elif node.isinstance(pr.BaseCommand):
        attrs = ['name', 'path', 'description', 'hidden', 'groups', 'enum', 'typeStr', 'disp']
        if node.isinstance(pr.RemoteCommand):
            attrs += ['offset', 'bitSize', 'bitOffset', 'varBytes']
    else:
        attrs = ['name', 'path', 'description', 'hidden', 'groups', 'enum',
                 'typeStr', 'disp', 'precision', 'mode', 'units', 'minimum',
                 'maximum', 'lowWarning', 'lowAlarm', 'highWarning',
                 'highAlarm', 'alarmStatus', 'alarmSeverity', 'pollInterval']
        if node.isinstance(pr.RemoteVariable):
            attrs += ['offset', 'bitSize', 'bitOffset', 'verifyEn', 'varBytes']

    rows = []
    for a in attrs:
        try:
            rows.append((a, str(getattr(node, a))))
        except Exception as e:  # noqa: BLE001
            rows.append((a, f'<{e}>'))
    if node.isinstance(pr.BaseVariable) and not node.isinstance(pr.BaseCommand):
        for lab, fn in (('Value', lambda: str(node.value())), ('ValueDisp', lambda: str(node.valueDisp()))):
            try:
                rows.append((lab, fn()))
            except Exception as e:  # noqa: BLE001
                rows.append((lab, f'<{e}>'))
    rows.append(('PyDM Path', f'rogue://{srv}/{node.path}'))
    if node.isinstance(pr.RemoteVariable):
        try:
            rows.append(('address', f'{node.address:#x}'))
        except Exception:  # noqa: BLE001
            pass
    w = max(len(a) for a, _ in rows)
    out = []
    for a, v in rows:
        vl = v.splitlines() or ['']
        out.append(f'{a.rjust(w)} : {vl[0]}')
        out += [' ' * (w + 3) + ln for ln in vl[1:]]
    return out


class View:
    """Common pieces: run actions through the worker, pick enums, edit values."""
    keys = []   # key bar: (key label, text, key sent when clicked)

    def __init__(self, app, srv, path):
        self.app = app
        self.session = app.session
        self.srv = srv
        self.path = path

    def node(self, path=None):
        return self.session.node(self.srv, path or self.path)

    def run(self, label, func, done=None):
        self.session.submit(label, func, done)

    def call(self, node, arg=None, label=None):
        label = label or (f'{node.name}({arg!r})' if arg is not None else f'{node.name}()')
        self.run(label, (lambda: node(arg)) if arg is not None else (lambda: node()))

    def set_disp(self, node, text):
        self.run(f'{node.name} <- {text!r}'[:120], lambda: node.setDisp(text))

    def choose_enum(self, meta, then, anchor=None):
        opts = list(meta.enum.values())
        cur = self.session.disp(self.srv, meta.path, '')
        idx = opts.index(cur) if cur in opts else 0
        self.app.push(ui.Choose(meta.name, opts, idx, anchor=anchor,
                                on_done=lambda i: i is not None and then(opts[i])))

    def edit(self, meta, anchor=None):
        """Edit a variable or run a command, picking the widget DebugTree would."""
        node = meta.node
        if meta.isCommand and not meta.arg:
            self.call(node)
        elif meta.isEnum:
            if meta.isCommand:
                self.choose_enum(meta, lambda v: self.call(node, v), anchor)
            else:
                self.choose_enum(meta, lambda v: self.set_disp(node, v), anchor)
        elif meta.isCommand:
            cur = self.session.disp(self.srv, meta.path, '')
            self.app.push(ui.Prompt(f'Execute {meta.path}', cur, f'Argument ({meta.typeStr}):',
                                    on_done=lambda t: t is not None and self.call(node, t)))
        elif meta.writable:
            cur = self.session.disp(self.srv, meta.path, '')
            units = f' [{meta.units}]' if meta.units else ''
            self.app.push(ui.Prompt(f'Set {meta.path}', cur,
                                    f'{meta.typeStr} disp={meta.disp!r}{units}',
                                    on_done=lambda t: t is not None and self.set_disp(node, t)))
        else:
            self.app.status(f'{meta.path} is read-only')

    def info(self, node):
        self.app.push(ui.TextView(f'Information for {node.name}',
                                  node_info_lines(self.session, self.srv, node)))

    def mouse(self, kind, y, x):
        pass


# ---------------------------------------------------------------------------
# System tab
# ---------------------------------------------------------------------------
class Cell:
    """
    One drawable piece of a form row; focusable when it has an action.
    click(dx) overrides action for mouse clicks (dx: column inside the cell).
    """

    def __init__(self, text, a=0, action=None, cid=None, desc='', enabled=True, click=None, space=None):
        self.text = text
        self.a = a
        self.action = action if enabled else None
        self.cid = cid or text
        self.desc = desc
        self.click = click
        self.space = space

    @property
    def focusable(self):
        return self.action is not None


class SystemView(View):
    keys = [('↑↓←→', 'Move', None), ('Enter', 'Press', 10), ('Spc', 'Mark file', ' '),
            ('Bksp', 'Dir up', 127), ('a', 'Log all/20', 'a'), ('e', 'Log expand', 'e'), ('i', 'Info', 'i')]
    CFG_PATTERNS = ('*.yml', '*.yaml')

    def __init__(self, app, srv, path):
        super().__init__(app, srv, path)
        self.focus = None
        self.top = 0
        self.fields = {'LoadConfig': '', 'SaveConfig': '', 'SaveState': ''}
        self.logOpen = set()
        self.logAll = False
        self._logCache = (None, [])
        root = self.node()
        self.writers = [v.name for v in root.getNodes(typ=pr.DataWriter).values()]
        self.runctrls = [v.name for v in root.getNodes(typ=pr.RunControl).values()]
        self._lines = []
        self._shownFocus = None
        self._y0 = 2
        self._h = 10
        self.cfgDir = os.path.abspath(os.path.expanduser(getattr(app, 'configDir', None) or os.getcwd()))
        self.cfgTop = 0
        self.cfgRows = 10
        self.cfgShow = True
        self.cfgAll = False
        self._cfgCache = (None, [], '')

    # ---- cell factories --------------------------------------------------
    def _p(self, name):
        return f'{self.path}.{name}'

    def _meta(self, path):
        try:
            return self.session.meta(self.srv, self.node(path))
        except Exception:  # noqa: BLE001
            return None

    def label(self, text):
        return Cell(text, curses.A_BOLD)

    def value(self, path, width=0, units=''):
        try:
            v = self.session.value(self.srv, path)
            text, a = v.valueDisp, severity_attr(v)
        except Exception:  # noqa: BLE001
            text, a = 'n/a', attr('dim')
        if units:
            text += f' {units}'
        return Cell(text.ljust(width), a, cid=path)

    def enum(self, path):
        m = self._meta(path)
        text = self.session.disp(self.srv, path)
        if m is None or not m.isEnum:
            return Cell(f'{text}', cid=path)
        return Cell(f'[{text} {ui.G_OPEN}]', attr('field'), cid=path, desc=m.description,
                    action=lambda: self.choose_enum(m, lambda v: self.set_disp(m.node, v)))

    def edit_var(self, path, width):
        m = self._meta(path)
        text = self.session.disp(self.srv, path, '')
        enabled = m is not None and m.writable
        return Cell(text[-width:].ljust(width), attr('field') if enabled else attr('dim'), cid=path,
                    desc=m.description if m else '', enabled=enabled,
                    action=lambda: self.edit(m))

    def button(self, label, cmdpath, arg=None, enabled=True, cid=None):
        try:
            node = self.node(cmdpath)
            desc = node.description
        except Exception:  # noqa: BLE001
            node, desc, enabled = None, '', False
        return Cell(f'[ {label} ]', attr('button') if enabled else attr('dim'),
                    cid=cid or f'btn:{cmdpath}', desc=desc, enabled=enabled,
                    action=lambda: self.call(node, arg() if callable(arg) else arg, label=label))

    def ui_button(self, label, action, cid, desc='', enabled=True):
        return Cell(f'[ {label} ]', attr('button') if enabled else attr('dim'), action=action,
                    cid=cid, desc=desc, enabled=enabled)

    def field(self, key, width):
        text = self.fields[key]
        if key == 'LoadConfig' and text:
            # names relative to the listed directory read better than full paths
            text = ', '.join(os.path.relpath(p, self.cfgDir) if p.startswith(self.cfgDir + os.sep) else p
                             for p in text.split(','))
        shown = text[-width:] if text else '(type a path, pick below or Browse)' if key == 'LoadConfig' \
            else '(type a path or Browse)'
        return Cell(shown.ljust(width), attr('field') if text else attr('field') | curses.A_DIM,
                    cid=f'field:{key}', desc=f'{key} file(s); Enter to edit, Tab completes',
                    action=lambda: self._edit_field(key))

    def _edit_field(self, key):
        def done(t):
            if t is None:
                return
            t = t.strip()
            if key == 'LoadConfig' and t and os.path.isdir(os.path.expanduser(t)):
                self._cfg_chdir(os.path.expanduser(t))   # a directory: list it below
            else:
                self.fields[key] = t
        self.app.push(ui.Prompt(key, self.fields[key], 'Path (comma-separate several for LoadConfig):',
                                on_done=done, complete_paths=True))

    def _browse_field(self, key):
        if key == 'LoadConfig':
            dlg = ui.FileBrowser('Read config file', self.CFG_PATTERNS, multi=True, start=self.cfgDir)
        elif key == 'SaveConfig':
            dlg = ui.FileBrowser('Save config file', ('*.yml',), save=True, start=self.cfgDir,
                                 suggest=ui.stamp('config_%Y%m%d_%H%M%S.yml'))
        else:
            dlg = ui.FileBrowser('Save State file', ('*.yml', '*.yml.zip'), save=True,
                                 suggest=ui.stamp('state_%Y%m%d_%H%M%S.yml.zip'))

        def done(p):
            if p:
                self.fields[key] = p
                if key == 'LoadConfig':
                    self._cfg_chdir(os.path.dirname(p.split(',')[0]), keepFocus=True)
        dlg.on_done = done
        self.app.push(dlg)

    def _browse_data(self, writer):
        dlg = ui.FileBrowser('Select data file', ('*.dat',), save=True,
                             suggest=ui.stamp('data_%Y%m%d_%H%M%S.dat'))
        node = self.node(self._p(f'{writer}.DataFile'))
        dlg.on_done = lambda p: p and self.set_disp(node, p)
        self.app.push(dlg)

    # ---- Load Config directory panel -------------------------------------
    def _cfg_entries(self):
        try:
            key = (self.cfgDir, os.stat(self.cfgDir).st_mtime, self.cfgAll)
            if self._cfgCache[0] != key:
                self._cfgCache = (key, ui.scan_dir(self.cfgDir, self.CFG_PATTERNS, not self.cfgAll), '')
        except OSError as e:
            self._cfgCache = (None, [ui.Entry('..', True, 0, 0, False)], str(e))
        return self._cfgCache[1], self._cfgCache[2]

    def _cfg_selected(self):
        return [p for p in self.fields['LoadConfig'].split(',') if p]

    def _cfg_chdir(self, d, keepFocus=False):
        self.cfgDir = os.path.abspath(os.path.join(self.cfgDir, d))
        self.cfgTop = 0
        if not keepFocus and self.focus and self.focus.startswith('cfg'):
            self.focus = 'cfg:..'

    def _cfg_activate(self, e):
        if e.isdir:
            self._cfg_chdir(e.name)
            return
        self.fields['LoadConfig'] = os.path.join(self.cfgDir, e.name)
        self.app.status(f'Load Config <- {e.name}  (press [ Load Config ] to load)')

    def _cfg_toggle(self, e):
        if e.isdir:
            return
        full = os.path.join(self.cfgDir, e.name)
        sel = self._cfg_selected()
        if full in sel:
            sel.remove(full)
        else:
            sel.append(full)
        self.fields['LoadConfig'] = ','.join(sel)

    def _cfg_prompt_dir(self):
        def done(t):
            if not t:
                return
            d = os.path.expanduser(t.strip())
            if os.path.isdir(d):
                self._cfg_chdir(d)
            else:
                self.app.status(f'not a directory: {d}', level='error')
        self.app.push(ui.Prompt('Config directory', self.cfgDir, 'Directory to list:', on_done=done,
                                complete_paths=True))

    def _cfg_rows(self, row, width):
        row(self.label('    Directory:'),
            Cell(self.cfgDir if len(self.cfgDir) <= width - 58 else '...' + self.cfgDir[-max(10, width - 61):],
                 attr('dir'), cid='cfgdir', desc='Directory listed below; Enter/click to type another',
                 action=self._cfg_prompt_dir),
            self.ui_button('Up', lambda: self._cfg_chdir('..'), 'cfgup', 'Parent directory'),
            self.ui_button('*.yml only' if self.cfgAll else 'All files', self._cfg_toggle_all, 'cfgall',
                           'Show only YAML files / every file'),
            self.ui_button('Hide list' if self.cfgShow else 'Show list', self._cfg_toggle_show, 'cfgshow'))
        if not self.cfgShow:
            return
        entries, err = self._cfg_entries()
        if err:
            row(Cell('      ' + err, attr('err')))
        n = len(entries)
        self.cfgTop = max(0, min(self.cfgTop, max(0, n - self.cfgRows)))
        sel = self._cfg_selected()
        nameW = max(20, width - 8 - 28)
        for e in entries[self.cfgTop:self.cfgTop + self.cfgRows]:
            marked = os.path.join(self.cfgDir, e.name) in sel
            chk = '   ' if e.isdir else ('[x]' if marked else '[ ]')
            icon = ui.G_CLOSED if e.isdir else ' '
            text = f'{chk} {icon} {e.label}'.ljust(nameW)[:nameW] + e.info().rjust(28)
            desc = ('Enter/click: open directory' if e.isdir else
                    'Enter/click: load this file  Space or click [ ]: add/remove (several files)')
            row(Cell('   '), Cell(text, e.attr(marked), cid=f'cfg:{e.name}', desc=desc,
                                  action=lambda e=e: self._cfg_activate(e),
                                  space=lambda e=e: self._cfg_toggle(e),
                                  click=lambda dx, e=e: self._cfg_toggle(e) if dx < 3 and not e.isdir
                                  else self._cfg_activate(e)))
        if n > self.cfgRows:
            row(Cell(f'      {self.cfgTop + 1}-{min(n, self.cfgTop + self.cfgRows)} of {n}'
                     f'  (scroll: arrows or wheel)', attr('dim')))
        elif n <= 1:
            row(Cell('      (no YAML files here)', attr('dim')))

    def _cfg_toggle_all(self):
        self.cfgAll = not self.cfgAll

    def _cfg_toggle_show(self):
        self.cfgShow = not self.cfgShow

    # ---- form ------------------------------------------------------------
    def rows(self, width):
        R = []

        def section(title):
            R.append(('section', title))

        def row(*cells):
            R.append(('row', [c for c in cells if c is not None]))

        section('Reset And Configuration')
        row(self.label('Poll Enable:'), self.enum(self._p('PollEn')),
            self.label('   Local Time:'), self.value(self._p('LocalTime')),
            self.label('   Rogue Version:'), self.value(self._p('RogueVersion')))
        row(self.button('Hard Reset', self._p('HardReset')),
            self.button('Initialize', self._p('Initialize')),
            self.button('Count Reset', self._p('CountReset')))
        fw = max(20, width - 34)
        for key, lab in (('LoadConfig', 'Load Config'), ('SaveConfig', 'Save Config'),
                         ('SaveState', 'Save State ')):
            row(self.button(lab, self._p(key), arg=lambda k=key: self.fields[k],
                            enabled=bool(self.fields[key])),
                self.field(key, fw),
                self.ui_button('Browse', lambda k=key: self._browse_field(k), f'browse:{key}'))
            if key == 'LoadConfig':
                self._cfg_rows(row, width)

        for w in self.writers:
            section(f'Data File Control ({w})')
            isOpen = self.session.disp(self.srv, self._p(f'{w}.IsOpen'), 'False') == 'True'
            row(self.label('Data File:'), self._data_file(w, width - 14, not isOpen))
            row(self.ui_button('Browse', lambda w=w: self._browse_data(w), f'browse:{w}', enabled=not isOpen),
                self.button('Auto Name', self._p(f'{w}.AutoName'), enabled=not isOpen),
                self.button('Open', self._p(f'{w}.Open'), enabled=not isOpen),
                self.button('Close', self._p(f'{w}.Close'), enabled=isOpen))
            row(self.label('        File Open:'), self._is_open(w),
                self.label('      Frame Count:'), self.value(self._p(f'{w}.FrameCount')))
            row(self.label('Current File Size:'), self.value(self._p(f'{w}.CurrentSize'), 18),
                self.label('        Bandwidth:'), self.value(self._p(f'{w}.Bandwidth'), units='Bytes/sec'))
            row(Cell(' ' * 37), self.label('  Total File Size:'), self.value(self._p(f'{w}.TotalSize')))

        for rc in self.runctrls:
            section(f'Run Control ({rc})')
            row(self.label(' Run Rate:'), self.enum(self._p(f'{rc}.runRate')))
            row(self.label('Run State:'), self.enum(self._p(f'{rc}.runState')),
                self.label('   Run Count:'), self.value(self._p(f'{rc}.runCount')))

        entries = self._log()
        shown = entries if self.logAll else entries[-20:]
        section(f'System Log ({"all " + str(len(entries)) if self.logAll else "20 most recent"} entries)')
        if not shown:
            row(Cell('(empty)', attr('dim')))
        for ent in shown:
            key = (ent.get('created'), ent.get('message'))
            opened = key in self.logOpen
            tags = []
            if ent.get('rogueCpp'):
                tags.append('C++')
            if ent.get('rogueComponent') is not None:
                tags.append(str(ent['rogueComponent']))
            st = time.strftime('%Y-%m-%d %H:%M:%S %Z', time.localtime(ent.get('created', 0)))
            if tags:
                st += f" [{' '.join(tags)}]"
            msg = str(ent.get('message', '')).replace('\n', ' ')
            g = ui.G_OPEN if opened else ui.G_CLOSED
            lvl = f"{ent.get('levelName', '')[:5]:5s}"
            row(Cell(f'{g} {st} {lvl} {msg}'.ljust(width - 2)[:max(width - 2, 10)],
                     level_attr(ent.get('levelNumber')), cid=f'log:{key}',
                     desc=msg + '   (i: full entry)', action=lambda k=key: self._toggle_log(k)))
            if opened:
                for lab, val in self._log_details(ent):
                    row(Cell(f'      {lab.rjust(12)}: {val}', attr('dim')))
        row(self.button('Clear Log', self._p('ClearLog')))
        return R

    def _is_open(self, w):
        c = self.value(self._p(f'{w}.IsOpen'), 18)
        if c.text.strip() == 'True':
            c.a = attr('ok') | curses.A_BOLD
        return c

    def _data_file(self, w, width, enabled):
        c = self.edit_var(self._p(f'{w}.DataFile'), max(20, width))
        if not enabled:
            c.action = None
            c.a = attr('dim')
        return c

    def _log(self):
        try:
            raw = self.session.value(self.srv, self._p('SystemLog')).value
        except Exception:  # noqa: BLE001
            return []
        if raw is not self._logCache[0]:
            try:
                self._logCache = (raw, json.loads(raw))
            except (TypeError, ValueError):
                self._logCache = (raw, [])
        return self._logCache[1]

    @staticmethod
    def _log_details(ent):
        out = [('Name', str(ent.get('name'))),
               ('Level', f"{ent.get('levelName')} ({ent.get('levelNumber')})")]
        if ent.get('rogueCpp'):
            out.append(('Source', 'Rogue C++'))
        for lab, k in (('Component', 'rogueComponent'), ('Rogue Logger', 'rogueLogger'),
                       ('Rogue TID', 'rogueTid'), ('Rogue PID', 'roguePid')):
            if ent.get(k) is not None:
                out.append((lab, str(ent[k])))
        msg = str(ent.get('message', ''))
        if '\n' in msg or len(msg) > 80:
            out += [('Message', ln) for ln in msg.splitlines()]
        if ent.get('exception') is not None:
            out.append(('exception', str(ent['exception'])))
            out += [('', ln.rstrip()) for tb in ent.get('traceBack') or [] for ln in tb.splitlines()]
        return out

    def _toggle_log(self, key):
        if key in self.logOpen:
            self.logOpen.remove(key)
        else:
            self.logOpen.add(key)

    def layout(self, width):
        """Wrap rows into screen lines: list of [(x, cell)] or ('section', title)."""
        lines = []
        for kind, data in self.rows(width):
            if kind == 'section':
                if lines:
                    lines.append([])
                lines.append(('section', data))
                continue
            line, x = [], 1
            for c in data:
                n = len(c.text)
                if x > 1 and x + n > width:
                    lines.append(line)
                    line, x = [], 3
                line.append((x, c))
                x += n + 1
            lines.append(line)
        return lines

    def _focusables(self):
        out = []
        for li, line in enumerate(self._lines):
            if isinstance(line, tuple):
                continue
            for x, c in line:
                if c.focusable:
                    out.append((li, x, c))
        return out

    def _current(self):
        f = self._focusables()
        if not f:
            return f, None
        for i, (li, x, c) in enumerate(f):
            if c.cid == self.focus:
                self._focusPos = (li, x)
                return f, i
        # focused cell vanished or got disabled (e.g. Open after opening): stay
        # nearby rather than jumping to the top, where Enter would hit Hard Reset
        li0, x0 = getattr(self, '_focusPos', (0, 0))
        i = min(range(len(f)), key=lambda j: (abs(f[j][0] - li0), abs(f[j][1] - x0)))
        self.focus = f[i][2].cid
        self._focusPos = f[i][:2]
        return f, i

    def draw(self, win, y0, h, w):
        self._lines = self.layout(w)
        self._y0, self._h = y0, h
        f, i = self._current()
        if i is not None:
            self.focus = f[i][2].cid
            li = f[i][0]
            # follow the focus only when it moved, so the wheel can scroll freely
            if self.focus != self._shownFocus:
                if li < self.top:
                    self.top = max(0, li - 1)
                if li >= self.top + h:
                    self.top = li - h + 2
                self._shownFocus = self.focus
        self.top = max(0, min(self.top, max(0, len(self._lines) - h)))
        for r in range(h):
            li = self.top + r
            if li >= len(self._lines):
                break
            line = self._lines[li]
            if isinstance(line, tuple):
                t = f'{ui.HLINE * 2} {line[1]} '
                put(win, y0 + r, 0, t + ui.HLINE * max(0, w - len(t) - 1), attr('section'))
                continue
            for x, c in line:
                a = attr('sel') if (c.cid == self.focus and c.focusable) else c.a
                put(win, y0 + r, x, c.text, a)
        if self.top > 0:
            put(win, y0, w - 3, ' ^ ', attr('dim'))
        if self.top + h < len(self._lines):
            put(win, y0 + h - 1, w - 3, ' v ', attr('dim'))
        return None

    def describe(self):
        f, i = self._current()
        if i is None:
            return ''
        c = f[i][2]
        return c.desc or (c.cid if not c.cid.startswith(('btn:', 'log:', 'field:', 'browse:', 'cfg')) else '')

    def _move_line(self, d):
        f, i = self._current()
        if i is None:
            return
        li, x, _ = f[i]
        cand = [e for e in f if (e[0] < li if d < 0 else e[0] > li)]
        if not cand:
            return
        target = max(e[0] for e in cand) if d < 0 else min(e[0] for e in cand)
        same = [e for e in cand if e[0] == target]
        self.focus = min(same, key=lambda e: abs(e[1] - x))[2].cid

    def _cfg_key(self, k):
        """Arrow keys inside the directory panel scroll it; at its ends they leave it."""
        entries, _ = self._cfg_entries()
        names = [e.name for e in entries]
        name = self.focus[4:]
        if name not in names:
            return False
        i, n = names.index(name), len(names)
        step = {curses.KEY_UP: -1, 'k': -1, curses.KEY_DOWN: 1, 'j': 1,
                curses.KEY_PPAGE: -self.cfgRows, curses.KEY_NPAGE: self.cfgRows}.get(k)
        if step is None:
            if k in ui.K_BACKSPACE:
                self._cfg_chdir('..')
                return True
            if k == ' ':
                self._cfg_toggle(entries[i])
                return True
            return False
        j = i + step
        if not (0 <= j < n) and abs(step) == 1:
            return False
        j = max(0, min(n - 1, j))
        self.focus = 'cfg:' + names[j]
        if j < self.cfgTop:
            self.cfgTop = j
        if j >= self.cfgTop + self.cfgRows:
            self.cfgTop = j - self.cfgRows + 1
        return True

    def key(self, k):
        if self.focus and self.focus.startswith('cfg:') and self._cfg_key(k):
            return True
        f, i = self._current()
        if k in (curses.KEY_UP, 'k'):
            self._move_line(-1)
        elif k in (curses.KEY_DOWN, 'j'):
            self._move_line(1)
        elif k in (curses.KEY_LEFT, 'h') and i is not None:
            self.focus = f[max(0, i - 1)][2].cid
        elif k in (curses.KEY_RIGHT, 'l') and i is not None:
            self.focus = f[min(len(f) - 1, i + 1)][2].cid
        elif k == curses.KEY_PPAGE:
            for _ in range(max(1, self._h // 2)):
                self._move_line(-1)
        elif k == curses.KEY_NPAGE:
            for _ in range(max(1, self._h // 2)):
                self._move_line(1)
        elif k == curses.KEY_HOME and f:
            self.focus = f[0][2].cid
        elif k == curses.KEY_END and f:
            self.focus = f[-1][2].cid
        elif k in ui.K_ENTER and i is not None:
            f[i][2].action()
        elif k == ' ' and i is not None:
            (f[i][2].space or f[i][2].action)()
        elif k == 'a':
            self.logAll = not self.logAll
        elif k == 'e':
            ents = self._log() if self.logAll else self._log()[-20:]
            keys = {(e.get('created'), e.get('message')) for e in ents}
            self.logOpen = set() if self.logOpen & keys else keys
        elif k == 'i' and i is not None and f[i][2].cid.startswith('log:'):
            self._log_entry(f[i][2].cid)
        elif k == 'i' and i is not None:
            self._info(f[i][2].cid)
        else:
            return False
        return True

    def _log_entry(self, cid):
        for ent in self._log():
            if f'log:{(ent.get("created"), ent.get("message"))}' == cid:
                lines = [(str(ent.get('message', '')), level_attr(ent.get('levelNumber')))]
                lines += [f'{a.rjust(12)}: {b}' for a, b in self._log_details(ent)]
                self.app.push(ui.TextView('System Log entry', lines))
                return

    def _info(self, cid):
        path = cid[4:] if cid.startswith('btn:') else cid
        try:
            self.info(self.node(path))
        except Exception:  # noqa: BLE001
            self.app.status('no node behind this item')

    def mouse(self, kind, y, x):
        li = self.top + (y - self._y0)
        line = self._lines[li] if 0 <= li < len(self._lines) else None
        hit = None
        if line and not isinstance(line, tuple):
            for cx, c in line:
                if cx <= x < cx + len(c.text):
                    hit = (cx, c)
        if kind in ('wheelup', 'wheeldown'):
            d = -3 if kind == 'wheelup' else 3
            if hit and hit[1].cid.startswith('cfg:'):
                self.cfgTop = max(0, self.cfgTop + d)
            else:
                self.top = max(0, self.top + d)
            return
        if hit is None or not hit[1].focusable:
            return
        cx, c = hit
        self.focus = c.cid
        if kind == 'click':
            if c.click:
                c.click(x - cx)
            else:
                c.action()
        elif kind == 'right':
            if c.cid.startswith('log:'):
                self._log_entry(c.cid)
            else:
                self._info(c.cid)


# ---------------------------------------------------------------------------
# Debug Tree tab
# ---------------------------------------------------------------------------
class Item:
    """Tree row: 'button' (Read All), 'dev', 'group', 'var' or 'cmd'."""

    def __init__(self, kind, parent, meta=None, name=''):
        self.kind = kind
        self.parent = parent
        self.meta = meta
        self.name = meta.name if meta else name
        self.depth = parent.depth + 1 if parent is not None else 0
        self.children = None
        self.expanded = False
        self.groupNodes = []

    @property
    def expandable(self):
        return self.kind in ('dev', 'group')


COLS = ['Node', 'Mode', 'Type', 'ByteOffset [BitRange]', 'Value', 'Command']


class TreeView(View):
    keys = [('Enter', 'Edit/Exec', 10), ('Spc', 'Expand', ' '), ('o', 'Menu', 'o'),
            ('r', 'Read', 'r'), ('R', 'ReadRec', 'R'), ('w', 'Write', 'w'), ('W', 'WriteRec', 'W'),
            ('A', 'ReadAll', 'A'), ('i', 'Info', 'i'), ('f', 'File', 'f'), ('/', 'Find', '/'),
            ('n', 'Next', 'n'), ('g', 'Goto', 'g'), ('*', 'ExpandAll', '*'), ('_', 'Collapse', '_'),
            ('c', 'Columns', 'c'), ('y', 'Copy', 'y'), ('Y', 'CopyPath', 'Y')]

    def __init__(self, app, srv, path):
        super().__init__(app, srv, path)
        self.colShown = [True, True, True, False, True, True]
        self.sel = 1
        self.top = 0
        self.search = ''
        rootNode = self.node()
        self.rootMeta = self.session.meta(srv, rootNode)
        self.toolbar = Item('button', None, name='Read All' if self.rootMeta.isRoot else 'Read Recursive')
        self.root = Item('dev', None, self.rootMeta)
        self._build(self.root, autoExpand=True)
        self.root.expanded = True
        self._flat = None
        self._widthsCache = [0] * 6
        self._y0, self._h = 2, 10

    # ---- structure -------------------------------------------------------
    def _make(self, parent, meta, autoExpand):
        if meta.isDevice:
            it = Item('dev', parent, meta)
            if autoExpand and meta.expand:
                self._build(it, autoExpand=True)
                it.expanded = True
        else:
            it = Item('cmd' if meta.isCommand else 'var', parent, meta)
        return it

    def _build(self, item, autoExpand=False):
        """DebugDev._setup / DebugGroup._setup: vars, commands, then devices; guiGroups fold."""
        if item.children is not None:
            return
        item.children = []
        if item.kind == 'group':
            for n in item.groupNodes:
                item.children.append(self._make(item, self.session.meta(self.srv, n), False))
            return
        variables, devices = self.session.children(self.srv, item.meta.node)
        groups = {}
        for n in variables + devices:
            if n.guiGroup is not None:
                g = groups.get(n.guiGroup)
                if g is None:
                    g = groups[n.guiGroup] = Item('group', item, name=n.guiGroup)
                    item.children.append(g)
                g.groupNodes.append(n)
            else:
                item.children.append(self._make(item, self.session.meta(self.srv, n), autoExpand))

    def _flatten(self):
        if self._flat is None:
            out = [self.toolbar]

            def walk(it):
                out.append(it)
                if it.expanded and it.children:
                    for c in it.children:
                        walk(c)
            walk(self.root)
            self._flat = out
        return self._flat

    def _changed(self):
        self._flat = None

    def _set_expanded(self, it, state):
        if not it.expandable:
            return
        if state:
            self.app.status(f'loading {it.name} ...', now=True)
            try:
                self._build(it)
            except Exception as e:  # noqa: BLE001
                self.app.status(f'expand {it.name}: {e}', level='error')
                return
            self.app.status('')
        it.expanded = state
        self._changed()

    def _select_item(self, target):
        p = target.parent
        while p is not None:
            if not p.expanded:
                p.expanded = True
                self._changed()
            p = p.parent
        self.sel = self._flatten().index(target)

    def _all_loaded(self, it=None):
        it = it or self.root
        yield it
        for c in it.children or []:
            yield from self._all_loaded(c)

    def _expand_all(self, it):
        if not it.expandable:
            it = it.parent
        if it is None:
            return
        t0 = time.time()
        stack = [it]
        n = 0
        while stack:
            cur = stack.pop()
            self._build(cur)
            cur.expanded = True
            n += 1
            stack += [c for c in cur.children if c.expandable]
        self._changed()
        self.app.status(f'expanded {n} nodes under {it.name} in {time.time() - t0:.1f} s')

    def _collapse_all(self):
        for it in self._all_loaded():
            if it is not self.root:
                it.expanded = False
        self._changed()
        self.sel = min(self.sel, len(self._flatten()) - 1)

    def goto(self, path):
        """Expand down to a node by path ('root.' prefix or relative path accepted)."""
        try:
            node = self.node(path)
        except Exception as e:  # noqa: BLE001
            self.app.status(str(e), level='error')
            return
        base = self.rootMeta.path
        if node.path != base and not node.path.startswith(base + '.'):
            self.app.status(f'{node.path} is not under {base}', level='error')
            return
        it = self.root
        for name in node.path[len(base):].split('.')[1:]:
            nxt = self._find_child(it, name)
            if nxt is None:
                self.app.status(f'{name} not shown under {it.name} (group filter?)', level='error')
                return
            it = nxt
        self._select_item(it)

    def _find_child(self, it, name):
        self._build(it)
        for c in it.children:
            if c.kind == 'group':
                if any(n.name == name for n in c.groupNodes):
                    self._build(c)
                    return self._find_child(c, name)
            elif c.name == name:
                return c
        return None

    def find(self, text, step=1):
        if not text:
            return
        items = [i for i in self._all_loaded() if i.kind != 'button']
        flat = self._flatten()
        cur = flat[self.sel] if 0 <= self.sel < len(flat) else None
        start = items.index(cur) if cur in items else 0
        tl = text.lower()
        for d in range(1, len(items) + 1):
            it = items[(start + d * step) % len(items)]
            if tl in it.name.lower() or (it.meta and tl in it.meta.path.lower()):
                self._select_item(it)
                return
        self.app.status(f'"{text}" not found in loaded nodes (use * to load a subtree, g to go to a path)',
                        level='error')

    # ---- actions ---------------------------------------------------------
    def _cur(self):
        flat = self._flatten()
        self.sel = max(0, min(self.sel, len(flat) - 1))
        return flat[self.sel]

    def _read_all(self):
        n = self.rootMeta.node
        if self.rootMeta.isRoot:
            self.call(n.ReadAll, label='ReadAll')
        else:
            self.call(n.ReadDevice, True, label=f'{n.name}.ReadDevice(recursive)')

    def activate(self, it, anchor=None):
        if it.kind == 'button':
            self._read_all()
        elif it.expandable:
            self._set_expanded(it, not it.expanded)
        else:
            self.edit(it.meta, anchor)

    def _command_col(self, it):
        """Command column: device [Read] (recursive, as the PyDM button) or [Exec]."""
        if it.kind == 'dev':
            self.call(it.meta.node.ReadDevice, True, label=f'{it.name}.ReadDevice')
        elif it.kind == 'cmd':
            self.edit(it.meta)

    def read(self, it, recursive):
        """pyrogue.pydm.tools ReadNode / ReadRecursive."""
        if it.kind == 'dev':
            self.call(it.meta.node.ReadDevice, recursive,
                      label=f'{it.name}.ReadDevice({"recursive" if recursive else "node"})')
        elif it.kind == 'var':
            if recursive:
                p = it.meta.node.parent
                self.call(p.ReadDevice, True, label=f'{p.name}.ReadDevice(recursive)')
            elif it.meta.mode == 'WO':
                self.app.status(f"Can't read from write only variable: {it.meta.path}", level='error')
            else:
                node = it.meta.node
                self.run(f'{it.name}.get()', lambda: node.get())
        elif it.kind == 'button':
            self._read_all()
        else:
            self.app.status(f"Can't read from non variable: {it.name}", level='error')

    def write(self, it, recursive):
        """pyrogue.pydm.tools WriteNode / WriteRecursive."""
        if it.kind == 'dev':
            self.call(it.meta.node.WriteDevice, recursive,
                      label=f'{it.name}.WriteDevice({"recursive" if recursive else "node"})')
        elif it.kind == 'var':
            if recursive:
                p = it.meta.node.parent
                self.call(p.WriteDevice, True, label=f'{p.name}.WriteDevice(recursive)')
            elif it.meta.mode == 'RO':
                self.app.status(f"Can't write to read only variable: {it.meta.path}", level='error')
            else:
                node = it.meta.node
                self.run(f'{it.name}.write()', lambda: node.write())
        else:
            self.app.status(f"Can't write to non variable: {it.name}", level='error')

    def browse(self, it):
        """pyrogue.pydm.tools GenericFile: pick a file and set it / pass it to a command."""
        if it.kind not in ('var', 'cmd'):
            self.app.status('File browser used with invalid node', level='error')
            return
        if it.kind == 'var' and it.meta.mode == 'RO':
            self.app.status(f"Can't set file to RO node: {it.name}", level='error')
            return
        node = it.meta.node
        save = it.name.lower().startswith(('save', 'write')) or it.name in ('DataFile',)

        def done(p):
            if not p:
                return
            if it.kind == 'cmd':
                self.call(node, p)
            else:
                self.run(f'{it.name} <- {p!r}', lambda: (node.set(p), node.get()))
        self.app.push(ui.FileBrowser(f'Select {"save" if save else "open"} file for {it.name}',
                                     ('*.yml', '*.dat', '*.csv', '*.npy'), save=save, on_done=done))

    def copy(self, it, path=False):
        if path:
            if it.meta is None:
                return
            txt = it.meta.path
        elif it.meta is not None and it.kind in ('var', 'cmd'):
            txt = self.session.disp(self.srv, it.meta.path, '')
        else:
            txt = it.name
        ui.copy_to_clipboard(txt)
        self.app.status(f'copied{" path" if path else ""}: {txt}'[:200])

    def menu(self, it, anchor=None):
        """The PyDM right-click menu (Rogue tools) for a row."""
        items = []

        def add(label, fn):
            items.append((label, fn))
        m = it.meta
        if it.kind == 'button':
            add(it.name, self._read_all)
        elif it.kind == 'group':
            add('Collapse' if it.expanded else 'Expand', lambda: self._set_expanded(it, not it.expanded))
            add('Expand all below', lambda: self._expand_all(it))
        else:
            if it.kind == 'dev':
                add('Collapse' if it.expanded else 'Expand', lambda: self._set_expanded(it, not it.expanded))
                add('Expand all below', lambda: self._expand_all(it))
            elif it.kind == 'cmd':
                add('Execute...' if m.arg else 'Execute', lambda: self.edit(m))
                add('Execute with file...', lambda: self.browse(it))
            elif m.writable:
                add('Edit value...', lambda: self.edit(m))
            if it.kind != 'cmd':
                if it.kind == 'dev' or m.mode != 'WO':
                    add('Read Node', lambda: self.read(it, False))
                add('Read Recursive', lambda: self.read(it, True))
                if it.kind == 'dev' or m.mode != 'RO':
                    add('Write Node', lambda: self.write(it, False))
                add('Write Recursive', lambda: self.write(it, True))
            if it.kind == 'var' and m.mode != 'RO':
                add('Set from file...', lambda: self.browse(it))
            add('Node Information', lambda: self.info(m.node))
            if it.kind in ('var', 'cmd'):
                add('Copy value', lambda: self.copy(it))
            add('Copy Path', lambda: self.copy(it, path=True))
        self.app.push(ui.Choose(it.name, [lab for lab, _ in items], 0, anchor=anchor,
                                on_done=lambda i: i is not None and items[i][1]()))

    # ---- drawing ---------------------------------------------------------
    def _widths(self, w, flat):
        nodeW = max([2 * it.depth + 3 + len(it.name) for it in flat if it.kind != 'button'] + [12])
        typeW = max([len(it.meta.typeStr) for it in flat if it.meta and it.meta.typeStr] + [4])
        widths = [min(nodeW, max(20, int(w * 0.45))), 4, min(typeW, 14), 18, 0, 10]
        shown = [widths[i] if self.colShown[i] else 0 for i in range(6)]
        rest = w - sum(shown) - sum(1 for i in range(6) if self.colShown[i]) - 1
        if self.colShown[4]:
            shown[4] = max(8, rest)
        return shown

    def _col_x(self, i):
        widths = self._widthsCache
        return sum(widths[j] + 1 for j in range(i) if widths[j])

    def draw(self, win, y0, h, w):
        flat = self._flatten()
        self.sel = max(0, min(self.sel, len(flat) - 1))
        widths = self._widths(w, flat)
        self._widthsCache = widths
        put(win, y0, 0, ' ' * w, attr('colhdr'))
        x = 0
        for i, name in enumerate(COLS):
            if widths[i]:
                put(win, y0, x, name.ljust(widths[i])[:widths[i]], attr('colhdr') | curses.A_BOLD)
                x += widths[i] + 1
        rows = h - 1
        if self.sel < self.top:
            self.top = self.sel
        if self.sel >= self.top + rows:
            self.top = self.sel - rows + 1
        self.top = max(0, min(self.top, max(0, len(flat) - rows)))
        for r in range(rows):
            j = self.top + r
            if j >= len(flat):
                break
            self._draw_row(win, y0 + 1 + r, flat[j], widths, j == self.sel, w)
        if self.top + rows < len(flat):
            put(win, y0 + h - 1, w - 3, ' v ', attr('dim'))
        self._y0, self._h = y0, h
        return None

    def _draw_row(self, win, y, it, widths, selected, w):
        cells = [''] * 6
        ca = [0] * 6
        sel = attr('sel')
        if it.kind == 'button':   # toolbar row ignores the columns
            put(win, y, 0, f'[ {it.name} ]', sel if selected else attr('button'))
            return
        g = (ui.G_OPEN if it.expanded else ui.G_CLOSED) if it.expandable else ui.G_LEAF
        cells[0] = '  ' * it.depth + f'{g} {it.name}'
        ca[0] = {'dev': attr('dev'), 'group': attr('group'), 'cmd': attr('cmd')}.get(it.kind, 0)
        m = it.meta
        if it.kind == 'dev':
            cells[3], ca[3] = m.offsetStr(), attr('dim')
            cells[5], ca[5] = '[Read]', attr('button')
        elif it.kind in ('var', 'cmd'):
            cells[1] = m.mode
            ca[1] = {'RW': attr('rw'), 'WO': attr('wo')}.get(m.mode, 0)
            cells[2], ca[2] = m.typeStr, attr('dim')
            cells[3], ca[3] = m.offsetStr(), attr('dim')
            if it.kind == 'var' or m.arg:
                try:
                    v = self.session.value(self.srv, m.path)
                    cells[4], ca[4] = v.valueDisp, severity_attr(v)
                except Exception:  # noqa: BLE001
                    cells[4], ca[4] = 'n/a', attr('dim')
                if m.units and it.kind == 'var':
                    cells[4] += f' {m.units}'
                if m.isEnum and it.kind == 'var':
                    cells[4] += f' {ui.G_OPEN}'
            if it.kind == 'cmd':
                cells[5], ca[5] = ('[Exec...]' if m.arg else '[Exec]'), attr('button')
                if m.arg:
                    cells[4] = f'arg: {cells[4]}'
                    ca[4] = attr('dim')
        if selected:
            put(win, y, 0, ' ' * w, sel)
        x = 0
        for i in range(6):
            if not widths[i]:
                continue
            text = cells[i]
            if len(text) > widths[i]:
                text = text[:widths[i] - 1] + ('…' if ui.UTF8 else '>')
            put(win, y, x, text.ljust(widths[i]), sel if selected else ca[i])
            x += widths[i] + 1

    def describe(self):
        it = self._cur()
        if it.kind == 'button':
            return 'Read all variables from hardware' if self.rootMeta.isRoot else 'Recursive read of this device'
        if it.kind == 'group':
            return f'guiGroup {it.name}'
        return f'{it.meta.path}: {it.meta.description}'

    # ---- input -----------------------------------------------------------
    def key(self, k):
        flat = self._flatten()
        it = self._cur()
        n = len(flat)
        if k in (curses.KEY_UP, 'k'):
            self.sel = max(0, self.sel - 1)
        elif k in (curses.KEY_DOWN, 'j'):
            self.sel = min(n - 1, self.sel + 1)
        elif k == curses.KEY_PPAGE:
            self.sel = max(0, self.sel - max(1, self._h - 2))
        elif k == curses.KEY_NPAGE:
            self.sel = min(n - 1, self.sel + max(1, self._h - 2))
        elif k == curses.KEY_HOME:
            self.sel = 0
        elif k == curses.KEY_END:
            self.sel = n - 1
        elif k in (curses.KEY_RIGHT, 'l', '+'):
            if it.expandable and not it.expanded:
                self._set_expanded(it, True)
            elif it.expandable and it.children:
                self.sel += 1
        elif k in (curses.KEY_LEFT, 'h', '-'):
            if it.expandable and it.expanded and it is not self.root:
                self._set_expanded(it, False)
            elif it.parent is not None:
                self._select_item(it.parent)
        elif k in ui.K_ENTER:
            self.activate(it)
        elif k == ' ':
            if it.expandable:
                self._set_expanded(it, not it.expanded)
            else:
                self.activate(it)
        elif k == 'e' and it.kind in ('var', 'cmd'):
            self.edit(it.meta)
        elif k in ('o', curses.KEY_F10):
            r = self.sel - self.top
            self.menu(it, anchor=(self._y0 + 2 + r, min(2 * it.depth + 4, 40)))
        elif k == 'x':
            self._command_col(it)
        elif k == 'r':
            self.read(it, False)
        elif k == 'R':
            self.read(it, True)
        elif k == 'w':
            self.write(it, False)
        elif k == 'W':
            self.write(it, True)
        elif k == 'A':
            self._read_all()
        elif k == 'i' and it.meta is not None:
            self.info(it.meta.node)
        elif k == 'f':
            self.browse(it)
        elif k == '*':
            self._expand_all(it)
        elif k == '_':
            self._collapse_all()
        elif k == 'c':
            self._columns()
        elif k == 'y':
            self.copy(it)
        elif k == 'Y':
            self.copy(it, path=True)
        elif k == '/':
            def done(t):
                if t:
                    self.search = t
                    self.find(t)
            self.app.push(ui.Prompt('Find', self.search, 'Name or path substring (loaded nodes):',
                                    on_done=done))
        elif k == 'n':
            self.find(self.search, 1)
        elif k == 'N':
            self.find(self.search, -1)
        elif k == 'g':
            self.app.push(ui.Prompt('Go to node', it.meta.path if it.meta else self.path,
                                    'Path (root.X.Y or X.Y):', on_done=lambda t: t and self.goto(t.strip())))
        else:
            return False
        return True

    def _columns(self):
        def done(states):
            if states is not None:
                self.colShown = [True] + states[1:]
        self.app.push(ui.Checklist('Columns', COLS, self.colShown, on_done=done))

    def mouse(self, kind, y, x):
        flat = self._flatten()
        if kind == 'wheelup':
            self.sel = max(0, self.sel - 3)
            return
        if kind == 'wheeldown':
            self.sel = min(len(flat) - 1, self.sel + 3)
            return
        r = y - self._y0 - 1
        if r == -1 and kind == 'click':
            self._columns()            # click on the column header
            return
        j = self.top + r
        if r < 0 or j >= len(flat):
            return
        self.sel = j
        it = flat[j]
        if kind == 'right':
            self.menu(it, anchor=(y + 1, min(x, 60)))
            return
        glyph = x <= 2 * it.depth + 1
        if kind == 'double':
            if it.expandable and not glyph:
                self._set_expanded(it, not it.expanded)
            elif it.kind in ('var', 'cmd'):
                self.activate(it)
            return
        if kind != 'click':
            return
        widths = self._widthsCache
        if it.kind == 'button':
            self._read_all()
        elif widths[5] and x >= self._col_x(5):
            self._command_col(it)
        elif it.expandable and glyph:
            self._set_expanded(it, not it.expanded)
        elif (widths[4] and self._col_x(4) <= x < self._col_x(4) + widths[4] and it.kind in ('var', 'cmd')
              and (it.meta.writable or it.meta.isEnum or (it.kind == 'cmd' and it.meta.arg))):
            self.edit(it.meta, anchor=(y + 1, self._col_x(4)))
