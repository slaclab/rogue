.. _migrating_rogue_v6:

=====================
Migrating To Rogue V6
=====================

The following instructions covers features that are no longer support in Rogue V6 and how to upgrade your classes to follow the new Rogue V6 styles.

ZmqServer
=========

This biggest impacting change in Rogue V6 is to remove the ZmqServer feature from the Root class. It is now treated as an interface to be consistent with the Rogue interface model. In the past the ZmqServer feature was controlled by setting the serverPort arg when instantiating the root class. By default this arg was '0' which resulted in the server port being automatically allocated. Instead you will need to add the zmqServer manually to the root class.

Similiarly the previous feature which allowed the user to pass the root class to pydm to figure out the server port no longer works. Below is an example of including the ZmqServer in your root class and then using it with pydm.

.. code::

   class ExampleRoot(pyrogue.Root):

       def __init__(self):
           pyrogue.Root.__init__(self,
                                 description="Example Root",
                                 timeout=2.0,
                                 pollEn=True)

           # Add zmq server, keep it as an attribute so we can access it later
           self.zmqServer = pyrogue.interfaces.ZmqServer(root=self, addr='*', port=0)
           self.addInterface(self.zmqServer)

   with ExampleRoot() as root:
        pyrogue.pydm.runPyDM(serverList=root.zmqServer.address,title='Test UI',sizeX=1000,sizeY=500)


More information can be found int he ZmqServer class documenation (TBD).


SqlLogger
=========

Similiar to the zmqServer, the sql logger is now removed to be an external interface. See below for example usage of the sql logger:

.. code::

   class ExampleRoot(pyrogue.Root):

       def __init__(self):
           pyrogue.Root.__init__(self,
                                 description="Example Root",
                                 timeout=2.0,
                                 pollEn=True)

           # Add sql logger
           self.addInterface(pyrogue.interfaces.SqlLogger(root=self, url='sqlite:///test.db'))


More information can be found int he SqlLogger class documenation (TBD).


Root Configuration Streaming
============================

In previous versions of rogue the Root class automatically supported the ability to stream configuration changes. This allowed the Root class to be added as a stream source to the StreamWriter class allow for configuration changes and status updates to be logged alongside the event data. In RogueV6 this feature is removed from the Root class with a new Variable streaming class which provides the same functionality. See below for an example of using this new class to stream configuration changes to the StreamWriter. This new method continues to support dumping the current status to the file immediatly after opening and right before closing:.

.. code::

   class ExampleRoot(pyrogue.Root):

       def __init__(self):
           pyrogue.Root.__init__(self,
                                 description="Example Root",
                                 timeout=2.0,
                                 pollEn=True)

           # Create configuration stream
           stream = pyrogue.interfaces.stream.Variable(root=self)

           # Create StreamWriter with the configuration stream included as channel 1
           sw = pyrogue.utilities.fileio.StreamWriter(configStream={1: stream})
           self.add(sw)


EPICS Version 3 Channel Access Server
=====================================

Epics version 3 channel access server is removed from Rogue V6. Please use the epics 4 pv access server (P4P) instead:

.. code::

   class ExampleRoot(pyrogue.Root):

       def __init__(self):
           pyrogue.Root.__init__(self,
                                 description="Example Root",
                                 timeout=2.0,
                                 pollEn=True)

           pvserv = pyrogue.protocols.epicsV4.EpicsPvServer(base="test", root=self,incGroups=None,excGroups=None)
           self.addProtocol(pvserv)


RawWrite and RawRead
====================

The deprecated rawWrite and rawRead calls are removed from Rogue V6. The new array variables added in Rogue V5 make these calls no longer needed. The user should no longer pass a 'size' arg to the Device class and then use rawWrite and rawRead to access memory space. Instead a array Variable should be used with the appropriate similiar size. The large Variables can then be configured to be excluded from the bulk read and write transactions and can also have other smaller Variables mapped to specific locations in the overall register space. See below for an example of how a Device can be upgraded to use list Variables instead of the rawWrite and rawRead calls:




