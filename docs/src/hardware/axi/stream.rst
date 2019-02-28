.. _hardware_axi_stream:

============================
Using The AxiStreamDma Class
============================

The AxiStreamDma class allows you to connect stream sources and destinations to 
a channel on the PCI Express board or Zynq FPGA fabric using the generic 
AXI Stream drivers. The set of hardware which use this include but are not
limited to:

- PgpCard3 with the AXI Stream DMA engine
- KCU1500 board
- Zynq7000 FPGA with TID-AIRs RCe core firmware

A single instances of the AxiStreamDma class will be used for each data channel
on the underlying firmware. The data channel is identified by a destination ID.

The following examples assume there are two destination fields in the underlying
hardware. One which will be associated with a register protocol (SRPV3 in this case)
and the other will be a bi-directional data channel. This channel will be connected to
the custom sender and receiver described in :ref:`interfaces_stream_sending` and
:ref:`interfaces_stream_receiving`. The example also uses the memory master 
created in :ref:`interface_memory_master_ex`.

See :ref:`hardware_axi_axi_stream_dma` for more information about the AxiStreamDma class methods.

Python AxiStreamDma Example
===========================

.. code-block:: python

   import pyrogue
   import rogue.hardware.axi
   import rogue.protocols.srp

   # First attach to destination 0 for register traffic
   regChan = rogue.hardware.axi.AxiStreamDma('/dev/datadev_0', 0)

   # Create an SRP engine 
   srp = rogue.protocols.srp.SrpV3()

   # Connect the SRP engine to the register DMA
   pyrogue.streamConnectBiDir(regChan, srp)

   # Create a memory master
   memMast = MyMemMaster()

   # Connect memory master to SRP
   pyrogue.busConnect(memMast,srp)

   # Next attach to destination 1 for data traffic
   dataChan = rogue.hardware.axi.AxiStreamDma('/dev/datadev_0', 1)

   # Create a master 
   myMast = MyCustomMaster()

   # Connect the master as data source to the DMA
   pyrogue.streamConnect(myMast, dataChan)

   # Create a slave
   mySlave = MyCustomSlave()

   # Connect the dma as data soruce to the slave
   pyrogue.streamConnect(dataChan, mySlave)

C++ AxiStreamDma Example
========================

The equivelent code in C++ is show below:

.. code-block:: c

   #include <rogue/Helpers.h>
   #include <rogue/hardware/axi/AxiStreamDma.h>
   #include <rogue/ptotocols/srp/SrpV3.h>

   // First attach to destination 0 for register traffic
   rogue::hardware::axi::AxiStreamDmaPtr regChan = rogue::hardware::axi::AxiStreamDma::create("/dev/datadev_0", 0);

   // Create an SRP engine 
   rogue::protocols::srp::SrpV3Ptr srp = rogue::protocols::srp::SrpV3::create();

   // Connect the SRP engine to the register DMA
   streamConnectBiDir(regChan, srp);

   // Create a memory master
   MyMemMasterPtr memMast = MyMemMaster.create();

   // Connect memory master to SRP
   busConnect(memMast,srp);

   // Next attach to destination 1 for data traffic
   rogue::hardware::axi::AxiStreamDmaPtr dataChan = rogue::hardware::axi::AxiStreamDma::create("/dev/datadev_0", 1);

   // Create a master 
   MyCustomMasterPtr myMast = MyCustomMaster::create();

   // Connect the master as data source to the DMA
   streamConnect(myMast, dataChan);

   // Create a slave
   MyCustomSlavePtr mySlave = MyCustomSlave::create();

   // Connect the dma as data soruce to the slave
   streamConnect(dataChan, mySlave);

