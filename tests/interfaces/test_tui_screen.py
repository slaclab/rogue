#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

# End-to-end: `python -m pyrogue tui` runs in a pseudo-terminal against a
# served tree, and pyte reconstructs the screen it draws. This covers what the
# headless tests cannot: curses start-up on a duplicated terminal descriptor,
# the tab layout, the console command line and a clean exit.

import fcntl
import os
import select
import struct
import subprocess
import sys
import termios
import time

import pyrogue.interfaces as pr_interfaces
import pytest

try:
    import pyte
except Exception as exc:
    pytest.skip(f"pyte unavailable: {exc}", allow_module_level=True)

from tui_support import TuiRoot

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(os.name != 'posix', reason="pseudo-terminals are POSIX only"),
]

COLS, ROWS = 120, 40


class Tty:
    """A child process on a pseudo-terminal, with a pyte screen of its output."""

    def __init__(self, args):
        self.screen = pyte.Screen(COLS, ROWS)
        self.stream = pyte.ByteStream(self.screen)
        self.master, slave = os.openpty()
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', ROWS, COLS, 0, 0))
        env = dict(os.environ, TERM='xterm-256color', LANG='C.UTF-8', LC_ALL='C.UTF-8')
        self.proc = subprocess.Popen(args, stdin=slave, stdout=slave, stderr=slave,
                                     env=env, start_new_session=True, close_fds=True)
        os.close(slave)

    def pump(self, seconds=0.1):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            r, _, _ = select.select([self.master], [], [], 0.05)
            if r:
                try:
                    self.stream.feed(os.read(self.master, 65536))
                except OSError:   # child closed the terminal
                    return

    def text(self):
        return '\n'.join(self.screen.display)

    def wait_for(self, needle, timeout=30.0):
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            self.pump()
            if needle in self.text():
                return True
        return False

    def send(self, data):
        os.write(self.master, data.encode())
        self.pump(0.3)

    def close(self):
        if self.proc.poll() is None:
            self.proc.kill()
            self.proc.wait(timeout=10)
        os.close(self.master)


@pytest.fixture
def tui(free_zmq_port):
    pr_interfaces.VirtualClient.ClientCache.clear()
    with TuiRoot(port=free_zmq_port) as root:
        server = f'127.0.0.1:{root.zmqServer.port()}'
        tty = Tty([sys.executable, '-m', 'pyrogue', f'--server={server}', 'tui', '--no-mouse'])
        try:
            yield root, tty
        finally:
            tty.close()


def test_tui_draws_tree_runs_console_and_exits(tui, wait_until):
    root, tty = tui
    assert tty.wait_for('Read All'), tty.text()
    assert 'Dev' in tty.text() and 'Debug Tree' in tty.text()

    tty.send(':')
    tty.send('Dev.Value = 9\r')
    assert wait_until(lambda: root.Dev.Value.get() == 9, timeout=10.0)

    tty.send('Dev.Value\r')
    assert tty.wait_for('Top.Dev.Value = 9', timeout=10.0), tty.text()

    tty.send('\x1b')              # leave the command line
    tty.send('1')                 # System tab
    assert tty.wait_for('Reset And Configuration', timeout=10.0), tty.text()

    tty.send('q')
    tty.send('y')
    assert tty.proc.wait(timeout=20) == 0
