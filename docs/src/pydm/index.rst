.. _pydm:

==================
Using the PyDM Gui
==================

Rogue makes use of the PyDM platform for its GUI. While Rogue provides a default debug GUI that auto populates, the user should consider creating custom GUIs using the numerous PyDYM widgets and other features.

Documentation on the PyDM platform can be found here:

http://slaclab.github.io/pydm/

Rogue provides a few custom features within the PyDM platform. First it supports its own custom channel driver using the URL prefix:

rogue://

Additionally Rogue provides a few custom widgets which can be used to visualize specific Rogue structures.

.. toctree::
   :maxdepth: 1
   :caption: Rogue PyDM Features:

   starting_gui
   timeplot_gui
   channel_urls
   rogue_widgets

