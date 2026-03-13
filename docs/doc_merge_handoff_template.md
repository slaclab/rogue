# Doc Merge Handoff Template

Use this file to start a new Codex topic window when continuing the built-in
modules documentation reorganization. Paste the relevant parts into the new
conversation, together with `docs/doc_merge_guidelines.md` and
`docs/doc_builtin_modules_reorg_plan.md`.

## Recommended Handoff Structure

Include these four things:

1. The goal of the built-in-modules reorganization.
2. The merge rules from `docs/doc_merge_guidelines.md`.
3. The current phase status from `docs/doc_builtin_modules_reorg_plan.md`.
4. The next target cluster of documents.

## Suggested Starter Prompt

```md
We are continuing the built-in modules documentation reorganization in this
repository.

Before making changes, read:
- `docs/doc_merge_guidelines.md`
- `docs/doc_builtin_modules_reorg_plan.md`
- `docs/doc_merge_handoff_template.md`

Task:
- Continue the next built-in-modules rewrite cluster by comparing the full old
  docs on `pre-release` with the current docs, then rewriting the current docs
  into a coherent narrative that preserves the best of both.

Working rules:
- Follow `docs/doc_merge_guidelines.md`.
- Compare entire old and new documents before rewriting.
- Verify examples against the actual code before writing them.
- Use GitHub and local example search as part of the normal workflow for
  reusable classes and helpers.
- Prefer use-case-led openings such as "For [task], Rogue provides ..." or
  "When [situation], PyRogue provides ...".
- Avoid calling modules or classes an "entry point".
- Vary opening sentence structure so the docs do not feel mechanical.
- Use `Subtopics` rather than `Choosing A ...` headings.
- Use `Key Constructor Arguments` when a page is mainly about instantiation.
- Use `Common Controls` when runtime settings and methods matter more.
- Prefer complete, commented examples over fragments.
- On direct `rogue.*` family pages, explicitly verify that useful Python and
  C++ examples both remain after the rewrite.
- When hardware DMA pages are involved, preserve the `aes-stream-drivers`
  linkage and keep zero-copy and `dest` mapping explanations intact.
- Do not identify source repos in the doc prose unless that provenance is
  technically important.

Already completed:
- Phase 1: built-in-modules landing pages
- Phase 2: mixed wrapper/core families
- Phase 3: direct `rogue.*` families

Important recent corrections:
- `protocols/rssi/*` needed threading and lifecycle detail restored after an
  earlier rewrite compressed it too far.
- `protocols/xilinx/*`, `protocols/packetizer/*`,
  `protocols/batcher/*`, and `utilities/compression/*` all needed second
  merge-quality passes to restore conceptual depth and missing examples.
- C++ examples have repeatedly been lost during cleanup passes. Check for that
  explicitly before finalizing a page.
- `hardware/dma/*` now includes explicit `aes-stream-drivers` context, a
  software-facing explanation of zero-copy DMA buffers, and `dest` mapping
  guidance.
- `hardware/raw/index.rst` now uses complete examples for both `Root`-based
  and standalone usage.

Next target:
- Phase 4 pure Python integration families:
  - `docs/src/built_in_modules/interfaces/sql.rst`
  - `docs/src/built_in_modules/interfaces/os_memory_bridge.rst`
  - `docs/src/built_in_modules/protocols/gpib.rst`
  - `docs/src/built_in_modules/protocols/epicsV4/*`
  - `docs/src/built_in_modules/protocols/uart.rst`
  - `docs/src/built_in_modules/simulation/*`
  - `docs/src/built_in_modules/utilities/hls/*`

If the old/new mapping becomes ambiguous, stop and state the ambiguity clearly
before continuing.
```

## Best Practices For Starting The New Window

- Paste the starter prompt first.
- Keep the handoff focused on decisions, completed work, and next targets.
- Mention any recent style corrections explicitly so they are not lost.
- Do not paste large document bodies into the new window unless the next task
  immediately depends on them.
- If the current work is in a direct `rogue.*` family, call out the need to
  preserve both conceptual depth and language coverage in examples.

## Minimal Version

If you want a shorter handoff, this is usually enough:

```md
Continue the built-in modules documentation reorganization in this repo.

Read and follow:
- `docs/doc_merge_guidelines.md`
- `docs/doc_builtin_modules_reorg_plan.md`

Current status:
- Phase 1 complete
- Phase 2 complete
- Phase 3 complete
- Phase 4 pending

Next target:
- `docs/src/built_in_modules/interfaces/sql.rst`
- `docs/src/built_in_modules/interfaces/os_memory_bridge.rst`
- `docs/src/built_in_modules/protocols/gpib.rst`
- `docs/src/built_in_modules/protocols/epicsV4/*`
- `docs/src/built_in_modules/protocols/uart.rst`
- `docs/src/built_in_modules/simulation/*`
- `docs/src/built_in_modules/utilities/hls/*`

Compare full old docs on `pre-release` against the current docs before
rewriting. Preserve the best narrative material from the old docs while
keeping the new structure. Verify examples against the actual code, prefer
complete commented examples, and do not let Python or C++ examples disappear
during cleanup passes.
```
