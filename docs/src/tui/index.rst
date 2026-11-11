.. _tui:

=======================
Using The Terminal UI
=======================

``pyrogue.tui`` is a text-mode version of the default PyDM debug GUI. It shows
the same ``System`` and ``Debug Tree`` tabs, with the same controls, in a plain
terminal. It needs no Qt, no PyDM and no X display, so it works over a bare
``ssh`` session, inside ``tmux`` or ``screen``, and on hosts where the GUI
stack is not installed.

It connects through the same ZMQ client interface as the GUI, so it can be
used next to a running GUI, scripts or notebooks attached to the same
``Root``.

Starting It
===========

From the command line, against a running server:

.. code-block:: bash

   $ python -m pyrogue --server=localhost:9099 tui

From a launcher script, in place of ``runPyDM``:

.. code-block:: python

   import pyrogue.tui

   with MyRoot() as root:
       pyrogue.tui.runTui(serverList=root.zmqServer.address)

To try it without hardware, the example tree has a ``--tui`` option:

.. code-block:: bash

   $ python -m pyrogue.examples --tui

``runTui`` returns when the user quits. Several servers can be given as a
comma-separated ``serverList``, and ``tabs`` accepts a custom layout of
``('system', channel)`` and ``('tree', channel)`` entries, for example one
Debug Tree per board. See :doc:`/api/python/pyrogue/tui_runtui`.

What It Shows
=============

The ``System`` tab mirrors ``SystemWindow``:

- Reset and configuration: Poll Enable, Local Time, Rogue Version, Hard Reset,
  Initialize, Count Reset, Load Config, Save Config and Save State.
- A directory list under Load Config shows the YAML files of the configuration
  directory with size and date. Select one to load it, or tick several to load
  them in order. ``--config-dir`` sets where the list starts.
- One Data File Control block per ``DataWriter`` and one Run Control block
  per ``RunControl``.
- The System Log, last 20 entries by default, each expandable to its details
  and traceback.

The ``Debug Tree`` tab mirrors ``DebugTree``: a lazily loaded tree with the
Node, Mode, Type, ByteOffset, Value and Command columns, guiGroup folders, the
``Hidden`` group excluded, ``[Read]`` per device, ``[Exec]`` for commands, enum
choosers and value editing. The PyDM right-click tools are on a context menu
(right click, or ``o``): Read and Write Node, Read and Write Recursive, Node
Information, set from file, copy value and copy path.

Values are updated live from the server. Actions run on a worker thread, so a
long Load Config does not freeze the screen; the header shows what is busy and
the status line the result. Press ``m`` for the history of results and errors.

Keys And Mouse
==============

A key bar at the bottom of the screen lists the keys of the current tab; each
entry can be clicked. ``?`` shows the full list. The most used ones:

=========================  ====================================================
Key                        Action
=========================  ====================================================
``Tab``, ``1`` .. ``9``    Switch tab
``Enter``                  Edit, execute, expand, or press the focused button
``r`` / ``R``              Read Node / Read Recursive
``w`` / ``W``              Write Node / Write Recursive
``/`` and ``n``            Find in the loaded tree, next match
``g``                      Go to a node by path
``:``                      Command line (see below)
``L``                      Show or hide the console pane
``q``                      Quit
=========================  ====================================================

The mouse works in the tabs and dialogs: click to select or press, double
click to open, right click for the Debug Tree menu, the wheel to scroll. While
the mouse is enabled most terminals select text with Shift held down;
``--no-mouse`` (or ``runTui(mouse=False)``) leaves the mouse to the terminal.

Console And Command Line
========================

Anything the process prints, Python ``print`` and logging, Rogue C++ logging
and the output of child processes, is collected in a console pane instead of
being written over the screen. ``L`` shows the pane; while it is hidden the
header counts the new lines.

``:`` opens a command line in the pane. Paths are relative to the root and Tab
completes them:

.. code-block:: text

   AxiVersion.ScratchPad              show a value (a device: list it)
   AxiVersion.ScratchPad = 0x10       set from the display string
   AxiVersion.TestCommand(hello)      execute a command, optionally with an argument
   ls AxiVersion -d 2                 list a device
   read -R AxiVersion                 Read Recursive (write -R likewise)
   info AxiVersion.ScratchPad         node information
   goto AxiVersion.ScratchPad         select the node in the Debug Tree
   load config.yml                    LoadConfig (save, state likewise)
   log 5                              last System Log entries
   py root.AxiVersion.UpTimeCnt.get() Python with root, client and pr

``help`` lists everything. Up and Down recall earlier commands.

Requirements And Limitations
============================

- The TUI uses the standard library ``curses`` module, which conda-forge and
  the usual Linux and macOS Python builds include (see `Dependencies`_).
- Linux and macOS only, like Rogue itself.
- File paths chosen in the file browser or typed for Load Config are resolved
  on the machine running the TUI and sent to the server as text, as in the GUI.
- Capturing output written directly to the terminal descriptor (C++ logging,
  child processes) needs the C library's ``stdout`` to be reachable through
  ``ctypes`` (``stdout`` in glibc, ``__stdoutp`` in macOS libc). Where it is
  not, Python output and standard error are still captured but output written
  to the terminal descriptor is not.
- There are no plot widgets; use the PyDM time plot for those.

Dependencies
============

The TUI adds no package dependencies to Rogue:

=====================================  ==========================================================
Needed                                 Provided by
=====================================  ==========================================================
``curses``, ``ctypes`` and the rest    The Python standard library. ``curses`` is built against
                                       ``ncurses``, which conda-forge ``python`` already depends
                                       on.
Remote access to the tree              ``pyrogue.interfaces.VirtualClient`` (``pyzmq``), already
                                       part of Rogue.
PyDM, Qt, pyqtgraph                    Not used. The ``gui`` extra is not needed.
``pyte`` (tests only)                  Already in ``conda.yml``, ``pip_requirements.txt`` and the
                                       conda recipe, for the PyDM terminal tab.
=====================================  ==========================================================

``install_requires`` and the conda recipe run requirements are unchanged. To
check that an environment can run it:

.. code-block:: bash

   $ python -c "import curses; print(curses.ncurses_version)"

Python builds compiled from source without the ncurses headers, and Windows,
lack ``curses``.

Code Layout
===========

``pyrogue.tui`` is pure Python under ``python/pyrogue/tui/``:

=====================  =========================================================================
Module                 Contents
=====================  =========================================================================
``__init__.py``        Public entry point ``runTui``.
``app.py``             Main loop, header, tab bar, status line, key bar, dialog stack, mouse
                       routing, output capture (``capture_output``, ``run_curses``), ``runTui``.
``model.py``           ``Session``: one ``VirtualClient`` per server, cached node metadata
                       (``Meta``), live value cache fed by ``addVarListener``, worker thread
                       for remote calls, link state.
``ui.py``              Colours, clipped drawing, line editor and the modal dialogs (prompt,
                       chooser, checklist, text viewer, confirm, file browser).
``views.py``           ``SystemView`` (``SystemWindow`` equivalent, including the Load Config
                       directory list) and ``TreeView`` (``DebugTree`` equivalent and the
                       context-menu tools).
``console.py``         Console pane and the ``:`` command interpreter.
``commands.py``        Text output shared by the console (device listings, System Log).
=====================  =========================================================================

Everything except ``app.py``'s screen loop and the drawing code can be used
without a terminal, which is how the tests exercise it.

Building And Testing
====================

These steps follow ``DEVELOPMENT.md`` and can be run as-is by a developer or
an agent from the repository root. The TUI itself needs no compiled code, but
the tests import the ``rogue`` extension, so build Rogue first.

.. code-block:: bash

   # Environment: reuse an existing rogue_build environment, or create it
   source "$(conda info --base)/etc/profile.d/conda.sh"
   conda env create -n rogue_build -f conda.yml     # only if it does not exist
   conda activate rogue_build

   # Build. conda.yml does not include rdma-core, so on Linux either install it
   # (conda install -c conda-forge rdma-core) or build without RoCEv2 as here.
   cmake -S . -B build -DROGUE_INSTALL=local -DROGUE_BUILD_TESTS=ON -DNO_ROCEV2=ON
   cmake --build build -j"$(nproc)"
   cmake --build build --target install
   source build/setup_rogue.sh
   export PYTHONPATH="${PWD}/python:${PYTHONPATH}"

   # Lint as CI does. flake8 and cpplint are not in conda.yml.
   python -m pip install flake8 cpplint
   bash scripts/run_linters.sh

   # TUI tests
   python -m pytest tests/interfaces/test_tui_session.py \
                    tests/interfaces/test_tui_console.py \
                    tests/interfaces/test_tui_screen.py -q

   # Documentation
   (cd docs && make clean html)

   # Manual check, in a real terminal of at least 80x24
   python -m pyrogue.examples --tui

The three test modules are marked ``integration`` because they serve a small
tree over ZMQ (shared tree in ``tests/interfaces/tui_support.py``):

- ``test_tui_session.py``: path aliases, live value updates, group filtering
  and worker error reporting.
- ``test_tui_console.py``: the command line (shorthand syntax, verbs, errors,
  Tab completion) without a terminal.
- ``test_tui_screen.py``: ``python -m pyrogue tui`` on a pseudo-terminal, with
  ``pyte`` reconstructing the screen; it needs the repository ``python/``
  directory on ``PYTHONPATH`` as above. Extend it for screen-level behaviour.

On a host without a display, run the wider suites with
``QT_QPA_PLATFORM=offscreen`` so the existing PyDM tests can create their Qt
application.

API Reference
=============

- :doc:`/api/python/pyrogue/tui_runtui`
