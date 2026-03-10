============
Logger Names
============

This page collects common Rogue and PyRogue logger names in one place. Use it
as a quick reference when enabling logging for a specific subsystem.

If you already have the object instance, prefer:

.. code-block:: python

   print(my_obj.logName())
   print(pyrogue.logName(my_obj))

Protocols
=========

.. list-table::
   :header-rows: 1
   :widths: 24 52 24

   * - Area
     - Logger name or pattern
     - Notes
   * - UDP
     - ``pyrogue.udp.Client``, ``pyrogue.udp.Server``
     - Transport sockets and frame movement
   * - RSSI
     - ``pyrogue.rssi.controller``
     - Link state, retries, retransmit behavior
   * - Packetizer
     - ``pyrogue.packetizer.Controller``
     - Framing, drop, timeout, CRC behavior
   * - SRP
     - ``pyrogue.SrpV0``, ``pyrogue.SrpV3``
     - Request/response header processing
   * - Xilinx/XVC
     - ``pyrogue.xilinx.xvc``, ``pyrogue.xilinx.jtag``
     - TCP bridge and JTAG protocol activity

Stream And Memory
=================

.. list-table::
   :header-rows: 1
   :widths: 24 52 24

   * - Area
     - Logger name or pattern
     - Notes
   * - Stream TCP bridge
     - ``pyrogue.stream.TcpCore.<addr>.<mode>.<port>``
     - Dynamic name; mode is ``Client`` or ``Server``
   * - Stream debug tap
     - ``pyrogue.<name>``
     - Created by ``setDebug(maxBytes, name)``
   * - Stream FIFO
     - ``pyrogue.stream.Fifo``
     - FIFO operation
   * - Stream filter
     - ``pyrogue.stream.Filter``
     - Channel filtering
   * - Memory hub
     - ``pyrogue.memory.Hub``
     - Routing and splitting
   * - Memory master
     - ``pyrogue.memory.Master``
     - Request issue path
   * - Memory block
     - ``pyrogue.memory.block.<path>``
     - Dynamic name derived from first bound Variable path
   * - Memory transaction
     - ``pyrogue.memory.Transaction``
     - Internal transaction correlation
   * - Memory TCP bridge
     - ``pyrogue.memory.TcpServer.<addr>.<port>``, ``pyrogue.memory.TcpClient.<addr>.<port>``
     - Dynamic bridge logger names

Hardware And Utilities
======================

.. list-table::
   :header-rows: 1
   :widths: 24 52 24

   * - Area
     - Logger name or pattern
     - Notes
   * - Raw MemMap
     - ``pyrogue.MemMap``
     - Mapped hardware window access
   * - AXI DMA stream
     - ``pyrogue.axi.AxiStreamDma``
     - DMA channel behavior
   * - AXI DMA memory
     - ``pyrogue.axi.AxiMemMap``
     - DMA-backed memory transactions
   * - PRBS core
     - ``pyrogue.prbs.tx``, ``pyrogue.prbs.rx``
     - PRBS generator and checker
   * - File writer
     - ``pyrogue.fileio.StreamWriter``
     - File open/close, rollover, write path
   * - ZMQ server transport
     - ``pyrogue.ZmqServer``
     - Underlying server transport

Python-Only Helpers
===================

.. list-table::
   :header-rows: 1
   :widths: 24 52 24

   * - Area
     - Logger name or pattern
     - Notes
   * - Virtual client
     - ``pyrogue.VirtualClient``
     - Mirrored-tree client behavior
   * - EPICS PV server
     - ``pyrogue.EpicsPvServer``
     - PV mapping and server behavior
   * - File reader
     - ``pyrogue.FileReader``
     - Iterative file reading
   * - UART memory
     - ``pyrogue.UartMemory.<device>``
     - Dynamic serial-device path
   * - GPIB controller
     - ``pyrogue.GpibController.GPIB.<board>.<addr>``
     - Dynamic board/address path
   * - SQL logger
     - ``pyrogue.SqlLogger``, ``pyrogue.SqlReader``
     - SQL-backed logging helpers
   * - SideBandSim
     - ``pyrogue.SideBandSim.<host>.<port>``
     - Sideband simulation endpoint

Notes
=====

- C++ logger names are commonly created with ``rogue::Logging::create("...")``.
- Python logger names are commonly created with ``pyrogue.logInit(...)``.
- Prefix-based configuration is often more practical than exact full names for
  dynamic loggers.
