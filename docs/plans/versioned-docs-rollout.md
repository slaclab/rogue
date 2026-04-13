# Versioned Documentation Rollout Plan

## Goal

Roll out versioned GitHub Pages publishing without breaking the current docs
site and without waiting for the next release tag to validate the new logic.

## Main Risk

If the new deployment logic is only exercised on release tags, the first full
end-to-end validation would happen at release time. That is avoidable.

The rollout should ensure:

- no PR or ordinary branch push overwrites the current site root
- release publishing can be tested before the next release
- `pre-release` publishing can be validated independently from release aliases

## Safety Rules

1. Do not change the current root site as the first step.
2. Do not let `pre-release` publishing write to `/latest/` or `/vX.Y.Z/`.
3. Do not let manual staging publish to production paths.
4. Keep release publishing tag-driven in production.

## Staged Rollout

### Stage 1: Land The Code Paths

Merge the workflow and scripting changes with:

- production release publishing still restricted to tag events
- `pre-release` publishing enabled only for `/pre-release/`
- manual staging support enabled for release-flow testing

Expected production impact:

- none on merge, unless there is also a push to `pre-release`

### Stage 2: Add Manual Staging Deploy

Add `workflow_dispatch` to the release-doc workflow.

Manual staging runs should publish into a sandbox prefix such as:

- `/staging-docs/`
- or `/test-docs/<run-id>/`

Manual staging should:

- build docs
- generate `versions.json`
- generate the versions index page
- exercise path rewriting and selector logic
- avoid touching:
  - `/latest/`
  - `/vX.Y.Z/`
  - `/`

This is the primary way to validate the release-doc pipeline before the next
actual tag.

### Stage 3: Enable `pre-release` Publishing

Publish the `pre-release` branch to:

- `/pre-release/`

This validates:

- docs build on the branch that accumulates release-bound changes
- GitHub Pages subdirectory publishing
- selector behavior with at least one dev path present
- metadata refresh logic

This stage should still leave:

- `/latest/` untouched
- root `/` untouched
- historical root docs intact

### Stage 4: Validate Production Release Publish

Before the next release, verify from staging and `pre-release` that:

- the docs build is stable
- the generated metadata is correct
- selector links are correct
- fallback navigation behaves sensibly
- the generated root redirect content is correct

Only after that should the team rely on the tag-triggered production release
publish to update:

- `/vX.Y.Z/`
- `/latest/`
- `/`

## Deployment Behavior By Trigger

### Pull Request

Behavior:

- CI only
- no publish to `gh-pages`

Result:

- current docs cannot be overwritten by a PR

### Push To Feature Branch

Behavior:

- CI only
- no publish to `gh-pages`

Result:

- current docs cannot be overwritten by a feature branch

### Push To `pre-release`

Behavior:

- publish to `/pre-release/`
- refresh metadata and versions index
- do not change `/latest/`
- do not change release snapshots
- do not change root `/` during initial rollout

Result:

- dev docs become testable without endangering released docs

### Manual Staging Run

Behavior:

- publish only to a staging prefix
- do not touch production aliases or root

Result:

- release-flow validation before the next real tag

### Tag Push

Behavior:

- publish release snapshot to `/vX.Y.Z/`
- update `/latest/`
- update root `/` redirect only after an explicit rollout gate is enabled

Result:

- production release docs move forward only on release

## Recommended Workflow Gating

Use explicit conditions so each path can only write where intended.

Recommended controls:

- separate workflows for release and `pre-release`
- explicit publish destination variables
- explicit validation for manual workflow inputs that affect publish paths
- explicit `if:` conditions by event type and ref
- keep production root redirect generation behind an explicit rollout flag until
  staging has been reviewed and accepted
- branch-scoped or event-scoped permissions where possible

## Validation Checklist

Before enabling full production cutover:

- manual staging deploy succeeds
- staging version selector renders correctly
- `pre-release` docs publish correctly
- `pre-release` banner renders correctly
- metadata contains `latest`, `pre-release`, and release entries in the right order
- same-page version switching works for common pages
- fallback to target version landing page works when a page is missing
- current public root docs remain unchanged

## Cutover Decision

Do not switch production root `/` to a generated redirect until staging has
been reviewed and accepted, and keep that behavior behind an explicit rollout
flag until then.

That keeps the current site behavior intact while the new machinery is proven.

## Rollback

If staging or `pre-release` deployment reveals problems:

- disable the new workflow trigger
- stop publishing `pre-release`
- leave the existing release-root docs untouched

Because the rollout avoids early modification of production release aliases and
root, rollback should be operationally simple.
