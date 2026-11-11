#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

# The TUI command line, driven without a terminal: shorthand syntax, verbs,
# error reporting and Tab completion against a served tree.

import pyrogue.interfaces as pr_interfaces
import pytest

from pyrogue.tui.console import Console
from pyrogue.tui.model import Session

from tui_support import TuiRoot

pytestmark = pytest.mark.integration


class _View:
    srv = 0


class _App:
    """The parts of the TUI App the console uses."""

    def __init__(self, session):
        self.session = session
        self.tabSpecs = [('Debug Tree', ('tree', 'rogue://0/root'))]
        self.cur = 0

    def view(self):
        return _View()


@pytest.fixture
def console(free_zmq_port):
    pr_interfaces.VirtualClient.ClientCache.clear()
    with TuiRoot(port=free_zmq_port) as root:
        session = Session(f'127.0.0.1:{root.zmqServer.port()}')
        try:
            yield root, Console(_App(session))
        finally:
            session.stop()


def _text(con):
    return [text for _, _, text in con.lines]


def _wait_line(con, wait_until, needle):
    return wait_until(lambda: any(needle in t for t in _text(con)), timeout=5.0)


def test_shorthand_set_get_and_exec(console, wait_until):
    root, con = console
    con.run('Dev.Value = 4')
    assert wait_until(lambda: root.Dev.Value.get() == 4, timeout=5.0)

    con.run('Dev.Value')
    assert _wait_line(con, wait_until, 'Top.Dev.Value = 4')

    con.run('Dev.Multiply(3)')
    assert _wait_line(con, wait_until, '-> 9')

    con.run('Dev.Mode = Run')
    assert wait_until(lambda: root.Dev.Mode.getDisp() == 'Run', timeout=5.0)


def test_verbs_and_python(console, wait_until):
    root, con = console
    con.run('set root.Dev.Value 11')
    assert wait_until(lambda: root.Dev.Value.get() == 11, timeout=5.0)

    con.run('ls Dev')
    assert _wait_line(con, wait_until, 'Multiply')

    con.run('py root.Dev.Value.get() + 1')
    assert _wait_line(con, wait_until, '12')


def test_errors_are_reported_not_raised(console, wait_until):
    _, con = console
    con.run('Dev.Missing')
    assert _wait_line(con, wait_until, 'no node Dev.Missing')

    con.run('Dev.Value()')
    assert _wait_line(con, wait_until, 'is not a command')

    con.run('Dev.Value = notanumber')
    assert wait_until(lambda: any(k == 'err' for _, k, _ in con.lines), timeout=5.0)


def test_tab_completion(console):
    _, con = console
    con.edit.text, con.edit.pos = 'Dev.Mu', len('Dev.Mu')
    con.complete()
    assert con.edit.text == 'Dev.Multiply'

    con.edit.text, con.edit.pos = 'le', 2
    con.complete()
    assert con.edit.text == 'le'          # no command or node starts with it

    con.edit.text, con.edit.pos = 'De', 2
    con.complete()
    assert con.edit.text == 'Dev.'        # a device completes with its dot

    con.edit.text, con.edit.pos = 'Dev.', 4
    con.complete()
    listed = _text(con)[-1]
    assert 'Value' in listed and 'Secret' not in listed   # Hidden stays hidden
