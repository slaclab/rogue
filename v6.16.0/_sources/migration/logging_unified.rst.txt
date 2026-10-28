======================
Unified Logging Update
======================

Recent Rogue documentation and examples now recommend the unified PyRogue
logging style for new Python code:

.. code-block:: python

   import logging
   import pyrogue as pr

   pr.setUnifiedLogging(True)
   pr.setLogLevel('pyrogue', 'INFO')

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
- configure both the Python logger level and the Rogue C++ filter
- let ``Root.SystemLog`` capture both Python and forwarded C++ records

For most applications, the simplest way to do that is
``pyrogue.setLogLevel(name, level)``.

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
   pr.setLogLevel('udp', 'DEBUG')
   pr.setLogLevel('rssi', 'DEBUG')

Notes
=====

- Python-only modules continue to use normal Python ``logging``.
- C++-backed modules can still be configured through direct ``rogue.Logging``
  calls when needed.
- ``pyrogue.setUnifiedLogging(True)`` changes where Rogue C++ logs are sent,
  but it does not by itself lower the Rogue C++ filter threshold.
- Module-specific documentation now lists the logger name or pattern for each
  subsystem.
