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
           pyrogue.streamConnect(self.testMaster,self.testSlave)

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

==================
Testing With EPICS
==================

The following scripts is similiar to the above but exposes the variables 
to epics to allow external control.

.. code:: python

   # Source for myEpicsTest.py

   import pyrogue
   import MyWrapper
   import time
   import pyrogue.protocols.epics

   class TestRoot(pyrogue.Root):

       def __init__(self):
           super().__init__(name="MyRoot")

           # Add master and slave devices
           self.add(MyWrapper.MyCustomMaster(name="testMaster"))
           self.add(MyWrapper.MyCustomSlave(name="testSlave"))

           # Connect master to slave
           pyrogue.streamConnect(self.testMaster,self.testSlave)

           # Start the tree
           self.start()

           # Add Epics
           self.epics = pyrogue.protocols.epics.EpicsCaServer(base='myTest',root=self)
           self.epics.start()
           self.epics.dump()

   with TestRoot() as r:
       print("Running")
       try:
           while True:
               time.sleep(1)
       except KeyboardInterrupt:
           print("Exiting")

Start the above script and generate frames using epics caput commands. You can also
monitor the counters as well. See below for an example:

In the first terminal:

.. code::

   $ python myEpicsTest.py 
   Rogue/pyrogue version v3.3.1-4-gd384a633. https://github.com/slaclab/rogue
   Loaded my module
   myTest:My Root:enable -> My Root.enable
   myTest:My Root:SystemLog -> My Root.SystemLog
   myTest:My Root:ForceWrite -> My Root.ForceWrite
   myTest:My Root:Time -> My Root.Time
   myTest:My Root:WriteAll -> My Root.WriteAll
   myTest:My Root:ReadAll -> My Root.ReadAll
   myTest:My Root:WriteState -> My Root.WriteState
   myTest:My Root:WriteConfig -> My Root.WriteConfig
   myTest:My Root:ReadConfig -> My Root.ReadConfig
   myTest:My Root:SoftReset -> My Root.SoftReset
   myTest:My Root:HardReset -> My Root.HardReset
   myTest:My Root:CountReset -> My Root.CountReset
   myTest:My Root:ClearLog -> My Root.ClearLog
   myTest:My Root:testMaster:enable -> My Root.testMaster.enable
   myTest:My Root:testMaster:FrameCount -> My Root.testMaster.FrameCount
   myTest:My Root:testMaster:ByteCount -> My Root.testMaster.ByteCount
   myTest:My Root:testMaster:FrameSize -> My Root.testMaster.FrameSize
   myTest:My Root:testMaster:MyFrameGen -> My Root.testMaster.MyFrameGen
   myTest:My Root:testSlave:enable -> My Root.testSlave.enable
   myTest:My Root:testSlave:FrameCount -> My Root.testSlave.FrameCount
   myTest:My Root:testSlave:ByteCount -> My Root.testSlave.ByteCount
   Running

In the second terminal we generate two frames from epics. Commands in
Rogue are exposed as Variables and a caput will initiate the Command
executation. Since our MyFrameGen Command does not take an arg we
pass a value of 0 to keep epics happy.

.. code::

   $ caget myTest:MyRoot:testMaster:FrameCount
   myTest:MyRoot:testMaster:FrameCount 0

   $ caget myTest:MyRoot:testSlave:FrameCount 
   myTest:MyRoot:testSlave:FrameCount 0

   $ caput myTest:MyRoot:testMaster:FrameSize 210
   Old : myTest:MyRoot:testMaster:FrameSize 0
   New : myTest:MyRoot:testMaster:FrameSize 210

   $ caput myTest:MyRoot:testMaster:MyFrameGen 0  
   Old : myTest:MyRoot:testMaster:MyFrameGen 0
   New : myTest:MyRoot:testMaster:MyFrameGen 0

   $ caput myTest:MyRoot:testMaster:MyFrameGen 0
   Old : myTest:MyRoot:testMaster:MyFrameGen 0
   New : myTest:MyRoot:testMaster:MyFrameGen 0

   $ caget myTest:MyRoot:testMaster:FrameCount   
   myTest:MyRoot:testMaster:FrameCount 2

   $ caget myTest:MyRoot:testMaster:ByteCount
   myTest:MyRoot:testMaster:ByteCount 420

   $ caget myTest:MyRoot:testSlave:FrameCount
   myTest:MyRoot:testSlave:FrameCount 2

   $ caget myTest:MyRoot:testSlave:ByteCount
   myTest:MyRoot:testSlave:ByteCount 420

==================
Testing With A GUI
==================

In the last test we will add a locally attached GUI along with EPICS. This will allow
you to experiment with how bot the GUI and EPICS can manipulate variables in parrallel.
In this test we start the GUI in the main script with the core Rogue. It is also possible
to start one or more remote GUIs. That process is described in TBD.

.. code:: python

   # Source for myEpicsGuiTest.py

   import pyrogue
   import MyWrapper
   import time
   import pyrogue.protocols.epics
   import pyrogue.gui
   import sys

   class TestRoot(pyrogue.Root):

       def __init__(self):
           super().__init__(name="MyRoot")

           # Add master and slave devices
           self.add(MyWrapper.MyCustomMaster(name="testMaster"))
           self.add(MyWrapper.MyCustomSlave(name="testSlave"))

           # Connect master to slave
           pyrogue.streamConnect(self.testMaster,self.testSlave)

           # Start the tree
           self.start()

           # Add Epics
           self.epics = pyrogue.protocols.epics.EpicsCaServer(base='myTest',root=self)
           self.epics.start()
           self.epics.dump()

   with TestRoot() as r:
       print("Running")

       # Create GUI
       appTop = pyrogue.gui.application(sys.argv)
       guiTop = pyrogue.gui.GuiTop(group='myTest')
       guiTop.addTree(r)

       # Run gui
       appTop.exec_()

You can then start the server:

.. code::

   $ python myEpicsGuiTest.py 

