.. _interfaces_clients_commandline:

==============================
Using the Command Line Client
==============================

PyRogue provides a command-line client entry point for quick access to the
running tree:

.. code-block:: bash

   python -m pyrogue --help

The CLI connects to a running server (typically ``ZmqServer``) and supports
common get/set/exec/monitor operations.

Connecting to a server
======================

By default, the CLI connects to ``localhost:9099``.
Use ``--server`` to select another endpoint:

.. code-block:: bash

   python -m pyrogue --server=localhost:9099

For GUI mode, ``--server`` may also be a comma-separated host list:

.. code-block:: bash

   python -m pyrogue --server=localhost:9099,otherHost:9099 gui

Command forms
=============

+---------------+-----------------+-----------------+----------------------------------------------------------------------------------+
| Cmd           | Path            | Value           | Operation                                                                        |
+===============+=================+=================+==================================================================================+
| gui           | NA              | NA              | Start the PyDM GUI                                                               |
+---------------+-----------------+-----------------+----------------------------------------------------------------------------------+
| syslog        | NA              | NA              | Dump current syslog and continue streaming updates                               |
+---------------+-----------------+-----------------+----------------------------------------------------------------------------------+
| monitor       | variable_path   | NA              | Display current Variable value and monitor updates                               |
+---------------+-----------------+-----------------+----------------------------------------------------------------------------------+
| get           | variable_path   | NA              | Read and display current Variable value                                          |
+---------------+-----------------+-----------------+----------------------------------------------------------------------------------+
| value         | variable_path   | NA              | Display cached/shadow Variable value (no read)                                   |
+---------------+-----------------+-----------------+----------------------------------------------------------------------------------+
| set           | variable_path   | variable_value  | Set Variable value                                                               |
+---------------+-----------------+-----------------+----------------------------------------------------------------------------------+
| exec          | command_path    | command_arg     | Execute Command with optional argument                                           |
+---------------+-----------------+-----------------+----------------------------------------------------------------------------------+

Examples
========

Start GUI:

.. code-block:: bash

   python -m pyrogue --server=localhost:9099 gui

Watch syslog:

.. code-block:: bash

   python -m pyrogue --server=localhost:9099 syslog

Monitor a Variable:

.. code-block:: bash

   python -m pyrogue --server=localhost:9099 monitor root.LocalTime

Read a Variable (forces read):

.. code-block:: bash

   python -m pyrogue --server=localhost:9099 get root.RogueVersion

Read cached value only:

.. code-block:: bash

   python -m pyrogue --server=localhost:9099 value root.AxiVersion.ScratchPad

Set a Variable:

.. code-block:: bash

   python -m pyrogue --server=localhost:9099 set root.AxiVersion.ScratchPad 0x1000

Execute a Command:

.. code-block:: bash

   python -m pyrogue --server=localhost:9099 exec root.SomeCommand 0x55

Related Topics
==============

- Server transport and bind options: :doc:`/pyrogue_tree/client_interfaces/zmq_server`
- Script-level client API: :doc:`/pyrogue_tree/client_interfaces/simple`
- Mirrored-tree client API: :doc:`/pyrogue_tree/client_interfaces/virtual`
