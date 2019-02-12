.. _custom_wrapper:

Wrapping Custom Module With PyRogue Device
==========================================

The following demonstraes the implemenation of a PyRogue Device wrapper for
the classes contained within the :ref:`custom_sourcefile`. The variables and commands
associated with the custom module are exposed to the PyRogue management 
layer.

.. code:: python

   class MyCustomSlave(pyrogue.Device):

       def __init__(self, *, name, **kwargs ):

           pyrogue.Device.__init__(self, name=name, description='My Custom Stream Slave', **kwargs)

           # Create an instance of MyCustomSlave from MyModule
           self._mySlave = MyModule.MyCustomSlave()

           # Add read only frame count variable
           self.add(pyrogue.LocalVariable(name='FrameCount', description='Total Frames Received',
                                          mode='RO', pollInterval=1, value=0,
                                          localGet=self._mySlave.getFrameCount))

           # Add read only byte count variable
           self.add(pyrogue.LocalVariable(name='ByteCount', description='Total Bytes Received',
                                          mode='RO', pollInterval=1, value=0,
                                          localGet=self._mySlave.getTotalBytes))

       # Method called by streamConnect, streamTap and streamConnectBiDir to access slave
       def _getStreamSlave(self):
           return self._mySlave

   class MyCustomMaster(pyrogue.Device):

       def __init__(self, *, name, **kwargs ):

           pyrogue.Device.__init__(self, name=name, description='My Custom Stream Master', **kwargs)

           # Create an instance of MyCustomSlave from MyModule
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
           self.add(pyrogue.LocalCommand(name='myFrameGen',description='Generate a single frame',
                                         function=self._myFrameGet))

       # Method called by streamConnect, streamTap and streamConnectBiDir to access master
       def _getStreamMaster(self):
           return self._myMast


