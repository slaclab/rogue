.. _documentation_plan_policies:

====================
Documentation Policy
====================

Narrative vs API Boundary
=========================

1. Conceptual and tutorial narrative belongs in primary documentation sections.
2. API pages are reference-first and should contain:

   - Signatures/types
   - Parameter/return documentation
   - Side effects and exceptions
   - Minimal usage notes

3. Long-form explanations in API pages must be extracted into primary docs.
4. Narrative pages must link to relevant API reference pages.
5. Key API pages should include at least one link back to conceptual guidance.

Sidebar Evolution
=================

The sidebar follows milestone freezes:

1. Freeze structure inside a milestone.
2. Allow structural changes between milestones.
3. Keep in-milestone changes additive and low risk.

M2 Freeze Record
================

M2 information architecture and navigation structure are frozen.

During freeze:

1. Keep legacy pages available and explicitly labeled.
2. Route readers to canonical entry points without deleting narrative content.
3. Defer structural relocation decisions to M3 unless required to resolve build
   errors.

Narrative Preservation Rule
===========================

During the current revamp phase, do not remove existing narrative text from the
documentation.

Allowed actions:

1. Move narrative content to a more appropriate section/page.
2. Add links and structure around existing narrative.
3. Apply minor wording edits for clarity or consistency.

Required practice:

- If minor wording edits are made to existing narrative, call them out in the
  change summary.
- Prefer preserving original narrative blocks verbatim when relocating content.
