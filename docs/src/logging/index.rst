.. _logging:

================
Logging In Rogue
================

Many Rogue and PyRogue modules emit useful log messages for transport bring-up,
transaction debugging, protocol state, and application behavior. The important
user-facing point is that these messages can be enabled and filtered with the
normal Python logging API.

For new Python code, the recommended interface is to use the unified PyRogue
logging path so both Python-side loggers and C++-backed Rogue loggers are
configured through Python ``logging``.

Internally, many C++-backed Rogue modules still use ``rogue.Logging``. In the
recommended unified mode, those messages are forwarded into Python logging so
they appear in the same logging path as the rest of the application.

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

Recommended Usage
=================

For a normal PyRogue application:

.. code-block:: python

   import logging
   import pyrogue as pr

   pr.setUnifiedLogging(True)
   logging.getLogger('pyrogue').setLevel(logging.INFO)
   logging.getLogger('pyrogue.udp').setLevel(logging.DEBUG)

This does three things:

- Rogue C++ log messages are forwarded into Python ``logging``.
- The native Rogue stdout sink is disabled to avoid duplicate output.
- In a running ``Root``, forwarded C++ messages can flow into
  ``Root.SystemLog``.

If you are already constructing a ``Root``, ``unifyLogs=True`` is a convenient
wrapper around the same behavior:

.. code-block:: python

   class MyRoot(pr.Root):
       def __init__(self, **kwargs):
           super().__init__(name='MyRoot', unifyLogs=True, **kwargs)

SystemLog Integration
=====================

``Root`` mirrors Python log records into:

- ``Root.SystemLog``
- ``Root.SystemLogLast``

With unified logging enabled, forwarded C++ log records can appear there as
well. Forwarded C++ records also carry additional metadata fields such as:

- ``rogueCpp``
- ``rogueTid``
- ``roguePid``
- ``rogueLogger``
- ``rogueTimestamp``
- ``rogueComponent``

This powers:

- The PyDM System Log widget
- ``pyrogue.interfaces.SystemLogMonitor``
- SQL log capture via ``SqlLogger``

Example forwarded ``SystemLog`` entry:

.. code-block:: json

   {
     "created": 1772812345.123456,
     "name": "pyrogue.udp.Client",
     "message": "UDP write call failed for 10.0.0.5: Connection refused",
     "levelName": "WARNING",
     "levelNumber": 30,
     "rogueCpp": true,
     "rogueTid": 48123,
     "roguePid": 90210,
     "rogueLogger": "pyrogue.udp.Client",
     "rogueTimestamp": 1772812345.123456,
     "rogueComponent": "udp"
   }

Legacy C++ Logging
==================

Rogue C++ code implements its own logging framework. In previous Rogue
releases, this logging had to be configured separately from Python
``logging``. That direct ``rogue.Logging`` API is still supported, and users
may still encounter it in older code, existing applications, standalone
transport scripts, or low-level debugging examples.

Today it is mainly useful for:

- older code
- standalone transport/protocol scripts
- low-level debugging outside a PyRogue ``Root``

Example:

.. code-block:: python

   import rogue

   rogue.Logging.setFilter('udp', rogue.Logging.Debug)

Useful direct C++ logging calls:

.. code-block:: python

   import rogue

   rogue.Logging.setLevel(rogue.Logging.Warning)
   rogue.Logging.setFilter('udp', rogue.Logging.Debug)
   rogue.Logging.setFilter('pyrogue.packetizer', rogue.Logging.Debug)

Severity constants are:

- ``rogue.Logging.Critical`` = 50
- ``rogue.Logging.Error`` = 40
- ``rogue.Logging.Thread`` = 35
- ``rogue.Logging.Warning`` = 30
- ``rogue.Logging.Info`` = 20
- ``rogue.Logging.Debug`` = 10

Filter matching is prefix-based. These are equivalent:

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
   rogue.Logging.setFilter('udp', rogue.Logging.Debug)
   rogue.Logging.setFilter('pyrogue.udp', rogue.Logging.Debug)

If you need the forwarding pieces directly, the unified helper is equivalent
to:

.. code-block:: python

   rogue.Logging.setForwardPython(True)
   rogue.Logging.setEmitStdout(False)

Logger Names
============

If you already have the object, the most direct way to discover the logger name
is to ask it:

.. code-block:: python

   print(my_obj.logName())
   print(pyrogue.logName(my_obj))

For a broader reference of common logger names and patterns, see
:doc:`/logging/logger_names`.

Practical Recipes
=================

Debug one Python subtree:

.. code-block:: python

   logging.getLogger('pyrogue.Device.MyDevice').setLevel(logging.DEBUG)

Debug one C++ subsystem in a PyRogue app:

.. code-block:: python

   import logging
   import pyrogue as pr

   pr.setUnifiedLogging(True)
   logging.getLogger('pyrogue.xilinx').setLevel(logging.DEBUG)

Debug one C++ subsystem in a standalone script:

.. code-block:: python

   import rogue

   rogue.Logging.setFilter('xilinx', rogue.Logging.Debug)

API Reference
=============

- Python: :doc:`/api/python/rogue/logging`
- C++: :doc:`/api/cpp/logging`

Current Rough Edges
===================

Module-specific docs now include local logging notes with the exact logger name
or pattern for that module. Use those pages first when you already know which
module you are debugging.

Related Topics
==============

- SQL-backed storage of ``SystemLog`` entries: :doc:`/built_in_modules/interfaces/sql`
- PyDM system log display: :doc:`/pydm/index`
- Root behavior and ``unifyLogs``: :doc:`/pyrogue_tree/core/root`
- Migration note for the unified logging style: :doc:`/migration/logging_unified`

.. toctree::
   :hidden:

   logger_names
