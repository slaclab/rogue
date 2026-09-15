#!/usr/bin/env python3
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

# Exercises the command line and startup code of the embedded IPython console.
# This half imports no Qt on purpose, so these tests run in CI environments that
# have no Qt binding and no display. The end of the file spawns a real console on
# a pseudo-terminal, which is what pins the '-i -c' behaviour the whole design
# rests on: that the startup code runs and the session then stays alive with what
# it defined still in scope.

import ast
import importlib.util
import os
import select
import sys
import time
from pathlib import Path

import pytest

posixOnly = pytest.mark.skipif(os.name != 'posix', reason="pseudo-terminals are POSIX only")


def _loadByPath(name, relative):
    """Load a widget module without importing the Qt-dependent widget package.

    ``pyrogue.pydm.widgets.__init__`` imports every widget, so the ordinary
    import path drags in pydm and a Qt binding even for modules that need
    neither.
    """
    path = Path(__file__).resolve().parents[2] / relative
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


ic = _loadByPath("rogue_test_ipython_core", "python/pyrogue/pydm/widgets/ipython_core.py")
tc = _loadByPath("rogue_test_terminal_core", "python/pyrogue/pydm/widgets/terminal_core.py")


def _drain(fd, seconds=1.0):
    """Read from a non-blocking descriptor for a bounded time."""
    out = b''
    end = time.monotonic() + seconds

    while time.monotonic() < end:
        ready, _, _ = select.select([fd], [], [], 0.05)
        if not ready:
            continue
        try:
            chunk = os.read(fd, 4096)
        except BlockingIOError:
            continue
        except OSError:
            break
        if not chunk:
            break
        out += chunk

    return out


# ---------------------------------------------------------------------------
# Startup code
# ---------------------------------------------------------------------------

def test_startup_code_connects_a_client():
    code = ic.startupCode('localhost', 9099)
    assert 'pr.interfaces.VirtualClient' in code
    assert "addr='localhost'" in code
    assert 'port=9099' in code


def test_startup_code_imports_the_interfaces_submodule():
    # 'import pyrogue as pr' does not bind pr.interfaces. Without the submodule
    # import the client construction raises AttributeError, which the guard below
    # it then reports as a connection failure: the console looks like it merely
    # could not reach the server, on every server.
    assert 'import pyrogue.interfaces' in ic.startupCode('localhost', 9099)


def test_startup_code_binds_the_conventional_names():
    # 'client' and 'root' are what the server suggests at startup and what the
    # notebooks and docs use, so a session must land on the same names.
    code = ic.startupCode('localhost', 9099)
    assert 'client = ' in code
    assert 'root = client.root' in code


def test_startup_code_carries_the_requested_server():
    code = ic.startupCode('rogue-host.example', 12345)
    assert "addr='rogue-host.example'" in code
    assert 'port=12345' in code
    assert 'localhost' not in code


def test_startup_code_survives_a_connection_failure():
    # Without this the console would come up dead: the exception from a missing
    # server would leave no prompt worth having.
    code = ic.startupCode('localhost', 9099)
    assert 'except Exception' in code
    assert 'Retry with' in code


def test_startup_code_is_valid_python():
    compile(ic.startupCode('localhost', 9099), '<startup>', 'exec')


def test_startup_code_quotes_the_address():
    # Every interpolation of the address goes through repr(), so an address can
    # neither terminate the literal it sits in nor smuggle in a statement.
    code = ic.startupCode("host'; import os", 9099)
    tree = ast.parse(code)
    imported = [alias.name
                for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))
                for alias in node.names]
    assert imported == ['pyrogue', 'pyrogue.interfaces']


# ---------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------

def test_argv_runs_ipython_on_the_gui_interpreter():
    # An 'ipython' from PATH could belong to another interpreter, which would
    # import a different pyrogue, or none, and would miss the PYTHONPATH of a
    # local build.
    argv = ic.ipythonArgv('localhost', 9099)
    assert argv[0] == sys.executable
    assert argv[1:3] == ['-m', 'IPython']


def test_argv_stays_interactive_after_the_startup_code():
    argv = ic.ipythonArgv('localhost', 9099)
    assert '-i' in argv
    assert argv[-2] == '-c'
    assert argv[-1] == ic.startupCode('localhost', 9099)


def test_argv_does_not_ask_to_confirm_exit():
    # Exiting is how the session is restarted, so a confirmation would be in the
    # way rather than a safeguard.
    assert '--no-confirm-exit' in ic.ipythonArgv('localhost', 9099)


def test_argv_turns_jedi_off():
    # jedi cannot complete the tree. Its static analysis crashes on the dynamic
    # __getattr__ nodes, and IPython then offers the crash text as the only
    # candidate, so Tab does nothing after 'root.'. IPython's own completer works
    # from dir(), which the tree answers.
    assert '--IPCompleter.use_jedi=False' in ic.ipythonArgv('localhost', 9099)


def test_argv_accepts_an_explicit_interpreter():
    argv = ic.ipythonArgv('localhost', 9099, executable='/usr/bin/python3')
    assert argv[0] == '/usr/bin/python3'


def test_startup_code_is_a_single_argument():
    # It reaches the child through '/bin/sh -c ... "$@"', so a multi-line string
    # has to stay one argv element rather than being split into words.
    argv = ic.ipythonArgv('localhost', 9099)
    assert len([a for a in argv if 'VirtualClient' in a]) == 1
    assert '\n' in argv[-1]


# ---------------------------------------------------------------------------
# Real console on a pseudo-terminal
# ---------------------------------------------------------------------------

@posixOnly
@pytest.mark.skipif(importlib.util.find_spec('IPython') is None, reason="IPython is not installed")
def test_console_reaches_a_prompt_with_no_server():
    # No Rogue server is running, so this also covers the failure path: the
    # startup code must report the problem and still hand over a live session.
    argv = ic.ipythonArgv('localhost', 9099)
    proc, master = tc.spawnShell(30, 100, argv=argv)

    try:
        out = _drain(master, 25.0).decode(errors='replace')
        assert 'In [' in out, f"no IPython prompt in output: {out[-400:]!r}"
        assert 'Rogue console' in out, f"startup code did not run: {out[-400:]!r}"

        # The session is alive and everything needed to build a client resolves.
        # Asserting on the class rather than on the connection means this fails
        # for a missing import even though no server is present to connect to.
        os.write(master, b'print("PROBE", pr.interfaces.VirtualClient.__name__)\r')
        typed = _drain(master, 15.0).decode(errors='replace')
        assert 'PROBE VirtualClient' in typed, f"names did not resolve: {typed[-400:]!r}"
    finally:
        tc.closeShell(proc, master)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
