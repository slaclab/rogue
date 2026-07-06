# Rogue Development Guide

This guide is the project-level orientation for people and AI agents working
on Rogue. It is intentionally tool-agnostic: any assistant or developer can
read it at the start of a fresh context window to understand what Rogue is,
where code lives, and what conventions changes should follow.

For test-specific guidance, also read `tests/METHODOLOGY.md`.

## Project Purpose

Rogue is a mixed C++/Python framework for hardware abstraction and data
acquisition applications. It provides reusable building blocks for:

- High-throughput streaming data paths.
- Register and memory-mapped control paths.
- Hierarchical device trees for hardware control applications.
- Python orchestration around performance-critical C++ components.
- Integration with GUI, file I/O, protocol, and control-system tooling.

Most application code is written through the Python-facing PyRogue tree model.
Performance-sensitive transport, memory, protocol, and utility paths are
implemented in C++ and exposed into Python through Boost.Python bindings.

## First Files To Read

For a new task, start with these files:

- `README.md`: release-user overview and install links.
- `DEVELOPMENT.md`: this guide.
- `tests/METHODOLOGY.md`: how to choose and write tests.
- `.github/workflows/rogue_ci.yml`: CI build/test matrix.
- Nearby `CMakeLists.txt` files for the subsystem you are editing.
- Existing tests in the nearest `tests/` or `tests/cpp/` directory.

Do not stage files or make commits unless explicitly asked.

## Repository Layout

Top-level areas:

- `include/`: public C++ headers installed for downstream users.
- `src/`: C++ implementations and Boost.Python binding registration.
- `python/`: Python package sources, primarily `pyrogue`.
- `tests/`: pytest suites, native C++ doctest suites, and test guidance.
- `docs/`: Sphinx and Doxygen documentation sources and publishing helpers.
- `scripts/`: linting, documentation, and performance-publishing utilities.
- `.github/workflows/`: CI workflows for Linux, macOS, docs, and perf jobs.
- `docs/plans/`: planning, progress, handoff, and decision notes for
  substantial feature work.
- `conda.yml`, `pip_requirements*.txt`, `conda-recipe/`, `docker/`:
  environment, packaging, and container support.

C++ subsystem layout is mirrored between `include/rogue/...` and
`src/rogue/...`:

- `interfaces/stream`: frame, pool, master/slave, FIFO, filter, rate drop,
  and TCP stream transport.
- `interfaces/memory`: transaction, block, variable, hub/master/slave,
  emulation, model, and TCP memory transport.
- `interfaces/api`: C++ API helper classes.
- `interfaces`: ZMQ client/server and shared interface utilities.
- `protocols`: UDP, RSSI, SRP, packetizer, batcher, and Xilinx XVC support.
- `hardware`: raw memory map and AXI hardware access paths.
- `utilities`: file I/O, PRBS, compression, and support utilities.

Python layout under `python/pyrogue/`:

- Core tree classes live in files such as `_Node.py`, `_Device.py`,
  `_Root.py`, `_Variable.py`, `_Command.py`, and `_Block.py`.
- `interfaces/`, `protocols/`, `hardware/`, and `utilities/` provide Python
  wrappers, application helpers, and higher-level integration modules.
- `pydm/` contains PyDM data plugins, widgets, and tools.
- `examples/` contains user-facing examples.

Generated and local-only outputs:

- `build/`, docs build outputs, caches, virtual environments, and local editor
  state are not source of truth.
- Update templates and source inputs, not generated outputs, unless the
  generated output is intentionally tracked by the repository.
- Do not rely on files produced by a previous local build when explaining or
  validating a change; rebuild or reconfigure when the generated state matters.

## Agent Work Records

For substantial feature work that may span multiple context windows, keep
agent-generated planning and handoff notes under
`docs/plans/<task-name>/`.

Use these files to preserve working context:

- `PLAN.md`: scope, assumptions, affected subsystems, intended approach, and
  validation plan.
- `PROGRESS.md`: completed work, commands run, results, blockers, and open
  questions.
- `HANDOFF.md`: current state, remaining tasks, risks, verification gaps, and
  exact next steps.
- `DECISIONS.md`: important tradeoffs or design decisions.

Keep these notes concise and factual. Do not store secrets, raw logs, or local
environment noise. When work completes, either keep useful durable notes or
move the important information into permanent docs, tests, comments, issues, or
PR text.

## Architecture

Rogue has two major public layers:

- C++ `rogue` namespace: fast transport, memory, protocol, and utility
  implementations. These classes often own worker threads, ZMQ sockets,
  frame buffers, memory transactions, or file handles.
- Python `pyrogue` package: tree construction, device orchestration,
  variables, commands, polling, logging integration, GUI helpers, and
  application-level workflow.

Important concepts:

- A PyRogue system is a tree rooted at `pyrogue.Root`.
- `Device` objects contain variables, commands, child devices, and optional
  memory interfaces.
- `RemoteVariable` and memory blocks map Python access into C++ memory
  transactions.
- Stream interfaces connect producers and consumers of frame data.
- Memory interfaces connect masters, slaves, hubs, blocks, and emulators for
  register/memory access.
- Protocol modules sit on top of stream or memory primitives.
- Python bindings expose selected C++ classes into the `rogue` Python module.

When changing behavior, identify the layer where the contract lives. A bug in
Python tree semantics usually belongs in `python/pyrogue` plus pytest coverage.
A transport, memory, protocol, or threading bug usually needs C++ changes and
native C++ or integration coverage.

## Public API Changes

Treat public Python APIs, installed C++ headers, and Boost.Python-exposed C++
classes as downstream contracts. Before changing one, check existing docs,
tests, examples, and naming patterns.

When adding or changing a Python-exposed C++ API, update the full path:

- Public header in `include/rogue/...`.
- Implementation in `src/rogue/...`.
- `setup_python()` binding in the implementation file.
- Submodule registration in the nearest `module.cpp` if a new class or module
  is introduced.
- `#ifndef NO_PYTHON` guards for Python-only code.
- Python API docs or C++ API docs, depending on the exposed surface.
- Tests for both the native behavior and Python-visible behavior when both are
  part of the contract.

Prefer additive changes for established user-facing APIs. If a breaking change
is unavoidable, document the migration path and update release or migration
notes in the docs tree when appropriate.

## Build Environments

The preferred local development environment is a Miniforge-managed conda
environment. Use a dedicated `rogue_build` environment, build in the
repo-local `build/` tree, and run tests against that same build.

Set up or refresh the environment from `conda.yml`:

```sh
source "${MINIFORGE_HOME:-$HOME/miniforge3}/etc/profile.d/conda.sh"
mamba env update -n rogue_build -f conda.yml
conda activate rogue_build
```

If the shell is not activated, use `conda run -n rogue_build <command>` for the
same commands.

Common CMake options:

- `-DROGUE_INSTALL=local`: install into the repository tree.
- `-DROGUE_INSTALL=conda`: install into the active conda environment.
- `-DROGUE_BUILD_TESTS=ON`: build native C++ tests under `tests/cpp`.
- `-DNO_PYTHON=1 -DSTATIC_LIB=1`: small static no-Python build.
- `-DNO_ROCEV2=ON`: build without RoCEv2 / `libibverbs` (Linux). Skips ibverbs
  discovery and linking and excludes the `rocev2` sources, so `rdma-core` is not
  required. For cross-compiled / packaged builds that do not need RoCEv2.
- `-DROGUE_SKIP_PIP_INSTALL=ON`: with `-DROGUE_INSTALL=system` (or `conda`), still
  install the C++ libraries, headers, and `RogueConfig.cmake`, but skip the
  cmake-driven `pip install` of the Python package. For packaging systems
  (Yocto `setuptools3`, distro `%py_install`, etc.) that stage the Python package
  into `DESTDIR` themselves.

For day-to-day local builds, use one of two modes:

- Fast repo-local build: configure with `-DROGUE_INSTALL=local`, build in
  `build/`, and source `build/setup_rogue.sh` before running local commands.
- Conda install build: configure with `-DROGUE_INSTALL=conda`, build, then
  install into the active `rogue_build` environment. Use this when validating
  the installed package shape or docs/autodoc behavior.

Typical Python-enabled local build with native C++ tests enabled:

```sh
cmake -S . -B build -DROGUE_INSTALL=local -DROGUE_BUILD_TESTS=ON
cmake --build build -j$(nproc)
cmake --build build --target install
source build/setup_rogue.sh
```

Use `$(sysctl -n hw.ncpu)` on macOS, `$(nproc)` on Linux, or a portable helper
such as `$(sysctl -n hw.ncpu 2>/dev/null || getconf _NPROCESSORS_ONLN)`.

When running Python tests against local source, source the build environment
and put the repo's Python tree first:

```sh
source build/setup_rogue.sh
export PYTHONPATH="${PWD}/python:${PYTHONPATH}"
```

For validation, prefer this progression:

- Build first.
- Run the narrow pytest path for the changed subsystem, or the fast marker
  selection for broad Python changes.
- Run integration or perf tests only when the change touches those behaviors.
- Build docs from `docs/` with `make clean html` when docs, public APIs, or
  autodoc inputs change.

Use the same build tree for configure, build, install, pytest, and ctest.
Switching install modes or Python/no-Python modes usually requires
reconfiguring CMake.

## CI Expectations

The main CI workflow is `.github/workflows/rogue_ci.yml`.

CI enforces:

- No trailing whitespace or tab characters in `*.cpp`, `*.h`, and `*.py`
  files, excluding vendored doctest.
- Python compile checks and flake8 through `scripts/run_linters.sh`.
- cpplint for C++ headers and sources.
- Linux full build with Python enabled and `-DROGUE_BUILD_TESTS=ON`.
- Linux small build with `-DNO_PYTHON=1 -DSTATIC_LIB=1`.
- macOS arm64 build with Python enabled.
- Native C++ tests through ctest labels.
- Python pytest suites, excluding perf in the main build jobs.
- Separate performance tests and perf result publishing.

Choose local verification based on the changed surface. For shared C++ code,
consider both Python-enabled and no-Python build paths when the code is
compiled into both.

## Coding Style

General expectations:

- Preserve the existing file and subsystem style.
- Keep changes scoped to the behavior requested.
- Do not reformat unrelated code.
- Avoid trailing whitespace and tab characters.
- Prefer clear, direct implementation over new abstractions unless an
  abstraction removes real duplication or matches an existing local pattern.
- Prefer behavior-focused comments. Avoid comments that restate obvious code.
- Keep public behavior documented where users or downstream code will rely on
  it.

License/header conventions:

- C++ and Python source files generally carry the SLAC/Rogue license header.
- New files should match the header style of neighboring files in the same
  subsystem.
- Do not edit vendored files unless the task is explicitly about vendored code.

## C++ Conventions

Rogue C++ is built with CMake and currently uses C++14 configuration while
supporting older idioms in much of the codebase. Follow neighboring style.

Public headers:

- Live under `include/rogue/...`.
- Use the existing include guard style in that tree.
- Include `rogue/Directives.h` near the top when neighboring headers do.
- Document public classes and methods with Doxygen comments.
- Keep public API changes intentional; downstream users may compile against
  these headers.

Implementations:

- Live under matching `src/rogue/...` paths.
- Prefer namespace aliases already used in the file, such as
  `namespace rim = rogue::interfaces::memory`.
- Use `rogue::GeneralError` for Rogue-specific runtime errors.
- Use `rogue::Logging` for component logging instead of ad hoc stdout output.
- Use `std::shared_ptr` factories named `create()` when matching existing
  Rogue pointer ownership patterns.
- Keep Python binding code behind `#ifndef NO_PYTHON`.
- Add or update `setup_python()` bindings when changing Python-exposed C++
  APIs.

Thread/resource lifecycle:

- Be explicit about ownership of threads, sockets, buffers, file descriptors,
  and contexts.
- Make destructors and `stop()`/`close()` paths idempotent where callers may
  invoke them repeatedly.
- Join worker threads before destruction.
- Release resources on constructor failure before rethrowing.
- Use `std::atomic` or another explicit synchronization mechanism for flags
  shared with worker threads.
- Release the Python GIL around blocking joins or operations that can wait on
  Python-facing worker paths.

No-Python builds:

- Code compiled under `-DNO_PYTHON=1` must not depend on Python, NumPy, or
  Boost.Python symbols.
- Guard Python-only includes, methods, and test registration with
  `#ifndef NO_PYTHON`.

Avoid source-audit tests:

- Do not add C++ tests that read production source files and assert on source
  text.
- Prefer behavioral tests, focused fakes, sanitizers, Valgrind, or dedicated
  static-analysis tooling outside the normal unit test suite.

## Python Conventions

Python code is primarily user-facing. Maintain compatibility with the package
style already present in `python/pyrogue`.

Style expectations:

- Use explicit imports near the top of the file.
- Prefer type hints for new or substantially edited public functions.
- Use NumPy-style docstrings for public classes, methods, and functions.
- Keep object lifetimes explicit, especially for `Root`, interface, and
  background-thread objects.
- Use logging for operational messages; avoid noisy prints in library code.
- Preserve public method names and keyword defaults unless intentionally
  changing the API.
- Add or update `@pr.expose` only when the method should be exposed through
  the Rogue/PyRogue interface layer.

PyRogue tree conventions:

- Use `Root` as a context manager in tests and examples when lifecycle matters.
- Add devices, variables, commands, and interfaces through existing `add()`
  and `addInterface()` patterns.
- Keep memory emulation local for deterministic tests and examples.
- Use update groups when batching related variable updates.
- Keep listener and polling behavior thread-safe.

Compatibility:

- Do not assume optional runtime integrations are installed unless the module
  already requires them.
- Optional docs imports are mocked in `docs/src/conf.py`; runtime code should
  still handle optional dependencies deliberately.

## Documentation Conventions

User documentation lives under `docs/src/` and is built with Sphinx. C++ API
documentation also uses Doxygen/Breathe integration.

Documentation sources:

- `docs/src/index.rst`: documentation landing page and main toctree.
- `docs/src/api/python/...`: Python API pages.
- `docs/src/api/cpp/...`: C++ API pages.
- `docs/src/migration/...`: user-facing migration notes for behavioral or API
  changes that require downstream action.
- `docs/src/_ext/`: custom Sphinx extensions for Boost.Python and C++ source
  links.
- `docs/README.md`: notes for docs generation helpers.
- `docs/plans/`: repo-local planning, progress, handoff, and decision notes
  for substantial feature work.

When changing public APIs:

- Update Python docstrings or C++ Doxygen comments.
- Add or update RST pages when adding a public module, class, or major
  workflow.
- Keep examples executable in principle; avoid snippets that depend on hidden
  local state.
- Prefer concise explanations of user-facing behavior, parameters, lifecycle,
  and failure modes.

Build docs locally from the docs directory:

```sh
cd docs
make clean html
```

The docs build prefers the source-tree Python package over installed copies.

## Test Conventions

Read `tests/METHODOLOGY.md` before adding tests.

Short version:

- Add the narrowest deterministic test that proves the behavior.
- Use pytest for Python/PyRogue behavior.
- Use doctest/ctest for native C++ behavior.
- Use integration markers for real sockets, transports, or multi-component
  workflows.
- Use perf markers for throughput, rate, soak, or host-sensitive checks.
- Label C++ tests correctly for `cpp`, `cpp-core`, `no-python`,
  `requires-python`, and `smoke` behavior.
- Do not add source-audit tests.

Common commands:

```sh
python -m pytest -m "not integration and not epics and not perf" -q
python -m pytest tests/core -q
python -m pytest tests/integration -q
ctest --test-dir build --output-on-failure -L cpp
ctest --test-dir build --output-on-failure -L no-python
```

## Dependency And Packaging Notes

Rogue supports conda and pip-oriented dependency flows:

- `conda.yml`: conda environment used by local and macOS CI workflows.
- `pip_requirements.txt`: broad runtime/test dependency set.
- `pip_requirements_ci.txt`: CI dependency set.
- `pip_requirements_docs.txt`: docs dependency set.
- `conda-recipe/`: conda packaging recipe.
- `templates/setup.py.in`: generated Python package setup template.

When adding dependencies:

- Prefer existing dependency groups.
- Keep optional GUI/control-system dependencies optional when practical.
- Update CI, docs, and packaging files together if a dependency becomes
  required.
- Avoid adding heavy runtime dependencies for narrow helper behavior.

When changing packaging behavior:

- Keep conda, pip, and CMake install paths aligned.
- Prefer editing package templates and recipes over generated install outputs.
- Verify imports from the installed environment when package layout changes.
- Be careful with version behavior; release tags, CMake configuration, Python
  package metadata, and docs all consume Rogue version information.

### CMake dependency-block sync

`CMakeLists.txt` and `templates/RogueConfig.cmake.in` intentionally duplicate the
dependency-discovery logic (Boost + Python, numpy, BZip2, ZeroMQ): the top-level
file uses it to build rogue, while the installed `RogueConfig.cmake` re-runs it so
downstream `find_package(Rogue)` consumers rediscover the same dependencies. The
duplicated region is delimited in both files by sentinel comments:

```
# >>> ROGUE_DEPENDENCY_DISCOVERY ...
...
# <<< ROGUE_DEPENDENCY_DISCOVERY
```

The lines between these markers must stay **byte-identical** in both files. Mirror
any edit to the dependency block into both. `scripts/check_cmake_sync.sh` enforces
this and runs as part of `scripts/run_linters.sh` in CI, failing the build on drift.

## Change Workflow

Use this workflow for most tasks:

1. Read the nearby code and tests before editing.
2. Identify whether the contract is C++, Python, docs, tests, packaging, or a
   cross-layer behavior.
3. For substantial feature work, create or update
   `docs/plans/<task-name>/PLAN.md`.
4. Make the smallest coherent change in the owning subsystem.
5. For public API changes, update bindings, docs, examples, and compatibility
   notes as needed.
6. Update public docs or docstrings when user-facing behavior changes.
7. Add or update focused tests following `tests/METHODOLOGY.md`.
8. Run the narrowest useful command first.
9. Expand verification to the closest CI-equivalent command when risk warrants.
10. Update `PROGRESS.md` or `HANDOFF.md` when the work spans context windows.
11. Leave unrelated files untouched.
12. Do not stage or commit unless explicitly asked.

## Pull Requests

Open pull requests against `pre-release` unless the user explicitly requests a
different base branch. Use `.github/pull_request_template.md` for PR
descriptions, keeping the release-note-facing `Description` section clean and
readable.

## Agent Checklist

At the start of a new AI-agent context window:

1. Read this file.
2. Read `tests/METHODOLOGY.md` for any change that may need tests.
3. Check `git status --short --branch`.
4. Inspect the files and tests nearest the requested change.
5. For substantial feature work, check `docs/plans/` for an existing
   feature plan or handoff.
6. Preserve user changes already present in the worktree.
7. Avoid broad rewrites and unrelated cleanup.
8. Report commands run and any verification gaps.

When uncertain, prefer the established local pattern over inventing a new one.
