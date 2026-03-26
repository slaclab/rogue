# External Integrations

**Analysis Date:** 2026-03-24

## APIs & External Services

**EPICS Control System (PVAccess / PV4):**
- Purpose: Expose PyRogue variables as EPICS Process Variables for accelerator control system integration
- SDK/Client: `p4p` (Python PVAccess library)
- Implementation: `python/pyrogue/protocols/epicsV4.py`
- Key classes: `EpicsPvServer`, `EpicsPvHolder`, `EpicsPvHandler`
- Auth: None (EPICS CA/PVA network-level access)
- Optional: imported with `try/except` - warns if `p4p` is not installed

**Xilinx Virtual Cable (XVC):**
- Purpose: Enables Vivado JTAG debugging over network via TCP XVC protocol
- Implementation: C++ in `src/rogue/protocols/xilinx/`, headers in `include/rogue/protocols/xilinx/`
- Key classes: `Xvc`, `XvcServer`, `XvcConnection`, `JtagDriver`
- Protocol: TCP-based XVC for JTAG shift/query operations bridged to Rogue stream transport
- Auth: None (TCP socket access)

**GPIB Instrument Control:**
- Purpose: Control SCPI-compatible instruments via GPIB bus
- SDK/Client: `gpib_ctypes` (optional, `pip install gpib_ctypes`)
- Implementation: `python/pyrogue/protocols/gpib.py`
- Key class: `GpibController` (translates memory-mapped R/W to GPIB SCPI commands)
- Auth: None (local GPIB bus)

**GitHub (CI/Release):**
- Purpose: Release generation, Docker image publishing
- SDK/Client: `pygithub` (dev dependency), `gh` CLI via reusable workflows
- Auth: `secrets.GH_TOKEN`
- Workflows: `slaclab/ruckus/.github/workflows/gen_release.yml`, `docker_build.yml`

**Anaconda/Conda-Forge:**
- Purpose: Conda package distribution
- Auth: `secrets.CONDA_UPLOAD_TOKEN_TAG`
- Workflow: `slaclab/ruckus/.github/workflows/conda_build_lib.yml`
- Channel: `tidair-tag` (SLAC channel on conda-forge)

## Messaging & Transport

**ZeroMQ (Core Messaging Layer):**
- Purpose: Primary inter-process communication backbone
- C++ implementation: `src/rogue/interfaces/ZmqServer.cpp`, `src/rogue/interfaces/ZmqClient.cpp`
- Python wrappers: `python/pyrogue/interfaces/_ZmqServer.py`, `python/pyrogue/interfaces/_SimpleClient.py`
- Transport: TCP sockets with pickle (binary) and JSON (string) serialization
- Use cases:
  - ZMQ Server/Client for remote tree access (get/set/exec operations)
  - Variable update pub/sub via `_publish()` mechanism
  - TCP stream bridge (`include/rogue/interfaces/stream/TcpCore.h`) uses ZMQ for stream data
  - Simulation sideband (`python/pyrogue/interfaces/simulation.py`) uses ZMQ PUSH/PULL

**UDP Transport:**
- Purpose: Network data streaming with optional reliable delivery
- C++ implementation: `src/rogue/protocols/udp/` (Client, Server, Core)
- Headers: `include/rogue/protocols/udp/`
- Supports jumbo frames (9000 MTU) and standard frames (1500 MTU)

**RSSI (Reliable SSI):**
- Purpose: Reliable stream transport over UDP
- C++ implementation: `src/rogue/protocols/rssi/` (Client, Server, Controller)
- Python wrapper: `python/pyrogue/protocols/_Network.py` (`UdpRssiPack` device)

**SRP (SLAC Register Protocol):**
- Purpose: Register read/write protocol for FPGA communication
- C++ implementation: `src/rogue/protocols/srp/` (SrpV0, SrpV3, Cmd)
- Versions: V0 and V3

**Packetizer:**
- Purpose: Frame packetization for multiplexed stream channels
- C++ implementation: `src/rogue/protocols/packetizer/` (V1 and V2)

**TCP Stream Bridge:**
- Purpose: Bridge Rogue stream data over TCP connections
- C++ implementation: `include/rogue/interfaces/stream/TcpCore.h`, `TcpClient.h`, `TcpServer.h`
- Uses ZeroMQ internally for the TCP transport

## Data Storage

**Databases:**
- SQL via SQLAlchemy (any SQLAlchemy-supported database)
  - Connection: URL string passed to `SqlLogger`/`SqlReader` constructor
  - Client: `sqlalchemy.create_engine(url)`
  - Implementation: `python/pyrogue/interfaces/_SqlLogging.py`
  - Tables: `variables` (path, enum, disp, value, valueDisp, severity, status) and `syslog` (name, message, exception, levelName, levelNumber)
  - Pattern: Background worker thread with queue-based batched inserts

**File Storage:**
- Local filesystem only
- Stream file I/O: `python/pyrogue/utilities/fileio/` (`StreamWriter`, `StreamReader`, `FileReader`)
- C++ stream file I/O: `src/rogue/utilities/fileio/`, `include/rogue/utilities/fileio/`
- Configuration save/load: YAML + ZIP archives via `_Root.py` (uses `zipfile`, `pyyaml`)
- Compression: BZip2-based stream compression (`StreamZip`/`StreamUnZip` in `src/rogue/utilities/`)

**Caching:**
- None (no external cache service)

## Hardware Interfaces

**AXI Stream DMA (aes-stream-drivers):**
- Purpose: Zero-copy DMA data streaming to/from FPGA hardware over PCIe or AXI
- Implementation: `src/rogue/hardware/axi/AxiStreamDma.cpp`, `include/rogue/hardware/axi/AxiStreamDma.h`
- Driver API: `include/rogue/hardware/drivers/DmaDriver.h`, `include/rogue/hardware/drivers/AxisDriver.h`
- Device paths: e.g., `/dev/datadev_0`
- External dependency: [aes-stream-drivers](https://github.com/slaclab/aes-stream-drivers) kernel module

**AXI Memory Map:**
- Purpose: Register read/write via AXI4 memory-mapped access through kernel driver
- Implementation: `src/rogue/hardware/axi/AxiMemMap.cpp`, `include/rogue/hardware/axi/AxiMemMap.h`
- Driver API: `dmaReadRegister`/`dmaWriteRegister` ioctl calls via DmaDriver.h

**Serial/UART:**
- Purpose: Register access over serial UART for embedded devices
- SDK/Client: `pyserial` (`serial.Serial`)
- Implementation: `python/pyrogue/protocols/_uart.py` (`UartMemory` class)

## Authentication & Identity

**Auth Provider:**
- None - Rogue is infrastructure/DAQ software without user authentication
- Network access control is at the transport level (ZMQ bind address, TCP ports)

## Monitoring & Observability

**Error Tracking:**
- Custom C++ exception hierarchy: `rogue::GeneralError` (`include/rogue/GeneralError.h`)
- Python: `pyrogue.logException()` helper

**Logging:**
- Python `logging` module with custom `RogueLogHandler` in `python/pyrogue/_Root.py`
- C++ `rogue::Logging` class (`include/rogue/Logging.h`)
- SystemLog: Accumulated log entries stored as JSON in root `SystemLog` and `SystemLogLast` variables
- SQL logging: Optional database sink via `SqlLogger` (`python/pyrogue/interfaces/_SqlLogging.py`)

## CI/CD & Deployment

**Hosting:**
- GitHub: [slaclab/rogue](https://github.com/slaclab/rogue)
- Docker: GitHub Container Registry (via `slaclab/ruckus` Docker build workflow)
- Conda: `tidair-tag` channel

**CI Pipeline:**
- GitHub Actions (`.github/workflows/rogue_ci.yml`)
- Jobs:
  1. `full_build_test` - Ubuntu 24.04, Python 3.12, full build + lint + pytest + coverage + docs
  2. `small_build_test` - Ubuntu 24.04, C++ only build (NO_PYTHON=1, STATIC_LIB=1)
  3. `macos_arm64_build_test` - macOS 15 arm64 via Miniforge conda environment
  4. `gen_release` - Reusable workflow from `slaclab/ruckus` (on tags)
  5. `conda_build_lib` - Conda package build and upload (on tags)
  6. `docker_build_rogue` - Docker image build and push (on tags)

**Documentation Deployment:**
- GitHub Pages via `peaceiris/actions-gh-pages@v3` (on tags)
- Generated from Sphinx + Breathe + Doxygen

## Environment Configuration

**Required env vars (runtime):**
- `PYTHONPATH` - Must include rogue `python/` directory (for local installs)
- `LD_LIBRARY_PATH` - Must include rogue `lib/` directory (for local installs)
- `ROGUE_DIR` - Rogue install root (for local/custom installs)

**Optional env vars (runtime):**
- `ROGUE_SERVERS` - Set by `pyrogue.pydm.runPyDM()` for GUI server list
- `PYQTDESIGNERPATH` - Path to PyDM widget directory for Qt Designer
- `PYDM_DATA_PLUGINS_PATH` - Path to `pyrogue/pydm/data_plugins` for Rogue data plugin auto-discovery
- `PYDM_TOOLS_PATH` - Path to `pyrogue/pydm/tools` for custom PyDM tools

**CI secrets:**
- `GH_TOKEN` - GitHub token for releases and Docker push
- `CONDA_UPLOAD_TOKEN_TAG` - Anaconda upload token for conda package publishing

**Secrets location:**
- GitHub Actions secrets (repository-level)

## Webhooks & Callbacks

**Incoming:**
- None (no webhook endpoints)

**Outgoing:**
- None (no outbound webhooks)

## Client/Remote Access Patterns

**ZMQ Server (primary remote API):**
- Default port: 9099 (configurable)
- Protocol: pickle-serialized Python objects over ZMQ REQ/REP + PUB/SUB
- String protocol: JSON request/response over ZMQ
- CLI tool: `python -m pyrogue {gui|syslog|monitor|get|set|exec} --server='host:port'`
- Implementation: `python/pyrogue/interfaces/_ZmqServer.py`, `python/pyrogue/interfaces/_SimpleClient.py`

**Virtual Client:**
- Purpose: Full tree-access client that mirrors remote Root structure locally
- Implementation: `python/pyrogue/interfaces/_Virtual.py` (`VirtualClient`, `VirtualNode`)
- Transport: ZMQ client connection to ZMQ server
- Usage: `client = pyrogue.interfaces.VirtualClient(addr='localhost', port=9099)`

**MATLAB Integration:**
- `SimpleClient` designed for MATLAB interop via `pyzmq`
- Documented in `python/pyrogue/interfaces/_SimpleClient.py`

---

*Integration audit: 2026-03-24*
