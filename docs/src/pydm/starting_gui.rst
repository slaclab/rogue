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

Starting From The Command Line
==============================

The normal command-line entry point is:

.. code-block:: bash

   python -m pyrogue gui

By default this connects to ``localhost:9099``. To point the GUI at a specific
server, pass ``--server``:

.. code-block:: bash

   python -m pyrogue --server localhost:9099 gui

You can also provide a comma-separated server list:

.. code-block:: bash

   python -m pyrogue --server localhost:9099,otherhost1:9099,otherhost2:9099 gui

Rogue exposes all of those servers to the PyDM session, but the stock debug
GUI is designed around one tree browser view. In practice, multi-server
sessions are most useful when you are providing a custom UI file that knows
which channels to bind to each server index.

Starting A Custom UI File
=========================

If you already have a PyDM ``.ui`` file, launch it through the same entry point
with ``--ui``:

.. code-block:: bash

   python -m pyrogue --server localhost:9099 --ui path/to/file.ui gui

This is the normal way to deploy a custom PyDM screen against a Rogue server.
The Rogue plugin and channel handling still come from the same runtime support
as the stock GUI.

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

To launch that display, pass the Python file path through ``ui=``:

.. code-block:: python

   import pyrogue.pydm

   pyrogue.pydm.runPyDM(
       serverList='localhost:9099',
       ui='path/to/my_top.py',
       title='My System',
   )

This is slightly awkward, but it reflects how PyDM loads custom top-level
displays today. Rogue is forwarding that loader mechanism rather than defining
a separate display-construction API of its own.

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
       )

In practice, ``runPyDM`` always connects through the Rogue client interface
path rather than attaching directly to the Root object.

Important Runtime Options
=========================

The main :py:func:`pyrogue.pydm.runPyDM` options are:

- ``serverList``: Comma-separated list of ``host:port`` server addresses.
- ``ui``: Optional custom ``.ui`` file or Python file containing a
  :py:class:`pydm.Display` top-level.
- ``title``: Window title.
- ``sizeX`` and ``sizeY``: Initial window size.
- ``maxListExpand`` and ``maxListSize``: Limits used by the debug-tree view.

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

- Python:

  - :doc:`/api/python/pyrogue/pydm_runpydm`
