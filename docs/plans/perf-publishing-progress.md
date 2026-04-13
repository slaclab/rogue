# Performance Publishing Progress

## Purpose

This document records the current implementation state of the durable
performance publishing work so the effort can be resumed without re-reading the
full conversation history.

Related plan:

- `perf-publishing-dashboard.md`

## Current Status

Implementation work has been completed locally and is currently guarded behind
an explicit rollout gate.

Key point:

- merging the code does **not** activate perf publishing by itself
- publication is gated by repository variable `ROGUE_ENABLE_PERF_PUBLISH`

## Implemented So Far

### CI Summary

The perf job in `.github/workflows/rogue_ci.yml` now:

- fetches `origin/gh-pages` if available
- renders perf summary using published data when present
- compares the current run against:
  - the latest published run for the same branch
  - the latest published `main` baseline
  - the latest published `pre-release` baseline

Relevant files:

- `.github/workflows/rogue_ci.yml`
- `scripts/ci_perf_summary.py`

### Durable Publisher

A new workflow publishes perf data to `gh-pages`:

- `.github/workflows/perf_publish.yml`

It:

- triggers from completed `Rogue Integration` runs
- downloads the `perf-results` artifact
- normalizes raw perf JSON
- writes published data under `gh-pages/perf/`
- updates the static `/perf/index.html` dashboard

The workflow is currently gated by:

- `vars.ROGUE_ENABLE_PERF_PUBLISH == 'true'`

### Shared Perf Data Model

Shared normalization and comparison logic now lives in:

- `scripts/perf_data.py`

This module is used by both:

- `scripts/ci_perf_summary.py`
- `scripts/perf_publish.py`

### Dashboard Output

The publisher currently generates:

- `perf/index.json`
- `perf/index.html`
- `perf/refs/main/latest.json`
- `perf/refs/pre-release/latest.json`
- `perf/branches/<branch-slug>/latest.json`
- `perf/branches/<branch-slug>/index.json`
- `perf/branches/<branch-slug>/history/<sha>.json`

### `gh-pages` Serialization Safety

The docs publishers and perf publisher now share the same concurrency group:

- `gh-pages-publish`

Updated workflows:

- `.github/workflows/docs_pre_release.yml`
- `.github/workflows/docs_release.yml`
- `.github/workflows/perf_publish.yml`

This was added so independent workflows do not push competing changes to
`gh-pages` at the same time.

### Tests Added

Focused tests were added for the new perf tooling:

- `tests/utilities/test_perf_tools.py`

These cover:

- result normalization
- branch history publishing
- baseline publication
- summary rendering against published data

## Local Verification Completed

The following checks were run successfully:

```bash
python3 -m py_compile scripts/perf_data.py scripts/perf_publish.py scripts/ci_perf_summary.py
source ./setup_rogue.sh && /Users/bareese/miniforge3/envs/rogue_build/bin/python -m pytest tests/utilities/test_perf_tools.py -q
```

## Not Yet Validated In GitHub

The following still need real GitHub-side validation:

- `workflow_run` artifact download in `perf_publish.yml`
- first end-to-end write into `gh-pages/perf/`
- generated `/perf/` dashboard on GitHub Pages
- CI summary output using real published baselines
- interaction between docs publishing and perf publishing under live `gh-pages`

## Rollout State

Current recommended rollout remains:

1. Merge with `ROGUE_ENABLE_PERF_PUBLISH` unset or `false`.
2. Confirm existing docs behavior is unchanged.
3. Set repository variable `ROGUE_ENABLE_PERF_PUBLISH=true`.
4. Observe first publication to `gh-pages/perf/`.
5. Inspect generated dashboard and CI summary behavior.
6. Disable the variable if rollback is needed.

## Likely Next Steps

### First Activation

After merge:

- create repository variable `ROGUE_ENABLE_PERF_PUBLISH`
- set it to `true`
- push a branch that triggers `Rogue Integration`
- inspect the `Performance Publish` workflow
- inspect the resulting `gh-pages` tree

### Validation Checklist

Confirm:

- no docs content outside `perf/` changed unexpectedly
- `perf/refs/main/latest.json` updates on `main`
- `perf/refs/pre-release/latest.json` updates on `pre-release`
- feature branches write to `perf/branches/<slug>/...`
- CI summary shows:
  - previous branch comparison
  - `main` comparison
  - `pre-release` comparison

### Possible Follow-Up Work

- add a Sphinx docs page or docs navigation link to `/perf/`
- add release-tag perf snapshots under `perf/releases/`
- add richer charts once the baseline publishing flow is stable
- add cleanup logic for stale branch directories if needed later

## Risks / Unknowns

- `workflow_run` behavior depends on GitHub-side execution, not local tests
- the current implementation publishes for any branch once enabled, not only
  `main` and `pre-release`
- branch history can grow over time, though per-branch history is capped
- discoverability is currently via `/perf/`; docs navigation integration has
  not been added yet

## Files To Inspect First When Resuming

- `docs/plans/perf-publishing-dashboard.md`
- `docs/plans/perf-publishing-progress.md`
- `.github/workflows/perf_publish.yml`
- `.github/workflows/rogue_ci.yml`
- `scripts/perf_data.py`
- `scripts/perf_publish.py`
- `scripts/ci_perf_summary.py`
- `tests/utilities/test_perf_tools.py`
