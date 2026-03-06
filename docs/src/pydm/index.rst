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
