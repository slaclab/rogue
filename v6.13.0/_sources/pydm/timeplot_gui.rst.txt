.. _timeplot_gui:

====================================
Starting The Rogue PyDM Timeplot GUI
====================================

The Rogue timeplot GUI is a focused PyDM application for plotting changing
values over time. It is a better fit than the full debug GUI when the main job
is watching trends, correlations, or slowly changing control values rather than
browsing the whole tree.

The stock launcher uses ``python/pyrogue/pydm/TimePlotTop.py``, which embeds a
single ``TimePlotter`` widget bound to ``rogue://0/root``.

Command-Line Launch
===================

Start the timeplot GUI with:

.. code-block:: bash

   python -m pyrogue timeplot

As with the main GUI, the command-line default target is ``localhost:9099``. To
connect to a specific server, pass ``--server``:

.. code-block:: bash

   python -m pyrogue --server localhost:9099 timeplot

You can also provide multiple servers:

.. code-block:: bash

   python -m pyrogue --server localhost:9099,otherhost1:9099 timeplot

The session still exposes multiple server indices through the Rogue channel
plugin, but the stock timeplot top-level is built around ``rogue://0/root``.
Multi-server sessions therefore become more useful when you build a custom
plotting screen that intentionally binds channels across indices.

How It Fits With The Main GUI
=============================

The timeplot GUI uses the same Rogue PyDM plugin and the same ``rogue://``
channel scheme as the standard debug GUI. The difference is only in the top
level screen that Rogue launches.

Use the timeplot GUI when:

- You want to focus on a small set of changing Variables.
- Trend viewing matters more than tree browsing.
- Operators or developers need a lighter-weight plotting view.

Use the standard GUI when:

- You also need Commands, system controls, configuration actions, or full tree
  browsing.

Choosing Good Channels To Plot
==============================

The timeplot GUI is most useful with Variables that update through polling,
callbacks, or periodic software refresh. In practice that usually means status
and monitoring values rather than one-shot configuration registers.

When building your own plotting screens, the same Rogue widget and channel URL
rules still apply. This page is only about the stock timeplot launcher.

Variables with a useful ``/disp`` string or stable scalar numeric values tend
to be the easiest to work with. Very large arrays or configuration values that
rarely change are usually a poor fit for the stock plotting workflow.

What To Explore Next
====================

- General GUI startup and custom UI launch: :doc:`starting_gui`
- Rogue channel syntax: :doc:`channel_urls`
- Rogue widgets for custom displays: :doc:`rogue_widgets`
