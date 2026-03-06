.. _logging:

================
Logging In Rogue
================

Rogue logging is structured by subsystem so you can target debug output at
specific classes and interfaces during bring-up and troubleshooting.

Use this page as a reference map for common logger path names.

The following table are the known logging paths for entities within Rogue. Values in brackets
are dynamic values dervied from the instance.

+------+-----------------------+-------------------+------------------------------------------------+
| Type | Section               | Class             | Log Path                                       |
+======+=======================+===================+================================================+
| C++  | interfaces/stream     | Slave             | pyrogue.stream.[name] (passed to setDebug)     |
+------+-----------------------+-------------------+------------------------------------------------+
| C++  | interfaces/stream     | Fifo              | pyrogue.stream.Fifo                            |
+------+-----------------------+-------------------+------------------------------------------------+
| C++  | interfaces/stream     | Filter            | pyrogue.stream.Filter                          |
+------+-----------------------+-------------------+------------------------------------------------+
| C++  | interfaces/stream     | TcpClient         | pyrogue.stream.TcpCore.[addr].Client.[port]    |
+------+-----------------------+-------------------+------------------------------------------------+
| C++  | interfaces/stream     | TcpServer         | pyrogue.stream.TcpCore.[addr].Server.[port]    |
+------+-----------------------+-------------------+------------------------------------------------+
| C++  | interfaces/memory     | Master            | pyrogue.memory.Master                          |
+------+-----------------------+-------------------+------------------------------------------------+
| C++  | interfaces/memory     | Block             | pyrogue.memory.Block.path                      |
+------+-----------------------+-------------------+------------------------------------------------+
| C++  | interfaces/memory     | Transaction       | pyrogue.memory.Master.Transaction              |
+------+-----------------------+-------------------+------------------------------------------------+
| C++  | interfaces/memory     | TcpClient         | pyrogue.memory.TcpClient.[addr].[port]         |
+------+-----------------------+-------------------+------------------------------------------------+
| C++  | interfaces/memory     | TcpServer         | pyrogue.memory.TcpServer.[addr].[port]         |
+------+-----------------------+-------------------+------------------------------------------------+
| C++  | hardware              | MemMap            | pyrogue.MemMap                                 |
+------+-----------------------+-------------------+------------------------------------------------+
| C++  | hardware/axi          | AxiMemMap         | pyrogue.axi.AxiMemMap                          |
+------+-----------------------+-------------------+------------------------------------------------+
| C++  | hardware/axi          | AxiStreamDma      | pyrogue.axi.AxiStreamDma                       |
+------+-----------------------+-------------------+------------------------------------------------+
| C++  | hardware/pgp          | PgpCard           | pyrogue.hardware.PgpCard                       |
+------+-----------------------+-------------------+------------------------------------------------+
| C++  | utilities             | PrbsTx            | pyrogue.prbs.tx                                |
+------+-----------------------+-------------------+------------------------------------------------+
| C++  | utilities             | PrbsRx            | pyrogue.prbs.rx                                |
+------+-----------------------+-------------------+------------------------------------------------+
| C++  | utilities/fileio      | StreamWriter      | pyrogue.fileio.StreamWriter                    |
+------+-----------------------+-------------------+------------------------------------------------+
| C++  | interfaces            | ZmqServer         | pyrogue.ZmqServer                              |
+------+-----------------------+-------------------+------------------------------------------------+
| C++  | interfaces            | ZmqClient         | pyrogue.ZmqClient                              |
+------+-----------------------+-------------------+------------------------------------------------+
| C++  | protocols/rssi        | Controller        | pyrogue.rssi.Controller                        |
+------+-----------------------+-------------------+------------------------------------------------+
| C++  | protocols/batcher     | CoreV1            | pyrogue.batcher.CoreV1                         |
+------+-----------------------+-------------------+------------------------------------------------+
| C++  | protocols/udp         | Server            | pyrogue.udp.Server                             |
+------+-----------------------+-------------------+------------------------------------------------+
| C++  | protocols/udp         | Client            | pyrogue.udp.Client                             |
+------+-----------------------+-------------------+------------------------------------------------+
| C++  | protocols/srp         | SrpV0             | pyrogue.SrpV0                                  |
+------+-----------------------+-------------------+------------------------------------------------+
| C++  | protocols/srp         | SrpV3             | pyrogue.SrpV3                                  |
+------+-----------------------+-------------------+------------------------------------------------+
| C++  | protocols/packetizer  | Controller        | pyrogue.packetizer.Controller                  |
+------+-----------------------+-------------------+------------------------------------------------+
| C++  |                       | LibraryBase       | pyrogue.LibraryBase                            |
+------+-----------------------+-------------------+------------------------------------------------+

What To Explore Next
====================

- SQL-backed Variable and syslog persistence: :doc:`/built_in_modules/sql`
- Client-side syslog monitoring workflows: :doc:`/pyrogue_tree/client_interfaces/commandline`
