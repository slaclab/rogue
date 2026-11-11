#-----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
#-----------------------------------------------------------------------------
#  Description:
#       PyRogue TUI: text output shared by the console
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
Text output shared by the one-shot sub-commands and the TUI console.
"""
import json
import time


def tree_lines(session, srv, node, depth=1, offset=False, full=False):
    """Device listing with mode/type/[offset]/value, `depth` levels down (-1: all)."""
    rows = []

    def walk(n, indent, level):
        m = session.meta(srv, n)
        if m.isDevice:
            rows.append(('  ' * indent + n.name + '/', '', '', m.offsetStr(), ''))
            if depth >= 0 and level >= depth:
                return
            variables, devices = session.children(srv, n)
            for c in variables + devices:
                walk(c, indent + 1, level + 1)
        else:
            if m.isCommand:
                val = '[cmd' + (f' arg={session.disp(srv, m.path)}]' if m.arg else ']')
            else:
                val = session.disp(srv, m.path) + (f' {m.units}' if m.units else '')
                if len(val) > 100 and not full:
                    val = val[:97] + '...'
            rows.append(('  ' * indent + n.name, m.mode, m.typeStr, m.offsetStr(), val))
    walk(node, 0, 0)
    w = [max(len(r[i]) for r in rows) for i in range(4)]
    out = []
    for r in rows:
        cols = [r[0].ljust(w[0]), r[1].ljust(max(w[1], 2)), r[2].ljust(w[2])]
        if offset:
            cols.append(r[3].ljust(w[3]))
        out.append('  '.join(cols + [r[4]]).rstrip())
    return out


def log_lines(root, n=20, verbose=False):
    """System Log entries as text, oldest first."""
    ents = json.loads(root.SystemLog.get(read=False) or '[]')
    if n:
        ents = ents[-n:]
    out = []
    for e in ents:
        st = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(e.get('created', 0)))
        out.append(f"{st} {e.get('levelName', ''):8s} {e.get('name', '')}: {e.get('message', '')}")
        if verbose:
            for k in ('rogueComponent', 'rogueLogger', 'rogueTid', 'roguePid'):
                if e.get(k) is not None:
                    out.append(f'    {k}: {e[k]}')
            if e.get('exception') is not None:
                out.append(f"    exception: {e['exception']}")
                for tb in e.get('traceBack') or []:
                    out += ['    ' + ln for ln in tb.rstrip().splitlines()]
    return out or ['(System Log empty)']
