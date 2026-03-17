.. _pydm:

===================
Using The PyDM GUI
===================

Rogue integrates with the PyDM platform for GUI-based monitoring and control of
a running PyRogue tree.

Rogue includes a default debug GUI and supports custom PyDM screens. The stock
GUI is useful during bring-up because it can browse an entire tree without any
screen-design work. Custom screens become more useful once the operator
workflow is known and only a smaller set of ``Variable`` and ``Command``
interactions should be exposed.

Documentation for the PyDM platform:

http://slaclab.github.io/pydm/

Rogue provides several Rogue-specific pieces on top of base PyDM. The most
important are a dedicated channel driver URL prefix:

rogue://

and a set of widgets that understand common PyRogue structures such as a Root,
``RunControl`` device, process node, or debug tree.

In practice, Rogue PyDM support is the operator-facing layer on top of the same
client interface used by other remote tools. A typical workflow is:

1. Start a ``Root`` and expose it through a Rogue client interface, usually a
   ZMQ server.
2. Launch either the stock debug GUI, the timeplot GUI, or a custom PyDM
   screen.
3. Bind widgets to Rogue nodes with ``rogue://`` channel URLs.
4. Use Rogue-specific widgets where the generic PyDM widgets do not capture the
   right behavior.

PyDM support in Rogue is therefore not just about launching a GUI. It also
defines how PyDM addresses Rogue nodes, how a multi-server session is named,
and which widgets are available when building custom displays.

Choosing Between The Stock GUI And Custom Screens
=================================================

Use the default debug GUI during bring-up, integration, and debugging when you
need broad visibility into the tree. It exposes the system summary widgets and
the debug-tree browser without any additional UI work.

Use a custom screen when the important task is no longer "browse everything"
but instead "guide the operator through a small number of controls and status
points". That usually means a ``.ui`` file or a Python ``pydm.Display`` subclass
that binds directly to the specific paths your system cares about.

Use the timeplot GUI when the main task is trend visualization of changing
values rather than full-tree browsing.

Relationship To Client Interfaces
=================================

PyDM connects through the same client/server model used by other remote tools.
In the current implementation, the Rogue PyDM plugin resolves channels through
the ``ROGUE_SERVERS`` environment variable populated by the launcher. That
usually means:

- A running :doc:`/pyrogue_tree/client_interfaces/zmq_server`
- One or more GUI sessions using Rogue channel URLs
- Optional coexistence with scripts, notebooks, or other clients attached to
  the same ``Root``

What To Explore Next
====================

- :doc:`starting_gui` for launching the standard debug GUI or a custom UI file
- :doc:`timeplot_gui` for time-series plotting workflows
- :doc:`channel_urls` for the Rogue-specific PyDM channel syntax
- :doc:`rogue_widgets` for the widget set used in custom screens

Related Topics
==============

- CLI launch and remote target selection: :doc:`/pyrogue_tree/client_interfaces/commandline`
- ZMQ server setup used by GUIs and remote clients: :doc:`/pyrogue_tree/client_interfaces/zmq_server`

.. toctree::
   :maxdepth: 1
   :caption: Rogue PyDM Features:

   starting_gui
   timeplot_gui
   channel_urls
   rogue_widgets
