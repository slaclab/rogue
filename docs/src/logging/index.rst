.. _logging:

================
Logging In Rogue
================

Rogue currently has two logging systems:

- Python/PyRogue code uses the standard Python ``logging`` module.
- Many C++ modules exposed to Python use Rogue's C++ ``rogue.Logging`` class.

As a user, this split is the main thing to understand. The APIs are different,
the logger names are constructed differently, and only the Python logging path
feeds the PyRogue ``Root.SystemLog`` mechanism.

How To Think About It
=====================

When you are debugging a problem, first identify which side emitted the message:

- Pure Python / PyRogue class:
  configure it with Python ``logging``.
- C++-backed Rogue object:
  configure it with ``rogue.Logging``.

If you are not sure, the practical rule is:

- ``self._log = pyrogue.logInit(...)`` means Python logging.
- ``rogue::Logging::create("...")`` means Rogue C++ logging.

Python Logging In PyRogue
=========================

PyRogue nodes and many Python helper classes create loggers with
``pyrogue.logInit()`` in [python/pyrogue/_Node.py](/Users/bareese/rogue/python/pyrogue/_Node.py).
That function ultimately returns a standard Python logger from
``logging.getLogger(...)``.

Logger Naming Rules
-------------------

The logger name starts with ``pyrogue`` and then appends type/class/path
information. Common patterns are:

- ``pyrogue.Root.<RootSubclass>.<path>``
- ``pyrogue.Device.<DeviceSubclass>.<path>``
- ``pyrogue.Variable.<VariableSubclass>.<path>``
- ``pyrogue.Command.<CommandSubclass>.<path>``

Because the full node path is usually included after tree attachment, Python
logger names are often predictable once you know the object path.

Examples from current code:

- A Device named ``Top.MyDevice`` will typically log under a name beginning
  with ``pyrogue.Device.<ClassName>.Top.MyDevice``.
- The file reader uses ``pyrogue.FileReader`` in
  [python/pyrogue/utilities/fileio/_FileReader.py](/Users/bareese/rogue/python/pyrogue/utilities/fileio/_FileReader.py).

How To Enable Python Logging
----------------------------

Use the standard Python logging API:

.. code-block:: python

   import logging

   # Enable all PyRogue Python loggers.
   logging.getLogger('pyrogue').setLevel(logging.DEBUG)

   # Or target one subtree.
   logging.getLogger('pyrogue.Device.MyDevice').setLevel(logging.DEBUG)

If you already have the object instance, the fastest way to discover the exact
logger name is to inspect ``obj._log.name``.

.. code-block:: python

   print(my_device._log.name)

Python Log Output And SystemLog
-------------------------------

PyRogue ``Root`` installs a Python logging handler on the ``pyrogue`` logger in
[python/pyrogue/_Root.py:199](/Users/bareese/rogue/python/pyrogue/_Root.py:199).
That handler mirrors Python log records into:

- ``Root.SystemLog``
- ``Root.SystemLogLast``

This is what powers:

- The PyDM System Log widget
- ``pyrogue.interfaces.SystemLogMonitor``
- SQL log capture via ``SqlLogger``

Important limitation:
Python log records under the ``pyrogue`` logger hierarchy are captured there,
but Rogue C++ ``rogue.Logging`` output is not automatically mirrored into
``SystemLog``.

Rogue C++ Logging
=================

Many C++ modules use ``rogue::Logging`` from
[include/rogue/Logging.h](/Users/bareese/rogue/include/rogue/Logging.h) and
[src/rogue/Logging.cpp](/Users/bareese/rogue/src/rogue/Logging.cpp).

Key API
-------

The Python-visible API is:

.. code-block:: python

   import rogue

   rogue.Logging.setLevel(rogue.Logging.Warning)
   rogue.Logging.setFilter('pyrogue.udp', rogue.Logging.Debug)

Severity constants are:

- ``rogue.Logging.Critical`` = 50
- ``rogue.Logging.Error`` = 40
- ``rogue.Logging.Thread`` = 35
- ``rogue.Logging.Warning`` = 30
- ``rogue.Logging.Info`` = 20
- ``rogue.Logging.Debug`` = 10

Logger Naming Rules
-------------------

Each C++ logger is created with ``rogue::Logging::create("name")``.
Rogue then prepends ``pyrogue.`` internally, so:

- ``Logging::create("udp.Client")`` becomes ``pyrogue.udp.Client``
- ``Logging::create("packetizer.Controller")`` becomes
  ``pyrogue.packetizer.Controller``

Some logger names are static, and some are built dynamically at runtime.

Examples currently in the codebase:

- ``pyrogue.udp.Client``
- ``pyrogue.udp.Server``
- ``pyrogue.rssi.controller``
- ``pyrogue.packetizer.Controller``
- ``pyrogue.SrpV0``
- ``pyrogue.SrpV3``
- ``pyrogue.xilinx.xvc``
- ``pyrogue.xilinx.jtag``
- ``pyrogue.fileio.StreamWriter``
- ``pyrogue.prbs.tx``
- ``pyrogue.prbs.rx``

Dynamic example:

- ``pyrogue.stream.TcpCore.<addr>.Client.<port>``
- ``pyrogue.stream.TcpCore.<addr>.Server.<port>``

That dynamic pattern is constructed in
[src/rogue/interfaces/stream/TcpCore.cpp](/Users/bareese/rogue/src/rogue/interfaces/stream/TcpCore.cpp).

How To Enable C++ Logging
-------------------------

Global level:

.. code-block:: python

   import rogue

   rogue.Logging.setLevel(rogue.Logging.Debug)

Prefix filter:

.. code-block:: python

   import rogue

   # Enable only UDP-related C++ logs
   rogue.Logging.setFilter('pyrogue.udp', rogue.Logging.Debug)

   # Enable only one logger family
   rogue.Logging.setFilter('pyrogue.packetizer', rogue.Logging.Debug)

Important caveat:
``rogue.Logging.setLevel()`` and ``rogue.Logging.setFilter()`` affect logger
objects when they are created. Existing logger instances keep the level that was
copied into them at construction time.

In practice, this means:

- Set C++ logging filters before constructing the objects you want to debug.
- If the objects already exist, changing the filter may not affect them.

This behavior comes directly from
[src/rogue/Logging.cpp](/Users/bareese/rogue/src/rogue/Logging.cpp), where the
logger copies the global/filter level into ``level_`` in the constructor and
does not re-check filters for each message.

How To Find The Right Logger Name
=================================

This is the main usability problem today. The most reliable approaches are:

1. For Python objects, inspect ``obj._log.name``.

.. code-block:: python

   print(my_obj._log.name)

2. For C++-backed modules, search the source for ``Logging::create("...")``.

.. code-block:: bash

   rg 'Logging::create\("' src include

3. For dynamic C++ logger names, read the constructor that builds the string.
   ``TcpCore`` is a good example of this pattern.

4. If you know the subsystem, use a prefix filter rather than an exact full
   logger name. For example:

.. code-block:: python

   rogue.Logging.setFilter('pyrogue.udp', rogue.Logging.Debug)
   rogue.Logging.setFilter('pyrogue.xilinx', rogue.Logging.Debug)

Recommended Usage Patterns
==========================

For Python/PyRogue classes:

.. code-block:: python

   import logging

   logging.getLogger('pyrogue').setLevel(logging.INFO)
   logging.getLogger('pyrogue.Device.MyDevice').setLevel(logging.DEBUG)

For C++ Rogue modules:

.. code-block:: python

   import rogue

   # Do this before creating the object you want to debug.
   rogue.Logging.setFilter('pyrogue.udp', rogue.Logging.Debug)

For mixed Python + C++ applications:

.. code-block:: python

   import logging
   import rogue

   logging.getLogger('pyrogue').setLevel(logging.DEBUG)
   rogue.Logging.setFilter('pyrogue.rssi', rogue.Logging.Debug)

API Reference
=============

- Python:

  - :doc:`/api/python/rogue/logging`

- C++:

  - :doc:`/api/cpp/logging`

Current Rough Edges
===================

The codebase works today, but there are a few real pain points:

- Python and C++ logging use different APIs.
- C++ logger names are not easy to discover unless you inspect source.
- C++ filter changes are not dynamically applied to existing logger instances.
- Only Python ``pyrogue`` logs flow into ``Root.SystemLog`` / PyDM system-log
  tooling.

Those are good targets for future code cleanup, but the current documentation
should at least make existing behavior predictable.

Related Tools
=============

- SQL-backed storage of PyRogue ``SystemLog`` entries:
  :doc:`/built_in_modules/interfaces/sql`
- PyDM system log display:
  :doc:`/pydm/index`
- Client-side log monitoring:
  :doc:`/pyrogue_tree/client_interfaces/commandline`
