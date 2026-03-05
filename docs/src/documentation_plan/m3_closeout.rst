.. _documentation_plan_m3_closeout:

===========
M3 Closeout
===========

M3 objective
============

Expand narrative coverage depth, replace placeholder protocol content with
code-backed documentation, and harden narrative/reference cross-links while
preserving the canonical information architecture.

Completion summary
==================

M3 is complete for coverage expansion and protocol/API boundary hardening.

Completed in M3:

- Expanded protocol narrative pages for UDP, Packetizer, and UART using
  implementation-backed behavior notes and examples.
- Expanded and standardized RSSI protocol narrative with lifecycle/threading
  consistency updates using Managed Interface Lifecycle terminology.
- Converted C++ protocol API placeholder wrappers for UDP and Packetizer into
  reference-first pages with links back to conceptual docs.
- Performed API<->narrative cross-link hardening across protocol sections
  (Batcher, RSSI, SRP, UDP, Packetizer, Xilinx).
- Harmonized ``interfaces/index`` into a transitional map that points to
  canonical homes in PyRogue Core, Stream Interface, and Memory Interface.
- Updated migration matrix entries to mark completed M3 coverage actions.

Validation
==========

- Documentation build completed without issues in local validation.
- Placeholder/TODO protocol content targeted for M3 was removed or replaced in
  covered pages.
- Lifecycle phrasing consistency applied where thread/lifecycle sections are
  documented.

Deferred to M4
==============

- Final harmonization sweep for naming/order consistency across sections.
- Final navigation cleanup of temporary/legacy paths still retained for
  compatibility.
