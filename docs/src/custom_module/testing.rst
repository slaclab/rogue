.. _custom_testing:

=========================
Testing The Custom Module
=========================

The following script tests the MyModule and MyWrapper implementations created
by the :ref:`custom_sourcefile`, :ref:`custom_makefile` and :ref:`custom_wrapper` steps.

.. code:: python

   # Source for myTest.py

   import pyrogue
   import MyWrapper

   class TestRoot(pyrogue.Root):

       def __init__(self):
           super().__init__(name="MyRoot")

           # Add master and slave devices
           self.add(MyWrapper.MyCustomMaster(name="testMaster"))
           self.add(MyWrapper.MyCustomSlave(name="testSlave"))

           # Connect master to slave
           self.testMaster >> self.testSlave

           # Start the tree
           self.start()

   with TestRoot() as r:

       # Set frame size to 200
       r.testMaster.FrameSize.set(200)

       # Generate 2 Frames
       r.testMaster.MyFrameGen()
       r.testMaster.MyFrameGen()

       # Display status
       print("Sent {} bytes in {} frames".format(r.testMaster.ByteCount.get(),r.testMaster.FrameCount.get()))
       print("Got  {} bytes in {} frames".format(r.testSlave.ByteCount.get(),r.testSlave.FrameCount.get()))


The output of this python script should be the following (with a different rogue version):

.. code::

   $ python myTest.py
   Rogue/pyrogue version v3.2.1. https://github.com/slaclab/rogue
   Loaded my module
   Sent 400 bytes in 2 frames
   Got  400 bytes in 2 frames

Testing With A GUI
==================

In this test we will add a locally attached GUI.
In this test we start the GUI in the main script with the core Rogue. It is also possible
to start one or more remote GUIs. That process is described in TBD.

.. code:: python

   # Source for guiTest.py

   import pyrogue
   import MyWrapper
   import time
   import pyrogue.pydm
   import sys

   class TestRoot(pyrogue.Root):

       def __init__(self):
           super().__init__(name="MyRoot")

           # Add master and slave devices
           self.add(MyWrapper.MyCustomMaster(name="testMaster"))
           self.add(MyWrapper.MyCustomSlave(name="testSlave"))

           # Connect master to slave
           self.testMaster >> self.testSlave

           # Start the tree
           self.start()

   with TestRoot() as r:
       print("Running")
       pyrogue.pydm.runPyDM(root=r,title='MyGui')

You can then start the server:

.. code::

   $ python guiTest.py

