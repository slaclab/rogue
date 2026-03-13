# Documentation Merge Guidelines

Use these directives when merging an older documentation page into a newer
reorganized page.

## Goal

Produce a new document that combines the best material from the old and new
versions into a single coherent narrative. Do not mechanically append recovered
text. Rewrite the page so it reads like one intentional document.

## Core Rule

Do not treat the job as a diff merge. Read the sources, understand the current
implementation and real-world usage, then rewrite the page so it teaches the
topic clearly in the current documentation structure.

## Standard Workflow

Treat each merge target as a small research-and-rewrite pass, not as a text
edit.

Follow this order:

1. Read the full old page on `pre-release`.
2. Read the full current page in the reorganized docs.
3. Read the relevant implementation in this repository so the behavior,
   examples, and parameter descriptions reflect the actual current API.
4. Check how the feature is used in practice:
   - Search local example-heavy repositories such as
     `/Users/bareese/surf`, `/Users/bareese/ldmx-firmware`, and
     `/Users/bareese/warm-tdm` when they are relevant.
   - Use authenticated `gh` code search against the `slaclab` GitHub
     organization for real-world usage patterns.
5. Decide what the old page explains better, what the new page structures
   better, and what the implementation/examples show about actual usage.
6. Rewrite the page as one coherent document.
7. After the rewrite, do a short consistency pass against neighboring pages in
   the same subsection so terminology, section patterns, and cross-links do not
   drift.

Do not skip the implementation read just because the old docs already contain
examples. Do not skip real-world example discovery just because the local page
already has one example.

For topics centered on a class, helper, or reusable workflow, GitHub example
search should usually be treated as part of the standard workflow, not as an
exception path. The point is to understand how the feature tends to be used in
real trees, not just how it is defined in isolation.

## Rewrite Priorities

When deciding what to keep or recover, prioritize:

- Recovering conceptual explanations that were lost during the reorganization.
- Keeping newer structure, navigation, and page boundaries when they improve
  the docs.
- Preserving detailed discussions of important mechanics, such as iterator use,
  zero-copy behavior, ownership, ordering, or performance tradeoffs.
- Integrating better old explanations into the new structure rather than
  restoring the old structure wholesale.
- Removing repetitive statements so each section adds a new piece of
  information instead of restating the same point in slightly different words.

## Narrative Structure

- Start with general use cases and the basic purpose of the subject.
- Explain the common workflow or lifecycle before advanced details.
- Present examples in the order a user is likely to need them.
- Move advanced mechanics, performance details, and edge cases later in the
  document.
- Write in subject-first narrative prose. Explain the thing itself rather than
  announcing what the section "covers", "describes", or "will explain".
- Avoid meta-introduction phrasing such as "this section covers", "this area
  covers", "in this section", or "the examples below show". Prefer direct
  statements about the behavior, workflow, or object.
- Prefer prose and narrative exposition over compressed bullet summaries.
- Use bullets when the content is naturally list-shaped, but do not reduce core
  explanation to bullets if a paragraph would teach the subject better.
- During editing passes, actively look for repeated statements between the page
  introduction, parameter sections, subclassing sections, and example
  commentary. Consolidate repeated ideas instead of leaving near-duplicates in
  multiple places.

## Example Workflow

- Preserve or restore high-quality explanatory comments in code examples.
- Prefer examples that teach how and why the code works, not just what API to
  call.
- Keep older examples when their comments or teaching value are better than the
  newer versions.
- When needed, combine a newer example structure with older inline commentary.
- Consult the actual code when writing or merging example code so the examples
  use real APIs and use them correctly.
- Do not assume an older example is still valid after a refactor or API change.
- If the old and new docs disagree about an API, verify against the
  implementation before writing the merged example.
- When repository-local examples are thin, also consult local example code in
  `/Users/bareese/surf`, `/Users/bareese/ldmx-firmware`, and
  `/Users/bareese/warm-tdm` for real-world usage patterns. Treat those as
  supplementary examples, not as a substitute for verifying Rogue APIs against
  this repository's implementation.
- Use authenticated `gh search code` queries against the `slaclab` GitHub
  organization to find Rogue-based usage patterns across public and accessible
  private repositories whenever the page describes a reusable class, helper,
  or workflow. This should be the normal path for pages such as built-in
  devices, command helpers, interface adapters, and other reusable APIs.
- Use GitHub search as a discovery tool, then inspect the matched source
  directly before carrying the example pattern into the docs.
- If GitHub search is unavailable in the environment, say so clearly and fall
  back to the best available local examples rather than silently skipping the
  step.
- `slaclab` repositories are generally fair game as example sources, but treat
  `pysmurf` as a special case because much of it targets an older Rogue API
  surface. If you consult `pysmurf`, cross-check the example carefully against
  the current implementation in this repository before reusing the pattern.
- When examples are informed by other local or `slaclab` repositories, do not
  call out the source project in the explanatory prose unless the provenance is
  itself technically important. Present them as documentation examples first.

## Page Conventions

### Parameter Documentation Style

- For tree classes, document parameters using the narrative pattern established
  in the current docs rather than trying to restate the full constructor
  signature inline.
- Use section title `What You Usually Set` to focus attention on the small set
  of parameters that most strongly shape behavior in real usage.
- Treat the generated API reference as the canonical place for full signatures
  and exhaustive parameter lists.
- In narrative docs, explain the meaning and design impact of the commonly used
  parameters instead of mechanically enumerating every argument.
- For subtype pages, start from the shared parameters already explained on the
  parent page, then add the subtype-specific parameters that matter most for
  choosing and using that subtype.
- When helpful, follow a short summary list of important parameters with a more
  focused explanatory section for the highest-value ones.

### Type Naming Style

- Refer to Rogue class types by their proper names, such as ``Master``,
  ``Slave``, ``Frame``, ``Buffer``, and ``FrameIterator``.
- These type names should usually be written in fixed-width formatting.
- Do not casually downcase class-type references in prose when the text is
  referring to the Rogue type rather than to a generic concept.
- Variable names in code examples do not need to follow this rule, but prose
  and explanatory comments usually should.

### Section Title Style

- Section titles should read like proper names, not sentence fragments.
- Use title case.
- Examples:
  - `C++ Master Subclass`
  - `Python Master Subclass`
  - `API Reference`
  - `Related Topics`
- Avoid headings like descriptive notes or phrases when a proper section name
  would do.

### List Style

- Items in a list should be capitalized.
- This applies to bullet lists and numbered lists.
- If a list item starts with a type name, concept name, or ordinary prose, use
  an initial capital letter.

### Ending Sections

Toward the end of a document, use these labels consistently:

#### What To Explore Next

Use this for links to topics in the same subsection as the current page.

Example:
- A page in `stream_interface/` should link to other `stream_interface/` pages
  here.
- If there are no same-subsection links that genuinely help the reader
  continue, omit `What To Explore Next` rather than forcing a weak list.

#### Related Topics

Use this for links to related topics in other subsections.

Example:
- A page in `stream_interface/` can link to `custom_module/` here.
- If there is no genuinely useful cross-subsection link, omit `Related Topics`
  rather than forcing a weak one.

#### API Reference

Use this for links to the relevant API reference pages for classes, helpers,
functions, or modules discussed in the document.

## Verification

Use docs-build validation after meaningful rewrites when the user wants
verification or when structural changes may have introduced Sphinx issues.

- After a meaningful doc rewrite, prefer validating the result with the
  repository's docs-build workflow when the user wants verification or when a
  structural change might have introduced Sphinx issues.
- In this repository, the canonical build path is the VS Code task
  `Docs: Build HTML`, or the equivalent shell sequence from `docs/`:
  `source "${MINIFORGE_HOME:-$HOME/miniforge3}/etc/profile.d/conda.sh"`
  then
  `conda run -n rogue_build python -c "import sphinx_autodoc_typehints, sphinx_copybutton" || conda run -n rogue_build pip install sphinx-autodoc-typehints sphinx-copybutton sphinxcontrib-napoleon`
  then
  `conda run -n rogue_build make clean html`
- Treat that task as the source of truth for how docs are built in this repo.
- Do not run the docs build automatically if it has not been requested. Ask the
  user before running it, especially because the task may install missing
  Python packages and performs `make clean html`.
- If the build is attempted and fails, report the exact failure and any missing
  dependency or environment step rather than hand-waving it away.

## Rewrite Standard

- Do not preserve awkward transitional text just because it already exists.
- Remove partial merges, stray headings, and mislabeled sections.
- Favor clarity, flow, and teaching value over minimizing edits.
- The final result should read as if it were written fresh with the current doc
  structure in mind.
