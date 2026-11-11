#-----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
#-----------------------------------------------------------------------------
#  Description:
#       PyRogue TUI: curses drawing helpers and dialogs
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
curses building blocks: colours, clipped drawing, a line editor and the modal
dialogs (prompt, choice list, checklist, text viewer, confirm, file browser).
Dialogs are non-blocking: the app draws the top one each frame, routes keys
and mouse events to it and calls on_done(result) when it closes (result None
means cancelled). Mouse events arrive as kind in {'click', 'double', 'right',
'wheelup', 'wheeldown'}.
"""
import base64
import curses
import datetime
import fnmatch
import glob
import locale
import os
import time

UTF8 = 'UTF-8' in (locale.getpreferredencoding(False) or '').upper()
G_OPEN, G_CLOSED, G_LEAF = ('▾', '▸', ' ') if UTF8 else ('-', '+', ' ')
HLINE = '─' if UTF8 else '-'

# Normalised control keys (get_wch returns str for these).
K_ENTER = (10, 13, curses.KEY_ENTER)
K_ESC = 27
K_BACKSPACE = (curses.KEY_BACKSPACE, 127, 8)
K_TAB = 9

C = {}

# name: (fg, bg, extra attrs); bg None = terminal default
PALETTE = {
    'header':   (curses.COLOR_WHITE, curses.COLOR_BLUE, curses.A_BOLD),
    'linkbad':  (curses.COLOR_WHITE, curses.COLOR_RED, curses.A_BOLD),
    'tab':      (curses.COLOR_BLACK, curses.COLOR_CYAN, curses.A_BOLD),
    'tabin':    (curses.COLOR_CYAN, None, 0),
    'sel':      (curses.COLOR_BLACK, curses.COLOR_CYAN, 0),
    'colhdr':   (curses.COLOR_WHITE, curses.COLOR_BLUE, 0),
    'section':  (curses.COLOR_MAGENTA, None, curses.A_BOLD),
    'dev':      (curses.COLOR_CYAN, None, curses.A_BOLD),
    'group':    (curses.COLOR_MAGENTA, None, curses.A_BOLD),
    'cmd':      (curses.COLOR_YELLOW, None, 0),
    'rw':       (curses.COLOR_GREEN, None, 0),
    'wo':       (curses.COLOR_YELLOW, None, 0),
    'dim':      (curses.COLOR_BLUE, None, 0),
    'button':   (curses.COLOR_CYAN, None, curses.A_BOLD),
    'field':    (curses.COLOR_BLACK, curses.COLOR_WHITE, 0),
    'major':    (curses.COLOR_WHITE, curses.COLOR_RED, curses.A_BOLD),
    'minor':    (curses.COLOR_BLACK, curses.COLOR_YELLOW, 0),
    'err':      (curses.COLOR_RED, None, curses.A_BOLD),
    'warn':     (curses.COLOR_YELLOW, None, curses.A_BOLD),
    'ok':       (curses.COLOR_GREEN, None, 0),
    'keykey':   (curses.COLOR_WHITE, curses.COLOR_BLACK, curses.A_BOLD),
    'keytext':  (curses.COLOR_BLACK, curses.COLOR_CYAN, 0),
    'border':   (curses.COLOR_CYAN, None, 0),
    'dtitle':   (curses.COLOR_YELLOW, None, curses.A_BOLD),
    'dir':      (curses.COLOR_BLUE, None, curses.A_BOLD),
    'cfgfile':  (curses.COLOR_GREEN, None, 0),
    'marked':   (curses.COLOR_YELLOW, None, curses.A_BOLD),
}

# Without colours: keep the meaning with reverse/bold/underline
MONO = {'header': curses.A_REVERSE | curses.A_BOLD, 'linkbad': curses.A_REVERSE | curses.A_BOLD,
        'tab': curses.A_REVERSE | curses.A_BOLD, 'sel': curses.A_REVERSE, 'colhdr': curses.A_UNDERLINE,
        'section': curses.A_BOLD, 'dev': curses.A_BOLD, 'group': curses.A_BOLD, 'button': curses.A_BOLD,
        'field': curses.A_UNDERLINE, 'major': curses.A_REVERSE | curses.A_BOLD, 'minor': curses.A_BOLD,
        'err': curses.A_BOLD, 'warn': curses.A_BOLD, 'keykey': curses.A_BOLD, 'keytext': curses.A_REVERSE,
        'dtitle': curses.A_BOLD, 'dir': curses.A_BOLD, 'marked': curses.A_BOLD}


def init_colors():
    if os.environ.get('NO_COLOR') or not curses.has_colors():
        C.update(MONO)
        return
    curses.start_color()
    try:
        curses.use_default_colors()
        default = -1
    except curses.error:
        default = curses.COLOR_BLACK
    for i, (name, (fg, bg, extra)) in enumerate(PALETTE.items(), start=1):
        try:
            curses.init_pair(i, fg, default if bg is None else bg)
            C[name] = curses.color_pair(i) | extra
        except curses.error:
            C[name] = MONO.get(name, 0)


def attr(name):
    return C.get(name, 0)


def put(win, y, x, text, a=0, width=None):
    """addstr clipped to the window (and to width); never raises."""
    h, w = win.getmaxyx()
    if y < 0 or y >= h or x >= w:
        return 0
    if x < 0:
        text = text[-x:]
        x = 0
    room = w - x if width is None else min(width, w - x)
    if room <= 0:
        return 0
    text = text[:room]
    try:
        win.addstr(y, x, text, a)
    except curses.error:
        pass  # writing the bottom-right cell raises after the text is drawn
    return len(text)


def box(win, y, x, h, w, title=''):
    """Bordered, cleared rectangle drawn straight onto win."""
    for r in range(h):
        put(win, y + r, x, ' ' * w)
    a = attr('border')
    try:
        win.attron(a)
        win.hline(y, x + 1, curses.ACS_HLINE, w - 2)
        win.hline(y + h - 1, x + 1, curses.ACS_HLINE, w - 2)
        win.vline(y + 1, x, curses.ACS_VLINE, h - 2)
        win.vline(y + 1, x + w - 1, curses.ACS_VLINE, h - 2)
        win.addch(y, x, curses.ACS_ULCORNER)
        win.addch(y, x + w - 1, curses.ACS_URCORNER)
        win.addch(y + h - 1, x, curses.ACS_LLCORNER)
        win.insch(y + h - 1, x + w - 1, curses.ACS_LRCORNER)
    except curses.error:
        pass
    win.attroff(a)
    if title:
        put(win, y, x + 2, f' {title} '[:w - 4], attr('dtitle'))


def copy_to_clipboard(text):
    """OSC 52: the terminal (incl. over ssh; tmux needs set-clipboard on) sets the clipboard."""
    seq = '\033]52;c;' + base64.b64encode(text.encode()).decode() + '\a'
    if os.environ.get('TMUX'):
        seq = '\033Ptmux;' + seq.replace('\033', '\033\033') + '\033\\'
    try:
        os.write(1, seq.encode())   # raw fd: sys.stdout is captured while the TUI runs
    except OSError:
        pass


def is_char(k):
    return isinstance(k, str) and k.isprintable()


def stamp(fmt):
    return datetime.datetime.now().strftime(fmt)


# ---- directory listing (file browser and the Load Config panel) -----------
class Entry:
    def __init__(self, name, isdir, size, mtime, match):
        self.name = name
        self.isdir = isdir
        self.size = size
        self.mtime = mtime
        self.match = match

    @property
    def label(self):
        return self.name + '/' if self.isdir else self.name

    def info(self):
        if self.name == '..':
            return ''
        if self.isdir:
            return f'{"<dir>":>9}  {fmt_time(self.mtime)}'
        return f'{fmt_size(self.size):>9}  {fmt_time(self.mtime)}'

    def attr(self, marked=False):
        if marked:
            return attr('marked')
        if self.isdir:
            return attr('dir')
        return attr('cfgfile') if self.match else 0


def fmt_size(n):
    for unit in ('B', 'kB', 'MB', 'GB'):
        if n < 1024 or unit == 'GB':
            return f'{n:.0f} {unit}' if unit == 'B' else f'{n:.1f} {unit}'
        n /= 1024
    return ''


def fmt_time(t):
    return time.strftime('%Y-%m-%d %H:%M', time.localtime(t)) if t else ''


def scan_dir(path, patterns=('*',), useFilter=True, showHidden=False):
    """'..' first, then directories, then files; raises OSError."""
    dirs, files = [], []
    for n in os.listdir(path):
        if n.startswith('.') and not showHidden:
            continue
        p = os.path.join(path, n)
        try:
            st = os.stat(p)
        except OSError:
            continue
        match = any(fnmatch.fnmatch(n, pat) for pat in patterns)
        if os.path.isdir(p):
            dirs.append(Entry(n, True, 0, st.st_mtime, False))
        elif match or not useFilter:
            files.append(Entry(n, False, st.st_size, st.st_mtime, match and tuple(patterns) != ('*',)))
    return ([Entry('..', True, 0, 0, False)] + sorted(dirs, key=lambda e: e.name)
            + sorted(files, key=lambda e: e.name))


class LineEdit:
    def __init__(self, text='', complete_paths=False):
        self.text = text
        self.pos = len(text)
        self.scroll = 0
        self.complete_paths = complete_paths
        self._geom = None

    def key(self, k):
        """Edit on k; returns True if consumed."""
        t, p = self.text, self.pos
        if is_char(k):
            self.text = t[:p] + k + t[p:]
            self.pos += len(k)
        elif k in (curses.KEY_LEFT, 2):
            self.pos = max(0, p - 1)
        elif k in (curses.KEY_RIGHT, 6):
            self.pos = min(len(t), p + 1)
        elif k in (curses.KEY_HOME, 1):
            self.pos = 0
        elif k in (curses.KEY_END, 5):
            self.pos = len(t)
        elif k in K_BACKSPACE:
            if p:
                self.text = t[:p - 1] + t[p:]
                self.pos -= 1
        elif k in (curses.KEY_DC, 4):
            self.text = t[:p] + t[p + 1:]
        elif k == 21:  # ^U
            self.text, self.pos = t[p:], 0
        elif k == 11:  # ^K
            self.text = t[:p]
        elif k == 23:  # ^W
            q = len(t[:p].rstrip().rsplit(' ', 1)[0]) if ' ' in t[:p].rstrip() else 0
            self.text, self.pos = t[:q] + t[p:], q
        elif k == K_TAB and self.complete_paths:
            self._complete()
        else:
            return False
        return True

    def _complete(self):
        head = self.text[:self.pos]
        start = head.rfind(',') + 1          # LoadConfig takes comma-separated files
        word = os.path.expanduser(head[start:])
        hits = sorted(glob.glob(word + '*'))
        if not hits:
            return
        common = os.path.commonprefix(hits)
        if len(hits) == 1 and os.path.isdir(common):
            common += '/'
        self.text = self.text[:start] + common + self.text[self.pos:]
        self.pos = start + len(common)

    def draw(self, win, y, x, width, a=None, focus=True):
        a = attr('field') if a is None else a
        if self.pos < self.scroll:
            self.scroll = self.pos
        if self.pos >= self.scroll + width:
            self.scroll = self.pos - width + 1
        put(win, y, x, self.text[self.scroll:self.scroll + width].ljust(width), a)
        self._geom = (y, x, width)
        return (y, x + self.pos - self.scroll) if focus else None

    def hit(self, y, x):
        """Click inside the field moves the cursor there; True if it was inside."""
        if self._geom is None:
            return False
        gy, gx, gw = self._geom
        if y == gy and gx <= x < gx + gw:
            self.pos = min(len(self.text), self.scroll + x - gx)
            return True
        return False


class Dialog:
    """Base modal; draw() returns the cursor position or None."""
    closeOnOutsideClick = False

    def __init__(self, title, on_done=None):
        self.title = title
        self.on_done = on_done
        self.closed = False
        self.result = None
        self.geom = (0, 0, 0, 0)
        self._hits = []

    def close(self, result=None):
        self.closed = True
        self.result = result

    def frame(self, win, want_h, want_w, anchor=None):
        H, W = win.getmaxyx()
        h, w = min(want_h, H - 2), min(want_w, W - 2)
        if anchor is None:
            y, x = (H - h) // 2, (W - w) // 2
        else:
            y, x = max(0, min(anchor[0], H - h - 1)), max(0, min(anchor[1], W - w - 1))
        box(win, y, x, h, w, self.title)
        self.geom = (y, x, h, w)
        self._hits = []
        return y, x, h, w

    def button(self, win, y, x, label, fn):
        """Clickable [ label ]; returns the width used."""
        n = put(win, y, x, f'[ {label} ]', attr('button'))
        self._hits.append((y, x, x + n, fn))
        return n + 1

    def inside(self, y, x):
        gy, gx, gh, gw = self.geom
        return gy <= y < gy + gh and gx <= x < gx + gw

    def mouse(self, kind, y, x):
        """Buttons and outside clicks; subclasses handle their own area first."""
        if kind in ('click', 'double'):
            for hy, x0, x1, fn in self._hits:
                if y == hy and x0 <= x < x1:
                    fn()
                    return True
            if not self.inside(y, x) and self.closeOnOutsideClick:
                self.close(None)
                return True
        return False


class Prompt(Dialog):
    def __init__(self, title, text='', label='', on_done=None, complete_paths=False, hint=''):
        super().__init__(title, on_done)
        self.edit = LineEdit(text, complete_paths)
        self.label = label
        self.hint = hint

    def draw(self, win):
        H, W = win.getmaxyx()
        y, x, h, w = self.frame(win, 7 if self.hint else 6, max(60, min(W - 4, 100)))
        put(win, y + 1, x + 2, self.label, curses.A_BOLD, w - 4)
        if self.hint:
            put(win, y + 4, x + 2, self.hint, attr('dim'), w - 4)
        bx = x + 2
        bx += self.button(win, y + h - 2, bx, 'OK', lambda: self.close(self.edit.text))
        bx += self.button(win, y + h - 2, bx, 'Cancel', lambda: self.close(None))
        tail = ' Enter: OK  Esc: cancel  ^U/^K: clear' + ('  Tab: complete' if self.edit.complete_paths else '')
        put(win, y + h - 2, bx, tail, attr('dim'), x + w - 2 - bx)
        return self.edit.draw(win, y + 2, x + 2, w - 4)

    def key(self, k):
        if k in K_ENTER:
            self.close(self.edit.text)
        elif k == K_ESC:
            self.close(None)
        else:
            self.edit.key(k)

    def mouse(self, kind, y, x):
        if kind == 'click' and self.edit.hit(y, x):
            return True
        return super().mouse(kind, y, x)


class Choose(Dialog):
    """Pick one of options; result is the index. anchor=(y, x) pops it up there (menus)."""
    closeOnOutsideClick = True

    def __init__(self, title, options, current=0, on_done=None, anchor=None, attrs=None):
        super().__init__(title, on_done)
        self.options = [str(o) for o in options]
        self.attrs = attrs or [0] * len(self.options)
        self.sel = max(0, min(current, len(self.options) - 1))
        self.top = 0
        self.anchor = anchor
        self._rows = (0, 0)

    def draw(self, win):
        width = max([len(o) for o in self.options] + [len(self.title) + 4, 26]) + 6
        y, x, h, w = self.frame(win, len(self.options) + 4, width, self.anchor)
        rows = h - 4
        self._rows = (y + 1, rows)
        if self.sel < self.top:
            self.top = self.sel
        if self.sel >= self.top + rows:
            self.top = self.sel - rows + 1
        for i in range(rows):
            j = self.top + i
            if j >= len(self.options):
                break
            a = attr('sel') if j == self.sel else self.attrs[j]
            put(win, y + 1 + i, x + 2, (' ' + self.options[j]).ljust(w - 4), a, w - 4)
        bx = x + 2 + self.button(win, y + h - 2, x + 2, 'Cancel', lambda: self.close(None))
        put(win, y + h - 2, bx, ' Enter/click: select', attr('dim'), x + w - 2 - bx)
        return None

    def key(self, k):
        n = len(self.options)
        if k in K_ENTER:
            self.close(self.sel)
        elif k in (K_ESC, 'q'):
            self.close(None)
        elif k in (curses.KEY_UP, 'k'):
            self.sel = (self.sel - 1) % n
        elif k in (curses.KEY_DOWN, 'j'):
            self.sel = (self.sel + 1) % n
        elif k == curses.KEY_PPAGE:
            self.sel = max(0, self.sel - 10)
        elif k == curses.KEY_NPAGE:
            self.sel = min(n - 1, self.sel + 10)
        elif k == curses.KEY_HOME:
            self.sel = 0
        elif k == curses.KEY_END:
            self.sel = n - 1
        elif is_char(k):
            # jump to the next option starting with the typed character
            for d in range(1, n + 1):
                j = (self.sel + d) % n
                if self.options[j].lower().startswith(k.lower()):
                    self.sel = j
                    break

    def mouse(self, kind, y, x):
        y0, rows = self._rows
        if kind == 'wheelup':
            self.sel = max(0, self.sel - 1)
        elif kind == 'wheeldown':
            self.sel = min(len(self.options) - 1, self.sel + 1)
        elif kind == 'click' and self.inside(y, x) and y0 <= y < y0 + rows:
            j = self.top + y - y0
            if j < len(self.options):
                self.close(j)
        else:
            return super().mouse(kind, y, x)
        return True


class Checklist(Dialog):
    """Toggle booleans; result is the list of states."""
    def __init__(self, title, labels, states, on_done=None):
        super().__init__(title, on_done)
        self.labels = labels
        self.states = list(states)
        self.sel = 0
        self._y0 = 0

    def draw(self, win):
        y, x, h, w = self.frame(win, len(self.labels) + 4, max(max(len(s) for s in self.labels) + 12, 44))
        self._y0 = y + 1
        for i, lab in enumerate(self.labels):
            a = attr('sel') if i == self.sel else 0
            put(win, y + 1 + i, x + 2, f' [{"x" if self.states[i] else " "}] {lab}'.ljust(w - 4), a, w - 4)
        bx = x + 2
        bx += self.button(win, y + h - 2, bx, 'Apply', lambda: self.close(self.states))
        bx += self.button(win, y + h - 2, bx, 'Cancel', lambda: self.close(None))
        put(win, y + h - 2, bx, ' Space/click: toggle', attr('dim'), x + w - 2 - bx)
        return None

    def key(self, k):
        if k in K_ENTER:
            self.close(self.states)
        elif k == K_ESC:
            self.close(None)
        elif k in (curses.KEY_UP, 'k'):
            self.sel = (self.sel - 1) % len(self.labels)
        elif k in (curses.KEY_DOWN, 'j'):
            self.sel = (self.sel + 1) % len(self.labels)
        elif k == ' ':
            self.states[self.sel] = not self.states[self.sel]

    def mouse(self, kind, y, x):
        i = y - self._y0
        if kind == 'click' and self.inside(y, x) and 0 <= i < len(self.labels):
            self.sel = i
            self.states[i] = not self.states[i]
            return True
        return super().mouse(kind, y, x)


class TextView(Dialog):
    """Scrollable text; lines are str or (str, attr). 'y' copies the selected line."""
    closeOnOutsideClick = True

    def __init__(self, title, lines, on_done=None):
        super().__init__(title, on_done)
        self.lines = [ln if isinstance(ln, tuple) else (ln, 0) for ln in lines]
        self.sel = 0
        self.top = 0
        self.hshift = 0
        self._rows = (0, 0)

    def draw(self, win):
        width = max([len(t) for t, _ in self.lines] + [60]) + 4
        y, x, h, w = self.frame(win, len(self.lines) + 4, width)
        rows = h - 4
        self._rows = (y + 1, rows)
        self.sel = max(0, min(self.sel, len(self.lines) - 1))
        if self.sel < self.top:
            self.top = self.sel
        if self.sel >= self.top + rows:
            self.top = self.sel - rows + 1
        for i in range(rows):
            j = self.top + i
            if j >= len(self.lines):
                break
            t, a = self.lines[j]
            if j == self.sel:
                a = attr('sel')
            put(win, y + 1 + i, x + 2, t[self.hshift:].ljust(w - 4), a, w - 4)
        bx = x + 2
        bx += self.button(win, y + h - 2, bx, 'Close', lambda: self.close(True))
        bx += self.button(win, y + h - 2, bx, 'Copy line', self._copy)
        put(win, y + h - 2, bx, f' {self.sel + 1}/{len(self.lines)}  arrows/PgUp/PgDn/wheel  y: copy',
            attr('dim'), x + w - 2 - bx)
        return None

    def _copy(self):
        if self.lines:
            copy_to_clipboard(self.lines[self.sel][0].strip())

    def key(self, k):
        n = len(self.lines)
        if k in K_ENTER or k in (K_ESC, 'q'):
            self.close(True)
        elif k in (curses.KEY_UP, 'k'):
            self.sel = max(0, self.sel - 1)
        elif k in (curses.KEY_DOWN, 'j'):
            self.sel = min(n - 1, self.sel + 1)
        elif k == curses.KEY_PPAGE:
            self.sel = max(0, self.sel - 20)
        elif k == curses.KEY_NPAGE:
            self.sel = min(n - 1, self.sel + 20)
        elif k == curses.KEY_HOME:
            self.sel = 0
        elif k == curses.KEY_END:
            self.sel = n - 1
        elif k == curses.KEY_RIGHT:
            self.hshift += 8
        elif k == curses.KEY_LEFT:
            self.hshift = max(0, self.hshift - 8)
        elif k == 'y':
            self._copy()

    def mouse(self, kind, y, x):
        y0, rows = self._rows
        if kind == 'wheelup':
            self.sel = max(0, self.sel - 3)
        elif kind == 'wheeldown':
            self.sel = min(len(self.lines) - 1, self.sel + 3)
        elif kind == 'click' and self.inside(y, x) and y0 <= y < y0 + rows:
            self.sel = min(len(self.lines) - 1, self.top + y - y0)
        else:
            return super().mouse(kind, y, x)
        return True


class Confirm(Dialog):
    def __init__(self, title, text, on_done=None):
        super().__init__(title, on_done)
        self.text = text

    def draw(self, win):
        y, x, h, w = self.frame(win, 5, max(40, len(self.text) + 6))
        put(win, y + 1, x + 2, self.text, curses.A_BOLD, w - 4)
        bx = x + 2
        bx += self.button(win, y + 3, bx, 'Yes', lambda: self.close(True))
        bx += self.button(win, y + 3, bx, 'No', lambda: self.close(None))
        put(win, y + 3, bx, ' y / n', attr('dim'), x + w - 2 - bx)
        return None

    def key(self, k):
        if k in ('y', 'Y') or k in K_ENTER:
            self.close(True)
        elif k in ('n', 'N', K_ESC, 'q'):
            self.close(None)


class FileBrowser(Dialog):
    """
    Replacement for QFileDialog. save=True edits a file name (pre-filled with
    `suggest`); multi=True lets Space (or a click on the [ ] box) mark several
    files (comma-joined result). Paths are on this machine: the server must
    see the same filesystem.
    """
    def __init__(self, title, patterns=('*',), save=False, suggest='', multi=False,
                 start=None, on_done=None):
        super().__init__(title, on_done)
        self.cwd = os.path.abspath(start or os.getcwd())
        self.patterns = tuple(patterns)
        self.useFilter = self.patterns != ('*',)
        self.save = save
        self.multi = multi
        self.marked = []
        self.name = LineEdit(suggest, complete_paths=True)
        self.focusName = save
        self.sel = 0
        self.top = 0
        self.showHidden = False
        self._rows = (0, 0, 0)
        self._scan()

    def _scan(self):
        try:
            self.entries = scan_dir(self.cwd, self.patterns, self.useFilter, self.showHidden)
            self.err = ''
        except OSError as e:
            self.entries = [Entry('..', True, 0, 0, False)]
            self.err = str(e)
        self.sel = min(self.sel, len(self.entries) - 1)

    def _chdir(self, d):
        self.cwd = os.path.abspath(os.path.join(self.cwd, d))
        self.sel = self.top = 0
        self._scan()

    def _toggle_filter(self):
        self.useFilter = not self.useFilter
        self._scan()

    def _toggle_hidden(self):
        self.showHidden = not self.showHidden
        self._scan()

    def _mark(self, e):
        full = os.path.join(self.cwd, e.name)
        if full in self.marked:
            self.marked.remove(full)
        else:
            self.marked.append(full)

    def draw(self, win):
        H, W = win.getmaxyx()
        y, x, h, w = self.frame(win, H - 4, min(W - 4, 110))
        put(win, y + 1, x + 2, self.cwd, curses.A_BOLD, w - 4)
        flt = ('filter: ' + ' '.join(self.patterns)) if self.useFilter else 'filter: all files'
        put(win, y + 2, x + 2, flt + (f'   marked: {len(self.marked)}' if self.multi else '')
            + (f'   {self.err}' if self.err else ''), attr('err') if self.err else attr('dim'), w - 4)
        rows = h - 7
        self._rows = (y + 3, rows, x + 2)
        if self.sel < self.top:
            self.top = self.sel
        if self.sel >= self.top + rows:
            self.top = self.sel - rows + 1
        infoW = 28
        nameW = max(0, w - 4 - infoW)
        for i in range(rows):
            j = self.top + i
            if j >= len(self.entries):
                break
            e = self.entries[j]
            marked = os.path.join(self.cwd, e.name) in self.marked
            chk = ('[x]' if marked else '[ ]') if (self.multi and not e.isdir) else '   '
            icon = G_CLOSED if e.isdir else ' '
            line = f'{chk} {icon} {e.label}'.ljust(nameW)[:nameW] + e.info().rjust(infoW)
            a = attr('sel') if (j == self.sel and not self.focusName) else e.attr(marked)
            put(win, y + 3 + i, x + 2, line.ljust(w - 4), a, w - 4)
        put(win, y + h - 3, x + 2, 'File: ', curses.A_BOLD)
        cur = self.name.draw(win, y + h - 3, x + 8, w - 10, focus=self.focusName)
        bx = x + 2
        bx += self.button(win, y + h - 2, bx, 'Save' if self.save else 'Open', self.accept)
        bx += self.button(win, y + h - 2, bx, 'Cancel', lambda: self.close(None))
        bx += self.button(win, y + h - 2, bx, 'Up', lambda: self._chdir('..'))
        bx += self.button(win, y + h - 2, bx, 'Home', lambda: self._chdir(os.path.expanduser('~')))
        bx += self.button(win, y + h - 2, bx, 'All files' if self.useFilter else 'Filter', self._toggle_filter)
        bx += self.button(win, y + h - 2, bx, 'Hidden', self._toggle_hidden)
        keys = ' Tab: list/name' + ('  Space: mark' if self.multi else '')
        put(win, y + h - 2, bx, keys, attr('dim'), x + w - 2 - bx)
        return cur

    def _finish(self, path):
        path = os.path.expanduser(path)
        if not os.path.isabs(path):
            path = os.path.join(self.cwd, path)
        if os.path.isdir(path):
            self._chdir(path)
            self.name.text, self.name.pos = '', 0
            return
        self.close(os.path.normpath(path))

    def accept(self):
        """Open/Save button: the name field, else the marked files, else the selected entry."""
        if (self.focusName or self.save) and self.name.text.strip():
            self._finish(self.name.text.strip())
        elif self.multi and self.marked:
            self.close(','.join(self.marked))
        else:
            self._activate(self.entries[self.sel])

    def _activate(self, e):
        if e.isdir:
            self._chdir(e.name)
        elif self.save:
            self.name.text, self.name.pos = e.name, len(e.name)
            self.focusName = True
        elif self.multi and self.marked:
            self.close(','.join(self.marked))
        else:
            self.close(os.path.join(self.cwd, e.name))

    def key(self, k):
        if k == K_ESC:
            self.close(None)
            return
        if k == K_TAB:
            self.focusName = not self.focusName
            return
        if k == 20:  # ^T
            self._toggle_filter()
            return
        if self.focusName:
            if k in K_ENTER:
                if self.name.text.strip():
                    self._finish(self.name.text.strip())
            else:
                self.name.key(k)
            return
        n = len(self.entries)
        e = self.entries[self.sel]
        if k in (curses.KEY_UP, 'k'):
            self.sel = max(0, self.sel - 1)
        elif k in (curses.KEY_DOWN, 'j'):
            self.sel = min(n - 1, self.sel + 1)
        elif k == curses.KEY_PPAGE:
            self.sel = max(0, self.sel - 20)
        elif k == curses.KEY_NPAGE:
            self.sel = min(n - 1, self.sel + 20)
        elif k == curses.KEY_HOME:
            self.sel = 0
        elif k == curses.KEY_END:
            self.sel = n - 1
        elif k == curses.KEY_LEFT or k in K_BACKSPACE:
            self._chdir('..')
        elif k == '~':
            self._chdir(os.path.expanduser('~'))
        elif k == '.':
            self._toggle_hidden()
        elif k == ' ' and self.multi and not e.isdir:
            self._mark(e)
            self.sel = min(n - 1, self.sel + 1)
        elif k == curses.KEY_RIGHT and e.isdir:
            self._chdir(e.name)
        elif k in K_ENTER:
            self._activate(e)

    def mouse(self, kind, y, x):
        y0, rows, x0 = self._rows
        j = self.top + y - y0
        inList = self.inside(y, x) and y0 <= y < y0 + rows and 0 <= j < len(self.entries)
        if kind == 'wheelup':
            self.sel = max(0, self.sel - 3)
        elif kind == 'wheeldown':
            self.sel = min(len(self.entries) - 1, self.sel + 3)
        elif kind in ('click', 'double') and inList:
            self.focusName = False
            e = self.entries[j]
            if self.multi and not e.isdir and x < x0 + 3:
                self._mark(e)               # click on the [ ] box
                self.sel = j
            elif kind == 'double' or (e.isdir and j == self.sel):
                self.sel = j
                self._activate(e)
            else:
                self.sel = j
        elif kind == 'click' and self.name.hit(y, x):
            self.focusName = True
        else:
            return super().mouse(kind, y, x)
        return True
