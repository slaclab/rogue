.. _interfaces_clients_commandline:

================================
Using The Command Line Interface
================================

Rogue provides a client interface which is able to interface to a currently running Rogue instances. In
order to utilize the client interface the Rogue Root class must be started with the serverPort argument
set to 0 (auto assign) or a specific value. The client interface is accessed with the following
command:

.. code::

   $ python -m pyrogue --help

The above command will print out the list of available commands and options.

By default the client will attempt to interface to the Rogue server on the localhost interface, using the
default serverPort value of 9099. Alternatively the --server argument can be used to specifiy a host.
The values passed to this argument can either be a host:port pair or a comman seperated list of host:port
values. The host:port list is only used when starting the PyDM GUI.

.. code::

   $ python -m pyrogue --server=localhost:9099

or

.. code::

   $ python -m pyrogue --server=localhost:9099,otherHost:9099

The command line client expects a cmd to the passed, with an optional path and value for some commands.
The possible command/path/value combinations are:

+---------------+-----------------+-----------------+----------------------------------------------------------------------------------+
| Cmd           | Path            | Value           | Operation                                                                        |
+===============+=================+=================+==================================================================================+
| gui           | NA              | NA              | Start the PyDM GUI                                                               |
+---------------+-----------------+-----------------+----------------------------------------------------------------------------------+
| syslog        | NA              | NA              | Dump the current syslog contents and listen for more syslog entries              |
+---------------+-----------------+-----------------+----------------------------------------------------------------------------------+
| monitor       | variable_path   | NA              | Display the current value of the passed variable path and monitor for updates    |
+---------------+-----------------+-----------------+----------------------------------------------------------------------------------+
| get           | variable_path   | NA              | Display the current value of the passed variable, performing a read operation    |
+---------------+-----------------+-----------------+----------------------------------------------------------------------------------+
| value         | variable_path   | NA              | Display the current value of the passed variable, without performing a read      |
+---------------+-----------------+-----------------+----------------------------------------------------------------------------------+
| set           | variable_path   | variable_value  | Set the variable_value to the passed variable.                                   |
+---------------+-----------------+-----------------+----------------------------------------------------------------------------------+
| exec          | command_path    | command_arg     | Execute the passed command with the provided optional command_arg value          |
+---------------+-----------------+-----------------+----------------------------------------------------------------------------------+

For example the PyDM GUI can be started with the following command:

.. code::

   $ python -m pyrogue --server=localhost:9099 gui

To dump the current syslog contents and monitor the syslog for updates:

.. code::

   $ python -m pyrogue --server=localhost:9099 syslog

To monitor a Rogue variable:

.. code::

   $ python -m pyrogue --server=localhost:9099 monitor root.LocalTime

To get a Rogue variable, forcing a read operation.

.. code::

   $ python -m pyrogue --server=localhost:9099 get root.RogueVersion

To display the value of a Rogue variable, without forcing a read operation:

.. code::

   $ python -m pyrogue --server=localhost:9099 value root.AxiVersion.ScratchPad

To set a new vale to a Rogue variable.

.. code::

   $ python -m pyrogue --server=localhost:9099 set root.AxiVersion.ScratchPad 0x1000

To execute a command without a passed argument.

.. code::

   $ python -m pyrogue --server=localhost:9099 exec root.SomeCommand

To execute a command with a passed argument.

.. code::

   $ python -m pyrogue --server=localhost:9099 exec root.SomeCommand 0x55

