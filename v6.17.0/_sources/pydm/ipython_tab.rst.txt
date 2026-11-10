.. _ipython_tab:

=========================
The IPython Console Tab
=========================

The stock debug GUI can show an interactive IPython session in its own top-level
tab, with a Rogue client already connected. When enabled, an ``IPython`` tab
appears alongside ``System`` and ``Debug Tree``. It is added last, so the existing
tab positions do not change, and ``Debug Tree`` remains the tab shown on startup.

This is the session the Rogue server suggests when it starts::

    To use a virtual client: client = pyrogue.interfaces.VirtualClient(addr='localhost', port=9099)

opened for you rather than typed out. It is useful whenever a task is easier to
express as a line of Python than as a sequence of clicks: reading a whole device
at once, looping over channels, computing a value from several variables, or
scripting a bring-up step while watching the ``Debug Tree`` update next to it.

The feature is off by default, and independent of the ``Terminal`` tab. Either
can be enabled without the other.

What Is Already Connected
=========================

The session starts with two names bound:

===============  ==============================================================
Name             Value
===============  ==============================================================
``client``       A connected ``pyrogue.interfaces.VirtualClient``
``root``         ``client.root``, the top of the tree
``pr``           ``pyrogue``, for everything else
===============  ==============================================================

So the tree is reachable immediately:

.. code-block:: python

   In [1]: root.LocalTime.get()
   In [2]: [v.get() for v in root.AxiVersion.variables.values()]

The client connects to the same server the rest of the GUI is using, taken from
the first entry of ``ROGUE_SERVERS``, which is what ``--server`` and the
``serverList`` argument set. The detached window title names that server, so a
console is never ambiguous about which system it is driving.

It is a separate client in a separate process, not the one the GUI's own displays
share. A session that is stopped, wedged, or exited therefore cannot take the
GUI's channels down with it. If the server is not reachable the console says so
and still hands over a prompt, along with the line to retry with once it is up.

Where It Runs
=============

.. warning::

   The console runs **on the machine displaying the GUI, as the user who launched
   the GUI**. It is not a session on the Rogue server. It reaches the tree the
   same way any other client does, over ZMQ.

The distinction matters for everything that is not tree access. ``os``,
``subprocess``, file paths, and ``!command`` all act on the machine showing the
GUI, which is frequently not the DAQ host.

Enabling It
===========

From the command line:

.. code-block:: bash

   $ python -m pyrogue gui --server localhost:9099 --ipython

From a launcher script:

.. code-block:: python

   import pyrogue.pydm

   pyrogue.pydm.runPyDM(serverList='localhost:9099', enableIPython=True)

Both tabs together:

.. code-block:: bash

   $ python -m pyrogue gui --server localhost:9099 --terminal --ipython

The console can also be placed in a custom screen. It takes the same kind of
channel as the other Rogue widgets, and uses it only to decide which server to
connect to:

.. code-block:: python

   from pyrogue.pydm.widgets import IPythonPanel

   panel = IPythonPanel(parent=None)                                   # rogue://0/root
   other = IPythonPanel(parent=None, init_channel='rogue://host:9099/root')

The detach button only acts when the panel is a page of a ``QTabWidget``, since
that is where it returns to. Elsewhere it does nothing rather than stranding the
console in a window it cannot come back from.

When The Session Starts
=======================

IPython starts the first time the tab is actually displayed, not when the GUI is
built. Two consequences follow:

- Enabling the feature costs nothing until someone opens the tab. No process
  exists and no connection is attempted before that.
- The connection attempt, which can take a few seconds against an absent server,
  never delays the GUI coming up.

Exiting, with ``exit`` or Ctrl-D, immediately starts a fresh session that
reconnects, as if the tab had just been opened for the first time. Ctrl-D is easy
to press by accident, and there is no reason for it to leave a dead tab that can
only be recovered by restarting the GUI. Note that a fresh session starts with a
fresh namespace: anything defined at the prompt is gone.

If a session exits without anything having been typed then it never started at
all, for example because IPython is not installed. After a few of those in a row
the tab stops retrying and says so, rather than spawning processes in a loop.

Security Considerations
=======================

Anyone who can reach the GUI window can execute arbitrary Python, and therefore
arbitrary code, with the privileges of the account running the GUI. The
considerations are the same as for :doc:`terminal_tab`, and for the same reasons:

- **This includes a shell.** ``!command`` and ``subprocess`` are ordinary IPython
  and Python features. Treat the console as equivalent to the terminal tab, not
  as something narrower because it is a Python prompt.
- **PyDM read-only mode does not constrain it.** ``PYDM_READ_ONLY`` gates channel
  writes. A read-only PyDM session with the console enabled is still fully
  writable, both through the shell and through ``root``.
- **Privileges are inherited.** If the GUI is launched with elevated rights for
  hardware access, the console gets them too. Do not enable it when the GUI runs
  as ``root`` or under a shared, kiosk, or service account.
- **A shared display is a shared session.** On a display reachable through X11
  forwarding or an unauthenticated VNC session, anyone who can see the window can
  use the console.
- **There is no audit trail.** IPython history goes to the launching user's normal
  history database, and the Rogue ``SystemLog`` records nothing about console
  activity. Sites needing accountability must use host-level auditing.

Because enabling the console requires editing the launching command or script, it
is always a deliberate act by someone who can already run arbitrary code in that
process. The option does not widen anyone's privileges; it changes who can
conveniently reach a prompt.

Detaching Into Its Own Window
=============================

The ``Detach`` button above the console moves it into a separate window, which
can be sized and positioned independently or moved to another monitor. That makes
a long session or a wide table of values readable without resizing the whole GUI,
and it allows the console and the ``Debug Tree`` to be watched side by side. The
button becomes ``Reattach`` to put it back in its original tab position.

Detaching does not disturb the session. The interpreter is held by a file
descriptor, not by a window, so the same session keeps running with its namespace,
history, and scrollback intact. Closing the detached window reattaches the console
rather than destroying it, and the detached window stays owned by the GUI, so
closing the GUI closes it too.

Appearance And Limitations
==========================

The console is the terminal widget of :doc:`terminal_tab` running IPython instead
of a shell, so its rendering, dark theme, 2000 line scrollback, color support and
key bindings are exactly as documented there, including ``Ctrl+Shift+C`` and
``Ctrl+Shift+V`` for the clipboard so that ``Ctrl-C`` can interrupt.

What that inherits, in practice:

- Syntax highlighting, tab completion, history search, ``%magics``, and
  multi-line editing all work, because they are terminal features of IPython.
- Completion is IPython's own, from ``dir()``, with jedi turned off. That is what
  makes ``root.<TAB>`` work at all: the tree resolves its children through
  ``__getattr__``, which jedi's static analysis cannot follow and in practice
  crashes on, leaving Tab doing nothing. What is given up is jedi's type
  inference on ordinary Python, mostly completions on expressions that were
  never assigned to a name.
- Completion listings and the ``?`` pager render as they do in a terminal, not as
  popups.
- Rich output does not. There is no inline plotting and no HTML rendering, since
  the view is a text screen. ``%matplotlib`` opens a separate window, as it does
  from a terminal IPython.
- Linux and macOS only. The implementation uses pseudo-terminals, which have no
  Windows equivalent.

IPython itself must be installed. It is part of the ``gui`` extra and of the conda
environment, so this is normally already true.

What To Explore Next
====================

- :doc:`terminal_tab` for the shell tab and the rendering both tabs share
- :doc:`starting_gui` for the other runtime options of the stock GUI
- :doc:`/pyrogue_tree/client_interfaces/virtual` for what ``client`` can do

API Reference
=============

- :doc:`/api/python/pyrogue/pydm_widgets/ipythonpanel`
- :doc:`/api/python/pyrogue/pydm_runpydm`
