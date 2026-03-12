# Doc Merge Handoff Template

Use this file to start a new Codex topic window when continuing the docs merge
work. Paste the relevant parts into the new conversation, together with
`docs/doc_merge_guidelines.md`.

## Recommended Handoff Structure

Include these four things:

1. The goal of the work.
2. The merge rules from `docs/doc_merge_guidelines.md`.
3. The current status of what has already been merged.
4. The next target cluster of documents.

## Suggested Starter Prompt

```md
We are continuing a documentation merge pass in this repository.

Before making changes, read:
- `docs/doc_merge_guidelines.md`

Task:
- Continue merging the next documentation cluster by comparing the full old
  docs on `pre-release` with the current docs, then rewriting the current docs
  into a coherent narrative that preserves the best of both.

Working rules:
- Follow `docs/doc_merge_guidelines.md`.
- Compare entire old and new documents before rewriting.
- Prefer narrative exposition over compressed bullets.
- Preserve strong explanatory comments in examples.
- Verify example APIs against the actual code before writing them.
- Use proper type names in fixed-width formatting, such as ``Master``,
  ``Slave``, ``Frame``, and ``Transaction``.
- Capitalize list items.
- Only include `What To Explore Next` and `Related Topics` when they are
  genuinely useful.

Already completed:
- `docs/src/stream_interface/index.rst`
- `docs/src/stream_interface/connecting.rst`
- `docs/src/stream_interface/frame_model.rst`
- `docs/src/stream_interface/sending.rst`
- `docs/src/stream_interface/receiving.rst`
- `docs/src/stream_interface/built_in_modules.rst`
- `docs/src/stream_interface/fifo.rst`
- `docs/src/stream_interface/filter.rst`
- `docs/src/stream_interface/rate_drop.rst`
- `docs/src/stream_interface/tcp_bridge.rst`
- `docs/src/stream_interface/debugStreams.rst`
- `docs/src/memory_interface/index.rst`
- `docs/src/memory_interface/connecting.rst`
- `docs/src/memory_interface/master.rst`
- `docs/src/memory_interface/slave.rst`
- `docs/src/memory_interface/hub.rst`
- `docs/src/memory_interface/tcp_bridge.rst`
- `docs/src/memory_interface/transactions.rst`

Important structural notes:
- Stream built-in module pages now sit under
  `docs/src/stream_interface/built_in_modules.rst`.
- `docs/src/memory_interface/hub.rst` includes both a fuller raw C++ `Hub`
  example and a `Using A Python Device Hub` section.
- No docs build has been run yet; verification so far is source-level only.

Next likely target:
- `docs/src/pyrogue_tree/index.rst`
- `docs/src/pyrogue_tree/core/index.rst`
- then the core concept pages under `docs/src/pyrogue_tree/core/`

If the old/new mapping becomes ambiguous, stop and state the ambiguity clearly
before continuing.
```

## Best Practices For Starting The New Window

- Paste the starter prompt first.
- Attach or paste any additional handoff summary only if it contains details
  not already covered by the prompt.
- Keep the handoff focused on decisions, completed work, and next targets.
- Do not paste large old and new document bodies into the new window unless the
  next task immediately depends on them.
- If there was a style correction made during the last window, mention it
  explicitly so it is not lost.

## Minimal Version

If you want a shorter handoff, this is usually enough:

```md
Continue the docs merge work in this repo.

Read and follow:
- `docs/doc_merge_guidelines.md`

Already merged:
- `docs/src/stream_interface/*`
- `docs/src/memory_interface/*`

Next target:
- `docs/src/pyrogue_tree/index.rst`
- `docs/src/pyrogue_tree/core/index.rst`

Compare full old docs on `pre-release` against the current docs before
rewriting. Preserve the best narrative material from the old docs while keeping
the new structure. Verify example APIs against the actual code.
```
