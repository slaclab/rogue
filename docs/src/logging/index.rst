.. _logging:

================
Logging In Rogue
================

The following table are the known logging paths for enetities within Rogue.

+------+--------------------+--------------+--------------------------+
| Type | Section            | Class        | Log Path                 |
+======+====================+==============+==========================+
| C++  | interfaces/stream  | Fifo         | pyrogue.stream.Fifo      |
+------+--------------------+--------------+--------------------------+
| C++  | interfaces/stream  | Filter       | pyrogue.stream.Filter    |
+------+--------------------+--------------+--------------------------+
| C++  | interfaces/stream  | TcpCore      | pyrogue.stream.TcpCore   |
+------+--------------------+--------------+--------------------------+
| C++  | interfaces/stream  | TcpClient    | pyrogue.stream.TcpCore   |
+------+--------------------+--------------+--------------------------+
| C++  | interfaces/stream  | TcpServer    | pyrogue.stream.TcpCore   |
+------+--------------------+--------------+--------------------------+
| C++  | interfaces/memory  | Master       | pyrogue.memory.Master    |
+------+--------------------+--------------+--------------------------+
| C++  | interfaces/memory  | TcpClient    | pyrogue.memory.TcpClient |
+------+--------------------+--------------+--------------------------+
| C++  | interfaces/memory  | TcpServer    | pyrogue.memory.TcpServer |
+------+--------------------+--------------+--------------------------+
| C++  | hardware/axi       | AxiMemMap    | pyrogue.axi.AxiMemMap    |
+------+--------------------+--------------+--------------------------+
| C++  | hardware/axi       | AxiStreamDma | pyrogue.axi.AxiStreamDma |
+------+--------------------+--------------+--------------------------+
| C++  | hardware/pgp       | PgpCard      | pyrogue.hardware.PgpCard |
+------+--------------------+--------------+--------------------------+


