.. _hardware_axi_stream:
.. _hardware_axi_features:

============
AxiStreamDma
============

``AxiStreamDma`` wraps ``aes-stream-drivers`` DMA channels as Rogue Stream
interfaces. This lets hardware channels participate directly in Rogue stream
topologies with normal ``>>``, ``<<``, and ``==`` connection semantics.

The ``AxiStreamDma`` class allows you to connect stream sources and
destinations to a channel on a PCIe board or Zynq FPGA fabric using the
generic AXI stream drivers. Hardware that uses this pattern includes, but is
not limited to:

- PgpCard3 with the AXI stream DMA engine.
- KCU1500.
- Zynq7000 FPGA with TID-AIR RCE firmware.

A single ``AxiStreamDma`` instance is typically used for each data channel in
the underlying firmware. The data channel is identified by a destination ID.

The examples below assume two destination IDs in the hardware: one for a
register protocol path (SRPv3) and one for a bidirectional data channel.
The data channel is connected to custom sender/receiver implementations as
described in :ref:`interfaces_stream_sending` and
:ref:`interfaces_stream_receiving`, and the register path uses the memory
master model shown in :ref:`interfaces_memory_master_ex`.

Parameter summary
=================

``AxiStreamDma(path, dest, ssiEnable)``:

- ``path`` Parameter: Linux device path, commonly ``/dev/datadev_0``.
- ``dest`` Parameter: Destination/channel selector used by firmware/driver routing.
- ``ssiEnable`` Parameter: Enables SSI SOF/EOFE handling for stream frames.

The class includes an internal RX thread. TX occurs when frames are accepted
from upstream.

Python AxiStreamDma Example
===========================

.. code-block:: python

   import rogue.hardware.axi as rha
   import rogue.protocols.srp as rps

   # Optional: disable zero-copy globally for this device path.
   # Normally you keep zero-copy enabled.
   rha.AxiStreamDma.zeroCopyDisable('/dev/datadev_0')

   # Destination 0: register/control channel
   reg_chan = rha.AxiStreamDma('/dev/datadev_0', 0, True)
   srp = rps.SrpV3()
   reg_chan == srp

   # Memory transactions route through SRP
   mem_mast = MyMemMaster()
   mem_mast >> srp

   # Destination 1: data channel
   data_chan = rha.AxiStreamDma('/dev/datadev_0', 1, True)
   my_mast = MyCustomMaster()
   my_slave = MyCustomSlave()
   my_mast >> data_chan >> my_slave

C++ AxiStreamDma Example
========================

.. code-block:: cpp

   #include <rogue/hardware/axi/AxiStreamDma.h>
   #include <rogue/protocols/srp/SrpV3.h>

   namespace rha = rogue::hardware::axi;
   namespace rps = rogue::protocols::srp;

   // Optional: disable zero-copy globally for this device path.
   // This must be called before creating any AxiStreamDma on the path.
   rha::AxiStreamDma::zeroCopyDisable("/dev/datadev_0");

   // Destination 0: register/control channel.
   auto regChan = rha::AxiStreamDma::create("/dev/datadev_0", 0, true);

   // SRPv3 converts stream frames <-> memory transactions.
   auto srp = rps::SrpV3::create();
   *regChan == srp;

   // Upstream memory master talks to SRPv3 for register accesses.
   auto memMast = MyMemMaster::create();
   *memMast >> srp;

   // Destination 1: data channel.
   auto dataChan = rha::AxiStreamDma::create("/dev/datadev_0", 1, true);

   // Example data source and sink attached to the data DMA channel.
   auto myMast = MyCustomMaster::create();
   auto mySlave = MyCustomSlave::create();
   *myMast >> dataChan >> mySlave;

Additional AxiStreamDma Features
================================

Kernel Module Debug
-------------------

Enable driver-level debug logging for the DMA path.

Python:

.. code-block:: python

   axi_stream.setDriverDebug(1)

C++:

.. code-block:: cpp

   axiStream->setDriverDebug(1);

View output with:

.. code-block:: bash

   dmesg

Zero-Copy Control
-----------------

``AxiStreamDma`` uses zero-copy buffers by default when supported by the
driver and device path. Disable this globally per device path before creating
any ``AxiStreamDma`` instance for that path.

Python:

.. code-block:: python

   import rogue.hardware.axi as rha
   rha.AxiStreamDma.zeroCopyDisable('/dev/datadev_0')

C++:

.. code-block:: cpp

   rogue::hardware::axi::AxiStreamDma::zeroCopyDisable("/dev/datadev_0");

DMA Acknowledge
---------------

Some driver/firmware combinations expose a DMA acknowledge pulse for custom
handshake schemes.

Python:

.. code-block:: python

   axi_stream.dmaAck()

C++:

.. code-block:: cpp

   axiStream->dmaAck();

Frame Send Timeout
------------------

When buffer allocation or frame send blocks, timeout warnings are emitted at a
configurable interval (microseconds).

Python:

.. code-block:: python

   axi_stream.setTimeout(1500)

C++:

.. code-block:: cpp

   axiStream->setTimeout(1500);

API references
==============

- :doc:`/api/cpp/hardware/axi/axiStreamDma`
- :doc:`/api/cpp/interfaces/stream/index`
