# Performance Publishing And Dashboard Plan

## Goal

Publish durable performance results to `gh-pages` so maintainers can:

- compare a branch's latest perf run against its previous run
- compare the same run against current `main` and `pre-release` baselines
- browse recent per-branch perf history outside transient CI artifacts

The published data should back both the GitHub Actions perf summary and a
simple GitHub Pages dashboard.

## Main Use Cases

### Branch Development

When working on a feature branch, a perf run should answer:

- did this commit improve or regress relative to the previous run on this branch
- how far is this branch from current `main`
- how far is this branch from current `pre-release`

This is the primary day-to-day workflow.

### Stable Reference Baselines

The repository should keep durable published baselines for:

- `main`
- `pre-release`

These should be updated from the latest successful perf artifact published for
those branches.

### Historical Browsing

Maintainers should be able to inspect a branch's recent perf history from
GitHub Pages without relying on artifact retention windows.

## Source Of Truth

The existing `perf_test` job in `.github/workflows/rogue_ci.yml` remains the
producer of raw perf result JSON.

Those raw results are then normalized and published into `gh-pages` by a
separate workflow. The published `gh-pages` data becomes the durable source of
truth for:

- branch history comparisons
- `main` and `pre-release` baselines
- the `/perf/` dashboard
- future docs links into published perf data

## Published Layout

Store perf data outside the versioned docs trees so docs publishes do not
overwrite it.

Target `gh-pages` layout:

```text
perf/
  index.html
  index.json
  refs/
    main/
      latest.json
    pre-release/
      latest.json
  branches/
    <branch-slug>/
      latest.json
      index.json
      history/
        <sha>.json
```

Notes:

- `refs/main/latest.json` is the durable current `main` baseline
- `refs/pre-release/latest.json` is the durable current `pre-release` baseline
- `branches/<branch-slug>/latest.json` is the latest published run for a branch
- `branches/<branch-slug>/history/<sha>.json` preserves recent branch history

## Data Model

Each published summary should include:

- `ref_name`
- `ref_slug`
- `sha`
- `short_sha`
- `published_at`
- `run_id`
- `run_url`
- normalized benchmark rows

Each normalized benchmark row should include:

- benchmark name
- current display string
- primary comparison metric and whether higher or lower is better
- completion/error status
- notes
- raw source metrics

This normalized shape lets CI summary rendering and the dashboard share the
same comparison logic.

## Workflow Structure

### Existing CI Producer

Keep `.github/workflows/rogue_ci.yml` as the perf producer:

- run perf tests
- emit `perf-results/*.json`
- upload `perf-results` artifact

### New Perf Publisher

Add `.github/workflows/perf_publish.yml`:

- trigger on `workflow_run` completion for `Rogue Integration`
- stay disabled by default behind repository variable `ROGUE_ENABLE_PERF_PUBLISH`
- download the `perf-results` artifact for the completed run
- publish the normalized result into `gh-pages/perf/...`
- update `refs/main` and `refs/pre-release` when those branches publish
- rebuild `/perf/index.html` and `/perf/index.json`

### Shared `gh-pages` Serialization

All workflows that push `gh-pages` should use the same concurrency group so the
docs publishers and perf publisher do not race.

## CI Summary Behavior

The GitHub Actions perf summary should:

1. load the current run's raw perf result JSON
2. load the published latest branch result for the current branch
3. load the published `main` baseline
4. load the published `pre-release` baseline
5. render a comparison table per benchmark

Target table columns:

- benchmark
- current metric
- vs previous branch run
- vs `main`
- vs `pre-release`
- complete
- rx errors
- notes

If a baseline is unavailable, render `n/a` instead of failing the job.

## Dashboard Behavior

Publish a simple `/perf/` dashboard page on GitHub Pages.

The page should show:

- current `main` and `pre-release` baseline metadata
- one section per tracked branch
- latest branch run metadata and links
- recent branch history
- per-benchmark comparisons against:
  - previous branch run
  - `main`
  - `pre-release`

The dashboard does not need client-side interactivity to be useful. A static
generated HTML page is sufficient for the first version.

## Retention Policy

Keep a bounded amount of branch history to avoid unbounded `gh-pages` growth.

Initial policy:

- keep the latest published result for every branch
- keep the most recent 20 history entries per branch

This can be adjusted later if the repository accumulates too many active
branches.

## Acceptance Criteria

- a feature-branch perf run compares against the previous run on that branch
- the same summary compares against current `main` and `pre-release`
- `main` and `pre-release` baselines survive artifact expiration
- `/perf/` exposes recent branch history without opening CI artifacts
- docs publishing does not overwrite perf data
- perf publishing does not overwrite docs content

## Rollout

Recommended rollout:

1. Merge the code with `ROGUE_ENABLE_PERF_PUBLISH` unset or set to `false`.
2. Verify ordinary branch CI and existing docs publishing remain unchanged.
3. Enable repository variable `ROGUE_ENABLE_PERF_PUBLISH=true`.
4. Observe the first `gh-pages/perf/` publication and validate the generated dashboard.
5. Disable the variable again if rollback is needed.

## Follow-Up Ideas

- add a docs page that links to `/perf/`
- add release-tag perf snapshots under `perf/releases/`
- add charts once the basic published history is stable
