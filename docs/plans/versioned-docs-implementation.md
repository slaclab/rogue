# Versioned Documentation Implementation Plan

## Goal

Retain documentation for every release, provide a clear selector for released
and development docs, and keep the current GitHub Pages hosting model.

This plan intentionally excludes per-PR preview publishing.

## Current State

The repository currently publishes docs only on tag pushes, and the deployment
overwrites the root of `gh-pages`.

Relevant repo locations:

- `.github/workflows/rogue_ci.yml`
- `docs/src/conf.py`
- `docs/src/_templates/layout.html`
- `docs/src/_static/custom.js`
- `docs/src/_static/custom.css`

## Source Of Truth

The branch and release model for documentation should be:

- `main`: latest released source only. Do not publish it separately.
- `pre-release`: development documentation source.
- release tags `vX.Y.Z`: immutable released documentation snapshots.

## Target URL Layout

Publish docs under these stable paths:

- `/latest/`
- `/pre-release/`
- `/vX.Y.Z/`
- `/versions/`
- `/` redirected to `/latest/`

Examples:

- `/latest/installing/index.html`
- `/pre-release/installing/index.html`
- `/v6.8.5/installing/index.html`

## Published Variants

### Release Docs

Trigger:

- tag push matching the normal release process

Behavior:

- build docs from the tagged commit
- publish to `/vX.Y.Z/`
- update `/latest/` to the same content
- refresh shared metadata and versions index
- refresh the root redirect to `/latest/`

Release directories are immutable in normal operation. A release may be rebuilt
only by explicit maintainer action.

### Development Docs

Trigger:

- push to `pre-release`

Behavior:

- build docs from the `pre-release` branch head
- publish to `/pre-release/`
- refresh shared metadata and versions index
- do not modify `/latest/`
- do not modify any `/vX.Y.Z/` release snapshot

## Metadata

Generate a single metadata file on `gh-pages`:

- `/versions.json`

Suggested structure:

```json
{
  "default": "latest",
  "versions": [
    {
      "slug": "latest",
      "title": "Latest Release",
      "kind": "alias",
      "url": "/rogue/latest/"
    },
    {
      "slug": "pre-release",
      "title": "Pre-release",
      "kind": "branch",
      "url": "/rogue/pre-release/"
    },
    {
      "slug": "v6.8.5",
      "title": "v6.8.5",
      "kind": "release",
      "url": "/rogue/v6.8.5/"
    }
  ]
}
```

Requirements:

- sort releases newest-first
- keep `latest` first
- keep `pre-release` near the top
- use one canonical data source for the selector and versions page

## Selector UI

Use the existing custom Sphinx hooks instead of changing themes.

Implementation points:

- add a selector container in `docs/src/_templates/layout.html`
- extend `docs/src/_static/custom.js` to fetch `/versions.json`
- style the selector and banners in `docs/src/_static/custom.css`

Behavior:

- detect the current version from the URL path
- render a selector containing:
  - `Latest Release`
  - `Pre-release`
  - recent release tags
  - a link to `All versions`
- when switching versions, attempt to load the same relative page
- if the target page is absent, fall back to that version's landing page

## Version Messaging

Add lightweight context banners:

- on `/pre-release/`:
  - "You are viewing unreleased documentation from `pre-release`."
- on archived `/vX.Y.Z/` pages:
  - "You are viewing archived documentation for `vX.Y.Z`. See `latest` for the newest release."
- on `/latest/`:
  - no archive warning

## Versions Index

Generate a simple page at `/versions/` from the same metadata source.

Suggested sections:

- Latest release
- Development docs
- Release history

Optional metadata:

- release date
- short label such as `current`, `development`, `archived`

## Workflow Structure

Split docs publishing from the current all-in-one CI workflow.

Recommended workflows:

- `.github/workflows/docs_release.yml`
- `.github/workflows/docs_pre_release.yml`

The existing `.github/workflows/rogue_ci.yml` should remain responsible for CI
validation, not long-term documentation branch management.

## Expected Repository Additions

Likely new files:

- `scripts/docs_publish_metadata.py`
- `scripts/docs_generate_versions_page.py`
- optional helper script for root redirect generation

Likely edited files:

- `.github/workflows/rogue_ci.yml`
- `docs/src/_templates/layout.html`
- `docs/src/_static/custom.js`
- `docs/src/_static/custom.css`
- `docs/src/conf.py`
- `pip_requirements.txt` if any new doc-side dependency is introduced

## Acceptance Criteria

- A release publish preserves prior release docs.
- `/latest/` always points to the newest released docs.
- `/pre-release/` reflects the current `pre-release` branch.
- Users can switch versions from within the docs UI.
- Historical release docs remain directly accessible by URL.
- Root `/` resolves users to `/latest/`.
- Development docs never overwrite release snapshots.

## Out Of Scope

This plan does not include:

- per-PR documentation previews
- migration to Read the Docs
- a Sphinx theme migration
- rebuilding all historical tags immediately
