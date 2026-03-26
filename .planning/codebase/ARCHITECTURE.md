# Architecture

**Analysis Date:** 2026-03-24

## Pattern Overview

**Overall:** Dual-layer hardware abstraction framework (C++ core with Python orchestration layer)

**Key Characteristics:**
- C++ core library (`rogue-core`) provides high-performance stream and memory interfaces, compiled as a shared library
- Boost.Python bindings expose the C++ core as the `rogue` Python module (compiled as `rogue.so`)
- Pure Python layer (`pyrogue`) builds a device tree, configuration management, and GUI on top of the C++ `rogue` module
- Master/Slave pattern governs all data flow (both stream and memory interfaces)
- The framework is designed for FPGA register access and data streaming at SLAC National Accelerator Laboratory

## Layers

**C++ Core Library (`rogue-core`):**
- Purpose: High-performance stream I/O, memory transaction management, protocol implementations, and hardware drivers
- Location: `src/rogue/`, `include/rogue/`
- Contains: Stream/memory interface abstractions, protocol encoders/decoders (SRP, RSSI, packetizer, UDP, batcher, Xilinx XVC), hardware drivers (AXI DMA, memory-mapped I/O), utilities (PRBS, compression, file I/O), logging, error handling
- Depends on: Boost.Python, ZeroMQ, BZip2, NumPy, POSIX/Linux APIs
- Used by: Python `rogue` module, C++ API consumers via `librogue-core.so`

**Boost.Python Binding Layer:**
- Purpose: Expose C++ classes to Python with virtual method overriding support
- Location: `src/package.cpp` (BOOST_PYTHON_MODULE entry), `src/rogue/module.cpp` (module registration), each C++ class has a `setup_python()` static method
- Contains: Python module initialization, `*Wrap` classes that enable Python subclassing of C++ virtual methods
- Depends on: `rogue-core`, Boost.Python
- Used by: Python `pyrogue` layer

**Python Orchestration Layer (`pyrogue`):**
- Purpose: Device tree management, variable/command abstraction, configuration load/save, polling, GUI integration, remote client/server
- Location: `python/pyrogue/`
- Contains: Node/Device/Root tree classes, Variable/Command abstractions, Block memory grouping, Model data type conversions, PollQueue, ZMQ server/client, PyDM GUI widgets, EPICS interface, simulation support
- Depends on: `rogue` (C++ module), PyYAML, NumPy, ZMQ (Python), optionally PyDM/Qt for GUI
- Used by: End-user applications that define hardware device trees

## Data Flow

**Stream Interface (Frame-Based):**

1. `stream::Master` requests a `Frame` from its primary `Slave` via `reqFrame()` -- `Slave` inherits `Pool` which allocates `Buffer` objects
2. `Master` populates the frame payload using `FrameIterator` to write across `Buffer` boundaries
3. `Master` calls `sendFrame()` which delivers the frame to all attached `Slave` objects via `acceptFrame()`
4. Secondary slaves receive frames first (in attachment order), primary slave receives last
5. `Slave` subclasses override `acceptFrame()` to process, transform, or forward data
6. Bridge classes inherit both `Master` and `Slave` for transform/protocol-layer chaining

**Connection operators:** `master >> slave` or `slave << master` (both C++ and Python). The `==` operator also attaches slaves.

**Memory Interface (Transaction-Based):**

1. `memory::Master` calls `reqTransaction()` specifying address, size, data pointer, and type (Read/Write/Post/Verify)
2. Transaction propagates down through `memory::Hub` nodes, each applying its address offset
3. Leaf `memory::Slave` receives the transaction via `doTransaction()` and performs hardware I/O
4. Transaction completion is signaled back; `Master` calls `waitTransaction()` to block until done
5. At the pyrogue level, `Device` extends `Hub` and groups variables into `Block` objects for batched transactions

**Connection:** `master >> slave` or `master._setSlave(slave)` in Python.

**PyRogue Device Tree Data Flow:**

1. `Root` (extends `Device`) is the top-level container; user adds `Device` sub-nodes via `root.add(device)`
2. Each `Device` contains `Variable` and `Command` nodes; variables map to `Block` objects that manage memory transactions
3. `Root.start()` initializes the tree, optionally performs initial read/write, starts `PollQueue` and update worker threads
4. Variable changes queue to `UpdateTracker` which batches and dispatches to registered `VarListener` callbacks
5. Configuration is saved/loaded as YAML; state includes all RW/RO variables; config includes RW/WO only

**State Management:**
- Variable state is tracked in `Block` objects (C++ `rogue::interfaces::memory::Block`) with stale/verify masks
- `PollQueue` schedules periodic reads of polled variables using a heap-based priority queue
- `UpdateTracker` batches variable updates and delivers them to listeners via a queue-based worker thread
- `Root` provides `updateGroup()` context manager for atomic batched updates

## Key Abstractions

**Node (`pyrogue._Node.Node`):**
- Purpose: Base class for all tree elements with name, path, parent, children, groups, logging
- Examples: `python/pyrogue/_Node.py`
- Pattern: Composite pattern - each node has `_nodes` (OrderedDict of children), attribute-based navigation (`root.device.variable`)

**Device (`pyrogue._Device.Device`):**
- Purpose: Represents a hardware component with memory-mapped registers
- Examples: `python/pyrogue/_Device.py`, `python/pyrogue/examples/_AxiVersion.py`
- Pattern: Extends both `Node` and `rogue.interfaces.memory.Hub`; contains `Variable`, `Command`, and sub-`Device` nodes; manages `Block` objects

**Variable (`pyrogue._Variable.py`):**
- Purpose: Represents a single register field or local value with get/set, type conversion, polling
- Examples: `python/pyrogue/_Variable.py` (BaseVariable, RemoteVariable, LocalVariable, LinkVariable)
- Pattern: `RemoteVariable` maps to bits within a `Block`; `LocalVariable` stores value in Python; `LinkVariable` derives value from other variables

**Command (`pyrogue._Command.py`):**
- Purpose: Represents an executable action, optionally writing to hardware
- Examples: `python/pyrogue/_Command.py` (BaseCommand, LocalCommand, RemoteCommand)
- Pattern: Extends `BaseVariable`; `function` callback receives `root`, `dev`, `cmd`, `arg` keyword arguments

**Block (`rogue.interfaces.memory.Block` / `pyrogue._Block.py`):**
- Purpose: Groups contiguous register variables for batch memory transactions
- Examples: `include/rogue/interfaces/memory/Block.h`, `python/pyrogue/_Block.py`
- Pattern: Each block owns a byte array; variables reference bit ranges within it; transactions are block-level Read/Write/Post/Verify

**Frame (`rogue.interfaces.stream.Frame`):**
- Purpose: Container for streaming data payloads
- Examples: `include/rogue/interfaces/stream/Frame.h`
- Pattern: Owns an ordered list of `Buffer` objects; `FrameIterator` provides byte-level traversal across buffer boundaries; carries metadata (flags, channel, error)

**Pool (`rogue.interfaces.stream.Pool`):**
- Purpose: Memory allocator for stream frames and buffers
- Examples: `include/rogue/interfaces/stream/Pool.h`
- Pattern: Base class for `Slave`; supports fixed-size buffers and pooled reuse for high-rate streaming

**Hub (`rogue.interfaces.memory.Hub`):**
- Purpose: Intermediate node in memory bus tree; applies address offsets and forwards transactions
- Examples: `include/rogue/interfaces/memory/Hub.h`
- Pattern: Inherits both `memory::Master` and `memory::Slave`; can act as virtual root with its own access limits

## Entry Points

**Python Module (`python -m pyrogue`):**
- Location: `python/pyrogue/__main__.py`
- Triggers: Command-line invocation as `python -m pyrogue <cmd>`
- Responsibilities: Client-side operations (GUI launch, system log monitoring, variable get/set/monitor) connecting to a running `ZmqServer`

**C++ Shared Library:**
- Location: `src/package.cpp` (BOOST_PYTHON_MODULE entry point)
- Triggers: `import rogue` in Python
- Responsibilities: Initializes Boost.Python module, registers all C++ types via hierarchical `setup_module()` calls, prints version

**Root.start() / Root.stop():**
- Location: `python/pyrogue/_Root.py`
- Triggers: User application calls `root.start()` (or uses context manager `with Root() as root:`)
- Responsibilities: Builds memory blocks, resolves variable overlaps, starts poll queue, starts ZMQ server, performs optional initial read/write, starts update worker threads

**CMake Build:**
- Location: `CMakeLists.txt`
- Triggers: `cmake . && make`
- Responsibilities: Builds `librogue-core.so` (C++ core) and `rogue.so` (Python extension module)

## Error Handling

**Strategy:** Hierarchical exception types with C++ to Python translation

**Patterns:**
- `rogue::GeneralError` (`include/rogue/GeneralError.h`): Primary C++ exception type, formatted as `source: message`, translated to Python via `setup_python()` / `translate()`
- `pyrogue.MemoryError`: Memory transaction errors, logged at error level (not exception level) via `logException()` in `python/pyrogue/_Node.py`
- `pyrogue.VariableError`, `pyrogue.CommandError`, `pyrogue.NodeError`, `pyrogue.DeviceError`: Domain-specific Python exceptions in their respective modules
- C++ `GilRelease` (`include/rogue/GilRelease.h`) and `ScopedGil` (`include/rogue/ScopedGil.h`): RAII wrappers for Python GIL management to prevent deadlocks in cross-language calls
- Transaction error strings stored per-`Master` via `getError()`/`clearError()` for asynchronous error reporting

## Cross-Cutting Concerns

**Logging:**
- C++ layer: Custom `rogue::Logging` class (`include/rogue/Logging.h`) with named loggers, global and per-name level filtering, severity constants (Critical=50, Error=40, Warning=30, Info=20, Debug=10)
- Python layer: Standard `logging` module with hierarchical names (`pyrogue.{Type}.{Class}.{Path}`), initialized via `logInit()` in `python/pyrogue/_Node.py`
- Integration: `RootLogHandler` captures Python log records into `SystemLog` / `SystemLogLast` variables for remote monitoring

**Validation:**
- Variable-level: Type conversion via `Model` classes (`python/pyrogue/_Model.py`), min/max bounds, enum validation, bit-width constraints
- Block-level: Overlap detection during `Root.start()`, stale tracking for write optimization, verify masks for readback checking

**Authentication:**
- Not applicable (hardware control framework, no user authentication)

**Remote Access:**
- ZeroMQ-based server/client (`rogue.interfaces.ZmqServer/ZmqClient`) on 3 sockets per instance (publish, binary req/rep, string req/rep)
- `pyrogue.interfaces.ZmqServer` wraps C++ server with Python operation dispatch
- `pyrogue.interfaces.SimpleClient` provides synchronous client API
- `pyrogue.interfaces.VirtualClient` provides full virtual device tree over ZMQ

**GIL Management:**
- `GilRelease` (`include/rogue/GilRelease.h`): RAII class that releases the Python GIL during long C++ operations (I/O, blocking calls)
- `ScopedGil` (`include/rogue/ScopedGil.h`): RAII class that acquires the GIL when C++ callbacks need to invoke Python

---

*Architecture analysis: 2026-03-24*
