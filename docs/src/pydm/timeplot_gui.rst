.. _timeplot_gui

===========================
Starting The Rogue PyDM Timeplot GUI
===========================

The Rogue PyDM Timeplot GUI can be started from the command line

Using The Command Line
======================

You use the rogue module from the command line to start the GUI in the following way:

.. code:: bash

   $ python -m pyrogue timeplot

This will start the Timeplot GUI and connect to the first Rogue server it fines while scanning the typical server ports opened by a Rogue instance.

You can also specify one or more Rogue server addresses on the command line:

.. code:: bash

   $ python -m pyrogue --server localhost:9099 timeplot

Or for connecting to multiple Rogue servers:

.. code:: bash

   $ python -m pyrogue --server localhost:9099,otherhost1:9099,otherhost2:9099 timeplot

The default GUI only supports a connection to one server at a time and will only display the debug GUI for the first server in the list. The additional servers are available in the PyDM session, but require a custom GUI to be created either programically or using the PyQT designer application.

The PyDM channel prefix for each instance of Rogue to which is is connected is rogue://n/ where n is the 0 based serial number of the server instance passed on the command line.


