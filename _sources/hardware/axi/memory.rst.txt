.. _hardware_axi_memory:

=========================
Using The AximemMap Class
=========================

The AxiMemMap class allows you to connect memory masters to PCI-Express and
Zynq7000 based FPGA firmware which utilize the generic AXI Stream drivers. 
The set of hardware which use this include but are not limited to:

- PgpCard3 with the AXI Stream DMA engine
- KCU1500 board
- Zynq7000 FPGA with TID-AIRs RCe core firmware

The following example assumes a single card is being accessed by a single master,
with the master being the device created in the :ref:`interface_memory_master_ex`.

See :ref:`hardware_axi_axi_mem_map` for more information about the AxiMemMap class methods.

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

   // Next attach to destination 1 for data traffic
   rogue::hardware::axi::AxiStreamDmaPtr dataChan = rogue::hardware::axi::AxiStreamDma::create("/dev/datadev_0", 1);

   // Create a master 
   MyCustomMasterPtr myMast = MyCustomMaster::create();

   // Connect the master as data source to the DMA
   streamConnect(myMast, dataChan);

   # Create a slave
   MyCustomSlavePtr mySlave = MyCustomSlave::create();

   # Connect the dma as data soruce to the slave
   streamConnect(dataChan, mySlave);

