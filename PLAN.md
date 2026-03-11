## Documentation Revamp Plan: Coherent Learning Path + Clean Reference Boundary

Superseded note
===============

This top-level plan was the initial working proposal for the documentation
revamp. The canonical historical record for what actually landed is under
``docs/src/documentation_plan/``.

Current status as of 2026-03-11:

- M1 through M4 are complete.
- The branch is in release-freeze cleanup state for merge into ``pre-release``.
- Any additional section expansion should be treated as follow-up work.

### Summary
Rebuild the docs around a clear user journey while preserving reference quality:
1. `Intro -> Quick Start -> Core Concepts -> Task Guides -> Reference`.
2. Move narrative explanations out of API pages into primary docs.
3. Keep API pages reference-only and cross-linked.
4. Evolve sidebar incrementally with **milestone freezes** (not fixed upfront forever, not fully ad hoc).

---

## Scope and Success Criteria

### Goals
- Make docs accessible to new users and efficient for experienced users.
- Remove duplicated/scattered explanations across API pages.
- Create a stable, maintainable information architecture (IA).

### Success Criteria
- New user can go from intro to first working setup without leaving primary docs.
- All major conceptual topics have narrative homes outside API reference.
- API pages are concise and consistent (signatures, params, behavior notes only).
- Sidebar supports discoverability and remains stable within each milestone.

### Out of Scope (for this revamp phase)
- Major code/API redesign.
- Full rewrite of every API docstring unless required for reference clarity.

---

## Target Information Architecture (Top-Level)

1. Introduction  
2. Quick Start  
3. Tutorials  
4. PyRogue Core  
5. Stream Interface  
6. Memory Interface  
7. Interfaces  
8. Utilities  
9. Hardware  
10. Protocols  
11. Cookbook  
12. API Reference (Python, C++)  
13. Operations (logging, PyDM, install/compile)

Notes:
- “Creating custom modules” moves under **Stream Interface**.
- Existing install/compile/logging/PyDM content is reused and normalized.

---

## Content Placement Rules (Hard Policy)

1. Narrative and conceptual guidance lives in main docs (Tutorial/How-to/Explanation sections).
2. API pages are reference-first:
   - Class/function signatures
   - Parameters/returns
   - Side effects/exceptions
   - Minimal behavioral notes
3. If an API page contains long narrative today, extract it to a main-doc page and replace with:
   - 2–5 line summary
   - links to conceptual/how-to pages
4. Every narrative page links to relevant API reference objects.
5. Every key API page links back to at least one “When/Why to use this” narrative page.

---

## Topic Mapping (Your Current List -> New Homes)

### PyRogue Core
- Tree model, class relationships
- ZMQ client connectivity (Simple Client / Virtual Client)
- Variable streams
- Polling
- YAML for configuration/state/status
- Model API
- Built-in Devices (DataReceiver, file writer, etc.)
- Advanced Device overrides
- Advanced Variable patterns (complex RemoteVariable/LinkVariable)

### Stream Interface
- Architecture overview
- Built-in modules: FIFO, Filter, Rate Drop, Debug, TCP Bridge
- Python bindings
- Custom module creation
- Example pipelines

### Memory Interface
- Conceptual memory transaction model
- Relationship to Rogue Tree
- “Most users use tree-level abstractions” guidance
- Low-level API remains in reference pages

### Cookbook
- Short, task-oriented recipes for Devices/Variables/advanced stream patterns
- Recipe pages stay practical; conceptual deep dives link to Explanations pages

---

## Sidebar Evolution Process (Selected: Milestone Freezes)

### Milestone 1: Skeleton IA
- Establish top-level sections and major landing pages.
- Freeze sidebar for this milestone.

### Milestone 2: Core Narrative Migration
- Move long narrative from highest-traffic API pages into main docs.
- Add bidirectional cross-links.
- Freeze sidebar at milestone end.

### Milestone 3: Coverage Expansion
- Fill PyRogue/Stream/Memory gaps and built-in module coverage.
- Add cookbook recipes.
- Freeze sidebar at milestone end.

### Milestone 4: Final Harmonization
- Remove stale navigation paths.
- Normalize naming and ordering.
- Final freeze for release.

Change control inside milestones:
- Only additive low-risk links/pages.
- Structural moves deferred to milestone boundaries.

---

## Implementation Work Breakdown

1. Inventory current docs and classify each page:
   - keep / move / split / merge / deprecate
2. Build migration matrix:
   - old path -> new path -> action -> owner -> milestone
3. Draft landing pages for each major section with consistent templates.
4. Migrate narrative from API pages in priority order:
   - Quick Start blockers first
   - PyRogue core pages second
   - Stream/Memory next
5. Refactor API pages to concise reference format.
6. Add cross-links and “Related pages” blocks.
7. Run coherence pass:
   - terminology consistency
   - duplicate content removal
   - link integrity
8. Final navigation cleanup at milestone boundaries.

---

## Important Interface/Type Changes

Public software APIs: **No functional code/API changes planned**.

Documentation interfaces that will change:
- Sidebar hierarchy (iterative at milestones)
- Page ownership boundaries (narrative vs reference)
- Standard page templates:
  - Tutorial
  - How-to
  - Explanation
  - Reference

---

## Test Cases and Validation Scenarios

1. New-user path test:
   - Intro -> Quick Start -> first working PyRogue task without API deep-dives.
2. Task completion test:
   - Find and execute common tasks (client connection, polling, YAML usage, stream setup).
3. Reference lookup test:
   - From narrative page, navigate to class API in <=2 clicks.
4. Reverse lookup test:
   - From API page, find “when/why/how” narrative guidance in <=1 click.
5. Navigation stability test:
   - No major sidebar reshuffle within a milestone.
6. Consistency test:
   - Identical terminology for same concepts across PyRogue/Stream/Memory docs.
7. Link integrity test:
   - No broken internal links after each migration batch.

---

## Assumptions and Defaults

- “Log narrative” was interpreted as “long-form narrative”; policy applied accordingly.
- Existing content is reused wherever possible; revamp focuses on structure and extraction, not full rewrites.
- Cookbook is kept as a separate section for discoverable recipes, with strict scope control.
- API reference remains authoritative for signatures/details; narrative authority shifts to main docs.
- Sidebar will evolve, but only at milestone boundaries (chosen default).
