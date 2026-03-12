# Documentation Merge Guidelines

Use these directives when merging an older documentation page into a newer
reorganized page.

## Goal

Produce a new document that combines the best material from the old and new
versions into a single coherent narrative. Do not mechanically append recovered
text. Rewrite the page so it reads like one intentional document.

## Comparison Method

1. Read the entirety of the old page.
2. Read the entirety of the new page.
3. Identify what the old page does better.
4. Identify what the new page does better.
5. Rewrite the full page around a clean narrative that preserves the best of
   both.

## Narrative Structure

- Start with general use cases and the basic purpose of the subject.
- Explain the common workflow or lifecycle before advanced details.
- Present examples in the order a user is likely to need them.
- Move advanced mechanics, performance details, and edge cases later in the
  document.
- Prefer prose and narrative exposition over compressed bullet summaries.
- Use bullets when the content is naturally list-shaped, but do not reduce core
  explanation to bullets if a paragraph would teach the subject better.

## Example And Commentary Style

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

## Technical Content Priorities

- Recover conceptual explanations that were lost during the reorganization.
- Keep newer structure, navigation, and page boundaries when they improve the
  docs.
- Preserve detailed discussions of important mechanics, such as iterator use,
  zero-copy behavior, ownership, ordering, or performance tradeoffs.
- When older content contains the better explanation, integrate it into the new
  structure rather than copying the old structure back wholesale.

## Type Naming Style

- Refer to Rogue class types by their proper names, such as ``Master``,
  ``Slave``, ``Frame``, ``Buffer``, and ``FrameIterator``.
- These type names should usually be written in fixed-width formatting.
- Do not casually downcase class-type references in prose when the text is
  referring to the Rogue type rather than to a generic concept.
- Variable names in code examples do not need to follow this rule, but prose
  and explanatory comments usually should.

## Section Title Style

- Section titles should read like proper names, not sentence fragments.
- Use title case.
- Examples:
  - `C++ Master Subclass`
  - `Python Master Subclass`
  - `API Reference`
  - `Related Topics`
- Avoid headings like descriptive notes or phrases when a proper section name
  would do.

## List Style

- Items in a list should be capitalized.
- This applies to bullet lists and numbered lists.
- If a list item starts with a type name, concept name, or ordinary prose, use
  an initial capital letter.

## Ending Sections

Toward the end of a document, use these labels consistently:

### What To Explore Next

Use this for links to topics in the same subsection as the current page.

Example:
- A page in `stream_interface/` should link to other `stream_interface/` pages
  here.
- If there are no same-subsection links that genuinely help the reader continue,
  omit `What To Explore Next` rather than forcing a weak list.

### Related Topics

Use this for links to related topics in other subsections.

Example:
- A page in `stream_interface/` can link to `custom_module/` here.
- If there is no genuinely useful cross-subsection link, omit `Related Topics`
  rather than forcing a weak one.

### API Reference

Use this for links to the relevant API reference pages for classes, helpers,
functions, or modules discussed in the document.

## Rewrite Standard

- Do not treat the job as a diff merge.
- Do not preserve awkward transitional text just because it already exists.
- Remove partial merges, stray headings, and mislabeled sections.
- Favor clarity, flow, and teaching value over minimizing edits.
- The final result should read as if it were written fresh with the current doc
  structure in mind.
