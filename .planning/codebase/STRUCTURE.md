# Codebase Structure

**Analysis Date:** 2026-03-24

## Directory Layout

```
rogue/
├── CMakeLists.txt              # Top-level CMake build (builds librogue-core.so + rogue.so)
├── include/                    # C++ public headers
│   └── rogue/                  # All headers under rogue namespace
│       ├── hardware/           # Hardware driver interfaces (AXI DMA, MemMap)
│       │   ├── axi/            # AXI-specific drivers
│       │   └── drivers/        # Low-level kernel driver headers
│       ├── interfaces/         # Core stream/memory/ZMQ abstractions
│       │   ├── api/            # BSP (Board Support Package) API
│       │   ├── memory/         # Memory transaction interface (Master/Slave/Hub/Block/Variable)
│       │   └── stream/         # Stream interface (Master/Slave/Frame/Buffer/Pool)
│       ├── protocols/          # Network/transport protocol implementations
│       │   ├── batcher/        # Frame batcher (V1/V2)
│       │   ├── packetizer/     # Packetizer protocol (V1/V2)
│       │   ├── rssi/           # Reliable SSI protocol (client/server)
│       │   ├── srp/            # SLAC Register Protocol (V0/V3)
│       │   ├── udp/            # UDP client/server
│       │   └── xilinx/         # Xilinx XVC/JTAG
│       └── utilities/          # Utility classes
│           └── fileio/         # Stream file reader/writer
├── src/                        # C++ source files
│   ├── package.cpp             # BOOST_PYTHON_MODULE entry point (builds rogue.so)
│   ├── CMakeLists.txt          # Globs .cpp for rogue.so target
│   └── rogue/                  # Core library sources (mirrors include/rogue/ structure)
│       ├── CMakeLists.txt      # Adds subdirs + core sources to rogue-core target
│       ├── hardware/           # Hardware driver implementations
│       ├── interfaces/         # Interface implementations
│       ├── protocols/          # Protocol implementations
│       └── utilities/          # Utility implementations
├── python/                     # Python packages
│   └── pyrogue/                # High-level Python device tree framework
│       ├── __init__.py         # Package init - imports all core classes
│       ├── __main__.py         # CLI entry point (python -m pyrogue)
│       ├── _Node.py            # Base Node class (tree element)
│       ├── _Device.py          # Device class (Node + memory Hub)
│       ├── _Root.py            # Root class (top-level Device)
│       ├── _Variable.py        # Variable classes (Remote/Local/Link)
│       ├── _Command.py         # Command classes (Local/Remote)
│       ├── _Block.py           # Block transaction helpers
│       ├── _Model.py           # Data type conversion models
│       ├── _PollQueue.py       # Variable polling scheduler
│       ├── _Process.py         # Process management
│       ├── _DataWriter.py      # Stream data writer device
│       ├── _DataReceiver.py    # Stream data receiver device
│       ├── _RunControl.py      # Run control device
│       ├── _HelperFunctions.py # Utility functions (YAML, config)
│       ├── examples/           # Example devices (AxiVersion, ExampleRoot)
│       ├── hardware/           # Hardware-specific Python devices
│       │   └── axi/            # AXI stream DMA monitor
│       ├── interfaces/         # Client/server and simulation interfaces
│       │   ├── _Virtual.py     # Virtual (remote) device tree client
│       │   ├── _ZmqServer.py   # ZMQ server for remote access
│       │   ├── _SimpleClient.py # Simple ZMQ client
│       │   ├── _SqlLogging.py  # SQL-based logging
│       │   ├── _OsCommandMemorySlave.py  # OS command memory slave
│       │   ├── simulation.py   # Simulation support (sideband, stream sim)
│       │   └── stream/         # Stream-level Python utilities (Fifo, Variable)
│       ├── protocols/          # Python protocol wrappers
│       │   ├── _Network.py     # Network protocol stack builder
│       │   ├── _uart.py        # UART protocol
│       │   ├── gpib.py         # GPIB instrument control
│       │   └── epicsV4.py      # EPICS V4 PVA interface
│       ├── pydm/               # PyDM GUI integration
│       │   ├── __init__.py     # PyDM launcher
│       │   ├── data_plugins/   # Rogue data plugin for PyDM
│       │   ├── widgets/        # Custom PyDM widgets (tree, controls, plots)
│       │   ├── tools/          # PyDM tools
│       │   └── examples/       # PyDM example files
│       └── utilities/          # Python utility modules
│           ├── fileio/         # File I/O wrappers (FileReader, StreamReader/Writer)
│           ├── hls/            # HLS register interface parser
│           ├── prbs.py         # PRBS test device
│           └── cpsw.py         # CPSW compatibility layer
├── tests/                      # Test suite
│   ├── test_*.py               # Python pytest test files
│   ├── test_config_in.yml      # Test fixture YAML
│   └── api_test/               # C++ API test
│       └── src/api_test.cpp    # C++ test source
├── templates/                  # Build system templates
│   ├── RogueConfig.h.in        # Version header template
│   ├── RogueConfig.cmake.in    # CMake config template
│   ├── setup.py.in             # Python setup.py template
│   └── setup_rogue.*.in        # Shell setup scripts (sh/csh/fish)
├── conda-recipe/               # Conda build recipe
├── docker/                     # Docker build files
│   ├── rogue/Dockerfile        # Standard build image
│   └── rogue-anaconda/Dockerfile  # Anaconda-based build image
├── docs/                       # Documentation source (RST-based)
├── scripts/                    # Development scripts
│   ├── run_linters.sh          # Lint runner
│   ├── updateDrivers.sh        # Driver update script
│   └── generate_boostpython_api_docs.py  # API doc generator
├── notebooks/                  # Jupyter notebooks
│   └── ExampleRoot.ipynb       # Example root notebook
├── .github/workflows/          # CI configuration
│   └── rogue_ci.yml            # GitHub Actions CI workflow
├── .clang-format               # C++ formatting config
├── .flake8                     # Python linting config
├── CPPLINT.cfg                 # C++ lint config
├── .coveragerc                 # Python coverage config
├── conda.yml                   # Conda environment spec
├── pip_requirements.txt        # Python pip dependencies
└── .gitignore                  # Git ignore rules
```

## Directory Purposes

**`include/rogue/`:**
- Purpose: Public C++ API headers for the rogue-core library
- Contains: Header files organized by subsystem (interfaces, protocols, hardware, utilities)
- Key files: `include/rogue/interfaces/stream/Master.h`, `include/rogue/interfaces/stream/Slave.h`, `include/rogue/interfaces/memory/Master.h`, `include/rogue/interfaces/memory/Slave.h`, `include/rogue/interfaces/memory/Hub.h`, `include/rogue/interfaces/memory/Block.h`, `include/rogue/interfaces/memory/Variable.h`

**`src/rogue/`:**
- Purpose: C++ implementation files for rogue-core, mirrors header structure
- Contains: `.cpp` files organized identically to `include/rogue/`, each directory has its own `CMakeLists.txt`
- Key files: `src/rogue/CMakeLists.txt` (adds subdirectories and core sources to `rogue-core` target)

**`src/` (top-level):**
- Purpose: Python extension module build source
- Contains: `package.cpp` (BOOST_PYTHON_MODULE entry), `CMakeLists.txt` (globs .cpp for `rogue` target)
- Key files: `src/package.cpp`

**`python/pyrogue/`:**
- Purpose: High-level Python framework for building device trees on top of C++ rogue
- Contains: Core tree classes, interface implementations, protocol wrappers, GUI widgets
- Key files: `python/pyrogue/_Root.py`, `python/pyrogue/_Device.py`, `python/pyrogue/_Variable.py`, `python/pyrogue/_Node.py`

**`tests/`:**
- Purpose: Test suite (Python pytest tests and one C++ API test)
- Contains: `test_*.py` files covering memory, variables, commands, protocols, file I/O, EPICS
- Key files: `tests/test_memory.py`, `tests/test_localvars.py`, `tests/test_hub.py`

**`templates/`:**
- Purpose: CMake configure_file templates for version headers, setup scripts, and Python setup.py
- Contains: `.in` files processed during build
- Key files: `templates/RogueConfig.h.in`, `templates/setup.py.in`

## Key File Locations

**Entry Points:**
- `src/package.cpp`: BOOST_PYTHON_MODULE - creates the `rogue` Python extension
- `python/pyrogue/__main__.py`: CLI entry point for `python -m pyrogue`
- `python/pyrogue/__init__.py`: Package initialization, imports all core classes
- `CMakeLists.txt`: Top-level build definition

**Configuration:**
- `CMakeLists.txt`: Build system, dependencies, install targets
- `.clang-format`: C++ code formatting rules
- `.flake8`: Python linting rules
- `CPPLINT.cfg`: C++ linting rules
- `.coveragerc`: Python test coverage config
- `conda.yml`: Conda environment specification
- `pip_requirements.txt`: Python pip dependencies
- `.github/workflows/rogue_ci.yml`: CI pipeline definition

**Core C++ Logic:**
- `include/rogue/interfaces/stream/Master.h` / `src/rogue/interfaces/stream/Master.cpp`: Stream master
- `include/rogue/interfaces/stream/Slave.h` / `src/rogue/interfaces/stream/Slave.cpp`: Stream slave
- `include/rogue/interfaces/stream/Frame.h` / `src/rogue/interfaces/stream/Frame.cpp`: Frame container
- `include/rogue/interfaces/stream/Pool.h` / `src/rogue/interfaces/stream/Pool.cpp`: Buffer pool
- `include/rogue/interfaces/memory/Master.h` / `src/rogue/interfaces/memory/Master.cpp`: Memory master
- `include/rogue/interfaces/memory/Slave.h` / `src/rogue/interfaces/memory/Slave.cpp`: Memory slave
- `include/rogue/interfaces/memory/Hub.h` / `src/rogue/interfaces/memory/Hub.cpp`: Memory hub
- `include/rogue/interfaces/memory/Block.h` / `src/rogue/interfaces/memory/Block.cpp`: Memory block
- `include/rogue/interfaces/memory/Variable.h` / `src/rogue/interfaces/memory/Variable.cpp`: Memory variable
- `include/rogue/interfaces/ZmqServer.h` / `src/rogue/interfaces/ZmqServer.cpp`: ZMQ server

**Core Python Logic:**
- `python/pyrogue/_Node.py`: Base tree node (1007 lines)
- `python/pyrogue/_Variable.py`: Variable classes (2052 lines, largest file)
- `python/pyrogue/_Root.py`: Root device tree node (1195 lines)
- `python/pyrogue/_Device.py`: Device abstraction (942 lines)
- `python/pyrogue/_Model.py`: Data type conversion (828 lines)
- `python/pyrogue/_Command.py`: Command classes (599 lines)
- `python/pyrogue/_Block.py`: Block transaction helpers (534 lines)
- `python/pyrogue/_HelperFunctions.py`: YAML load/save, config utilities (544 lines)

**Testing:**
- `tests/test_*.py`: 18 Python test files
- `tests/api_test/src/api_test.cpp`: C++ API test

## Naming Conventions

**Files:**
- C++ headers: `PascalCase.h` (e.g., `Master.h`, `StreamWriter.h`, `AxiStreamDma.h`)
- C++ sources: `PascalCase.cpp` matching header names
- Python core modules: `_PascalCase.py` with leading underscore (e.g., `_Node.py`, `_Variable.py`, `_Root.py`)
- Python non-core modules: `snake_case.py` (e.g., `simulation.py`, `epicsV4.py`)
- Test files: `test_snake_case.py` (e.g., `test_memory.py`, `test_localvars.py`)

**Directories:**
- C++ namespaces map to directories: `rogue/interfaces/stream/` -> `rogue::interfaces::stream`
- Python packages use lowercase: `pyrogue/`, `interfaces/`, `protocols/`, `utilities/`

**C++ Classes:**
- PascalCase class names: `Master`, `Slave`, `Hub`, `Frame`, `Buffer`, `Pool`
- `*Wrap` suffix for Boost.Python wrapper classes: `SlaveWrap`, `HubWrap`
- `*Ptr` typedef for shared pointers: `MasterPtr`, `SlavePtr`, `FramePtr`

**Python Classes:**
- PascalCase: `Node`, `Device`, `Root`, `BaseVariable`, `RemoteVariable`, `LocalCommand`
- `setup_python()` static method on every C++-exposed class

## Where to Add New Code

**New Hardware Driver:**
- C++ header: `include/rogue/hardware/<subsystem>/<DriverName>.h`
- C++ source: `src/rogue/hardware/<subsystem>/<DriverName>.cpp`
- Add `setup_python()` call in `src/rogue/hardware/<subsystem>/module.cpp`
- Add `target_sources()` in `src/rogue/hardware/<subsystem>/CMakeLists.txt`
- Python device wrapper (if needed): `python/pyrogue/hardware/<subsystem>/`

**New Protocol:**
- C++ header: `include/rogue/protocols/<protocol>/<ClassName>.h`
- C++ source: `src/rogue/protocols/<protocol>/<ClassName>.cpp`
- Add `setup_python()` call in `src/rogue/protocols/<protocol>/module.cpp`
- Add `target_sources()` in `src/rogue/protocols/<protocol>/CMakeLists.txt`
- Python wrapper (if needed): `python/pyrogue/protocols/`

**New Stream Utility:**
- C++ header: `include/rogue/utilities/<ClassName>.h`
- C++ source: `src/rogue/utilities/<ClassName>.cpp`
- Add `setup_python()` call in `src/rogue/utilities/module.cpp`
- Add `target_sources()` in `src/rogue/utilities/CMakeLists.txt`

**New PyRogue Device:**
- Python file: `python/pyrogue/examples/<_DeviceName>.py` (for examples) or a separate downstream package
- Pattern: Subclass `pyrogue.Device`, add `RemoteVariable`/`RemoteCommand`/`LocalVariable` nodes in `__init__`
- Import: Add to `__init__.py` in the containing package

**New PyRogue Interface:**
- Python file: `python/pyrogue/interfaces/_InterfaceName.py`
- Import: Add to `python/pyrogue/interfaces/__init__.py`

**New Test:**
- Python test: `tests/test_<feature>.py`
- Follow existing pattern: import `pyrogue`, create `Root`, add devices, call `root.start()`/`root.stop()` in test setup/teardown

**New PyDM Widget:**
- Python file: `python/pyrogue/pydm/widgets/<widget_name>.py`
- Import: Add to `python/pyrogue/pydm/widgets/__init__.py`

## Special Directories

**`templates/`:**
- Purpose: CMake `configure_file()` input templates for build-time code generation
- Generated: Templates are processed at build time to produce `RogueConfig.h`, `setup.py`, shell setup scripts
- Committed: Yes (input templates are committed; generated outputs are not)

**`docker/`:**
- Purpose: Dockerfile definitions for containerized builds
- Generated: No
- Committed: Yes

**`conda-recipe/`:**
- Purpose: Conda package build recipe (meta.yaml, build.sh)
- Generated: No
- Committed: Yes

**`notebooks/`:**
- Purpose: Jupyter notebooks for interactive examples
- Generated: No (but contains cell outputs)
- Committed: Yes

**`docs/`:**
- Purpose: Documentation source files (RST format for Sphinx/similar)
- Generated: Documentation is built from these sources
- Committed: Yes (source only)

---

*Structure analysis: 2026-03-24*
