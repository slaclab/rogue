#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

# The TUI's client-side state: path resolution, the live value cache fed by
# the ZMQ publisher, DebugTree group filtering and worker error reporting.
# None of it touches curses, so it runs without a terminal.

import pyrogue.interfaces as pr_interfaces
import pytest

from pyrogue.tui.model import Session, parse_channel
from tui_support import TuiRoot

pytestmark = pytest.mark.integration


@pytest.fixture
def served(free_zmq_port):
    pr_interfaces.VirtualClient.ClientCache.clear()
    with TuiRoot(port=free_zmq_port) as root:
        session = Session(f'127.0.0.1:{root.zmqServer.port()}')
        try:
            yield root, session
        finally:
            session.stop()


def test_parse_channel_defaults_to_first_server():
    assert parse_channel('rogue://1/root.Dev.Value') == (1, 'root.Dev.Value')
    assert parse_channel('Dev.Value') == (0, 'Dev.Value')


def test_node_accepts_root_alias_and_relative_paths(served):
    _, session = served
    for path in ('root.Dev.Value', 'Top.Dev.Value', 'Dev.Value'):
        assert session.node(0, path).path == 'Top.Dev.Value'
    with pytest.raises(KeyError):
        session.node(0, 'Dev.Missing')


def test_value_cache_follows_server_updates_through_root_alias(served, wait_until):
    # Listener updates arrive under the real root name; a value first read
    # through the 'root.' alias must still be refreshed by them.
    root, session = served
    assert session.disp(0, 'root.Dev.Value') == '1'
    root.Dev.Value.set(7)
    assert wait_until(lambda: session.disp(0, 'root.Dev.Value') == '7', timeout=5.0)


def test_children_follow_debugtree_group_filter(served):
    _, session = served
    dev = session.node(0, 'Dev')
    variables, _ = session.children(0, dev)
    names = {n.name for n in variables}
    assert {'Value', 'Mode', 'Bias0', 'Multiply'} <= names
    assert 'Secret' not in names

    session.excGroups = None
    variables, _ = session.children(0, dev)
    assert 'Secret' in {n.name for n in variables}


def test_meta_exposes_widget_choice(served):
    _, session = served
    mode = session.meta(0, session.node(0, 'Dev.Mode'))
    assert mode.isEnum and mode.writable
    cmd = session.meta(0, session.node(0, 'Dev.Multiply'))
    assert cmd.isCommand and cmd.arg


def test_worker_reports_success_and_failure(served, wait_until):
    _, session = served

    def boom():
        raise RuntimeError('expected failure')

    session.submit('good', lambda: 42)
    session.submit('bad', boom)
    assert wait_until(lambda: len(session.messages) >= 2 and not session.busy, timeout=5.0)
    levels = {text.split(':')[0]: level for _, level, text in session.messages}
    assert levels['good'] == 'ok'
    assert levels['bad'] == 'error'
