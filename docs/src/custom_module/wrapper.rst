.. _custom_wrapper:

==========================================
Wrapping Custom Module With PyRogue Device
==========================================

The example below wraps the classes from :ref:`custom_sourcefile` in PyRogue
``Device`` objects. That wrapper is what exposes Variables, Commands, and
stream connection hooks to the rest of the PyRogue management layer.

In practice, this file can be created as ``MyWrapper.py`` in the same Python
directory as the shared library produced by :ref:`custom_makefile`.

.. code:: python

   # Source Code For MyWrapper.py

   import rogue
   import pyrogue
   import MyModule

   class MyCustomSlave(pyrogue.Device):

      def __init__(self, *, name, **kwargs ):

          pyrogue.Device.__init__(self, name=name, description='My Custom Stream Slave', **kwargs)

          # Create the underlying C++ slave object from MyModule
          self._mySlave = MyModule.MyCustomSlave()

          # Add read only frame count variable
          self.add(pyrogue.LocalVariable(name='FrameCount', description='Total Frames Received',
                                         mode='RO', pollInterval=1, value=0,
                                         localGet=self._mySlave.getFrameCount))

          # Add read only byte count variable
          self.add(pyrogue.LocalVariable(name='ByteCount', description='Total Bytes Received',
                                         mode='RO', pollInterval=1, value=0,
                                         localGet=self._mySlave.getTotalBytes))

      # Method called by streamConnect and streamConnectBiDir to access slave
      def _getStreamSlave(self):
          return self._mySlave

      # Support << operator
      def __lshift__(self, other):
          pyrogue.streamConnect(other,self)
          return other

   class MyCustomMaster(pyrogue.Device):

      def __init__(self, *, name, **kwargs ):

          pyrogue.Device.__init__(self, name=name, description='My Custom Stream Master', **kwargs)

          # Create the underlying C++ master object from MyModule
          self._myMast = MyModule.MyCustomMaster()

          # Add read only frame count variable
          self.add(pyrogue.LocalVariable(name='FrameCount', description='Total Frames Received',
                                         mode='RO', pollInterval=1, value=0,
                                         localGet=self._myMast.getFrameCount))

          # Add read only byte count variable
          self.add(pyrogue.LocalVariable(name='ByteCount', description='Total Bytes Received',
                                         mode='RO', pollInterval=1, value=0,
                                         localGet=self._myMast.getTotalBytes))

          # Add read write frame size variable
          self.add(pyrogue.LocalVariable(name='FrameSize', description='Transmit Frame Size',
                                         mode='RW', pollInterval=1, value=0,
                                         localGet=self._myMast.getFrameSize,
                                         localSet=lambda value: self._myMast.setFrameSize(value)))

          # Frame generation command
          self.add(pyrogue.LocalCommand(name='MyFrameGen',description='Generate a single frame',
                                        function=self._myMast.myFrameGen))

      # Method called by streamConnect and streamConnectBiDir to access master
      def _getStreamMaster(self):
          return self._myMast

      # Support >> operator
      def __rshift__(self, other):
          pyrogue.streamConnect(self,other)
          return other

What To Explore Next
====================

- Testing the wrapped module: :ref:`custom_testing`
- Stream interface composition patterns: :doc:`/stream_interface/index`
