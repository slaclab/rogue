.. _starting_gui:

===========================
Starting The Rogue PyDM GUI
===========================

The standard Rogue PyDM GUI is the general-purpose browser for a running
PyRogue tree. It is most useful during bring-up and debugging, when you want
broad visibility into Devices, Variables, Commands, run-control state, and the
system log without first building a custom operator screen.

The GUI can be launched either from the command line or from a Python
application. Both paths ultimately run the same Rogue PyDM support code against
one or more Rogue servers.

How The GUI Is Structured
=========================

The default top-level display is implemented in
``python/pyrogue/pydm/pydmTop.py``. It creates two tabs:

- ``System`` for root-level controls, ``RunControl`` widgets, ``DataWriter``
  widgets, and the system log.
- ``Debug Tree`` for the full tree browser.

That structure is useful context when deciding whether the stock GUI is enough
or whether a custom screen would better match the operator workflow.

Starting From The Command Line
==============================

The normal command-line entry point is:

.. code-block:: bash

   python -m pyrogue gui

By default the command-line tool connects to ``localhost:9099``. To point the
GUI at a specific server, pass ``--server``:

.. code-block:: bash

   python -m pyrogue --server localhost:9099 gui

You can also provide a comma-separated server list:

.. code-block:: bash

   python -m pyrogue --server localhost:9099,otherhost1:9099,otherhost2:9099 gui

Rogue exposes all of those servers to the PyDM session, but the stock debug
GUI is designed around one top-level tree browser rooted at ``rogue://0/root``.
In practice, multi-server sessions are most useful when you are providing a
custom UI file that deliberately binds channels to multiple server indices.

Starting A Custom UI File
=========================

If you already have a PyDM ``.ui`` file, launch it through the same entry point
with ``--ui``:

.. code-block:: bash

   python -m pyrogue --server localhost:9099 --ui path/to/file.ui gui

This is the normal way to deploy a custom PyDM screen against a Rogue server.
The Rogue plugin and channel handling still come from the same runtime support
as the stock GUI.

If the custom screen should work against different systems, prefer the
``root`` alias in channel URLs instead of hard-coding a specific ``Root`` name.
That keeps the UI portable across applications with different root-class names.

Custom Python Top-Level Displays
================================

PyDM also supports top-level displays implemented directly in Python. The usual
pattern is to subclass :py:class:`pydm.Display`, build the layout in code, and
return ``None`` from ``ui_filepath()``:

.. code-block:: python

   from pydm import Display
   from qtpy.QtWidgets import QVBoxLayout
   from pyrogue.pydm.widgets import DebugTree, SystemWindow

   class MyTop(Display):
       def __init__(self, parent=None, args=None, macros=None):
           super().__init__(parent=parent, args=args, macros=macros)

           layout = QVBoxLayout(self)
           layout.addWidget(SystemWindow(parent=None, init_channel='rogue://0/root'))
           layout.addWidget(DebugTree(parent=None, init_channel='rogue://0/root'))

       def ui_filepath(self):
           return None

Rogue now supports passing that top-level class directly to
:py:func:`pyrogue.pydm.runPyDM`:

.. code-block:: python

   import pyrogue.pydm

   pyrogue.pydm.runPyDM(
       serverList='localhost:9099',
       display=MyTop,
       title='My System',
   )

If the display needs custom constructor behavior, pass a small factory
instead:

.. code-block:: python

   pyrogue.pydm.runPyDM(
       serverList='localhost:9099',
       display_factory=lambda: MyTop(mode='ops'),
       title='My System',
   )

The older file-based pattern still works:

.. code-block:: python

   pyrogue.pydm.runPyDM(
       serverList='localhost:9099',
       ui='path/to/my_top.py',
       title='My System',
   )

That ``ui=`` form is still useful for Qt Designer ``.ui`` files and remains
supported for backward compatibility, but for Python-defined top-level displays
the direct ``display=`` path is the cleaner Rogue-facing API.

Starting From Python
====================

The Python entry point is :py:func:`pyrogue.pydm.runPyDM`:

.. code-block:: python

   import pyrogue.pydm

   pyrogue.pydm.runPyDM(
       serverList='localhost:9099',
       title='Remote System',
   )

If the GUI is part of the same Python application as a local Root, the usual
pattern is to expose that Root through a ZMQ server and then pass its address
to :py:func:`pyrogue.pydm.runPyDM`:

.. code-block:: python

   import pyrogue as pr
   import pyrogue.pydm

   with MyRoot() as root:
       pyrogue.pydm.runPyDM(
           serverList=root.zmqServer.address,
           title='My System',
           sizeX=1000,
           sizeY=500,
           linkTimeout=600.0,
           requestStallTimeout=None,
       )

In practice, ``runPyDM`` always connects through the Rogue client interface
path rather than attaching directly to the Root object.

The current :py:func:`pyrogue.pydm.runPyDM` signature accepts ``serverList``
and does not accept a ``root=`` argument. Older examples that passed a local
``Root`` directly are stale and should be updated to expose a server first.

Important Runtime Options
=========================

The main :py:func:`pyrogue.pydm.runPyDM` options are:

- ``serverList``: Comma-separated list of ``host:port`` server addresses.
- ``ui``: Optional custom ``.ui`` file or legacy file-based top-level path.
- ``display``: A :py:class:`pydm.Display` subclass to instantiate directly.
- ``display_factory``: A callable that returns a
  :py:class:`pydm.Display` instance.
- ``title``: Window title.
- ``sizeX`` and ``sizeY``: Initial window size.
- ``maxListExpand`` and ``maxListSize``: Limits used by the debug-tree view.
- ``linkTimeout``: Idle timeout for the cached ``VirtualClient`` instances
  used by the GUI. This is the primary knob for tolerating long busy periods.
- ``requestStallTimeout``: Optional per-request stall policy for the cached
  ``VirtualClient`` instances. This is disabled by default and usually only
  makes sense when the application has a strict upper bound for valid request
  duration.

The command-line launcher defaults to ``localhost:9099``. The Python helper's
function signature currently defaults to ``localhost:9090``, so in practice it
is better to pass ``serverList`` explicitly rather than rely on the helper
default.

For simulation or co-simulation applications, the common pattern is to leave
``requestStallTimeout`` disabled and increase ``linkTimeout`` to match the
expected busy period:

.. code-block:: python

   pyrogue.pydm.runPyDM(
       serverList=root.zmqServer.address,
       linkTimeout=600.0,
       requestStallTimeout=None,
   )

Rogue Channel Prefix
====================

Rogue PyDM channels use the ``rogue://`` prefix. The first server in the
session is index ``0``, the second is ``1``, and so on. A typical channel
looks like:

.. code-block:: text

   rogue://0/root.MyDevice.MyVariable

The full channel syntax is covered in :doc:`channel_urls`.

What To Explore Next
====================

- Rogue channel syntax: :doc:`channel_urls`
- Widget set for custom screens: :doc:`rogue_widgets`
- Time-series plotting UI: :doc:`timeplot_gui`
- ZMQ server setup used by PyDM sessions: :doc:`/pyrogue_tree/client_interfaces/zmq_server`

API Reference
=============

- Python: :doc:`/api/python/pyrogue/pydm_runpydm`
