.. _custom_testing:

=========================
Testing The Custom Module
=========================

The following script tests the ``MyModule`` and ``MyWrapper``
implementations created by the :ref:`custom_sourcefile`,
:ref:`custom_makefile`, and :ref:`custom_wrapper` steps.

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


The output of this Python script should look similar to the following, with a
different Rogue version string:

.. code::

   $ python myTest.py
   Rogue/pyrogue version v3.2.1. https://github.com/slaclab/rogue
   Loaded my module
   Sent 400 bytes in 2 frames
   Got  400 bytes in 2 frames

Testing With EPICS
==================

The following script is similar to the one above but exposes the Variables
through EPICS so external clients can drive them.

.. code:: python

   # Source for myEpicsTest.py

   import pyrogue
   import MyWrapper
   import time
   import pyrogue.protocols.epicsV4

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

           # Add Epics
           self.epics = pyrogue.protocols.epicsV4.EpicsPvServer(base='myTest',root=self)
           self.addProtocol(self.epics)

   with TestRoot() as r:
      r.epics.dump()

       print("Running")
       try:
           while True:
               time.sleep(1)
       except KeyboardInterrupt:
           print("Exiting")

Start the script above and generate frames using EPICS commands. You can also
monitor the counters. A simple example is shown below.

In the first terminal:

.. code::

   $ python myEpicsTest.py
   Rogue/pyrogue version v3.3.1-4-gd384a633. https://github.com/slaclab/rogue
   Loaded my module
   myTest:MyRoot:enable -> MyRoot.enable
   myTest:MyRoot:SystemLog -> MyRoot.SystemLog
   myTest:MyRoot:ForceWrite -> MyRoot.ForceWrite
   myTest:MyRoot:Time -> MyRoot.Time
   myTest:MyRoot:WriteAll -> MyRoot.WriteAll
   myTest:MyRoot:ReadAll -> MyRoot.ReadAll
   myTest:MyRoot:WriteState -> MyRoot.WriteState
   myTest:MyRoot:WriteConfig -> MyRoot.WriteConfig
   myTest:MyRoot:ReadConfig -> MyRoot.ReadConfig
   myTest:MyRoot:SoftReset -> MyRoot.SoftReset
   myTest:MyRoot:HardReset -> MyRoot.HardReset
   myTest:MyRoot:CountReset -> MyRoot.CountReset
   myTest:MyRoot:ClearLog -> MyRoot.ClearLog
   myTest:MyRoot:testMaster:enable -> MyRoot.testMaster.enable
   myTest:MyRoot:testMaster:FrameCount -> MyRoot.testMaster.FrameCount
   myTest:MyRoot:testMaster:ByteCount -> MyRoot.testMaster.ByteCount
   myTest:MyRoot:testMaster:FrameSize -> MyRoot.testMaster.FrameSize
   myTest:MyRoot:testMaster:MyFrameGen -> MyRoot.testMaster.MyFrameGen
   myTest:MyRoot:testSlave:enable -> MyRoot.testSlave.enable
   myTest:MyRoot:testSlave:FrameCount -> MyRoot.testSlave.FrameCount
   myTest:MyRoot:testSlave:ByteCount -> MyRoot.testSlave.ByteCount
   Running

In the second terminal, generate two frames from EPICS. Commands in Rogue are
exposed as Variables, and a ``pvput`` initiates Command execution. Since
``MyFrameGen`` does not take an argument, pass a value of ``0`` to keep EPICS
happy.

.. code::

   $ pvget myTest:MyRoot:testMaster:FrameCount
   myTest:MyRoot:testMaster:FrameCount 0

   $ pvget myTest:MyRoot:testSlave:FrameCount
   myTest:MyRoot:testSlave:FrameCount 0

   $ pvput myTest:MyRoot:testMaster:FrameSize 210
   Old : myTest:MyRoot:testMaster:FrameSize 0
   New : myTest:MyRoot:testMaster:FrameSize 210

   $ pvput myTest:MyRoot:testMaster:MyFrameGen 0
   Old : myTest:MyRoot:testMaster:MyFrameGen 0
   New : myTest:MyRoot:testMaster:MyFrameGen 0

   $ pvput myTest:MyRoot:testMaster:MyFrameGen 0
   Old : myTest:MyRoot:testMaster:MyFrameGen 0
   New : myTest:MyRoot:testMaster:MyFrameGen 0

   $ caget myTest:MyRoot:testMaster:FrameCount
   myTest:MyRoot:testMaster:FrameCount 2

   $ pvget myTest:MyRoot:testMaster:ByteCount
   myTest:MyRoot:testMaster:ByteCount 420

   $ pvget myTest:MyRoot:testSlave:FrameCount
   myTest:MyRoot:testSlave:FrameCount 2

   $ pvget myTest:MyRoot:testSlave:ByteCount
   myTest:MyRoot:testSlave:ByteCount 420

Testing With A GUI
==================

The last test adds a locally attached GUI along with EPICS. This allows you to
experiment with how both the GUI and EPICS can manipulate Variables in
parallel.

In this test, the GUI is started in the main script alongside the core Rogue
application. It is also possible to start one or more remote GUIs, but that
workflow is described elsewhere.

.. code:: python

   # Source for myEpicsGuiTest.py

   import pyrogue
   import MyWrapper
   import time
   import pyrogue.protocols.epicsv4
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

           # Add Epics
           self.epics = pyrogue.protocols.epicsV4.EpicsPvServer(base='myTest',root=self)
           self.addProtocol(self.epics)

   with TestRoot() as r:
       print("Running")
       pyrogue.pydm.runPyDM(root=r,title='MyGui')

You can then start the server:

.. code::

   $ python myEpicsGuiTest.py

What To Explore Next
====================

- Stream interface narrative and examples: :doc:`/stream_interface/index`
- EPICS integration details: :doc:`/built_in_modules/protocols/epicsV4/index`
- PyDM GUI workflows: :doc:`/pydm/index`
