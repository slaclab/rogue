.. _terminal_tab:

==========================
The Embedded Terminal Tab
==========================

The stock debug GUI can show an interactive shell in its own top-level tab. When
enabled, a ``Terminal`` tab appears alongside ``System`` and ``Debug Tree``. It
is added last, so the existing tab positions do not change, and ``Debug Tree``
remains the tab shown on startup.

Giving the terminal a top-level tab means it gets the full height of the window,
which keeps it readable even in a small window.

This is useful during bring-up and debugging, when checking ``dmesg``, tailing a
file, inspecting ``/proc``, or restarting a service would otherwise mean leaving
the GUI to find a separate terminal.

The feature is off by default. Nothing changes for an existing GUI unless it is
explicitly turned on.

Where The Shell Runs
====================

.. warning::

   The shell runs **on the machine displaying the GUI, as the user who launched
   the GUI**. It is not a shell on the Rogue server.

This matters because the GUI is frequently a remote client: ``runPyDM`` connects
to ``serverList`` over ZMQ, so the GUI and the ``Root`` often live on different
machines. Running a destructive command in the terminal believing you are on the
DAQ host is the realistic accident this warning is here to prevent. Run
``hostname`` in the terminal if there is any doubt.

Enabling It
===========

From the command line:

.. code-block:: bash

   $ python -m pyrogue gui --server localhost:9099 --terminal

From a launcher script:

.. code-block:: python

   import pyrogue.pydm

   pyrogue.pydm.runPyDM(serverList='localhost:9099', enableTerminal=True)

The terminal can also be placed in a custom screen. Neither widget takes a
channel or any arguments. Use ``TerminalPanel`` to get the detach button, or
``LinuxTerminal`` for just the terminal with no surrounding controls:

.. code-block:: python

   from pyrogue.pydm.widgets import LinuxTerminal, TerminalPanel

   panel = TerminalPanel(parent=None)     # terminal plus the detach button
   term = LinuxTerminal(parent=None)      # terminal on its own

The detach button only acts when the panel is a page of a ``QTabWidget``, since
that is where it returns to. Elsewhere it does nothing rather than stranding the
terminal in a window it cannot come back from.

When The Shell Starts
=====================

Exiting the shell, with ``exit`` or Ctrl-D, immediately starts a fresh session in
a clean state, as if the GUI had just been opened. Ctrl-D is easy to press by
accident, and there is no reason for it to leave a dead terminal that can only be
recovered by restarting the GUI.

If a shell exits without the user having typed anything then it never started at
all, for example because ``$SHELL`` is not runnable. After a few of those in a
row the terminal stops retrying and says so, rather than spawning processes in a
loop.

The shell starts the first time the tab is actually displayed, not when the GUI
is built. Two consequences follow:

- Enabling the feature costs nothing until someone opens the tab. No shell
  process exists before that.
- The terminal needs no Rogue channel, so unlike the other tabs it still works
  while the Rogue link is down, which is exactly when a shell tends to be most
  useful.

Security Considerations
=======================

Anyone who can reach the GUI window gets an interactive shell with the
privileges of the account running the GUI. Before enabling it, consider:

- **PyDM read-only mode does not constrain it.** ``PYDM_READ_ONLY`` gates
  channel writes. A read-only PyDM session with the terminal enabled is still
  fully writable through the shell.
- **Privileges are inherited.** If the GUI is launched with elevated rights for
  hardware access, the shell gets them too. Do not enable the terminal when the
  GUI runs as ``root`` or under a shared, kiosk, or service account.
- **A shared display is a shared shell.** On a display reachable through X11
  forwarding or an unauthenticated VNC session, anyone who can see the window
  can use the shell.
- **There is no audit trail.** Shell history goes to the launching user's normal
  history file, and the Rogue ``SystemLog`` records nothing about terminal
  activity. Sites needing accountability must use host-level auditing.

Because enabling the terminal requires editing the launching command or script,
it is always a deliberate act by someone who can already run arbitrary code in
that process. The option does not widen anyone's privileges; it changes who can
conveniently reach a shell.

Detaching Into Its Own Window
=============================

A tab is only as tall as the window it lives in. The ``Detach`` button above the
terminal moves it into a separate window, which can be sized and positioned
independently or moved to another monitor. That makes a long build log or a full
screen program readable without resizing the whole GUI. The button becomes
``Reattach`` to put it back in its original tab position.

Detaching does not disturb the shell. The child process is held by a file
descriptor, not by a window, so the same shell keeps running with its working
directory, command history, and scrollback intact.

Two details worth knowing:

- Closing the detached window reattaches the terminal rather than destroying it,
  so there is no way to lose a running shell by closing the wrong window.
- The detached window stays owned by the GUI, so closing the GUI closes it too
  and the process exits normally.

Appearance And Scrollback
=========================

The view is dark themed and uses the platform's fixed-pitch font. It keeps
2000 lines of scrollback above the live screen, with a scrollbar on the right.

The emulated screen is a fixed grid that exactly fills the view, so it behaves
like any other terminal. Once enough output has accumulated the prompt sits on
the bottom row and output scrolls up past it. Immediately after starting, or
after ``clear``, the prompt is at the top with blank space beneath it, because
the screen genuinely is empty at that point.

``clear`` blanks the view as expected. Earlier output is not destroyed, it moves
into the scrollback and can still be reached by scrolling up.

Color
=====

Colored output is rendered, so ``ls``, ``grep --color``, ``git``, and compiler
diagnostics look the way they do in any other terminal. The full range is
supported: the sixteen named colors, 256 color, and 24 bit true color, along with
bold, italic, underline, strikethrough, and reverse video. Colors are kept when a
line scrolls into the scrollback.

Bold combined with a color is rendered in the bright shade of that color, which
is the convention colorizing tools assume. Blink is deliberately ignored.

The palette comes from the standard xterm colors, so it matches what other
terminals show for the same escape sequences.

Scrolling behaves the way a terminal should: while you are scrolled up the view
stays where you left it, so a burst of output will not yank you back. Once the
view is at the bottom again it resumes following new output. Select with the
mouse and copy with ``Ctrl+Shift+C``.

The scrollback bound is what keeps a terminal left open for days from growing
without limit. Oldest lines are dropped once it is reached.

Current Limitations
===================

The terminal emulates a VT-style screen with `pyte
<https://pypi.org/project/pyte/>`_ and renders it into a plain Qt text view.
Interactive shells, job control, scrollback, and full-screen programs work. The
following are not implemented:

- **No alternate screen buffer.** Programs such as ``vim`` and ``htop`` run and
  respond normally, but on exit they leave their last frame on screen instead of
  restoring what was there before. Press Enter to get a fresh prompt.
- **No mouse reporting.** Mouse-driven full-screen programs are keyboard-only.
  The mouse selects text in the widget instead.
- **No input method support.** Dead keys and compose sequences are ignored.
- **Linux and macOS only.** The implementation uses pseudo-terminals, which have
  no Windows equivalent.

Key Bindings
============

Keys are forwarded to the shell, so ``Ctrl-C``, ``Ctrl-Z``, ``Ctrl-D``, and tab
completion behave as they would in any terminal. Because ``Ctrl-C`` must reach
the shell as an interrupt, the clipboard uses shifted chords:

=========================  ====================================================
Binding                    Action
=========================  ====================================================
``Ctrl+Shift+C``           Copy the selection
``Ctrl+Shift+V``           Paste into the shell
``Ctrl+C``                 Interrupt the foreground job, as usual
=========================  ====================================================

Multi-line pastes are wrapped in bracketed-paste markers when the shell has that
mode enabled, so a pasted block is presented as a single line for review rather
than executing each line as it arrives.

What To Explore Next
====================

- :doc:`starting_gui` for the other runtime options of the stock GUI
- :doc:`rogue_widgets` for the rest of the Rogue widget set

API Reference
=============

- :doc:`/api/python/pyrogue/pydm_widgets/linuxterminal`
- :doc:`/api/python/pyrogue/pydm_runpydm`
