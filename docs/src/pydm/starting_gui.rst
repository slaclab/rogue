.. _starting_gui

===========================
Starting The Rogue PyDM GUI
===========================

The Rogue PyDM GUI can be started either from the command line or within a python application.

Using The Command Line
======================

You use the rogue module from the command line to start the GUI in the following way:

.. code:: bash

   $ python -m pyrogue gui

This will start the default Rogue debug GUI and connect to the first Rogue server it fines while scanning the typical server ports opened by a Rogue instance.

You can also specify one or more Rogue server addresses on the command line:

.. code:: bash

   $ python -m pyrogue --server localhost:9099 gui

Or for connecting to multiple Rogue servers:

.. code:: bash

   $ python -m pyrogue --server localhost:9099,otherhost1:9099,otherhost2:9099 gui

The default GUI only supports a connection to one server at a time and will only display the debug GUI for the first server in the list. The additional servers are available in the PyDM session, but require a custom GUI to be created either programically or using the PyQT designer application.

The PyDM channel prefix for each instance of Rogue to which is is connected is rogue://n/ where n is the 0 based serial number of the server instance passed on the command line.

If you have created a custom PyDM display using the designer tool, you can start that display from the command line by passing the path to the created designer ui file:

.. code:: bash

   $ python -m pyrogue --server localhost:9099,otherhost1:9099,otherhost2:9099 --ui path/to/file.ui gui

Using A Python Script
=====================

The alternative way to start the PyDM GUI is to execute the Rogue helper function for starting PyDM from within a python script, using the Rogue Virtual Client, or directly with a local Rogue root:

.. code:: python

    import pyrogue.pydm

    with MyRoot() as root:
         pyrogue.pydm.runPyDM(root=root,title='MyTitle',sizeX=1000,sizeY=500)

The possible args that can be passed to the runPyDm function are:

   - serverList: A string list of Rogue servers to connect to. i.e. localhost:9099,server1:9099,server2:9099
   - root: An existing Rogue root object using a virutal client or local root
   - ui: The path to a UI file created with the PyQT designer tool
   - title: The title of the main window
   - sizeX: The GUI size in the X dimension
   - sizeY: The GUI size in the Y dimension
