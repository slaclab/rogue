# Docs Window Handoff

Last updated: 2026-03-12
Branch: `doc-update-6`
Merge target: `pre-release`

## Purpose

This note captures the work completed in this window so a new Codex window can
 resume cleanly without re-discovering project-specific docs workflow and
recent decisions.

## Important User Instructions

- This branch and PR merge into `pre-release`, not `main`.
- Do not try to build docs manually with ad hoc commands like raw `make html`
  unless you are matching the existing VS Code task behavior.
- Use the VS Code tasks already defined in `.vscode/tasks.json`.
- The docs build should be validated from the existing conda environment and
  task setup, not by guessing the environment.

## Canonical Docs Build Method

The user explicitly said to use the VS Code tasks already defined.

Primary task:

- `Docs: Build HTML`

Task command currently defined in `.vscode/tasks.json`:

```sh
source "${MINIFORGE_HOME:-$HOME/miniforge3}/etc/profile.d/conda.sh" && \
conda run -n rogue_build python -c "import sphinx_autodoc_typehints, sphinx_copybutton" || \
conda run -n rogue_build pip install sphinx-autodoc-typehints sphinx-copybutton sphinxcontrib-napoleon && \
conda run -n rogue_build make clean html
```

Working directory for that task:

- `docs/`

What to expect from validation:

- Full docs build succeeds.
- Remaining warning is environmental, not content-related:
  intersphinx cannot fetch `https://docs.python.org/objects.inv` in restricted
  network conditions.
- Matplotlib may also warn about cache directory permissions in this sandboxed
  environment.

## Branch State From This Window

The docs revamp is in merge-ready cleanup state, not open-ended restructuring.

Completed in this window:

- Finalized M4 closeout / release-freeze language in:
  - `DOCS_REVAMP_HANDOFF.md`
  - `PLAN.md`
  - `docs/src/documentation_plan/m4_closeout.rst`
- Added follow-up backlog page:
  - `docs/src/documentation_plan/post_merge_followups.rst`
- Cleaned public docs wording so legacy/example material is framed as
  supplemental rather than unfinished:
  - `docs/src/cookbook/index.rst`
  - `docs/src/tutorials/index.rst`
  - `docs/src/advanced_examples/index.rst`
- Added conceptual backlinks across API reference pages.
- Normalized backlink wording:
  - API index pages use `Related Topics`
  - API leaf pages generally use `For conceptual usage, see:`
- Removed the specific follow-up backlog item about missing API backlinks,
  because that work is done.
- Added local source-code links for C++ API docs using generated Doxygen HTML,
  not GitHub links.
- Enabled Doxygen source browsing and `.cpp` indexing so C++ API entries can
  link to both declarations and implementations when available.
- Added a docs-only Doxygen input filter so `.cpp` alias spellings are
  normalized for Doxygen parsing without changing production C++ code.
- Fixed the `maxVecLen` Doxygen parameter-name typo in
  `include/rogue/protocols/xilinx/XvcConnection.h`.

## Sidebar/Nav Decisions Made Here

### 1. API section should expand deeply

This behavior was kept for `api/...` pages.

Current mechanism:

- Local theme override in `docs/src/_templates/layout.html`
- For `pagename.startswith('api/')`, sidebar nav depth is `-1`
- For non-API pages, nav depth is shallower (`4`)

### 2. Main docs/homepage should not expand like API

This was addressed by the same template override:

- API pages: deep nav
- Non-API pages: shallower nav

### 3. API sidebar should show API document navigation only

The user explicitly did **not** want `Related Topics` showing in the API side
nav.

This was handled in two ways:

- API `Related Topics` blocks were changed from section headings to
  `.. rubric:: Related Topics` so they remain visible in page content but do
  not become sidebar heading links.
- A fallback API-only JS cleanup was added in `docs/src/_static/custom.js` and
  included from `docs/src/conf.py` to remove fragment-link sidebar items on API
  pages if they still appear.

### 4. API toctrees should stay title-focused

Top-level API-driving toctrees were updated with `:titlesonly:` where needed so
the generated sidebar stays document-focused.

### 5. Deep expansion belongs in the API sidebar, not the page body

The user explicitly wants the API navbar/sidebar to expand as deep as needed,
but does not want the page-body toctree content expanded.

Current rule:

- API sidebar depth is controlled by `docs/src/_templates/layout.html`
- API page-body toctrees stay shallow with `:maxdepth: 1`
- This is now true across `docs/src/api/**/index.rst`

If this behavior regresses, check both:

- sidebar rendering in built HTML
- source `:maxdepth:` values in API `index.rst` files

## Files Added/Changed That Matter Most

Workflow / build behavior:

- `.vscode/tasks.json`
- `docs/src/conf.py`
- `docs/src/_templates/layout.html`
- `docs/src/_static/custom.js`
- `docs/Doxyfile`
- `docs/src/_ext/rogue_cpp_source_links.py`
- `docs/src/_ext/rogue_doxygen_input_filter.py`
- `docs/src/_static/custom.css`

Handoff / planning:

- `WINDOW_HANDOFF_DOCS.md`
- `DOCS_REVAMP_HANDOFF.md`
- `PLAN.md`
- `docs/src/documentation_plan/index.rst`
- `docs/src/documentation_plan/m4_closeout.rst`
- `docs/src/documentation_plan/post_merge_followups.rst`

Key API/nav examples touched:

- `docs/src/api/index.rst`
- `docs/src/api/python/index.rst`
- `docs/src/api/cpp/index.rst`
- `docs/src/api/python/pyrogue/index.rst`
- `docs/src/api/python/rogue/index.rst`

## How To Verify Sidebar Behavior

After running the docs build task, inspect built HTML directly if needed:

- `docs/build/html/index.html`
- `docs/build/html/api/index.html`
- `docs/build/html/api/python/index.html`

The user specifically pointed to local built HTML inspection when checking nav
behavior. Looking at the generated HTML or opening it locally is valid and was
useful in this window.

Expected current result for `docs/build/html/api/python/index.html`:

- Sidebar includes API document entries like `Python API`, `pyrogue`,
  `rogue`, `C++ API`
- Sidebar does **not** include `Related Topics`
- Page body shows only the immediate API landing-page entries, not the fully
  expanded descendant tree

## C++ Source Link Behavior

Recent work added local source links for the C++ API pages.

Current mechanism:

- Doxygen HTML source pages are generated under `docs/build/doxyhtml`
- During Sphinx HTML build they are copied into `docs/build/html/_doxygen`
- C++ API signatures rendered by Breathe get source links injected by
  `docs/src/_ext/rogue_cpp_source_links.py`

Current expected behavior:

- C++ class entries usually show `[header]`
- C++ methods/functions with out-of-line definitions show both
  `[header]` and `[impl]`
- Links target local generated HTML like
  `docs/build/html/_doxygen/Bsp_8h_source.html#l00044`
  and
  `docs/build/html/_doxygen/Bsp_8cpp_source.html#l00099`

Important decision:

- The user explicitly does **not** want GitHub source links for this feature.
- This should remain a local Doxygen/Sphinx-generated source browser flow.

Implementation notes:

- `docs/Doxyfile` now has:
  - `INPUT = ../include/ ../src/`
  - `SOURCE_BROWSER = YES`
- `docs/src/_ext/rogue_doxygen_input_filter.py` is used via
  `FILTER_PATTERNS` for `*.cpp`
- The filter exists to help Doxygen match implementation signatures that use
  local aliases like `bp::object`, `ria::BspPtr`, `rim::...`, `ris::...`
  back to the canonical header declarations
- This warning cleanup was done in docs tooling only; do not "fix" it by
  rewriting production C++ signatures unless the user explicitly asks

How to verify source-link behavior:

- Build docs with the normal docs task
- Inspect a generated C++ API page in `docs/build/html`, for example:
  - `docs/build/html/api/cpp/interfaces/api/bsp.html`
- Confirm links resolve into `docs/build/html/_doxygen/...`
- Confirm representative methods show both declaration and implementation links
  where appropriate

## Known Remaining Issues

- Intersphinx warning due to unavailable network access remains expected.
- Matplotlib cache-dir warning may appear in this environment.
- There may still be opportunities to simplify the fallback JS/sidebar logic
  later, but current behavior builds and matches the requested nav behavior.
- The user has not yet decided how Boost.Python-exported C++ API pages should
  expose source links. Do not assume they want wrapper-source links added.
- For that mixed API area, the user explicitly said not to implement step 3
  ("binding source" links) yet.

## Recommended Next Step For A New Window

If more work is needed:

1. Start from `WINDOW_HANDOFF_DOCS.md`
2. Treat the branch as merge-close, not as a fresh docs reorg
3. Use the VS Code docs task workflow, not an improvised build method
4. If sidebar behavior is questioned, inspect `docs/build/html/api/python/index.html`
   directly after a task-driven build
5. If C++ source links are questioned, inspect `docs/build/html/api/cpp/...`
   and the copied local Doxygen pages under `docs/build/html/_doxygen/`
