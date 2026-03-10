.. _interfaces_sql:

===========
SQL Logging
===========

``pyrogue.interfaces.SqlLogger`` records variable updates and system-log entries
from a running ``pyrogue.Root`` into a SQL database using SQLAlchemy.

Typical uses:

- Run-history capture during hardware tests
- Post-run analysis of variable trends and alarms
- Centralized logging for long-running deployments

Configuration
=============

.. code-block:: python

   import pyrogue

   class MyRoot(pyrogue.Root):
       def __init__(self):
           super().__init__(name='MyRoot')

           # Attach SQL logger as a root interface.
           self.addInterface(
               pyrogue.interfaces.SqlLogger(
                   root=self,
                   # SQLAlchemy URL: sqlite:///..., postgresql://..., etc.
                   url='sqlite:///rogue_run.db',
                   # Optional include filter for variable groups.
                   incGroups=None,
                   # Exclude groups tagged as NoSql.
                   excGroups=['NoSql'],
               )
           )

Parameters:

- ``root``: source tree to monitor
- ``url``: SQLAlchemy connection URL (for example SQLite, PostgreSQL)
- ``incGroups``: optional include filter for variable listeners
- ``excGroups``: optional exclude filter (defaults to ``['NoSql']``)

Recorded tables
===============

``SqlLogger`` creates two tables (if absent):

- ``variables``: path, enum, display format, raw/display value, severity/status
- ``syslog``: name, message, exception, level metadata

Operational notes
=================

- Writes are queued and committed by a worker thread
- Multiple queued entries are batched into a single DB transaction
- If DB connection is lost, logger reports the error and stops committing

Logging
=======

Both SQL helpers use Python logging.

- ``SqlLogger`` logger name: ``pyrogue.SqlLogger``
- ``SqlReader`` logger name: ``pyrogue.SqlReader``
- Logging API:
  ``logging.getLogger('pyrogue.SqlLogger').setLevel(logging.DEBUG)``

``SqlLogger`` logs database open failures, connection success, and worker-side
database write failures. 

What To Explore Next
====================

- Tree variable concepts: :doc:`/pyrogue_tree/core/variable`
- Logging subsystem overview: :doc:`/logging/index`
- Version gating for deployments: :doc:`/built_in_modules/interfaces/version`
