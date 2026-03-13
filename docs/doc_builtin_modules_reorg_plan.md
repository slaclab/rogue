# Built-In Modules Documentation Reorganization Plan

Use this file as the working plan and progress tracker for the built-in module
documentation reorganization. Keep it updated as decisions are made and pages
are rewritten so the work can continue cleanly across context windows.

## Goal

Organize the built-in module documentation so it helps readers:

- Discover what exists.
- Choose the right object or module for a task.
- Understand how the `pyrogue.*` and `rogue.*` namespaces relate.

The layout should support discovery first, while still building a clear mental
map of the namespace hierarchy.

## Namespace Model

The documentation should teach these layers explicitly:

1. `pyrogue`
   Top-level tree framework and top-level tree-facing classes.
2. `pyrogue.<submodule>`
   Python integrations and wrapper devices below the top-level namespace.
3. `rogue.<submodule>`
   Lower-level exported Rogue modules and endpoints.

## Documentation Patterns

### Pattern A: Top-Level PyRogue Class

Use for:

- `pyrogue.RunControl`
- `pyrogue.Process`
- `pyrogue.DataWriter`
- `pyrogue.DataReceiver`

Recommended order:

1. What it is
2. When to use it
3. What you usually set
4. Subclassing / lifecycle / behavior
5. Example
6. Related lower-level modules if relevant

### Pattern B: Module With A Common PyRogue Wrapper

Use for:

- `utilities/fileio`
- `utilities/prbs`
- `protocols/network`

Recommended order:

1. Start with the most common user-facing entry point
2. Name the underlying Rogue utility immediately
3. Explain how the wrapper changes the usage model
4. Show the common wrapper example first when that is the usual entry point
5. Show the direct Rogue utility form after that
6. Keep lower-level mechanics clearly separated

### Pattern C: Direct Rogue Module

Use for:

- `protocols/udp`
- `protocols/rssi`
- `protocols/srp`
- `protocols/packetizer`
- `protocols/batcher`
- `protocols/xilinx`
- `utilities/compression`
- `hardware/*`

Recommended order:

1. What the Rogue module does
2. How it fits in the stream or memory topology
3. Key classes
4. Python example
5. C++ example
6. PyRogue integration only when it is genuinely helpful

### Pattern D: Pure Python Integration Helper

Use for:

- `interfaces/sql`
- `interfaces/os_memory_bridge`
- `protocols/gpib`
- `protocols/epicsV4`
- `protocols/uart`
- `simulation/*`
- `utilities/hls/*`

Recommended order:

1. What the helper does
2. Where it lives in the namespace
3. How it integrates with Rogue or PyRogue
4. Workflow or example
5. Limitations and operational notes

## Inventory And Classification

### Top-Level PyRogue Built-Ins

These belong in `pyrogue_tree`.

| Area | Primary Objects | Type |
|---|---|---|
| Tree built-ins | `pyrogue.RunControl` | Python only |
| Tree built-ins | `pyrogue.Process` | Python only |
| Tree built-ins | `pyrogue.DataWriter` | Python only |
| Tree built-ins | `pyrogue.DataReceiver` | Python only |

### Built-In Modules: Hardware

| Area | Primary Objects | Type |
|---|---|---|
| Hardware DMA stream | `rogue.hardware.axi.AxiStreamDma` | C++ only |
| Hardware DMA memory | `rogue.hardware.axi.AxiMemMap` | C++ only |
| Hardware raw memory | `rogue.hardware.MemMap` | C++ only |

### Built-In Modules: Interfaces

| Area | Primary Objects | Type |
|---|---|---|
| SQL | `pyrogue.interfaces.SqlLogger`, `SqlReader` | Python only |
| OS memory bridge | `pyrogue.interfaces.OsCommandMemorySlave` | Python only |
| Version | `rogue.Version` | C++ only |
| C++ API wrapper | conceptual guide | not a builtin module class |

### Built-In Modules: Simulation

| Area | Primary Objects | Type |
|---|---|---|
| Memory emulation | `pyrogue.interfaces.simulation.MemEmulate` | Python only |
| PGP2B simulation | `pyrogue.interfaces.simulation.Pgp2bSim`, `SideBandSim` | Python only |

### Built-In Modules: Protocols

| Area | Primary Objects | Type |
|---|---|---|
| UDP | `rogue.protocols.udp.Client`, `Server`, `Core` | C++ only |
| RSSI | `rogue.protocols.rssi.*` | C++ only |
| SRP | `rogue.protocols.srp.*` | C++ only |
| Packetizer | `rogue.protocols.packetizer.*` | C++ only |
| Batcher | `rogue.protocols.batcher.*` | C++ only |
| Xilinx | `rogue.protocols.xilinx.*` | C++ only |
| Network bundle | `pyrogue.protocols.UdpRssiPack` | C++ with Python `Device` wrapper |
| GPIB | `pyrogue.protocols.GpibController`, `GpibDevice` | Python only |
| EPICS V4 | `pyrogue.protocols.epicsV4.*` | Python only |
| UART | `pyrogue.protocols.UartMemory` | Python only |

### Built-In Modules: Utilities

| Area | Primary Objects | Type |
|---|---|---|
| File I/O core | `rogue.utilities.fileio.StreamWriter`, `StreamReader` | C++ only |
| File I/O tree wrappers | `pyrogue.utilities.fileio.StreamWriter`, `StreamReader` | C++ with Python `Device` wrapper |
| File I/O offline reader | `pyrogue.utilities.fileio.FileReader` | Python only |
| PRBS core | `rogue.utilities.Prbs` | C++ only |
| PRBS tree wrappers | `pyrogue.utilities.prbs.PrbsTx`, `PrbsRx`, `PrbsPair` | C++ with Python `Device` wrapper |
| Compression | `rogue.utilities.StreamZip`, `StreamUnZip` | C++ only |
| HLS parser | `pyrogue.utilities.hls._RegInterfParser` | Python only |

## Execution Plan

### Phase 1: Restructure Index Pages

Status: `completed`

- [x] `docs/src/built_in_modules/index.rst`
- [x] `docs/src/built_in_modules/utilities/index.rst`
- [x] `docs/src/built_in_modules/protocols/index.rst`
- [x] `docs/src/built_in_modules/interfaces/index.rst`
- [x] `docs/src/built_in_modules/hardware/index.rst`

Goals:

- Make the namespace hierarchy legible at the index level.
- Distinguish exported Rogue modules, pure Python integrations, and Python
  wrappers around Rogue modules.
- Improve discovery before readers land on leaf pages.

### Phase 2: Normalize Mixed Wrapper/Core Families

Status: `in_progress`

- [ ] `docs/src/built_in_modules/utilities/fileio/index.rst`
- [ ] `docs/src/built_in_modules/utilities/fileio/writing.rst`
- [ ] `docs/src/built_in_modules/utilities/fileio/reading.rst`
- [ ] `docs/src/built_in_modules/utilities/prbs/index.rst`
- [ ] `docs/src/built_in_modules/utilities/prbs/writing.rst`
- [ ] `docs/src/built_in_modules/utilities/prbs/reading.rst`
- [ ] `docs/src/built_in_modules/protocols/network.rst`

Goals:

- Start from the common user-facing entry point.
- Name the underlying Rogue utility immediately.
- Keep wrapper behavior and lower-level utility behavior distinct.

### Phase 3: Normalize Direct Rogue Module Families

Status: `pending`

- [ ] `docs/src/built_in_modules/protocols/udp/*`
- [ ] `docs/src/built_in_modules/protocols/rssi/*`
- [ ] `docs/src/built_in_modules/protocols/srp/*`
- [ ] `docs/src/built_in_modules/protocols/packetizer/*`
- [ ] `docs/src/built_in_modules/protocols/batcher/*`
- [ ] `docs/src/built_in_modules/protocols/xilinx/*`
- [ ] `docs/src/built_in_modules/utilities/compression/*`
- [ ] `docs/src/built_in_modules/hardware/*`

Goals:

- Keep these pages `rogue.*`-first.
- Explain topology and key classes clearly.
- Mention PyRogue integration only when useful.

### Phase 4: Normalize Pure Python Integration Families

Status: `pending`

- [ ] `docs/src/built_in_modules/interfaces/sql.rst`
- [ ] `docs/src/built_in_modules/interfaces/os_memory_bridge.rst`
- [ ] `docs/src/built_in_modules/protocols/gpib.rst`
- [ ] `docs/src/built_in_modules/protocols/epicsV4/*`
- [ ] `docs/src/built_in_modules/protocols/uart.rst`
- [ ] `docs/src/built_in_modules/simulation/*`
- [ ] `docs/src/built_in_modules/utilities/hls/*`

Goals:

- Describe what the Python helper does.
- Show how it integrates with Rogue or PyRogue.
- Avoid forcing a wrapper/core split when none exists.

### Phase 5: Cross-Section Consistency Pass

Status: `pending`

- [ ] Verify `pyrogue_tree` only owns top-level `pyrogue` classes
- [ ] Verify `built_in_modules` owns submodule APIs and wrapper families
- [ ] Check cross-links between `pyrogue_tree` and `built_in_modules`
- [ ] Remove any remaining bolted-on wrapper-note sections
- [ ] Remove repeated intro text and other narrative drift

## Recommended Working Order

1. `docs/src/built_in_modules/index.rst`
2. `docs/src/built_in_modules/utilities/index.rst`
3. `docs/src/built_in_modules/protocols/index.rst`
4. `docs/src/built_in_modules/interfaces/index.rst`
5. `docs/src/built_in_modules/hardware/index.rst`
6. `docs/src/built_in_modules/utilities/fileio/*`
7. `docs/src/built_in_modules/utilities/prbs/*`
8. `docs/src/built_in_modules/protocols/network.rst`
9. Direct Rogue protocol families
10. Pure Python helper families
11. Final consistency pass

## Current Decisions

- `pyrogue_tree/builtin_devices` should be limited to classes exposed in the
  top-level `pyrogue` namespace.
- Submodule wrappers such as `pyrogue.utilities.fileio.*` and
  `pyrogue.utilities.prbs.*` belong under `built_in_modules`.
- Discovery should come before implementation layering in page organization,
  but the namespace and wrapper relationships should still be made explicit
  early in each page.
- Avoid meta phrasing such as "this section covers", "this area covers", or
  "most readers start here if...".

## Progress Notes

Use this section to record real state changes as the work moves forward.

- `2026-03-13`: Created the execution plan and inventory file.
- `2026-03-13`: Confirmed that mixed wrapper/core families are concentrated in
  `utilities/fileio`, `utilities/prbs`, and `protocols/network`.
- `2026-03-13`: Confirmed that top-level `pyrogue` built-ins are limited to
  `RunControl`, `Process`, `DataWriter`, and `DataReceiver`.
- `2026-03-13`: Rewrote the built-in-modules landing pages for `index`,
  `utilities`, `protocols`, `interfaces`, and `hardware` so they now present
  the `pyrogue` vs `pyrogue.<submodule>` vs `rogue.<submodule>` split
  explicitly and guide readers by discovery-first subsections.

## Context-Handoff Notes

When continuing this work in a new context window:

1. Read `docs/doc_merge_guidelines.md`.
2. Read this file.
3. Continue from the first unchecked item in the current phase unless a newer
   note in `Progress Notes` says otherwise.
4. Update phase status and checkboxes as soon as a page cluster is completed.
