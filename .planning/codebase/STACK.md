# Technology Stack

**Analysis Date:** 2026-03-24

## Languages

**Primary:**
- C++ (C++14 standard) - Core library (`src/rogue/`, `include/rogue/`), ~86 `.cpp` source files, ~95 `.h` header files
- Python (>= 3.6, builds target 3.10-3.13) - High-level API, GUI, protocols (`python/pyrogue/`), ~74 `.py` files

**Secondary:**
- CMake - Build system (`CMakeLists.txt`)
- Bash - Build/setup scripts (`scripts/`, `templates/*.sh.in`, `conda-recipe/build.sh`)

## Runtime

**Environment:**
- Linux (primary target, Ubuntu 22.04/24.04 in CI and Docker)
- macOS arm64 (supported via Miniforge/conda, no x86 macOS)
- Python 3.10, 3.11, 3.12, 3.13 (conda variant builds in `conda-recipe/conda_build_config.yaml`)
- C++14 runtime with Boost.Python bridge

**Package Manager:**
- Conda (conda-forge channel, primary distribution method)
- pip (for development/CI dependencies)
- Lockfile: Not present (no `conda-lock.yml` or `requirements.lock`)

## Frameworks

**Core:**
- Boost.Python - C++/Python binding layer, discovered via CMake `find_package(Boost)` in `CMakeLists.txt`
- ZeroMQ (libzmq) - Inter-process messaging, TCP stream bridging, ZMQ server/client in `src/rogue/interfaces/`
- NumPy - Array data type support at the C++ binding layer and Python layer

**GUI:**
- PyDM (>= 1.18.0) - Qt-based display manager for Rogue GUIs (`python/pyrogue/pydm/`)
- PyQt5 (>= 5.15) - Qt bindings required by PyDM

**Testing:**
- pytest (>= 3.6) - Python test runner, configured via `python -m pytest --cov`
- pytest-cov - Coverage plugin
- coverage + codecov - Coverage reporting in CI

**Build/Dev:**
- CMake (>= 3.15) - Primary C++ build system (`CMakeLists.txt`)
- setuptools - Python package installation via generated `setup.py` from `templates/setup.py.in`
- flake8 - Python linting (run via `scripts/run_linters.sh`)
- cpplint - C++ linting with custom config (`CPPLINT.cfg`)
- Sphinx + Breathe + RTD theme - Documentation generation (`docs/`)
- Doxygen - C++ API doc generation (`docs/Doxyfile`)

## Key Dependencies

**Critical (Runtime):**
- `boost` - C++/Python interop, threading; linked via `TARGET_LINK_LIBRARIES` in `CMakeLists.txt`
- `zeromq` (libzmq) - Messaging backbone for ZMQ server/client, TCP stream bridge, simulation sideband
- `numpy` (>= 2.0 for conda builds) - Array data types throughout variable system
- `pyyaml` - Configuration file serialization/deserialization
- `pyzmq` - Python ZeroMQ bindings for `SimpleClient`, `SideBandSim`
- `bzip2` (libbz2) - Compression support in stream utilities (`StreamZip`/`StreamUnZip`)

**Infrastructure (Runtime):**
- `sqlalchemy` - SQL database logging (`python/pyrogue/interfaces/_SqlLogging.py`)
- `p4p` - EPICS PVAccess (PV4) server for control system integration (`python/pyrogue/protocols/epicsV4.py`)
- `pyserial` - Serial/UART communication (`python/pyrogue/protocols/_uart.py`)
- `parse` - String parsing utility
- `click` - CLI argument handling
- `jsonpickle` - Object serialization
- `matplotlib` - Plotting support
- `pydm` (>= 1.18.0) - Qt display manager framework for GUI widgets

**Development Only:**
- `gitpython` - Git operations in scripts
- `pygithub` - GitHub API access in CI/scripts
- `hwcounter` - Hardware performance counters (Linux x86_64 only)
- `ipython` - Interactive shell

## Configuration

**Environment:**
- `ROGUE_DIR` - Root directory for local installs, set by `setup_rogue.sh`
- `CONDA_PREFIX` - Auto-detected for conda installs; controls build type and paths in `CMakeLists.txt`
- `PYTHONPATH` - Must include `python/` directory for local builds (set by generated `setup_rogue.sh`)
- `LD_LIBRARY_PATH` - Must include `lib/` directory for local builds
- `PYQTDESIGNERPATH` - Points to `pyrogue/pydm` for PyDM widget discovery
- `PYDM_DATA_PLUGINS_PATH` - Points to `pyrogue/pydm/data_plugins` for Rogue data plugin
- `PYDM_TOOLS_PATH` - Points to `pyrogue/pydm/tools` for custom PyDM tools
- `ROGUE_SERVERS` - Set at runtime by `pyrogue.pydm.runPyDM()` for GUI server connection

**Build:**
- `CMakeLists.txt` - Main build configuration with options:
  - `-DROGUE_INSTALL={local|conda|system|custom|target_arch}` - Install mode
  - `-DROGUE_DIR=<path>` - Custom install path
  - `-DNO_PYTHON=1` - Build without Python/Boost bindings
  - `-DSTATIC_LIB=1` - Also build static library
  - `-DROGUE_VERSION=<ver>` - Override version (defaults to `git describe`)
- `CPPLINT.cfg` - C++ lint settings (linelength=250, filters for c++11 headers, include order, header guard, whitespace)
- `templates/RogueConfig.h.in` - Generated version header
- `templates/setup.py.in` - Generated Python package setup with PEP 440 version normalization
- `conda-recipe/meta.yaml` - Conda package recipe
- `conda-recipe/conda_build_config.yaml` - Python version variants (3.10-3.13)

## Platform Requirements

**Development:**
- Linux (Ubuntu 22.04+) or macOS arm64
- CMake >= 3.15
- C/C++ compiler (gcc or clang with C++14 support)
- Boost libraries with Python component
- ZeroMQ (libzmq3-dev on Debian/Ubuntu)
- BZip2 (libbz2-dev)
- Python 3.10+ with development headers
- NumPy with C headers
- Git (required for version generation)

**Production/Deployment:**
- Conda package distributed via `tidair-tag` channel on conda-forge
- Docker images: `docker/rogue/Dockerfile` (Ubuntu 22.04 base), `docker/rogue-anaconda/Dockerfile` (Miniforge base)
- For hardware access: Linux with SLAC `aes-stream-drivers` kernel module (e.g., `datadev`, `axi_memory_map`)

**CI/CD:**
- GitHub Actions (`rogue_ci.yml`)
- Runs on `ubuntu-24.04` and `macos-15` (arm64)
- Reusable workflows from `slaclab/ruckus` for release generation, conda build, and Docker build
- Secrets: `GH_TOKEN` (GitHub), `CONDA_UPLOAD_TOKEN_TAG` (Anaconda upload)

---

*Stack analysis: 2026-03-24*
