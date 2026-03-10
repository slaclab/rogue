.. _pydm:

==================
Using the PyDM Gui
==================

Rogue integrates with the PyDM platform for GUI-based monitoring and control of
a running PyRogue tree.

Rogue includes a default debug GUI and supports custom PyDM screens. For
production deployments, custom screens are typically preferred so operators can
focus on system-specific Variables and Commands.

Documentation for the PyDM platform:

http://slaclab.github.io/pydm/

Rogue provides custom features within PyDM, including a dedicated channel
driver URL prefix:

rogue://

Rogue also provides custom widgets that visualize Rogue-specific structures.

In practice, Rogue PyDM support is the operator-facing layer on top of a
running Root. A typical workflow is:

1. Start or connect to a PyRogue Root,
2. Expose it through the normal client interface path,
3. Open either the stock debug GUI or a custom PyDM screen,
4. Use Rogue-specific channels and widgets to interact with the tree.

PyDM support in Rogue is therefore not just about launching a GUI. It also
defines how PyDM addresses Rogue nodes, how multi-server sessions are named,
and which widgets are available when building custom displays.

When To Use The Default GUI vs A Custom Screen
==============================================

- Use the default debug GUI during bring-up, integration, and debugging when
  you need broad visibility into the tree.
- Use custom screens for production or operator workflows where only a focused
  subset of Variables and Commands should be exposed.
- Use the timeplot GUI when the main task is trend visualization of polled
  values rather than full-tree browsing.

Relationship To Client Interfaces
=================================

PyDM connects through the same client/server model used by other remote tools.
That usually means:

- A running :doc:`/pyrogue_tree/client_interfaces/zmq_server`
- One or more GUI sessions using Rogue channel URLs
- Optional coexistence with scripts, notebooks, or other clients attached to
  the same Root

What To Explore In This Section
===============================

- :doc:`starting_gui` for launching the standard debug GUI or a custom UI file
- :doc:`timeplot_gui` for time-series plotting workflows
- :doc:`channel_urls` for the Rogue-specific PyDM channel syntax
- :doc:`rogue_widgets` for the widget set used in custom screens

What To Explore Next
====================

- CLI launch and remote target selection: :doc:`/pyrogue_tree/client_interfaces/commandline`
- ZMQ server setup used by GUIs and remote clients: :doc:`/pyrogue_tree/client_interfaces/zmq_server`

.. toctree::
   :maxdepth: 1
   :caption: Rogue PyDM Features:

   starting_gui
   timeplot_gui
   channel_urls
   rogue_widgets
