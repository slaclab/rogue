.. _channel_urls:

============
Channel URLs
============

PyDM widgets connect to Rogue nodes through the Rogue data-plugin URL scheme:

.. code-block:: text

   rogue://0/MyRoot.MyDevice.MyVariable

The general form is:

.. code-block:: text

   rogue://<server>/<path>/<mode>/<index>

Only the server selector and path are required. ``mode`` and ``index`` are
optional.

The plugin parses these addresses in
``python/pyrogue/pydm/data_plugins/rogue_plugin.py`` and resolves them against
the server list for the current PyDM session.

Server Selection
================

The ``<server>`` field can be either:

- A zero-based server index within the current PyDM session, or
- An explicit ``host:port`` pair

Examples:

.. code-block:: text

   rogue://0/root.MyDevice.MyVariable
   rogue://localhost:9099/root.MyDevice.MyVariable

Using an explicit ``host:port`` can be convenient for one-off debugging. Using
the numeric server index is usually better for reusable screens because the UI
can stay the same while the launcher chooses which servers occupy indices
``0``, ``1``, and so on.

Using ``root`` as an Alias
==========================

Rogue accepts both the real Root name and the ``root`` alias in channel paths.
The alias is useful when building generic screens that should work across
systems whose actual Root names differ.

Examples:

.. code-block:: text

   rogue://0/root
   rogue://0/MyRoot

Access Modes
============

The optional ``mode`` suffix tells the plugin what view of the node to expose.
The main supported modes are:

- ``value``: Raw value access. This is the default.
- ``disp``: Display-formatted value from ``getDisp()``.
- ``name``: Node name.
- ``path``: Full Rogue path.

When no ``mode`` is supplied, the plugin uses ``value``.

Example:

.. code-block:: text

   rogue://0/root.Device.Variable/disp

This is especially useful when binding labels and line edits:

- Use ``/name`` for labels that should show the node name.
- Use ``/path`` when the full path is useful in the UI.
- Use ``/disp`` when the display representation matters more than the raw
  underlying type.

For editable text widgets, ``/disp`` is usually the most practical choice
because it follows Rogue's display formatting and string conversion behavior.

Array Indexing
==============

The optional ``index`` field selects an element from list-like values:

.. code-block:: text

   rogue://0/root.Device.ArrayVariable/value/3

That allows a widget to bind to one element of a larger list or array without
having to display the whole object.

This suffix is applied after the mode field. For example, the third element of
an array variable's display value uses:

.. code-block:: text

   rogue://0/root.Device.ArrayVariable/disp/2

What To Explore Next
====================

- Launching the stock or custom GUI: :doc:`starting_gui`
- Rogue-specific widget behavior: :doc:`rogue_widgets`
