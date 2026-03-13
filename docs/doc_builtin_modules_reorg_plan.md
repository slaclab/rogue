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

1. Start with the use case or workflow the wrapper serves
2. Name the underlying Rogue utility immediately
3. Explain how the wrapper changes the usage model
4. Use `Key Constructor Arguments` when the wrapper is mainly chosen at
   construction time; use `Common Controls` when runtime settings matter more
5. Show the common wrapper example first when that is the usual form in real use
6. Show the direct Rogue utility form after that
7. Keep lower-level mechanics clearly separated

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

Status: `completed`

- [x] `docs/src/built_in_modules/utilities/fileio/index.rst`
- [x] `docs/src/built_in_modules/utilities/fileio/writing.rst`
- [x] `docs/src/built_in_modules/utilities/fileio/reading.rst`
- [x] `docs/src/built_in_modules/utilities/prbs/index.rst`
- [x] `docs/src/built_in_modules/utilities/prbs/writing.rst`
- [x] `docs/src/built_in_modules/utilities/prbs/reading.rst`
- [x] `docs/src/built_in_modules/protocols/network.rst`

Goals:

- Start from the common user-facing entry point.
- Name the underlying Rogue utility immediately.
- Keep wrapper behavior and lower-level utility behavior distinct.

### Phase 3: Normalize Direct Rogue Module Families

Status: `completed`

- [x] `docs/src/built_in_modules/protocols/udp/*`
- [x] `docs/src/built_in_modules/protocols/rssi/*`
- [x] `docs/src/built_in_modules/protocols/srp/*`
- [x] `docs/src/built_in_modules/protocols/packetizer/*`
- [x] `docs/src/built_in_modules/protocols/batcher/*`
- [x] `docs/src/built_in_modules/protocols/xilinx/*`
- [x] `docs/src/built_in_modules/utilities/compression/*`
- [x] `docs/src/built_in_modules/hardware/*`

Goals:

- Keep these pages `rogue.*`-first.
- Explain topology and key classes clearly.
- Mention PyRogue integration only when useful.

Progress Notes:

- `protocols/udp/*` now frames UDP as the transport layer commonly used under
  RSSI and packetizer, with `Client` as the common FPGA-facing form and
  `Server` as the less common peer-facing form.
- `protocols/rssi/*` had a follow-up recovery pass to restore threading and
  lifecycle details, including controller ownership, application worker-thread
  behavior, and standalone `_start()` / `_stop()` guidance.
- `protocols/srp/*` now keeps SRP focused on the memory-to-stream bridge role,
  with `SrpV3` as the preferred current protocol and `Cmd` separated as the
  fire-and-forget opcode path.
- `protocols/packetizer/*` had a second merge-quality rewrite to restore the
  fuller protocol overview, v1/v2 comparison, Python examples, and C++
  examples that were getting compressed away.
- `protocols/batcher/*` had a second merge-quality rewrite to restore the
  parser-core model, stronger splitter vs inverter guidance, and both Python
  and C++ examples.
- `protocols/xilinx/*` had a second merge-quality rewrite to restore workflow
  explanation, `JtagDriver` details, and both standalone and `Root`-based
  examples in Python and C++.
- `utilities/compression/*` had a second merge-quality rewrite to restore the
  fuller pipeline explanation, synchronous behavior notes, and both Python and
  C++ examples.
- `hardware/dma/*` and `hardware/raw/index.rst` needed follow-up corrections
  for style, complete examples, and hardware-specific mechanics such as
  `aes-stream-drivers`, zero-copy DMA behavior, and `dest` mapping.

### Phase 4: Normalize Pure Python Integration Families

Status: `completed`

- [x] `docs/src/built_in_modules/interfaces/sql.rst`
- [x] `docs/src/built_in_modules/interfaces/os_memory_bridge.rst`
- [x] `docs/src/built_in_modules/protocols/gpib.rst`
- [x] `docs/src/built_in_modules/protocols/epicsV4/*`
- [x] `docs/src/built_in_modules/protocols/uart.rst`
- [x] `docs/src/built_in_modules/simulation/*`
- [x] `docs/src/built_in_modules/utilities/hls/*`

Goals:

- Describe what the Python helper does.
- Show how it integrates with Rogue or PyRogue.
- Avoid forcing a wrapper/core split when none exists.

Progress Notes:

- `interfaces/sql.rst` now explains `SqlLogger` as a managed `Root` interface,
  keeps the focus on the actual logging workflow, and treats `SqlReader` as a
  lightweight schema helper rather than a fuller query layer.
- `interfaces/os_memory_bridge.rst` now keeps the bridge pattern focused on
  command-backed memory transactions and the `OsMemMaster` example pairing,
  with clearer mapping rules and same-subsection navigation.
- `protocols/gpib.rst` and `protocols/uart.rst` now describe these helpers as
  pure Python transaction adapters, foregrounding host dependencies, mapping
  behavior, and operational limits instead of reading like thin API notes.
- `protocols/epicsV4/*` now presents the server/holder relationship as one
  coherent publication workflow, with filtering, mapping, metadata translation,
  and logging responsibilities separated cleanly across the pages.
- `simulation/*` now distinguishes memory emulation from PGP2B/sideband
  co-simulation more clearly and preserves implementation-specific mechanics
  such as retry-drop behavior and the fixed sideband port offset.
- `utilities/hls/*` now frames the parser as a bootstrap utility that turns
  generated HLS register headers into a starter PyRogue model, with the parser
  workflow and cleanup expectations stated more directly.

### Phase 5: Cross-Section Consistency Pass

Status: `in_progress`

- [ ] Verify `pyrogue_tree` only owns top-level `pyrogue` classes
- [ ] Verify `built_in_modules` owns submodule APIs and wrapper families
- [ ] Check cross-links between `pyrogue_tree` and `built_in_modules`
- [ ] Remove any remaining bolted-on wrapper-note sections
- [ ] Remove repeated intro text and other narrative drift

Progress Notes:

- The first pass confirmed that the top-level ownership split is mostly in the
  right place: `pyrogue_tree` is centered on the `Root`/`Device`/`Variable`
  model and top-level `pyrogue` built-ins, while `built_in_modules` carries
  submodule wrappers, protocol families, hardware endpoints, simulation, and
  helper integrations.
- Initial cleanup corrected a few remaining scope-description drifts on the
  landing pages, including namespace wording on `built_in_modules/index.rst`,
  more precise ownership language on `built_in_modules/interfaces/index.rst`,
  and a tighter summary of the UART page role on
  `built_in_modules/protocols/index.rst`.

## Recommended Working Order

1. `docs/src/built_in_modules/index.rst`

## Current Decisions

- Prefer use-case-led openings such as "For [task], Rogue provides ..." or
  "When [situation], PyRogue provides ...".
- Avoid calling classes or modules an "entry point".
- Vary opening sentence structure so pages do not feel mechanically templated.
- Use `Subtopics` rather than `Choosing A ...` headings on family and landing
  pages.
- Use `Key Constructor Arguments` when a page is mainly about instantiating a
  class or helper.
- Use `Common Controls` when runtime methods, variables, or settings matter
  more than constructor arguments.
- Prefer complete, commented examples over fragments.
- On direct `rogue.*` family pages, explicitly verify that useful Python and
  C++ examples both remain after the rewrite. This has regressed repeatedly
  during cleanup passes.
- In hardware DMA pages, keep the lower-level driver context visible when it is
  part of the real mental model. In particular, preserve the
  `slaclab/aes-stream-drivers` reference, the explanation of zero-copy buffer
  handling, and the common `dest` mapping convention.

## Next Target

Phase 4 is the next clean starting point:

- `docs/src/built_in_modules/interfaces/sql.rst`
- `docs/src/built_in_modules/interfaces/os_memory_bridge.rst`
- `docs/src/built_in_modules/protocols/gpib.rst`
- `docs/src/built_in_modules/protocols/epicsV4/*`
- `docs/src/built_in_modules/protocols/uart.rst`
- `docs/src/built_in_modules/simulation/*`
- `docs/src/built_in_modules/utilities/hls/*`
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
- Prefer use-case-led topic introductions such as "For [task], Rogue provides
  ..." or "When [situation], PyRogue provides ...", while varying sentence
  structure enough that the docs do not feel mechanically templated.
- Avoid framing a class or module as an "entry point". Describe what task it
  serves and how it relates to the lower-level object instead.

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
- `2026-03-13`: Completed the mixed wrapper/core family rewrite for
  `utilities/fileio`, `utilities/prbs`, and `protocols/network`, keeping the
  common PyRogue wrapper form first while naming the underlying Rogue utility
  immediately and separating wrapper behavior from direct-endpoint behavior.
- `2026-03-13`: Added a built-in-modules intro-style rule: lead with the use
  case, avoid calling things an "entry point", and vary opening sentence
  structure so pages do not read like a rigid template.
- `2026-03-13`: Completed the direct-UDP rewrite for `protocols/udp`, using
  the implementation and `tests/test_udpPacketizer.py` to document `Core`,
  `Client`, and `Server` as lower-level transport pieces that usually sit
  below RSSI and packetizer.
- `2026-03-13`: Completed the direct-RSSI rewrite for `protocols/rssi`,
  keeping the docs `rogue.*`-first while clarifying that
  `pyrogue.protocols.UdpRssiPack` remains the normal FPGA-facing path and the
  direct RSSI classes are the lower-level composition and debugging tools.
- `2026-03-13`: Completed the direct-SRP rewrite for `protocols/srp`,
  keeping the focus on SRP as the bridge between memory transactions and stream
  transport while separating `SrpV0`, `SrpV3`, and `Cmd` by actual use case.
- `2026-03-13`: Completed the direct packetizer rewrite for
  `protocols/packetizer`, keeping the docs focused on packetizer as the
  destination-routing layer above transport and restoring explicit controller,
  version-selection, and lower-layer lifecycle guidance.
- `2026-03-13`: Completed the direct batcher rewrite for `protocols/batcher`,
  separating splitter and inverter workflows by actual downstream needs and
  restoring the no-worker-thread execution model from the implementation.
- `2026-03-13`: Completed the direct Xilinx rewrite for `protocols/xilinx`,
  keeping `Xvc` as the normal object, `JtagDriver` as the lower-level protocol
  base, and explicitly documenting the XVC server thread and managed-interface
  lifecycle pattern.
- `2026-03-13`: Completed the compression utility rewrite for
  `utilities/compression`, keeping the docs focused on in-line stream payload
  transformation and preserving the synchronous execution model from the
  implementation.
- `2026-03-13`: Completed the hardware wrapper rewrite for `hardware/*`,
  sharpening the distinction between DMA-backed wrappers and raw `/dev/mem`
  mapping while restoring explicit worker-thread and zero-copy behavior notes.

## Context-Handoff Notes

When continuing this work in a new context window:

1. Read `docs/doc_merge_guidelines.md`.
2. Read this file.
3. Continue from the first unchecked item in the current phase unless a newer
   note in `Progress Notes` says otherwise.
4. Update phase status and checkboxes as soon as a page cluster is completed.
