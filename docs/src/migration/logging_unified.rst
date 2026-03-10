======================
Unified Logging Update
======================

Recent Rogue documentation and examples now recommend the unified PyRogue
logging style for new Python code:

.. code-block:: python

   import logging
   import pyrogue as pr

   pr.setUnifiedLogging(True)
   logging.getLogger('pyrogue').setLevel(logging.INFO)

What changed
============

Historically, Python logging and Rogue C++ logging were configured through
different APIs. Python code used ``logging``, while many C++-backed Rogue
modules required direct calls such as:

.. code-block:: python

   import rogue

   rogue.Logging.setFilter('udp', rogue.Logging.Debug)

That direct API is still supported, but for new Python applications the
recommended approach is:

- enable unified logging with ``pyrogue.setUnifiedLogging(True)``
- configure logger levels through Python ``logging``
- let ``Root.SystemLog`` capture both Python and forwarded C++ records

Compatibility
=============

Older code does not need to change immediately.

- Existing direct ``rogue.Logging`` calls still work.
- Standalone transport or protocol scripts can still use the direct API.
- ``Root(unifyLogs=True)`` remains a convenience wrapper around the same
  unified behavior.

Practical migration
===================

Typical migration from older code is straightforward:

Before:

.. code-block:: python

   import rogue

   rogue.Logging.setFilter('udp', rogue.Logging.Debug)
   rogue.Logging.setFilter('rssi', rogue.Logging.Debug)

After:

.. code-block:: python

   import logging
   import pyrogue as pr

   pr.setUnifiedLogging(True)
   logging.getLogger('pyrogue.udp').setLevel(logging.DEBUG)
   logging.getLogger('pyrogue.rssi').setLevel(logging.DEBUG)

Notes
=====

- Python-only modules continue to use normal Python ``logging``.
- C++-backed modules can still be configured through direct ``rogue.Logging``
  calls when needed.
- Module-specific documentation now lists the logger name or pattern for each
  subsystem.
