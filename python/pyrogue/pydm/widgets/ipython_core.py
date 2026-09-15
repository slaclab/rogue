from __future__ import annotations

#-----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
#-----------------------------------------------------------------------------
#  Description:
#       PyRogue PyDM Embedded IPython Console Startup Support
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

# This module deliberately imports no Qt. It builds the command line that starts
# the console and the code that runs inside it before the user gets the prompt,
# so both stay testable in a CI environment with no Qt binding.

import sys


def startupCode(addr: str, port: int) -> str:
    """Return the code IPython runs before handing over the prompt.

    Connects a :class:`pyrogue.interfaces.VirtualClient` and leaves it bound as
    ``client``, with the tree root as ``root``, which is the naming the Rogue
    server itself suggests when it starts and the one the notebooks and docs use.

    A failure to connect is caught rather than left to propagate. The console is
    still useful without a link, and the user gets the exact line to retry with
    once the server is up. ``VirtualClient`` prints its own connection banner, so
    the success path only names what is now in scope.

    Parameters
    ----------
    addr : str
        Rogue server host name or address.
    port : int
        Rogue server base ZMQ port.

    Returns
    -------
    str
        Python source, passed to IPython as a single ``-c`` argument.
    """
    # The address is only ever interpolated through repr(): into the call as a
    # literal, and into the messages as whole pre-built strings. Interpolating it
    # into a quoted message directly would collide with its own quoting.
    connect = f"pr.interfaces.VirtualClient(addr={addr!r}, port={port})"
    ready = "Rogue console: 'client' and 'root' are ready"
    failed = f"Rogue console: cannot reach {addr}:{port}: "
    retry = f"Retry with: client = {connect}"

    return (
        "import pyrogue as pr\n"
        # Importing the package alone does not bind the interfaces submodule, so
        # without this the client construction fails with an AttributeError.
        "import pyrogue.interfaces\n"
        "\n"
        "try:\n"
        f"    client = {connect}\n"
        "    root = client.root\n"
        f"    print({ready!r})\n"
        "except Exception as exc:\n"
        f"    print({failed!r} + str(exc))\n"
        f"    print({retry!r})\n"
    )


def ipythonArgv(addr: str, port: int, executable: str | None = None) -> list[str]:
    """Return the argv that starts IPython with the client already connected.

    Started as ``-m IPython`` on the interpreter running the GUI rather than
    through an ``ipython`` found on ``PATH``. A console that runs on a different
    interpreter would import a different, or no, ``pyrogue``, and would not see
    the ``PYTHONPATH`` of a local Rogue build.

    ``-i`` is what keeps the session alive after the ``-c`` code has run, so the
    connected client stays in the namespace the user types into.

    Parameters
    ----------
    addr : str
        Rogue server host name or address.
    port : int
        Rogue server base ZMQ port.
    executable : str | None, optional
        Interpreter to run. Defaults to the running interpreter.

    Returns
    -------
    list[str]
        Argument vector suitable for
        :func:`pyrogue.pydm.widgets.terminal_core.spawnShell`.
    """
    return [
        executable or sys.executable,
        '-m', 'IPython',
        # Exiting is how the session is restarted, so a confirmation prompt would
        # only be in the way.
        '--no-confirm-exit',
        # Completing on the tree is the reason the console exists, and jedi
        # cannot do it: its static analysis crashes on the dynamic __getattr__
        # nodes with "'TreeInstance' object has no attribute 'with_generics'",
        # and IPython then offers that crash text as the only candidate, so Tab
        # appears to do nothing after `root.`. IPython's own completer works
        # from dir(), which the tree answers correctly. Even without the crash
        # jedi would refuse to resolve attributes it has to call __getattr__
        # for, so this is not a workaround for one broken version.
        '--IPCompleter.use_jedi=False',
        '-i',
        '-c', startupCode(addr, port),
    ]
