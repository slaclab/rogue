============
Logger Names
============

This page collects common Rogue and PyRogue logger names in one place. Use it
as a quick reference when enabling logging for a specific subsystem.

If you already have the object instance, prefer:

.. code-block:: python

   print(my_obj.logName())
   print(pyrogue.logName(my_obj))

Common Logger Names
===================

.. list-table::
   :header-rows: 1
   :widths: 24 40 12 24

   * - Area
     - Logger name or pattern
     - Backend
     - Notes
   * - UDP
     - ``pyrogue.udp.Client``, ``pyrogue.udp.Server``
     - C++
     - Transport sockets and frame movement
   * - RSSI
     - ``pyrogue.rssi.controller``
     - C++
     - Link state, retries, retransmit behavior
   * - Packetizer
     - ``pyrogue.packetizer.Controller``
     - C++
     - Framing, drop, timeout, CRC behavior
   * - SRP
     - ``pyrogue.SrpV0``, ``pyrogue.SrpV3``
     - C++
     - Request/response header processing
   * - Xilinx/XVC
     - ``pyrogue.xilinx.xvc``, ``pyrogue.xilinx.jtag``
     - C++
     - TCP bridge and JTAG protocol activity
   * - Stream TCP bridge
     - ``pyrogue.stream.TcpCore.<addr>.<mode>.<port>``
     - C++
     - Dynamic name; mode is ``Client`` or ``Server``
   * - Stream debug tap
     - ``pyrogue.<name>``
     - C++
     - Created by ``setDebug(maxBytes, name)``
   * - Stream FIFO
     - ``pyrogue.stream.Fifo``
     - C++
     - FIFO operation
   * - Stream filter
     - ``pyrogue.stream.Filter``
     - C++
     - Channel filtering
   * - Memory hub
     - ``pyrogue.memory.Hub``
     - C++
     - Routing and splitting
   * - Memory master
     - ``pyrogue.memory.Master``
     - C++
     - Request issue path
   * - Memory block
     - ``pyrogue.memory.block.<path>``
     - C++
     - Dynamic name derived from first bound Variable path
   * - Memory transaction
     - ``pyrogue.memory.Transaction``
     - C++
     - Internal transaction correlation
   * - Memory TCP bridge
     - ``pyrogue.memory.TcpServer.<addr>.<port>``, ``pyrogue.memory.TcpClient.<addr>.<port>``
     - C++
     - Dynamic bridge logger names
   * - Raw MemMap
     - ``pyrogue.MemMap``
     - C++
     - Mapped hardware window access
   * - AXI DMA stream
     - ``pyrogue.axi.AxiStreamDma``
     - C++
     - DMA channel behavior
   * - AXI DMA memory
     - ``pyrogue.axi.AxiMemMap``
     - C++
     - DMA-backed memory transactions
   * - PRBS core
     - ``pyrogue.prbs.tx``, ``pyrogue.prbs.rx``
     - C++
     - PRBS generator and checker
   * - File writer
     - ``pyrogue.fileio.StreamWriter``
     - C++
     - File open/close, rollover, write path
   * - ZMQ server transport
     - ``pyrogue.ZmqServer``
     - C++
     - Underlying server transport
   * - Virtual client
     - ``pyrogue.VirtualClient``
     - Python
     - Mirrored-tree client behavior
   * - EPICS PV server
     - ``pyrogue.EpicsPvServer``
     - Python
     - PV mapping and server behavior
   * - File reader
     - ``pyrogue.FileReader``
     - Python
     - Iterative file reading
   * - UART memory
     - ``pyrogue.UartMemory.<device>``
     - Python
     - Dynamic serial-device path
   * - GPIB controller
     - ``pyrogue.GpibController.GPIB.<board>.<addr>``
     - Python
     - Dynamic board/address path
   * - SQL logger
     - ``pyrogue.SqlLogger``, ``pyrogue.SqlReader``
     - Python
     - SQL-backed logging helpers
   * - SideBandSim
     - ``pyrogue.SideBandSim.<host>.<port>``
     - Python
     - Sideband simulation endpoint

Notes
=====

- C++ logger names are commonly created with ``rogue::Logging::create("...")``.
- Python logger names are commonly created with ``pyrogue.logInit(...)``.
- Prefix-based configuration is often more practical than exact full names for
  dynamic loggers.
