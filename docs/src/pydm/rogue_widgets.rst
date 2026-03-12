.. _rogue_widgets:

=============
Rogue Widgets
=============

Rogue provides PyDM widgets that understand common PyRogue structures and
workflows. These are most useful when building custom screens, because they let
you reuse the same tree-aware controls that appear in the stock debug tools.

The available widgets are:

- ``SystemWindow``: Top-level system window that combines root controls, run
  control widgets, data-writer widgets, and the system log.
- ``RootControl``: Widget for reset actions and configuration file management.
- ``RunControl``: Widget for a ``pyrogue.RunControl`` Device.
- ``DataWriter``: Widget for a ``pyrogue.DataWriter`` Device.
- ``SystemLog``: Widget that displays the Rogue system log.
- ``Process``: Widget for a ``pyrogue.Process`` Device.
- ``DebugTree``: Tree browser for Devices, Variables, and Commands.
- ``PyRogueLineEdit``: Rogue-aware line edit that keeps the stale-value visual
  state.
- ``TimePlotter``: Plotting widget for time-varying values.

How To Use Them
===============

These widgets are typically placed in a Qt Designer ``.ui`` file and then bound
to Rogue channels such as:

.. code-block:: text

   rogue://0/root
   rogue://0/root.MyProcess
   rogue://0/root.MyDevice.MyVariable/disp

Some widgets expect to bind to a Root-level path, while others expect a
specific Device or Variable path. In general:

- ``SystemWindow`` and ``DebugTree`` are Root-oriented.
- ``Process``, ``RunControl``, and ``DataWriter`` are Device-oriented.
- ``PyRogueLineEdit`` is typically Variable-oriented.

Choosing Between Stock And Custom Widgets
=========================================

Use the stock debug GUI when you want a ready-made environment for broad tree
inspection. Use custom screens with Rogue widgets when you want:

- A reduced operator-facing surface,
- A system-specific workflow,
- Or a custom layout that focuses on the important Variables and Commands.

For code-constructed displays, the normal top-level object is a
:py:class:`pydm.Display` subclass. Rogue's widgets are then added to that
display just like any other Qt/PyDM widget tree. The launcher details for that
pattern are covered in :doc:`starting_gui`.

What To Explore Next
====================

- Rogue channel syntax and modes: :doc:`channel_urls`
- Launching a custom UI file: :doc:`starting_gui`
- Time-series plotting workflows: :doc:`timeplot_gui`
