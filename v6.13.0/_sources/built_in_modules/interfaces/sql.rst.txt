.. _interfaces_sql:

===========
SQL Logging
===========

For persistent logging of a running PyRogue tree, ``pyrogue.interfaces.SqlLogger``
attaches to a ``pyrogue.Root`` and writes variable updates plus system-log
events into a SQL database through SQLAlchemy.

This helper lives in the ``pyrogue.interfaces`` namespace because it is a
host-side integration layer, not a stream or memory transport. It is useful
when a system needs a durable run record, offline trend analysis, or a
database-backed audit trail alongside the live tree.

Typical uses:

- Variable history during hardware tests and commissioning runs.
- Alarm and status changes for post-run analysis.
- System-log messages from long-running control processes.

SqlLogger Workflow
==================

``SqlLogger`` is added as a managed interface on the ``Root``:

- ``addInterface()`` makes it part of the ``Root`` lifecycle.
- ``root.addVarListener(...)`` subscribes it to variable updates.
- ``root.SystemLogLast`` is watched so system-log events are written into the
  same database as variable changes.
- A background worker thread dequeues updates and commits them in batches.
- ``Root.stop()`` drives ``SqlLogger._stop()`` so queued entries are flushed
  before the worker exits.

This keeps SQL logging in the host-side integration layer without changing the
stream topology or the structure of the device tree.

Configuration Example
=====================

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

Key Constructor Arguments
=========================

- ``root`` selects the running ``Root`` whose variables and syslog updates will
  be monitored.
- ``url`` is the SQLAlchemy connection URL, such as ``sqlite:///rogue_run.db``
  for a local SQLite file or a PostgreSQL-style URL for a network database.
- ``incGroups`` limits logging to variables in selected groups.
- ``excGroups`` excludes groups from logging. It defaults to ``['NoSql']``, so
  variables tagged ``NoSql`` are skipped unless the filter is changed.

Group filtering matters most on large trees. It lets a deployment keep the
database focused on operationally relevant variables instead of logging every
polled or internal node.

Recorded Tables
===============

``SqlLogger`` creates two tables when they are not already present:

- ``variables`` stores each update path together with enum, display,
  raw/display value, severity, and status information.
- ``syslog`` stores mirrored system-log fields such as logger name, message
  text, exception text, and level metadata.

Because the logger listens to the tree rather than to a data stream, both
tables reflect the same variable-update and system-log activity that PyRogue
exposes to other host-side interfaces.

Operational Notes
=================

- Writes are queued and committed by a worker thread.
- Multiple queued entries are grouped into one transaction when possible.
- If the database connection fails during operation, the logger reports the
  error, drops the active engine, and stops committing new entries.
- Very large integers are stored through their display representation when they
  do not fit cleanly into a native 64-bit integer field.
- Tuple values are stringified before insertion.

SqlReader Access
================

``pyrogue.interfaces.SqlReader`` opens the same database schema and reflects
the ``variables`` and ``syslog`` tables for host-side inspection workflows.

The current implementation is minimal compared with ``SqlLogger``. It is best
treated as a lightweight helper around the logged schema rather than as a
full-featured query interface. In most deployments the practical workflow is to
log data with ``SqlLogger`` during the run, then inspect the resulting tables
with standard SQLAlchemy or database tooling suited to the deployment.

Logging
=======

Both SQL helpers use Python logging.

- ``SqlLogger`` logger name: ``pyrogue.SqlLogger``
- ``SqlReader`` logger name: ``pyrogue.SqlReader``
- Logging API:
  ``pyrogue.setLogLevel('pyrogue.SqlLogger', 'DEBUG')``

``SqlLogger`` logs database open failures, connection success, and worker-side
database write failures. 

Related Topics
==============

- Tree variable concepts: :doc:`/pyrogue_tree/core/variable`
- Logging subsystem overview: :doc:`/logging/index`
- GUI and client access patterns for live trees: :doc:`/pyrogue_tree/client_interfaces/index`

API Reference
=============

- Python:
  :doc:`/api/python/pyrogue/interfaces/sqllogger`
  :doc:`/api/python/pyrogue/interfaces/sqlreader`
