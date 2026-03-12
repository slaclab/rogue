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
- When useful, also consult local example code in `/Users/bareese/surf`,
  `/Users/bareese/ldmx-firmware`, and `/Users/bareese/warm-tdm` for real-world
  usage patterns.
- When useful, also use authenticated `gh search code` queries against the
  `slaclab` GitHub organization to discover Rogue-based examples in public and
  accessible private repositories, then verify the relevant source directly
  before reflecting those patterns in the docs.
- `slaclab` repositories are generally acceptable example sources, but treat
  `pysmurf` cautiously because it often reflects older Rogue APIs; verify any
  reused pattern against the current implementation in this repository first.
- Do not identify example source projects in the doc prose unless that
  provenance is technically important; present examples as documentation
  examples first.
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
- `docs/src/pydm/index.rst`
- `docs/src/pydm/starting_gui.rst`
- `docs/src/pydm/channel_urls.rst`
- `docs/src/pydm/rogue_widgets.rst`
- `docs/src/pydm/timeplot_gui.rst`
- `docs/src/api/python/pyrogue/pydm_widgets/index.rst`
- `docs/src/api/python/pyrogue/pydm_widgets/*`
- `docs/src/pyrogue_tree/index.rst`
- `docs/src/pyrogue_tree/core/index.rst`
- `docs/src/pyrogue_tree/core/root.rst`
- `docs/src/pyrogue_tree/core/device.rst`
- `docs/src/pyrogue_tree/core/variable.rst`
- `docs/src/pyrogue_tree/core/command.rst`
- `docs/src/pyrogue_tree/core/local_variable.rst`
- `docs/src/pyrogue_tree/core/remote_variable.rst`
- `docs/src/pyrogue_tree/core/link_variable.rst`
- `docs/src/pyrogue_tree/core/local_command.rst`
- `docs/src/pyrogue_tree/core/remote_command.rst`
- `docs/src/pyrogue_tree/core/groups.rst`
- `docs/src/pyrogue_tree/core/block.rst`
- `docs/src/pyrogue_tree/core/block_operations.rst`
- `docs/src/pyrogue_tree/core/memory_variable_stream.rst`
- `docs/src/pyrogue_tree/core/model.rst`
- `docs/src/pyrogue_tree/core/fixed_point_models.rst`
- `docs/src/pyrogue_tree/core/poll_queue.rst`
- `docs/src/pyrogue_tree/core/yaml_configuration.rst`

Important structural notes:
- Stream built-in module pages now sit under
  `docs/src/stream_interface/built_in_modules.rst`.
- `docs/src/memory_interface/hub.rst` includes both a fuller raw C++ `Hub`
  example and a `Using A Python Device Hub` section.
- Helpful local example-code repositories for doc writing:
  `/Users/bareese/surf`, `/Users/bareese/ldmx-firmware`, and
  `/Users/bareese/warm-tdm`.
- GitHub CLI auth is available for `gh search code` against the `slaclab`
  organization and should be used when broader Rogue example discovery would
  help the merge.
- `slaclab` repos are acceptable example sources in general, but `pysmurf`
  should be treated as legacy-oriented and cross-checked carefully before its
  patterns are reused.
- In `pyrogue_tree/core`, the foundational narrative now runs:
  `Root` -> `Device` -> `Variable` / `Command` -> subtype pages -> advanced
  mechanics pages such as `Block`, `Device Block Operations`, `Model`, and YAML.
- `Device` now carries the first conceptual introduction to write / verify /
  read / check. `post()` exists, but the current docs treat it as narrower:
  part of the memory transaction model and relevant to hardware-backed
  Variables and `RemoteCommand`, not one of the core full-Device traversal
  operations.
- `Variable` now introduces `get()`, `set()`, `getDisp()`, `setDisp()`,
  `value()`, and `valueDisp()`, with `post()` described as a narrower
  hardware-backed API.
- `Block` now includes a dedicated explanation of the `Device._buildBlocks()`
  grouping process.
- `LinkVariable` examples were expanded using real patterns from local/example
  repos, but the docs should avoid naming the source project in the example
  prose unless technically necessary.
- `LocalCommand` now covers callback argument injection, default command
  arguments via `value=`, and the `@self.command` decorator.
- `RemoteCommand` now includes a fuller explanation of the built-in command
  helper functions (`toggle`, `touchOne`, `touchZero`, posted helpers, and the
  `create...` helpers).
- `Groups` was rewritten in the newer narrative style, but its built-in-group
  sections intentionally preserve more of the older page's operational detail.
- In `memory_interface`, `Transaction`, `Master`, and `Slave` now introduce
  `Post` more explicitly. The current doc position is: `Post` is a real memory
  transaction type, often handled like `Write` at the transport boundary, but
  available for downstream paths that want distinct posted-write policy.
- `memory_variable_stream.rst` is implementation-driven because the old-page
  equivalent on `pre-release` was effectively a stub.
- `model.rst` now links to a dedicated
  `docs/src/pyrogue_tree/core/fixed_point_models.rst` page so the main Model
  page stays focused while `Fixed` / `UFixed` get fuller explanation.
- `yaml_configuration.rst` was split so it now stays focused on YAML structure,
  file inputs, filters, `writeEach`, and array matching; the generic bulk
  write / verify / check transaction model now lives in
  `docs/src/pyrogue_tree/core/block_operations.rst`.
- The docs build workflow is now documented in
  `docs/doc_merge_guidelines.md`: use the repo's `Docs: Build HTML` task /
  `rogue_build` conda environment, but ask the user before running it because
  it may install packages and runs `make clean html`.
- A docs build has now been run successfully in the proper environment.
  Current status: `build succeeded, 1 warning`.
- The remaining warning is environmental, not a page-content problem:
  Sphinx could not fetch the Python intersphinx inventory from
  `https://docs.python.org/objects.inv`.
- To make the docs build robust, `docs/src/conf.py` now mocks additional
  optional GUI dependencies (`qtpy`, `matplotlib`, `pyqtgraph`, `sip`) and the
  `python/pyrogue/pydm/widgets/*.py` modules now use
  `from __future__ import annotations` so autodoc imports do not eagerly
  evaluate mocked Qt type annotations.

Next likely target:
- Do a consistency pass on nearby pages that mention command helpers,
  group filters, YAML workflows, or posted writes if any wording drift remains.
- Consider whether `docs/src/pyrogue_tree/core/remote_variable.rst` should add
  a short pointer to `fixed_point_models.rst`, since that is where many users
  first encounter `base=pr.Fixed(...)`.
- If needed, continue source-level cleanup for docs-build robustness, but treat
  the remaining intersphinx warning as an environment/network issue unless the
  build context changes.

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
- `docs/src/pydm/*`
- much of `docs/src/pyrogue_tree/core/*`

Next target:
- consistency pass on nearby `docs/src/pyrogue_tree/core/*` pages
- optionally add fixed-point cross-links from `remote_variable.rst`
- then move to the next unresolved doc cluster

Compare full old docs on `pre-release` against the current docs before
rewriting. Preserve the best narrative material from the old docs while keeping
the new structure. Verify example APIs against the actual code.
```
