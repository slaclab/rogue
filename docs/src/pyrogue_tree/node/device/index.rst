.. _pyrogue_tree_node_device:

======
Device 
======

A Device node is a container for Variable and Commands as well as other devices

* A Device class is a sub-class of rogue::interfaces::memory::Hub

   * This allows it to serve as a memory master as well as act as a hub to other memory masters
   * Variables (and their connected Blocks) associated with hardware will have an offset relative to the Device base address and will use the Device's linked memory::Slave when performing register accesses
   * Added Devices which are not already associated with a memory Slave interface will inherit the base Device's base address and Slave interface
   * A Device can have it's own direct link to a memory Slave which is not related to parent.

Key Attributes
--------------
* Devices have the following attributes, in addition to all inherited from Node:

   * offset, address, memBase, enabled
   * enabled acts as an on/off switch for invidual devices within the tree.

Key Functions
-------------
* Sub-Devices, Variables and Commands are added using the :py:meth:`add() <pyrogue.Device.add>` method
* A special device-specific :py:meth:`addRemoteVariables <pyrogue.Device.addRemoteVariables>` method allows the creation of RemoteVariable arrays
* Hide or Unhide all variables with :py:meth:`hideVariables() <pyrogue.Device.hideVariables>`
* Optional override behavior for when a system-wide hardreset is generated - :py:meth:`hardReset() <pyrogue.Device.hardReset>`
* Optional override for soft resets - :py:meth:`softReset() <pyrogue.Device.softReset>`
* Optional override for countReset - :py:meth:`countReset() <pyrogue.Device.countReset>`

Device Read/Write Operations
----------------------------

When system wide config, write and read operations are generated the blocks in each Device are manipulated by the top level Root node

* In a bulk config the shadow values in each variable are written by issuing the :py:meth:`setDisp() <pyrogue.Variable.setDisp>` call of each variable with the value contained in the configuration file

   * A write() transaction in each block is then generated and added to the queue
   * A verify() transaction in each block is then generated and added to the queue
   * The system then waits for the previous two transactions in each block to complete and then checks the result. Updated variables are then notified.

* In a bulk read operation:

   * A read() transaction in each block is then generated and added to the queue
   * The system then waits for the read transaction in each block to complete and then checks the result.

Similarly individual variable writes (from EPICS, a GUI or a script) will result in transactions occurring on each Block

* A variable set(write=True) issues the following sequence:

   * set() the value to the variable
   * Issue a write to the associated Block
   * Issue a verify to the associated Block
   * Check the result of the transactions and generate updates.

* A variable get(read=True) issues the following sequence:

   * Issue a read from the associated block
   * Check the result of the transaction
   * Return the updated value and generate updates. 

* In some special Devices this above order may not work. Some Devices may require a special command sequence to be issued before and/or after each write or read transaction.
* The Device class allows the user to override the Device level functions that are called during these read and write operations.

Custom Read/Write Operations
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* Write Transaction - :py:meth:`writeBlocks() <pyrogue.Device.writeBlocks>`
* Verify Transaction - :py:meth:`verifyBlocks() <pyrogue.Device.verifyBlocks>`
* Read Transation - :py:meth:`readBlocks() <pyrogue.Device.readBlocks>`
* Wait on the result of multiple transations - :py:meth:`checkBlocks() <pyrogue.Device.checkBlocks>`

.. code-block:: python

   def writeBlocks(self, force=False, recurse=True, variable=None):
      # Do something before transation
      super(writeBlocks, self)(recurse=recurse, variable=variable)
      # Do something after transation

   def verifyBlocks(self, recurse=True, variable=None):
      # Do something before transation
      super(verifyBlocks, self)(recurse=recurse, variable=variable)
      # Do something after transation

   def readBlocks(self, recurse=True, variable=None):
      # Do something before transation
      super(readBlocks, self)(recurse=recurse, variable=variable)
      # Do something after transation

   def checkBlocks(self, recurse=True, variable=None):
      # Do something before transation
      super(checkBlocks, self)(recurse=recurse, variable=variable)
      # Do something after transation

Raw Read/Write Device Calls
^^^^^^^^^^^^^^^^^^^^^^^^^^^
*  In some cases the user will want to create a Device which accesses memory directly without exposing values through Variables

   * Prom programming or reading DAC waveforms from a file

* A Device can be created with an offset and size and access memory within its mapped space using _rawWrite and _rawRead calls

   * Operations are usually triggered by a LocalCommand or LocalVariable within the device

* In the following, _rawWrite and _rawRead are blocking calls

:code:`def _rawWrite(self, offset, data, base=pyrogue.UInt, stride=4, wordBitSize=32):`
* offset : Offset in bytes from Device base address
* data: data to write in the form of a single value or a list of values
* base: base class indicating the type of value(s) being written
* stride: the spacing between the value locations in bytes
* wordBitSize: the size of each value in bits

:code:`def _rawRead(self, offset, numWords=1, base=pyrogue.UInt, stride=4, wordBitSize=32, data=None):`
* offset : Offset in bytes from Device base address
* numWords: Number of values to read (if data=None)
* base: base class indicating the type of value(s) being read
* stride: the spacing between the value locations in bytes
* wordBitSize: the size of each value in bits
* data: optional list in which the read data values will be stored

   * If data list is provided the number of values read is determined by the list length

Device Command Decorators
-------------------------
* Two types of command decorators can be used in Device to create LocalCommands

   * Decorators on class methods
   * Decorators on functions created within :py:meth:`pyrogue.Device.init()`

* Currently decorators can only be used to create LocalCommands

   * This may be expanded to include RemoteCommands as well
   * Can be detected as RemoteCommands when offset is passed in the decorator

Decorator Example
^^^^^^^^^^^^^^^^^

.. code-block:: python

   @pyrogue.command(order=1, name='readConfig', value='', description='Read config')
   def _readConfig(self,arg):

* Class method decorators:

   * The previous code is from the Root class which issues a readConfig from a file.

* This decorator will create a LocalCommand named :code:`readConfig` and pass the :code:`_readConfig` method as the function
* If name was not provided the LocalCommand would use the method name
* Any decorator args are passed through to the LocalCommand creation
* Because the method has the argument :code:`arg`, the LocalCommand will be configured to accept arguments. If it was not there arguments would be disabled.

   * :code:`value=''` sets the arg type as string

* The order arg in the decorator is used to control the order of the LocalCommand creation

   * This command does not have an arg and value is not passed because it is not necessary

.. code-block:: python

   @pyrogue.command(order=6, name="readAll", description='Read all values')
   def _read(self):

Init Decorator Example
^^^^^^^^^^^^^^^^^^^^^^

The following code is from the Lmk04828 class.

.. code-block:: python
   def __init__(...):
      ...
      @self.command(description="Load the CodeLoader .MAC file",value='',)
      def LoadCodeLoaderMacFile(arg):
      ...

* This decorator will create a LocalCommand named :code:`LocalCodeLoaderMacFile` and pass the decorated method as the function

   * Alternative a name arg could be passed to the decorator to override the name

* Any decorator args are passed through to the LocalCommand creation
* Because the command has the argument arg, the LocalCommand will be configured to accept arguments. If it was not there arguments would be disabled.

   * :code:`value=''` sets the arg type as string

Custom Device Classes
=====================

The following example references a class defined in :ref:`pyrogue/utilities/prbs.py <https://github.com/slaclab/rogue/blob/master/python/pyrogue/utilities/prbs.py>`.
* This is a Device class which interfaces to an underlying c++ class which receives and checks prbs data

   * Note the creation of LocalVariables which call the underlying c++ class method directly
   * Note the countReset() method

.. code-block:: python
   class PrbsRx(pyrogue.Device):
    """PRBS RX Wrapper"""

    def __init__(self, *, width=None, checkPayload=True, taps=None, stream=None, **kwargs ):

        pyrogue.Device.__init__(self, description='PRBS Software Receiver', **kwargs)
        self._prbs = rogue.utilities.Prbs()

        if width is not None:
            self._prbs.setWidth(width)

        if taps is not None:
            self._prbs.setTaps(taps)

        if stream is not None:
            pyrogue.streamConnect(stream, self)

        self.add(pyrogue.LocalVariable(name='rxEnable', description='RX Enable',
                                       mode='RW', value=True,
                                       localGet=lambda : self._prbs.getRxEnable(),
                                       localSet=lambda value: self._prbs.setRxEnable(value)))

        self.add(pyrogue.LocalVariable(name='rxErrors', description='RX Error Count',
                                       mode='RO', pollInterval=1, value=0, typeStr='UInt32',
                                       localGet=self._prbs.getRxErrors))

        self.add(pyrogue.LocalVariable(name='rxCount', description='RX Count',
                                       mode='RO', pollInterval=1, value=0, typeStr='UInt32',
                                       localGet=self._prbs.getRxCount))

        self.add(pyrogue.LocalVariable(name='rxBytes', description='RX Bytes',
                                       mode='RO', pollInterval=1, value=0, typeStr='UInt32',
                                       localGet=self._prbs.getRxBytes))

        self.add(pyrogue.LocalVariable(name='rxRate', description='RX Rate', disp="{:.3e}",
                                       mode='RO', pollInterval=1, value=0.0, units='Frames/s',
                                       localGet=self._prbs.getRxRate))

        self.add(pyrogue.LocalVariable(name='rxBw', description='RX BW', disp="{:.3e}",
                                       mode='RO', pollInterval=1, value=0.0, units='Bytes/s',
                                       localGet=self._prbs.getRxBw))

        self.add(pyrogue.LocalVariable(name='checkPayload', description='Payload Check Enable',
                                       mode='RW', value=checkPayload, localSet=self._plEnable))
    def _plEnable(self,value,changed):
        self._prbs.checkPayload(value)

    def countReset(self):
        self._prbs.resetCount()
        super().countReset()

    def _getStreamSlave(self):
        return self._prbs

    def __lshift__(self,other):
        pyrogue.streamConnect(other,self)
        return other

    def setWidth(self,width):
        self._prbs.setWidth(width)

    def setTaps(self,taps):
        self._prbs.setTaps(taps)

Another custom device class from the same link, PrbsTx, is as follows:

* Note the genFrame LocalCommand which generates a call to the underlying c++ class

   * It also gets the value of a pure local variable (txSize) which is passed as an arg to the c++ class

* Note the txEnable variable which uses the changed arg to determine whether to start or stop a backup thread in the C++ class using enable and disable

.. code-block:: python
   class PrbsTx(pyrogue.Device):
      """PRBS TX Wrapper"""

      def __init__(self, *, sendCount=False, width=None, taps=None, stream=None, **kwargs ):

         pyrogue.Device.__init__(self, description='PRBS Software Transmitter', **kwargs)
         self._prbs = rogue.utilities.Prbs()

         if width is not None:
               self._prbs.setWidth(width)

         if taps is not None:
               self._prbs.setTaps(taps)

         if stream is not None:
               pyrogue.streamConnect(self, stream)

         self._prbs.sendCount(sendCount)

         self.add(pyrogue.LocalVariable(name='txSize', description='PRBS Frame Size', units='Bytes',
                                          localSet=self._txSize, mode='RW', value=1024, typeStr='UInt32'))

         self.add(pyrogue.LocalVariable(name='txPeriod', description='Tx Period In Microseconds', units='uS',
                                          localSet=lambda value: self._prbs.setTxPeriod(value), localGet=lambda: self._prbs.getTxPeriod(), mode='RW', typeStr='UInt32'))

         self.add(pyrogue.LocalVariable(name='txEnable', description='PRBS Run Enable', mode='RW',
                                          value=False, localSet=self._txEnable))

         self.add(pyrogue.LocalCommand(name='genFrame',description='Generate n frames',value=1,
                                       function=self._genFrame))

         self.add(pyrogue.LocalVariable(name='txErrors', description='TX Error Count', mode='RO', pollInterval = 1,
                                          value=0, typeStr='UInt32', localGet=self._prbs.getTxErrors))

         self.add(pyrogue.LocalVariable(name='txCount', description='TX Count', mode='RO', pollInterval = 1,
                                          value=0, typeStr='UInt32', localGet=self._prbs.getTxCount))

         self.add(pyrogue.LocalVariable(name='txBytes', description='TX Bytes', mode='RO', pollInterval = 1,
                                          value=0, typeStr='UInt32', localGet=self._prbs.getTxBytes))
         self.add(pyrogue.LocalVariable(name='genPayload', description='Payload Generate Enable',
                                       mode='RW', value=True, localSet=self._plEnable))

         self.add(pyrogue.LocalVariable(name='txRate', description='TX Rate',  disp="{:.3e}",
                                       mode='RO', pollInterval=1, value=0.0, units='Frames/s',
                                       localGet=self._prbs.getTxRate))

        self.add(pyrogue.LocalVariable(name='txBw', description='TX BW',  disp="{:.3e}",
                                       mode='RO', pollInterval=1, value=0.0, units='Bytes/s',
                                       localGet=self._prbs.getTxBw))

    def _plEnable(self,value,changed):
        self._prbs.genPayload(value)

    def countReset(self):
        self._prbs.resetCount()
        super().countReset()

    def _genFrame(self,arg=1):
        for i in range(arg):
            self._prbs.genFrame(self.txSize.value())

    def _txSize(self,value,changed):
        if changed and int(self.txEnable.value()) == 1:
            self._prbs.disable()
            self._prbs.enable(value)

    def _txEnable(self,value,changed):
        if changed:
            if int(value) == 0:
                self._prbs.disable()
            else:
                self._prbs.enable(self.txSize.value())
    def _getStreamMaster(self):
        return self._prbs

    def __rshift__(self,other):
        pyrogue.streamConnect(self,other)
        return other

    def setWidth(self,width):
        self._prbs.setWidth(width)

    def setTaps(self,taps):
        self._prbs.setTaps(taps)

    def sendCount(self,en):
        self._prbs.sendCount(en)

    def _stop(self):
        self._prbs.disable()

Device Class Documentation
==========================

.. autoclass:: pyrogue.Device
   :members:
   :member-order: bysource
   :inherited-members:


Python Device Example
=====================

Below is an example of creating a Device which ...

.. code-block:: python

    import pyrogue

    # Create a subclass of a Device 
    class MyDevice(...):

C++ Device Example
==================

Below is an example of creating a Device class in C++.

.. code-block:: c

   #include <rogue/interfaces/memory/Constants.h>
   #include <boost/thread.hpp>

   // Create a subclass of a Device 
   class MyDevice : public rogue:: ... {
      public:

      protected:

   };

A few notes on the above examples ...

