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

Logger naming rules
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

If you already have the object instance, use the standard helper API instead of
reaching into ``obj._log`` directly.

.. code-block:: python

   print(my_device.logName())
   print(pyrogue.logName(my_device))

You can also set the level directly from the object or class:

.. code-block:: python

   my_device.setLogLevel('DEBUG', includeRogue=False)
   MyDevice.setClassLogLevel('DEBUG', includeRogue=False)

Python Log Output And SystemLog
-------------------------------

PyRogue ``Root`` installs a Python logging handler on the ``pyrogue`` logger in
[python/pyrogue/_Root.py:199](/Users/bareese/rogue/python/pyrogue/_Root.py:199).
That handler mirrors Python log records into:

- ``Root.SystemLog``
- ``Root.SystemLogLast``

This is what powers:

- the PyDM System Log widget
- ``pyrogue.interfaces.SystemLogMonitor``
- SQL log capture via ``SqlLogger``

For a PyRogue application that wants one unified logging path for both Python
and Rogue C++ modules, prefer enabling it at the Root:

.. code-block:: python

   import pyrogue as pr

   class MyRoot(pr.Root):
       def __init__(self, **kwargs):
           super().__init__(name='MyRoot', unifyLogs=True, **kwargs)

With ``unifyLogs=True``:

- Rogue C++ logs are forwarded into Python logging.
- Native Rogue stdout emission is disabled to avoid duplicate output.
- The forwarded records can flow into ``Root.SystemLog`` through the normal
  Python handler path.

Important limitation:
Python log records under the ``pyrogue`` logger hierarchy are captured there,
but Rogue C++ ``rogue.Logging`` output is not mirrored into ``SystemLog``
unless you explicitly enable Python forwarding for C++ logs.

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
   rogue.Logging.setFilter('udp', rogue.Logging.Debug)
   rogue.Logging.setFilter('pyrogue.packetizer', rogue.Logging.Debug)
   rogue.Logging.setForwardPython(True)
   rogue.Logging.setEmitStdout(False)

Severity constants are:

- ``rogue.Logging.Critical`` = 50
- ``rogue.Logging.Error`` = 40
- ``rogue.Logging.Thread`` = 35
- ``rogue.Logging.Warning`` = 30
- ``rogue.Logging.Info`` = 20
- ``rogue.Logging.Debug`` = 10

Logger naming rules
-------------------

Each C++ logger is created with ``rogue::Logging::create("name")``.
Rogue emits names in the ``pyrogue.`` namespace, so:

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

If a Python wrapper exposes the C++ logger as ``obj._log``, use the same
standard helper API rather than calling into the logger object directly:

.. code-block:: python

   print(pyrogue.logName(cpp_obj))

Direct ``cpp_obj._log.name()`` access still works for wrappers that expose the
underlying ``rogue.Logging`` instance, but it is not the preferred interface.

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
   rogue.Logging.setFilter('udp', rogue.Logging.Debug)

   # Enable only one logger family
   rogue.Logging.setFilter('pyrogue.packetizer', rogue.Logging.Debug)

Filter matching is prefix-based, and both prefixed and unprefixed names work.
These are equivalent:

.. code-block:: python

   rogue.Logging.setFilter('udp', rogue.Logging.Debug)
   rogue.Logging.setFilter('pyrogue.udp', rogue.Logging.Debug)

Unlike older Rogue releases, changing the global level or filters now updates
existing ``rogue.Logging`` instances as well as future ones.

Optional Python forwarding
--------------------------

Rogue C++ logging can also be forwarded into Python ``logging``:

.. code-block:: python

   import rogue

   rogue.Logging.setForwardPython(True)
   rogue.Logging.setEmitStdout(False)

When enabled:

- Rogue C++ log messages can be forwarded into Python ``logging`` using the same
  fully-qualified logger name.
- In a PyRogue application with a running ``Root``, those forwarded records can
  then flow into ``Root.SystemLog`` through the normal Python handler path.
- If you also call ``rogue.Logging.setEmitStdout(False)``, the native C++
  console print path is disabled so the forwarded Python record becomes the only
  visible copy.

Both forwarding and stdout suppression are disabled by default to avoid changing
existing application behavior.

How To Find The Right Logger Name
=================================

This is the main usability problem today. The most reliable approaches are:

1. For Python objects and wrapped C++ objects, use ``obj.logName()`` when it is
   available, or ``pyrogue.logName(obj)`` as the generic helper.

.. code-block:: python

   print(my_obj.logName())
   print(pyrogue.logName(my_obj))

2. For C++-backed modules, search the source for ``Logging::create("...")``.

.. code-block:: bash

   rg 'Logging::create\("' src include

3. For dynamic C++ logger names, read the constructor that builds the string.
   ``TcpCore`` is a good example of this pattern.

4. If you know the subsystem, use a prefix filter rather than an exact full
   logger name. For example:

.. code-block:: python

   rogue.Logging.setFilter('udp', rogue.Logging.Debug)
   rogue.Logging.setFilter('xilinx', rogue.Logging.Debug)

Recommended Usage Patterns
==========================

For Python/PyRogue classes:

.. code-block:: python

   import logging
   import pyrogue

   logging.getLogger('pyrogue').setLevel(logging.INFO)
   logging.getLogger('pyrogue.Device.MyDevice').setLevel(logging.DEBUG)

   # Or use the helper API on an object you already have.
   my_device.setLogLevel('DEBUG', includeRogue=False)
   pyrogue.setLogLevel(my_device, 'INFO', includeRogue=False)

For C++ Rogue modules:

.. code-block:: python

   import rogue

   rogue.Logging.setFilter('udp', rogue.Logging.Debug)

For mixed Python + C++ applications:

.. code-block:: python

   import logging
   import rogue
   import pyrogue

   logging.getLogger('pyrogue').setLevel(logging.DEBUG)
   rogue.Logging.setFilter('rssi', rogue.Logging.Debug)
   rogue.Logging.setForwardPython(True)
   rogue.Logging.setEmitStdout(False)

   # If you have a PyRogue node object, one call can configure both.
   pyrogue.setLogLevel(root.MyDevice, 'DEBUG')

Current Rough Edges
===================

The codebase works today, but there are a few real pain points:

- Python and C++ logging still use different APIs even though they now share
  some helper methods.
- C++ logger names are not easy to discover unless you inspect source.
- C++ log forwarding into Python/SystemLog is opt-in rather than automatic.

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
